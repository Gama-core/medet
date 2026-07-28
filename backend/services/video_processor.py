"""
Traitement video — boucle generique de lecture/analyse frame par frame.
Utilisee par le traitement de fichier video uploade ET par le traitement de
flux reseau (RTSP/HTTP), qui partagent la meme logique de parcours de frames.

Produit egalement des "segments" (regroupement de frames consecutives de
meme detection), au meme format que le rapport CSV genere par app2.py
(Streamlit) : debut, fin, duree, confiance max, nombre de frames.
"""

import time
from typing import List, Optional

import cv2
from fastapi import HTTPException
from PIL import Image

from models.schemas import FrameResult, SegmentResult, VideoResult
from services.pipeline import run_pipeline_on_image

# Ecart maximum (en secondes) entre deux frames detectees pour qu'elles soient
# considerees comme faisant partie du meme segment. Au-dela, on ferme le
# segment courant et on en ouvre un nouveau.
SEGMENT_GAP_TOLERANCE_SECONDS = 2.0


def _build_segments(detections: List[FrameResult]) -> List[SegmentResult]:
    """Regroupe une liste de FrameResult (deja filtree sur is_polyp=True) en segments."""
    if not detections:
        return []

    segments: List[SegmentResult] = []
    current_frames = [detections[0]]

    for frame_result in detections[1:]:
        prev = current_frames[-1]
        gap = frame_result.timestamp_seconds - prev.timestamp_seconds
        same_type = frame_result.prediction.polyp_type == prev.prediction.polyp_type

        if gap <= SEGMENT_GAP_TOLERANCE_SECONDS and same_type:
            current_frames.append(frame_result)
        else:
            segments.append(_frames_to_segment(current_frames))
            current_frames = [frame_result]

    segments.append(_frames_to_segment(current_frames))
    return segments


def _frames_to_segment(frames: List[FrameResult]) -> SegmentResult:
    confidences = [f.prediction.confidence for f in frames]
    first, last = frames[0], frames[-1]
    return SegmentResult(
        start_timestamp_seconds=first.timestamp_seconds,
        end_timestamp_seconds=last.timestamp_seconds,
        duration_seconds=round(last.timestamp_seconds - first.timestamp_seconds, 2),
        polyp_type=first.prediction.polyp_type,
        polyp_label=first.prediction.polyp_label,
        max_confidence=round(max(confidences), 4),
        frame_count=len(frames),
    )


def process_capture(
    cap: cv2.VideoCapture, frame_skip: int, max_frames: Optional[int] = None
) -> VideoResult:
    """
    Boucle generique sur un cv2.VideoCapture deja ouvert (fichier local ou
    flux reseau), en analysant 1 frame sur `frame_skip`. `max_frames` borne le
    nombre total de frames lues (utile pour les flux reseau, illimites par nature).
    """
    start_time = time.perf_counter()
    fps_source = cap.get(cv2.CAP_PROP_FPS) or 25.0

    detections: List[FrameResult] = []
    frame_index = 0
    frames_analyzed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index % frame_skip == 0:
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            prediction = run_pipeline_on_image(image)
            if prediction is not None and prediction.is_polyp:
                detections.append(
                    FrameResult(
                        frame_index=frame_index,
                        timestamp_seconds=round(frame_index / fps_source, 2),
                        prediction=prediction,
                    )
                )
            frames_analyzed += 1

        frame_index += 1
        if max_frames is not None and frame_index >= max_frames:
            break

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    segments = _build_segments(detections)

    return VideoResult(
        total_frames_read=frame_index,
        frames_analyzed=frames_analyzed,
        fps_source=fps_source,
        detections=detections,
        segments=segments,
        processing_time_ms=round(elapsed_ms, 2),
    )


def process_video_file(file_path: str, frame_skip: int) -> VideoResult:
    """Ouvre un fichier video local et l'analyse en integralite."""
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Impossible de lire la video.")
    try:
        return process_capture(cap, frame_skip=frame_skip)
    finally:
        cap.release()
