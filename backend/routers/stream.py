"""Routes /predict/stream — analyse ponctuelle bornée dans le temps, et
mode session live (start / next / stop) pour un affichage frame par frame."""

import base64
import time
import uuid
from typing import Dict, Optional

import cv2
from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel

from models.schemas import StreamRequest, StreamResult
from services.pipeline import run_pipeline_on_image
from services.stream_processor import process_stream

router = APIRouter(prefix="/predict", tags=["stream"])


@router.post("/stream", response_model=StreamResult)
async def predict_stream(request: StreamRequest):
    """Se connecte a un flux RTSP/HTTP/HTTPS et l'analyse pendant une duree donnee."""
    return process_stream(request)


# ============================================================================
# Mode session live : start / next / stop — pour un affichage frame par frame
# cote frontend, en reutilisant le meme pipeline que /predict/image.
# ============================================================================


class StreamSessionStartRequest(BaseModel):
    url: str
    frame_skip: int = 5


class StreamSessionStartResponse(BaseModel):
    session_id: str


class _Session:
    def __init__(self, cap: cv2.VideoCapture, frame_skip: int):
        self.cap = cap
        self.frame_skip = frame_skip
        self.frame_index = 0
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 25.0


_sessions: Dict[str, _Session] = {}


def _encode_frame_base64(frame, quality: int = 70) -> Optional[str]:
    """Encode une frame OpenCV (BGR) en data URL JPEG, pour affichage direct
    cote frontend (<img src="...">), sans passer par un fichier disque."""
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return None
    b64 = base64.b64encode(buf).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


@router.post("/stream/start", response_model=StreamSessionStartResponse)
def start_stream_session(request: StreamSessionStartRequest):
    cap = cv2.VideoCapture(request.url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        raise HTTPException(
            status_code=404,
            detail="Connexion impossible — vérifie l'URL, les identifiants et la disponibilité du flux.",
        )
    session_id = str(uuid.uuid4())
    _sessions[session_id] = _Session(cap, request.frame_skip)
    return StreamSessionStartResponse(session_id=session_id)


@router.get("/stream/{session_id}/next")
def next_stream_frame(session_id: str):
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session inconnue ou déjà fermée.")

    # Avance de frame_skip frames (grab() est plus léger que read() pour "sauter")
    for _ in range(max(0, session.frame_skip - 1)):
        session.cap.grab()

    ret, frame = session.cap.read()
    if not ret:
        session.cap.release()
        _sessions.pop(session_id, None)
        return {"status": "ended"}

    session.frame_index += session.frame_skip
    elapsed_s = session.frame_index / session.fps
    frame_base64 = _encode_frame_base64(frame)

    # cv2 lit en BGR — le pipeline attend du PIL/RGB
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    prediction = run_pipeline_on_image(image)

    if prediction is None:
        return {
            "status": "ok",
            "elapsed_s": round(elapsed_s, 2),
            "frame_base64": frame_base64,
            "is_polyp": False,
            "polyp_type": None,
            "polyp_label": None,
            "confidence": None,
            "all_probabilities": None,
            "yolo_confidence": 0.0,
            "yolo_zone": "ignored",
            "bounding_box": None,
            "action": "ignored",
            "processing_time_ms": 0.0,
        }

    return {
        "status": "ok",
        "elapsed_s": round(elapsed_s, 2),
        "frame_base64": frame_base64,
        **prediction.model_dump(),
    }


@router.post("/stream/{session_id}/stop")
def stop_stream_session(session_id: str):
    session = _sessions.pop(session_id, None)
    if session:
        session.cap.release()
    return {"stopped": True}
