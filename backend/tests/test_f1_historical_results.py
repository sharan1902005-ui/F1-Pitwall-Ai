"""Tests for immutable, provider-backed historical classifications."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.f1_reference import F1HistoricalRaceResult
from app.services.f1_reference_service import F1ReferenceImportService, F1ReferenceService


class ResultsClient:
    provider_name = "jolpica"
    def __init__(self) -> None:
        self.drivers = [{"driverId": "winner", "givenName": "Win", "familyName": "Driver"}, {"driverId": "retired", "givenName": "Ret", "familyName": "Driver"}]
        self.constructors = [{"constructorId": "team_one", "name": "Team One"}, {"constructorId": "team_two", "name": "Team Two"}]
        self.circuits = [{"circuitId": "test", "circuitName": "Test Circuit", "Location": {"country": "Testland"}}]
        self.results = [{"season": "2024", "round": "1", "raceName": "Test Grand Prix", "date": "2024-03-01", "Circuit": {"circuitId": "test", "circuitName": "Test Circuit", "Location": {"country": "Testland"}}, "Results": [{"Driver": {"driverId": "winner"}, "Constructor": {"constructorId": "team_one"}, "position": "1", "positionText": "1", "points": "25", "grid": "2", "laps": "50", "status": "Finished", "Time": {"millis": "5000000", "time": "1:23:20.000"}, "FastestLap": {"rank": "1", "lap": "48", "Time": {"time": "1:30.500"}, "AverageSpeed": {"speed": "210.1"}}}, {"Driver": {"driverId": "retired"}, "Constructor": {"constructorId": "team_two"}, "position": "", "positionText": "DSQ", "points": "0", "grid": "5", "laps": "49", "status": "Disqualified"}]}]
    def list_drivers(self): return self.drivers
    def list_constructors(self): return self.constructors
    def list_circuits(self): return self.circuits
    def list_race_results(self, season, round_number=None): return self.results
    def list_seasons(self): return []
    def list_qualifying_results(self, season, round_number=None): return []
    def list_laps(self, season, round_number): return []
    def list_pit_stops(self, season, round_number): return []


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine); session = sessionmaker(bind=engine)()
    try: yield session
    finally: session.close()


def test_import_preserves_results_statuses_and_optional_timing(db_session: Session) -> None:
    counts = F1ReferenceImportService().import_historical_results(ResultsClient(), db_session, 2024)
    rows = db_session.scalars(select(F1HistoricalRaceResult).order_by(F1HistoricalRaceResult.id)).all()
    assert counts["results"] == 2 and rows[0].race_time_millis == 5000000
    assert rows[0].fastest_lap_time_seconds == pytest.approx(90.5)
    assert rows[1].position is None and rows[1].position_text == "DSQ" and rows[1].status == "Disqualified"


def test_repeated_import_is_insert_only_and_analytics_use_stored_rows(db_session: Session) -> None:
    service, client = F1ReferenceImportService(), ResultsClient()
    service.import_historical_results(client, db_session, 2024)
    repeated = service.import_historical_results(client, db_session, 2024)
    analytics = F1ReferenceService().result_analytics(2024, db_session, None, None)
    assert repeated["results"] == 0 and repeated["skipped"] == 2
    assert analytics == {"season": 2024, "races_used": 1, "driver_id": None, "constructor_id": None, "wins": 1, "podiums": 1, "points": 25.0, "classified_results": 1}


def test_historical_result_apis_filter_search_and_serialize(db_session: Session) -> None:
    F1ReferenceImportService().import_historical_results(ResultsClient(), db_session, 2024)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        assert client.get("/api/f1-data/historical-results/seasons").json() == [{"season": 2024, "events": 1, "results": 2}]
        event = client.get("/api/f1-data/historical-results/events?season=2024").json()[0]
        results = client.get(f"/api/f1-data/historical-results?event_id={event['id']}&search=Win")
        assert results.status_code == 200 and results.json()[0]["driver"]["provider_driver_id"] == "winner"
        result_id = results.json()[0]["id"]
        assert client.get(f"/api/f1-data/historical-results/{result_id}").status_code == 200
        assert client.get("/api/f1-data/historical-results/analytics/2024").json()["points"] == 25.0
        driver_id = results.json()[0]["driver"]["id"]
        constructor_id = results.json()[0]["constructor"]["id"]
        assert client.get("/api/f1-data/seasons/2024/events?limit=1").json()[0]["circuit"]["provider_circuit_id"] == "test"
        assert client.get(f"/api/f1-data/events/{event['id']}").json()["race_name"] == "Test Grand Prix"
        assert len(client.get(f"/api/f1-data/drivers/{driver_id}/historical-results?season=2024").json()) == 1
        assert len(client.get(f"/api/f1-data/constructors/{constructor_id}/historical-results?season=2024").json()) == 1
        assert client.get("/api/f1-data/historical-results?season=2024&limit=1&offset=1").status_code == 200
        assert client.get("/api/f1-data/events/9999").status_code == 404
    finally: app.dependency_overrides.clear()
