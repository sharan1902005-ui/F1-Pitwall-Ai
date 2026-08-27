"""Schemas for interactive live race sessions."""

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.race_engineer import EngineerResponse
from app.schemas.simulation import LapResult, RaceConfig, StrategyResult, TyreCompound, WeatherState


class RaceStatus(str, Enum):
    """Live race lifecycle and race-control states."""

    READY = "READY"
    RUNNING = "RUNNING"
    SAFETY_CAR = "SAFETY_CAR"
    VIRTUAL_SAFETY_CAR = "VIRTUAL_SAFETY_CAR"
    FINISHED = "FINISHED"
    ABORTED = "ABORTED"


class LiveActionType(str, Enum):
    """Supported user actions before advancing a lap."""

    STAY_OUT = "STAY_OUT"
    PIT = "PIT"
    FOLLOW_RECOMMENDATION = "FOLLOW_RECOMMENDATION"


class RaceEventType(str, Enum):
    """Deterministic simulated race event types."""

    SAFETY_CAR = "SAFETY_CAR"
    VIRTUAL_SAFETY_CAR = "VIRTUAL_SAFETY_CAR"
    DRYING_TRACK = "DRYING_TRACK"
    RAIN_INCREASE = "RAIN_INCREASE"
    RAIN_DECREASE = "RAIN_DECREASE"
    TRACK_TEMPERATURE_CHANGE = "TRACK_TEMPERATURE_CHANGE"
    TYRE_CROSSOVER = "TYRE_CROSSOVER"


class LiveRaceAction(BaseModel):
    """User race-control action."""

    action: LiveActionType
    compound: TyreCompound | None = None


class RaceControlEvent(BaseModel):
    """Structured simulated race-control event."""

    event_type: RaceEventType
    lap: int
    active: bool
    reason: str


class RaceActionRecord(BaseModel):
    """Recorded user decision against an AI recommendation."""

    lap: int
    recommended_action: str
    user_action: LiveActionType
    followed_recommendation: bool
    time_impact: float


class RaceTimelineEntry(BaseModel):
    """Timeline item for race replay and decision history."""

    lap: int
    entry_type: str
    description: str


class LiveRaceState(BaseModel):
    """Current state of an interactive race session."""

    race_id: str
    race_config: RaceConfig
    current_lap: int
    total_laps: int
    current_compound: TyreCompound
    tyre_age: int
    fuel_remaining_kg: float = Field(ge=0)
    track_wetness: float = Field(ge=0, le=1)
    rain_probability: float = Field(ge=0, le=1)
    rain_intensity: float = Field(ge=0, le=1)
    track_temperature: float
    air_temperature: float
    current_race_time: float
    pit_stop_count: int
    race_status: RaceStatus
    weather_seed_state: int
    event_seed_state: int
    history: list[LapResult]
    weather_history: list[WeatherState]
    events: list[RaceControlEvent]
    actions: list[RaceActionRecord]
    timeline: list[RaceTimelineEntry]
    recommendation: EngineerResponse | None = None
    strategy: StrategyResult | None = None
    strategy_recalculation_count: int = 0


class LiveRaceStartResponse(BaseModel):
    """Response returned when a live race is started."""

    race_id: str
    race_state: LiveRaceState


class LiveRaceAdvanceResponse(BaseModel):
    """Response returned after advancing one lap."""

    race_id: str
    current_lap: int
    total_laps: int
    lap_result: LapResult | None
    race_state: LiveRaceState
    events: list[RaceControlEvent]
    race_status: RaceStatus


class LiveRaceRecommendationResponse(BaseModel):
    """Current live recommendation response."""

    race_id: str
    recommendation: EngineerResponse
    strategy: StrategyResult | None
