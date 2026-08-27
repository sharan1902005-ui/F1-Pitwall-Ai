"""Circuit configuration models."""

from pydantic import BaseModel, Field


class CircuitConfig(BaseModel):
    """Static circuit inputs required to configure a race simulation."""

    circuit_name: str = Field(min_length=1)
    total_laps: int = Field(gt=0)
    base_lap_time_seconds: float = Field(gt=0)
    pit_lane_time_loss_seconds: float = Field(ge=0)
    avg_track_temp: float
    avg_air_temp: float
