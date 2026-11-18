"""Read contracts for provider-sourced driver and constructor reference data."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class F1DriverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    provider_driver_id: str
    code: str | None
    permanent_number: int | None
    given_name: str
    family_name: str
    date_of_birth: date | None
    nationality: str | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime


class F1ConstructorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    provider_constructor_id: str
    name: str
    nationality: str | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime


class F1DriverConstructorSeasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    season: int
    first_seen_round: int
    last_seen_round: int
    driver: F1DriverRead
    constructor: F1ConstructorRead


class F1CircuitEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    season: int
    round_number: int
    race_name: str
    race_date: date


class F1CircuitEventDetailRead(F1CircuitEventRead):
    """Imported historical event with its provider-backed circuit identity."""

    circuit: "F1CircuitRead"


class F1CircuitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    provider_circuit_id: str
    name: str
    city: str | None
    country: str
    latitude: float | None
    longitude: float | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime


class F1HistoricalResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    position: int | None
    position_text: str | None
    grid_position: int | None
    points: float | None
    laps_completed: int | None
    status: str | None
    race_time_millis: int | None
    race_time_text: str | None
    fastest_lap_rank: int | None
    fastest_lap_number: int | None
    fastest_lap_time_seconds: float | None
    fastest_lap_speed_kph: float | None
    imported_at: datetime
    event: F1CircuitEventRead
    driver: F1DriverRead
    constructor: F1ConstructorRead


class F1HistoricalSeasonSummary(BaseModel):
    season: int
    events: int
    results: int


class F1HistoricalAnalyticsRead(BaseModel):
    season: int
    races_used: int
    driver_id: int | None
    constructor_id: int | None
    wins: int
    podiums: int
    points: float
    classified_results: int


class F1QualifyingResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; source: str; position: int; q1_seconds: float | None; q2_seconds: float | None; q3_seconds: float | None; imported_at: datetime
    event: F1CircuitEventRead; driver: F1DriverRead; constructor: F1ConstructorRead


class F1StartingGridRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; source: str; grid_position: int; imported_at: datetime
    event: F1CircuitEventRead; driver: F1DriverRead; constructor: F1ConstructorRead


class F1QualifyingAnalyticsRead(BaseModel):
    season: int; driver_id: int | None; constructor_id: int | None; samples: int; average_position: float | None; poles: int; grid_changes: int


class F1HistoricalLapTimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; source: str; lap_number: int; position: int; lap_time_seconds: float; imported_at: datetime
    event: F1CircuitEventRead; driver: F1DriverRead


class F1HistoricalPitStopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; source: str; stop_number: int; lap_number: int; time: str; duration_seconds: float; imported_at: datetime
    event: F1CircuitEventRead; driver: F1DriverRead


class F1HistoricalWeatherObservationRead(BaseModel):
    """Verified OpenF1 observation; temperatures are °C, pressure mbar, wind m/s."""

    model_config = ConfigDict(from_attributes=True)
    id: int; source: str; provider_meeting_key: int; provider_session_key: int; observed_at: datetime
    air_temperature_celsius: float | None; track_temperature_celsius: float | None; humidity_percent: float | None
    pressure_mbar: float | None; wind_speed_mps: float | None; wind_direction_degrees: float | None; rainfall: bool | None
    imported_at: datetime; event: F1CircuitEventRead


class F1HistoricalWeatherSummaryRead(BaseModel):
    event_id: int; provider_session_key: int | None; observations: int
    first_observed_at: datetime | None; last_observed_at: datetime | None
    average_air_temperature_celsius: float | None; average_track_temperature_celsius: float | None
    rainfall_observations: int


class F1HistoricalPerformanceAnalyticsRead(BaseModel):
    event_id: int; driver_id: int | None; lap_samples: int; average_lap_time_seconds: float | None; fastest_lap_seconds: float | None; slowest_lap_seconds: float | None; pit_stop_samples: int; average_pit_stop_duration_seconds: float | None


class F1PerformanceAnalyticsRead(BaseModel):
    subject_id: int; season: int | None; starts: int; wins: int; podiums: int; points: float | None
    average_finish: float | None; best_finish: int | None; dnf_count: int; finish_rate: float | None
    average_qualifying_position: float | None; average_grid_to_finish_change: float | None


class F1LapAnalyticsRead(BaseModel):
    event_id: int; driver_id: int | None; samples: int; average_lap_time_seconds: float | None
    median_lap_time_seconds: float | None; fastest_lap_seconds: float | None; slowest_lap_seconds: float | None; variation_seconds: float | None


class F1PitStopAnalyticsRead(BaseModel):
    event_id: int; driver_id: int | None; samples: int; average_duration_seconds: float | None
    fastest_duration_seconds: float | None; slowest_duration_seconds: float | None


class F1SeasonAnalyticsRead(BaseModel):
    season: int; imported_events: int; imported_results: int; classified_results: int; dnfs: int
    driver_wins: dict[str, int]; constructor_points: dict[str, float]

class F1HistoricalStrategyBenchmarkRead(BaseModel):
    source: str = "historical_imported_data"
    season: int | None; event_id: int | None; circuit_id: int | None
    races_used: int; result_samples: int; pit_stop_samples: int; lap_samples: int
    average_pit_stops_per_race: float | None; average_pit_stop_duration_seconds: float | None
    average_lap_time_seconds: float | None; average_grid_to_finish_change: float | None
    note: str
