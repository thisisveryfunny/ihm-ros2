"""
Collision detection node: reads lidar data and stops the robot if an obstacle is too close.

Subscribes to:
  /scan  (sensor_msgs/msg/LaserScan) — MS200 lidar

Publishes:
  /cmd_vel             (geometry_msgs/msg/Twist)  — sends stop command on collision
  /collision_blocked   (std_msgs/msg/Bool)        — blocked state for control_node

Also sends collision-alert messages via WebSocket to notify the dashboard.

ROS2 parameters:
  server_url    (string, default "localhost:5173")
  min_distance  (double, default 0.3 meters)
"""

import json
import math
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

import websocket


class CollisionNode(Node):
    # QoS compatible with the Yahboom driver (publishes with best_effort/volatile)
    SENSOR_QOS = QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
    )

    def __init__(self):
        super().__init__('collision_node')

        self.declare_parameter('server_url', 'localhost:5173')
        self.declare_parameter('min_distance', 0.3)

        self.server_url = self.get_parameter('server_url').get_parameter_value().string_value
        self.min_distance = self.get_parameter('min_distance').get_parameter_value().double_value

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.blocked_pub = self.create_publisher(Bool, '/collision_blocked', 10)

        # Subscriber (use BEST_EFFORT QoS to match the Yahboom driver's sensor topics)
        self.create_subscription(LaserScan, '/scan', self._scan_callback, self.SENSOR_QOS)

        # State
        self._blocked = False
        self._ws = None
        self._ws_lock = threading.Lock()

        # WebSocket connection in daemon thread
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()

        self.get_logger().info(
            f'Collision node started (threshold: {self.min_distance}m), '
            f'connecting to ws://{self.server_url}/ws?role=robot'
        )

    def _ws_loop(self):
        """Connect to WebSocket with auto-reconnect."""
        while rclpy.ok():
            try:
                ws_url = f'ws://{self.server_url}/ws?role=robot'
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_ws_open,
                    on_close=self._on_ws_close,
                    on_error=self._on_ws_error,
                )
                ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                self.get_logger().warn(f'WebSocket error: {e}')

            if not rclpy.ok():
                break
            self.get_logger().info('Reconnecting in 2 seconds...')
            time.sleep(2)

    def _on_ws_open(self, ws):
        with self._ws_lock:
            self._ws = ws
        self.get_logger().info('WebSocket connected')

    def _on_ws_close(self, ws, close_status_code, close_msg):
        with self._ws_lock:
            self._ws = None
        self.get_logger().info('WebSocket disconnected')

    def _on_ws_error(self, ws, error):
        self.get_logger().warn(f'WebSocket error: {error}')

    def _send_ws(self, msg: dict):
        """Send a message via WebSocket if connected."""
        with self._ws_lock:
            ws = self._ws
        if ws:
            try:
                ws.send(json.dumps(msg))
            except Exception as e:
                self.get_logger().warn(f'Failed to send WS message: {e}')

    def _scan_callback(self, msg: LaserScan):
        """Process lidar scan and detect collisions."""
        # Filter out invalid readings (0.0, inf, NaN)
        valid_ranges = [
            r for r in msg.ranges
            if r > msg.range_min and r < msg.range_max and math.isfinite(r)
        ]

        if not valid_ranges:
            return

        closest = min(valid_ranges)
        was_blocked = self._blocked

        if closest < self.min_distance:
            self._blocked = True

            # Stop the robot immediately
            self.cmd_vel_pub.publish(Twist())

            # Notify on state transition only
            if not was_blocked:
                self.get_logger().warn(
                    f'COLLISION ALERT: obstacle at {closest:.2f}m (threshold: {self.min_distance}m)'
                )
                self._send_ws({
                    'type': 'collision-alert',
                    'distance': round(closest, 3),
                    'blocked': True,
                })
        else:
            self._blocked = False

            if was_blocked:
                self.get_logger().info(
                    f'Collision cleared: nearest obstacle at {closest:.2f}m'
                )
                self._send_ws({
                    'type': 'collision-alert',
                    'distance': round(closest, 3),
                    'blocked': False,
                })

        # Always publish the blocked state so control_node stays in sync
        blocked_msg = Bool()
        blocked_msg.data = self._blocked
        self.blocked_pub.publish(blocked_msg)


def main(args=None):
    rclpy.init(args=args)
    node = CollisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
