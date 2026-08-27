"""Deterministic race-control event engine."""

import random

from app.schemas.live_race import RaceControlEvent, RaceEventType
from app.schemas.simulation import RaceConfig, WeatherState


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
    ) -> list[RaceControlEvent]:
        """Return deterministic events for a lap."""
        rng = random.Random(
            config.weather_seed_state * 100_003
            + event_seed_state * 1_009
            + lap_number * 97
        )
        events: list[RaceControlEvent] = []

        sc_threshold = min(0.35, config.safety_car_base_probability * 0.08)
        vsc_threshold = min(0.45, config.safety_car_base_probability * 0.12)
        roll = rng.random()
        if roll < sc_threshold:
            events.append(
                RaceControlEvent(
                    event_type=RaceEventType.SAFETY_CAR,
                    lap=lap_number,
                    active=True,
                    reason="SIMULATED INCIDENT - safety car deployed",
                )
            )
        elif roll < sc_threshold + vsc_threshold:
            events.append(
                RaceControlEvent(
                    event_type=RaceEventType.VIRTUAL_SAFETY_CAR,
                    lap=lap_number,
                    active=True,
                    reason="SIMULATED INCIDENT - virtual safety car deployed",
                )
            )

        if previous_weather is not None:
            wetness_delta = weather.track_wetness - previous_weather.track_wetness
            if wetness_delta >= 0.12:
                events.append(
                    RaceControlEvent(
                        event_type=RaceEventType.RAIN_INCREASE,
                        lap=lap_number,
                        active=True,
                        reason="SIMULATED WEATHER - rain intensity increasing",
                    )
                )
            elif wetness_delta <= -0.08:
                events.append(
                    RaceControlEvent(
                        event_type=RaceEventType.DRYING_TRACK,
                        lap=lap_number,
                        active=True,
                        reason="SIMULATED WEATHER - track drying",
                    )
                )

        if abs(weather.track_temperature - config.circuit.avg_track_temp) >= 5.0:
            events.append(
                RaceControlEvent(
                    event_type=RaceEventType.TRACK_TEMPERATURE_CHANGE,
                    lap=lap_number,
                    active=True,
                    reason="SIMULATED WEATHER - track temperature shift",
                )
            )
        return events

    @staticmethod
    def race_control_status(events: list[RaceControlEvent]) -> str | None:
        """Return the active race-control status from a set of events."""
        if any(event.event_type == RaceEventType.SAFETY_CAR for event in events):
            return "SAFETY_CAR"
        if any(event.event_type == RaceEventType.VIRTUAL_SAFETY_CAR for event in events):
            return "VIRTUAL_SAFETY_CAR"
        return None
