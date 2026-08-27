"""Schemas for multi-driver race simulation and competitive strategy analysis."""

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.schemas.live_race import RaceControlEvent, RaceStatus
from app.schemas.race_engineer import EngineerResponse
from app.schemas.simulation import PitInstruction, RaceConfig, TyreCompound, WeatherState


class DriverRaceStatus(str, Enum):
    """Per-driver race lifecycle status."""

    RUNNING = "RUNNING"
    PITTING = "PITTING"
    FINISHED = "FINISHED"


class DriverStrategyMode(str, Enum):
    """How a driver's pit strategy should be resolved."""

    MANUAL = "MANUAL"
    AI = "AI"


class DriverConfig(BaseModel):
    """One competitor in a shared race environment."""

    driver_id: str = Field(min_length=1, max_length=24)
    driver_name: str = Field(min_length=1, max_length=80)
    team_name: str = Field(min_length=1, max_length=80)
    starting_compound: TyreCompound
    starting_fuel_kg: float = Field(ge=0, le=160)
    pace_factor: float = Field(ge=0.94, le=1.08)
    degradation_factor: float = Field(ge=0.70, le=1.40)
    strategy_mode: DriverStrategyMode = DriverStrategyMode.MANUAL
    strategy: list[PitInstruction] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def validate_strategy_order(self) -> "DriverConfig":
        """Require deterministic, non-ambiguous pit plans."""
        laps = [instruction.lap for instruction in self.strategy]
        if len(laps) != len(set(laps)):
            raise ValueError("Driver strategy cannot contain duplicate pit laps")
        if laps != sorted(laps):
            raise ValueError("Driver strategy pit laps must be sorted")
        return self


class MultiDriverRaceConfig(BaseModel):
    """Wrapper that preserves the existing single-driver RaceConfig contract."""

    race_config: RaceConfig
    drivers: list[DriverConfig] = Field(min_length=2, max_length=20)
    event_seed_state: int = 0

    @model_validator(mode="after")
    def validate_drivers(self) -> "MultiDriverRaceConfig":
        """Validate driver IDs and strategy lap ranges."""
        driver_ids = [driver.driver_id for driver in self.drivers]
        if len(driver_ids) != len(set(driver_ids)):
            raise ValueError("Driver IDs must be unique")
        total_laps = self.race_config.circuit.total_laps
        for driver in self.drivers:
            for instruction in driver.strategy:
                if instruction.lap > total_laps:
                    raise ValueError("Driver strategy pit lap exceeds race distance")
        return self


class DriverLapResult(BaseModel):
    """Computed lap state for one driver in a multi-driver race."""

    driver_id: str
    lap_number: int
    position: int
    lap_time_seconds: float
    compound: TyreCompound
    tyre_age: int
    tyre_life_percent: float = Field(ge=0, le=100)
    fuel_remaining_kg: float = Field(ge=0)
    pit_time_loss_seconds: float = Field(ge=0)
    race_status: DriverRaceStatus
    cumulative_race_time: float


class ClassificationEntry(BaseModel):
    """Race classification entry."""

    position: int
    driver_id: str
    driver_name: str
    team_name: str
    completed_laps: int
    total_race_time_seconds: float
    gap_to_leader_seconds: float
    pit_stop_count: int
    final_compound: TyreCompound
    final_strategy: list[PitInstruction]


class LapClassification(BaseModel):
    """Classification snapshot after a completed race lap."""

    lap_number: int
    classification: list[ClassificationEntry]


class DriverRaceResult(BaseModel):
    """Complete per-driver race result."""

    driver_id: str
    driver_name: str
    team_name: str
    completed_laps: int
    total_race_time_seconds: float
    final_compound: TyreCompound
    final_tyre_age: int
    final_fuel_remaining_kg: float = Field(ge=0)
    pit_stop_count: int
    final_strategy: list[PitInstruction]
    lap_results: list[DriverLapResult]


class OpponentStrategyInsight(BaseModel):
    """Backend-generated opponent strategy context."""

    driver_id: str
    driver_name: str
    current_tyre: TyreCompound
    tyre_age: int
    likely_pit_window_start: int | None = None
    likely_pit_window_end: int | None = None
    prediction_available: bool


class MultiDriverRaceResult(BaseModel):
    """Complete multi-driver simulation response."""

    total_laps: int
    shared_weather_history: list[WeatherState]
    shared_events: list[RaceControlEvent]
    driver_results: list[DriverRaceResult]
    classification: list[ClassificationEntry]
    classification_by_lap: list[LapClassification]
    opponent_insights: list[OpponentStrategyInsight]
    engineer_explanation: EngineerResponse | None = None


class StrategyScenario(BaseModel):
    """One alternative strategy scenario for a selected driver."""

    scenario_name: str = Field(min_length=1, max_length=80)
    driver_id: str = Field(min_length=1)
    strategy: list[PitInstruction] = Field(default_factory=list, max_length=6)


class StrategyComparisonRequest(BaseModel):
    """Compare alternative strategies under identical conditions."""

    base_config: MultiDriverRaceConfig
    scenarios: list[StrategyScenario] = Field(min_length=1, max_length=8)


class StrategyComparisonResult(BaseModel):
    """Result for one compared strategy scenario."""

    scenario_name: str
    driver_id: str
    final_position: int
    total_race_time_seconds: float
    gap_to_leader_seconds: float
    strategy: list[PitInstruction]
    time_difference_seconds: float
    position_difference: int


class StrategyComparisonResponse(BaseModel):
    """Strategy comparison response."""

    baseline: MultiDriverRaceResult
    results: list[StrategyComparisonResult]


class CounterfactualRequest(BaseModel):
    """Controlled counterfactual for one selected driver's pit plan."""

    base_config: MultiDriverRaceConfig
    driver_id: str = Field(min_length=1)
    alternative_strategy: list[PitInstruction] = Field(default_factory=list, max_length=6)


class CounterfactualDriverSummary(BaseModel):
    """Selected driver summary for baseline/counterfactual comparison."""

    position: int
    race_time_seconds: float
    gap_to_leader_seconds: float
    strategy: list[PitInstruction]


class CounterfactualResult(BaseModel):
    """Controlled counterfactual result."""

    driver_id: str
    baseline: CounterfactualDriverSummary
    counterfactual: CounterfactualDriverSummary
    time_difference_seconds: float
    position_difference: int
    weather_identical: bool
    events_identical: bool


class CompetitiveEngineerRequest(BaseModel):
    """Request for deterministic competitive race engineer context."""

    race_result: MultiDriverRaceResult
    driver_id: str = Field(min_length=1)
