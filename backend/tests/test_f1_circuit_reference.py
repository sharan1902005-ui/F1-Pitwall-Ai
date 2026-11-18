"""Tests for real circuit reference persistence and APIs."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.f1_reference import F1Circuit, F1CircuitEvent
from app.services.f1_ingestion import F1Dataset, F1IngestionEngine, IngestionRequest
from app.services.f1_reference_service import F1ReferenceImportService


class CircuitClient:
    provider_name = "jolpica"
    def __init__(self) -> None:
        self.circuits = [{"circuitId": "monza", "circuitName": "Autodromo Nazionale Monza", "url": "https://example.test/monza", "Location": {"lat": "45.6156", "long": "9.2811", "locality": "Monza", "country": "Italy"}}]
        self.results = [{"season": "2024", "round": "16", "raceName": "Italian Grand Prix", "date": "2024-09-01", "Circuit": {"circuitId": "monza", "circuitName": "Autodromo Nazionale Monza", "Location": {"country": "Italy"}}, "Results": []}, {"season": "2024", "round": "17", "raceName": "Monza Historic Event", "date": "2024-09-08", "Circuit": {"circuitId": "monza", "circuitName": "Autodromo Nazionale Monza", "Location": {"country": "Italy"}}, "Results": []}]
    def list_circuits(self): return self.circuits
    def list_race_results(self, season, round_number=None): return self.results
    def list_seasons(self): return []
    def list_drivers(self): return []
    def list_constructors(self): return []
    def list_qualifying_results(self, season, round_number=None): return []
    def list_laps(self, season, round_number): return []
    def list_pit_stops(self, season, round_number): return []


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try: yield session
    finally: session.close()


def test_circuit_import_persists_metadata_and_multiple_events(db_session: Session) -> None:
    result = F1ReferenceImportService().import_circuit_data(CircuitClient(), db_session, season=2024)
    circuit = db_session.scalar(select(F1Circuit))
    assert result["circuits"] == 1 and result["events"] == 2
    assert circuit is not None and circuit.city == "Monza" and circuit.latitude == pytest.approx(45.6156)
    assert len(db_session.scalars(select(F1CircuitEvent)).all()) == 2


def test_repeated_circuit_import_and_provider_id_lookup_are_safe(db_session: Session) -> None:
    service, client = F1ReferenceImportService(), CircuitClient()
    service.import_circuit_data(client, db_session, season=2024)
    again = service.import_circuit_data(client, db_session, season=2024)
    assert again["events"] == 0
    assert len(db_session.scalars(select(F1Circuit)).all()) == 1


def test_invalid_coordinates_and_identifiers_are_rejected() -> None:
    client = CircuitClient()
    client.circuits = [{"circuitId": "", "circuitName": "Broken", "Location": {"lat": "99", "country": "Test"}}]
    report = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.CIRCUITS,))).reports[F1Dataset.CIRCUITS]
    assert report.rejected == 1


def test_circuit_apis_search_filter_events_and_not_found(db_session: Session) -> None:
    F1ReferenceImportService().import_circuit_data(CircuitClient(), db_session, season=2024)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        circuits = client.get("/api/f1-data/circuits?search=Monza&country=Italy")
        assert circuits.status_code == 200 and circuits.json()[0]["provider_circuit_id"] == "monza"
        circuit_id = circuits.json()[0]["id"]
        assert len(client.get(f"/api/f1-data/circuits/{circuit_id}/events?season=2024").json()) == 2
        assert client.get("/api/f1-data/circuits/provider/monza").status_code == 200
        assert client.get("/api/f1-data/circuits/999999").status_code == 404
    finally: app.dependency_overrides.clear()
