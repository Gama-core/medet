"""
Routes de gestion des enregistrements anonymes (historique des examens
recents) et de leur partage entre confreres.

Confidentialite : ces endpoints ne manipulent jamais d'identite reelle de
patient — voir services/records_service.py pour le detail.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import RecordCreate, RecordDetail, RecordSummary, ShareResponse
from services import records_service

router = APIRouter(tags=["records"])


@router.post("/records", response_model=RecordDetail)
def create_record(payload: RecordCreate, db: Session = Depends(get_db)):
    """Enregistre le resultat d'un examen (segments detectes) dans l'historique."""
    return records_service.create_record(db, payload)


@router.get("/records", response_model=list[RecordSummary])
def list_records(limit: int = 50, db: Session = Depends(get_db)):
    """Liste les examens recents (vue allegee, pour l'ecran d'accueil de l'app)."""
    return records_service.list_recent_records(db, limit=limit)


@router.get("/records/{record_id}", response_model=RecordDetail)
def get_record(record_id: str, db: Session = Depends(get_db)):
    """Detail complet d'un examen (tous les segments)."""
    return records_service.get_record(db, record_id)


@router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: str, db: Session = Depends(get_db)):
    """Supprime definitivement un enregistrement."""
    records_service.delete_record(db, record_id)


@router.post("/records/{record_id}/share", response_model=ShareResponse)
def share_record(record_id: str, db: Session = Depends(get_db)):
    """Active le partage et retourne le lien a transmettre a un confrere."""
    return records_service.enable_share(db, record_id)


@router.delete("/records/{record_id}/share", status_code=204)
def unshare_record(record_id: str, db: Session = Depends(get_db)):
    """Desactive le partage (le lien existant cesse de fonctionner)."""
    records_service.revoke_share(db, record_id)


@router.get("/shared/{token}", response_model=RecordDetail)
def view_shared_record(token: str, db: Session = Depends(get_db)):
    """
    Consultation d'un examen partage par un confrere, via le lien recu.
    Accessible sans authentification — protege uniquement par la connaissance
    du token (assez long pour ne pas etre devinable).
    """
    return records_service.get_by_share_token(db, token)
