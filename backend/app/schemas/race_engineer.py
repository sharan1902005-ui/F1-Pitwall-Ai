"""Schemas for AI race engineer explanations and scenarios."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.simulation import RaceConfig, StrategyResult, TyreCompound


class Urgency(str, Enum):
    """Race engineer urgency levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ScenarioType(str, Enum):
    """Supported deterministic scenario types."""

    RAIN_INTENSITY_INCREASE = "RAIN_INTENSITY_INCREASE"
    RAIN_ARRIVES_EARLIER = "RAIN_ARRIVES_EARLIER"
    DEGRADATION_INCREASE = "DEGRADATION_INCREASE"
    TRACK_WETNESS_STAYS_LOW = "TRACK_WETNESS_STAYS_LOW"


class RaceContext(BaseModel):
    """Structured race state used for explanation only."""

    current_lap: int = Field(gt=0)
    total_laps: int = Field(gt=0)
    current_compound: TyreCompound
    tyre_age: int = Field(ge=0)
    fuel_remaining_kg: float = Field(ge=0)
    track_wetness: float = Field(ge=0, le=1)
    rain_probability: float = Field(ge=0, le=1)
    rain_intensity: float = Field(ge=0, le=1)
    track_temperature: float
    air_temperature: float
    current_position: int | None = Field(default=None, gt=0)
    gap_ahead_seconds: float | None = Field(default=None, ge=0)
    gap_behind_seconds: float | None = Field(default=None, ge=0)
    opponent_strategies: list[str] = Field(default_factory=list)
    safety_car_status: str | None = None
    relative_tyre_state: str | None = None
    recent_lap_times: list[float] = Field(default_factory=list)


class EngineerResponse(BaseModel):
    """Grounded race engineer response."""

    decision: str
    urgency: Urgency
    explanation: str
    key_factors: list[str]
    estimated_time_gain_seconds: float | None = None
    recommended_compound: TyreCompound | None = None
    recommended_pit_lap: int | None = None
    confidence: float | None = None
    risk: str | None = None


class ExplainStrategyRequest(BaseModel):
    """Request to explain a strategy selected from strategy analysis."""

    race_config: RaceConfig
    strategy_id: str | None = None
    context: RaceContext | None = None


class DecisionRequest(BaseModel):
    """Request for a current-race recommendation from structured context."""

    race_config: RaceConfig
    context: RaceContext


class ScenarioRequest(BaseModel):
    """Request for controlled deterministic what-if analysis."""

    race_config: RaceConfig
    scenario_type: ScenarioType
    scenario_parameters: dict[str, Any] = Field(default_factory=dict)


class ScenarioResponse(BaseModel):
    """Scenario analysis result with deterministic comparison and explanation."""

    baseline_strategy: str
    scenario_strategy: str
    baseline_race_time: float
    scenario_race_time: float
    time_difference: float
    strategy_changed: bool
    key_changes: list[str]
    engineer_explanation: EngineerResponse
