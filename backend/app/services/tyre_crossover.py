"""Tyre crossover detection based on continuous tyre performance."""

from dataclasses import dataclass

from app.models.circuit import CircuitConfig
from app.schemas.simulation import CrossoverResult, TyreCompound, WeatherState
from app.services.tyre_model import TyrePerformanceModel


@dataclass(frozen=True)
class CrossoverInput:
    """Inputs required to compare staying out with switching tyres."""

    current_compound: TyreCompound
    alternative_compound: TyreCompound
    track_wetness: float
    rain_intensity: float
    expected_future_laps: int
    pit_lane_time_loss_seconds: float


class TyreCrossoverEngine:
    """Compare compounds and identify net-beneficial tyre changes."""

    minimum_gain_seconds: float = 0.5
    minimum_faster_laps: int = 2

    def __init__(self, tyre_model: TyrePerformanceModel | None = None) -> None:
        self.tyre_model = tyre_model or TyrePerformanceModel()

    def evaluate(self, crossover_input: CrossoverInput) -> CrossoverResult:
        """Evaluate a one-lap wetness projection from a legacy input object."""
        wetness = [crossover_input.track_wetness] * crossover_input.expected_future_laps
        circuit = CircuitConfig(
            circuit_name="crossover",
            total_laps=crossover_input.expected_future_laps,
            base_lap_time_seconds=90.0,
            pit_lane_time_loss_seconds=crossover_input.pit_lane_time_loss_seconds,
            avg_track_temp=30.0,
            avg_air_temp=24.0,
        )
        return self.find_crossover_lap(
            current_compound=crossover_input.current_compound,
            alternative_compound=crossover_input.alternative_compound,
            current_tyre_age=0,
            current_lap=1,
            remaining_laps=crossover_input.expected_future_laps,
            predicted_weather=wetness,
            circuit_config=circuit,
        )

    def find_crossover_lap(
        self,
        current_compound: TyreCompound,
        alternative_compound: TyreCompound,
        current_tyre_age: int,
        current_lap: int,
        remaining_laps: int,
        predicted_weather: list[WeatherState] | list[float],
        circuit_config: CircuitConfig,
    ) -> CrossoverResult:
        """Find the earliest future pit lap with positive accumulated time gain."""
        wetness_by_lap = self._wetness_values(predicted_weather)
        if remaining_laps <= 0 or not wetness_by_lap:
            return self._no_crossover(
                current_compound,
                alternative_compound,
                "No remaining laps available for crossover analysis.",
            )

        best_lap: int | None = None
        best_gain = 0.0

        for offset in range(remaining_laps):
            pit_lap = current_lap + offset
            future_wetness = wetness_by_lap[offset:]
            current_total = 0.0
            alternative_total = circuit_config.pit_lane_time_loss_seconds
            faster_laps = 0

            for future_index, track_wetness in enumerate(future_wetness, start=1):
                current_age = current_tyre_age + offset + future_index
                alternative_age = future_index
                current_penalty = self.tyre_model.performance_penalty(
                    current_compound,
                    current_age,
                    track_wetness,
                )
                alternative_penalty = self.tyre_model.performance_penalty(
                    alternative_compound,
                    alternative_age,
                    track_wetness,
                )
                current_total += current_penalty
                alternative_total += alternative_penalty
                if alternative_penalty < current_penalty:
                    faster_laps += 1

            net_gain = current_total - alternative_total
            if (
                faster_laps >= self.minimum_faster_laps
                and net_gain > self.minimum_gain_seconds
            ):
                best_lap = pit_lap
                best_gain = net_gain
                break

        if best_lap is None:
            return self._no_crossover(
                current_compound,
                alternative_compound,
                (
                    "Alternative tyre does not recover pit lane loss over the "
                    "remaining laps."
                ),
            )

        return CrossoverResult(
            crossover_detected=True,
            recommended_pit_lap=best_lap,
            current_compound=current_compound,
            recommended_compound=alternative_compound,
            estimated_time_gain_seconds=round(best_gain, 6),
            reason=(
                f"{alternative_compound.value} is projected to recover pit loss "
                f"from lap {best_lap}."
            ),
        )

    @staticmethod
    def _wetness_values(predicted_weather: list[WeatherState] | list[float]) -> list[float]:
        """Extract clamped wetness values from weather models or floats."""
        values: list[float] = []
        for item in predicted_weather:
            value = item.track_wetness if isinstance(item, WeatherState) else float(item)
            values.append(max(0.0, min(1.0, value)))
        return values

    @staticmethod
    def _no_crossover(
        current_compound: TyreCompound,
        alternative_compound: TyreCompound,
        reason: str,
    ) -> CrossoverResult:
        """Build a no-crossover result."""
        return CrossoverResult(
            crossover_detected=False,
            recommended_pit_lap=None,
            current_compound=current_compound,
            recommended_compound=alternative_compound,
            estimated_time_gain_seconds=0.0,
            reason=reason,
        )
