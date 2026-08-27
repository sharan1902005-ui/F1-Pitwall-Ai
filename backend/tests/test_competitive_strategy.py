from app.models.circuit import CircuitConfig
from app.schemas.multi_race import (
    DriverConfig,
    MultiDriverRaceConfig,
    StrategyComparisonRequest,
    StrategyScenario,
)
from app.schemas.simulation import PitInstruction, RaceConfig, TyreCompound
from app.services.competitive_strategy_service import CompetitiveStrategyService


def _config() -> MultiDriverRaceConfig:
    race_config = RaceConfig(
        circuit=CircuitConfig(
            circuit_name="Silverstone",
            total_laps=20,
            base_lap_time_seconds=88,
            pit_lane_time_loss_seconds=21,
            avg_track_temp=29,
            avg_air_temp=22,
        ),
        starting_compound=TyreCompound.MEDIUM,
        starting_fuel_kg=80,
        weather_seed_state=11,
        safety_car_base_probability=0.2,
    )
    return MultiDriverRaceConfig(
        race_config=race_config,
        event_seed_state=5,
        drivers=[
            DriverConfig(
                driver_id="a",
                driver_name="Driver A",
                team_name="Alpha",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=80,
                pace_factor=1.0,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=10, compound=TyreCompound.HARD)],
            ),
            DriverConfig(
                driver_id="b",
                driver_name="Driver B",
                team_name="Beta",
                starting_compound=TyreCompound.SOFT,
                starting_fuel_kg=80,
                pace_factor=1.0,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=8, compound=TyreCompound.HARD)],
            ),
        ],
    )


def test_strategy_comparison_calculates_differences() -> None:
    response = CompetitiveStrategyService().compare_strategies(
        StrategyComparisonRequest(
            base_config=_config(),
            scenarios=[
                StrategyScenario(
                    scenario_name="wait",
                    driver_id="a",
                    strategy=[PitInstruction(lap=14, compound=TyreCompound.HARD)],
                )
            ],
        )
    )

    result = response.results[0]
    baseline_entry = next(
        entry for entry in response.baseline.classification if entry.driver_id == "a"
    )

    assert result.time_difference_seconds == round(
        result.total_race_time_seconds - baseline_entry.total_race_time_seconds,
        6,
    )
    assert result.position_difference == baseline_entry.position - result.final_position


def test_pit_strategy_changes_outcome() -> None:
    service = CompetitiveStrategyService()
    baseline = service.simulate(_config())
    no_stop_config = _config().model_copy(
        update={
            "drivers": [
                _config().drivers[0].model_copy(update={"strategy": []}),
                _config().drivers[1],
            ]
        }
    )
    no_stop = service.simulate(no_stop_config)

    baseline_a = next(entry for entry in baseline.classification if entry.driver_id == "a")
    no_stop_a = next(entry for entry in no_stop.classification if entry.driver_id == "a")

    assert baseline_a.total_race_time_seconds != no_stop_a.total_race_time_seconds
