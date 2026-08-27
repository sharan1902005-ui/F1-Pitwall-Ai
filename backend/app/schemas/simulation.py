"""Schemas for simulation-related API requests."""

from enum import Enum

from pydantic import BaseModel, Field

from app.models.circuit import CircuitConfig


class TyreCompound(str, Enum):
    """Supported tyre compounds for the race configuration."""

    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"


class RaceConfig(BaseModel):
    """Race configuration accepted by simulation endpoints."""

    circuit: CircuitConfig
    starting_compound: TyreCompound
    starting_fuel_kg: float = Field(ge=0)
    weather_seed_state: int
    safety_car_base_probability: float = Field(ge=0, le=1)


class PitInstruction(BaseModel):
    """Predefined pit stop instruction for in-memory simulations."""

    lap: int = Field(gt=0)
    compound: TyreCompound


class WeatherState(BaseModel):
    """Deterministic weather state for one simulated lap."""

    lap_number: int
    rain_probability: float = Field(ge=0, le=1)
    rain_intensity: float = Field(ge=0, le=1)
    track_temperature: float
    air_temperature: float
    track_wetness: float = Field(ge=0, le=1)


class LapResult(BaseModel):
    """Computed state and timing for a completed lap."""

    lap_number: int
    lap_time_seconds: float
    compound: TyreCompound
    tyre_age: int
    tyre_life_percent: float = Field(ge=0, le=100)
    fuel_remaining_kg: float = Field(ge=0)
    track_temperature: float
    air_temperature: float
    rain_probability: float = Field(ge=0, le=1)
    track_wetness: float = Field(ge=0, le=1)
    cumulative_race_time: float


class PitStop(BaseModel):
    """Recorded pit stop event."""

    lap_number: int
    old_compound: TyreCompound
    new_compound: TyreCompound
    pit_time_loss_seconds: float = Field(ge=0)


class RaceResult(BaseModel):
    """Complete deterministic race simulation result."""

    total_laps: int
    completed_laps: int
    final_race_time_seconds: float
    final_compound: TyreCompound
    final_tyre_age: int
    final_fuel_remaining_kg: float = Field(ge=0)
    lap_results: list[LapResult]
    pit_stops: list[PitStop]
    weather_history: list[WeatherState]


class CrossoverResult(BaseModel):
    """Result of comparing a current tyre with an alternative compound."""

    crossover_detected: bool
    recommended_pit_lap: int | None
    current_compound: TyreCompound
    recommended_compound: TyreCompound
    estimated_time_gain_seconds: float
    reason: str


class StrategyStint(BaseModel):
    """One stint within a candidate race strategy."""

    compound: TyreCompound
    start_lap: int = Field(gt=0)
    end_lap: int = Field(gt=0)


class StrategyResult(BaseModel):
    """Ranked strategy analysis result."""

    strategy_id: str
    stints: list[StrategyStint]
    pit_laps: list[int]
    expected_race_time_seconds: float
    pit_stop_count: int
    projected_finish: int
    confidence: float = Field(ge=0, le=1)
    risk: str
    recommendation_reason: str


class StrategyAnalysisResponse(BaseModel):
    """API response containing the best strategy and all ranked candidates."""

    recommended_strategy: StrategyResult | None
    strategies: list[StrategyResult]
