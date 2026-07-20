"""Service de classification — etage 2 (EfficientNet binaire + type de polype)."""

import logging
import os
from typing import Optional, Tuple

import torch
import torch.nn as nn
from fastapi import HTTPException
from PIL import Image
from torchvision import models

from utils.helpers import (
    BINARY_CLASSES,
    BINARY_WEIGHTS_PATH,
    DEVICE,
    TYPE_CLASSES,
    TYPE_WEIGHTS_PATH,
)
from utils.transforms import classification_transform

logger = logging.getLogger("medet-backend.classifier")

_binary_model = None
_type_model = None


def _build_efficientnet(num_classes: int) -> nn.Module:
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    return model


def load_classifiers() -> None:
    """Charge les deux modeles EfficientNet (binaire + type). A appeler au demarrage."""
    global _binary_model, _type_model

    try:
        if os.path.exists(BINARY_WEIGHTS_PATH):
            model = _build_efficientnet(len(BINARY_CLASSES))
            model.load_state_dict(torch.load(BINARY_WEIGHTS_PATH, map_location="cpu"))
            model.to(DEVICE).eval()
            _binary_model = model
            logger.info("EfficientNet Etage2 (binaire) charge.")
        else:
            logger.warning("Poids binaires introuvables : %s", BINARY_WEIGHTS_PATH)
    except Exception:
        logger.exception("Erreur chargement EfficientNet binaire")

    try:
        if os.path.exists(TYPE_WEIGHTS_PATH):
            model = _build_efficientnet(len(TYPE_CLASSES))
            model.load_state_dict(torch.load(TYPE_WEIGHTS_PATH, map_location="cpu"))
            model.to(DEVICE).eval()
            _type_model = model
            logger.info("EfficientNet types charge.")
        else:
            logger.warning("Poids types introuvables : %s", TYPE_WEIGHTS_PATH)
    except Exception:
        logger.exception("Erreur chargement EfficientNet types")


def binary_loaded() -> bool:
    return _binary_model is not None


def type_loaded() -> bool:
    return _type_model is not None


def classify_binary(roi: Image.Image) -> Tuple[str, float, dict]:
    """Verifie si la zone recadree est vraiment un polype. Retourne (label, confiance, toutes_probas)."""
    if _binary_model is None:
        raise HTTPException(status_code=503, detail="EfficientNet binaire non charge.")

    img_tensor = classification_transform(roi).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        out = _binary_model(img_tensor)
        probs = torch.softmax(out, dim=1)[0]

    pred_idx = int(probs.argmax().item())
    label = BINARY_CLASSES[pred_idx]
    all_probs = {c: round(p.item(), 4) for c, p in zip(BINARY_CLASSES, probs)}
    return label, round(probs[pred_idx].item(), 4), all_probs


def classify_type(roi: Image.Image) -> Tuple[str, float, dict]:
    """Classifie le type de polype (1p/1s/2/3). Retourne (type, confiance, toutes_probas)."""
    if _type_model is None:
        raise HTTPException(status_code=503, detail="EfficientNet types non charge.")

    img_tensor = classification_transform(roi).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        out = _type_model(img_tensor)
        probs = torch.softmax(out, dim=1)[0]

    conf, idx = torch.max(probs, dim=0)
    polyp_type = TYPE_CLASSES[int(idx.item())]
    all_probs = {c: round(p.item(), 4) for c, p in zip(TYPE_CLASSES, probs)}
    return polyp_type, round(conf.item(), 4), all_probs
