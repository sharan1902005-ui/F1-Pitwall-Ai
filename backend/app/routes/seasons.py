"""Championship season routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.season import (
    ChampionshipProjectionResponse,
    ConstructorStandingResponse,
    DriverStandingResponse,
    SeasonCreateRequest,
    SeasonRaceResult,
    SeasonRaceSummary,
    SeasonResponse,
    SeasonScenarioRequest,
    SeasonScenarioResponse,
    SeasonStandingsResponse,
)
from app.services.season_simulator import (
    SeasonNotFoundError,
    SeasonSimulator,
    SeasonStateError,
)


router = APIRouter(prefix="/api/seasons", tags=["seasons"])
service = SeasonSimulator()


@router.post("", response_model=SeasonResponse)
def create_season(
    request: SeasonCreateRequest,
    db: Session = Depends(get_db),
) -> SeasonResponse:
    """Create a persistent championship season."""
    try:
        return service.create_season(request, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{season_id}", response_model=SeasonResponse)
def get_season(season_id: int, db: Session = Depends(get_db)) -> SeasonResponse:
    """Return complete season state."""
    try:
        return service.get_season(season_id, db)
    except SeasonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{season_id}/standings", response_model=SeasonStandingsResponse)
def get_standings(
    season_id: int,
    db: Session = Depends(get_db),
) -> SeasonStandingsResponse:
    """Return driver and constructor standings."""
    try:
        drivers, constructors = service.standings(season_id, db)
        return SeasonStandingsResponse(drivers=drivers, constructors=constructors)
    except SeasonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{season_id}/calendar", response_model=list[SeasonRaceSummary])
def get_calendar(
    season_id: int,
    db: Session = Depends(get_db),
) -> list[SeasonRaceSummary]:
    """Return season calendar state."""
    try:
        return service.calendar(season_id, db)
    except SeasonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{season_id}/next-race", response_model=SeasonRaceResult)
def run_next_race(
    season_id: int,
    db: Session = Depends(get_db),
) -> SeasonRaceResult:
    """Run the next incomplete championship race."""
    try:
        return service.run_next_race(season_id, db)
    except SeasonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SeasonStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{season_id}/simulate", response_model=SeasonResponse)
def simulate_remaining(
    season_id: int,
    db: Session = Depends(get_db),
) -> SeasonResponse:
    """Simulate all remaining races."""
    try:
        return service.simulate_remaining(season_id, db)
    except SeasonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{season_id}/scenario", response_model=SeasonScenarioResponse)
def analyze_scenario(
    season_id: int,
    request: SeasonScenarioRequest,
    db: Session = Depends(get_db),
) -> SeasonScenarioResponse:
    """Run a non-mutating championship what-if scenario."""
    try:
        return service.scenario(season_id, request, db)
    except SeasonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{season_id}/projection", response_model=ChampionshipProjectionResponse)
def project_championship(
    season_id: int,
    simulations: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ChampionshipProjectionResponse:
    """Run optional simulation-based championship projections."""
    try:
        return service.projection(season_id, db, simulations=simulations)
    except SeasonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
