import statistics

from fastapi.testclient import TestClient

from app.main import app
from app.models.circuit import CircuitConfig
from app.schemas.simulation import RaceConfig, StrategyStint, TyreCompound
from app.services.strategy_engine import CandidateStrategy, Perturbation, StrategyEngine


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


def test_strategy_generation_produces_candidates() -> None:
    candidates = StrategyEngine().generate_candidate_strategies(default_config())

    assert len(candidates) >= 1
    assert all(candidate.stints for candidate in candidates)


def test_strategy_analysis_is_ranked_by_expected_race_time() -> None:
    response = StrategyEngine().analyze(default_config())
    times = [strategy.expected_race_time_seconds for strategy in response.strategies]

    assert times == sorted(times)
    assert response.recommended_strategy == response.strategies[0]


def test_strategy_confidence_is_between_zero_and_one() -> None:
    response = StrategyEngine().analyze(default_config())

    assert response.strategies
    assert all(0.0 <= strategy.confidence <= 1.0 for strategy in response.strategies)


def test_every_strategy_runs_exactly_twenty_perturbations() -> None:
    engine = StrategyEngine()
    response = engine.analyze(default_config())

    assert response.strategies
    assert set(engine.last_perturbation_counts) == {
        strategy.strategy_id for strategy in response.strategies
    }
    assert all(count == 20 for count in engine.last_perturbation_counts.values())


def test_strategy_analysis_is_deterministic() -> None:
    engine = StrategyEngine()
    config = default_config()

    first = engine.analyze(config)
    second = engine.analyze(config)

    assert [strategy.strategy_id for strategy in first.strategies] == [
        strategy.strategy_id for strategy in second.strategies
    ]
    assert [strategy.expected_race_time_seconds for strategy in first.strategies] == [
        strategy.expected_race_time_seconds for strategy in second.strategies
    ]
    assert [strategy.confidence for strategy in first.strategies] == [
        strategy.confidence for strategy in second.strategies
    ]


def test_perturbation_bounds() -> None:
    perturbations = StrategyEngine().generate_perturbations(
        default_config(),
        "MEDIUM-HARD-25",
    )

    assert len(perturbations) == 20
    for perturbation in perturbations:
        assert 0.85 <= perturbation.rain_probability_multiplier <= 1.15
        assert 0.0 <= min(1.0, 0.60 * perturbation.rain_probability_multiplier) <= 1.0
        assert 0.90 <= perturbation.degradation_multiplier <= 1.10
        assert perturbation.degradation_multiplier >= 0


def test_confidence_uses_required_formula() -> None:
    class FixedResult:
        def __init__(self, final_race_time_seconds: float) -> None:
            self.final_race_time_seconds = final_race_time_seconds

    class FixedSimulator:
        def __init__(self) -> None:
            self.times = iter(float(value) for value in range(100, 120))

        def run(self, *args: object, **kwargs: object) -> FixedResult:
            return FixedResult(next(self.times))

    engine = StrategyEngine(simulator=FixedSimulator())  # type: ignore[arg-type]
    candidate = CandidateStrategy(
        strategy_id="FIXED",
        stints=(StrategyStint(compound=TyreCompound.MEDIUM, start_lap=1, end_lap=57),),
        recommendation_reason="Formula test.",
    )
    times = [float(value) for value in range(100, 120)]
    expected = round(
        max(0.0, min(1.0, 1 - (statistics.pstdev(times) / statistics.mean(times)))),
        6,
    )

    assert engine.calculate_confidence(default_config(), candidate) == expected
    assert engine.last_perturbation_counts["FIXED"] == 20


def test_strategy_endpoint_returns_ranked_strategies() -> None:
    response = client.post("/api/strategy/analyze", json=default_payload())
    body = response.json()

    assert response.status_code == 200
    assert body["recommended_strategy"] == body["strategies"][0]
    assert len(body["strategies"]) >= 1
    assert body["strategies"][0]["expected_race_time_seconds"] > 0


def test_strategy_endpoint_rejects_invalid_race_config() -> None:
    payload = default_payload()
    payload["starting_compound"] = "DRY"

    response = client.post("/api/strategy/analyze", json=payload)

    assert response.status_code == 422
