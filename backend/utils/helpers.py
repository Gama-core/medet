"""
Constantes partagees et fonctions utilitaires (validation d'upload, lecture
d'image, calcul de ratio de boite) utilisees par les services et routers.
"""

import io

import torch
from fastapi import HTTPException, UploadFile
from PIL import Image

# -------------------------------------------------------------------------
# Chemins des poids
# -------------------------------------------------------------------------

YOLO_WEIGHTS_PATH = "weights/yolo_best.pt"
BINARY_WEIGHTS_PATH = "weights/efficientnet_etage2.pt"
TYPE_WEIGHTS_PATH = "weights/efficientnet_polyp_types.pt"

# -------------------------------------------------------------------------
# Classes et labels
# -------------------------------------------------------------------------

TYPE_CLASSES = ["1p", "1s", "2", "3"]
BINARY_CLASSES = [
    "mauvaise_preparation",
    "mici",
    "normal",
    "polype",
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

# -------------------------------------------------------------------------
# Seuils de decision (YOLO)
# -------------------------------------------------------------------------

YOLO_LOW = 0.50
YOLO_HIGH = 0.90
MAX_BOX_AREA_RATIO = 0.60  # au-dela, boite consideree comme un faux positif evident

DEVICE = torch.device("cpu")


# -------------------------------------------------------------------------
# Validation / lecture des uploads
# -------------------------------------------------------------------------


def validate_image_upload(file: UploadFile) -> None:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, detail="Le fichier doit etre une image (jpg, png...)."
        )


def validate_video_upload(file: UploadFile) -> None:
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400, detail="Le fichier doit etre une video (mp4, avi...)."
        )


async def read_pil_image(file: UploadFile) -> Image.Image:
    try:
        image_bytes = await file.read()
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de lire l'image.")


def box_area_ratio(x1: int, y1: int, x2: int, y2: int, img_width: int, img_height: int) -> float:
    """Ratio de la surface de la boite par rapport a la surface totale de l'image."""
    box_area = (x2 - x1) * (y2 - y1)
    img_area = img_width * img_height
    if img_area <= 0:
        return 0.0
    return box_area / img_area