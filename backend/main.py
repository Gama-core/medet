"""
Backend FastAPI — Etage 2 (cloud) du pipeline hybride de detection de polypes
==============================================================================

Expose le modele EfficientNet (deja entraine dans Hybrid_Pipeline_YOLO_EfficientNet.ipynb)
derriere une API REST simple, appelee par l'application mobile Flutter uniquement
quand l'etage 1 (YOLO, local) a detecte une anomalie suspecte.

Pour lancer le serveur :
    pip install fastapi uvicorn torch torchvision pillow python-multipart
    uvicorn main:app --host 0.0.0.0 --port 8000

Documentation interactive auto-generee disponible sur :
    http://localhost:8000/docs
"""

import io
import logging

import torch
import torch.nn as nn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
from torchvision import models, transforms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medet-backend")

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

WEIGHTS_PATH = "weights/efficientnet_etage2.pt"

# Ordre des classes : doit correspondre exactement a celui utilise lors de
# l'entrainement (torchvision.datasets.ImageFolder trie par ordre alphabetique).
CLASS_NAMES = ["mauvaise_preparation", "mici", "normal", "polype"]

IMAGE_SIZE = (224, 224)

transform = transforms.Compose([
    transforms.Resize(IMAGE_SIZE),
    transforms.ToTensor(),
])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# -------------------------------------------------------------------------
# Schemas de reponse
# -------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    predicted_class: str
    confidence: float
    all_probabilities: dict[str, float]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str


# -------------------------------------------------------------------------
# Chargement du modele (une seule fois, au demarrage du serveur)
# -------------------------------------------------------------------------

model = None


def load_model():
    global model
    try:
        eff = models.efficientnet_b0(weights=None)
        eff.classifier[1] = nn.Linear(eff.classifier[1].in_features, len(CLASS_NAMES))
        eff.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
        eff.to(device)
        eff.eval()
        model = eff
        logger.info("Modele EfficientNet charge avec succes depuis %s", WEIGHTS_PATH)
    except FileNotFoundError:
        logger.warning(
            "Fichier de poids introuvable (%s) — le serveur démarre mais "
            "/predict renverra une erreur 503 jusqu'à ce que les poids soient "
            "ajoutés.",
            WEIGHTS_PATH,
        )
        model = None
    except Exception:
        logger.exception("Erreur lors du chargement du modele")
        model = None


# -------------------------------------------------------------------------
# Application FastAPI
# -------------------------------------------------------------------------

app = FastAPI(
    title="medet — API de classification d'anomalies digestives",
    description=(
        "Etage 2 (cloud) du pipeline hybride. Recoit une image jugee "
        "suspecte par l'etage 1 (YOLO, local) et renvoie la classe precise "
        "parmi : normal, polype, mici, mauvaise_preparation."
    ),
    version="1.0.0",
)

# CORS ouvert pour le developpement — a restreindre aux domaines autorises
# avant un passage en production.
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
    """Verifie que le serveur tourne et que le modele est bien charge."""
    return HealthResponse(
        status="ok",
        model_loaded=model is not None,
        device=str(device),
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    """
    Recoit une image et renvoie la classe predite par EfficientNet.

    A appeler uniquement lorsque l'etage 1 (YOLO, local sur l'app mobile)
    a detecte une anomalie suspecte — pas pour chaque image.
    """
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Le modele n'est pas charge. Verifiez que le fichier "
                f"'{WEIGHTS_PATH}' existe et relancez le serveur."
            ),
        )

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Le fichier envoye doit etre une image (jpg, png, ...).",
        )

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Impossible de lire l'image envoyee. Fichier corrompu ou format non supporte.",
        )

    img_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(img_tensor)
        probs = torch.softmax(outputs, dim=1)[0]

    all_probabilities = {
        cls_name: round(prob.item(), 4)
        for cls_name, prob in zip(CLASS_NAMES, probs)
    }

    confidence, pred_idx = torch.max(probs, dim=0)
    predicted_class = CLASS_NAMES[pred_idx.item()]

    logger.info(
        "Prediction: %s (confiance: %.2f%%)", predicted_class, confidence.item() * 100
    )

    return PredictionResponse(
        predicted_class=predicted_class,
        confidence=round(confidence.item(), 4),
        all_probabilities=all_probabilities,
    )


@app.get("/")
def root():
    return {
        "message": "API medet — etage 2 (cloud) du pipeline hybride de detection de polypes",
        "docs": "/docs",
        "health": "/health",
    }
