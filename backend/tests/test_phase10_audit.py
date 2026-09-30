"""Contract and configuration checks for the Phase 10 audit."""

import inspect
from collections.abc import Callable

from fastapi.params import Depends
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.routes import circuits, live_race, races, seasons


client = TestClient(app)


def race_config_payload() -> dict[str, object]:
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


def test_phase10_strategy_endpoint_contracts() -> None:
    driver = {
        "driver_name": "PitWall Driver",
        "position": 5,
        "compound": "MEDIUM",
        "tyre_age": 16,
        "gap_to_driver_ahead_seconds": 1.2,
        "current_lap": 20,
        "base_lap_time_seconds": 85.0,
        "degradation_per_lap": 0.08,
    }
    cases = [
        (
            "/api/strategy/analyze",
            race_config_payload(),
            {"recommended_strategy", "strategies"},
        ),
        (
            "/api/strategy/undercut",
            {
                "attacker": driver,
                "defender": {**driver, "driver_name": "Driver Ahead", "position": 4},
                "pit_lane_time_loss_seconds": 22.0,
                "new_compound": "HARD",
                "defender_stays_out_laps": 2,
            },
            {
                "undercut_available",
                "projected_gain_seconds",
                "confidence",
                "recommendation",
            },
        ),
        (
            "/api/strategy/overcut",
            {
                "driver": driver,
                "opponent": {**driver, "driver_name": "Driver Ahead", "position": 4},
                "pit_lane_time_loss_seconds": 22.0,
                "max_stay_out_laps": 3,
            },
            {"overcut_available", "confidence", "recommendation", "options"},
        ),
        (
            "/api/strategy/pit-window",
            {
                "driver": {**driver, "current_lap": 20, "total_laps": 57},
                "pit_lane_time_loss_seconds": 22.0,
                "earliest_pit_lap": 21,
                "latest_pit_lap": 27,
                "new_compound": "HARD",
            },
            {"earliest_lap", "optimal_lap", "latest_lap", "confidence", "options"},
        ),
        (
            "/api/strategy/opponent-prediction",
            {
                "driver_name": "Driver Ahead",
                "position": 4,
                "compound": "MEDIUM",
                "tyre_age": 18,
                "current_lap": 20,
                "total_laps": 57,
                "base_lap_time_seconds": 85.0,
                "degradation_per_lap": 0.1,
                "pit_stops_completed": 0,
                "weather_risk": 0.1,
                "prediction_window_laps": 5,
            },
            {"most_likely_pit_lap", "most_likely_probability", "confidence", "predictions"},
        ),
        (
            "/api/strategy/traffic",
            {
                "driver": {
                    "driver_name": "PitWall Driver",
                    "current_position": 5,
                    "current_lap": 20,
                    "base_lap_time_seconds": 85.0,
                },
                "car_ahead": {
                    "driver_name": "Driver Ahead",
                    "gap_seconds": 1.2,
                    "pace_delta_seconds": 0.15,
                    "overtaking_difficulty": 0.7,
                },
                "laps_in_traffic": 5,
            },
            {
                "dirty_air_penalty_seconds",
                "projected_traffic_loss_seconds",
                "traffic_risk",
                "recommendation",
            },
        ),
        (
            "/api/strategy/risk",
            {
                "weather_risk": 0.1,
                "traffic_risk": "MEDIUM",
                "tyre_age": 16,
                "estimated_tyre_life": 30,
                "degradation_per_lap": 0.08,
                "safety_car_probability": 0.15,
                "opponent_pit_probability": 50.0,
                "pit_lane_time_loss_seconds": 22.0,
            },
            {
                "overall_risk_score",
                "risk_level",
                "weather_risk_score",
                "recommendation",
            },
        ),
    ]

    for path, payload, expected_fields in cases:
        response = client.post(path, json=payload)

        assert response.status_code == 200, response.text
        assert expected_fields <= response.json().keys()


def test_cors_allows_the_frontend_origin() -> None:
    response = client.options(
        "/api/simulation/run",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_database_routes_use_get_db_dependency() -> None:
    database_routes: tuple[Callable[..., object], ...] = (
        circuits.list_circuits,
        circuits.get_circuit,
        circuits.get_circuit_config,
        races.list_races,
        races.get_race,
        races.get_race_laps,
        races.get_race_pit_stops,
        live_race.start_live_race,
        live_race.get_live_race,
        live_race.advance_live_race,
        live_race.submit_live_action,
        live_race.pit_live_race,
        live_race.live_recommendation,
        seasons.create_season,
        seasons.get_season,
        seasons.get_standings,
        seasons.get_calendar,
        seasons.run_next_race,
        seasons.simulate_remaining,
        seasons.analyze_scenario,
        seasons.project_championship,
    )

    for route in database_routes:
        dependency = inspect.signature(route).parameters["db"].default

        assert isinstance(dependency, Depends)
        assert dependency.dependency is get_db
