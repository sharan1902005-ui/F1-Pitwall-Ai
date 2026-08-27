from fastapi.testclient import TestClient

from app.main import app
from app.models.circuit import CircuitConfig
from app.schemas.race_engineer import ScenarioRequest
from app.schemas.simulation import RaceConfig
from app.services.scenario_service import ScenarioService
from app.services.strategy_engine import StrategyEngine


client = TestClient(app)


def default_config() -> RaceConfig:
    return RaceConfig(
        circuit=CircuitConfig(
            circuit_name="Monza",
            total_laps=57,
            base_lap_time_seconds=85.0,
            pit_lane_time_loss_seconds=22.0,
            avg_track_temp=35.0,
            avg_air_temp=28.0,
        ),
        starting_compound="MEDIUM",
        starting_fuel_kg=100.0,
        weather_seed_state=42,
        safety_car_base_probability=0.15,
    )


def scenario_payload() -> dict[str, object]:
    return {
        "race_config": {
            "circuit": {
                "circuit_name": "Monza",
                "total_laps": 57,
                "base_lap_time_seconds": 85.0,
                "pit_lane_time_loss_seconds": 22.0,
                "avg_track_temp": 35.0,
                "avg_air_temp": 28.0,
            },
            "starting_compound": "MEDIUM",
            "starting_fuel_kg": 100.0,
            "weather_seed_state": 42,
            "safety_car_base_probability": 0.15,
        },
        "scenario_type": "DEGRADATION_INCREASE",
        "scenario_parameters": {"percent": 0.10},
    }


def test_scenario_analysis_runs_baseline_and_scenario() -> None:
    request = ScenarioRequest(
        race_config=default_config(),
        scenario_type="DEGRADATION_INCREASE",
        scenario_parameters={"percent": 0.10},
    )

    response = ScenarioService().analyze(request)

    assert response.baseline_race_time > 0
    assert response.scenario_race_time > 0
    assert response.engineer_explanation.explanation


def test_time_difference_is_calculated_from_strategy_outputs() -> None:
    config = default_config()
    expected_baseline = StrategyEngine().analyze(config).recommended_strategy
    expected_scenario = StrategyEngine().analyze(
        config,
        degradation_multiplier=1.10,
    ).recommended_strategy

    assert expected_baseline is not None
    assert expected_scenario is not None
    response = ScenarioService().analyze(
        ScenarioRequest(
            race_config=config,
            scenario_type="DEGRADATION_INCREASE",
            scenario_parameters={"percent": 0.10},
        )
    )

    assert response.baseline_race_time == expected_baseline.expected_race_time_seconds
    assert response.scenario_race_time == expected_scenario.expected_race_time_seconds
    assert response.time_difference == round(
        response.scenario_race_time - response.baseline_race_time,
        6,
    )


def test_strategy_changed_matches_strategy_ids() -> None:
    response = ScenarioService().analyze(
        ScenarioRequest(
            race_config=default_config(),
            scenario_type="RAIN_INTENSITY_INCREASE",
            scenario_parameters={"percent": 0.20},
        )
    )

    assert response.strategy_changed == (
        response.baseline_strategy != response.scenario_strategy
    )


def test_invalid_scenario_parameter_raises_value_error() -> None:
    request = ScenarioRequest(
        race_config=default_config(),
        scenario_type="DEGRADATION_INCREASE",
        scenario_parameters={"percent": -0.10},
    )

    try:
        ScenarioService().analyze(request)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("Expected invalid scenario to raise ValueError")


def test_scenario_endpoint_returns_response() -> None:
    response = client.post("/api/race-engineer/scenario", json=scenario_payload())
    body = response.json()

    assert response.status_code == 200
    assert body["baseline_race_time"] > 0
    assert body["scenario_race_time"] > 0
    assert body["time_difference"] == round(
        body["scenario_race_time"] - body["baseline_race_time"],
        6,
    )
    assert body["engineer_explanation"]["explanation"]


def test_scenario_endpoint_returns_422_for_invalid_parameter() -> None:
    payload = scenario_payload()
    payload["scenario_parameters"] = {"percent": -0.10}

    response = client.post("/api/race-engineer/scenario", json=payload)

    assert response.status_code == 422
