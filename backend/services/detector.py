"""Service de detection — etage 1 (YOLO)."""

import logging
import os
from typing import Optional, Tuple

from fastapi import HTTPException
from PIL import Image
from ultralytics import YOLO

from utils.helpers import MAX_BOX_AREA_RATIO, YOLO_LOW, YOLO_WEIGHTS_PATH, box_area_ratio

logger = logging.getLogger("medet-backend.detector")

_yolo_model: Optional[YOLO] = None


def load_yolo() -> None:
    """Charge le modele YOLO en memoire. A appeler une fois au demarrage."""
    global _yolo_model
    try:
        if os.path.exists(YOLO_WEIGHTS_PATH):
            _yolo_model = YOLO(YOLO_WEIGHTS_PATH)
            logger.info("YOLO charge : %s", YOLO_WEIGHTS_PATH)
        else:
            logger.warning("YOLO poids introuvables : %s", YOLO_WEIGHTS_PATH)
    except Exception:
        logger.exception("Erreur chargement YOLO")


def is_loaded() -> bool:
    return _yolo_model is not None


def detect(image: Image.Image) -> Optional[Tuple[int, int, int, int, float]]:
    """
    Applique YOLO sur l'image et retourne (x1, y1, x2, y2, confidence) de la
    boite la plus confiante au-dessus de YOLO_LOW. Retourne None si aucune
    detection, ou si la boite est un faux positif evident (trop grande).
    """
    if _yolo_model is None:
        raise HTTPException(status_code=503, detail="YOLO non charge.")

    results = _yolo_model.predict(source=image, conf=YOLO_LOW, verbose=False)
    if len(results[0].boxes) == 0:
        return None

    box = max(results[0].boxes, key=lambda b: float(b.conf[0]))
    confidence = float(box.conf[0])
    x1, y1, x2, y2 = map(int, box.xyxy[0])

    w_img, h_img = image.size
    if box_area_ratio(x1, y1, x2, y2, w_img, h_img) > MAX_BOX_AREA_RATIO:
        return None

    return x1, y1, x2, y2, confidence