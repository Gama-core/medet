"""
Service de gestion des enregistrements anonymes (historique des examens) et
de leur partage entre pairs.

Rappel de confidentialite : aucune identite reelle n'est jamais stockee ici.
`reference_label` est un texte libre choisi par le medecin pour se reperer,
jamais un nom, une date de naissance, ou un numero de dossier hospitalier.
"""

import json
import secrets
from collections import Counter
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.db_models import Record
from models.schemas import RecordCreate, RecordDetail, RecordSummary, SegmentResult, ShareResponse


def create_record(db: Session, payload: RecordCreate) -> RecordDetail:
    summary = Counter(seg.polyp_type for seg in payload.segments if seg.polyp_type)

    record = Record(
        source_type=payload.source_type,
        reference_label=payload.reference_label,
        notes=payload.notes,
        summary_json=json.dumps(dict(summary)),
        segments_json=json.dumps([seg.model_dump() for seg in payload.segments]),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return _to_detail(record)


def list_recent_records(db: Session, limit: int = 50) -> List[RecordSummary]:
    records = (
        db.query(Record).order_by(Record.created_at.desc()).limit(limit).all()
    )
    return [_to_summary(r) for r in records]


def get_record(db: Session, record_id: str) -> RecordDetail:
    record = db.query(Record).filter(Record.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Enregistrement introuvable.")
    return _to_detail(record)


def delete_record(db: Session, record_id: str) -> None:
    record = db.query(Record).filter(Record.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Enregistrement introuvable.")
    db.delete(record)
    db.commit()


def enable_share(db: Session, record_id: str) -> ShareResponse:
    """Genere (ou renvoie) un token de partage pour un enregistrement, afin
    qu'un confrere puisse consulter ce cas via un lien, sans authentification."""
    record = db.query(Record).filter(Record.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Enregistrement introuvable.")

    if not record.share_token:
        record.share_token = secrets.token_urlsafe(24)
    record.share_enabled = True

    db.commit()
    db.refresh(record)

    return ShareResponse(
        record_id=record.id,
        share_token=record.share_token,
        share_url_path=f"/shared/{record.share_token}",
    )


def revoke_share(db: Session, record_id: str) -> None:
    record = db.query(Record).filter(Record.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Enregistrement introuvable.")
    record.share_enabled = False
    db.commit()


def get_by_share_token(db: Session, token: str) -> RecordDetail:
    """Consultation publique (par un confrere) via le lien de partage — pas
    d'authentification, mais accessible uniquement si `share_enabled` est vrai
    et que le token exact est connu."""
    record = (
        db.query(Record)
        .filter(Record.share_token == token, Record.share_enabled.is_(True))
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=404, detail="Lien de partage invalide, expire, ou desactive."
        )
    return _to_detail(record)


# -------------------------------------------------------------------------
# Conversions internes
# -------------------------------------------------------------------------


def _to_summary(record: Record) -> RecordSummary:
    summary = json.loads(record.summary_json)
    return RecordSummary(
        id=record.id,
        created_at=record.created_at.isoformat(),
        source_type=record.source_type,
        reference_label=record.reference_label,
        segment_count=sum(summary.values()) if summary else 0,
        types_detected=list(summary.keys()),
        share_enabled=record.share_enabled,
    )


def _to_detail(record: Record) -> RecordDetail:
    segments_raw = json.loads(record.segments_json)
    summary = json.loads(record.summary_json)
    return RecordDetail(
        id=record.id,
        created_at=record.created_at.isoformat(),
        source_type=record.source_type,
        reference_label=record.reference_label,
        notes=record.notes,
        segments=[SegmentResult(**s) for s in segments_raw],
        summary=summary,
        share_enabled=record.share_enabled,
        share_token=record.share_token if record.share_enabled else None,
    )