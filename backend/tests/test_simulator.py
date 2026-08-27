import time

from fastapi.testclient import TestClient

from app.main import app
from app.models.circuit import CircuitConfig
from app.schemas.simulation import PitInstruction, RaceConfig, TyreCompound
from app.services.simulator import RaceSimulator


client = TestClient(app)


def valid_payload() -> dict[str, object]:
    return {
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
    }


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


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_validate_simulation_config() -> None:
    response = client.post("/api/simulation/validate", json=valid_payload())

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "circuit": "Monza",
        "total_laps": 57,
        "starting_compound": "MEDIUM",
    }


def test_validate_simulation_rejects_invalid_body() -> None:
    payload = valid_payload()
    payload["starting_compound"] = "DRY"

    response = client.post("/api/simulation/validate", json=payload)

    assert response.status_code == 422


def test_complete_race_simulation() -> None:
    result = RaceSimulator().run(default_config())

    assert result.completed_laps == 57
    assert len(result.lap_results) == 57


def test_fuel_decreases_and_never_goes_negative() -> None:
    result = RaceSimulator().run(default_config())

    assert result.lap_results[0].fuel_remaining_kg < 100.0
    assert result.final_fuel_remaining_kg >= 0.0
    assert result.lap_results[-1].fuel_remaining_kg == result.final_fuel_remaining_kg


def test_tyre_age_increases_without_pit_stop() -> None:
    result = RaceSimulator().run(default_config())

    tyre_ages = [lap.tyre_age for lap in result.lap_results]

    assert tyre_ages == list(range(1, 58))


def test_simulation_is_deterministic() -> None:
    simulator = RaceSimulator()
    config = default_config()

    result_1 = simulator.run(config)
    result_2 = simulator.run(config)

    assert result_1.final_race_time_seconds == result_2.final_race_time_seconds
    assert [lap.lap_time_seconds for lap in result_1.lap_results] == [
        lap.lap_time_seconds for lap in result_2.lap_results
    ]
    assert result_1.weather_history == result_2.weather_history


def test_predefined_pit_stop_changes_compound_and_resets_tyre_age() -> None:
    config = default_config()
    pit_plan = [PitInstruction(lap=20, compound=TyreCompound.HARD)]

    result = RaceSimulator().run(config, pit_plan=pit_plan)
    lap_20 = result.lap_results[19]

    assert len(result.pit_stops) == 1
    assert result.pit_stops[0].lap_number == 20
    assert result.pit_stops[0].old_compound == TyreCompound.MEDIUM
    assert result.pit_stops[0].new_compound == TyreCompound.HARD
    assert (
        result.pit_stops[0].pit_time_loss_seconds
        == config.circuit.pit_lane_time_loss_seconds
    )
    assert lap_20.compound == TyreCompound.HARD
    assert lap_20.tyre_age == 1
    assert lap_20.lap_time_seconds > config.circuit.pit_lane_time_loss_seconds


def test_default_57_lap_simulation_runs_under_two_seconds() -> None:
    simulator = RaceSimulator()
    start = time.perf_counter()

    result = simulator.run(default_config())

    elapsed = time.perf_counter() - start
    assert result.completed_laps == 57
    assert elapsed < 2.0


def test_run_simulation_endpoint() -> None:
    response = client.post("/api/simulation/run", json=valid_payload())
    body = response.json()

    assert response.status_code == 200
    assert body["completed_laps"] == 57
    assert len(body["lap_results"]) == 57
    assert body["final_race_time_seconds"] > 0


def test_run_simulation_rejects_invalid_body() -> None:
    payload = valid_payload()
    payload["safety_car_base_probability"] = 1.5

    response = client.post("/api/simulation/run", json=payload)

    assert response.status_code == 422
