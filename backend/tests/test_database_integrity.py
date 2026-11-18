"""Integrity guarantees for provider-backed reference persistence."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, enable_sqlite_foreign_keys
from app.models.f1_reference import F1CircuitEvent, F1HistoricalRaceResult
from app.services.f1_reference_service import F1ReferenceImportService
from tests.test_f1_reference_data import ReferenceClient


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_foreign_keys_reject_orphans_and_rollback_keeps_existing_rows(db_session: Session) -> None:
    service = F1ReferenceImportService()
    service.import_historical_results(ReferenceClient(), db_session, 2023)
    before = len(db_session.scalars(select(F1HistoricalRaceResult)).all())
    db_session.add(F1HistoricalRaceResult(source="jolpica", event_id=9999, driver_id=9999, constructor_id=9999))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert len(db_session.scalars(select(F1HistoricalRaceResult)).all()) == before


def test_repeat_import_preserves_existing_profile_and_historical_result(db_session: Session) -> None:
    service, initial = F1ReferenceImportService(), ReferenceClient()
    initial.list_circuits = lambda: [{"circuitId": "test", "circuitName": "Test Circuit", "Location": {"country": "Test"}}]  # type: ignore[method-assign]
    initial.drivers[0]["givenName"] = "Original"
    service.import_historical_results(initial, db_session, 2023)
    changed = ReferenceClient()
    changed.list_circuits = lambda: [{"circuitId": "test", "circuitName": "Test Circuit", "Location": {"country": "Test"}}]  # type: ignore[method-assign]
    changed.drivers[0]["givenName"] = "Changed By Provider"
    service.import_historical_results(changed, db_session, 2023)
    event = db_session.scalar(select(F1CircuitEvent)); result = db_session.scalar(select(F1HistoricalRaceResult))
    assert event is not None and result is not None
    assert result.driver.given_name == "Original"
    assert len(db_session.scalars(select(F1HistoricalRaceResult)).all()) == 1
