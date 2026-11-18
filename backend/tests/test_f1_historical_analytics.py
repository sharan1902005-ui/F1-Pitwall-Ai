from collections.abc import Generator
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.database import Base,get_db
from app.main import app
from app.models.f1_reference import F1CircuitEvent,F1Driver
from app.services.f1_reference_service import F1ReferenceImportService
from app.services.f1_historical_analytics import F1HistoricalAnalyticsService
from app.services.historical_strategy_benchmark import HistoricalStrategyBenchmarkService
from tests.test_f1_historical_results import ResultsClient
from tests.test_f1_lap_and_pit_data import LapPitClient

def db_session() -> Generator[Session,None,None]:
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool); Base.metadata.create_all(bind=engine); session=sessionmaker(bind=engine)()
    try: yield session
    finally: session.close()

def test_driver_season_and_empty_lap_pit_analytics() -> None:
    session=next(db_session()); F1ReferenceImportService().import_historical_results(ResultsClient(),session,2024)
    driver=session.scalar(select(F1Driver).where(F1Driver.provider_driver_id=="winner")); event=session.scalar(select(F1CircuitEvent)); assert driver and event
    analytics=F1HistoricalAnalyticsService().driver(session,driver.id,2024)
    assert analytics["starts"]==1 and analytics["wins"]==1 and analytics["average_grid_to_finish_change"]==1
    assert F1HistoricalAnalyticsService().lap(session,event.id,None)["samples"]==0
    assert F1HistoricalAnalyticsService().pit(session,event.id,None)["average_duration_seconds"] is None
    session.close()

def test_analytics_routes_validate_source_backed_records() -> None:
    session=next(db_session()); F1ReferenceImportService().import_historical_results(ResultsClient(),session,2024); driver=session.scalar(select(F1Driver).where(F1Driver.provider_driver_id=="winner")); assert driver
    app.dependency_overrides[get_db]=lambda:session
    try:
        client=TestClient(app); assert client.get(f"/api/f1-data/analytics/drivers/{driver.id}?season=2024").json()["points"]==25
        assert client.get("/api/f1-data/analytics/events/999/laps").status_code==404
        assert client.get("/api/f1-data/analytics/seasons/2024").json()["imported_results"]==2
    finally: app.dependency_overrides.clear(); session.close()


def test_historical_strategy_benchmark_is_read_only_and_reports_empty_scope() -> None:
    session = next(db_session())
    importer = F1ReferenceImportService()
    importer.import_historical_results(ResultsClient(), session, 2024)
    importer.import_laps_and_pit_stops(LapPitClient(), session, 2024, 1)

    benchmark = HistoricalStrategyBenchmarkService().benchmark(session, 2024, None, None)
    assert benchmark["races_used"] == 1
    assert benchmark["result_samples"] == 2
    assert benchmark["lap_samples"] == 3
    assert benchmark["pit_stop_samples"] == 2
    assert benchmark["average_pit_stops_per_race"] == 2
    assert benchmark["average_pit_stop_duration_seconds"] == 23
    assert benchmark["average_lap_time_seconds"] == pytest.approx(90.1666666667)
    assert benchmark["average_grid_to_finish_change"] == 1

    app.dependency_overrides[get_db] = lambda: session
    try:
        client = TestClient(app)
        response = client.get("/api/f1-data/strategy-benchmark?season=2024")
        assert response.status_code == 200
        assert response.json()["source"] == "historical_imported_data"
        assert response.json()["note"].startswith("Historical benchmark only")
        event = session.scalar(select(F1CircuitEvent))
        assert event is not None
        scoped = client.get(f"/api/f1-data/strategy-benchmark?season=2024&event_id={event.id}&circuit_id={event.circuit_id}")
        assert scoped.status_code == 200
        assert scoped.json()["races_used"] == 1
        empty = client.get("/api/f1-data/strategy-benchmark?season=2023")
        assert empty.status_code == 200
        assert empty.json()["races_used"] == 0
        assert empty.json()["average_lap_time_seconds"] is None
    finally:
        app.dependency_overrides.clear()
        session.close()
