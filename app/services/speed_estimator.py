from typing import Dict, Any, List, Tuple, Optional


Point = Tuple[float, float]


def orientation(p: Point, q: Point, r: Point) -> int:
    value = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    if abs(value) < 1e-6:
        return 0

    return 1 if value > 0 else 2


def on_segment(p: Point, q: Point, r: Point) -> bool:
    return (
        min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
        and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])
    )


def segments_intersect(p1: Point, q1: Point, p2: Point, q2: Point) -> bool:
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
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
    def __init__(
        self,
        line1: List[List[float]],
        line2: List[List[float]],
        distance_m: float,
        fps: float
    ):
        self.line1 = self._to_line(line1)
        self.line2 = self._to_line(line2)

        self.distance_m = float(distance_m)
        self.fps = float(fps)

        self.vehicle_states: Dict[int, Dict[str, Any]] = {}
        self.results: List[Dict[str, Any]] = []

    @staticmethod
    def _to_line(line: List[List[float]]) -> Tuple[Point, Point]:
        return (
            (float(line[0][0]), float(line[0][1])),
            (float(line[1][0]), float(line[1][1]))
        )

    def set_config(
        self,
        line1: List[List[float]],
        line2: List[List[float]],
        distance_m: float,
        fps: float
    ):
        self.line1 = self._to_line(line1)
        self.line2 = self._to_line(line2)
        self.distance_m = float(distance_m)
        self.fps = float(fps)

        self.reset()

    def reset(self):
        self.vehicle_states.clear()
        self.results.clear()

    def update(
        self,
        track_id: int,
        trajectory: List[Point],
        frame_id: int
    ) -> Optional[float]:
        if len(trajectory) < 2:
            return None

        prev_point = trajectory[-2]
        curr_point = trajectory[-1]

        cross_line1 = segments_intersect(
            prev_point,
            curr_point,
            self.line1[0],
            self.line1[1]
        )

        cross_line2 = segments_intersect(
            prev_point,
            curr_point,
            self.line2[0],
            self.line2[1]
        )

        state = self.vehicle_states.setdefault(
            track_id,
            {
                "track_id": track_id,
                "first_line": None,
                "first_frame": None,
                "second_line": None,
                "second_frame": None,
                "frame_diff": None,
                "time_seconds": None,
                "speed_kmh": None,
                "calculated": False
            }
        )

        if state["calculated"]:
            return state["speed_kmh"]

        if state["first_line"] is None:
            if cross_line1:
                state["first_line"] = 1
                state["first_frame"] = frame_id
            elif cross_line2:
                state["first_line"] = 2
                state["first_frame"] = frame_id

            return None

        if state["first_line"] == 1 and cross_line2:
            return self._calculate_speed(state, second_line=2, second_frame=frame_id)

        if state["first_line"] == 2 and cross_line1:
            return self._calculate_speed(state, second_line=1, second_frame=frame_id)

        return None

    def _calculate_speed(
        self,
        state: Dict[str, Any],
        second_line: int,
        second_frame: int
    ) -> Optional[float]:
        frame_diff = abs(second_frame - state["first_frame"])

        if frame_diff <= 0:
            return None

        time_seconds = frame_diff / self.fps

        if time_seconds <= 0:
            return None

        speed_mps = self.distance_m / time_seconds
        speed_kmh = speed_mps * 3.6

        state["second_line"] = second_line
        state["second_frame"] = second_frame
        state["frame_diff"] = frame_diff
        state["time_seconds"] = time_seconds
        state["speed_kmh"] = speed_kmh
        state["calculated"] = True

        result = {
            "track_id": state["track_id"],
            "first_line": state["first_line"],
            "second_line": state["second_line"],
            "first_frame": state["first_frame"],
            "second_frame": state["second_frame"],
            "frame_diff": frame_diff,
            "time_seconds": round(time_seconds, 3),
            "distance_m": self.distance_m,
            "speed_kmh": round(speed_kmh, 2)
        }

        self.results.append(result)

        return speed_kmh

    def get_speed(self, track_id: int) -> Optional[float]:
        state = self.vehicle_states.get(track_id)

        if not state:
            return None

        return state.get("speed_kmh")

    def get_results(self) -> List[Dict[str, Any]]:
        return self.results