"""Database session setup for PitWall AI."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db(seed: bool = True) -> None:
    """Create development tables and optionally seed default data."""
    from app.models import historical  # noqa: F401
    from app.models import season  # noqa: F401
    from app.services.data_import_service import DataImportService

    Base.metadata.create_all(bind=engine)
    if seed:
        db = SessionLocal()
        try:
            DataImportService().seed_defaults(db)
        finally:
            db.close()


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
