"""
Configuration de la base de donnees — SQLite via SQLAlchemy.

IMPORTANT (confidentialite) : aucune donnee d'identite reelle du patient
n'est stockee (pas de nom, pas de date de naissance, pas de numero de
dossier hospitalier). Chaque enregistrement est identifie uniquement par un
UUID genere par le systeme et un libelle de reference optionnel choisi par
le medecin (ex: "Salle 2 - matin", "Examen du 19/07"), jamais une identite.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./medet_records.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Cree les tables si elles n'existent pas. A appeler au demarrage."""
    from models import db_models  # noqa: F401 (assure que le modele est enregistre)

    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency FastAPI — fournit une session DB, la ferme apres la requete."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()