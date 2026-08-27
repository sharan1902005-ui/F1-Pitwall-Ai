"""Deterministic multi-driver race simulator."""

from dataclasses import dataclass, field

from app.schemas.live_race import RaceEventType
from app.schemas.multi_race import (
    ClassificationEntry,
    DriverConfig,
    DriverLapResult,
    DriverRaceResult,
    DriverRaceStatus,
    DriverStrategyMode,
    LapClassification,
    MultiDriverRaceConfig,
    MultiDriverRaceResult,
    OpponentStrategyInsight,
)
from app.schemas.race_engineer import EngineerResponse, Urgency
from app.schemas.simulation import PitInstruction, RaceConfig, TyreCompound
from app.services.race_environment import RaceEnvironment, RaceEnvironmentService
from app.services.race_event_engine import RaceEventEngine
from app.services.simulator import RaceSimulator
from app.services.strategy_engine import StrategyEngine
from app.services.tyre_model import TyrePerformanceModel


@dataclass
class DriverRuntimeState:
    """Mutable per-driver simulation state."""

    config: DriverConfig
    strategy: list[PitInstruction]
    current_lap: int = 0
    current_position: int = 0
    current_compound: TyreCompound | None = None
    tyre_age: int = 0
    fuel_remaining_kg: float = 0.0
    total_race_time_seconds: float = 0.0
    pit_stop_count: int = 0
    race_status: DriverRaceStatus = DriverRaceStatus.RUNNING
    lap_results: list[DriverLapResult] = field(default_factory=list)


class MultiDriverRaceSimulator:
    """Simulate competitors in one shared deterministic race environment."""

    def __init__(
        self,
        simulator: RaceSimulator | None = None,
        tyre_model: TyrePerformanceModel | None = None,
        environment_service: RaceEnvironmentService | None = None,
        event_engine: RaceEventEngine | None = None,
        strategy_engine: StrategyEngine | None = None,
    ) -> None:
        self.simulator = simulator or RaceSimulator()
        self.tyre_model = tyre_model or TyrePerformanceModel()
        self.event_engine = event_engine or RaceEventEngine()
        self.environment_service = environment_service or RaceEnvironmentService(
            event_engine=self.event_engine,
        )
        self.strategy_engine = strategy_engine or StrategyEngine()

    def run(
        self,
        config: MultiDriverRaceConfig,
        environment: RaceEnvironment | None = None,
    ) -> MultiDriverRaceResult:
        """Run a full multi-driver race."""
        environment = environment or self.environment_service.generate(
            config.race_config,
            event_seed_state=config.event_seed_state,
        )
        states = self._initialize_driver_states(config)
        classification_by_lap: list[LapClassification] = []

        for lap_number in range(1, config.race_config.circuit.total_laps + 1):
            weather = environment.weather_by_lap[lap_number]
            events = environment.events_by_lap[lap_number]
            race_control = self.event_engine.race_control_status(events)
            for state in states:
                self._advance_driver(
                    race_config=config.race_config,
                    state=state,
                    lap_number=lap_number,
                    track_wetness=weather.track_wetness,
                    race_control=race_control,
                )
            classification = self._classification(states)
            classification_by_lap.append(
                LapClassification(lap_number=lap_number, classification=classification)
            )
            for entry in classification:
                state = self._state_for_driver(states, entry.driver_id)
                state.current_position = entry.position
                state.lap_results[-1].position = entry.position

        driver_results = [self._driver_result(state) for state in states]
        final_classification = self._classification(states)
        return MultiDriverRaceResult(
            total_laps=config.race_config.circuit.total_laps,
            shared_weather_history=environment.weather_history,
            shared_events=environment.events,
            driver_results=driver_results,
            classification=final_classification,
            classification_by_lap=classification_by_lap,
            opponent_insights=self._opponent_insights(states, config.race_config.circuit.total_laps),
            engineer_explanation=self._engineer_summary(final_classification, states, environment),
        )

    def _initialize_driver_states(
        self,
        config: MultiDriverRaceConfig,
    ) -> list[DriverRuntimeState]:
        """Create deterministic driver states and resolve AI strategies once."""
        states: list[DriverRuntimeState] = []
        for driver in config.drivers:
            strategy = list(driver.strategy)
            if driver.strategy_mode == DriverStrategyMode.AI:
                strategy = self._ai_strategy_for_driver(config.race_config, driver)
            states.append(
                DriverRuntimeState(
                    config=driver,
                    strategy=strategy,
                    current_compound=driver.starting_compound,
                    fuel_remaining_kg=driver.starting_fuel_kg,
                )
            )
        return states

    def _advance_driver(
        self,
        race_config: RaceConfig,
        state: DriverRuntimeState,
        lap_number: int,
        track_wetness: float,
        race_control: str | None,
    ) -> None:
        """Advance a single driver by one lap using shared conditions."""
        pit_loss = 0.0
        status = DriverRaceStatus.RUNNING
        instruction = self._pit_instruction_for_lap(state.strategy, lap_number)
        if instruction is not None:
            state.current_compound = instruction.compound
            state.tyre_age = 0
            state.pit_stop_count += 1
            pit_loss = self._pit_loss(race_config, race_control)
            status = DriverRaceStatus.PITTING

        assert state.current_compound is not None
        tyre_age_for_lap = state.tyre_age + 1
        fuel_for_lap = state.fuel_remaining_kg
        fuel_consumption = (
            state.config.starting_fuel_kg / race_config.circuit.total_laps
            if race_config.circuit.total_laps > 0
            else 0.0
        )
        degradation_multiplier = state.config.degradation_factor
        lap_time_multiplier = 1.0
        if race_control == "SAFETY_CAR":
            degradation_multiplier *= self.event_engine.safety_car_degradation_multiplier
            fuel_consumption *= self.event_engine.safety_car_fuel_multiplier
            lap_time_multiplier = self.event_engine.safety_car_lap_time_multiplier
        elif race_control == "VIRTUAL_SAFETY_CAR":
            degradation_multiplier *= self.event_engine.vsc_degradation_multiplier
            fuel_consumption *= self.event_engine.vsc_fuel_multiplier
            lap_time_multiplier = self.event_engine.vsc_lap_time_multiplier

        driving_time = self.simulator._calculate_lap_time(
            config=race_config,
            compound=state.current_compound,
            tyre_age=tyre_age_for_lap,
            fuel_remaining_kg=fuel_for_lap,
            track_wetness=track_wetness,
            pit_time_loss_seconds=0.0,
            degradation_multiplier=degradation_multiplier,
        )
        lap_time = round(driving_time * state.config.pace_factor * lap_time_multiplier + pit_loss, 6)
        state.total_race_time_seconds = round(state.total_race_time_seconds + lap_time, 6)
        state.fuel_remaining_kg = round(max(0.0, state.fuel_remaining_kg - fuel_consumption), 6)
        state.tyre_age = tyre_age_for_lap
        state.current_lap = lap_number
        if lap_number >= race_config.circuit.total_laps:
            status = DriverRaceStatus.FINISHED
        state.race_status = status
        state.lap_results.append(
            DriverLapResult(
                driver_id=state.config.driver_id,
                lap_number=lap_number,
                position=state.current_position or 0,
                lap_time_seconds=lap_time,
                compound=state.current_compound,
                tyre_age=state.tyre_age,
                tyre_life_percent=self.tyre_model.life_percent(
                    state.current_compound,
                    state.tyre_age,
                ),
                fuel_remaining_kg=state.fuel_remaining_kg,
                pit_time_loss_seconds=pit_loss,
                race_status=status,
                cumulative_race_time=state.total_race_time_seconds,
            )
        )

    def _classification(
        self,
        states: list[DriverRuntimeState],
    ) -> list[ClassificationEntry]:
        """Sort drivers by laps, elapsed time, then stable driver ID."""
        ordered = sorted(
            states,
            key=lambda state: (
                -state.current_lap,
                state.total_race_time_seconds,
                state.config.driver_id,
            ),
        )
        leader_time = ordered[0].total_race_time_seconds if ordered else 0.0
        classification: list[ClassificationEntry] = []
        for position, state in enumerate(ordered, start=1):
            assert state.current_compound is not None
            classification.append(
                ClassificationEntry(
                    position=position,
                    driver_id=state.config.driver_id,
                    driver_name=state.config.driver_name,
                    team_name=state.config.team_name,
                    completed_laps=state.current_lap,
                    total_race_time_seconds=state.total_race_time_seconds,
                    gap_to_leader_seconds=round(state.total_race_time_seconds - leader_time, 6),
                    pit_stop_count=state.pit_stop_count,
                    final_compound=state.current_compound,
                    final_strategy=state.strategy,
                )
            )
        return classification

    def _driver_result(self, state: DriverRuntimeState) -> DriverRaceResult:
        """Convert mutable state to response schema."""
        assert state.current_compound is not None
        return DriverRaceResult(
            driver_id=state.config.driver_id,
            driver_name=state.config.driver_name,
            team_name=state.config.team_name,
            completed_laps=state.current_lap,
            total_race_time_seconds=state.total_race_time_seconds,
            final_compound=state.current_compound,
            final_tyre_age=state.tyre_age,
            final_fuel_remaining_kg=state.fuel_remaining_kg,
            pit_stop_count=state.pit_stop_count,
            final_strategy=state.strategy,
            lap_results=state.lap_results,
        )

    def _ai_strategy_for_driver(
        self,
        race_config: RaceConfig,
        driver: DriverConfig,
    ) -> list[PitInstruction]:
        """Resolve an AI-generated strategy using the existing StrategyEngine once."""
        driver_race_config = race_config.model_copy(
            update={
                "starting_compound": driver.starting_compound,
                "starting_fuel_kg": driver.starting_fuel_kg,
            }
        )
        analysis = self.strategy_engine.analyze(
            driver_race_config,
            degradation_multiplier=driver.degradation_factor,
        )
        strategy = analysis.recommended_strategy
        if strategy is None:
            return []
        return [
            PitInstruction(lap=stint.start_lap, compound=stint.compound)
            for stint in strategy.stints[1:]
        ]

    def _opponent_insights(
        self,
        states: list[DriverRuntimeState],
        total_laps: int,
    ) -> list[OpponentStrategyInsight]:
        """Return simple backend-generated strategy windows from resolved pit plans."""
        insights: list[OpponentStrategyInsight] = []
        for state in states:
            next_pit = next(
                (
                    instruction.lap
                    for instruction in state.strategy
                    if instruction.lap > state.current_lap
                ),
                None,
            )
            if next_pit is None:
                start = end = None
                available = False
            else:
                start = max(1, next_pit - 2)
                end = min(total_laps, next_pit + 2)
                available = True
            assert state.current_compound is not None
            insights.append(
                OpponentStrategyInsight(
                    driver_id=state.config.driver_id,
                    driver_name=state.config.driver_name,
                    current_tyre=state.current_compound,
                    tyre_age=state.tyre_age,
                    likely_pit_window_start=start,
                    likely_pit_window_end=end,
                    prediction_available=available,
                )
            )
        return insights

    def _engineer_summary(
        self,
        classification: list[ClassificationEntry],
        states: list[DriverRuntimeState],
        environment: RaceEnvironment,
    ) -> EngineerResponse | None:
        """Return a deterministic competitive-mode explanation for the leader."""
        if not classification:
            return None
        leader = classification[0]
        state = self._state_for_driver(states, leader.driver_id)
        gap_behind = classification[1].gap_to_leader_seconds if len(classification) > 1 else None
        active_events = [
            event.event_type
            for event in environment.events_by_lap.get(state.current_lap, [])
            if event.event_type in {RaceEventType.SAFETY_CAR, RaceEventType.VIRTUAL_SAFETY_CAR}
        ]
        key_factors = [
            f"{leader.driver_name} leads after {leader.completed_laps} laps.",
            f"Pit stops completed: {leader.pit_stop_count}.",
            f"Current tyre: {leader.final_compound.value} aged {state.tyre_age} laps.",
        ]
        if gap_behind is not None:
            key_factors.append(f"Gap behind is {gap_behind:.3f} seconds.")
        if active_events:
            key_factors.append(f"Race control status: {active_events[0].value}.")
        explanation = (
            "Competitive mode uses the shared deterministic race simulation for "
            "positions, gaps, tyre state, and race-control context."
        )
        return EngineerResponse(
            decision="PROTECT TRACK POSITION",
            urgency=Urgency.MEDIUM if gap_behind is not None and gap_behind < 5 else Urgency.LOW,
            explanation=explanation,
            key_factors=key_factors,
            confidence=1.0,
            risk="LOW",
        )

    @staticmethod
    def _pit_instruction_for_lap(
        strategy: list[PitInstruction],
        lap_number: int,
    ) -> PitInstruction | None:
        """Return a pit instruction for the lap if one exists."""
        return next(
            (instruction for instruction in strategy if instruction.lap == lap_number),
            None,
        )

    def _pit_loss(self, race_config: RaceConfig, race_control: str | None) -> float:
        """Return pit loss adjusted for shared Safety Car/VSC status."""
        base = race_config.circuit.pit_lane_time_loss_seconds
        if race_control == "SAFETY_CAR":
            return round(base * self.event_engine.safety_car_pit_loss_multiplier, 6)
        if race_control == "VIRTUAL_SAFETY_CAR":
            return round(base * self.event_engine.vsc_pit_loss_multiplier, 6)
        return base

    @staticmethod
    def _state_for_driver(
        states: list[DriverRuntimeState],
        driver_id: str,
    ) -> DriverRuntimeState:
        """Find a driver runtime state."""
        return next(state for state in states if state.config.driver_id == driver_id)
