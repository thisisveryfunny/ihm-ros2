"""
Camera control node: drives a pan/tilt servo hat from WebSocket commands.

WebSocket messages received:
  { "type": "camera", "direction": "up"|"down"|"left"|"right"|"stop" }

Behavior:
  Continuous while held. A 'left'/'right' command starts panning at `pan_speed`
  degrees per tick; 'up'/'down' starts tilting at `tilt_speed` deg/tick; 'stop'
  holds the current angle. Angles are clamped to [min, max] bounds.

ROS2 parameters:
  server_url      (string, default "localhost:5173")
  pan_pin         (int, default 17)        GPIO pin for pan servo
  tilt_pin        (int, default 18)        GPIO pin for tilt servo
  pan_min         (double, default -90.0)  Min pan angle in degrees
  pan_max         (double, default 90.0)   Max pan angle in degrees
  tilt_min        (double, default -45.0)  Min tilt angle in degrees
  tilt_max        (double, default 45.0)   Max tilt angle in degrees
  pan_speed       (double, default 2.0)    Degrees per tick
  tilt_speed      (double, default 2.0)    Degrees per tick
  tick_hz         (double, default 30.0)   Control loop rate

Servo driver:
  Defaults to gpiozero.AngularServo (direct GPIO PWM). Swap the ServoDriver
  class for a different backend (e.g. adafruit-servokit for PCA9685 hats)
  without touching the message handling.
"""

import json
import threading
import time

import rclpy
from rclpy.node import Node

import websocket


class ServoDriver:
    """Thin wrapper around gpiozero.AngularServo so the backend is swappable."""

    def __init__(self, pin: int, min_angle: float, max_angle: float):
        from gpiozero import AngularServo

        self._servo = AngularServo(
            pin,
            min_angle=min_angle,
            max_angle=max_angle,
            min_pulse_width=0.0005,
            max_pulse_width=0.0025,
        )
        self._servo.angle = 0.0

    @property
    def angle(self) -> float:
        return float(self._servo.angle or 0.0)

    @angle.setter
    def angle(self, value: float) -> None:
        self._servo.angle = value

    def close(self) -> None:
        self._servo.close()


class CameraControlNode(Node):
    def __init__(self):
        super().__init__('camera_control_node')

        self.declare_parameter('server_url', 'localhost:5173')
        self.declare_parameter('pan_pin', 17)
        self.declare_parameter('tilt_pin', 18)
        self.declare_parameter('pan_min', -90.0)
        self.declare_parameter('pan_max', 90.0)
        self.declare_parameter('tilt_min', -45.0)
        self.declare_parameter('tilt_max', 45.0)
        self.declare_parameter('pan_speed', 2.0)
        self.declare_parameter('tilt_speed', 2.0)
        self.declare_parameter('tick_hz', 30.0)

        p = self.get_parameter
        self.server_url = p('server_url').get_parameter_value().string_value
        pan_pin = p('pan_pin').get_parameter_value().integer_value
        tilt_pin = p('tilt_pin').get_parameter_value().integer_value
        self.pan_min = p('pan_min').get_parameter_value().double_value
        self.pan_max = p('pan_max').get_parameter_value().double_value
        self.tilt_min = p('tilt_min').get_parameter_value().double_value
        self.tilt_max = p('tilt_max').get_parameter_value().double_value
        self.pan_speed = p('pan_speed').get_parameter_value().double_value
        self.tilt_speed = p('tilt_speed').get_parameter_value().double_value
        tick_hz = p('tick_hz').get_parameter_value().double_value

        self._tick_dt = 1.0 / max(tick_hz, 1.0)

        # Servo drivers (fall back to logging-only if hardware/library missing)
        try:
            self._pan = ServoDriver(pan_pin, self.pan_min, self.pan_max)
            self._tilt = ServoDriver(tilt_pin, self.tilt_min, self.tilt_max)
            self._hardware = True
            self.get_logger().info(
                f'Servos initialised: pan GPIO{pan_pin}, tilt GPIO{tilt_pin}'
            )
        except Exception as e:
            self._hardware = False
            self._pan_angle = 0.0
            self._tilt_angle = 0.0
            self.get_logger().warn(
                f'Servo hardware unavailable ({e}); running in log-only mode'
            )

        # Active motion state (None when stopped)
        self._pan_dir = 0   # -1 left, +1 right, 0 stop
        self._tilt_dir = 0  # -1 down, +1 up, 0 stop
        self._state_lock = threading.Lock()

        # Tick thread drives continuous motion while a key is held
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()

        # WebSocket listener
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()

        self.get_logger().info(
            f'Camera control node started, connecting to ws://{self.server_url}/ws/camera?role=robot'
        )

    # ── Motion tick ────────────────────────────────────────────────────────

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _current_angles(self) -> tuple[float, float]:
        if self._hardware:
            return self._pan.angle, self._tilt.angle
        return self._pan_angle, self._tilt_angle

    def _apply_angles(self, pan: float, tilt: float) -> None:
        if self._hardware:
            self._pan.angle = pan
            self._tilt.angle = tilt
        else:
            self._pan_angle = pan
            self._tilt_angle = tilt

    def _tick_loop(self) -> None:
        while rclpy.ok():
            with self._state_lock:
                pan_dir = self._pan_dir
                tilt_dir = self._tilt_dir

            if pan_dir != 0 or tilt_dir != 0:
                pan, tilt = self._current_angles()
                if pan_dir != 0:
                    pan = self._clamp(
                        pan + pan_dir * self.pan_speed, self.pan_min, self.pan_max
                    )
                if tilt_dir != 0:
                    tilt = self._clamp(
                        tilt + tilt_dir * self.tilt_speed, self.tilt_min, self.tilt_max
                    )
                self._apply_angles(pan, tilt)
                if not self._hardware:
                    self.get_logger().info(f'Camera → pan={pan:.1f}° tilt={tilt:.1f}°')

            time.sleep(self._tick_dt)

    # ── WebSocket ──────────────────────────────────────────────────────────

    def _ws_loop(self):
        while rclpy.ok():
            try:
                ws_url = f'ws://{self.server_url}/ws/camera?role=robot'
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
        with self._state_lock:
            self._pan_dir = 0
            self._tilt_dir = 0

    def _on_error(self, ws, error):
        self.get_logger().warn(f'WebSocket error: {error}')

    def _on_message(self, ws, message):
        try:
            msg = json.loads(message)
        except json.JSONDecodeError:
            return

        if msg.get('type') != 'camera':
            return

        direction = msg.get('direction')
        with self._state_lock:
            if direction == 'left':
                self._pan_dir = -1
            elif direction == 'right':
                self._pan_dir = 1
            elif direction == 'up':
                self._tilt_dir = 1
            elif direction == 'down':
                self._tilt_dir = -1
            elif direction == 'stop':
                self._pan_dir = 0
                self._tilt_dir = 0

    def destroy_node(self):
        try:
            if self._hardware:
                self._pan.close()
                self._tilt.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
