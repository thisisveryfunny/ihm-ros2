"""
Telemetry node: subscribes to ROS2 sensor topics and POSTs data to the web server API every 2 seconds.

Topics:
  /imu/data          (sensor_msgs/msg/Imu)            → POST /api/imu
  /imu/mag           (sensor_msgs/msg/MagneticField)   → merged into POST /api/imu
  /battery           (std_msgs/msg/Float32)            → POST /api/batterie
  /odom/unfiltered   (nav_msgs/msg/Odometry)           → POST /api/vitesse

ROS2 parameters:
  server_url  (string, default "http://localhost:5173")
"""

import math
import threading

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField
from std_msgs.msg import Float32
from nav_msgs.msg import Odometry

import requests


class TelemetryNode(Node):
    def __init__(self):
        super().__init__('telemetry_node')

        self.declare_parameter('server_url', 'http://localhost:5173')
        self.server_url = self.get_parameter('server_url').get_parameter_value().string_value

        # Latest cached readings
        self._imu_data = None
        self._mag_data = None
        self._battery = None
        self._speed = None
        self._lock = threading.Lock()

        # Subscribers
        self.create_subscription(Imu, '/imu/data', self._imu_callback, 10)
        self.create_subscription(MagneticField, '/imu/mag', self._mag_callback, 10)
        self.create_subscription(Float32, '/battery', self._battery_callback, 10)
        self.create_subscription(Odometry, '/odom/unfiltered', self._odom_callback, 10)

        # Timer: POST every 2 seconds
        self.create_timer(2.0, self._send_telemetry)

        self.get_logger().info(f'Telemetry node started, posting to {self.server_url}')

    def _imu_callback(self, msg: Imu):
        with self._lock:
            self._imu_data = msg

    def _mag_callback(self, msg: MagneticField):
        with self._lock:
            self._mag_data = msg

    def _battery_callback(self, msg: Float32):
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
            mag = self._mag_data
            battery = self._battery
            speed = self._speed

        # Run HTTP requests in a thread so we don't block the ROS2 executor
        thread = threading.Thread(
            target=self._do_post,
            args=(imu, mag, battery, speed),
            daemon=True,
        )
        thread.start()

    def _do_post(self, imu, mag, battery, speed):
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

        # POST IMU (accel + gyro from /imu/data, magnetometer from /imu/mag)
        if imu is not None:
            payload = {
                'accel_x': imu.linear_acceleration.x,
                'accel_y': imu.linear_acceleration.y,
                'accel_z': imu.linear_acceleration.z,
                'gyro_x': imu.angular_velocity.x,
                'gyro_y': imu.angular_velocity.y,
                'gyro_z': imu.angular_velocity.z,
                'mag_x': mag.magnetic_field.x if mag else 0.0,
                'mag_y': mag.magnetic_field.y if mag else 0.0,
                'mag_z': mag.magnetic_field.z if mag else 0.0,
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
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
