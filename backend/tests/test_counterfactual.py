from app.models.circuit import CircuitConfig
from app.schemas.multi_race import CounterfactualRequest, DriverConfig, MultiDriverRaceConfig
from app.schemas.simulation import PitInstruction, RaceConfig, TyreCompound
from app.services.competitive_strategy_service import CompetitiveStrategyService


def _config() -> MultiDriverRaceConfig:
    return MultiDriverRaceConfig(
        race_config=RaceConfig(
            circuit=CircuitConfig(
                circuit_name="Spa",
                total_laps=22,
                base_lap_time_seconds=101,
                pit_lane_time_loss_seconds=23,
                avg_track_temp=26,
                avg_air_temp=19,
            ),
            starting_compound=TyreCompound.MEDIUM,
            starting_fuel_kg=85,
            weather_seed_state=31,
            safety_car_base_probability=0.25,
        ),
        event_seed_state=3,
        drivers=[
            DriverConfig(
                driver_id="a",
                driver_name="Driver A",
                team_name="Alpha",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=85,
                pace_factor=0.995,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=11, compound=TyreCompound.HARD)],
            ),
            DriverConfig(
                driver_id="b",
                driver_name="Driver B",
                team_name="Beta",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=85,
                pace_factor=1.0,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=12, compound=TyreCompound.HARD)],
            ),
            DriverConfig(
                driver_id="c",
                driver_name="Driver C",
                team_name="Gamma",
                starting_compound=TyreCompound.HARD,
                starting_fuel_kg=85,
                pace_factor=1.005,
                degradation_factor=0.95,
                strategy=[PitInstruction(lap=15, compound=TyreCompound.MEDIUM)],
            ),
        ],
    )


def test_counterfactual_keeps_weather_and_events_identical() -> None:
    result = CompetitiveStrategyService().counterfactual(
        CounterfactualRequest(
            base_config=_config(),
            driver_id="a",
            alternative_strategy=[PitInstruction(lap=15, compound=TyreCompound.HARD)],
        )
    )

    assert result.weather_identical is True
    assert result.events_identical is True
    assert result.time_difference_seconds == round(
        result.counterfactual.race_time_seconds - result.baseline.race_time_seconds,
        6,
    )
    assert result.position_difference == result.baseline.position - result.counterfactual.position


def test_counterfactual_only_selected_driver_strategy_changes() -> None:
    service = CompetitiveStrategyService()
    baseline = service.simulate(_config())
    counterfactual_config = _config().model_copy(
        update={
            "drivers": [
                _config().drivers[0].model_copy(
                    update={"strategy": [PitInstruction(lap=15, compound=TyreCompound.HARD)]}
                ),
                _config().drivers[1],
                _config().drivers[2],
            ]
        }
    )
    counterfactual = service.simulate(counterfactual_config)

    for driver_id in {"b", "c"}:
        baseline_driver = next(driver for driver in baseline.driver_results if driver.driver_id == driver_id)
        counterfactual_driver = next(
            driver for driver in counterfactual.driver_results if driver.driver_id == driver_id
        )
        assert baseline_driver.final_strategy == counterfactual_driver.final_strategy
        assert [
            lap.model_copy(update={"position": 0})
            for lap in baseline_driver.lap_results
        ] == [
            lap.model_copy(update={"position": 0})
            for lap in counterfactual_driver.lap_results
        ]
