from pydantic import BaseModel, Field


class TrafficDriverRequest(BaseModel):

    driver_name: str

    current_position: int = Field(
        ge=1,
        le=20,
    )

    current_lap: int = Field(
        ge=1,
    )

    base_lap_time_seconds: float = Field(
        gt=0,
    )


class CarAheadRequest(BaseModel):

    driver_name: str

    gap_seconds: float = Field(
        ge=0,
    )

    pace_delta_seconds: float = Field(
        ge=0,
    )

    overtaking_difficulty: float = Field(
        ge=0,
        le=1,
    )


class TrafficRequest(BaseModel):

    driver: TrafficDriverRequest

    car_ahead: CarAheadRequest

    laps_in_traffic: int = Field(
        default=5,
        ge=1,
        le=20,
    )


class TrafficResponse(BaseModel):

    dirty_air_penalty_seconds: float

    projected_traffic_loss_seconds: float

    overtaking_difficulty: float

    traffic_risk: str

    recommendation: str