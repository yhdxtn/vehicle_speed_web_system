import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple


def draw_speed_lines(
    frame,
    line1: Tuple[Tuple[float, float], Tuple[float, float]],
    line2: Tuple[Tuple[float, float], Tuple[float, float]],
    distance_m: float
):
    p1 = tuple(map(int, line1[0]))
    p2 = tuple(map(int, line1[1]))
    p3 = tuple(map(int, line2[0]))
    p4 = tuple(map(int, line2[1]))

    cv2.line(frame, p1, p2, (0, 255, 255), 3)
    cv2.line(frame, p3, p4, (0, 0, 255), 3)

    cv2.putText(
        frame,
        "Line 1",
        (p1[0], max(25, p1[1] - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "Line 2",
        (p3[0], max(25, p3[1] - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )

    mid_x = int((p1[0] + p2[0]) / 2)
    mid_y = int((p1[1] + p3[1]) / 2)

    cv2.putText(
        frame,
        f"Distance: {distance_m:.1f} m",
        (mid_x - 100, mid_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


def draw_tracks(
    frame,
    tracks: List[Dict[str, Any]],
    speed_getter
):
    for track in tracks:
        track_id = track["track_id"]
        bbox = track["bbox"]
        trajectory = track.get("trajectory", [])

        x1, y1, x2, y2 = map(int, bbox)

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        speed = speed_getter(track_id)

        if speed is not None:
            label = f"ID:{track_id}  {speed:.1f} km/h"
        else:
            label = f"ID:{track_id}"

        cv2.putText(
            frame,
            label,
            (x1, max(25, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2
        )

        if len(trajectory) >= 2:
            points = np.array(
                [[int(x), int(y)] for x, y in trajectory],
                dtype=np.int32
            )

            cv2.polylines(
                frame,
                [points],
                isClosed=False,
                color=(255, 0, 0),
                thickness=2
            )