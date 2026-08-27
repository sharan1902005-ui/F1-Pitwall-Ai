"""Interactive live race session service."""

from uuid import uuid4

from app.schemas.live_race import (
    LiveActionType,
    LiveRaceAction,
    LiveRaceAdvanceResponse,
    LiveRaceRecommendationResponse,
    LiveRaceStartResponse,
    LiveRaceState,
    RaceActionRecord,
    RaceControlEvent,
    RaceEventType,
    RaceStatus,
    RaceTimelineEntry,
)
from app.schemas.race_engineer import EngineerResponse, RaceContext, Urgency
from app.schemas.simulation import LapResult, RaceConfig, StrategyResult, TyreCompound
from app.services.race_engineer import RaceEngineer
from app.services.race_event_engine import RaceEventEngine
from app.services.simulator import RaceSimulator
from app.services.strategy_engine import StrategyEngine
from app.services.tyre_crossover import TyreCrossoverEngine
from app.services.tyre_model import TyrePerformanceModel
from app.services.weather_engine import WeatherEngine


class LiveRaceNotFoundError(LookupError):
    """Raised when a live race session does not exist."""


class LiveRaceStateError(RuntimeError):
    """Raised when a live race operation is invalid for the current state."""


class LiveRaceService:
    """Manage in-memory deterministic live race sessions."""

    def __init__(
        self,
        weather_engine: WeatherEngine | None = None,
        tyre_model: TyrePerformanceModel | None = None,
        simulator: RaceSimulator | None = None,
        strategy_engine: StrategyEngine | None = None,
        event_engine: RaceEventEngine | None = None,
        race_engineer: RaceEngineer | None = None,
    ) -> None:
        self.weather_engine = weather_engine or WeatherEngine()
        self.tyre_model = tyre_model or TyrePerformanceModel()
        self.simulator = simulator or RaceSimulator(
            weather_engine=self.weather_engine,
            tyre_model=self.tyre_model,
        )
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.event_engine = event_engine or RaceEventEngine()
        self.race_engineer = race_engineer or RaceEngineer()
        self.sessions: dict[str, LiveRaceState] = {}
        self.pending_actions: dict[str, LiveRaceAction] = {}

    def start(self, config: RaceConfig, event_seed_state: int = 0) -> LiveRaceStartResponse:
        """Start a live race from the exact RaceConfig contract."""
        race_id = str(uuid4())
        strategy_analysis = self.strategy_engine.analyze(config)
        strategy = strategy_analysis.recommended_strategy
        recommendation = (
            self.race_engineer.explain_strategy(config, strategy)
            if strategy is not None
            else None
        )
        state = LiveRaceState(
            race_id=race_id,
            race_config=config,
            current_lap=0,
            total_laps=config.circuit.total_laps,
            current_compound=config.starting_compound,
            tyre_age=0,
            fuel_remaining_kg=config.starting_fuel_kg,
            track_wetness=0.0,
            rain_probability=0.0,
            rain_intensity=0.0,
            track_temperature=config.circuit.avg_track_temp,
            air_temperature=config.circuit.avg_air_temp,
            current_race_time=0.0,
            pit_stop_count=0,
            race_status=RaceStatus.READY,
            weather_seed_state=config.weather_seed_state,
            event_seed_state=event_seed_state,
            history=[],
            weather_history=[],
            events=[],
            actions=[],
            timeline=[
                RaceTimelineEntry(
                    lap=0,
                    entry_type="SESSION",
                    description="Live race session created.",
                )
            ],
            recommendation=recommendation,
            strategy=strategy,
            strategy_recalculation_count=1 if strategy is not None else 0,
        )
        self.sessions[race_id] = state
        return LiveRaceStartResponse(race_id=race_id, race_state=state)

    def get(self, race_id: str) -> LiveRaceState:
        """Return a live race state."""
        if race_id not in self.sessions:
            raise LiveRaceNotFoundError(f"Race session not found: {race_id}")
        return self.sessions[race_id]

    def submit_action(
        self,
        race_id: str,
        action: LiveRaceAction | dict[str, object],
    ) -> LiveRaceState:
        """Store a user action for the next lap."""
        if isinstance(action, dict):
            action = LiveRaceAction.model_validate(action)
        state = self.get(race_id)
        if state.race_status in {RaceStatus.FINISHED, RaceStatus.ABORTED}:
            raise LiveRaceStateError("Race is not active")
        if action.action == LiveActionType.PIT and action.compound is None:
            raise ValueError("PIT action requires compound")
        self.pending_actions[race_id] = action
        state.timeline.append(
            RaceTimelineEntry(
                lap=state.current_lap + 1,
                entry_type="USER_ACTION",
                description=self._action_description(action),
            )
        )
        return state

    def pit(self, race_id: str, compound: TyreCompound) -> LiveRaceState:
        """Shortcut for submitting a pit action."""
        return self.submit_action(
            race_id,
            LiveRaceAction(action=LiveActionType.PIT, compound=compound),
        )

    def recommendation(self, race_id: str) -> LiveRaceRecommendationResponse:
        """Return the current live race engineer recommendation."""
        state = self.get(race_id)
        if state.recommendation is None:
            self._recalculate_strategy(state, "Recommendation requested.")
        if state.recommendation is None:
            raise LiveRaceStateError("No recommendation available")
        return LiveRaceRecommendationResponse(
            race_id=race_id,
            recommendation=state.recommendation,
            strategy=state.strategy,
        )

    def advance(self, race_id: str) -> LiveRaceAdvanceResponse:
        """Advance an active race by exactly one lap."""
        state = self.get(race_id)
        if state.race_status in {RaceStatus.FINISHED, RaceStatus.ABORTED}:
            raise LiveRaceStateError("Race is not active")
        if state.current_lap >= state.total_laps:
            state.race_status = RaceStatus.FINISHED
            return LiveRaceAdvanceResponse(
                race_id=race_id,
                current_lap=state.current_lap,
                total_laps=state.total_laps,
                lap_result=None,
                race_state=state,
                events=[],
                race_status=state.race_status,
            )

        next_lap = state.current_lap + 1
        state.race_status = RaceStatus.RUNNING
        action = self.pending_actions.pop(
            race_id,
            LiveRaceAction(action=LiveActionType.STAY_OUT),
        )
        pit_loss = self._apply_user_action(state, action)
        previous_weather = state.weather_history[-1] if state.weather_history else None
        rng = self.weather_engine.create_rng(state.weather_seed_state)
        previous_wetness = 0.0
        weather = None
        for lap_number in range(1, next_lap + 1):
            weather = self.weather_engine.next_lap(
                lap_number=lap_number,
                circuit=state.race_config.circuit,
                rng=rng,
                previous_wetness=previous_wetness,
            )
            previous_wetness = weather.track_wetness
        assert weather is not None

        events = self.event_engine.events_for_lap(
            state.race_config,
            state.event_seed_state,
            next_lap,
            weather,
            previous_weather,
        )
        self._append_events(state, events)
        race_control = self.event_engine.race_control_status(events)
        state.race_status = RaceStatus(race_control) if race_control else RaceStatus.RUNNING

        tyre_age_for_lap = state.tyre_age + 1
        fuel_for_lap = state.fuel_remaining_kg
        fuel_consumption = state.race_config.starting_fuel_kg / state.total_laps
        degradation_multiplier = 1.0
        lap_time_multiplier = 1.0
        if state.race_status == RaceStatus.SAFETY_CAR:
            degradation_multiplier = self.event_engine.safety_car_degradation_multiplier
            fuel_consumption *= self.event_engine.safety_car_fuel_multiplier
            lap_time_multiplier = self.event_engine.safety_car_lap_time_multiplier
        elif state.race_status == RaceStatus.VIRTUAL_SAFETY_CAR:
            degradation_multiplier = self.event_engine.vsc_degradation_multiplier
            fuel_consumption *= self.event_engine.vsc_fuel_multiplier
            lap_time_multiplier = self.event_engine.vsc_lap_time_multiplier

        lap_time = self.simulator._calculate_lap_time(
            config=state.race_config,
            compound=state.current_compound,
            tyre_age=tyre_age_for_lap,
            fuel_remaining_kg=fuel_for_lap,
            track_wetness=weather.track_wetness,
            pit_time_loss_seconds=pit_loss,
            degradation_multiplier=degradation_multiplier,
        )
        lap_time = round(lap_time * lap_time_multiplier, 6)
        state.fuel_remaining_kg = round(max(0.0, state.fuel_remaining_kg - fuel_consumption), 6)
        state.tyre_age = tyre_age_for_lap
        state.current_lap = next_lap
        state.current_race_time = round(state.current_race_time + lap_time, 6)
        state.track_wetness = weather.track_wetness
        state.rain_probability = weather.rain_probability
        state.rain_intensity = weather.rain_intensity
        state.track_temperature = weather.track_temperature
        state.air_temperature = weather.air_temperature
        state.weather_history.append(weather)

        lap_result = LapResult(
            lap_number=next_lap,
            lap_time_seconds=lap_time,
            compound=state.current_compound,
            tyre_age=state.tyre_age,
            tyre_life_percent=self.tyre_model.life_percent(
                state.current_compound,
                state.tyre_age,
            ),
            fuel_remaining_kg=state.fuel_remaining_kg,
            track_temperature=state.track_temperature,
            air_temperature=state.air_temperature,
            rain_probability=state.rain_probability,
            track_wetness=state.track_wetness,
            cumulative_race_time=state.current_race_time,
        )
        state.history.append(lap_result)
        state.timeline.append(
            RaceTimelineEntry(
                lap=next_lap,
                entry_type="LAP",
                description=f"Lap {next_lap} completed in {lap_time:.3f}s.",
            )
        )

        if self._should_recalculate(state, events, action):
            self._recalculate_strategy(state, "Live race trigger changed recommendation.")

        if state.current_lap >= state.total_laps:
            state.race_status = RaceStatus.FINISHED
            state.timeline.append(
                RaceTimelineEntry(
                    lap=state.current_lap,
                    entry_type="FINISH",
                    description="Race finished.",
                )
            )

        return LiveRaceAdvanceResponse(
            race_id=race_id,
            current_lap=state.current_lap,
            total_laps=state.total_laps,
            lap_result=lap_result,
            race_state=state,
            events=events,
            race_status=state.race_status,
        )

    def _apply_user_action(self, state: LiveRaceState, action: LiveRaceAction) -> float:
        """Apply user action and return any pit time loss for this lap."""
        original_action = action.action
        recommended_action = state.recommendation.decision if state.recommendation else "NO RECOMMENDATION"
        followed = False
        pit_loss = 0.0
        if action.action == LiveActionType.FOLLOW_RECOMMENDATION and state.recommendation:
            followed = True
            if state.recommendation.recommended_compound is not None:
                action = LiveRaceAction(
                    action=LiveActionType.PIT,
                    compound=state.recommendation.recommended_compound,
                )
            else:
                action = LiveRaceAction(action=LiveActionType.STAY_OUT)
        elif action.action == LiveActionType.STAY_OUT:
            followed = state.recommendation is not None and state.recommendation.recommended_pit_lap is None

        if action.action == LiveActionType.PIT and action.compound is not None:
            pit_loss = self._current_pit_loss(state)
            state.current_compound = action.compound
            state.tyre_age = 0
            state.pit_stop_count += 1
            followed = (
                state.recommendation is not None
                and state.recommendation.recommended_compound == action.compound
            )

        impact = self._decision_impact(state, action)
        state.actions.append(
            RaceActionRecord(
                lap=state.current_lap + 1,
                recommended_action=recommended_action,
                user_action=original_action,
                followed_recommendation=followed,
                time_impact=impact,
            )
        )
        return pit_loss

    def _current_pit_loss(self, state: LiveRaceState) -> float:
        """Return pit loss adjusted for active race-control status."""
        base = state.race_config.circuit.pit_lane_time_loss_seconds
        if state.race_status == RaceStatus.SAFETY_CAR:
            return round(base * self.event_engine.safety_car_pit_loss_multiplier, 6)
        if state.race_status == RaceStatus.VIRTUAL_SAFETY_CAR:
            return round(base * self.event_engine.vsc_pit_loss_multiplier, 6)
        return base

    def _decision_impact(self, state: LiveRaceState, action: LiveRaceAction) -> float:
        """Estimate action impact from deterministic tyre penalty comparison."""
        if state.recommendation is None or state.recommendation.recommended_compound is None:
            return 0.0
        recommended = state.recommendation.recommended_compound
        current_penalty = self.tyre_model.performance_penalty(
            state.current_compound,
            state.tyre_age + 1,
            state.track_wetness,
        )
        recommended_penalty = self.tyre_model.performance_penalty(
            recommended,
            1,
            state.track_wetness,
        )
        if action.action == LiveActionType.STAY_OUT:
            return round(max(0.0, current_penalty - recommended_penalty), 6)
        return round(recommended_penalty - current_penalty, 6)

    def _should_recalculate(
        self,
        state: LiveRaceState,
        events: list[RaceControlEvent],
        action: LiveRaceAction,
    ) -> bool:
        """Trigger strategy recalculation only after meaningful live changes."""
        if action.action != LiveActionType.STAY_OUT:
            return True
        if any(
            event.event_type
            in {
                RaceEventType.SAFETY_CAR,
                RaceEventType.VIRTUAL_SAFETY_CAR,
                RaceEventType.RAIN_INCREASE,
                RaceEventType.DRYING_TRACK,
            }
            for event in events
        ):
            return True
        max_life = self.tyre_model.characteristics[state.current_compound].max_useful_life_laps
        if state.tyre_age >= int(max_life * 0.9):
            return True
        if state.track_wetness >= 0.45 and state.current_compound in {
            TyreCompound.SOFT,
            TyreCompound.MEDIUM,
            TyreCompound.HARD,
        }:
            state.events.append(
                RaceControlEvent(
                    event_type=RaceEventType.TYRE_CROSSOVER,
                    lap=state.current_lap,
                    active=True,
                    reason="SIMULATED STRATEGY - wet tyre crossover pressure detected",
                )
            )
            return True
        return False

    def _recalculate_strategy(self, state: LiveRaceState, reason: str) -> None:
        """Refresh strategy and grounded recommendation."""
        analysis = self.strategy_engine.analyze(state.race_config)
        state.strategy = analysis.recommended_strategy
        if state.strategy is None:
            return
        context = RaceContext(
            current_lap=max(1, state.current_lap),
            total_laps=state.total_laps,
            current_compound=state.current_compound,
            tyre_age=state.tyre_age,
            fuel_remaining_kg=state.fuel_remaining_kg,
            track_wetness=state.track_wetness,
            rain_probability=state.rain_probability,
            rain_intensity=state.rain_intensity,
            track_temperature=state.track_temperature,
            air_temperature=state.air_temperature,
            recent_lap_times=[lap.lap_time_seconds for lap in state.history[-3:]],
        )
        state.recommendation = self.race_engineer.explain_strategy(
            state.race_config,
            state.strategy,
            context,
        )
        state.strategy_recalculation_count += 1
        state.timeline.append(
            RaceTimelineEntry(
                lap=state.current_lap,
                entry_type="AI_RECOMMENDATION",
                description=reason,
            )
        )

    @staticmethod
    def _append_events(state: LiveRaceState, events: list[RaceControlEvent]) -> None:
        """Add events to state and timeline."""
        state.events.extend(events)
        for event in events:
            state.timeline.append(
                RaceTimelineEntry(
                    lap=event.lap,
                    entry_type="EVENT",
                    description=f"{event.event_type.value}: {event.reason}",
                )
            )

    @staticmethod
    def _action_description(action: LiveRaceAction) -> str:
        """Return a concise action description."""
        if action.action == LiveActionType.PIT:
            return f"User selected PIT for {action.compound}."
        return f"User selected {action.action.value}."
