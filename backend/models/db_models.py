"""Modele ORM (SQLAlchemy) — enregistrement anonyme d'un examen."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from database import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class Record(Base):
    """
    Un enregistrement = le resultat d'une analyse (image, video, webcam ou
    flux), rattache a AUCUNE identite reelle. `reference_label` est un texte
    libre choisi par le medecin pour se reperer (ex: "Salle 2 - matin"),
    jamais un nom ou identifiant patient.
    """

    __tablename__ = "records"

    id = Column(String, primary_key=True, default=_generate_uuid)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source_type = Column(String, nullable=False)  # image / video / webcam / stream
    reference_label = Column(String, nullable=True)  # libelle libre, non identifiant
    notes = Column(Text, nullable=True)  # notes libres du medecin

    # Resume et segments serialises en JSON (texte)
    summary_json = Column(Text, nullable=False)  # ex: {"1s": 3, "2": 1}
    segments_json = Column(Text, nullable=False)  # liste de segments (voir schemas.SegmentResult)

    # Partage entre pairs
    share_token = Column(String, unique=True, nullable=True, index=True)
    share_enabled = Column(Boolean, default=False, nullable=False)