"""Deterministic lap-by-lap race simulator."""

from app.schemas.simulation import (
    LapResult,
    PitInstruction,
    PitStop,
    RaceConfig,
    RaceResult,
    TyreCompound,
)
from app.services.tyre_model import TyrePerformanceModel
from app.services.weather_engine import WeatherEngine


class CircuitIntelligence:
    """Optional circuit modifiers resolved outside the lap loop."""

    def __init__(
        self,
        tyre_wear_factor: float = 1.0,
        safety_car_factor: float = 1.0,
    ) -> None:
        self.tyre_wear_factor = tyre_wear_factor
        self.safety_car_factor = safety_car_factor


class RaceSimulator:
    """Run complete in-memory race simulations from a RaceConfig."""

    fuel_time_penalty_per_kg: float = 0.032
    wet_weather_drag_seconds: float = 1.25
    minimum_lap_time_seconds: float = 30.0

    def __init__(
        self,
        weather_engine: WeatherEngine | None = None,
        tyre_model: TyrePerformanceModel | None = None,
    ) -> None:
        self.weather_engine = weather_engine or WeatherEngine()
        self.tyre_model = tyre_model or TyrePerformanceModel()

    def validate_config(self, config: RaceConfig) -> RaceConfig:
        """Return a validated race config for early integration points."""
        return config

    def run(
        self,
        config: RaceConfig,
        pit_plan: list[PitInstruction] | None = None,
        rain_probability_multiplier: float = 1.0,
        degradation_multiplier: float = 1.0,
        circuit_intelligence: CircuitIntelligence | None = None,
    ) -> RaceResult:
        """Simulate every configured lap and return the complete race result."""
        intelligence = circuit_intelligence or CircuitIntelligence()
        effective_degradation_multiplier = (
            degradation_multiplier * intelligence.tyre_wear_factor
        )
        _effective_safety_car_probability = max(
            0.0,
            min(
                1.0,
                config.safety_car_base_probability * intelligence.safety_car_factor,
            ),
        )
        total_laps = config.circuit.total_laps
        fuel_consumption_per_lap = (
            config.starting_fuel_kg / total_laps if total_laps > 0 else 0.0
        )
        pit_by_lap = self._normalize_pit_plan(pit_plan)
        rng = self.weather_engine.create_rng(config.weather_seed_state)

        current_compound = config.starting_compound
        tyre_age = 0
        fuel_remaining = config.starting_fuel_kg
        cumulative_time = 0.0
        previous_wetness = 0.0

        lap_results: list[LapResult] = []
        pit_stops: list[PitStop] = []
        weather_history: list = []

        for lap_number in range(1, total_laps + 1):
            pit_time_loss = 0.0
            instruction = pit_by_lap.get(lap_number)
            if instruction is not None:
                old_compound = current_compound
                current_compound = instruction.compound
                tyre_age = 0
                pit_time_loss = config.circuit.pit_lane_time_loss_seconds
                pit_stops.append(
                    PitStop(
                        lap_number=lap_number,
                        old_compound=old_compound,
                        new_compound=current_compound,
                        pit_time_loss_seconds=pit_time_loss,
                    )
                )

            tyre_age += 1
            weather = self.weather_engine.next_lap(
                lap_number=lap_number,
                circuit=config.circuit,
                rng=rng,
                previous_wetness=previous_wetness,
                rain_probability_multiplier=rain_probability_multiplier,
            )
            previous_wetness = weather.track_wetness
            weather_history.append(weather)

            fuel_for_lap = fuel_remaining
            fuel_remaining = max(0.0, fuel_remaining - fuel_consumption_per_lap)

            lap_time = self._calculate_lap_time(
                config=config,
                compound=current_compound,
                tyre_age=tyre_age,
                fuel_remaining_kg=fuel_for_lap,
                track_wetness=weather.track_wetness,
                pit_time_loss_seconds=pit_time_loss,
                degradation_multiplier=effective_degradation_multiplier,
            )
            cumulative_time = round(cumulative_time + lap_time, 6)

            lap_results.append(
                LapResult(
                    lap_number=lap_number,
                    lap_time_seconds=lap_time,
                    compound=current_compound,
                    tyre_age=tyre_age,
                    tyre_life_percent=self.tyre_model.life_percent(
                        current_compound,
                        tyre_age,
                    ),
                    fuel_remaining_kg=round(fuel_remaining, 6),
                    track_temperature=weather.track_temperature,
                    air_temperature=weather.air_temperature,
                    rain_probability=weather.rain_probability,
                    track_wetness=weather.track_wetness,
                    cumulative_race_time=cumulative_time,
                )
            )

        return RaceResult(
            total_laps=total_laps,
            completed_laps=len(lap_results),
            final_race_time_seconds=cumulative_time,
            final_compound=current_compound,
            final_tyre_age=tyre_age,
            final_fuel_remaining_kg=round(fuel_remaining, 6),
            lap_results=lap_results,
            pit_stops=pit_stops,
            weather_history=weather_history,
        )

    def _calculate_lap_time(
        self,
        config: RaceConfig,
        compound: TyreCompound,
        tyre_age: int,
        fuel_remaining_kg: float,
        track_wetness: float,
        pit_time_loss_seconds: float,
        degradation_multiplier: float = 1.0,
    ) -> float:
        """Calculate lap time from base pace, fuel, tyres, weather, and pit loss."""
        fuel_penalty = fuel_remaining_kg * self.fuel_time_penalty_per_kg
        tyre_penalty = self.tyre_model.performance_penalty(
            compound,
            tyre_age,
            track_wetness,
            degradation_multiplier=degradation_multiplier,
        )
        weather_penalty = track_wetness * self.wet_weather_drag_seconds

        lap_time = (
            config.circuit.base_lap_time_seconds
            + fuel_penalty
            + tyre_penalty
            + weather_penalty
            + pit_time_loss_seconds
        )
        return round(max(self.minimum_lap_time_seconds, lap_time), 6)

    @staticmethod
    def _normalize_pit_plan(
        pit_plan: list[PitInstruction] | None,
    ) -> dict[int, PitInstruction]:
        """Index pit instructions by lap, keeping the last instruction per lap."""
        if pit_plan is None:
            return {}
        return {instruction.lap: instruction for instruction in pit_plan}
