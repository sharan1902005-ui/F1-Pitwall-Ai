"""OpenF1 historical-weather client, ingestion, persistence, and API tests."""

from collections.abc import Generator
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import OpenF1Settings
from app.database import Base, get_db
from app.integrations.f1.errors import F1ProviderPayloadError, F1ProviderTimeoutError
from app.integrations.f1.openf1_weather_client import OpenF1WeatherClient
from app.main import app
from app.models.f1_reference import F1Circuit, F1CircuitEvent, F1HistoricalWeatherObservation
from app.services.f1_ingestion import F1Dataset, F1IngestionEngine, IngestionRequest
from app.services.f1_weather_service import F1WeatherImportService


def _settings(**overrides: object) -> OpenF1Settings:
    values: dict[str, object] = {"base_url": "https://openf1.test", "connect_timeout_seconds": 0.1, "read_timeout_seconds": 0.1, "retry_limit": 0, "max_retry_delay_seconds": 1.0}
    values.update(overrides)
    return OpenF1Settings(**values)  # type: ignore[arg-type]


def test_openf1_client_uses_documented_session_and_weather_routes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/sessions":
            assert request.url.params["year"] == "2024"
            return httpx.Response(200, json=[{"session_key": 9001}], request=request)
        assert request.url.path == "/v1/weather" and request.url.params["session_key"] == "9001"
        return httpx.Response(200, json=[{"date": "2024-05-05T12:00:00+00:00"}], request=request)
    client = OpenF1WeatherClient(_settings(), transport=httpx.MockTransport(handler))
    assert client.list_sessions(2024)[0]["session_key"] == 9001
    assert client.list_weather(9001)[0]["date"] == "2024-05-05T12:00:00+00:00"


def test_openf1_client_rejects_invalid_payload_and_reports_timeout() -> None:
    invalid = OpenF1WeatherClient(_settings(), transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}, request=request)))
    try:
        invalid.list_sessions(2024)
        assert False, "invalid payload must fail"
    except F1ProviderPayloadError:
        pass
    timeout = OpenF1WeatherClient(_settings(), transport=httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectTimeout("timeout", request=request))))
    try:
        timeout.list_weather(1)
        assert False, "timeout must fail"
    except F1ProviderTimeoutError:
        pass


class WeatherClient:
    provider_name = "openf1"
    def list_sessions(self, season: int):
        assert season == 2024
        return [{"session_key": 9001, "country_name": "Italy", "date_start": "2024-05-03T11:00:00+00:00"}]
    def list_weather(self, session_key: int):
        assert session_key == 9001
        return [
            {"date": "2024-05-03T11:00:00+00:00", "meeting_key": 1200, "session_key": 9001, "air_temperature": 22.5, "track_temperature": 34.2, "humidity": 55, "pressure": 1012.4, "rainfall": 0, "wind_direction": 180, "wind_speed": 2.5},
            {"date": "2024-05-03T11:01:00+00:00", "meeting_key": 1200, "session_key": 9001, "air_temperature": None, "track_temperature": 34.4, "humidity": 56, "pressure": 1012.2, "rainfall": 1, "wind_direction": 181, "wind_speed": 2.7},
        ]


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine); session = sessionmaker(bind=engine)()
    circuit = F1Circuit(source="jolpica", provider_circuit_id="monza", name="Monza", city="Monza", country="Italy", latitude=None, longitude=None, source_url=None)
    session.add(circuit); session.flush(); session.add(F1CircuitEvent(source="jolpica", circuit_id=circuit.id, season=2024, round_number=7, race_name="Italian GP", race_date=date(2024, 5, 5)))
    session.commit()
    try: yield session
    finally: session.close()


def test_weather_ingestion_normalizes_missing_values_and_persists_idempotently(db_session: Session) -> None:
    event_id = db_session.scalar(select(F1CircuitEvent.id)); assert event_id is not None
    result = F1IngestionEngine(WeatherClient()).ingest(IngestionRequest((F1Dataset.HISTORICAL_WEATHER,), session_key=9001))
    record = result.reports[F1Dataset.HISTORICAL_WEATHER].records[1]
    assert record.data["air_temperature_celsius"] is None and record.data["rainfall"] is True
    service = F1WeatherImportService()
    first, second = service.import_event_weather(WeatherClient(), db_session, event_id), service.import_event_weather(WeatherClient(), db_session, event_id)
    assert first["observations"] == 2 and second["skipped"] == 2
    assert db_session.scalar(select(F1HistoricalWeatherObservation.rainfall).where(F1HistoricalWeatherObservation.air_temperature_celsius.is_(None))) is True


def test_weather_api_filters_ranges_and_returns_summary(db_session: Session) -> None:
    event_id = db_session.scalar(select(F1CircuitEvent.id)); assert event_id is not None
    F1WeatherImportService().import_event_weather(WeatherClient(), db_session, event_id)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        observations = client.get(f"/api/f1-data/historical-weather?event_id={event_id}&session_key=9001").json()
        summary = client.get(f"/api/f1-data/historical-weather/events/{event_id}/summary").json()
        assert len(observations) == 2 and observations[0]["track_temperature_celsius"] == 34.2
        assert summary["rainfall_observations"] == 1 and summary["average_air_temperature_celsius"] == 22.5
        assert client.get(f"/api/f1-data/historical-weather?event_id={event_id}&observed_from=2024-05-04T00:00:00Z&observed_to=2024-05-03T00:00:00Z").status_code == 422
    finally: app.dependency_overrides.clear()
