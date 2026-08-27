from sqlalchemy.orm import Session

from app.services.season_simulator import SeasonSimulator
from tests.season_helpers import season_db, season_request


def test_constructor_points_equal_sum_of_driver_points(season_db: Session) -> None:
    service = SeasonSimulator()
    season = service.create_season(season_request(season_db), season_db)

    completed = service.simulate_remaining(season.id, season_db)
    driver_points_by_team: dict[str, float] = {}
    for driver in completed.driver_standings:
        driver_points_by_team[driver.team_name] = (
            driver_points_by_team.get(driver.team_name, 0.0) + driver.points
        )

    for constructor in completed.constructor_standings:
        assert constructor.points == driver_points_by_team[constructor.team_name]


def test_constructor_standings_are_sorted_by_points(season_db: Session) -> None:
    service = SeasonSimulator()
    season = service.create_season(season_request(season_db), season_db)

    completed = service.simulate_remaining(season.id, season_db)
    points = [constructor.points for constructor in completed.constructor_standings]

    assert points == sorted(points, reverse=True)
