from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


client = TestClient(app)


def setup_module() -> None:
    init_db(seed=True)


def test_circuit_api_returns_seeded_circuits() -> None:
    response = client.get("/api/circuits")
    body = response.json()

    assert response.status_code == 200
    assert len(body) >= 3
    assert {"Monza", "Silverstone", "Monaco"}.issubset(
        {circuit["name"] for circuit in body}
    )


def test_circuit_detail_and_config_endpoints() -> None:
    circuits = client.get("/api/circuits").json()
    monza = next(circuit for circuit in circuits if circuit["name"] == "Monza")

    detail = client.get(f"/api/circuits/{monza['id']}")
    config = client.get(f"/api/circuits/{monza['id']}/config")

    assert detail.status_code == 200
    assert detail.json()["name"] == "Monza"
    assert config.status_code == 200
    assert config.json() == {
        "circuit_name": "Monza",
        "total_laps": 57,
        "base_lap_time_seconds": 85.0,
        "pit_lane_time_loss_seconds": 22.0,
        "avg_track_temp": 35.0,
        "avg_air_temp": 28.0,
    }


def test_historical_race_lap_and_pit_stop_endpoints() -> None:
    races = client.get("/api/races").json()
    race_id = races[0]["id"]

    race_response = client.get(f"/api/races/{race_id}")
    laps_response = client.get(f"/api/races/{race_id}/laps?limit=2")
    pit_stops_response = client.get(f"/api/races/{race_id}/pit-stops")

    assert race_response.status_code == 200
    assert laps_response.status_code == 200
    assert len(laps_response.json()) <= 2
    assert pit_stops_response.status_code == 200
    assert isinstance(pit_stops_response.json(), list)


def test_missing_circuit_and_race_return_404() -> None:
    assert client.get("/api/circuits/999999").status_code == 404
    assert client.get("/api/races/999999").status_code == 404
