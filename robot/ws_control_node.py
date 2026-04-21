import asyncio
import time
import requests
import json
import websockets
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import UInt16
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

WS_SERVER = "ws://10.10.211.71:5173/ws?role=robot"
API_BASE = "http://10.10.211.71:5173/api"
THROTTLE_INTERVAL = 1.0  # seconds


class WSControlNode(Node):

    def __init__(self):
        super().__init__("ws_control_node")

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(LaserScan, "/scan", self.scan_cb, 10)
        self.obstacle_front = False
        self.create_subscription(UInt16, "/battery", self.battery_cb, 10)
        self.create_subscription(Imu, "/imu", self.imu_cb, 10)
        self.create_subscription(Odometry, "/odom_raw", self.odom_cb, 10)

        self._last_sent = {"batterie": 0.0, "vitesse": 0.0, "imu": 0.0}

        # Populated from main() so _send_ws can schedule coroutines from
        # the ROS spin thread onto the asyncio loop.
        self.ws = None
        self._loop = None

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
        voltage = msg.data
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
        loop.run_until_complete(node.websocket_loop())
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
