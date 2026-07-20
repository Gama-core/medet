"""Schemas Pydantic (requetes et reponses) pour l'API medet."""

from typing import Optional

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class PredictionResponse(BaseModel):
    is_polyp: bool
    polyp_type: Optional[str]
    polyp_label: str
    confidence: float
    all_probabilities: dict[str, float]
    yolo_confidence: float
    yolo_zone: str
    bounding_box: Optional[BoundingBox]
    action: str
    processing_time_ms: float


class FrameResult(BaseModel):
    frame_index: int
    timestamp_seconds: float
    prediction: Optional[PredictionResponse]


class SegmentResult(BaseModel):
    """Regroupe des frames consecutives de meme detection en un segment,
    au meme format que le rapport CSV produit par app2.py (Streamlit)."""

    start_timestamp_seconds: float
    end_timestamp_seconds: float
    duration_seconds: float
    polyp_type: Optional[str]
    polyp_label: str
    max_confidence: float
    frame_count: int


class VideoResult(BaseModel):
    total_frames_read: int
    frames_analyzed: int
    fps_source: float
    detections: list[FrameResult]
    segments: list[SegmentResult]
    processing_time_ms: float


class StreamRequest(BaseModel):
    url: str = Field(..., description="URL RTSP, HTTP ou HTTPS du flux")
    duration_seconds: int = Field(30, ge=1, le=600, description="Duree d'analyse max")
    frame_skip: int = Field(5, ge=1, le=30, description="Analyser 1 frame sur N")
    export: Optional[str] = Field(
        None, description="'csv' pour recevoir directement le rapport CSV au lieu du JSON"
    )


class StreamResult(BaseModel):
    url: str
    connected: bool
    total_frames_read: int
    frames_analyzed: int
    detections: list[FrameResult]
    segments: list[SegmentResult]
    processing_time_ms: float
    message: str


class HealthResponse(BaseModel):
    status: str
    yolo_loaded: bool
    binary_loaded: bool
    type_loaded: bool
    device: str
    version: str


# -------------------------------------------------------------------------
# Enregistrements anonymes et partage entre pairs
# -------------------------------------------------------------------------


class RecordCreate(BaseModel):
    """Creation d'un enregistrement — AUCUNE identite reelle, uniquement un
    libelle de reference libre choisi par le medecin (ex: 'Salle 2 - matin')."""

    source_type: str = Field(..., description="image / video / webcam / stream")
    reference_label: Optional[str] = Field(None, description="Libelle libre, non identifiant")
    notes: Optional[str] = None
    segments: list[SegmentResult] = Field(default_factory=list)


class RecordSummary(BaseModel):
    """Vue allegee, utilisee pour la liste des enregistrements recents."""

    id: str
    created_at: str
    source_type: str
    reference_label: Optional[str]
    segment_count: int
    types_detected: list[str]
    share_enabled: bool


class RecordDetail(BaseModel):
    """Vue complete d'un enregistrement."""

    id: str
    created_at: str
    source_type: str
    reference_label: Optional[str]
    notes: Optional[str]
    segments: list[SegmentResult]
    summary: dict[str, int]
    share_enabled: bool
    share_token: Optional[str]


class ShareResponse(BaseModel):
    record_id: str
    share_token: str
    share_url_path: str  # ex: /shared/{token} — a prefixer par le domaine cote client