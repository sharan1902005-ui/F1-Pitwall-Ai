"""Database session setup for PitWall AI."""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)


def enable_sqlite_foreign_keys(target: Engine) -> None:
    """Enable SQLite's opt-in FK checks for runtime and disposable test engines."""
    if target.dialect.name != "sqlite":
        return

    @event.listens_for(target, "connect")
    def _set_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


enable_sqlite_foreign_keys(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db(seed: bool = True) -> None:
    """Create development tables and optionally seed default data."""
    from app.models import historical  # noqa: F401
    from app.models import f1_reference  # noqa: F401
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
