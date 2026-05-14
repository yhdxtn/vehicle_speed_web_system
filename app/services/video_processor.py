import cv2
import numpy as np
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.config import CONFIG, get_default_fps, get_output_size
from app.services.detector import YOLOVehicleDetector
from app.services.tracker import IOUTracker
from app.services.speed_estimator import SpeedEstimator
from app.services.draw_utils import draw_speed_lines, draw_tracks


class VideoProcessor:
    def __init__(self):
        speed_cfg = CONFIG.get("speed", {})

        line1 = [
            speed_cfg.get("line1", {}).get("start", [80, 250]),
            speed_cfg.get("line1", {}).get("end", [880, 250])
        ]

        line2 = [
            speed_cfg.get("line2", {}).get("start", [80, 340]),
            speed_cfg.get("line2", {}).get("end", [880, 340])
        ]

        distance_m = float(speed_cfg.get("distance_m", 10))
        fps = float(get_default_fps())

        self.output_width, self.output_height = get_output_size()

        self.detector = YOLOVehicleDetector()
        self.tracker = IOUTracker()
        self.speed_estimator = SpeedEstimator(
            line1=line1,
            line2=line2,
            distance_m=distance_m,
            fps=fps
        )

        self.video_path: Optional[str] = None
        self.lock = threading.Lock()

    def set_video_path(self, video_path: str):
        with self.lock:
            self.video_path = video_path
            self.reset_runtime_state()

    def reset_runtime_state(self):
        self.tracker.reset()
        self.speed_estimator.reset()

    def set_line_config(
        self,
        line1: List[List[float]],
        line2: List[List[float]],
        distance_m: float,
        fps: float
    ):
        with self.lock:
            self.speed_estimator.set_config(
                line1=line1,
                line2=line2,
                distance_m=distance_m,
                fps=fps
            )
            self.tracker.reset()

    def get_results(self) -> List[Dict[str, Any]]:
        return self.speed_estimator.get_results()

    def _make_placeholder_frame(self, message: str):
        frame = np.zeros(
            (self.output_height, self.output_width, 3),
            dtype=np.uint8
        )

        cv2.putText(
            frame,
            message,
            (40, self.output_height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        return frame

    @staticmethod
    def _encode_frame(frame):
        success, buffer = cv2.imencode(".jpg", frame)

        if not success:
            return None

        return buffer.tobytes()

    def _yield_frame(self, frame):
        encoded = self._encode_frame(frame)

        if encoded is None:
            return None

        return (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + encoded + b"\r\n"
        )

    def stream(self):
        with self.lock:
            video_path = self.video_path

        if not video_path:
            frame = self._make_placeholder_frame("Please upload a video first.")
            yield self._yield_frame(frame)
            return

        if not Path(video_path).exists():
            frame = self._make_placeholder_frame("Video file not found.")
            yield self._yield_frame(frame)
            return

        self.reset_runtime_state()

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            frame = self._make_placeholder_frame("Failed to open video.")
            yield self._yield_frame(frame)
            return

        frame_id = 0

        try:
            while True:
                ret, frame = cap.read()

                if not ret:
                    break

                frame_id += 1

                frame = cv2.resize(
                    frame,
                    (self.output_width, self.output_height)
                )

                detections = self.detector.detect(frame)
                tracks = self.tracker.update(detections)

                for track in tracks:
                    self.speed_estimator.update(
                        track_id=track["track_id"],
                        trajectory=track["trajectory"],
                        frame_id=frame_id
                    )

                draw_speed_lines(
                    frame,
                    self.speed_estimator.line1,
                    self.speed_estimator.line2,
                    self.speed_estimator.distance_m
                )

                draw_tracks(
                    frame,
                    tracks,
                    self.speed_estimator.get_speed
                )

                cv2.putText(
                    frame,
                    f"Frame: {frame_id}  FPS for speed: {self.speed_estimator.fps:.1f}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2
                )

                data = self._yield_frame(frame)

                if data:
                    yield data

        except Exception as e:
            error_frame = self._make_placeholder_frame(f"Error: {str(e)}")
            yield self._yield_frame(error_frame)

        finally:
            cap.release()


processor = VideoProcessor()