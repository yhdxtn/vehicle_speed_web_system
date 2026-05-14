import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse

from app.config import UPLOAD_DIR
from app.services.video_processor import processor

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()

    if suffix not in [".mp4", ".avi", ".mov", ".mkv"]:
        return {
            "code": 400,
            "message": "仅支持 mp4、avi、mov、mkv 格式视频",
            "video_path": ""
        }

    filename = f"{uuid.uuid4().hex}{suffix}"
    save_path = UPLOAD_DIR / filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    processor.set_video_path(str(save_path))

    return {
        "code": 200,
        "message": "视频上传成功",
        "video_path": str(save_path)
    }


@router.get("/stream")
def video_stream():
    return StreamingResponse(
        processor.stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )