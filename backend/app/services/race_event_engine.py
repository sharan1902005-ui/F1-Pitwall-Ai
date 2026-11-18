"""Deterministic race-control event engine."""

import random

from app.schemas.live_race import RaceControlEvent, RaceEventType
from app.schemas.simulation import RaceConfig, WeatherState

# Minimum lap gap before the same *transition* event type can fire again.
_DEDUP_GAP = 3

# Track temperature thresholds (°C above circuit average).
_HOT_TRACK_DELTA = 6.0
_TEMP_CHANGE_DELTA = 4.0

# Tyre life thresholds for state-machine degradation events.
_DEGRADATION_WARNING_LIFE = 40.0   # 40% — first warning
_DEGRADATION_CRITICAL_LIFE = 15.0  # 15% — critical

# Wetness thresholds for crossover state machine (hysteresis).
_CROSSOVER_WETNESS_ENTER = 0.45
_CROSSOVER_WETNESS_EXIT = 0.30


class RaceEventEngine:
    """Generate reproducible simulated events from race and event seeds."""

    safety_car_lap_time_multiplier: float = 1.32
    vsc_lap_time_multiplier: float = 1.16
    safety_car_degradation_multiplier: float = 0.35
    vsc_degradation_multiplier: float = 0.65
    safety_car_fuel_multiplier: float = 0.70
    vsc_fuel_multiplier: float = 0.84
    safety_car_pit_loss_multiplier: float = 0.55
    vsc_pit_loss_multiplier: float = 0.78

    def events_for_lap(
        self,
        config: RaceConfig,
        event_seed_state: int,
        lap_number: int,
        weather: WeatherState,
        previous_weather: WeatherState | None,
        previous_events: list[RaceControlEvent] | None = None,
    ) -> list[RaceControlEvent]:
        """Return deterministic events for a lap."""
        rng = random.Random(
            config.weather_seed_state * 100_003
            + event_seed_state * 1_009
            + lap_number * 97
        )
        events: list[RaceControlEvent] = []
        prev = previous_events or []

        # --- Race-control events (SC / VSC) ---
        sc_threshold = min(0.35, config.safety_car_base_probability * 0.08)
        vsc_threshold = min(0.45, config.safety_car_base_probability * 0.12)
        roll = rng.random()
        if roll < sc_threshold:
            events.append(RaceControlEvent(
                event_type=RaceEventType.SAFETY_CAR,
                lap=lap_number,
                active=True,
                reason="SIMULATED INCIDENT - safety car deployed",
            ))
        elif roll < sc_threshold + vsc_threshold:
            events.append(RaceControlEvent(
                event_type=RaceEventType.VIRTUAL_SAFETY_CAR,
                lap=lap_number,
                active=True,
                reason="SIMULATED INCIDENT - virtual safety car deployed",
            ))

        if previous_weather is None:
            return events

        # --- Weather transition events ---
        wetness_delta = weather.track_wetness - previous_weather.track_wetness
        if wetness_delta >= 0.12 and self._can_emit(prev, RaceEventType.RAIN_INCREASE, lap_number):
            events.append(RaceControlEvent(
                event_type=RaceEventType.RAIN_INCREASE,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED WEATHER - rain intensity increasing "
                    f"(wetness {previous_weather.track_wetness:.2f} \u2192 {weather.track_wetness:.2f})"
                ),
            ))
        elif wetness_delta <= -0.08 and self._can_emit(prev, RaceEventType.RAIN_DECREASE, lap_number):
            events.append(RaceControlEvent(
                event_type=RaceEventType.RAIN_DECREASE,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED WEATHER - rain decreasing, track drying "
                    f"(wetness {previous_weather.track_wetness:.2f} \u2192 {weather.track_wetness:.2f})"
                ),
            ))
        elif wetness_delta <= -0.08 and self._can_emit(prev, RaceEventType.DRYING_TRACK, lap_number):
            # Legacy alias kept for backward compatibility
            events.append(RaceControlEvent(
                event_type=RaceEventType.DRYING_TRACK,
                lap=lap_number,
                active=True,
                reason="SIMULATED WEATHER - track drying",
            ))

        # --- Track temperature events ---
        temp_delta = weather.track_temperature - previous_weather.track_temperature
        temp_above_avg = weather.track_temperature - config.circuit.avg_track_temp

        if temp_above_avg >= _HOT_TRACK_DELTA and self._can_emit(prev, RaceEventType.HOT_TRACK, lap_number):
            events.append(RaceControlEvent(
                event_type=RaceEventType.HOT_TRACK,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED WEATHER - elevated track temperature "
                    f"{weather.track_temperature:.1f}\u00b0C "
                    f"(avg {config.circuit.avg_track_temp:.1f}\u00b0C)"
                ),
            ))
        elif temp_delta >= _TEMP_CHANGE_DELTA and self._can_emit(prev, RaceEventType.TRACK_TEMP_RISING, lap_number):
            events.append(RaceControlEvent(
                event_type=RaceEventType.TRACK_TEMP_RISING,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED WEATHER - track temperature rising "
                    f"{previous_weather.track_temperature:.1f}\u00b0C \u2192 {weather.track_temperature:.1f}\u00b0C"
                ),
            ))
        elif temp_delta <= -_TEMP_CHANGE_DELTA and self._can_emit(prev, RaceEventType.TRACK_TEMP_FALLING, lap_number):
            events.append(RaceControlEvent(
                event_type=RaceEventType.TRACK_TEMP_FALLING,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED WEATHER - track temperature falling "
                    f"{previous_weather.track_temperature:.1f}\u00b0C \u2192 {weather.track_temperature:.1f}\u00b0C"
                ),
            ))
        elif abs(temp_delta) >= _TEMP_CHANGE_DELTA and self._can_emit(prev, RaceEventType.TRACK_TEMPERATURE_CHANGE, lap_number):
            # Legacy fallback
            events.append(RaceControlEvent(
                event_type=RaceEventType.TRACK_TEMPERATURE_CHANGE,
                lap=lap_number,
                active=True,
                reason="SIMULATED WEATHER - track temperature shift",
            ))

        return events

    def crossover_state_events(
        self,
        lap_number: int,
        track_wetness: float,
        tyre_compound: str,
        crossover_active: bool,
    ) -> tuple[list[RaceControlEvent], bool]:
        """Return crossover state-transition events and updated crossover_active flag.

        Uses hysteresis: enters at _CROSSOVER_WETNESS_ENTER, exits at
        _CROSSOVER_WETNESS_EXIT.  Only dry-compound tyres trigger crossover.
        Returns (events, new_crossover_active).
        """
        events: list[RaceControlEvent] = []
        dry_compounds = {"SOFT", "MEDIUM", "HARD"}
        if tyre_compound not in dry_compounds:
            # On wet-weather tyres crossover is not relevant; clear state.
            return events, False

        if not crossover_active and track_wetness >= _CROSSOVER_WETNESS_ENTER:
            events.append(RaceControlEvent(
                event_type=RaceEventType.TYRE_CROSSOVER_REACHED,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED STRATEGY - wet tyre crossover reached "
                    f"(wetness {track_wetness:.2f} \u2265 {_CROSSOVER_WETNESS_ENTER:.2f}). "
                    f"Intermediate or Wet tyres now faster than {tyre_compound}."
                ),
            ))
            return events, True

        if crossover_active and track_wetness < _CROSSOVER_WETNESS_EXIT:
            events.append(RaceControlEvent(
                event_type=RaceEventType.TYRE_CROSSOVER_CLEARED,
                lap=lap_number,
                active=False,
                reason=(
                    f"SIMULATED STRATEGY - crossover condition cleared "
                    f"(wetness {track_wetness:.2f} < {_CROSSOVER_WETNESS_EXIT:.2f}). "
                    f"Slick tyres viable again."
                ),
            ))
            return events, False

        # Approaching threshold — informational, uses dedup gap
        if (
            not crossover_active
            and 0.25 <= track_wetness < _CROSSOVER_WETNESS_ENTER
        ):
            # Emit at most once per 5 laps while approaching
            events.append(RaceControlEvent(
                event_type=RaceEventType.TYRE_CROSSOVER_APPROACHING,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED STRATEGY - crossover approaching "
                    f"(wetness {track_wetness:.2f}). Monitor conditions."
                ),
            ))

        return events, crossover_active

    def degradation_state_events(
        self,
        lap_number: int,
        tyre_compound: str,
        tyre_age: int,
        tyre_life_percent: float,
        degradation_warned: bool,
        degradation_critical: bool,
    ) -> tuple[list[RaceControlEvent], bool, bool]:
        """Return degradation state-transition events and updated flags.

        Emits DEGRADATION_WARNING once when life falls to/below 40%.
        Emits CRITICAL_TYRE_WEAR once when life falls to/below 15%.
        Returns (events, new_degradation_warned, new_degradation_critical).
        """
        events: list[RaceControlEvent] = []

        if not degradation_warned and tyre_life_percent <= _DEGRADATION_WARNING_LIFE:
            events.append(RaceControlEvent(
                event_type=RaceEventType.DEGRADATION_WARNING,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED STRATEGY - {tyre_compound} tyre life at "
                    f"{tyre_life_percent:.1f}% (lap {tyre_age}). "
                    f"Consider pit window."
                ),
            ))
            degradation_warned = True

        if not degradation_critical and tyre_life_percent <= _DEGRADATION_CRITICAL_LIFE:
            events.append(RaceControlEvent(
                event_type=RaceEventType.CRITICAL_TYRE_WEAR,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED STRATEGY - {tyre_compound} tyre critically worn "
                    f"({tyre_life_percent:.1f}% life, lap {tyre_age}). "
                    f"Pit stop required."
                ),
            ))
            degradation_critical = True

        return events, degradation_warned, degradation_critical

    def pit_window_events(
        self,
        lap_number: int,
        remaining_laps: int,
        previous_events: list[RaceControlEvent],
    ) -> list[RaceControlEvent]:
        """Return pit-window open/closing events based on race fraction."""
        events: list[RaceControlEvent] = []
        race_fraction = 1.0 - (remaining_laps / max(1, remaining_laps + lap_number - 1))

        if (
            0.28 <= race_fraction <= 0.32
            and self._can_emit(previous_events, RaceEventType.PIT_WINDOW_OPEN, lap_number)
        ):
            events.append(RaceControlEvent(
                event_type=RaceEventType.PIT_WINDOW_OPEN,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED STRATEGY - primary pit window now open "
                    f"(lap {lap_number}, {remaining_laps} laps remaining)"
                ),
            ))

        if (
            0.65 <= race_fraction <= 0.70
            and self._can_emit(previous_events, RaceEventType.PIT_WINDOW_CLOSING, lap_number)
        ):
            events.append(RaceControlEvent(
                event_type=RaceEventType.PIT_WINDOW_CLOSING,
                lap=lap_number,
                active=True,
                reason=(
                    f"SIMULATED STRATEGY - pit window closing "
                    f"({remaining_laps} laps remaining)"
                ),
            ))

        return events

    # Keep for backward compatibility with multi-driver simulator and tests
    def environmental_strategy_events(
        self,
        lap_number: int,
        weather: WeatherState,
        tyre_compound: str,
        tyre_age: int,
        tyre_life_percent: float,
        remaining_laps: int,
        previous_events: list[RaceControlEvent],
    ) -> list[RaceControlEvent]:
        """Legacy method: returns pit-window events only.

        Crossover and degradation events are now emitted via state-machine
        methods called directly from LiveRaceService, which holds the
        per-session state flags.  This method is retained so existing callers
        (multi-driver simulator, tests) continue to work unchanged.
        """
        return self.pit_window_events(lap_number, remaining_laps, previous_events)

    @staticmethod
    def race_control_status(events: list[RaceControlEvent]) -> str | None:
        """Return the active race-control status from a set of events."""
        if any(event.event_type == RaceEventType.SAFETY_CAR for event in events):
            return "SAFETY_CAR"
        if any(event.event_type == RaceEventType.VIRTUAL_SAFETY_CAR for event in events):
            return "VIRTUAL_SAFETY_CAR"
        return None

    @staticmethod
    def _can_emit(
        previous_events: list[RaceControlEvent],
        event_type: RaceEventType,
        current_lap: int,
    ) -> bool:
        """Return True if no identical event was emitted within _DEDUP_GAP laps."""
        for event in reversed(previous_events):
            if event.event_type == event_type:
                return current_lap - event.lap >= _DEDUP_GAP
        return True
