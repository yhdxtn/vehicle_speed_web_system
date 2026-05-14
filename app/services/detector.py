from typing import List, Dict, Any
from pathlib import Path

from ultralytics import YOLO

from app.config import CONFIG, get_model_path


class YOLOVehicleDetector:
    def __init__(self):
        model_cfg = CONFIG.get("model", {})
        self.weight_path = get_model_path()
        self.conf_threshold = float(model_cfg.get("conf_threshold", 0.35))
        self.iou_threshold = float(model_cfg.get("iou_threshold", 0.45))

        self.model = None

        self.vehicle_class_names = {
            "car",
            "bus",
            "truck",
            "motorcycle"
        }

        # COCO 数据集里的车辆相关类别
        self.vehicle_class_ids = {2, 3, 5, 7}

    def load_model(self):
        if self.model is not None:
            return

        if not Path(self.weight_path).exists():
            raise FileNotFoundError(f"模型文件不存在：{self.weight_path}")

        self.model = YOLO(self.weight_path)

    def detect(self, frame) -> List[Dict[str, Any]]:
        self.load_model()

        results = self.model(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False
        )

        result = results[0]
        detections = []

        if result.boxes is None:
            return detections

        names = self.model.names

        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])

            if isinstance(names, dict):
                class_name = names.get(cls_id, str(cls_id))
            else:
                class_name = names[cls_id] if cls_id < len(names) else str(cls_id)

            if cls_id not in self.vehicle_class_ids and class_name not in self.vehicle_class_names:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detections.append(
                {
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "confidence": conf,
                    "class_id": cls_id,
                    "class_name": class_name
                }
            )

        return detections