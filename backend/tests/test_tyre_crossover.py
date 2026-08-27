from app.models.circuit import CircuitConfig
from app.schemas.simulation import TyreCompound
from app.services.tyre_crossover import TyreCrossoverEngine
from app.services.tyre_model import TyrePerformanceModel


def circuit() -> CircuitConfig:
    return CircuitConfig(
        circuit_name="Monza",
        total_laps=57,
        base_lap_time_seconds=85.0,
        pit_lane_time_loss_seconds=22.0,
        avg_track_temp=35.0,
        avg_air_temp=28.0,
    )


def test_slicks_outperform_wet_tyres_on_dry_track() -> None:
    model = TyrePerformanceModel()

    medium = model.performance_penalty(TyreCompound.MEDIUM, 5, 0.0)
    intermediate = model.performance_penalty(TyreCompound.INTERMEDIATE, 5, 0.0)
    wet = model.performance_penalty(TyreCompound.WET, 5, 0.0)

    assert medium < intermediate
    assert medium < wet


def test_intermediate_becomes_more_competitive_with_moderate_wetness() -> None:
    model = TyrePerformanceModel()

    dry_gap = model.performance_penalty(
        TyreCompound.INTERMEDIATE,
        5,
        0.0,
    ) - model.performance_penalty(TyreCompound.MEDIUM, 5, 0.0)
    moderate_gap = model.performance_penalty(
        TyreCompound.INTERMEDIATE,
        5,
        0.45,
    ) - model.performance_penalty(TyreCompound.MEDIUM, 5, 0.45)

    assert moderate_gap < dry_gap


def test_wet_tyre_becomes_competitive_in_heavy_wetness() -> None:
    model = TyrePerformanceModel()

    wet_penalty = model.performance_penalty(TyreCompound.WET, 5, 0.9)
    intermediate_penalty = model.performance_penalty(TyreCompound.INTERMEDIATE, 5, 0.9)
    medium_penalty = model.performance_penalty(TyreCompound.MEDIUM, 5, 0.9)

    assert wet_penalty < intermediate_penalty
    assert wet_penalty < medium_penalty


def test_crossover_considers_pit_lane_loss_and_can_return_none() -> None:
    engine = TyreCrossoverEngine()

    result = engine.find_crossover_lap(
        current_compound=TyreCompound.MEDIUM,
        alternative_compound=TyreCompound.INTERMEDIATE,
        current_tyre_age=5,
        current_lap=10,
        remaining_laps=8,
        predicted_weather=[0.28] * 8,
        circuit_config=circuit(),
    )

    assert result.crossover_detected is False
    assert result.recommended_pit_lap is None


def test_crossover_is_not_a_rain_boolean_rule() -> None:
    engine = TyreCrossoverEngine()

    short_heavy_wet = engine.find_crossover_lap(
        current_compound=TyreCompound.MEDIUM,
        alternative_compound=TyreCompound.INTERMEDIATE,
        current_tyre_age=5,
        current_lap=20,
        remaining_laps=1,
        predicted_weather=[0.95],
        circuit_config=circuit(),
    )
    sustained_heavy_wet = engine.find_crossover_lap(
        current_compound=TyreCompound.MEDIUM,
        alternative_compound=TyreCompound.INTERMEDIATE,
        current_tyre_age=5,
        current_lap=20,
        remaining_laps=20,
        predicted_weather=[0.95] * 20,
        circuit_config=circuit(),
    )

    assert short_heavy_wet.crossover_detected is False
    assert sustained_heavy_wet.crossover_detected is True


def test_heavy_wetness_can_trigger_wet_crossover() -> None:
    engine = TyreCrossoverEngine()

    result = engine.find_crossover_lap(
        current_compound=TyreCompound.INTERMEDIATE,
        alternative_compound=TyreCompound.WET,
        current_tyre_age=10,
        current_lap=25,
        remaining_laps=20,
        predicted_weather=[0.9] * 20,
        circuit_config=circuit(),
    )

    assert result.crossover_detected is True
    assert result.recommended_compound == TyreCompound.WET
