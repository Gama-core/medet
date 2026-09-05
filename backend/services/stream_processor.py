"""
Traitement de flux reseau (RTSP/HTTP/HTTPS) — connexion et analyse bornee
dans le temps. Reutilise la boucle generique de video_processor.
"""

import time

import cv2

from models.schemas import StreamRequest, StreamResult
from services.video_processor import process_capture


def process_stream(request: StreamRequest) -> StreamResult:
    """
    Se connecte a un flux RTSP/HTTP/HTTPS et l'analyse pendant
    `duration_seconds` secondes maximum (1 frame sur `frame_skip`).

    Note : conçu pour une analyse bornee dans le temps (usage API synchrone).
    Pour un affichage live continu cote client, prevoir un WebSocket ou un
    polling repete sur cet endpoint avec des segments courts.
    """
    start_time = time.perf_counter()

    cap = cv2.VideoCapture(request.url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return StreamResult(
            url=request.url,
            connected=False,
            total_frames_read=0,
            frames_analyzed=0,
            detections=[],
            segments=[],
            processing_time_ms=round(elapsed_ms, 2),
            message="Connexion impossible — verifie l'URL, les identifiants et la disponibilite du flux.",
        )

    fps_source = cap.get(cv2.CAP_PROP_FPS) or 25.0
    max_frames = int(fps_source * request.duration_seconds)

    result = process_capture(cap, frame_skip=request.frame_skip, max_frames=max_frames)
    cap.release()

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return StreamResult(
        url=request.url,
        connected=True,
        total_frames_read=result.total_frames_read,
        frames_analyzed=result.frames_analyzed,
        detections=result.detections,
        segments=result.segments,
        processing_time_ms=round(elapsed_ms, 2),
        message=f"Analyse terminee sur {request.duration_seconds}s ({result.total_frames_read} frames lues).",
    )