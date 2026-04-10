"""
Telemetry node: subscribes to ROS2 sensor topics and POSTs data to the web server API every 2 seconds.

Topics:
  /imu               (sensor_msgs/msg/Imu)            → POST /api/imu
  /battery           (std_msgs/msg/UInt16)              → POST /api/batterie
  /odom_raw          (nav_msgs/msg/Odometry)            → POST /api/vitesse

ROS2 parameters:
  server_url  (string, default "http://localhost:5173")
"""

import math
import os
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Imu
from std_msgs.msg import UInt16
from nav_msgs.msg import Odometry

import requests


class TelemetryNode(Node):
    # QoS matching the Yahboom driver (publishes with reliable/volatile)
    SENSOR_QOS = QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
    )

    def __init__(self):
        super().__init__('telemetry_node')

        self.declare_parameter('server_url', 'http://localhost:5173')
        self.server_url = self.get_parameter('server_url').get_parameter_value().string_value

        # Latest cached readings
        self._imu_data = None
        self._battery = None
        self._speed = None
        self._lock = threading.Lock()

        # Subscribers (use RELIABLE QoS to match the Yahboom driver's sensor topics)
        self.create_subscription(Imu, '/imu', self._imu_callback, self.SENSOR_QOS)
        self.create_subscription(UInt16, '/battery', self._battery_callback, self.SENSOR_QOS)
        self.create_subscription(Odometry, '/odom_raw', self._odom_callback, self.SENSOR_QOS)

        # Timer: POST every 2 seconds
        self.create_timer(2.0, self._send_telemetry)

        self.get_logger().info(f'Telemetry node started, posting to {self.server_url}')
        self.get_logger().info(f'ROS_DOMAIN_ID = {os.environ.get("ROS_DOMAIN_ID", "NOT SET")}')
        self.get_logger().info(
            f'QoS: reliability={self.SENSOR_QOS.reliability.name}, '
            f'durability={self.SENSOR_QOS.durability.name}, depth={self.SENSOR_QOS.depth}'
        )

    def _imu_callback(self, msg: Imu):
        self.get_logger().info('Received IMU data', once=True)
        with self._lock:
            self._imu_data = msg

    def _battery_callback(self, msg: UInt16):
        with self._lock:
            self._battery = msg.data

    def _odom_callback(self, msg: Odometry):
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        speed = math.sqrt(vx * vx + vy * vy)
        with self._lock:
            self._speed = speed

    def _send_telemetry(self):
        """Collect cached data and POST to the web server in a background thread."""
        with self._lock:
            imu = self._imu_data
            battery = self._battery
            speed = self._speed

        self.get_logger().info(
            f'Timer tick: imu={imu is not None}, '
            f'battery={battery is not None}, speed={speed is not None}'
        )

        # Run HTTP requests in a thread so we don't block the ROS2 executor
        thread = threading.Thread(
            target=self._do_post,
            args=(imu, battery, speed),
            daemon=True,
        )
        thread.start()

    def _do_post(self, imu, battery, speed):
        url = self.server_url

        # POST battery
        if battery is not None:
            try:
                requests.post(
                    f'{url}/api/batterie',
                    json={'percentage': float(battery)},
                    timeout=5,
                )
            except Exception as e:
                self.get_logger().warn(f'Failed to post battery: {e}')

        # POST IMU (accel + gyro from /imu)
        if imu is not None:
            payload = {
                'accel_x': imu.linear_acceleration.x,
                'accel_y': imu.linear_acceleration.y,
                'accel_z': imu.linear_acceleration.z,
                'gyro_x': imu.angular_velocity.x,
                'gyro_y': imu.angular_velocity.y,
                'gyro_z': imu.angular_velocity.z,
            }
            try:
                requests.post(f'{url}/api/imu', json=payload, timeout=5)
            except Exception as e:
                self.get_logger().warn(f'Failed to post IMU: {e}')

        # POST speed
        if speed is not None:
            try:
                requests.post(
                    f'{url}/api/vitesse',
                    json={'speed': float(speed)},
                    timeout=5,
                )
            except Exception as e:
                self.get_logger().warn(f'Failed to post speed: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = TelemetryNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
