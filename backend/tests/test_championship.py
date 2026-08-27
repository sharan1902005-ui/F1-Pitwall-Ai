from sqlalchemy.orm import Session

from app.schemas.season import SeasonScenarioRequest
from app.services.season_simulator import SeasonSimulator
from tests.season_helpers import season_db, season_request


def test_driver_standings_accumulate_points(season_db: Session) -> None:
    service = SeasonSimulator()
    season = service.create_season(season_request(season_db), season_db)

    after_round_one = service.run_next_race(season.id, season_db).season
    after_round_two = service.run_next_race(season.id, season_db).season

    round_one_points = {driver.driver_id: driver.points for driver in after_round_one.driver_standings}
    round_two_points = {driver.driver_id: driver.points for driver in after_round_two.driver_standings}

    assert any(round_two_points[driver_id] > round_one_points[driver_id] for driver_id in round_one_points)
    assert sum(round_two_points.values()) > sum(round_one_points.values())


def test_scenario_analysis_preserves_baseline(season_db: Session) -> None:
    service = SeasonSimulator()
    season = service.create_season(season_request(season_db), season_db)
    baseline = service.run_next_race(season.id, season_db).season

    scenario = service.scenario(
        season.id,
        request=SeasonScenarioRequest(
            driver_id="b",
            round_number=1,
            hypothetical_position=1,
        ),
        db=season_db,
    )
    after = service.get_season(season.id, season_db)

    assert baseline.driver_standings == after.driver_standings
    assert scenario.hypothetical is True
    assert scenario.selected_driver_delta.points_difference != 0
