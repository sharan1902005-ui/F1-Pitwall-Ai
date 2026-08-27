from fastapi.testclient import TestClient

from app.main import app
from app.models.circuit import CircuitConfig
from app.schemas.race_engineer import RaceContext
from app.schemas.simulation import RaceConfig, TyreCompound
from app.services.race_engineer import (
    OptionalLLMRaceEngineerProvider,
    RaceEngineer,
)
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


def default_payload() -> dict[str, object]:
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
        }
    }


def wet_context() -> RaceContext:
    return RaceContext(
        current_lap=27,
        total_laps=57,
        current_compound="MEDIUM",
        tyre_age=26,
        fuel_remaining_kg=52.0,
        track_wetness=0.52,
        rain_probability=0.78,
        rain_intensity=0.61,
        track_temperature=29.4,
        air_temperature=24.8,
        current_position=3,
        recent_lap_times=[95.2, 96.4, 98.1],
    )


def test_deterministic_fallback_works_without_llm_key() -> None:
    config = default_config()
    strategy = StrategyEngine().analyze(config).recommended_strategy

    assert strategy is not None
    response = RaceEngineer().explain_strategy(config, strategy)

    assert response.explanation
    assert response.confidence == strategy.confidence
    assert response.risk == strategy.risk


def test_strategy_grounding_does_not_change_engine_output() -> None:
    config = default_config()
    strategy = StrategyEngine().analyze(config).recommended_strategy

    assert strategy is not None
    response = RaceEngineer().explain_strategy(config, strategy)

    expected_compound = strategy.stints[1].compound
    assert response.recommended_compound == expected_compound
    assert response.recommended_pit_lap == strategy.pit_laps[0]
    assert response.confidence == strategy.confidence


def test_wet_track_context_explanation_references_actual_values() -> None:
    config = default_config()
    strategy = StrategyEngine().analyze(config).recommended_strategy
    context = wet_context()

    assert strategy is not None
    response = RaceEngineer().explain_strategy(config, strategy, context)
    key_text = " ".join(response.key_factors)

    assert "0.520" in key_text
    assert context.current_compound.value in key_text
    assert response.recommended_compound.value in key_text


def test_unavailable_llm_provider_uses_deterministic_fallback() -> None:
    config = default_config()
    strategy = StrategyEngine().analyze(config).recommended_strategy

    assert strategy is not None
    response = OptionalLLMRaceEngineerProvider().generate_explanation(
        config,
        strategy,
        None,
    )

    assert response.decision
    assert response.confidence == strategy.confidence


def test_explain_strategy_endpoint() -> None:
    response = client.post("/api/race-engineer/explain-strategy", json=default_payload())
    body = response.json()

    assert response.status_code == 200
    assert body["recommended_compound"] == "INTERMEDIATE"
    assert body["recommended_pit_lap"] == 2
    assert body["confidence"] is not None


def test_explain_strategy_endpoint_returns_404_for_missing_strategy() -> None:
    payload = default_payload()
    payload["strategy_id"] = "NOT-A-REAL-STRATEGY"

    response = client.post("/api/race-engineer/explain-strategy", json=payload)

    assert response.status_code == 404


def test_decision_endpoint_uses_context() -> None:
    payload = default_payload()
    payload["context"] = wet_context().model_dump(mode="json")

    response = client.post("/api/race-engineer/decision", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert "0.520" in " ".join(body["key_factors"])
    assert body["decision"] == "BOX FOR INTERMEDIATE"
