"""Route POST /predict/video."""

import os
import tempfile

from fastapi import APIRouter, File, UploadFile

from models.schemas import VideoResult
from services.video_processor import process_video_file
from utils.helpers import validate_video_upload

router = APIRouter(prefix="/predict", tags=["video"])


@router.post("/video", response_model=VideoResult)
async def predict_video(file: UploadFile = File(...), frame_skip: int = 5):
    """Analyse une video complete (MP4/AVI), frame par frame (1 frame sur `frame_skip`)."""
    validate_video_upload(file)

    suffix = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = process_video_file(tmp_path, frame_skip=max(1, frame_skip))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return result