"""
Backend FastAPI v3 — medet
Pipeline hybride YOLO + EfficientNet avec classification fine des polypes
=========================================================================

Nouvelle architecture (demande manager) :
- Score YOLO < 50%          → ignoré
- Score YOLO 50% - 90%      → EfficientNet vérifie (vrai polype ?)
                               + classifie le type (1p / 1s / 2 / 3)
- Score YOLO > 90%          → classifie directement le type (1p / 1s / 2 / 3)

EfficientNet gère maintenant 5 classes :
  - normal        (faux positif YOLO)
  - polype_1p     (pédiculé)
  - polype_1s     (sessile)
  - polype_2      (lésion plane)
  - polype_3      (lésion ulcérée)

Déploiement : Render.com (CPU uniquement)
"""

import io
import json
import logging
import os

import torch
import torch.nn as nn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
from torchvision import models, transforms
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medet-backend")

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

WEIGHTS_PATH = "weights/efficientnet_polyp_types.pt"
META_PATH    = "weights/efficientnet_classes.json"
yolo = YOLO("weights/yolo_best.pt")

# Classes par défaut si pas de fichier de métadonnées
DEFAULT_CLASS_NAMES = ["normal", "polype_1p", "polype_1s", "polype_2", "polype_3"]

# Classes considérées comme "vrai polype" (pas faux positif)
POLYP_CLASSES = {"polype_1p", "polype_1s", "polype_2", "polype_3"}

# Labels lisibles pour l'équipe médicale
POLYP_LABELS = {
    "polype_1p": "Polype pédiculé (1p)",
    "polype_1s": "Polype sessile (1s)",
    "polype_2":  "Lésion plane (2)",
    "polype_3":  "Lésion ulcérée (3)",
    "normal":    "Pas de polype (faux positif YOLO)",
}

# Forcer CPU pour déploiement VPS
device = torch.device("cpu")

# Charger les métadonnées si disponibles
if os.path.exists(META_PATH):
    with open(META_PATH) as f:
        meta = json.load(f)
    CLASS_NAMES = meta["class_names"]
    IMAGE_SIZE  = meta.get("img_size", 224)
    NORM_MEAN   = meta.get("normalize_mean", [0.485, 0.456, 0.406])
    NORM_STD    = meta.get("normalize_std",  [0.229, 0.224, 0.225])
    logger.info("Métadonnées chargées : %s", CLASS_NAMES)
else:
    CLASS_NAMES = DEFAULT_CLASS_NAMES
    IMAGE_SIZE  = 224
    NORM_MEAN   = [0.485, 0.456, 0.406]
    NORM_STD    = [0.229, 0.224, 0.225]
    logger.warning("Pas de fichier métadonnées — valeurs par défaut utilisées.")

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(NORM_MEAN, NORM_STD),
])

# -------------------------------------------------------------------------
# Schémas de réponse
# -------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    # Résultat principal
    is_polyp: bool                      # vrai polype ou faux positif
    polyp_type: str | None              # "polype_1p" / "polype_1s" / "polype_2" / "polype_3" / None
    polyp_label: str                    # label lisible pour le médecin
    confidence: float                   # confiance EfficientNet sur la classe prédite
    all_probabilities: dict[str, float] # détail par classe

    # Contexte YOLO
    yolo_confidence: float              # score YOLO transmis par l'app
    yolo_zone: str                      # "uncertain" (50-90%) ou "high" (>90%)

    # Action effectuée
    action: str                         # "verified_and_classified" | "directly_classified"


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    class_names: list[str]
    polyp_classes: list[str]
    version: str


# -------------------------------------------------------------------------
# Chargement du modèle
# -------------------------------------------------------------------------

model = None


def load_model():
    global model
    try:
        eff = models.efficientnet_b0(weights=None)
        eff.classifier[1] = nn.Linear(
            eff.classifier[1].in_features, len(CLASS_NAMES)
        )
        eff.load_state_dict(torch.load(WEIGHTS_PATH, map_location="cpu"))
        eff.to(device)
        eff.eval()
        model = eff
        logger.info(
            "EfficientNet chargé : %s — %d classes : %s",
            WEIGHTS_PATH, len(CLASS_NAMES), CLASS_NAMES
        )
    except FileNotFoundError:
        logger.warning("Poids introuvables (%s) — /predict renverra 503.", WEIGHTS_PATH)
        model = None
    except Exception:
        logger.exception("Erreur chargement modèle")
        model = None


# -------------------------------------------------------------------------
# Application
# -------------------------------------------------------------------------

app = FastAPI(
    title="medet — Classification fine des polypes",
    description=(
        "Etage 2 (cloud) du pipeline hybride medet v3.\n\n"
        "Reçoit une image détectée par YOLO (étage 1 local) avec son score "
        "de confiance, et retourne :\n"
        "- Si le score YOLO est entre 50% et 90% : vérifie si c'est un vrai "
        "polype ET classifie le type (1p / 1s / 2 / 3)\n"
        "- Si le score YOLO est > 90% : classifie directement le type sans "
        "vérification (YOLO est déjà confiant)\n\n"
        "Types de polypes : 1p (pédiculé), 1s (sessile), 2 (plan), 3 (ulcéré)"
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    load_model()


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        model_loaded=model is not None,
        device=str(device),
        class_names=CLASS_NAMES,
        polyp_classes=list(POLYP_CLASSES),
        version="3.0.0",
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(
    file: UploadFile = File(...),
    yolo_confidence: float = Form(...),  # score YOLO transmis par l'app (0.0 - 1.0)
):
    """
    Classifie une image détectée par YOLO.

    Paramètres :
    - file             : image (jpg/png) de la zone suspecte détectée par YOLO
    - yolo_confidence  : score de confiance YOLO (entre 0.50 et 1.0)

    Logique :
    - 50% ≤ yolo_confidence < 90% → vérifie (vrai polype ?) + classifie le type
    - yolo_confidence ≥ 90%       → classifie directement le type
    """
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=f"Modèle non chargé. Vérifiez '{WEIGHTS_PATH}'.",
        )

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit être une image (jpg, png...).",
        )

    if not (0.0 <= yolo_confidence <= 1.0):
        raise HTTPException(
            status_code=422,
            detail="yolo_confidence doit être entre 0.0 et 1.0.",
        )

    # Lecture de l'image
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Impossible de lire l'image.",
        )

    # Inférence EfficientNet
    img_tensor = transform(image).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(img_tensor)
        probs   = torch.softmax(outputs, dim=1)[0]

    all_probabilities = {
        cls: round(prob.item(), 4)
        for cls, prob in zip(CLASS_NAMES, probs)
    }
    confidence, pred_idx = torch.max(probs, dim=0)
    predicted_class = CLASS_NAMES[pred_idx.item()]

    # ---------------------------------------------------------------
    # Logique selon la zone YOLO
    # ---------------------------------------------------------------

    yolo_zone = "uncertain" if yolo_confidence < 0.90 else "high"

    if yolo_zone == "uncertain":
        # Zone 50%-90% : EfficientNet vérifie ET classifie
        # Si EfficientNet dit "normal" → faux positif YOLO confirmé
        is_polyp   = predicted_class in POLYP_CLASSES
        polyp_type = predicted_class if is_polyp else None
        action     = "verified_and_classified"

    else:
        # Zone >90% : YOLO très confiant → on classifie directement
        # EfficientNet ne vérifie plus le "vrai/faux" mais donne le type
        # Si EfficientNet dit quand même "normal" (cas rare), on garde "polype_1s" par défaut
        if predicted_class in POLYP_CLASSES:
            polyp_type = predicted_class
        else:
            # Prendre le type de polype avec la plus haute proba parmi les classes polype
            polyp_probs = {
                cls: all_probabilities[cls]
                for cls in CLASS_NAMES if cls in POLYP_CLASSES
            }
            polyp_type = max(polyp_probs, key=polyp_probs.get)
        is_polyp = True
        action   = "directly_classified"

    polyp_label = POLYP_LABELS.get(polyp_type or "normal", polyp_type or "normal")

    logger.info(
        "YOLO=%.0f%% (%s) → EfficientNet=%s (%.0f%%) → is_polyp=%s type=%s",
        yolo_confidence * 100, yolo_zone,
        predicted_class, confidence.item() * 100,
        is_polyp, polyp_type
    )

    return PredictionResponse(
        is_polyp=is_polyp,
        polyp_type=polyp_type,
        polyp_label=polyp_label,
        confidence=round(confidence.item(), 4),
        all_probabilities=all_probabilities,
        yolo_confidence=round(yolo_confidence, 4),
        yolo_zone=yolo_zone,
        action=action,
    )


@app.get("/")
def root():
    return {
        "message": "medet API v3 — classification fine des polypes",
        "docs":    "/docs",
        "health":  "/health",
        "version": "3.0.0",
        "polyp_types": POLYP_LABELS,
    }
