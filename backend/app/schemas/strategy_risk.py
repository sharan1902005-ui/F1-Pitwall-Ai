from typing import Literal

from pydantic import BaseModel, Field


class StrategyRiskRequest(BaseModel):

    weather_risk: float = Field(
        ge=0.0,
        le=1.0,
    )

    traffic_risk: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ]

    tyre_age: int = Field(
        ge=0,
    )

    estimated_tyre_life: int = Field(
        gt=0,
    )

    degradation_per_lap: float = Field(
        ge=0.0,
    )

    safety_car_probability: float = Field(
        ge=0.0,
        le=1.0,
    )

    opponent_pit_probability: float = Field(
        ge=0.0,
        le=100.0,
    )

    pit_lane_time_loss_seconds: float = Field(
        gt=0,
    )


class StrategyRiskResponse(BaseModel):

    overall_risk_score: float

    risk_level: str

    weather_risk_score: float

    traffic_risk_score: float

    tyre_risk_score: float

    safety_car_risk_score: float

    opponent_risk_score: float

    recommendation: str