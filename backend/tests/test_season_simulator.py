from sqlalchemy.orm import Session

from app.services.season_simulator import SeasonSimulator
from tests.season_helpers import season_db, season_request


def test_run_next_race_increments_current_round(season_db: Session) -> None:
    service = SeasonSimulator()
    season = service.create_season(season_request(season_db), season_db)

    result = service.run_next_race(season.id, season_db)

    assert result.season.current_round == 1
    assert result.season.calendar[0].completed is True
    assert result.race_result is not None


def test_full_season_completes_all_calendar_races(season_db: Session) -> None:
    service = SeasonSimulator()
    season = service.create_season(season_request(season_db), season_db)

    completed = service.simulate_remaining(season.id, season_db)

    assert completed.status == "COMPLETED"
    assert completed.current_round == completed.total_rounds
    assert all(race.completed for race in completed.calendar)


def test_points_are_awarded_by_position(season_db: Session) -> None:
    service = SeasonSimulator()
    season = service.create_season(season_request(season_db), season_db)

    result = service.run_next_race(season.id, season_db)
    leader = result.season.driver_standings[0]

    assert leader.wins == 1
    assert leader.points == 25
