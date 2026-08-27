"""Live race control routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.live_race import (
    LiveRaceAction,
    LiveRaceAdvanceResponse,
    LiveRaceRecommendationResponse,
    LiveRaceStartResponse,
    LiveRaceState,
)
from app.schemas.simulation import RaceConfig, TyreCompound
from app.services.live_race_service import (
    LiveRaceNotFoundError,
    LiveRaceService,
    LiveRaceStateError,
)


router = APIRouter(prefix="/api/live-race", tags=["live-race"])
live_race_service = LiveRaceService()


@router.post("/start", response_model=LiveRaceStartResponse)
def start_live_race(
    config: RaceConfig,
    event_seed_state: int = Query(default=0),
    db: Session = Depends(get_db),
) -> LiveRaceStartResponse:
    """Start an interactive live race session."""
    _ = db
    return live_race_service.start(config, event_seed_state=event_seed_state)


@router.get("/{race_id}", response_model=LiveRaceState)
def get_live_race(
    race_id: str,
    db: Session = Depends(get_db),
) -> LiveRaceState:
    """Return live race session state."""
    _ = db
    try:
        return live_race_service.get(race_id)
    except LiveRaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{race_id}/advance", response_model=LiveRaceAdvanceResponse)
def advance_live_race(
    race_id: str,
    db: Session = Depends(get_db),
) -> LiveRaceAdvanceResponse:
    """Advance an interactive race by one lap."""
    _ = db
    try:
        return live_race_service.advance(race_id)
    except LiveRaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LiveRaceStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{race_id}/action", response_model=LiveRaceState)
def submit_live_action(
    race_id: str,
    action: LiveRaceAction,
    db: Session = Depends(get_db),
) -> LiveRaceState:
    """Submit a race-control action for the next lap."""
    _ = db
    try:
        return live_race_service.submit_action(race_id, action)
    except LiveRaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (LiveRaceStateError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{race_id}/pit", response_model=LiveRaceState)
def pit_live_race(
    race_id: str,
    compound: TyreCompound = Query(...),
    db: Session = Depends(get_db),
) -> LiveRaceState:
    """Shortcut endpoint to pit on the next lap."""
    _ = db
    try:
        return live_race_service.pit(race_id, compound)
    except LiveRaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LiveRaceStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{race_id}/recommendation", response_model=LiveRaceRecommendationResponse)
def live_recommendation(
    race_id: str,
    db: Session = Depends(get_db),
) -> LiveRaceRecommendationResponse:
    """Return current live race engineer recommendation."""
    _ = db
    try:
        return live_race_service.recommendation(race_id)
    except LiveRaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LiveRaceStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
