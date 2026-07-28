"""Route POST /predict/webcam."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from models.schemas import PredictionResponse
from services.pipeline import run_pipeline_on_image
from utils.helpers import YOLO_LOW, read_pil_image, validate_image_upload

router = APIRouter(prefix="/predict", tags=["webcam"])


@router.post("/webcam", response_model=PredictionResponse)
async def predict_webcam(file: UploadFile = File(...)):
    """
    Analyse une frame unique envoyee par le client (webcam locale cote client,
    postee frame par frame ou a intervalle regulier). Meme pipeline que
    /predict/image ; endpoint distinct pour un routage/logging clair cote client.
    """
    validate_image_upload(file)
    image = await read_pil_image(file)

    prediction = run_pipeline_on_image(image)
    if prediction is None:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune detection au-dessus du seuil ({YOLO_LOW:.0%}) ou faux positif evident.",
        )
    return prediction
