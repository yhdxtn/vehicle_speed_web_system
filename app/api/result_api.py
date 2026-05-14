from fastapi import APIRouter
from app.services.video_processor import processor

router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("")
def get_results():
    return {
        "code": 200,
        "data": processor.get_results()
    }