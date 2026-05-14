from typing import List, Dict, Any, Tuple
from app.config import CONFIG


def get_center(bbox: List[float]) -> Tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2, (y1 + y2) / 2


def bbox_iou(box_a: List[float], box_b: List[float]) -> float:
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


class IOUTracker:
    def __init__(self):
        tracker_cfg = CONFIG.get("tracker", {})

        self.iou_threshold = float(tracker_cfg.get("iou_threshold", 0.3))
        self.max_lost_frames = int(tracker_cfg.get("max_lost_frames", 30))

        self.next_id = 1
        self.tracks: Dict[int, Dict[str, Any]] = {}

    def reset(self):
        self.next_id = 1
        self.tracks.clear()

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        active_tracks = []
        used_detection_indexes = set()

        updated_tracks = {}

        for track_id, track in list(self.tracks.items()):
            best_iou = 0.0
            best_det_index = -1

            for det_index, det in enumerate(detections):
                if det_index in used_detection_indexes:
                    continue

                iou = bbox_iou(track["bbox"], det["bbox"])

                if iou > best_iou:
                    best_iou = iou
                    best_det_index = det_index

            if best_iou >= self.iou_threshold and best_det_index >= 0:
                det = detections[best_det_index]
                used_detection_indexes.add(best_det_index)

                center = get_center(det["bbox"])

                track["bbox"] = det["bbox"]
                track["center"] = center
                track["confidence"] = det["confidence"]
                track["class_name"] = det["class_name"]
                track["lost"] = 0
                track["trajectory"].append(center)

                if len(track["trajectory"]) > 80:
                    track["trajectory"] = track["trajectory"][-80:]

                updated_tracks[track_id] = track
                active_tracks.append(track.copy())
            else:
                track["lost"] += 1

                if track["lost"] <= self.max_lost_frames:
                    updated_tracks[track_id] = track

        for det_index, det in enumerate(detections):
            if det_index in used_detection_indexes:
                continue

            center = get_center(det["bbox"])

            track = {
                "track_id": self.next_id,
                "bbox": det["bbox"],
                "center": center,
                "confidence": det["confidence"],
                "class_name": det["class_name"],
                "trajectory": [center],
                "lost": 0
            }

            updated_tracks[self.next_id] = track
            active_tracks.append(track.copy())

            self.next_id += 1

        self.tracks = updated_tracks

        return active_tracks