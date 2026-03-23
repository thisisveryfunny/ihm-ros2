"""
Sign detection node: uses the camera and ORB feature matching to detect printed signs
(stop, arrows) and control the robot accordingly.

Reference images loaded from assets/ folder:
  stop-sign.jpg  → stop (speed = 0)
  up-arrow.jpg   → forward
  down-arrow.jpg → backward
  left-arrow.jpg → turn left
  right-arrow.jpg → turn right

When no sign is detected, no command is published — dashboard control passes through.
Dashboard commands override sign detection (higher publish frequency).

Published topic:
  /cmd_vel  (geometry_msgs/msg/Twist)

WebSocket message sent:
  { "type": "sign-detected", "sign": "stop"|"up"|"down"|"left"|"right"|null }

ROS2 parameters:
  server_url       (string, default "localhost:5173")
  assets_path      (string, default "../assets")
  linear_speed     (double, default 0.2 m/s)
  angular_speed    (double, default 1.0 rad/s)
  match_threshold  (int, default 15) — minimum good matches to trigger detection
  process_interval (double, default 0.1) — seconds between frame processing
  camera_index     (int, default 0)
"""

import json
import os
import threading
import time

import cv2

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

import websocket


# Sign name → reference image filename
SIGN_FILES = {
    'stop': 'stop-sign.jpg',
    'up': 'up-arrow.jpg',
    'down': 'down-arrow.jpg',
    'left': 'left-arrow.jpg',
    'right': 'right-arrow.jpg',
}


class SignDetectionNode(Node):
    def __init__(self):
        super().__init__('sign_detection_node')

        # Parameters
        self.declare_parameter('server_url', 'localhost:5173')
        self.declare_parameter('assets_path', '../assets')
        self.declare_parameter('linear_speed', 0.2)
        self.declare_parameter('angular_speed', 1.0)
        self.declare_parameter('match_threshold', 15)
        self.declare_parameter('process_interval', 0.1)
        self.declare_parameter('camera_index', 0)

        self.server_url = self.get_parameter('server_url').get_parameter_value().string_value
        assets_path = self.get_parameter('assets_path').get_parameter_value().string_value
        self.linear_speed = self.get_parameter('linear_speed').get_parameter_value().double_value
        self.angular_speed = self.get_parameter('angular_speed').get_parameter_value().double_value
        self.match_threshold = self.get_parameter('match_threshold').get_parameter_value().integer_value
        process_interval = self.get_parameter('process_interval').get_parameter_value().double_value
        camera_index = self.get_parameter('camera_index').get_parameter_value().integer_value

        # Publisher
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # ORB detector and matcher
        self._orb = cv2.ORB_create(nfeatures=500)
        self._bf = cv2.BFMatcher(cv2.NORM_HAMMING)

        # Load reference images and compute descriptors
        self._references = {}
        for sign_name, filename in SIGN_FILES.items():
            filepath = os.path.join(assets_path, filename)
            img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                self.get_logger().warn(f'Could not load reference image: {filepath}')
                continue
            kp, des = self._orb.detectAndCompute(img, None)
            if des is not None:
                self._references[sign_name] = des
                self.get_logger().info(f'Loaded reference: {sign_name} ({len(kp)} keypoints)')
            else:
                self.get_logger().warn(f'No features found in: {filepath}')

        if not self._references:
            self.get_logger().error('No reference images loaded! Check assets_path parameter.')

        # Camera
        self._cap = cv2.VideoCapture(camera_index)
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self._cap.isOpened():
            self.get_logger().error(f'Cannot open camera at index {camera_index}')

        # State
        self._last_sign = None
        self._ws = None
        self._ws_lock = threading.Lock()

        # WebSocket thread
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()

        # Processing timer
        self.create_timer(process_interval, self._process_frame)

        self.get_logger().info(
            f'Sign detection node started (threshold: {self.match_threshold} matches, '
            f'interval: {process_interval}s)'
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
            time.sleep(2)

    def _on_ws_open(self, ws):
        with self._ws_lock:
            self._ws = ws
        self.get_logger().info('WebSocket connected')

    def _on_ws_close(self, ws, close_status_code, close_msg):
        with self._ws_lock:
            self._ws = None

    def _on_ws_error(self, ws, error):
        self.get_logger().warn(f'WebSocket error: {error}')

    def _send_ws(self, msg: dict):
        with self._ws_lock:
            ws = self._ws
        if ws:
            try:
                ws.send(json.dumps(msg))
            except Exception:
                pass

    def _match_sign(self, frame_gray):
        """Match frame against all references. Returns (sign_name, match_count) or (None, 0)."""
        kp, des = self._orb.detectAndCompute(frame_gray, None)
        if des is None:
            return None, 0

        best_sign = None
        best_count = 0

        for sign_name, ref_des in self._references.items():
            try:
                matches = self._bf.knnMatch(ref_des, des, k=2)
            except cv2.error:
                continue

            # Lowe's ratio test
            good = []
            for match in matches:
                if len(match) == 2:
                    m, n = match
                    if m.distance < 0.75 * n.distance:
                        good.append(m)

            if len(good) > best_count:
                best_count = len(good)
                best_sign = sign_name

        if best_count >= self.match_threshold:
            return best_sign, best_count
        return None, best_count

    def _process_frame(self):
        """Capture a frame, detect signs, and act."""
        if not self._cap.isOpened() or not self._references:
            return

        ret, frame = self._cap.read()
        if not ret:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sign, count = self._match_sign(gray)

        # Only act on state changes to avoid spamming
        if sign != self._last_sign:
            self._last_sign = sign
            self._send_ws({'type': 'sign-detected', 'sign': sign})

            if sign:
                self.get_logger().info(f'Detected: {sign} ({count} matches)')

        # Publish cmd_vel only when a sign is detected
        if sign is not None:
            twist = Twist()
            if sign == 'stop':
                pass  # all zeros
            elif sign == 'up':
                twist.linear.x = self.linear_speed
            elif sign == 'down':
                twist.linear.x = -self.linear_speed
            elif sign == 'left':
                twist.angular.z = self.angular_speed
            elif sign == 'right':
                twist.angular.z = -self.angular_speed
            self.cmd_vel_pub.publish(twist)

    def destroy_node(self):
        if self._cap.isOpened():
            self._cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SignDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
