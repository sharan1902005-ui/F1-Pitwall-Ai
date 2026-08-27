"""Persistent championship season simulator."""

import json
from collections import defaultdict
from copy import deepcopy

from sqlalchemy.orm import Session

from app.models.circuit import CircuitConfig
from app.models.historical import Circuit
from app.models.season import (
    Season,
    SeasonConstructorStanding,
    SeasonDriverStanding,
    SeasonRace,
)
from app.schemas.multi_race import DriverConfig, MultiDriverRaceConfig, MultiDriverRaceResult
from app.schemas.season import (
    ChampionshipProjectionEntry,
    ChampionshipProjectionResponse,
    ConstructorStandingResponse,
    DriverSeasonAnalysis,
    DriverStandingResponse,
    MomentumLabel,
    PointsSystem,
    SeasonAnalyticsResponse,
    SeasonCalendarRound,
    SeasonCreateRequest,
    SeasonRaceResult,
    SeasonRaceSummary,
    SeasonResponse,
    SeasonScenarioRequest,
    SeasonScenarioResponse,
    SeasonScenarioStandingDelta,
    SeasonStatus,
    StrategySeasonMetric,
)
from app.schemas.simulation import RaceConfig
from app.services.circuit_service import CircuitService
from app.services.multi_driver_simulator import MultiDriverRaceSimulator


class SeasonNotFoundError(LookupError):
    """Raised when a season cannot be found."""


class SeasonStateError(RuntimeError):
    """Raised when a season operation is not valid."""


class SeasonSimulator:
    """Create and advance persistent championship seasons."""

    def __init__(
        self,
        circuit_service: CircuitService | None = None,
        race_simulator: MultiDriverRaceSimulator | None = None,
    ) -> None:
        self.circuit_service = circuit_service or CircuitService()
        self.race_simulator = race_simulator or MultiDriverRaceSimulator()

    def create_season(self, request: SeasonCreateRequest, db: Session) -> SeasonResponse:
        """Create a persistent season and empty standings."""
        circuits = self._circuits_for_calendar(request.calendar, db)
        season = Season(
            season_name=request.season_name,
            current_round=0,
            total_rounds=len(request.calendar),
            weather_seed=request.weather_seed,
            event_seed=request.event_seed,
            points_system_json=self._json(request.points_system.model_dump(mode="json")),
            config_json=self._json(request.model_dump(mode="json")),
            status=SeasonStatus.CREATED.value,
        )
        db.add(season)
        db.flush()

        for calendar_round in request.calendar:
            circuit = circuits[calendar_round.circuit_id]
            db.add(
                SeasonRace(
                    season_id=season.id,
                    round_number=calendar_round.round_number,
                    circuit_id=circuit.id,
                    circuit_name=circuit.name,
                    total_laps=circuit.total_laps,
                    base_lap_time_seconds=circuit.base_lap_time_seconds,
                    pit_lane_time_loss_seconds=circuit.pit_lane_time_loss_seconds,
                    avg_track_temp=circuit.avg_track_temp,
                    avg_air_temp=circuit.avg_air_temp,
                )
            )
        for driver in request.drivers:
            db.add(
                SeasonDriverStanding(
                    season_id=season.id,
                    driver_id=driver.driver_id,
                    driver_name=driver.driver_name,
                    team_name=driver.team_name,
                )
            )
        for team_name in sorted({driver.team_name for driver in request.drivers}):
            db.add(SeasonConstructorStanding(season_id=season.id, team_name=team_name))
        db.commit()
        db.refresh(season)
        return self.get_season(season.id, db)

    def get_season(self, season_id: int, db: Session) -> SeasonResponse:
        """Return complete season state."""
        season = self._get_season_model(season_id, db)
        return self._season_response(season)

    def calendar(self, season_id: int, db: Session) -> list[SeasonRaceSummary]:
        """Return the season calendar."""
        season = self._get_season_model(season_id, db)
        return [self._race_summary(race) for race in season.races]

    def standings(
        self,
        season_id: int,
        db: Session,
    ) -> tuple[list[DriverStandingResponse], list[ConstructorStandingResponse]]:
        """Return driver and constructor standings."""
        season = self._get_season_model(season_id, db)
        return self._driver_standings(season), self._constructor_standings(season)

    def run_next_race(self, season_id: int, db: Session) -> SeasonRaceResult:
        """Run the next incomplete championship round."""
        season = self._get_season_model(season_id, db)
        if season.current_round >= season.total_rounds:
            raise SeasonStateError("Season is already complete")
        next_race = next((race for race in season.races if not race.completed), None)
        if next_race is None:
            raise SeasonStateError("No incomplete race remains")
        race_result = self._run_round(season, next_race, db)
        db.commit()
        db.refresh(season)
        return SeasonRaceResult(season=self._season_response(season), race_result=race_result)

    def simulate_remaining(self, season_id: int, db: Session) -> SeasonResponse:
        """Run all remaining races in order."""
        season = self._get_season_model(season_id, db)
        while season.current_round < season.total_rounds:
            next_race = next((race for race in season.races if not race.completed), None)
            if next_race is None:
                break
            self._run_round(season, next_race, db)
        db.commit()
        db.refresh(season)
        return self._season_response(season)

    def scenario(
        self,
        season_id: int,
        request: SeasonScenarioRequest,
        db: Session,
    ) -> SeasonScenarioResponse:
        """Run a non-mutating hypothetical standings scenario."""
        season = self._get_season_model(season_id, db)
        points_system = self._points_system(season)
        if request.driver_id not in {standing.driver_id for standing in season.driver_standings}:
            raise ValueError(f"Driver not found: {request.driver_id}")
        if request.round_number < 1 or request.round_number > season.total_rounds:
            raise ValueError("Scenario round is outside this season")

        baseline = self._driver_standings(season)
        scenario_points = {standing.driver_id: standing.points for standing in baseline}
        race = next(race for race in season.races if race.round_number == request.round_number)
        previous_points = self._race_points(race).get(request.driver_id, 0.0)
        hypothetical_points = points_system.points_by_position.get(request.hypothetical_position, 0.0)
        scenario_points[request.driver_id] = (
            scenario_points[request.driver_id] - previous_points + hypothetical_points
        )
        scenario = self._standings_from_points(season, scenario_points)
        baseline_entry = next(entry for entry in baseline if entry.driver_id == request.driver_id)
        scenario_entry = next(entry for entry in scenario if entry.driver_id == request.driver_id)

        return SeasonScenarioResponse(
            hypothetical=True,
            baseline_standings=baseline,
            scenario_standings=scenario,
            selected_driver_delta=SeasonScenarioStandingDelta(
                driver_id=request.driver_id,
                baseline_position=baseline_entry.position,
                scenario_position=scenario_entry.position,
                baseline_points=baseline_entry.points,
                scenario_points=scenario_entry.points,
                points_difference=round(scenario_entry.points - baseline_entry.points, 6),
                position_difference=baseline_entry.position - scenario_entry.position,
            ),
            championship_leader_changed=(
                bool(baseline)
                and bool(scenario)
                and baseline[0].driver_id != scenario[0].driver_id
            ),
        )

    def projection(
        self,
        season_id: int,
        db: Session,
        simulations: int = 20,
    ) -> ChampionshipProjectionResponse:
        """Run optional deterministic projection simulations for remaining rounds."""
        season = self._get_season_model(season_id, db)
        simulations = max(1, min(50, simulations))
        config = SeasonCreateRequest.model_validate(self._config(season))
        points_system = self._points_system(season)
        current_points = {
            standing.driver_id: standing.points
            for standing in self._driver_standings(season)
        }
        win_counts = defaultdict(int)
        points_totals = defaultdict(float)
        position_totals = defaultdict(float)

        remaining_rounds = [
            race for race in season.races if not race.completed
        ]
        for simulation_index in range(simulations):
            projected_points = dict(current_points)
            for race in remaining_rounds:
                race_result = self._simulate_round_result(
                    season=season,
                    race=race,
                    drivers=config.drivers,
                    safety_car_base_probability=config.safety_car_base_probability,
                    weather_seed_offset=simulation_index * 7_919,
                    event_seed_offset=simulation_index * 3_571,
                )
                for entry in race_result.classification:
                    projected_points[entry.driver_id] = projected_points.get(entry.driver_id, 0.0) + (
                        points_system.points_by_position.get(entry.position, 0.0)
                    )
            ordered = sorted(
                projected_points.items(),
                key=lambda item: (-item[1], item[0]),
            )
            if ordered:
                win_counts[ordered[0][0]] += 1
            for position, (driver_id, points) in enumerate(ordered, start=1):
                points_totals[driver_id] += points
                position_totals[driver_id] += position

        projections = [
            ChampionshipProjectionEntry(
                driver_id=driver.driver_id,
                driver_name=driver.driver_name,
                championship_win_probability=round(win_counts[driver.driver_id] / simulations, 6),
                expected_final_points=round(points_totals[driver.driver_id] / simulations, 6),
                expected_final_position=round(position_totals[driver.driver_id] / simulations, 6),
            )
            for driver in config.drivers
        ]
        projections.sort(
            key=lambda entry: (
                -entry.championship_win_probability,
                -entry.expected_final_points,
                entry.driver_id,
            )
        )
        return ChampionshipProjectionResponse(
            simulations=simulations,
            methodology=(
                "Remaining rounds are replayed with the multi-driver simulator using "
                "deterministic seed perturbations; completed rounds remain fixed."
            ),
            seed_behavior=(
                "Projection run n adds n*7919 to weather seeds and n*3571 to event seeds."
            ),
            projections=projections,
        )

    def _run_round(
        self,
        season: Season,
        race: SeasonRace,
        db: Session,
    ) -> MultiDriverRaceResult:
        """Run one race, store result, and update standings."""
        config = SeasonCreateRequest.model_validate(self._config(season))
        race_result = self._simulate_round_result(
            season=season,
            race=race,
            drivers=config.drivers,
            safety_car_base_probability=config.safety_car_base_probability,
        )
        points_awarded = self._points_for_classification(race_result, self._points_system(season))
        race.result_json = race_result.model_dump_json()
        race.points_json = self._json(points_awarded)
        race.completed = 1
        race.winner_driver_id = race_result.classification[0].driver_id
        race.winner_driver_name = race_result.classification[0].driver_name
        self._apply_race_to_standings(season, race_result, points_awarded)
        season.current_round = max(season.current_round, race.round_number)
        season.status = (
            SeasonStatus.COMPLETED.value
            if season.current_round >= season.total_rounds
            else SeasonStatus.IN_PROGRESS.value
        )
        db.flush()
        return race_result

    def _simulate_round_result(
        self,
        season: Season,
        race: SeasonRace,
        drivers: list[DriverConfig],
        safety_car_base_probability: float,
        weather_seed_offset: int = 0,
        event_seed_offset: int = 0,
    ) -> MultiDriverRaceResult:
        """Build a race config from stored circuit data and run Phase 8 simulator."""
        circuit_config = self._circuit_config_from_race(race)
        race_config = RaceConfig(
            circuit=circuit_config,
            starting_compound=drivers[0].starting_compound,
            starting_fuel_kg=drivers[0].starting_fuel_kg,
            weather_seed_state=self._round_weather_seed(season, race.round_number) + weather_seed_offset,
            safety_car_base_probability=safety_car_base_probability,
        )
        multi_config = MultiDriverRaceConfig(
            race_config=race_config,
            drivers=drivers,
            event_seed_state=self._round_event_seed(season, race.round_number) + event_seed_offset,
        )
        return self.race_simulator.run(multi_config)

    def _apply_race_to_standings(
        self,
        season: Season,
        result: MultiDriverRaceResult,
        points_awarded: dict[str, float],
    ) -> None:
        """Apply one completed race result to stored standings."""
        driver_rows = {standing.driver_id: standing for standing in season.driver_standings}
        team_rows = {standing.team_name: standing for standing in season.constructor_standings}
        for entry in result.classification:
            standing = driver_rows[entry.driver_id]
            race_points = points_awarded.get(entry.driver_id, 0.0)
            standing.points = round(standing.points + race_points, 6)
            standing.races += 1
            standing.wins += 1 if entry.position == 1 else 0
            standing.podiums += 1 if entry.position <= 3 else 0
            standing.best_finish = (
                entry.position
                if standing.best_finish is None
                else min(standing.best_finish, entry.position)
            )
            standing.finish_sum += entry.position
            standing.total_race_time = round(
                standing.total_race_time + entry.total_race_time_seconds,
                6,
            )
            points_history = self._loads(standing.points_history_json, [])
            position_history = self._loads(standing.positions_history_json, [])
            points_history.append(race_points)
            position_history.append(entry.position)
            standing.points_history_json = self._json(points_history)
            standing.positions_history_json = self._json(position_history)

            constructor = team_rows[entry.team_name]
            constructor.points = round(constructor.points + race_points, 6)
            constructor.races += 1
            constructor.wins += 1 if entry.position == 1 else 0
            constructor.podiums += 1 if entry.position <= 3 else 0
        for constructor in season.constructor_standings:
            team_points_history = self._loads(constructor.points_history_json, [])
            round_points = sum(
                points_awarded.get(entry.driver_id, 0.0)
                for entry in result.classification
                if entry.team_name == constructor.team_name
            )
            team_points_history.append(round_points)
            constructor.points_history_json = self._json(team_points_history)

    def _season_response(self, season: Season) -> SeasonResponse:
        """Build the full API response."""
        return SeasonResponse(
            id=season.id,
            season_name=season.season_name,
            current_round=season.current_round,
            total_rounds=season.total_rounds,
            status=SeasonStatus(season.status),
            calendar=[self._race_summary(race) for race in season.races],
            driver_standings=self._driver_standings(season),
            constructor_standings=self._constructor_standings(season),
            analytics=self._analytics(season),
        )

    def _driver_standings(self, season: Season) -> list[DriverStandingResponse]:
        """Return sorted driver standings."""
        ordered = sorted(
            season.driver_standings,
            key=lambda row: (-row.points, -row.wins, -row.podiums, row.driver_id),
        )
        return [
            DriverStandingResponse(
                position=index,
                driver_id=row.driver_id,
                driver_name=row.driver_name,
                team_name=row.team_name,
                points=row.points,
                wins=row.wins,
                podiums=row.podiums,
                races=row.races,
                best_finish=row.best_finish,
                average_finish=(
                    round(row.finish_sum / row.races, 3) if row.races else None
                ),
                total_race_time=row.total_race_time,
                momentum=self._momentum(self._loads(row.points_history_json, [])),
                points_history=self._loads(row.points_history_json, []),
                position_history=self._loads(row.positions_history_json, []),
            )
            for index, row in enumerate(ordered, start=1)
        ]

    def _constructor_standings(self, season: Season) -> list[ConstructorStandingResponse]:
        """Return sorted constructor standings."""
        ordered = sorted(
            season.constructor_standings,
            key=lambda row: (-row.points, -row.wins, -row.podiums, row.team_name),
        )
        return [
            ConstructorStandingResponse(
                position=index,
                team_name=row.team_name,
                points=row.points,
                wins=row.wins,
                podiums=row.podiums,
                races=row.races,
                momentum=self._momentum(self._loads(row.points_history_json, [])),
                points_history=self._loads(row.points_history_json, []),
            )
            for index, row in enumerate(ordered, start=1)
        ]

    def _analytics(self, season: Season) -> SeasonAnalyticsResponse:
        """Calculate season analytics from stored race results."""
        strategy_rows: dict[str, dict[str, float]] = {}
        driver_rows: dict[str, dict[str, object]] = {}
        total_pit_stops = 0
        total_entries = 0
        for race in season.races:
            if not race.result_json:
                continue
            result = MultiDriverRaceResult.model_validate_json(race.result_json)
            for entry in result.classification:
                label = " -> ".join(pit.compound.value for pit in entry.final_strategy)
                label = f"{entry.final_compound.value} / {label}" if label else entry.final_compound.value
                metric = strategy_rows.setdefault(
                    label,
                    {
                        "races": 0,
                        "position_sum": 0,
                        "time_sum": 0.0,
                        "wins": 0,
                        "podiums": 0,
                        "pit_sum": 0,
                    },
                )
                metric["races"] += 1
                metric["position_sum"] += entry.position
                metric["time_sum"] += entry.total_race_time_seconds
                metric["wins"] += 1 if entry.position == 1 else 0
                metric["podiums"] += 1 if entry.position <= 3 else 0
                metric["pit_sum"] += entry.pit_stop_count
                total_pit_stops += entry.pit_stop_count
                total_entries += 1

                driver_metric = driver_rows.setdefault(
                    entry.driver_id,
                    {
                        "driver_name": entry.driver_name,
                        "positions": [],
                        "points": 0.0,
                        "wins": 0,
                        "podiums": 0,
                        "best": None,
                        "worst": None,
                    },
                )
                driver_metric["positions"].append(entry.position)
                driver_metric["wins"] += 1 if entry.position == 1 else 0
                driver_metric["podiums"] += 1 if entry.position <= 3 else 0
                if driver_metric["best"] is None or entry.position < driver_metric["best"][1]:
                    driver_metric["best"] = (race.circuit_name, entry.position)
                if driver_metric["worst"] is None or entry.position > driver_metric["worst"][1]:
                    driver_metric["worst"] = (race.circuit_name, entry.position)
        for standing in self._driver_standings(season):
            if standing.driver_id in driver_rows:
                driver_rows[standing.driver_id]["points"] = standing.points

        strategy_metrics = [
            StrategySeasonMetric(
                strategy_label=label,
                races=int(data["races"]),
                average_position=round(data["position_sum"] / data["races"], 3),
                average_race_time=round(data["time_sum"] / data["races"], 6),
                wins=int(data["wins"]),
                podiums=int(data["podiums"]),
                average_pit_stops=round(data["pit_sum"] / data["races"], 3),
            )
            for label, data in strategy_rows.items()
            if data["races"]
        ]
        strategy_metrics.sort(key=lambda metric: (-metric.wins, metric.average_position, metric.strategy_label))
        driver_analysis = []
        for driver_id, data in driver_rows.items():
            positions = data["positions"]
            best = data["best"]
            worst = data["worst"]
            driver_analysis.append(
                DriverSeasonAnalysis(
                    driver_id=driver_id,
                    driver_name=str(data["driver_name"]),
                    average_race_position=round(sum(positions) / len(positions), 3) if positions else None,
                    wins=int(data["wins"]),
                    podiums=int(data["podiums"]),
                    points_per_race=round(float(data["points"]) / len(positions), 3) if positions else 0.0,
                    best_circuit=best[0] if best else None,
                    worst_circuit=worst[0] if worst else None,
                )
            )
        driver_analysis.sort(key=lambda item: item.average_race_position or 999)
        return SeasonAnalyticsResponse(
            strategy_metrics=strategy_metrics,
            most_successful_strategy=strategy_metrics[0] if strategy_metrics else None,
            average_pit_stops=round(total_pit_stops / total_entries, 3) if total_entries else 0.0,
            driver_analysis=driver_analysis,
            momentum_method=(
                "Momentum compares the first and last values in the last three points "
                "scores: delta > 3 IMPROVING, delta < -3 DECLINING, otherwise STABLE."
            ),
        )

    def _standings_from_points(
        self,
        season: Season,
        points_by_driver: dict[str, float],
    ) -> list[DriverStandingResponse]:
        """Build hypothetical standings from altered points."""
        rows = deepcopy(self._driver_standings(season))
        for row in rows:
            row.points = round(points_by_driver[row.driver_id], 6)
        rows.sort(key=lambda row: (-row.points, -row.wins, -row.podiums, row.driver_id))
        for index, row in enumerate(rows, start=1):
            row.position = index
        return rows

    @staticmethod
    def _points_for_classification(
        result: MultiDriverRaceResult,
        points_system: PointsSystem,
    ) -> dict[str, float]:
        """Award points by finishing position."""
        return {
            entry.driver_id: points_system.points_by_position.get(entry.position, 0.0)
            for entry in result.classification
        }

    @staticmethod
    def _momentum(points_history: list[float]) -> MomentumLabel:
        """Classify momentum from last three race point scores."""
        recent = points_history[-3:]
        if len(recent) < 3:
            return MomentumLabel.STABLE
        delta = recent[-1] - recent[0]
        if delta > 3:
            return MomentumLabel.IMPROVING
        if delta < -3:
            return MomentumLabel.DECLINING
        return MomentumLabel.STABLE

    def _circuits_for_calendar(
        self,
        calendar: list[SeasonCalendarRound],
        db: Session,
    ) -> dict[int, Circuit]:
        """Load and validate requested circuits."""
        circuits: dict[int, Circuit] = {}
        for calendar_round in calendar:
            circuit = self.circuit_service.get_circuit_by_id(calendar_round.circuit_id, db)
            if circuit is None:
                raise ValueError(f"Circuit not found: {calendar_round.circuit_id}")
            circuits[circuit.id] = circuit
        return circuits

    @staticmethod
    def _circuit_config_from_race(race: SeasonRace) -> CircuitConfig:
        """Build a simulation circuit config from stored round defaults."""
        return CircuitConfig(
            circuit_name=race.circuit_name,
            total_laps=race.total_laps,
            base_lap_time_seconds=race.base_lap_time_seconds,
            pit_lane_time_loss_seconds=race.pit_lane_time_loss_seconds,
            avg_track_temp=race.avg_track_temp,
            avg_air_temp=race.avg_air_temp,
        )

    def _get_season_model(self, season_id: int, db: Session) -> Season:
        """Load one season or raise."""
        season = db.get(Season, season_id)
        if season is None:
            raise SeasonNotFoundError(f"Season not found: {season_id}")
        return season

    def _points_system(self, season: Season) -> PointsSystem:
        """Parse stored points system."""
        return PointsSystem.model_validate(self._loads(season.points_system_json, {}))

    def _config(self, season: Season) -> dict[str, object]:
        """Parse stored season config."""
        return self._loads(season.config_json, {})

    @staticmethod
    def _race_points(race: SeasonRace) -> dict[str, float]:
        """Parse stored points for a race."""
        return SeasonSimulator._loads(race.points_json, {})

    @staticmethod
    def _race_summary(race: SeasonRace) -> SeasonRaceSummary:
        """Convert a race model into a calendar summary."""
        return SeasonRaceSummary(
            round_number=race.round_number,
            circuit_id=race.circuit_id,
            circuit_name=race.circuit_name,
            completed=bool(race.completed),
            winner_driver_id=race.winner_driver_id,
            winner_driver_name=race.winner_driver_name,
        )

    @staticmethod
    def _round_weather_seed(season: Season, round_number: int) -> int:
        """Derive deterministic per-round weather seed."""
        return season.weather_seed * 100_003 + round_number * 1_009

    @staticmethod
    def _round_event_seed(season: Season, round_number: int) -> int:
        """Derive deterministic per-round event seed."""
        return season.event_seed * 10_007 + round_number * 313

    @staticmethod
    def _json(value: object) -> str:
        """Serialize deterministic JSON."""
        return json.dumps(value, sort_keys=True)

    @staticmethod
    def _loads(value: str | None, default: object) -> object:
        """Deserialize JSON with a default."""
        if not value:
            return default
        return json.loads(value)
