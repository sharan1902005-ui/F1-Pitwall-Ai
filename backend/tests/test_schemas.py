import pytest
from pydantic import ValidationError

from app.models.circuit import CircuitConfig
from app.schemas.simulation import RaceConfig, TyreCompound


def valid_circuit() -> CircuitConfig:
    return CircuitConfig(
        circuit_name="Monza",
        total_laps=57,
        base_lap_time_seconds=85.0,
        pit_lane_time_loss_seconds=22.0,
        avg_track_temp=35.0,
        avg_air_temp=28.0,
    )


def test_valid_circuit_config() -> None:
    circuit = valid_circuit()

    assert circuit.circuit_name == "Monza"
    assert circuit.total_laps == 57


def test_valid_race_config() -> None:
    config = RaceConfig(
        circuit=valid_circuit(),
        starting_compound="MEDIUM",
        starting_fuel_kg=100.0,
        weather_seed_state=42,
        safety_car_base_probability=0.15,
    )

    assert config.circuit.circuit_name == "Monza"
    assert config.starting_compound == TyreCompound.MEDIUM


def test_invalid_total_laps() -> None:
    with pytest.raises(ValidationError):
        CircuitConfig(
            circuit_name="Monza",
            total_laps=0,
            base_lap_time_seconds=85.0,
            pit_lane_time_loss_seconds=22.0,
            avg_track_temp=35.0,
            avg_air_temp=28.0,
        )


def test_invalid_negative_fuel() -> None:
    with pytest.raises(ValidationError):
        RaceConfig(
            circuit=valid_circuit(),
            starting_compound="MEDIUM",
            starting_fuel_kg=-1.0,
            weather_seed_state=42,
            safety_car_base_probability=0.15,
        )


@pytest.mark.parametrize("probability", [-0.01, 1.01])
def test_invalid_safety_car_probability(probability: float) -> None:
    with pytest.raises(ValidationError):
        RaceConfig(
            circuit=valid_circuit(),
            starting_compound="MEDIUM",
            starting_fuel_kg=100.0,
            weather_seed_state=42,
            safety_car_base_probability=probability,
        )


def test_invalid_tyre_compound() -> None:
    with pytest.raises(ValidationError):
        RaceConfig(
            circuit=valid_circuit(),
            starting_compound="SUPER_SOFT",
            starting_fuel_kg=100.0,
            weather_seed_state=42,
            safety_car_base_probability=0.15,
        )
