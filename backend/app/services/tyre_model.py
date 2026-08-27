"""Deterministic tyre performance model."""

from dataclasses import dataclass

from app.schemas.simulation import TyreCompound


@dataclass(frozen=True)
class TyreCharacteristics:
    """Static tyre behaviour constants for the simple simulator."""

    base_offset_seconds: float
    degradation_rate: float
    max_useful_life_laps: int
    ideal_wetness: float
    wetness_sensitivity: float


class TyrePerformanceModel:
    """Calculate compound performance from age and track wetness."""

    characteristics: dict[TyreCompound, TyreCharacteristics] = {
        TyreCompound.SOFT: TyreCharacteristics(-0.75, 0.055, 24, 0.0, 16.0),
        TyreCompound.MEDIUM: TyreCharacteristics(0.0, 0.038, 34, 0.0, 14.0),
        TyreCompound.HARD: TyreCharacteristics(0.45, 0.026, 45, 0.0, 12.5),
        TyreCompound.INTERMEDIATE: TyreCharacteristics(1.65, 0.035, 30, 0.48, 8.0),
        TyreCompound.WET: TyreCharacteristics(3.2, 0.032, 28, 0.88, 10.5),
    }

    def supported_compounds(self) -> tuple[TyreCompound, ...]:
        """Return the compounds the tyre model supports."""
        return tuple(TyreCompound)

    def performance_penalty(
        self,
        compound: TyreCompound,
        tyre_age: int,
        track_wetness: float,
        degradation_multiplier: float = 1.0,
    ) -> float:
        """Return the tyre time penalty in seconds for the current conditions."""
        data = self.characteristics[compound]
        age = max(0, tyre_age)
        wetness = max(0.0, min(1.0, track_wetness))
        degradation_rate = max(0.0, data.degradation_rate * degradation_multiplier)

        degradation_penalty = degradation_rate * (age ** 1.18)
        life_overrun = max(0, age - data.max_useful_life_laps)
        cliff_penalty = 0.18 * (life_overrun ** 1.35)
        wetness_penalty = abs(wetness - data.ideal_wetness) * data.wetness_sensitivity

        return round(
            data.base_offset_seconds
            + degradation_penalty
            + cliff_penalty
            + wetness_penalty,
            6,
        )

    def life_percent(self, compound: TyreCompound, tyre_age: int) -> float:
        """Return remaining useful tyre life as a percentage."""
        max_life = self.characteristics[compound].max_useful_life_laps
        remaining = max(0.0, 1.0 - (tyre_age / max_life))
        return round(remaining * 100.0, 3)
