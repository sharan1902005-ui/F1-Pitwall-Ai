"""Tests for provider-backed qualifying and separate starting grids."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.f1_reference import F1QualifyingResult, F1StartingGrid
from app.services.f1_reference_service import F1ReferenceImportService, F1ReferenceService


class QualifyingClient:
    provider_name = "jolpica"
    def __init__(self) -> None:
        self.drivers = [{"driverId": "driver_one", "givenName": "One", "familyName": "Driver"}, {"driverId": "driver_two", "givenName": "Two", "familyName": "Driver"}]
        self.constructors = [{"constructorId": "team", "name": "Team"}]
        self.circuits = [{"circuitId": "test", "circuitName": "Test", "Location": {"country": "Test"}}]
        base = {"season": "2024", "round": "1", "raceName": "Test GP", "date": "2024-01-01", "Circuit": {"circuitId": "test", "circuitName": "Test", "Location": {"country": "Test"}}}
        self.qualifying = [{**base, "QualifyingResults": [{"Driver": {"driverId": "driver_one"}, "Constructor": {"constructorId": "team"}, "position": "1", "Q1": "1:30.000", "Q2": "1:29.000", "Q3": "1:28.000"}, {"Driver": {"driverId": "driver_two"}, "Constructor": {"constructorId": "team"}, "position": "2"}]}]
        self.results = [{**base, "Results": [{"Driver": {"driverId": "driver_one"}, "Constructor": {"constructorId": "team"}, "position": "2", "grid": "3", "laps": "50"}, {"Driver": {"driverId": "driver_two"}, "Constructor": {"constructorId": "team"}, "position": "1", "grid": "1", "laps": "50"}]}]
    def list_drivers(self): return self.drivers
    def list_constructors(self): return self.constructors
    def list_circuits(self): return self.circuits
    def list_qualifying_results(self, season, round_number=None): return self.qualifying
    def list_race_results(self, season, round_number=None): return self.results
    def list_seasons(self): return []
    def list_laps(self, season, round_number): return []
    def list_pit_stops(self, season, round_number): return []


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine); session = sessionmaker(bind=engine)()
    try: yield session
    finally: session.close()


def test_import_keeps_qualifying_and_grid_positions_separate(db_session: Session) -> None:
    result = F1ReferenceImportService().import_qualifying_and_grids(QualifyingClient(), db_session, 2024)
    qualifying = db_session.scalars(select(F1QualifyingResult).order_by(F1QualifyingResult.position)).all(); grids = db_session.scalars(select(F1StartingGrid).order_by(F1StartingGrid.grid_position)).all()
    assert result["qualifying"] == 2 and result["grids"] == 2
    assert qualifying[0].position == 1 and qualifying[0].q3_seconds == pytest.approx(88)
    assert qualifying[1].q1_seconds is None and grids[1].grid_position == 3


def test_repeated_import_and_qualifying_analytics(db_session: Session) -> None:
    service, client = F1ReferenceImportService(), QualifyingClient()
    service.import_qualifying_and_grids(client, db_session, 2024)
    again = service.import_qualifying_and_grids(client, db_session, 2024)
    analytics = F1ReferenceService().qualifying_analytics(2024, db_session, None, None)
    assert again["qualifying"] == 0 and again["grids"] == 0
    assert analytics == {"season": 2024, "driver_id": None, "constructor_id": None, "samples": 2, "average_position": 1.5, "poles": 1, "grid_changes": 2}


def test_qualifying_and_grid_apis(db_session: Session) -> None:
    F1ReferenceImportService().import_qualifying_and_grids(QualifyingClient(), db_session, 2024)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app); qualifying = client.get("/api/f1-data/qualifying?season=2024")
        assert qualifying.status_code == 200 and qualifying.json()[0]["q3_seconds"] == 88
        event_id = qualifying.json()[0]["event"]["id"]
        assert client.get(f"/api/f1-data/starting-grids/{event_id}").json()[0]["grid_position"] == 1
        assert client.get("/api/f1-data/qualifying/analytics/2024").json()["poles"] == 1
    finally: app.dependency_overrides.clear()
