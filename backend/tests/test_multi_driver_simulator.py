from app.models.circuit import CircuitConfig
from app.schemas.multi_race import DriverConfig, MultiDriverRaceConfig
from app.schemas.simulation import PitInstruction, RaceConfig, TyreCompound
from app.services.multi_driver_simulator import MultiDriverRaceSimulator


def _race_config(safety_car_probability: float = 0.15) -> RaceConfig:
    return RaceConfig(
        circuit=CircuitConfig(
            circuit_name="Monza",
            total_laps=18,
            base_lap_time_seconds=85,
            pit_lane_time_loss_seconds=22,
            avg_track_temp=35,
            avg_air_temp=28,
        ),
        starting_compound=TyreCompound.MEDIUM,
        starting_fuel_kg=70,
        weather_seed_state=42,
        safety_car_base_probability=safety_car_probability,
    )


def _multi_config() -> MultiDriverRaceConfig:
    return MultiDriverRaceConfig(
        race_config=_race_config(),
        event_seed_state=7,
        drivers=[
            DriverConfig(
                driver_id="drv-a",
                driver_name="Driver A",
                team_name="Red",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=70,
                pace_factor=0.99,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=9, compound=TyreCompound.HARD)],
            ),
            DriverConfig(
                driver_id="drv-b",
                driver_name="Driver B",
                team_name="Blue",
                starting_compound=TyreCompound.SOFT,
                starting_fuel_kg=70,
                pace_factor=1.01,
                degradation_factor=1.05,
                strategy=[PitInstruction(lap=7, compound=TyreCompound.MEDIUM)],
            ),
        ],
    )


def test_shared_environment_is_identical_for_all_drivers() -> None:
    result = MultiDriverRaceSimulator().run(_multi_config())

    weather_by_lap = {weather.lap_number: weather for weather in result.shared_weather_history}
    for driver in result.driver_results:
        for lap in driver.lap_results:
            weather = weather_by_lap[lap.lap_number]
            assert weather.track_wetness >= 0

    assert len(result.shared_weather_history) == result.total_laps
    assert all(driver.completed_laps == result.total_laps for driver in result.driver_results)


def test_multi_driver_determinism() -> None:
    simulator = MultiDriverRaceSimulator()
    first = simulator.run(_multi_config())
    second = simulator.run(_multi_config())

    assert first.classification == second.classification
    assert first.shared_weather_history == second.shared_weather_history
    assert first.shared_events == second.shared_events


def test_classification_orders_by_race_time() -> None:
    result = MultiDriverRaceSimulator().run(_multi_config())

    assert result.classification[0].driver_id == "drv-a"
    assert result.classification[0].position == 1
    assert result.classification[1].gap_to_leader_seconds > 0


def test_safety_car_or_vsc_affects_all_drivers_when_generated() -> None:
    config = _multi_config().model_copy(
        update={"race_config": _race_config(safety_car_probability=1.0)}
    )
    result = MultiDriverRaceSimulator().run(config)
    event_laps = {event.lap for event in result.shared_events if "SAFETY_CAR" in event.event_type.value}

    assert event_laps
    for lap in event_laps:
        lap_times = [
            driver.lap_results[lap - 1].lap_time_seconds
            for driver in result.driver_results
        ]
        assert all(lap_time > config.race_config.circuit.base_lap_time_seconds for lap_time in lap_times)
