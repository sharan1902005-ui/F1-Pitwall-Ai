from fastapi.testclient import TestClient

from app.main import app
from app.models.circuit import CircuitConfig
from app.schemas.live_race import LiveActionType, RaceStatus
from app.schemas.simulation import RaceConfig, TyreCompound
from app.services.live_race_service import LiveRaceService


client = TestClient(app)


def config(laps: int = 6, safety_car_probability: float = 0.15) -> RaceConfig:
    return RaceConfig(
        circuit=CircuitConfig(
            circuit_name="Monza",
            total_laps=laps,
            base_lap_time_seconds=85.0,
            pit_lane_time_loss_seconds=22.0,
            avg_track_temp=35.0,
            avg_air_temp=28.0,
        ),
        starting_compound="MEDIUM",
        starting_fuel_kg=30.0,
        weather_seed_state=42,
        safety_car_base_probability=safety_car_probability,
    )


def test_live_race_lifecycle_start_advance_finish() -> None:
    service = LiveRaceService()
    started = service.start(config(laps=3), event_seed_state=1)

    assert started.race_state.current_lap == 0
    race_id = started.race_id
    for _ in range(3):
        response = service.advance(race_id)

    assert response.race_state.current_lap == 3
    assert response.race_state.race_status == RaceStatus.FINISHED
    assert len(response.race_state.history) == 3


def test_live_race_is_deterministic_for_same_actions_and_seeds() -> None:
    actions = [
        {"action": LiveActionType.STAY_OUT},
        {"action": LiveActionType.PIT, "compound": TyreCompound.HARD},
        {"action": LiveActionType.STAY_OUT},
    ]
    outputs = []
    for _ in range(2):
        service = LiveRaceService()
        started = service.start(config(laps=3), event_seed_state=5)
        race_id = started.race_id
        for action in actions:
            service.submit_action(race_id, action)  # type: ignore[arg-type]
            service.advance(race_id)
        state = service.get(race_id)
        outputs.append(
            (
                [lap.lap_time_seconds for lap in state.history],
                state.weather_history,
                state.actions,
                state.current_race_time,
            )
        )

    assert outputs[0] == outputs[1]


def test_actions_stay_out_pit_and_follow_recommendation() -> None:
    service = LiveRaceService()
    started = service.start(config(laps=4), event_seed_state=1)
    race_id = started.race_id

    service.submit_action(race_id, {"action": "STAY_OUT"})  # type: ignore[arg-type]
    service.advance(race_id)
    service.submit_action(race_id, {"action": "PIT", "compound": "HARD"})  # type: ignore[arg-type]
    service.advance(race_id)
    service.submit_action(race_id, {"action": "FOLLOW_RECOMMENDATION"})  # type: ignore[arg-type]
    service.advance(race_id)

    state = service.get(race_id)
    assert [action.user_action for action in state.actions[:3]] == [
        LiveActionType.STAY_OUT,
        LiveActionType.PIT,
        LiveActionType.FOLLOW_RECOMMENDATION,
    ]
    assert state.pit_stop_count >= 1


def test_live_race_api_start_advance_and_recommendation() -> None:
    response = client.post(
        "/api/live-race/start?event_seed_state=2",
        json=config(laps=3).model_dump(mode="json"),
    )
    body = response.json()

    assert response.status_code == 200
    race_id = body["race_id"]
    advance = client.post(f"/api/live-race/{race_id}/advance")
    recommendation = client.post(f"/api/live-race/{race_id}/recommendation")

    assert advance.status_code == 200
    assert advance.json()["current_lap"] == 1
    assert recommendation.status_code == 200
    assert recommendation.json()["recommendation"]["decision"]


def test_live_race_completion_status() -> None:
    service = LiveRaceService()
    started = service.start(config(laps=2), event_seed_state=1)

    service.advance(started.race_id)
    result = service.advance(started.race_id)

    assert result.current_lap == 2
    assert result.race_status == RaceStatus.FINISHED
