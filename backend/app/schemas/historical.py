"""Schemas for circuit metadata and historical race APIs."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CircuitRead(BaseModel):
    """Circuit metadata returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str
    city: str
    total_laps: int
    base_lap_time_seconds: float
    pit_lane_time_loss_seconds: float
    avg_track_temp: float
    avg_air_temp: float
    track_length_km: float
    tyre_wear_factor: float
    overtaking_difficulty: float
    safety_car_factor: float


class HistoricalRaceRead(BaseModel):
    """Historical race summary returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    season: int
    race_name: str
    circuit_id: int
    race_date: date
    total_laps: int
    weather_summary: str
    safety_car_count: int
    vsc_count: int


class HistoricalLapRead(BaseModel):
    """Historical lap sample returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    race_id: int
    driver_code: str
    lap_number: int
    lap_time_seconds: float
    compound: str
    tyre_age: int
    position: int


class HistoricalPitStopRead(BaseModel):
    """Historical pit stop returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    race_id: int
    driver_code: str
    lap_number: int
    duration_seconds: float
    new_compound: str


class RaceComparison(BaseModel):
    """Simple comparison between simulated and historical race data."""

    simulated_total_time_seconds: float
    historical_average_lap_time_seconds: float | None
    simulated_average_lap_time_seconds: float
    simulated_pit_stop_count: int
    historical_pit_stop_count: int
    simulated_tyre_stint_lengths: list[int] = Field(default_factory=list)
    historical_tyre_stint_lengths: list[int] = Field(default_factory=list)
