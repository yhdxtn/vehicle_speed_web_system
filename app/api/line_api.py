from fastapi import APIRouter
from app.schemas import SpeedLineConfig
from app.services.video_processor import processor

router = APIRouter(prefix="/api/line", tags=["line"])


def is_valid_line(line):
    if not isinstance(line, list):
        return False

    if len(line) != 2:
        return False

    for point in line:
        if not isinstance(point, list):
            return False

        if len(point) != 2:
            return False

    return True


@router.post("/config")
def set_line_config(config: SpeedLineConfig):
    if not is_valid_line(config.line1) or not is_valid_line(config.line2):
        return {
            "code": 400,
            "message": "测速线格式错误"
        }

    if config.distance_m <= 0:
        return {
            "code": 400,
            "message": "两条测速线之间的实际距离必须大于 0"
        }

    if config.fps <= 0:
        return {
            "code": 400,
            "message": "FPS 必须大于 0"
        }

    processor.set_line_config(
        line1=config.line1,
        line2=config.line2,
        distance_m=config.distance_m,
        fps=config.fps
    )

    return {
        "code": 200,
        "message": "测速线配置成功"
    }