"""Schemas for championship season simulation."""

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.schemas.multi_race import DriverConfig, MultiDriverRaceResult


class SeasonStatus(str, Enum):
    """Season lifecycle status."""

    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class MomentumLabel(str, Enum):
    """Deterministic championship momentum label."""

    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"


class SeasonCalendarRound(BaseModel):
    """One race on a season calendar."""

    round_number: int = Field(gt=0)
    circuit_id: int = Field(gt=0)


class PointsSystem(BaseModel):
    """Configurable points system indexed by finishing position."""

    points_by_position: dict[int, float] = Field(
        default_factory=lambda: {
            1: 25,
            2: 18,
            3: 15,
            4: 12,
            5: 10,
            6: 8,
            7: 6,
            8: 4,
            9: 2,
            10: 1,
        }
    )

    @model_validator(mode="after")
    def validate_points(self) -> "PointsSystem":
        """Require positive position keys and non-negative points."""
        if not self.points_by_position:
            raise ValueError("Points system must contain at least one scoring position")
        for position, points in self.points_by_position.items():
            if position <= 0:
                raise ValueError("Points positions must be positive")
            if points < 0:
                raise ValueError("Points values cannot be negative")
        return self


class SeasonCreateRequest(BaseModel):
    """Request to create a persistent championship season."""

    season_name: str = Field(min_length=1, max_length=120)
    calendar: list[SeasonCalendarRound] = Field(min_length=2, max_length=30)
    drivers: list[DriverConfig] = Field(min_length=2, max_length=20)
    points_system: PointsSystem = Field(default_factory=PointsSystem)
    weather_seed: int = 42
    event_seed: int = 0
    safety_car_base_probability: float = Field(default=0.15, ge=0, le=1)
    allow_duplicate_circuits: bool = False

    @model_validator(mode="after")
    def validate_season(self) -> "SeasonCreateRequest":
        """Validate season calendar and driver identity."""
        driver_ids = [driver.driver_id for driver in self.drivers]
        if len(driver_ids) != len(set(driver_ids)):
            raise ValueError("Driver IDs must be unique")
        teams = {driver.team_name for driver in self.drivers}
        if any(not team for team in teams):
            raise ValueError("Drivers must have valid teams")
        circuit_ids = [round_config.circuit_id for round_config in self.calendar]
        if not self.allow_duplicate_circuits and len(circuit_ids) != len(set(circuit_ids)):
            raise ValueError("Duplicate circuits are not allowed unless explicitly enabled")
        round_numbers = [round_config.round_number for round_config in self.calendar]
        if sorted(round_numbers) != list(range(1, len(round_numbers) + 1)):
            raise ValueError("Calendar rounds must be contiguous from 1")
        return self


class DriverStandingResponse(BaseModel):
    """Driver championship standing."""

    position: int
    driver_id: str
    driver_name: str
    team_name: str
    points: float
    wins: int
    podiums: int
    races: int
    best_finish: int | None
    average_finish: float | None
    total_race_time: float
    momentum: MomentumLabel
    points_history: list[float]
    position_history: list[int]


class ConstructorStandingResponse(BaseModel):
    """Constructor championship standing."""

    position: int
    team_name: str
    points: float
    wins: int
    podiums: int
    races: int
    momentum: MomentumLabel
    points_history: list[float]


class SeasonRaceSummary(BaseModel):
    """Calendar round state and result summary."""

    round_number: int
    circuit_id: int
    circuit_name: str
    completed: bool
    winner_driver_id: str | None = None
    winner_driver_name: str | None = None


class StrategySeasonMetric(BaseModel):
    """Season-level strategy performance metric."""

    strategy_label: str
    races: int
    average_position: float
    average_race_time: float
    wins: int
    podiums: int
    average_pit_stops: float


class DriverSeasonAnalysis(BaseModel):
    """Race-based driver analytics."""

    driver_id: str
    driver_name: str
    average_race_position: float | None
    wins: int
    podiums: int
    points_per_race: float
    best_circuit: str | None
    worst_circuit: str | None


class SeasonAnalyticsResponse(BaseModel):
    """Season-level analytics supported by stored results."""

    strategy_metrics: list[StrategySeasonMetric]
    most_successful_strategy: StrategySeasonMetric | None
    average_pit_stops: float
    driver_analysis: list[DriverSeasonAnalysis]
    momentum_method: str


class SeasonResponse(BaseModel):
    """Complete season state response."""

    id: int
    season_name: str
    current_round: int
    total_rounds: int
    status: SeasonStatus
    calendar: list[SeasonRaceSummary]
    driver_standings: list[DriverStandingResponse]
    constructor_standings: list[ConstructorStandingResponse]
    analytics: SeasonAnalyticsResponse


class SeasonStandingsResponse(BaseModel):
    """Driver and constructor standings response."""

    drivers: list[DriverStandingResponse]
    constructors: list[ConstructorStandingResponse]


class SeasonRaceResult(BaseModel):
    """Response returned after running a season race."""

    season: SeasonResponse
    race_result: MultiDriverRaceResult | None


class SeasonScenarioRequest(BaseModel):
    """Controlled hypothetical championship scenario."""

    driver_id: str = Field(min_length=1)
    round_number: int = Field(gt=0)
    hypothetical_position: int = Field(gt=0, le=20)


class SeasonScenarioStandingDelta(BaseModel):
    """Scenario delta for one driver."""

    driver_id: str
    baseline_position: int
    scenario_position: int
    baseline_points: float
    scenario_points: float
    points_difference: float
    position_difference: int


class SeasonScenarioResponse(BaseModel):
    """Hypothetical championship scenario response."""

    hypothetical: bool
    baseline_standings: list[DriverStandingResponse]
    scenario_standings: list[DriverStandingResponse]
    selected_driver_delta: SeasonScenarioStandingDelta
    championship_leader_changed: bool


class ChampionshipProjectionEntry(BaseModel):
    """Simulation-based championship projection for one driver."""

    driver_id: str
    driver_name: str
    championship_win_probability: float = Field(ge=0, le=1)
    expected_final_points: float
    expected_final_position: float


class ChampionshipProjectionResponse(BaseModel):
    """Optional deterministic season projection response."""

    simulations: int
    methodology: str
    seed_behavior: str
    projections: list[ChampionshipProjectionEntry]
