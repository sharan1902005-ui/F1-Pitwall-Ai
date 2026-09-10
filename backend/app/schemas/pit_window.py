from typing import Literal

from pydantic import BaseModel, Field


TyreCompound = Literal[
    "SOFT",
    "MEDIUM",
    "HARD",
    "INTERMEDIATE",
    "WET",
]


class PitWindowDriverRequest(BaseModel):

    driver_name: str

    current_lap: int = Field(
        ge=1,
    )

    total_laps: int = Field(
        ge=1,
    )

    position: int = Field(
        ge=1,
        le=20,
    )

    compound: TyreCompound

    tyre_age: int = Field(
        ge=0,
    )

    base_lap_time_seconds: float = Field(
        gt=0,
    )

    degradation_per_lap: float = Field(
        ge=0,
    )

    gap_to_driver_ahead_seconds: float = Field(
        ge=0,
    )


class PitWindowRequest(BaseModel):

    driver: PitWindowDriverRequest

    pit_lane_time_loss_seconds: float = Field(
        gt=0,
    )

    earliest_pit_lap: int = Field(
        ge=1,
    )

    latest_pit_lap: int = Field(
        ge=1,
    )

    new_compound: TyreCompound = "HARD"


class PitWindowOptionResponse(BaseModel):

    pit_lap: int
    projected_race_time_seconds: float
    projected_gain_seconds: float


class PitWindowResponse(BaseModel):

    earliest_lap: int
    optimal_lap: int
    latest_lap: int

    recommended_compound: TyreCompound

    projected_gain_seconds: float

    projected_race_time_seconds: float

    confidence: float

    recommendation: str

    options: list[PitWindowOptionResponse]