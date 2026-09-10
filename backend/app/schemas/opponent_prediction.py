from typing import Literal

from pydantic import BaseModel, Field


TyreCompound = Literal[
    "SOFT",
    "MEDIUM",
    "HARD",
    "INTERMEDIATE",
    "WET",
]


class OpponentPredictionRequest(BaseModel):

    driver_name: str

    position: int = Field(
        ge=1,
        le=20,
    )

    compound: TyreCompound

    tyre_age: int = Field(
        ge=0,
    )

    current_lap: int = Field(
        ge=1,
    )

    total_laps: int = Field(
        ge=1,
    )

    base_lap_time_seconds: float = Field(
        gt=0,
    )

    degradation_per_lap: float = Field(
        ge=0,
    )

    pit_stops_completed: int = Field(
        default=0,
        ge=0,
    )

    weather_risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    prediction_window_laps: int = Field(
        default=5,
        ge=1,
        le=15,
    )


class PitProbabilityResponse(BaseModel):

    lap: int
    probability: float


class OpponentPredictionResponse(BaseModel):

    driver_name: str

    most_likely_pit_lap: int

    most_likely_probability: float

    confidence: float

    recommendation: str

    predictions: list[PitProbabilityResponse]