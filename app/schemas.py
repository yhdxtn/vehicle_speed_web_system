from pydantic import BaseModel
from typing import List


class UploadResponse(BaseModel):
    code: int
    message: str
    video_path: str


class SpeedLineConfig(BaseModel):
    line1: List[List[float]]
    line2: List[List[float]]
    distance_m: float = 10.0
    fps: float = 30.0


class CommonResponse(BaseModel):
    code: int
    message: str