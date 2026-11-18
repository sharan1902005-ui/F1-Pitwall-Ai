"""Read-only APIs for real, provider-sourced F1 reference data."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.f1_reference import F1CircuitEventDetailRead, F1CircuitEventRead, F1CircuitRead, F1ConstructorRead, F1DriverConstructorSeasonRead, F1DriverRead, F1HistoricalAnalyticsRead, F1HistoricalLapTimeRead, F1HistoricalPerformanceAnalyticsRead, F1HistoricalPitStopRead, F1HistoricalResultRead, F1HistoricalSeasonSummary, F1HistoricalStrategyBenchmarkRead, F1HistoricalWeatherObservationRead, F1HistoricalWeatherSummaryRead, F1LapAnalyticsRead, F1PerformanceAnalyticsRead, F1PitStopAnalyticsRead, F1QualifyingAnalyticsRead, F1QualifyingResultRead, F1SeasonAnalyticsRead, F1StartingGridRead
from app.services.historical_strategy_benchmark import HistoricalStrategyBenchmarkService
from app.services.f1_reference_service import F1ReferenceNotFoundError, F1ReferenceService
from app.services.f1_historical_analytics import F1HistoricalAnalyticsService
from app.services.f1_weather_service import F1WeatherReferenceService

router = APIRouter(prefix="/api/f1-data", tags=["f1-reference-data"])
service = F1ReferenceService()
weather_service = F1WeatherReferenceService()
analytics_service = F1HistoricalAnalyticsService()
benchmark_service = HistoricalStrategyBenchmarkService()

@router.get("/strategy-benchmark", response_model=F1HistoricalStrategyBenchmarkRead)
def historical_strategy_benchmark(season:int|None=Query(default=None,ge=1950),event_id:int|None=Query(default=None,gt=0),circuit_id:int|None=Query(default=None,gt=0),db:Session=Depends(get_db))->F1HistoricalStrategyBenchmarkRead:
    return F1HistoricalStrategyBenchmarkRead(**benchmark_service.benchmark(db,season,event_id,circuit_id))


@router.get("/drivers", response_model=list[F1DriverRead])
def list_drivers(search: str | None = Query(default=None, max_length=100), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1DriverRead]:
    return service.list_drivers(db, search, limit, offset)


@router.get("/drivers/{driver_id}", response_model=F1DriverRead)
def get_driver(driver_id: int, db: Session = Depends(get_db)) -> F1DriverRead:
    try:
        return service.get_driver(driver_id, db)
    except F1ReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/analytics/drivers/{driver_id}", response_model=F1PerformanceAnalyticsRead)
def driver_analytics(driver_id: int, season: int | None = Query(default=None, ge=1950), db: Session = Depends(get_db)) -> F1PerformanceAnalyticsRead:
    try: service.get_driver(driver_id, db); return F1PerformanceAnalyticsRead(**analytics_service.driver(db, driver_id, season))
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/drivers/{driver_id}/historical-results", response_model=list[F1HistoricalResultRead])
def driver_historical_results(driver_id: int, season: int | None = Query(default=None, ge=1950), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1HistoricalResultRead]:
    try:
        service.get_driver(driver_id, db)
    except F1ReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service.results(db, None, driver_id, None, None, None, limit, offset, season)


@router.get("/drivers/{driver_id}/qualifying", response_model=list[F1QualifyingResultRead])
def driver_qualifying_history(driver_id: int, season: int = Query(ge=1950), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1QualifyingResultRead]:
    try:
        service.get_driver(driver_id, db)
    except F1ReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service.qualifying(season, db, None, driver_id, limit, offset)


@router.get("/constructors", response_model=list[F1ConstructorRead])
def list_constructors(search: str | None = Query(default=None, max_length=100), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1ConstructorRead]:
    return service.list_constructors(db, search, limit, offset)


@router.get("/constructors/{constructor_id}", response_model=F1ConstructorRead)
def get_constructor(constructor_id: int, db: Session = Depends(get_db)) -> F1ConstructorRead:
    try:
        return service.get_constructor(constructor_id, db)
    except F1ReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/analytics/constructors/{constructor_id}", response_model=F1PerformanceAnalyticsRead)
def constructor_analytics(constructor_id: int, season: int | None = Query(default=None, ge=1950), db: Session = Depends(get_db)) -> F1PerformanceAnalyticsRead:
    try: service.get_constructor(constructor_id, db); return F1PerformanceAnalyticsRead(**analytics_service.constructor(db, constructor_id, season))
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/constructors/{constructor_id}/historical-results", response_model=list[F1HistoricalResultRead])
def constructor_historical_results(constructor_id: int, season: int | None = Query(default=None, ge=1950), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1HistoricalResultRead]:
    try:
        service.get_constructor(constructor_id, db)
    except F1ReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service.results(db, None, None, constructor_id, None, None, limit, offset, season)


@router.get("/seasons/{season}/drivers", response_model=list[F1DriverRead])
def season_drivers(season: int, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1DriverRead]:
    return service.drivers_by_season(season, db, limit, offset)


@router.get("/seasons/{season}/constructors", response_model=list[F1ConstructorRead])
def season_constructors(season: int, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1ConstructorRead]:
    return service.constructors_by_season(season, db, limit, offset)


@router.get("/seasons/{season}/driver-constructor-associations", response_model=list[F1DriverConstructorSeasonRead])
def season_associations(season: int, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1DriverConstructorSeasonRead]:
    return service.associations(season, db, limit, offset)


@router.get("/seasons/{season}/events", response_model=list[F1CircuitEventDetailRead])
def season_events(season: int, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1CircuitEventDetailRead]:
    return service.events_by_season(season, db, limit, offset)


@router.get("/events/{event_id}", response_model=F1CircuitEventDetailRead)
def get_event(event_id: int, db: Session = Depends(get_db)) -> F1CircuitEventDetailRead:
    try:
        return service.get_event(event_id, db)
    except F1ReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/circuits", response_model=list[F1CircuitRead])
def list_imported_circuits(search: str | None = Query(default=None, max_length=100), country: str | None = Query(default=None, max_length=120), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1CircuitRead]:
    return service.list_circuits(db, search, country, limit, offset)


@router.get("/circuits/provider/{provider_circuit_id}", response_model=F1CircuitRead)
def get_imported_circuit_by_provider_id(provider_circuit_id: str, db: Session = Depends(get_db)) -> F1CircuitRead:
    try: return service.get_circuit_by_provider_id(provider_circuit_id, db)
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/circuits/{circuit_id}", response_model=F1CircuitRead)
def get_imported_circuit(circuit_id: int, db: Session = Depends(get_db)) -> F1CircuitRead:
    try: return service.get_circuit(circuit_id, db)
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/circuits/{circuit_id}/events", response_model=list[F1CircuitEventRead])
def get_imported_circuit_events(circuit_id: int, season: int | None = Query(default=None, ge=1950), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1CircuitEventRead]:
    try: return service.circuit_events(circuit_id, db, season, limit, offset)
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/historical-results/seasons", response_model=list[F1HistoricalSeasonSummary])
def list_result_seasons(db: Session = Depends(get_db)) -> list[F1HistoricalSeasonSummary]:
    return [F1HistoricalSeasonSummary(season=season, events=events, results=results) for season, events, results in service.result_seasons(db)]


@router.get("/historical-results/events", response_model=list[F1CircuitEventRead])
def list_result_events(season: int = Query(ge=1950), db: Session = Depends(get_db)) -> list[F1CircuitEventRead]:
    return service.result_events(season, db)


@router.get("/historical-results", response_model=list[F1HistoricalResultRead])
def list_historical_results(season: int | None = Query(default=None, ge=1950), event_id: int | None = Query(default=None, gt=0), driver_id: int | None = Query(default=None, gt=0), constructor_id: int | None = Query(default=None, gt=0), circuit_id: int | None = Query(default=None, gt=0), search: str | None = Query(default=None, max_length=100), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1HistoricalResultRead]:
    return service.results(db, event_id, driver_id, constructor_id, circuit_id, search, limit, offset, season)


@router.get("/historical-results/analytics/{season}", response_model=F1HistoricalAnalyticsRead)
def historical_analytics(season: int, driver_id: int | None = Query(default=None, gt=0), constructor_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> F1HistoricalAnalyticsRead:
    return F1HistoricalAnalyticsRead(**service.result_analytics(season, db, driver_id, constructor_id))


@router.get("/qualifying", response_model=list[F1QualifyingResultRead])
def list_qualifying(season: int = Query(ge=1950), event_id: int | None = Query(default=None, gt=0), driver_id: int | None = Query(default=None, gt=0), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1QualifyingResultRead]:
    return service.qualifying(season, db, event_id, driver_id, limit, offset)


@router.get("/qualifying/analytics/{season}", response_model=F1QualifyingAnalyticsRead)
def qualifying_analytics(season: int, driver_id: int | None = Query(default=None, gt=0), constructor_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> F1QualifyingAnalyticsRead:
    return F1QualifyingAnalyticsRead(**service.qualifying_analytics(season, db, driver_id, constructor_id))


@router.get("/starting-grids/{event_id}", response_model=list[F1StartingGridRead])
def starting_grid(event_id: int, db: Session = Depends(get_db)) -> list[F1StartingGridRead]:
    try: return service.grids(event_id, db)
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/lap-times/{event_id}", response_model=list[F1HistoricalLapTimeRead])
def lap_times(event_id: int, driver_id: int | None = Query(default=None, gt=0), lap_from: int | None = Query(default=None, gt=0), lap_to: int | None = Query(default=None, gt=0), limit: int = Query(default=200, ge=1, le=500), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1HistoricalLapTimeRead]:
    if lap_from is not None and lap_to is not None and lap_from > lap_to: raise HTTPException(status_code=422, detail="lap_from cannot exceed lap_to")
    try: return service.lap_times(event_id, db, driver_id, lap_from, lap_to, limit, offset)
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/pit-stops/{event_id}", response_model=list[F1HistoricalPitStopRead])
def pit_stops(event_id: int, driver_id: int | None = Query(default=None, gt=0), limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[F1HistoricalPitStopRead]:
    try: return service.pit_stops(event_id, db, driver_id, limit, offset)
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/performance/analytics/{event_id}", response_model=F1HistoricalPerformanceAnalyticsRead)
def performance_analytics(event_id: int, driver_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> F1HistoricalPerformanceAnalyticsRead:
    try: return F1HistoricalPerformanceAnalyticsRead(**service.performance_analytics(event_id, db, driver_id))
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/analytics/events/{event_id}/laps", response_model=F1LapAnalyticsRead)
def lap_analytics(event_id: int, driver_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> F1LapAnalyticsRead:
    try: return F1LapAnalyticsRead(**analytics_service.lap(db,event_id,driver_id))
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/analytics/events/{event_id}/pit-stops", response_model=F1PitStopAnalyticsRead)
def pit_analytics(event_id: int, driver_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> F1PitStopAnalyticsRead:
    try: return F1PitStopAnalyticsRead(**analytics_service.pit(db,event_id,driver_id))
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/analytics/seasons/{season}", response_model=F1SeasonAnalyticsRead)
def season_analytics(season: int, db: Session = Depends(get_db)) -> F1SeasonAnalyticsRead:
    return F1SeasonAnalyticsRead(**analytics_service.season(db,season))


@router.get("/historical-weather", response_model=list[F1HistoricalWeatherObservationRead])
def list_historical_weather(
    event_id: int = Query(gt=0),
    session_key: int | None = Query(default=None, gt=0),
    observed_from: datetime | None = Query(default=None),
    observed_to: datetime | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[F1HistoricalWeatherObservationRead]:
    if observed_from is not None and observed_to is not None and observed_from > observed_to:
        raise HTTPException(status_code=422, detail="observed_from cannot exceed observed_to")
    return weather_service.observations(db, event_id, session_key, observed_from, observed_to, limit, offset)


@router.get("/historical-weather/events/{event_id}/summary", response_model=F1HistoricalWeatherSummaryRead)
def historical_weather_summary(event_id: int, session_key: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> F1HistoricalWeatherSummaryRead:
    return F1HistoricalWeatherSummaryRead(**weather_service.summary(db, event_id, session_key))


@router.get("/historical-weather/events/{event_id}/temperature-trends", response_model=list[F1HistoricalWeatherObservationRead])
def historical_temperature_trends(event_id: int, session_key: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> list[F1HistoricalWeatherObservationRead]:
    return weather_service.observations(db, event_id, session_key, None, None, 2000, 0)


@router.get("/historical-weather/events/{event_id}/rainfall", response_model=list[F1HistoricalWeatherObservationRead])
def historical_rainfall(event_id: int, session_key: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> list[F1HistoricalWeatherObservationRead]:
    return [row for row in weather_service.observations(db, event_id, session_key, None, None, 2000, 0) if row.rainfall is True]


@router.get("/historical-results/{result_id}", response_model=F1HistoricalResultRead)
def get_historical_result(result_id: int, db: Session = Depends(get_db)) -> F1HistoricalResultRead:
    try: return service.get_result(result_id, db)
    except F1ReferenceNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
