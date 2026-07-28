"""
Pipeline complet — orchestre l'etage 1 (detector) et l'etage 2 (classifier)
selon les seuils de decision :

- YOLO < 50%       -> ignore (detect() retourne deja None dans ce cas)
- YOLO 50% - 90%   -> classify_binary() verifie, puis classify_type() si vrai polype
- YOLO > 90%       -> classify_type() directement, pas de verification binaire
"""

import logging
import time
from typing import Optional

from PIL import Image

from models.schemas import BoundingBox, PredictionResponse
from services import classifier, detector
from utils.helpers import POLYP_LABELS, YOLO_HIGH

logger = logging.getLogger("medet-backend.pipeline")


def run_pipeline_on_image(image: Image.Image) -> Optional[PredictionResponse]:
    """Point d'entree unique du pipeline, partage par tous les endpoints /predict/*."""
    start_time = time.perf_counter()

    detection = detector.detect(image)
    if detection is None:
        return None

    x1, y1, x2, y2, yolo_confidence = detection
    roi = image.crop((x1, y1, x2, y2))

    yolo_zone = "uncertain" if yolo_confidence < YOLO_HIGH else "high"

    if yolo_zone == "uncertain":
        predicted, confidence, all_probs = classifier.classify_binary(roi)

        if predicted != "polype":
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return PredictionResponse(
                is_polyp=False,
                polyp_type=None,
                polyp_label=POLYP_LABELS.get(predicted, predicted),
                confidence=confidence,
                all_probabilities=all_probs,
                yolo_confidence=round(yolo_confidence, 4),
                yolo_zone=yolo_zone,
                bounding_box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                action="verified_and_classified",
                processing_time_ms=round(elapsed_ms, 2),
            )

        action = "verified_and_classified"
    else:
        action = "directly_classified"

    polyp_type, confidence, all_probs = classifier.classify_type(roi)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "YOLO=%.0f%% (%s) -> type=%s (%.0f%%) action=%s [%.1fms]",
        yolo_confidence * 100,
        yolo_zone,
        polyp_type,
        confidence * 100,
        action,
        elapsed_ms,
    )

    return PredictionResponse(
        is_polyp=True,
        polyp_type=polyp_type,
        polyp_label=POLYP_LABELS[polyp_type],
        confidence=confidence,
        all_probabilities=all_probs,
        yolo_confidence=round(yolo_confidence, 4),
        yolo_zone=yolo_zone,
        bounding_box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
        action=action,
        processing_time_ms=round(elapsed_ms, 2),
    )
