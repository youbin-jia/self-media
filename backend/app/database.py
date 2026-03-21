# backend/app/database.py
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings


def _normalize_database_url(database_url: str) -> str:
    """Normalize SQLite file paths and ensure parent directory exists."""
    url = make_url(database_url)
    if url.drivername.startswith("sqlite"):
        database = url.database
        if database and database != ":memory:":
            db_path = Path(database)
            # Keep relative SQLite paths stable regardless of process cwd.
            if not db_path.is_absolute():
                backend_dir = Path(__file__).resolve().parents[1]
                db_path = (backend_dir / db_path).resolve()

            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path.as_posix()}"

    return database_url


engine = create_engine(
    _normalize_database_url(settings.DATABASE_URL),
    connect_args={"check_same_thread": False}  # Only for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    # Dynamically look up SessionLocal from the module to allow test overrides
    db = sys.modules[__name__].SessionLocal()
    try:
        yield db
    finally:
        db.close()
