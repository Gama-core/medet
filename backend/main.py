"""
Backend FastAPI v3 — medet
Pipeline hybride YOLO + EfficientNet avec classification fine des polypes
=========================================================================

Nouvelle architecture :
- Score YOLO < 50%       -> ignore
- Score YOLO 50% - 90%  -> EfficientNet verifie (vrai polype ?) + classifie le type
- Score YOLO > 90%       -> classifie directement le type (1p / 1s / 2 / 3)

Modeles :
- weights/yolo_best.pt                  : YOLO detection
- weights/efficientnet_etage2.pt : classification (mauvaise_preparation / mici / normal / polype)
- weights/efficientnet_polyp_types.pt   : classification type - 4 classes (1p/1s/2/3)
"""

import io
import logging
import os

import torch
import torch.nn as nn
from fastapi import FastAPI, File, HTTPException, UploadFile
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

YOLO_WEIGHTS_PATH   = "weights/yolo_best.pt"
BINARY_WEIGHTS_PATH = "weights/efficientnet_etage2.pt"
TYPE_WEIGHTS_PATH   = "weights/efficientnet_polyp_types.pt"


TYPE_CLASSES = ["1p", "1s", "2", "3"]
BINARY_CLASSES = [
    "mauvaise_preparation",   
    "mici",                   
    "normal",                 
    "polype"                  
]

POLYP_LABELS = {
    "1p": "Polype pédiculé (1p)",
    "1s": "Polype sessile (1s)",
    "2": "Lésion plane (2)",
    "3": "Lésion ulcérée (3)",

    "normal": "Pas de polype",
    "mici": "MICI",
    "mauvaise_preparation": "Mauvaise préparation",
}

YOLO_LOW  = 0.50
YOLO_HIGH = 0.90

device = torch.device("cpu")

# Transform commun aux deux EfficientNet
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# -------------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    is_polyp:          bool
    polyp_type:        str | None
    polyp_label:       str
    confidence:        float
    all_probabilities: dict[str, float]
    yolo_confidence:   float
    yolo_zone:         str
    action:            str


class HealthResponse(BaseModel):
    status:        str
    yolo_loaded:   bool
    binary_loaded: bool
    type_loaded:   bool
    device:        str
    version:       str


# -------------------------------------------------------------------------
# Chargement des modeles
# -------------------------------------------------------------------------

yolo_model   = None
binary_model = None
type_model   = None


def load_models():
    global yolo_model, binary_model, type_model

    # YOLO
    try:
        if os.path.exists(YOLO_WEIGHTS_PATH):
            yolo_model = YOLO(YOLO_WEIGHTS_PATH)
            logger.info("YOLO charge : %s", YOLO_WEIGHTS_PATH)
        else:
            logger.warning("YOLO poids introuvables : %s", YOLO_WEIGHTS_PATH)
    except Exception:
        logger.exception("Erreur chargement YOLO")

    # EfficientNet Etage 2
    # normal / polype / mici / mauvaise_preparation
    print("===================================")
    print("Chemin :", BINARY_WEIGHTS_PATH)
    print("Existe ?", os.path.exists(BINARY_WEIGHTS_PATH))
    print("===================================")

    try:
        eff_binary = models.efficientnet_b0(weights=None)

        eff_binary.classifier[1] = nn.Linear(
            eff_binary.classifier[1].in_features,
            4
        )

        state = torch.load(BINARY_WEIGHTS_PATH, map_location="cpu")

        print(type(state))

        if isinstance(state, dict):
            print(state.keys())

        eff_binary.load_state_dict(state)
        eff_binary.to(device)
        eff_binary.eval()

        binary_model = eff_binary
        logger.info("EfficientNet Etage2 chargé.")
        print("MODELE BINAIRE CHARGE")

    except Exception as e:
        print(e)
    # EfficientNet types (1p / 1s / 2 / 3)
    try:
        if os.path.exists(TYPE_WEIGHTS_PATH):
            eff_types = models.efficientnet_b0(weights=None)
            eff_types.classifier[1] = nn.Linear(
                eff_types.classifier[1].in_features, 4
            )
            eff_types.load_state_dict(
                torch.load(TYPE_WEIGHTS_PATH, map_location="cpu")
            )
            eff_types.to(device).eval()
            type_model = eff_types
            logger.info("EfficientNet types charge.")
        else:
            logger.warning("Poids types introuvables : %s", TYPE_WEIGHTS_PATH)
    except Exception:
        logger.exception("Erreur chargement EfficientNet types")


# -------------------------------------------------------------------------
# Application FastAPI
# -------------------------------------------------------------------------

app = FastAPI(
    title="medet — Classification fine des polypes",
    description=(
        "Pipeline hybride YOLO + EfficientNet v3.\n\n"
        "YOLO < 50%  : ignore\n"
        "YOLO 50-90% : verifie + classifie le type\n"
        "YOLO > 90%  : classifie directement le type\n\n"
        "Types : 1p (pediculé), 1s (sessile), 2 (plan), 3 (ulcere)"
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
    load_models()


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        yolo_loaded=yolo_model is not None,
        binary_loaded=binary_model is not None,
        type_loaded=type_model is not None,
        device=str(device),
        version="3.0.0",
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    """
    Recoit une image, applique YOLO puis EfficientNet selon la zone de confiance.

    Zone YOLO < 50%       : HTTPException 400 (ne devrait pas etre appele)
    Zone YOLO 50% - 90%   : verifie vrai/faux polype + classifie le type
    Zone YOLO > 90%       : classifie directement le type
    """
    # Verification des modeles
    if yolo_model is None:
        raise HTTPException(status_code=503, detail="YOLO non charge.")
    if type_model is None:
        raise HTTPException(status_code=503, detail="EfficientNet types non charge.")

    # Verification du fichier
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit etre une image (jpg, png...).",
        )

    # Lecture de l'image
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de lire l'image.")

    # ---------------------------------------------------------------
    # Etage 1 : YOLO
    # ---------------------------------------------------------------
    results = yolo_model.predict(source=image, conf=YOLO_LOW, verbose=False)

    if len(results[0].boxes) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune detection YOLO au-dessus du seuil ({YOLO_LOW:.0%})."
        )

    # Boite la plus confiante
    box             = max(results[0].boxes, key=lambda b: float(b.conf[0]))
    yolo_confidence = float(box.conf[0])
    x1, y1, x2, y2 = map(int, box.xyxy[0])

    # Filtrer les boites qui couvrent plus de 60% de l'image (faux positif evident)
    W_img, H_img = image.size
    box_area  = (x2 - x1) * (y2 - y1)
    img_area  = W_img * H_img
    if box_area / img_area > 0.60:
        raise HTTPException(
            status_code=400,
            detail="Boite de detection trop grande (> 60% image) — faux positif ignore."
        )

    # Recadrer la region detectee par YOLO pour EfficientNet
    roi        = image.crop((x1, y1, x2, y2))
    img_tensor = transform(roi).unsqueeze(0).to(device)

    # ---------------------------------------------------------------
    # Determination de la zone YOLO
    # ---------------------------------------------------------------
    yolo_zone = "uncertain" if yolo_confidence < YOLO_HIGH else "high"

    # ---------------------------------------------------------------
    # Zone incertaine (50% - 90%) : verification binaire puis type
    # ---------------------------------------------------------------
    if yolo_zone == "uncertain":

        # Etape 1 : verification normal / polype
        if binary_model is None:
            raise HTTPException(
                status_code=503,
                detail="EfficientNet binaire non charge (necessaire pour zone incertaine)."
            )

        with torch.no_grad():
            binary_out   = binary_model(img_tensor)
            binary_probs = torch.softmax(binary_out, dim=1)[0]
            binary_pred = binary_probs.argmax().item()
            predicted = BINARY_CLASSES[binary_pred]

        if predicted != "polype":

            return PredictionResponse(
                is_polyp=False,
                polyp_type=None,
                polyp_label=POLYP_LABELS.get(predicted, predicted),
                confidence=round(binary_probs[binary_pred].item(),4),
                all_probabilities={
                    c: round(p.item(),4)
                    for c,p in zip(BINARY_CLASSES,binary_probs)
                },
                yolo_confidence=round(yolo_confidence,4),
                yolo_zone=yolo_zone,
                action="verified_and_classified",
            )

        # 1 = vrai polype -> classifier le type
        with torch.no_grad():
            type_out = type_model(img_tensor)

        action = "verified_and_classified"

    # ---------------------------------------------------------------
    # Zone haute confiance (> 90%) : classification directe du type
    # ---------------------------------------------------------------
    else:
        with torch.no_grad():
            type_out = type_model(img_tensor)

        action = "directly_classified"

    # ---------------------------------------------------------------
    # Classification du type (commune aux deux zones)
    # ---------------------------------------------------------------
    type_probs  = torch.softmax(type_out, dim=1)[0]
    conf, idx   = torch.max(type_probs, dim=0)
    polyp_type  = TYPE_CLASSES[idx.item()]

    all_probabilities = {
        cls: round(prob.item(), 4)
        for cls, prob in zip(TYPE_CLASSES, type_probs)
    }

    logger.info(
        "YOLO=%.0f%% (%s) -> type=%s (%.0f%%) action=%s",
        yolo_confidence * 100, yolo_zone,
        polyp_type, conf.item() * 100, action
    )

    return PredictionResponse(
        is_polyp=True,
        polyp_type=polyp_type,
        polyp_label=POLYP_LABELS[polyp_type],
        confidence=round(conf.item(), 4),
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
