"""
Backend FastAPI — medet
Pipeline hybride YOLO + EfficientNet avec classification fine des polypes
=========================================================================

Point d'entree de l'application : assemble les routers, charge les modeles
au demarrage, expose /health et /.

Architecture de decision (voir services/pipeline.py) :
- Score YOLO < 50%      -> ignore
- Score YOLO 50% - 90%  -> EfficientNet verifie (vrai polype ?) + classifie le type
- Score YOLO > 90%      -> classifie directement le type (1p / 1s / 2 / 3)

Entrees supportees : image, video, webcam (frame par frame), flux RTSP/HTTP/HTTPS.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from models.schemas import HealthResponse
from routers import image, records, stream, video, webcam
from services import classifier, detector
from utils.helpers import DEVICE, POLYP_LABELS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medet-backend")

# Force le transport RTSP en TCP (evite "Unsupported Transport" observe en test)
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

app = FastAPI(
    title="medet — Classification fine des polypes",
    description=(
        "Pipeline hybride YOLO + EfficientNet.\n\n"
        "YOLO < 50%  : ignore\n"
        "YOLO 50-90% : verifie + classifie le type\n"
        "YOLO > 90%  : classifie directement le type\n\n"
        "Types : 1p (pediculé), 1s (sessile), 2 (plan), 3 (ulcere)\n\n"
        "Entrees supportees : image, video, webcam (frame par frame), flux RTSP/HTTP/HTTPS."
    ),
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(image.router)
app.include_router(video.router)
app.include_router(webcam.router)
app.include_router(stream.router)
app.include_router(records.router)


@app.on_event("startup")
def on_startup():
    detector.load_yolo()
    classifier.load_classifiers()
    init_db()


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        yolo_loaded=detector.is_loaded(),
        binary_loaded=classifier.binary_loaded(),
        type_loaded=classifier.type_loaded(),
        device=str(DEVICE),
        version="4.0.0",
    )


@app.get("/")
def root():
    return {
        "message": "medet API — classification fine des polypes",
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "/predict/image",
            "/predict/video",
            "/predict/webcam",
            "/predict/stream",
        ],
        "version": "4.0.0",
        "polyp_types": POLYP_LABELS,
    }