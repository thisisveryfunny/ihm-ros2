import asyncio
import time
import requests
import json
import websockets
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import UInt16, Int32
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

WS_SERVER = "ws://10.10.211.145:5173/ws?role=robot"
WS_CAMERA_SERVER = "ws://10.10.211.145:5173/ws/camera?role=robot"
API_BASE = "http://10.10.211.145:5173/api"
THROTTLE_INTERVAL = 1.0  # seconds

# Camera servo config — driven via Yahboom /servo_s1 (pan) and /servo_s2 (tilt).
# Yahboom servos use an absolute 0-180 degree range with 90 as the centre.
PAN_CENTER = 90
PAN_MIN = 0
PAN_MAX = 180
TILT_CENTER = 90
TILT_MIN = 45
TILT_MAX = 135
PAN_STEP = 2   # degrees per tick
TILT_STEP = 2  # degrees per tick
TICK_HZ = 30.0


class WSControlNode(Node):

    def __init__(self):
        super().__init__("ws_control_node")

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(LaserScan, "/scan", self.scan_cb, 10)
        self.obstacle_front = False
        self.create_subscription(UInt16, "/battery", self.battery_cb, 10)
        self.create_subscription(Imu, "/imu", self.imu_cb, 10)
        self.create_subscription(Odometry, "/odom_raw", self.odom_cb, 10)

        # Yahboom pan/tilt servo publishers
        self.pan_pub = self.create_publisher(Int32, "/servo_s1", 10)
        self.tilt_pub = self.create_publisher(Int32, "/servo_s2", 10)

        self._last_sent = {"batterie": 0.0, "vitesse": 0.0, "imu": 0.0}

        # Populated from main() so _send_ws can schedule coroutines from
        # the ROS spin thread onto the asyncio loop.
        self.ws = None
        self.ws_camera = None
        self._loop = None

        # ── Camera servo state ───────────────────────────────────────
        self._pan_angle = PAN_CENTER
        self._tilt_angle = TILT_CENTER
        self._pan_dir = 0   # -1 left, +1 right, 0 stop
        self._tilt_dir = 0  # -1 down, +1 up, 0 stop
        self._servo_lock = threading.Lock()
        self._tick_dt = 1.0 / TICK_HZ

        # Publish initial centred pose so the servos snap to a known state
        self._publish_servo_angles(self._pan_angle, self._tilt_angle)

        # Tick thread drives continuous pan/tilt motion while a key is held
        self._tick_thread = threading.Thread(target=self._servo_tick_loop, daemon=True)
        self._tick_thread.start()

        self.get_logger().info("WebSocket control node started")

    def _post_throttled(self, endpoint: str, payload: dict) -> bool:
        now = time.monotonic()
        if now - self._last_sent[endpoint] < THROTTLE_INTERVAL:
            return False
        self._last_sent[endpoint] = now
        try:
            requests.post(f"{API_BASE}/{endpoint}", json=payload, timeout=1)
            return True
        except Exception as e:
            self.get_logger().error(f"{endpoint} send error: {e}")
            return False

    def _send_ws(self, payload):
        if self.ws is None or self._loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps(payload)),
                self._loop,
            )
        except Exception as e:
            self.get_logger().error(f"WS send error: {e}")

    def scan_cb(self, msg):
        # check 60° in front of robot
        front = msg.ranges[150:210]

        valid = [d for d in front if 0.01 < d < 10.0]
        if not valid:
            return

        min_dist = min(valid)

        if min_dist < 0.30:
            if not self.obstacle_front:
                self.publish_cmd(0.0, 0.0)
                self.get_logger().warn(f"⚠️ Obstacle detected at {min_dist:.2f}m")
                self._send_ws({
                    'type': 'collision-alert',
                    'distance': round(min_dist, 3),
                    'blocked': True,
                })

            self.obstacle_front = True
        else:
            if self.obstacle_front:

                self.get_logger().info(f"✅ Path clear at {min_dist:.2f}m")
                self._send_ws({
                    'type': 'collision-alert',
                    'distance': round(min_dist, 3),
                    'blocked': False,
                })
            self.obstacle_front = False

    # 🔋 Battery
    def battery_cb(self, msg):
        raw = msg.data
        self.get_logger().info(f"Battery raw UInt16: {raw}")

        # TODO: adjust divisor once the unit is confirmed via `ros2 topic echo /battery`
        voltage = raw / 100.0  # centivolts assumption (e.g. 750 → 7.5V)
        min_v = 6.4
        max_v = 8.4
        percentage = (voltage - min_v) / (max_v - min_v) * 100
        percentage = max(0, min(100, percentage))

        payload = {"percentage": float(percentage)}
        if self._post_throttled("batterie", payload):
            self.get_logger().info(f"Battery sent: {percentage:.1f}% ({voltage:.2f}V)")

    # 🚗 Speed
    def odom_cb(self, msg):
        payload = {"speed": float(msg.twist.twist.linear.x)}
        self._post_throttled("vitesse", payload)

    # 🧭 IMU
    def imu_cb(self, msg):
        payload = {
            "accel_x": msg.linear_acceleration.x,
            "accel_y": msg.linear_acceleration.y,
            "accel_z": msg.linear_acceleration.z,
            "gyro_x": msg.angular_velocity.x,
            "gyro_y": msg.angular_velocity.y,
            "gyro_z": msg.angular_velocity.z,
        }
        self._post_throttled("imu", payload)

    def publish_cmd(self, lin, ang):
        msg = Twist()
        msg.linear.x = float(lin)
        msg.angular.z = float(ang)
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"PUBLISHED → linear.x={lin}, angular.z={ang}")

    def handle_command(self, data):
        self.get_logger().info(f"RAW PARSED DATA → {data}")

        if data.get("type") != "command":
            self.get_logger().warn("Ignored message (not type=command)")
            return

        direction = data.get("direction")
        self.get_logger().info(f"COMMAND RECEIVED → direction={direction}")

        if direction == "front":
            if self.obstacle_front:
                self.get_logger().warn("Blocked forward command (obstacle)")
                self.publish_cmd(0.0, 0.0)
            else:
                self.publish_cmd(0.3, 0.0)
        elif direction == "back":
            self.publish_cmd(-0.3, 0.0)
        elif direction == "left":
            self.publish_cmd(0.0, 1.0)
        elif direction == "right":
            self.publish_cmd(0.0, -1.0)
        elif direction == "stop":
            self.publish_cmd(0.0, 0.0)
        else:
            self.get_logger().warn(f"UNKNOWN direction: {direction}")

    # ── Camera servo tick + handler ──────────────────────────────────

    @staticmethod
    def _clamp(value: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, value))

    def _publish_servo_angles(self, pan: int, tilt: int) -> None:
        pan_msg = Int32()
        pan_msg.data = int(pan)
        self.pan_pub.publish(pan_msg)

        tilt_msg = Int32()
        tilt_msg.data = int(tilt)
        self.tilt_pub.publish(tilt_msg)

    def _servo_tick_loop(self) -> None:
        while rclpy.ok():
            with self._servo_lock:
                pan_dir = self._pan_dir
                tilt_dir = self._tilt_dir

            if pan_dir == 0 and tilt_dir == 0:
                time.sleep(self._tick_dt)
                continue

            with self._servo_lock:
                if pan_dir != 0:
                    self._pan_angle = self._clamp(
                        self._pan_angle + pan_dir * PAN_STEP, PAN_MIN, PAN_MAX
                    )
                if tilt_dir != 0:
                    self._tilt_angle = self._clamp(
                        self._tilt_angle + tilt_dir * TILT_STEP, TILT_MIN, TILT_MAX
                    )
                pan_a = self._pan_angle
                tilt_a = self._tilt_angle

            self._publish_servo_angles(pan_a, tilt_a)
            self.get_logger().info(f"Camera → pan={pan_a}° tilt={tilt_a}°")

            time.sleep(self._tick_dt)

    def handle_camera(self, data):
        direction = data.get("direction")
        self.get_logger().info(f"CAMERA RECEIVED → direction={direction}")
        with self._servo_lock:
            if direction == "left":
                self._pan_dir = -1
            elif direction == "right":
                self._pan_dir = 1
            elif direction == "up":
                self._tilt_dir = 1
            elif direction == "down":
                self._tilt_dir = -1
            elif direction == "stop":
                self._pan_dir = 0
                self._tilt_dir = 0
            else:
                self.get_logger().warn(f"UNKNOWN camera direction: {direction}")

    # ── WebSocket loops ──────────────────────────────────────────────

    async def websocket_loop(self):
        while True:
            try:
                self.get_logger().info(f"Connecting to WS → {WS_SERVER}")
                async with websockets.connect(WS_SERVER) as ws:
                    self.ws = ws
                    self.get_logger().info("CONNECTED to WebSocket")
                    async for message in ws:
                        self.get_logger().info(f"RAW MESSAGE → {message}")
                        try:
                            data = json.loads(message)
                        except Exception as e:
                            self.get_logger().error(f"JSON PARSE ERROR: {e}")
                            continue
                        try:
                            self.handle_command(data)
                        except Exception as e:
                            self.get_logger().error(f"COMMAND HANDLER ERROR: {e}")
            except Exception as e:
                self.get_logger().error(f"WS CONNECTION ERROR: {e}")
                self.ws = None
                await asyncio.sleep(2)

    async def camera_websocket_loop(self):
        while True:
            try:
                self.get_logger().info(f"Connecting to camera WS → {WS_CAMERA_SERVER}")
                async with websockets.connect(WS_CAMERA_SERVER) as ws:
                    self.ws_camera = ws
                    self.get_logger().info("CONNECTED to camera WebSocket")
                    async for message in ws:
                        try:
                            data = json.loads(message)
                        except Exception as e:
                            self.get_logger().error(f"CAMERA JSON PARSE ERROR: {e}")
                            continue
                        if data.get("type") == "camera":
                            try:
                                self.handle_camera(data)
                            except Exception as e:
                                self.get_logger().error(f"CAMERA HANDLER ERROR: {e}")
            except Exception as e:
                self.get_logger().error(f"CAMERA WS CONNECTION ERROR: {e}")
                self.ws_camera = None
                # Safety: stop motion on disconnect so the servos don't drift
                with self._servo_lock:
                    self._pan_dir = 0
                    self._tilt_dir = 0
                await asyncio.sleep(2)


def main():
    rclpy.init()

    node = WSControlNode()

    # Capture the asyncio loop so the ROS spin thread can schedule WS sends
    # onto it via run_coroutine_threadsafe.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    node._loop = loop

    # Run ROS spinning in background
    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()

    try:
        loop.run_until_complete(
            asyncio.gather(
                node.websocket_loop(),
                node.camera_websocket_loop(),
            )
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
