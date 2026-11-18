"""Persistence and API tests for provider-sourced drivers and constructors."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.f1_reference import F1Constructor, F1Driver, F1DriverConstructorSeason
from app.services.f1_reference_service import F1ReferenceImportService, F1ReferenceService


def _race(season: str, constructor: str = "red_bull") -> dict[str, object]:
    return {"season": season, "round": "1", "raceName": "Test Grand Prix", "date": f"{season}-03-01", "Circuit": {"circuitId": "test", "circuitName": "Test Circuit", "Location": {"country": "Test"}}, "Results": [{"Driver": {"driverId": "alex_driver"}, "Constructor": {"constructorId": constructor}, "position": "1", "grid": "1", "laps": "50"}]}


class ReferenceClient:
    provider_name = "jolpica"
    def __init__(self, season: str = "2023", constructor: str = "red_bull") -> None:
        self.drivers = [{"driverId": "alex_driver", "givenName": "Alex", "familyName": "Driver", "dateOfBirth": "1995-01-02", "nationality": "Test", "code": "ALX", "permanentNumber": "7"}]
        self.constructors = [{"constructorId": "red_bull", "name": "Red Bull"}, {"constructorId": "mclaren", "name": "McLaren"}]
        self.results = [_race(season, constructor)]
    def list_drivers(self): return self.drivers
    def list_constructors(self): return self.constructors
    def list_race_results(self, season, round_number=None): return self.results
    def list_seasons(self): return []
    def list_circuits(self): return []
    def list_qualifying_results(self, season, round_number=None): return []
    def list_laps(self, season, round_number): return []
    def list_pit_stops(self, season, round_number): return []


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_import_persists_profiles_and_association(db_session: Session) -> None:
    result = F1ReferenceImportService().import_reference_data(ReferenceClient(), db_session, season=2023)
    association = db_session.scalar(select(F1DriverConstructorSeason))
    assert result["drivers"] == 1 and result["constructors"] == 2 and result["associations"] == 1
    assert association is not None and association.season == 2023
    assert association.driver.provider_driver_id == "alex_driver"
    assert association.constructor.provider_constructor_id == "red_bull"


def test_repeated_import_is_safe(db_session: Session) -> None:
    service, client = F1ReferenceImportService(), ReferenceClient()
    service.import_reference_data(client, db_session, season=2023)
    repeated = service.import_reference_data(client, db_session, season=2023)
    assert repeated["associations"] == 0
    assert len(db_session.scalars(select(F1Driver)).all()) == 1
    assert len(db_session.scalars(select(F1Constructor)).all()) == 2
    assert len(db_session.scalars(select(F1DriverConstructorSeason)).all()) == 1


def test_driver_constructor_history_is_preserved_across_seasons(db_session: Session) -> None:
    service = F1ReferenceImportService()
    service.import_reference_data(ReferenceClient("2023", "red_bull"), db_session, season=2023)
    service.import_reference_data(ReferenceClient("2024", "mclaren"), db_session, season=2024)
    associations = db_session.scalars(select(F1DriverConstructorSeason).order_by(F1DriverConstructorSeason.season)).all()
    assert [(item.season, item.constructor.provider_constructor_id) for item in associations] == [(2023, "red_bull"), (2024, "mclaren")]


def test_optional_fields_and_invalid_identifiers(db_session: Session) -> None:
    client = ReferenceClient(); client.drivers[0].pop("code"); client.drivers[0].pop("permanentNumber")
    F1ReferenceImportService().import_reference_data(client, db_session)
    assert db_session.scalar(select(F1Driver)).code is None  # type: ignore[union-attr]
    invalid = ReferenceClient(); invalid.drivers = [{"driverId": "", "givenName": "Bad", "familyName": "Driver"}]
    result = F1ReferenceImportService().import_reference_data(invalid, db_session)
    assert result["rejected"] == 1


def test_unknown_result_profiles_do_not_create_invalid_foreign_keys(db_session: Session) -> None:
    client = ReferenceClient(); client.drivers = []
    result = F1ReferenceImportService().import_reference_data(client, db_session, season=2023)
    assert result["associations"] == 0
    assert db_session.scalar(select(F1DriverConstructorSeason)) is None


def test_reference_data_apis_validate_responses(db_session: Session) -> None:
    F1ReferenceImportService().import_reference_data(ReferenceClient(), db_session, season=2023)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client, driver = TestClient(app), db_session.scalar(select(F1Driver))
        assert driver is not None
        assert client.get("/api/f1-data/drivers?search=Alex").status_code == 200
        assert client.get(f"/api/f1-data/drivers/{driver.id}").json()["provider_driver_id"] == "alex_driver"
        assert client.get("/api/f1-data/seasons/2023/drivers").json()[0]["family_name"] == "Driver"
        assert client.get("/api/f1-data/seasons/2023/constructors").status_code == 200
        assert client.get("/api/f1-data/seasons/2023/driver-constructor-associations").json()[0]["constructor"]["provider_constructor_id"] == "red_bull"
    finally:
        app.dependency_overrides.clear()


def test_reference_lookup_service_search_and_pagination(db_session: Session) -> None:
    F1ReferenceImportService().import_reference_data(ReferenceClient(), db_session)
    service = F1ReferenceService()
    assert len(service.list_drivers(db_session, "alex", 10, 0)) == 1
    assert service.list_constructors(db_session, "missing", 10, 0) == []
