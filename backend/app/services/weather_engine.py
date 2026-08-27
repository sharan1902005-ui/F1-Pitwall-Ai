"""Deterministic weather engine for race simulations."""

import math
import random

from app.models.circuit import CircuitConfig
from app.schemas.simulation import WeatherState

class WeatherEngine:
    """Generate reproducible lap weather from a local seeded random source."""

    drying_rate: float = 0.035
    wetness_gain: float = 0.18

    def initial_state(self, seed: int) -> int:
        """Return the seed used to initialize deterministic future weather."""
        return seed

    def create_rng(self, seed: int) -> random.Random:
        """Create a local random generator so global randomness is never used."""
        return random.Random(seed)

    def next_lap(
        self,
        lap_number: int,
        circuit: CircuitConfig,
        rng: random.Random,
        previous_wetness: float,
        rain_probability_multiplier: float = 1.0,
    ) -> WeatherState:
        """Calculate weather for one lap, with wetness evolving gradually."""
        trend = 0.5 + 0.28 * math.sin((lap_number + rng.random()) / 9.0)
        noise = rng.uniform(-0.18, 0.18)
        rain_probability = self._clamp((trend + noise) * rain_probability_multiplier)

        rain_trigger = rng.random()
        raw_intensity = max(0.0, rain_probability - rain_trigger)
        rain_intensity = self._clamp(raw_intensity * 1.8)

        wetness = previous_wetness
        wetness += rain_intensity * self.wetness_gain
        wetness -= (1.0 - rain_intensity) * self.drying_rate
        track_wetness = self._clamp(wetness)

        temp_wave = math.sin(lap_number / 12.0)
        rain_cooling = rain_intensity * 4.0 + track_wetness * 2.0
        track_temperature = circuit.avg_track_temp + temp_wave * 1.5 - rain_cooling
        air_temperature = circuit.avg_air_temp + temp_wave * 0.8 - rain_intensity * 1.5

        return WeatherState(
            lap_number=lap_number,
            rain_probability=round(rain_probability, 6),
            rain_intensity=round(rain_intensity, 6),
            track_temperature=round(track_temperature, 3),
            air_temperature=round(air_temperature, 3),
            track_wetness=round(track_wetness, 6),
        )

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp weather probabilities and wetness to the inclusive unit range."""
        return max(0.0, min(1.0, value))
