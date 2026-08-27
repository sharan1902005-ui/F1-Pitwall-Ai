"""Historical race routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.historical import HistoricalLap, HistoricalPitStop, HistoricalRace
from app.schemas.historical import (
    HistoricalLapRead,
    HistoricalPitStopRead,
    HistoricalRaceRead,
)


router = APIRouter(prefix="/api/races", tags=["races"])


@router.get("", response_model=list[HistoricalRaceRead])
def list_races(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[HistoricalRaceRead]:
    """Return paginated historical race summaries."""
    return list(
        db.scalars(
            select(HistoricalRace)
            .order_by(HistoricalRace.season.desc(), HistoricalRace.race_name)
            .offset(offset)
            .limit(limit)
        )
    )


@router.get("/{race_id}", response_model=HistoricalRaceRead)
def get_race(race_id: int, db: Session = Depends(get_db)) -> HistoricalRaceRead:
    """Return one historical race by ID."""
    race = db.get(HistoricalRace, race_id)
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    return race


@router.get("/{race_id}/laps", response_model=list[HistoricalLapRead])
def get_race_laps(
    race_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[HistoricalLapRead]:
    """Return paginated historical laps for a race."""
    if db.get(HistoricalRace, race_id) is None:
        raise HTTPException(status_code=404, detail="Race not found")
    return list(
        db.scalars(
            select(HistoricalLap)
            .where(HistoricalLap.race_id == race_id)
            .order_by(HistoricalLap.driver_code, HistoricalLap.lap_number)
            .offset(offset)
            .limit(limit)
        )
    )


@router.get("/{race_id}/pit-stops", response_model=list[HistoricalPitStopRead])
def get_race_pit_stops(
    race_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[HistoricalPitStopRead]:
    """Return paginated historical pit stops for a race."""
    if db.get(HistoricalRace, race_id) is None:
        raise HTTPException(status_code=404, detail="Race not found")
    return list(
        db.scalars(
            select(HistoricalPitStop)
            .where(HistoricalPitStop.race_id == race_id)
            .order_by(HistoricalPitStop.driver_code, HistoricalPitStop.lap_number)
            .offset(offset)
            .limit(limit)
        )
    )
