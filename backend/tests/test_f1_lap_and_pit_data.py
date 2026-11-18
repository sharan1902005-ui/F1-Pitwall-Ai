"""Tests for event-scoped historical lap and pit-stop observations."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.f1_reference import F1HistoricalLapTime, F1HistoricalPitStop
from app.services.f1_reference_service import F1ReferenceImportService, F1ReferenceService


class LapPitClient:
    provider_name = "jolpica"
    def __init__(self) -> None:
        self.drivers = [{"driverId": "driver_one", "givenName": "One", "familyName": "Driver"}]
        self.circuits = [{"circuitId": "test", "circuitName": "Test", "Location": {"country": "Test"}}]
        base = {"season": "2024", "round": "1", "raceName": "Test GP", "date": "2024-01-01", "Circuit": {"circuitId": "test", "circuitName": "Test", "Location": {"country": "Test"}}}
        self.results = [{**base, "Results": [{"Driver": {"driverId": "driver_one"}, "Constructor": {"constructorId": "team"}, "position": "1", "grid": "1", "laps": "3"}]}]
        self.laps = [{**base, "Laps": [{"number": "1", "Timings": [{"driverId": "driver_one", "position": "1", "time": "1:30.500"}]}, {"number": "2", "Timings": [{"driverId": "driver_one", "position": "1", "time": "1:29.000"}]}, {"number": "3", "Timings": [{"driverId": "driver_one", "position": "1", "time": "1:31.000"}]}]}]
        self.pits = [{**base, "PitStops": [{"driverId": "driver_one", "stop": "1", "lap": "2", "time": "12:30:00", "duration": "22.500"}, {"driverId": "driver_one", "stop": "2", "lap": "3", "time": "12:31:00", "duration": "23.500"}]}]
    def list_drivers(self): return self.drivers
    def list_circuits(self): return self.circuits
    def list_race_results(self, season, round_number=None): return self.results
    def list_laps(self, season, round_number): return self.laps
    def list_pit_stops(self, season, round_number): return self.pits
    def list_seasons(self): return []
    def list_constructors(self): return []
    def list_qualifying_results(self, season, round_number=None): return []


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine); session = sessionmaker(bind=engine)()
    try: yield session
    finally: session.close()


def test_import_preserves_lap_precision_and_multiple_pit_stops(db_session: Session) -> None:
    counts = F1ReferenceImportService().import_laps_and_pit_stops(LapPitClient(), db_session, 2024, 1)
    laps = db_session.scalars(select(F1HistoricalLapTime).order_by(F1HistoricalLapTime.lap_number)).all(); pits = db_session.scalars(select(F1HistoricalPitStop).order_by(F1HistoricalPitStop.stop_number)).all()
    assert counts["laps"] == 3 and counts["pit_stops"] == 2
    assert laps[0].lap_time_seconds == pytest.approx(90.5) and pits[1].duration_seconds == pytest.approx(23.5)


def test_repeated_import_pagination_and_performance_analytics(db_session: Session) -> None:
    service, client = F1ReferenceImportService(), LapPitClient(); service.import_laps_and_pit_stops(client, db_session, 2024, 1)
    again = service.import_laps_and_pit_stops(client, db_session, 2024, 1)
    event_id = db_session.scalar(select(F1HistoricalLapTime.event_id)); assert event_id is not None
    laps = F1ReferenceService().lap_times(event_id, db_session, None, 2, 3, 1, 0); analytics = F1ReferenceService().performance_analytics(event_id, db_session, None)
    assert again["laps"] == 0 and again["pit_stops"] == 0 and len(laps) == 1 and laps[0].lap_number == 2
    assert analytics == {"event_id": event_id, "driver_id": None, "lap_samples": 3, "average_lap_time_seconds": pytest.approx(90.1666666667), "fastest_lap_seconds": 89.0, "slowest_lap_seconds": 91.0, "pit_stop_samples": 2, "average_pit_stop_duration_seconds": 23.0}


def test_lap_and_pit_apis_validate_ranges_and_serialize(db_session: Session) -> None:
    F1ReferenceImportService().import_laps_and_pit_stops(LapPitClient(), db_session, 2024, 1)
    event_id = db_session.scalar(select(F1HistoricalLapTime.event_id)); assert event_id is not None
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        assert len(client.get(f"/api/f1-data/lap-times/{event_id}?lap_from=1&lap_to=3").json()) == 3
        assert client.get(f"/api/f1-data/lap-times/{event_id}?lap_from=3&lap_to=1").status_code == 422
        assert client.get(f"/api/f1-data/pit-stops/{event_id}").json()[0]["duration_seconds"] == 22.5
        assert client.get(f"/api/f1-data/performance/analytics/{event_id}").json()["fastest_lap_seconds"] == 89
    finally: app.dependency_overrides.clear()
