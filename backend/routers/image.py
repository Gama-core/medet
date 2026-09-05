"""Route POST /predict/image."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from models.schemas import PredictionResponse
from services.pipeline import run_pipeline_on_image
from utils.helpers import YOLO_LOW, read_pil_image, validate_image_upload

router = APIRouter(prefix="/predict", tags=["image"])


@router.post("/image", response_model=PredictionResponse)
async def predict_image(file: UploadFile = File(...)):
    """Analyse une image unique (JPG/PNG)."""
    validate_image_upload(file)
    image = await read_pil_image(file)

    prediction = run_pipeline_on_image(image)
    if prediction is None:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune detection au-dessus du seuil ({YOLO_LOW:.0%}) ou faux positif evident.",
        )
    return prediction