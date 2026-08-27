from sqlalchemy.orm import Session

from app.services.season_simulator import SeasonSimulator
from tests.season_helpers import season_db, season_request


def test_same_season_config_and_seeds_are_deterministic(season_db: Session) -> None:
    service = SeasonSimulator()
    first = service.create_season(season_request(season_db), season_db)
    second = service.create_season(season_request(season_db), season_db)

    first_completed = service.simulate_remaining(first.id, season_db)
    second_completed = service.simulate_remaining(second.id, season_db)

    assert first_completed.driver_standings == second_completed.driver_standings
    assert first_completed.constructor_standings == second_completed.constructor_standings
    assert first_completed.calendar == second_completed.calendar


def test_projection_is_seeded_and_repeatable(season_db: Session) -> None:
    service = SeasonSimulator()
    season = service.create_season(season_request(season_db), season_db)
    service.run_next_race(season.id, season_db)

    first = service.projection(season.id, season_db, simulations=4)
    second = service.projection(season.id, season_db, simulations=4)

    assert first == second
    assert first.simulations == 4
