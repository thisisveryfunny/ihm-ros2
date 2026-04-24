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


BATTERY_EMPTY_V = 6.0
BATTERY_FULL_V = 8.4


def battery_percentage_from_deci_volts(raw: int) -> tuple[float, float]:
    voltage = raw / 10.0
    percentage = (voltage - BATTERY_EMPTY_V) / (BATTERY_FULL_V - BATTERY_EMPTY_V) * 100
    return voltage, max(0.0, min(100.0, percentage))


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

        # Message counters for periodic heartbeat logging
        self._imu_count = 0
        self._battery_count = 0
        self._odom_count = 0

        # Subscribers (use RELIABLE QoS to match the Yahboom driver's sensor topics)
        self.create_subscription(Imu, '/imu', self._imu_callback, self.SENSOR_QOS)
        self.create_subscription(UInt16, '/battery', self._battery_callback, self.SENSOR_QOS)
        self.create_subscription(Odometry, '/odom_raw', self._odom_callback, self.SENSOR_QOS)

        # Timer: POST every 2 seconds
        self.create_timer(2.0, self._send_telemetry)

        # One-shot timer to list discovered topics on the ROS graph after startup.
        self._graph_timer = self.create_timer(2.0, self._log_discovered_topics)

        self.get_logger().info(f'Telemetry node started, posting to {self.server_url}')
        self.get_logger().info(f'SERVER_URL env = {os.environ.get("SERVER_URL", "NOT SET")}')
        self.get_logger().info(f'ROS_DOMAIN_ID = {os.environ.get("ROS_DOMAIN_ID", "NOT SET")}')
        self.get_logger().info(
            f'QoS: reliability={self.SENSOR_QOS.reliability.name}, '
            f'durability={self.SENSOR_QOS.durability.name}, depth={self.SENSOR_QOS.depth}'
        )
        self.get_logger().info(
            'Note: network_mode=host — localhost inside the container '
            'points at the Docker host only on Linux. '
            'On macOS/Windows use host.docker.internal.'
        )

    def _log_discovered_topics(self):
        # Run once, then cancel.
        self._graph_timer.cancel()
        topics = self.get_topic_names_and_types()
        if not topics:
            self.get_logger().warn(
                'No topics discovered on the ROS graph. '
                'Is the Yahboom driver running? Does ROS_DOMAIN_ID match?'
            )
            return
        self.get_logger().info(f'Discovered {len(topics)} topic(s) on the ROS graph:')
        for name, types in topics:
            self.get_logger().info(f'  {name} [{", ".join(types)}]')
        wanted = {'/imu', '/battery', '/odom_raw'}
        missing = wanted - {name for name, _ in topics}
        if missing:
            self.get_logger().warn(f'Expected topic(s) not found: {sorted(missing)}')

    def _imu_callback(self, msg: Imu):
        self.get_logger().info('Received first IMU message', once=True)
        self._imu_count += 1
        if self._imu_count % 50 == 0:
            self.get_logger().info(f'IMU messages received: {self._imu_count}')
        with self._lock:
            self._imu_data = msg

    def _battery_callback(self, msg: UInt16):
        self.get_logger().info(f'Received first battery message: {msg.data}', once=True)
        self._battery_count += 1
        if self._battery_count % 20 == 0:
            self.get_logger().info(f'Battery messages received: {self._battery_count}')
        with self._lock:
            self._battery = msg.data

    def _odom_callback(self, msg: Odometry):
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        speed = math.sqrt(vx * vx + vy * vy)
        self.get_logger().info(
            f'Received first odom message: vx={vx:.3f} vy={vy:.3f} speed={speed:.3f}',
            once=True,
        )
        self._odom_count += 1
        if self._odom_count % 50 == 0:
            self.get_logger().info(f'Odom messages received: {self._odom_count}')
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

    def _post(self, path: str, payload: dict):
        url = f'{self.server_url}{path}'
        try:
            r = requests.post(url, json=payload, timeout=5)
        except Exception as e:
            self.get_logger().warn(f'POST {path} connection failed ({url}): {e}')
            return
        if r.status_code >= 400:
            self.get_logger().warn(
                f'POST {path} -> {r.status_code}: {r.text[:200]}'
            )
        else:
            self.get_logger().info(
                f'POST {path} -> {r.status_code}',
                throttle_duration_sec=10.0,
            )

    def _do_post(self, imu, battery, speed):
        if battery is not None:
            voltage, percentage = battery_percentage_from_deci_volts(battery)
            self.get_logger().info(
                f'Battery raw={battery} voltage={voltage:.2f}V percentage={percentage:.1f}%'
            )
            self._post('/api/batterie', {'percentage': float(percentage)})

        if imu is not None:
            self._post(
                '/api/imu',
                {
                    'accel_x': imu.linear_acceleration.x,
                    'accel_y': imu.linear_acceleration.y,
                    'accel_z': imu.linear_acceleration.z,
                    'gyro_x': imu.angular_velocity.x,
                    'gyro_y': imu.angular_velocity.y,
                    'gyro_z': imu.angular_velocity.z,
                },
            )

        if speed is not None:
            self._post('/api/vitesse', {'speed': float(speed)})


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
