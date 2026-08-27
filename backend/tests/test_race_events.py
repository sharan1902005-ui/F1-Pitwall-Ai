from app.models.circuit import CircuitConfig
from app.schemas.simulation import RaceConfig
from app.services.race_event_engine import RaceEventEngine
from app.services.weather_engine import WeatherEngine


def config(probability: float = 1.0) -> RaceConfig:
    return RaceConfig(
        circuit=CircuitConfig(
            circuit_name="Monza",
            total_laps=10,
            base_lap_time_seconds=85.0,
            pit_lane_time_loss_seconds=22.0,
            avg_track_temp=35.0,
            avg_air_temp=28.0,
        ),
        starting_compound="MEDIUM",
        starting_fuel_kg=30.0,
        weather_seed_state=42,
        safety_car_base_probability=probability,
    )


def test_race_events_are_deterministic() -> None:
    event_engine = RaceEventEngine()
    weather_engine = WeatherEngine()
    race_config = config()
    rng_a = weather_engine.create_rng(race_config.weather_seed_state)
    rng_b = weather_engine.create_rng(race_config.weather_seed_state)
    weather_a = weather_engine.next_lap(3, race_config.circuit, rng_a, 0.1)
    weather_b = weather_engine.next_lap(3, race_config.circuit, rng_b, 0.1)

    events_a = event_engine.events_for_lap(race_config, 7, 3, weather_a, None)
    events_b = event_engine.events_for_lap(race_config, 7, 3, weather_b, None)

    assert events_a == events_b


def test_safety_car_and_vsc_modifiers_are_distinct() -> None:
    event_engine = RaceEventEngine()

    assert event_engine.safety_car_lap_time_multiplier > event_engine.vsc_lap_time_multiplier
    assert event_engine.safety_car_pit_loss_multiplier < event_engine.vsc_pit_loss_multiplier
    assert event_engine.safety_car_degradation_multiplier < event_engine.vsc_degradation_multiplier
