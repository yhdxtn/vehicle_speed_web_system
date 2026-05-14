from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class VehicleTrack:
    track_id: int
    bbox: List[float]
    center: Tuple[float, float]
    class_name: str = "vehicle"
    confidence: float = 0.0
    trajectory: List[Tuple[float, float]] = field(default_factory=list)
    speed_kmh: Optional[float] = None