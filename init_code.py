from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

files = {}

files["requirements.txt"] = r"""
fastapi
uvicorn[standard]
jinja2
python-multipart
opencv-python
ultralytics
numpy
pyyaml
pydantic
"""

files["run.py"] = r"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
"""

files["configs/default.yaml"] = r"""
model:
  weight_path: "weights/yolov8m.pt"
  conf_threshold: 0.35
  iou_threshold: 0.45

video:
  default_fps: 30
  output_width: 1280
  output_height: 720

speed:
  distance_m: 10
  line1:
    start: [100, 300]
    end: [900, 300]
  line2:
    start: [100, 420]
    end: [900, 420]

tracker:
  max_lost_frames: 30
  iou_threshold: 0.3

web:
  host: "0.0.0.0"
  port: 8000
"""

files["app/config.py"] = r"""
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = BASE_DIR / "configs" / "default.yaml"

DEFAULT_CONFIG = {
    "model": {
        "weight_path": "weights/yolov8m.pt",
        "conf_threshold": 0.35,
        "iou_threshold": 0.45,
    },
    "video": {
        "default_fps": 30,
        "output_width": 1280,
        "output_height": 720,
    },
    "speed": {
        "distance_m": 10,
        "line1": {
            "start": [100, 300],
            "end": [900, 300],
        },
        "line2": {
            "start": [100, 420],
            "end": [900, 420],
        },
    },
    "tracker": {
        "max_lost_frames": 30,
        "iou_threshold": 0.3,
    },
}


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return DEFAULT_CONFIG


config = load_config()
"""

files["app/schemas.py"] = r"""
from typing import List
from pydantic import BaseModel


class LineConfig(BaseModel):
    line1: List[List[int]]
    line2: List[List[int]]
    distance_m: float
    fps: float = 30.0
"""

files["app/main.py"] = r"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import video_api, line_api, result_api
from app.config import BASE_DIR

app = FastAPI(title="Vehicle Speed Web System")

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "app" / "static")),
    name="static"
)

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

app.include_router(video_api.router, prefix="/api/video", tags=["video"])
app.include_router(line_api.router, prefix="/api/line", tags=["line"])
app.include_router(result_api.router, prefix="/api/results", tags=["results"])


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
"""

files["app/api/video_api.py"] = r"""
from pathlib import Path

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import BASE_DIR
from app.services.video_processor import processor

router = APIRouter()


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    upload_dir = BASE_DIR / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    save_path = upload_dir / file.filename

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    processor.set_video_path(str(save_path))

    return {
        "code": 200,
        "message": "视频上传成功",
        "video_path": str(save_path)
    }


@router.get("/stream")
def video_stream():
    if not processor.video_path:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "请先上传视频"}
        )

    return StreamingResponse(
        processor.generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.post("/reset")
def reset_video():
    processor.reset()
    return {"code": 200, "message": "系统已重置"}
"""

files["app/api/line_api.py"] = r"""
from fastapi import APIRouter

from app.schemas import LineConfig
from app.services.video_processor import processor

router = APIRouter()


@router.post("/config")
def set_line_config(data: LineConfig):
    processor.set_line_config(
        line1=data.line1,
        line2=data.line2,
        distance_m=data.distance_m,
        fps=data.fps
    )

    return {
        "code": 200,
        "message": "测速线配置成功",
        "data": data
    }


@router.get("/config")
def get_line_config():
    return processor.get_line_config()
"""

files["app/api/result_api.py"] = r"""
from fastapi import APIRouter

from app.services.video_processor import processor

router = APIRouter()


@router.get("")
def get_results():
    return {
        "code": 200,
        "data": processor.get_results()
    }
"""

files["app/models/vehicle.py"] = r"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class VehicleTrack:
    track_id: int
    bbox: List[int]
    center: Tuple[int, int]
    lost_frames: int = 0
    trajectory: List[Tuple[int, int]] = field(default_factory=list)
    speed_kmh: Optional[float] = None
"""

files["app/services/detector.py"] = r"""
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from app.config import BASE_DIR, config


class VehicleDetector:
    def __init__(self):
        model_cfg = config.get("model", {})
        weight_path = BASE_DIR / model_cfg.get("weight_path", "weights/yolov8m.pt")

        if not weight_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {weight_path}")

        self.model = YOLO(str(weight_path))
        self.conf_threshold = float(model_cfg.get("conf_threshold", 0.35))
        self.iou_threshold = float(model_cfg.get("iou_threshold", 0.45))

        self.vehicle_names = {
            "car",
            "bus",
            "truck",
            "motorcycle",
            "vehicle"
        }

    def detect(self, frame):
        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False
        )

        detections = []

        if not results:
            return detections

        result = results[0]

        if result.boxes is None:
            return detections

        names = result.names

        for box in result.boxes:
            xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            cls_name = str(names.get(cls_id, cls_id))

            # 如果是 COCO 车辆类别，则保留
            # 如果你的模型是自训练模型，类别名不是 car/bus/truck，也可以暂时全部保留
            if cls_name in self.vehicle_names or len(names) <= 2:
                detections.append({
                    "bbox": xyxy,
                    "confidence": conf,
                    "class_id": cls_id,
                    "class_name": cls_name
                })

        return detections
"""

files["app/services/tracker.py"] = r"""
from typing import List, Dict
import numpy as np


def calc_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)

    union_area = area_a + area_b - inter_area

    if union_area <= 0:
        return 0.0

    return inter_area / union_area


def get_center(bbox):
    x1, y1, x2, y2 = bbox
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


class IOUTracker:
    def __init__(self, iou_threshold=0.3, max_lost_frames=30):
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.next_track_id = 1
        self.tracks: Dict[int, dict] = {}

    def reset(self):
        self.next_track_id = 1
        self.tracks.clear()

    def update(self, detections: List[dict]):
        matched_track_ids = set()
        matched_det_ids = set()

        track_items = list(self.tracks.items())

        for det_idx, det in enumerate(detections):
            best_iou = 0
            best_track_id = None

            for track_id, track in track_items:
                if track_id in matched_track_ids:
                    continue

                iou = calc_iou(track["bbox"], det["bbox"])

                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id is not None and best_iou >= self.iou_threshold:
                bbox = det["bbox"]
                center = get_center(bbox)

                track = self.tracks[best_track_id]
                track["bbox"] = bbox
                track["center"] = center
                track["lost_frames"] = 0
                track["confidence"] = det["confidence"]
                track["class_name"] = det["class_name"]
                track["trajectory"].append(center)

                if len(track["trajectory"]) > 80:
                    track["trajectory"] = track["trajectory"][-80:]

                matched_track_ids.add(best_track_id)
                matched_det_ids.add(det_idx)

        for track_id, track in list(self.tracks.items()):
            if track_id not in matched_track_ids:
                track["lost_frames"] += 1

                if track["lost_frames"] > self.max_lost_frames:
                    del self.tracks[track_id]

        for det_idx, det in enumerate(detections):
            if det_idx in matched_det_ids:
                continue

            bbox = det["bbox"]
            center = get_center(bbox)

            self.tracks[self.next_track_id] = {
                "track_id": self.next_track_id,
                "bbox": bbox,
                "center": center,
                "lost_frames": 0,
                "confidence": det["confidence"],
                "class_name": det["class_name"],
                "trajectory": [center],
                "speed_kmh": None
            }

            self.next_track_id += 1

        active_tracks = [
            track for track in self.tracks.values()
            if track["lost_frames"] == 0
        ]

        return active_tracks
"""

files["app/services/speed_estimator.py"] = r"""
from typing import List, Dict, Tuple


def orientation(a, b, c):
    return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])


def on_segment(a, b, c):
    return (
        min(a[0], c[0]) <= b[0] <= max(a[0], c[0])
        and min(a[1], c[1]) <= b[1] <= max(a[1], c[1])
    )


def segments_intersect(p1, q1, p2, q2):
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if o1 * o2 < 0 and o3 * o4 < 0:
        return True

    if o1 == 0 and on_segment(p1, p2, q1):
        return True
    if o2 == 0 and on_segment(p1, q2, q1):
        return True
    if o3 == 0 and on_segment(p2, p1, q2):
        return True
    if o4 == 0 and on_segment(p2, q1, q2):
        return True

    return False


class SpeedEstimator:
    def __init__(self, line1, line2, distance_m=10.0, fps=30.0):
        self.line1 = line1
        self.line2 = line2
        self.distance_m = float(distance_m)
        self.fps = float(fps)

        self.vehicle_states: Dict[int, dict] = {}
        self.results: List[dict] = []

    def reset(self):
        self.vehicle_states.clear()
        self.results.clear()

    def set_config(self, line1, line2, distance_m, fps):
        self.line1 = line1
        self.line2 = line2
        self.distance_m = float(distance_m)
        self.fps = float(fps)
        self.reset()

    def update(self, tracks, frame_id):
        for track in tracks:
            track_id = track["track_id"]
            trajectory = track.get("trajectory", [])

            if len(trajectory) < 2:
                continue

            prev_center = trajectory[-2]
            curr_center = trajectory[-1]

            if track_id not in self.vehicle_states:
                self.vehicle_states[track_id] = {
                    "line1_frame": None,
                    "line2_frame": None,
                    "calculated": False,
                    "speed_kmh": None
                }

            state = self.vehicle_states[track_id]

            crossed_line1 = segments_intersect(
                prev_center,
                curr_center,
                tuple(self.line1[0]),
                tuple(self.line1[1])
            )

            crossed_line2 = segments_intersect(
                prev_center,
                curr_center,
                tuple(self.line2[0]),
                tuple(self.line2[1])
            )

            if crossed_line1 and state["line1_frame"] is None:
                state["line1_frame"] = frame_id

            if crossed_line2 and state["line2_frame"] is None:
                state["line2_frame"] = frame_id

            if (
                state["line1_frame"] is not None
                and state["line2_frame"] is not None
                and not state["calculated"]
            ):
                frame_diff = abs(state["line2_frame"] - state["line1_frame"])

                if frame_diff > 0 and self.fps > 0:
                    time_seconds = frame_diff / self.fps
                    speed_mps = self.distance_m / time_seconds
                    speed_kmh = speed_mps * 3.6

                    state["speed_kmh"] = speed_kmh
                    state["calculated"] = True

                    track["speed_kmh"] = speed_kmh

                    result = {
                        "track_id": track_id,
                        "line1_frame": state["line1_frame"],
                        "line2_frame": state["line2_frame"],
                        "frame_diff": frame_diff,
                        "time_seconds": round(time_seconds, 3),
                        "distance_m": self.distance_m,
                        "speed_kmh": round(speed_kmh, 2)
                    }

                    self.results.append(result)

            if state["speed_kmh"] is not None:
                track["speed_kmh"] = state["speed_kmh"]

        return tracks

    def get_results(self):
        return self.results
"""

files["app/services/draw_utils.py"] = r"""
import cv2


def draw_speed_lines(frame, line1, line2, distance_m, fps):
    p1, p2 = tuple(line1[0]), tuple(line1[1])
    p3, p4 = tuple(line2[0]), tuple(line2[1])

    cv2.line(frame, p1, p2, (0, 255, 255), 3)
    cv2.line(frame, p3, p4, (255, 0, 255), 3)

    cv2.putText(
        frame,
        "Line 1",
        (p1[0], p1[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "Line 2",
        (p3[0], p3[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 255),
        2
    )

    cv2.putText(
        frame,
        f"Distance: {distance_m} m | FPS: {fps}",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2
    )


def draw_tracks(frame, tracks):
    for track in tracks:
        x1, y1, x2, y2 = track["bbox"]
        track_id = track["track_id"]
        speed_kmh = track.get("speed_kmh")

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        label = f"ID:{track_id}"

        if speed_kmh is not None:
            label += f" {speed_kmh:.1f} km/h"

        cv2.putText(
            frame,
            label,
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        trajectory = track.get("trajectory", [])

        for i in range(1, len(trajectory)):
            cv2.line(
                frame,
                trajectory[i - 1],
                trajectory[i],
                (255, 255, 0),
                2
            )

        if trajectory:
            cv2.circle(frame, trajectory[-1], 4, (0, 0, 255), -1)

    return frame
"""

files["app/services/video_processor.py"] = r"""
import cv2

from app.config import config
from app.services.detector import VehicleDetector
from app.services.tracker import IOUTracker
from app.services.speed_estimator import SpeedEstimator
from app.services.draw_utils import draw_tracks, draw_speed_lines


class VideoProcessor:
    def __init__(self):
        speed_cfg = config.get("speed", {})
        tracker_cfg = config.get("tracker", {})
        video_cfg = config.get("video", {})

        self.video_path = None

        self.line1 = [
            speed_cfg.get("line1", {}).get("start", [100, 300]),
            speed_cfg.get("line1", {}).get("end", [900, 300])
        ]

        self.line2 = [
            speed_cfg.get("line2", {}).get("start", [100, 420]),
            speed_cfg.get("line2", {}).get("end", [900, 420])
        ]

        self.distance_m = float(speed_cfg.get("distance_m", 10))
        self.fps = float(video_cfg.get("default_fps", 30))

        self.detector = VehicleDetector()

        self.tracker = IOUTracker(
            iou_threshold=float(tracker_cfg.get("iou_threshold", 0.3)),
            max_lost_frames=int(tracker_cfg.get("max_lost_frames", 30))
        )

        self.speed_estimator = SpeedEstimator(
            line1=self.line1,
            line2=self.line2,
            distance_m=self.distance_m,
            fps=self.fps
        )

    def set_video_path(self, video_path):
        self.video_path = video_path
        self.reset()

    def set_line_config(self, line1, line2, distance_m, fps):
        self.line1 = line1
        self.line2 = line2
        self.distance_m = float(distance_m)
        self.fps = float(fps)

        self.speed_estimator.set_config(
            line1=self.line1,
            line2=self.line2,
            distance_m=self.distance_m,
            fps=self.fps
        )

    def get_line_config(self):
        return {
            "line1": self.line1,
            "line2": self.line2,
            "distance_m": self.distance_m,
            "fps": self.fps
        }

    def reset(self):
        self.tracker.reset()
        self.speed_estimator.reset()

    def get_results(self):
        return self.speed_estimator.get_results()

    def generate_frames(self):
        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            return

        frame_id = 0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            frame_id += 1

            detections = self.detector.detect(frame)
            tracks = self.tracker.update(detections)
            tracks = self.speed_estimator.update(tracks, frame_id)

            draw_speed_lines(
                frame,
                self.line1,
                self.line2,
                self.distance_m,
                self.fps
            )

            frame = draw_tracks(frame, tracks)

            ok, buffer = cv2.imencode(".jpg", frame)

            if not ok:
                continue

            frame_bytes = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame_bytes +
                b"\r\n"
            )

        cap.release()


processor = VideoProcessor()
"""

files["app/templates/index.html"] = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>车辆速度跟踪与检测系统</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
<div class="page">
    <header class="header">
        <h1>车辆速度跟踪与检测系统</h1>
        <p>YOLOv8 车辆检测 + IOU 跟踪 + 双线测速</p>
    </header>

    <main class="main">
        <section class="video-panel">
            <div class="video-box">
                <img id="videoStream" alt="视频检测画面">
            </div>
        </section>

        <section class="control-panel">
            <h2>操作面板</h2>

            <div class="card">
                <h3>1. 上传视频</h3>
                <input type="file" id="videoFile" accept="video/*">
                <button onclick="uploadVideo()">上传视频</button>
                <p id="uploadStatus"></p>
            </div>

            <div class="card">
                <h3>2. 测速参数</h3>

                <label>视频 FPS：</label>
                <input type="number" id="fps" value="30" step="1">

                <label>两线实际距离/米：</label>
                <input type="number" id="distance" value="10" step="0.1">

                <h4>第一条测速线</h4>
                <div class="grid">
                    <input id="l1x1" type="number" value="100" placeholder="x1">
                    <input id="l1y1" type="number" value="300" placeholder="y1">
                    <input id="l1x2" type="number" value="900" placeholder="x2">
                    <input id="l1y2" type="number" value="300" placeholder="y2">
                </div>

                <h4>第二条测速线</h4>
                <div class="grid">
                    <input id="l2x1" type="number" value="100" placeholder="x1">
                    <input id="l2y1" type="number" value="420" placeholder="y1">
                    <input id="l2x2" type="number" value="900" placeholder="x2">
                    <input id="l2y2" type="number" value="420" placeholder="y2">
                </div>

                <button onclick="saveLineConfig()">保存测速线配置</button>
            </div>

            <div class="card">
                <h3>3. 开始检测</h3>
                <button class="start-btn" onclick="startDetection()">开始检测</button>
                <button onclick="resetSystem()">重置</button>
            </div>
        </section>
    </main>

    <section class="result-panel">
        <h2>测速结果</h2>
        <table>
            <thead>
            <tr>
                <th>车辆 ID</th>
                <th>第一线帧号</th>
                <th>第二线帧号</th>
                <th>间隔帧数</th>
                <th>用时/s</th>
                <th>距离/m</th>
                <th>速度/km/h</th>
            </tr>
            </thead>
            <tbody id="resultBody">
            </tbody>
        </table>
    </section>
</div>

<script src="/static/js/main.js"></script>
<script src="/static/js/line_editor.js"></script>
<script src="/static/js/video_player.js"></script>
</body>
</html>
"""

files["app/static/css/style.css"] = r"""
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, "Microsoft YaHei", sans-serif;
    background: #101522;
    color: #f2f2f2;
}

.page {
    width: 100%;
    min-height: 100vh;
    padding: 20px;
}

.header {
    text-align: center;
    margin-bottom: 20px;
}

.header h1 {
    margin: 0;
    font-size: 32px;
}

.header p {
    color: #b8c0d0;
}

.main {
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 20px;
}

.video-panel {
    background: #171d2e;
    padding: 16px;
    border-radius: 12px;
}

.video-box {
    width: 100%;
    min-height: 620px;
    background: #000;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

.video-box img {
    width: 100%;
    height: auto;
    display: block;
}

.control-panel {
    background: #171d2e;
    padding: 16px;
    border-radius: 12px;
}

.card {
    background: #20283c;
    padding: 14px;
    border-radius: 10px;
    margin-bottom: 16px;
}

.card h3 {
    margin-top: 0;
}

label {
    display: block;
    margin-top: 10px;
    margin-bottom: 6px;
    color: #d8def0;
}

input {
    width: 100%;
    padding: 8px;
    border-radius: 6px;
    border: none;
    margin-bottom: 8px;
}

button {
    width: 100%;
    padding: 10px;
    margin-top: 8px;
    border: none;
    border-radius: 6px;
    background: #3e7bff;
    color: white;
    cursor: pointer;
    font-size: 15px;
}

button:hover {
    background: #6798ff;
}

.start-btn {
    background: #16a34a;
}

.start-btn:hover {
    background: #22c55e;
}

.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}

.result-panel {
    margin-top: 20px;
    background: #171d2e;
    padding: 16px;
    border-radius: 12px;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: #20283c;
    border-radius: 8px;
    overflow: hidden;
}

th, td {
    padding: 10px;
    border-bottom: 1px solid #313b55;
    text-align: center;
}

th {
    background: #2b3550;
}

#uploadStatus {
    color: #8bd3ff;
}
"""

files["app/static/js/main.js"] = r"""
async function uploadVideo() {
    const fileInput = document.getElementById("videoFile");
    const status = document.getElementById("uploadStatus");

    if (!fileInput.files.length) {
        alert("请先选择视频文件");
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    status.innerText = "正在上传视频...";

    const res = await fetch("/api/video/upload", {
        method: "POST",
        body: formData
    });

    const data = await res.json();

    if (data.code === 200) {
        status.innerText = "上传成功：" + data.video_path;
    } else {
        status.innerText = "上传失败";
    }
}

async function saveLineConfig() {
    const fps = parseFloat(document.getElementById("fps").value);
    const distance = parseFloat(document.getElementById("distance").value);

    const line1 = [
        [
            parseInt(document.getElementById("l1x1").value),
            parseInt(document.getElementById("l1y1").value)
        ],
        [
            parseInt(document.getElementById("l1x2").value),
            parseInt(document.getElementById("l1y2").value)
        ]
    ];

    const line2 = [
        [
            parseInt(document.getElementById("l2x1").value),
            parseInt(document.getElementById("l2y1").value)
        ],
        [
            parseInt(document.getElementById("l2x2").value),
            parseInt(document.getElementById("l2y2").value)
        ]
    ];

    const body = {
        line1: line1,
        line2: line2,
        distance_m: distance,
        fps: fps
    };

    const res = await fetch("/api/line/config", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    });

    const data = await res.json();

    if (data.code === 200) {
        alert("测速线配置成功");
    } else {
        alert("测速线配置失败");
    }
}

function startDetection() {
    const img = document.getElementById("videoStream");
    img.src = "/api/video/stream?t=" + new Date().getTime();

    if (window.resultTimer) {
        clearInterval(window.resultTimer);
    }

    window.resultTimer = setInterval(loadResults, 1000);
}

async function resetSystem() {
    await fetch("/api/video/reset", {
        method: "POST"
    });

    document.getElementById("videoStream").src = "";
    document.getElementById("resultBody").innerHTML = "";

    if (window.resultTimer) {
        clearInterval(window.resultTimer);
    }

    alert("系统已重置");
}

async function loadResults() {
    const res = await fetch("/api/results");
    const data = await res.json();

    const tbody = document.getElementById("resultBody");
    tbody.innerHTML = "";

    if (!data.data || data.data.length === 0) {
        return;
    }

    data.data.forEach(item => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${item.track_id}</td>
            <td>${item.line1_frame}</td>
            <td>${item.line2_frame}</td>
            <td>${item.frame_diff}</td>
            <td>${item.time_seconds}</td>
            <td>${item.distance_m}</td>
            <td>${item.speed_kmh}</td>
        `;

        tbody.appendChild(tr);
    });
}
"""

files["app/static/js/line_editor.js"] = r"""
// 第二版可以在这里实现：鼠标拖动测速线
// 当前第一版先使用右侧坐标输入框调整测速线位置
"""

files["app/static/js/video_player.js"] = r"""
// 第二版可以在这里实现：暂停、继续、单帧调试等功能
"""

files["README.md"] = r"""
# Vehicle Speed Web System

基于 YOLOv8 的车辆检测、跟踪与速度检测系统。

## 功能

- 网页端上传视频
- YOLOv8 车辆检测
- IOU Tracker 车辆跟踪
- 绘制车辆方框
- 绘制车辆轨迹
- 双虚拟测速线测速
- 根据视频帧号和 FPS 计算速度
- 避免电脑性能影响测速结果

## 启动方式

```bash
pip install -r requirements.txt
python run.py