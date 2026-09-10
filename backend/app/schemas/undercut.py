from typing import Literal

from pydantic import BaseModel, Field


TyreCompound = Literal[
    "SOFT",
    "MEDIUM",
    "HARD",
    "INTERMEDIATE",
    "WET",
]


class DriverUndercutRequest(BaseModel):
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


class UndercutRequest(BaseModel):
    attacker: DriverUndercutRequest
    defender: DriverUndercutRequest

    pit_lane_time_loss_seconds: float = Field(
        gt=0,
    )

    new_compound: TyreCompound = "HARD"

    defender_stays_out_laps: int = Field(
        default=2,
        ge=1,
        le=5,
    )


class UndercutResponse(BaseModel):
    undercut_available: bool

    projected_gain_seconds: float

    projected_gap_after_cycle_seconds: float

    projected_position: int

    confidence: float

    recommendation: str

    recommended_compound: TyreCompound

    analysis_laps: int