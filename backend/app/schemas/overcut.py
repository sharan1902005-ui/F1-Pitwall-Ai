from typing import Literal

from pydantic import BaseModel, Field


TyreCompound = Literal[
    "SOFT",
    "MEDIUM",
    "HARD",
    "INTERMEDIATE",
    "WET",
]


class DriverOvercutRequest(BaseModel):
    driver_name: str

    position: int = Field(
        ge=1,
        le=20,
    )

    compound: TyreCompound

    tyre_age: int = Field(
        ge=0,
        le=100,
    )

    gap_to_driver_ahead_seconds: float = Field(
        ge=0,
    )

    current_lap: int = Field(
        ge=1,
    )

    base_lap_time_seconds: float = Field(
        gt=0,
    )

    degradation_per_lap: float = Field(
        ge=0,
    )


class OvercutRequest(BaseModel):
    driver: DriverOvercutRequest
    opponent: DriverOvercutRequest

    pit_lane_time_loss_seconds: float = Field(
        gt=0,
    )

    max_stay_out_laps: int = Field(
        default=3,
        ge=1,
        le=5,
    )


class OvercutOptionResponse(BaseModel):
    stay_out_laps: int
    projected_advantage_seconds: float
    projected_gap_after_cycle_seconds: float


class OvercutResponse(BaseModel):
    overcut_available: bool
    best_stay_out_laps: int
    projected_advantage_seconds: float
    projected_gap_after_cycle_seconds: float
    projected_position: int
    confidence: float
    recommendation: str
    options: list[OvercutOptionResponse]