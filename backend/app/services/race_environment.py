"""Shared race-wide environment generation for multi-driver simulations."""

from dataclasses import dataclass

from app.schemas.live_race import RaceControlEvent
from app.schemas.simulation import RaceConfig, WeatherState
from app.services.race_event_engine import RaceEventEngine
from app.services.weather_engine import WeatherEngine


@dataclass(frozen=True)
class RaceEnvironment:
    """Weather and race-control state shared by every driver."""

    weather_by_lap: dict[int, WeatherState]
    events_by_lap: dict[int, list[RaceControlEvent]]

    @property
    def weather_history(self) -> list[WeatherState]:
        """Return weather in lap order."""
        return [self.weather_by_lap[lap] for lap in sorted(self.weather_by_lap)]

    @property
    def events(self) -> list[RaceControlEvent]:
        """Return all events in lap order."""
        return [
            event
            for lap in sorted(self.events_by_lap)
            for event in self.events_by_lap[lap]
        ]


class RaceEnvironmentService:
    """Generate deterministic shared weather and race-control timelines once."""

    def __init__(
        self,
        weather_engine: WeatherEngine | None = None,
        event_engine: RaceEventEngine | None = None,
    ) -> None:
        self.weather_engine = weather_engine or WeatherEngine()
        self.event_engine = event_engine or RaceEventEngine()

    def generate(
        self,
        config: RaceConfig,
        event_seed_state: int = 0,
    ) -> RaceEnvironment:
        """Generate the complete shared race environment."""
        rng = self.weather_engine.create_rng(config.weather_seed_state)
        previous_wetness = 0.0
        previous_weather: WeatherState | None = None
        weather_by_lap: dict[int, WeatherState] = {}
        events_by_lap: dict[int, list[RaceControlEvent]] = {}

        for lap_number in range(1, config.circuit.total_laps + 1):
            weather = self.weather_engine.next_lap(
                lap_number=lap_number,
                circuit=config.circuit,
                rng=rng,
                previous_wetness=previous_wetness,
            )
            events = self.event_engine.events_for_lap(
                config,
                event_seed_state,
                lap_number,
                weather,
                previous_weather,
            )
            weather_by_lap[lap_number] = weather
            events_by_lap[lap_number] = events
            previous_wetness = weather.track_wetness
            previous_weather = weather

        return RaceEnvironment(
            weather_by_lap=weather_by_lap,
            events_by_lap=events_by_lap,
        )
