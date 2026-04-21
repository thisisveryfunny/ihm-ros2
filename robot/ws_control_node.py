"""
Movement control node: receives WebSocket commands from the dashboard and
publishes geometry_msgs/Twist to /cmd_vel.

WebSocket endpoint:
  ws://{server_url}/ws?role=robot

Messages consumed:
  { "type": "command", "direction": "front"|"back"|"left"|"right"|"stop" }

Camera servo control is handled by camera_control_node.py over /ws/camera.
Battery / IMU / odometry telemetry is handled by telemetry_node.py.
"""

import asyncio
import json
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

import websockets


LINEAR_SPEED = 0.3
ANGULAR_SPEED = 1.0
RECONNECT_DELAY_S = 2.0


class WSControlNode(Node):

    def __init__(self):
        super().__init__("ws_control_node")

        self.declare_parameter("server_url", "localhost:5173")
        self.server_url = (
            self.get_parameter("server_url").get_parameter_value().string_value
        )

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        self.get_logger().info(
            f"Movement control node started, connecting to ws://{self.server_url}/ws?role=robot"
        )

    def publish_cmd(self, lin: float, ang: float) -> None:
        msg = Twist()
        msg.linear.x = float(lin)
        msg.angular.z = float(ang)
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"PUBLISHED → linear.x={lin}, angular.z={ang}")

    def handle_command(self, data: dict) -> None:
        if data.get("type") != "command":
            return

        direction = data.get("direction")
        self.get_logger().info(f"COMMAND RECEIVED → direction={direction}")

        if direction == "front":
            self.publish_cmd(LINEAR_SPEED, 0.0)
        elif direction == "back":
            self.publish_cmd(-LINEAR_SPEED, 0.0)
        elif direction == "left":
            self.publish_cmd(0.0, ANGULAR_SPEED)
        elif direction == "right":
            self.publish_cmd(0.0, -ANGULAR_SPEED)
        elif direction == "stop":
            self.publish_cmd(0.0, 0.0)
        else:
            self.get_logger().warn(f"UNKNOWN direction: {direction}")

    async def websocket_loop(self) -> None:
        ws_url = f"ws://{self.server_url}/ws?role=robot"
        while rclpy.ok():
            try:
                self.get_logger().info(f"Connecting to WS → {ws_url}")
                async with websockets.connect(ws_url) as ws:
                    self.get_logger().info("CONNECTED to WebSocket")
                    async for message in ws:
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError as e:
                            self.get_logger().error(f"JSON PARSE ERROR: {e}")
                            continue
                        try:
                            self.handle_command(data)
                        except Exception as e:
                            self.get_logger().error(f"COMMAND HANDLER ERROR: {e}")
            except Exception as e:
                self.get_logger().error(f"WS CONNECTION ERROR: {e}")
                await asyncio.sleep(RECONNECT_DELAY_S)


def main():
    rclpy.init()
    node = WSControlNode()

    # Spin ROS2 in a background thread so publishing stays responsive while
    # the asyncio WebSocket loop owns the main thread.
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    try:
        asyncio.run(node.websocket_loop())
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
