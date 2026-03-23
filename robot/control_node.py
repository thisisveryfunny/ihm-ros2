"""
Control node: connects to the web server WebSocket and translates movement commands to /cmd_vel.

WebSocket messages received:
  { "type": "command", "direction": "front"|"back"|"left"|"right"|"stop" }

Published topic:
  /cmd_vel  (geometry_msgs/msg/Twist)

Subscribed topics:
  /collision_blocked  (std_msgs/msg/Bool)  — ignores movement commands when True

ROS2 parameters:
  server_url     (string, default "localhost:5173")
  linear_speed   (double, default 0.2 m/s)
  angular_speed  (double, default 1.0 rad/s)
"""

import json
import threading
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

import websocket


class ControlNode(Node):
    def __init__(self):
        super().__init__('control_node')

        self.declare_parameter('server_url', 'localhost:5173')
        self.declare_parameter('linear_speed', 0.2)
        self.declare_parameter('angular_speed', 1.0)

        self.server_url = self.get_parameter('server_url').get_parameter_value().string_value
        self.linear_speed = self.get_parameter('linear_speed').get_parameter_value().double_value
        self.angular_speed = self.get_parameter('angular_speed').get_parameter_value().double_value

        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Collision state from collision_node
        self._blocked = False
        self.create_subscription(Bool, '/collision_blocked', self._blocked_callback, 10)

        # Start WebSocket listener in a daemon thread
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()

        self.get_logger().info(
            f'Control node started, connecting to ws://{self.server_url}/ws?role=robot'
        )

    def _ws_loop(self):
        """Connect to WebSocket with auto-reconnect."""
        while rclpy.ok():
            try:
                ws_url = f'ws://{self.server_url}/ws?role=robot'
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                self.get_logger().warn(f'WebSocket error: {e}')

            if not rclpy.ok():
                break
            self.get_logger().info('Reconnecting in 2 seconds...')
            time.sleep(2)

    def _on_open(self, ws):
        self.get_logger().info('WebSocket connected')

    def _on_close(self, ws, close_status_code, close_msg):
        self.get_logger().info('WebSocket disconnected')

    def _on_error(self, ws, error):
        self.get_logger().warn(f'WebSocket error: {error}')

    def _blocked_callback(self, msg: Bool):
        self._blocked = msg.data

    def _on_message(self, ws, message):
        try:
            msg = json.loads(message)
        except json.JSONDecodeError:
            return

        if msg.get('type') != 'command':
            return

        direction = msg.get('direction')

        # When collision-blocked, ignore movement commands (only allow stop)
        if self._blocked and direction != 'stop':
            return

        twist = Twist()

        if direction == 'front':
            twist.linear.x = self.linear_speed
        elif direction == 'back':
            twist.linear.x = -self.linear_speed
        elif direction == 'left':
            twist.angular.z = self.angular_speed
        elif direction == 'right':
            twist.angular.z = -self.angular_speed
        # 'stop' leaves twist as all zeros

        self.cmd_vel_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
