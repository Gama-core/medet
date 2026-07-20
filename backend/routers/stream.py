"""Route POST /predict/stream."""

from fastapi import APIRouter

from models.schemas import StreamRequest, StreamResult
from services.stream_processor import process_stream

router = APIRouter(prefix="/predict", tags=["stream"])


@router.post("/stream", response_model=StreamResult)
async def predict_stream(request: StreamRequest):
    """Se connecte a un flux RTSP/HTTP/HTTPS et l'analyse pendant une duree donnee."""
    return process_stream(request)