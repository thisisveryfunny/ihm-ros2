#!/usr/bin/env python3

import subprocess
import time

import cv2
import mediapipe as mp
import rclpy
from rclpy.node import Node


class AIDetectorNode(Node):
    def __init__(self) -> None:
        super().__init__("ai_detector_node")

        self.declare_parameter("camera_index", 0)
        self.declare_parameter("frame_width", 640)
        self.declare_parameter("frame_height", 480)
        self.declare_parameter("camera_fps", 30)
        self.declare_parameter("detection_width", 320)
        self.declare_parameter("face_every_n_frames", 1)
        self.declare_parameter("hand_every_n_frames", 1)
        self.declare_parameter("feet_every_n_frames", 2)
        self.declare_parameter("min_detection_confidence", 0.55)
        self.declare_parameter("min_tracking_confidence", 0.5)
        self.declare_parameter("foot_visibility_threshold", 0.55)
        self.declare_parameter("show_window", False)
        self.declare_parameter("rtsp_url", "rtsp://127.0.0.1:8554/robot")
        self.declare_parameter("ffmpeg_binary", "ffmpeg")

        self.camera_index = self.get_parameter("camera_index").value
        self.frame_width = int(self.get_parameter("frame_width").value)
        self.frame_height = int(self.get_parameter("frame_height").value)
        self.camera_fps = max(1, int(self.get_parameter("camera_fps").value))
        self.detection_width = int(self.get_parameter("detection_width").value)
        self.face_every_n_frames = max(1, int(self.get_parameter("face_every_n_frames").value))
        self.hand_every_n_frames = max(1, int(self.get_parameter("hand_every_n_frames").value))
        self.feet_every_n_frames = max(1, int(self.get_parameter("feet_every_n_frames").value))
        self.show_window = bool(self.get_parameter("show_window").value)
        self.rtsp_url = str(self.get_parameter("rtsp_url").value)
        self.ffmpeg_binary = str(self.get_parameter("ffmpeg_binary").value)
        self.foot_visibility_threshold = float(self.get_parameter("foot_visibility_threshold").value)

        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.camera_fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera at index {self.camera_index}")

        self.face_detector = mp.solutions.face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=float(self.get_parameter("min_detection_confidence").value),
        )
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=float(self.get_parameter("min_detection_confidence").value),
            min_tracking_confidence=float(self.get_parameter("min_tracking_confidence").value),
        )
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=float(self.get_parameter("min_detection_confidence").value),
            min_tracking_confidence=float(self.get_parameter("min_tracking_confidence").value),
        )
        self.hand_connections = mp.solutions.hands.HAND_CONNECTIONS
        self.pose_landmark = mp.solutions.pose.PoseLandmark

        self.ffmpeg = None
        self.frame_count = 0
        self.faces = []
        self.hands_seen = []
        self.feet = []
        self.fps = 0.0
        self.fps_frames = 0
        self.last_fps_time = time.monotonic()

        self.create_timer(1.0 / self.camera_fps, self.process_frame)
        self.get_logger().info(f"Camera: {self.frame_width}x{self.frame_height} @ {self.camera_fps} FPS")
        self.get_logger().info(f"Streaming annotated frames to {self.rtsp_url}")

    def start_ffmpeg(self, width: int, height: int) -> None:
        command = [
            self.ffmpeg_binary,
            "-loglevel",
            "warning",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(self.camera_fps),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-bf",
            "0",
            "-threads",
            "1",
            "-f",
            "rtsp",
            "-rtsp_transport",
            "tcp",
            self.rtsp_url,
        ]
        self.ffmpeg = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def detection_frame(self, frame):
        height, width = frame.shape[:2]
        scale = 1.0
        detection_frame = frame

        if 0 < self.detection_width < width:
            scale = self.detection_width / width
            detection_frame = cv2.resize(frame, (self.detection_width, int(height * scale)))

        rgb = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        return rgb, detection_frame.shape[:2], scale

    def detect_faces(self, frame, rgb, detect_shape, scale):
        height, width = frame.shape[:2]
        result = self.face_detector.process(rgb)
        if not result.detections:
            return []

        detect_height, detect_width = detect_shape
        faces = []
        for detection in result.detections:
            box = detection.location_data.relative_bounding_box
            x1 = int(box.xmin * detect_width / scale)
            y1 = int(box.ymin * detect_height / scale)
            x2 = int((box.xmin + box.width) * detect_width / scale)
            y2 = int((box.ymin + box.height) * detect_height / scale)
            score = float(detection.score[0]) if detection.score else 0.0
            faces.append((max(0, x1), max(0, y1), min(width - 1, x2), min(height - 1, y2), score))
        return faces

    def detect_hands(self, frame, rgb, detect_shape, scale):
        height, width = frame.shape[:2]
        detect_height, detect_width = detect_shape
        result = self.hands.process(rgb)
        hands = []
        if not result.multi_hand_landmarks:
            return hands

        for hand_landmarks in result.multi_hand_landmarks:
            points = []
            for landmark in hand_landmarks.landmark:
                x = int(landmark.x * detect_width / scale)
                y = int(landmark.y * detect_height / scale)
                points.append((max(0, min(width - 1, x)), max(0, min(height - 1, y))))
            hands.append(points)
        return hands

    def detect_feet(self, frame, rgb, detect_shape, scale):
        height, width = frame.shape[:2]
        detect_height, detect_width = detect_shape
        result = self.pose.process(rgb)
        if not result.pose_landmarks:
            return []

        landmarks = result.pose_landmarks.landmark
        foot_landmarks = (
            self.pose_landmark.LEFT_ANKLE,
            self.pose_landmark.RIGHT_ANKLE,
            self.pose_landmark.LEFT_HEEL,
            self.pose_landmark.RIGHT_HEEL,
            self.pose_landmark.LEFT_FOOT_INDEX,
            self.pose_landmark.RIGHT_FOOT_INDEX,
        )
        feet = []
        for point in foot_landmarks:
            landmark = landmarks[point.value]
            if landmark.visibility < self.foot_visibility_threshold:
                continue
            x = int(landmark.x * detect_width / scale)
            y = int(landmark.y * detect_height / scale)
            feet.append((max(0, min(width - 1, x)), max(0, min(height - 1, y))))
        return feet

    def annotate(self, frame, faces, hands_seen, feet) -> None:
        for x1, y1, x2, y2, score in faces:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 80), 2)
            cv2.putText(
                frame,
                f"Face {score:.2f}",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 220, 80),
                2,
                cv2.LINE_AA,
            )

        for points in hands_seen:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            cv2.rectangle(frame, (min(xs), min(ys)), (max(xs), max(ys)), (255, 170, 0), 2)
            for start, end in self.hand_connections:
                cv2.line(frame, points[start], points[end], (255, 170, 0), 1, cv2.LINE_AA)
            for point in points:
                cv2.circle(frame, point, 2, (255, 220, 80), -1)

        for point in feet:
            cv2.circle(frame, point, 7, (40, 120, 255), -1)
            cv2.circle(frame, point, 11, (40, 120, 255), 2)

        status = f"Faces: {len(faces)}  Hands: {len(hands_seen)}  Feet pts: {len(feet)}  FPS: {self.fps:.1f}"
        cv2.rectangle(frame, (10, 10), (430, 42), (20, 20, 20), -1)
        cv2.putText(frame, status, (18, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (245, 245, 245), 1, cv2.LINE_AA)

    def stream_frame(self, frame) -> None:
        if self.ffmpeg is None or self.ffmpeg.poll() is not None:
            self.start_ffmpeg(frame.shape[1], frame.shape[0])
        if self.ffmpeg.stdin is None:
            return
        try:
            self.ffmpeg.stdin.write(frame.tobytes())
        except (BrokenPipeError, OSError):
            self.get_logger().warn("ffmpeg write failed; restarting stream")
            self.stop_ffmpeg()

    def update_fps(self) -> None:
        self.fps_frames += 1
        now = time.monotonic()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps = self.fps_frames / elapsed
            self.fps_frames = 0
            self.last_fps_time = now

    def process_frame(self) -> None:
        ok, frame = self.cap.read()
        if not ok:
            self.get_logger().warn("Camera frame read failed")
            return

        rgb, detect_shape, scale = self.detection_frame(frame)
        if self.frame_count % self.face_every_n_frames == 0:
            self.faces = self.detect_faces(frame, rgb, detect_shape, scale)
        if self.frame_count % self.hand_every_n_frames == 0:
            self.hands_seen = self.detect_hands(frame, rgb, detect_shape, scale)
        if self.frame_count % self.feet_every_n_frames == 0:
            self.feet = self.detect_feet(frame, rgb, detect_shape, scale)
        self.frame_count += 1

        self.update_fps()
        self.annotate(frame, self.faces, self.hands_seen, self.feet)
        self.stream_frame(frame)

        if self.show_window:
            cv2.imshow("ROS2 AI Detector", frame)
            cv2.waitKey(1)

    def stop_ffmpeg(self) -> None:
        if self.ffmpeg is None:
            return
        if self.ffmpeg.stdin:
            self.ffmpeg.stdin.close()
        self.ffmpeg.terminate()
        self.ffmpeg = None

    def destroy_node(self) -> None:
        self.stop_ffmpeg()
        self.cap.release()
        self.face_detector.close()
        self.hands.close()
        self.pose.close()
        if self.show_window:
            cv2.destroyAllWindows()
        super().destroy_node()


def main() -> None:
    rclpy.init()
    node = None
    try:
        node = AIDetectorNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f"Failed to start ai detector node: {error}")
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
