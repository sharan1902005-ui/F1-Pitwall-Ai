"""Grounded AI race engineer explanation layer."""

from typing import Protocol

from app.config import settings
from app.schemas.race_engineer import EngineerResponse, RaceContext, Urgency
from app.schemas.simulation import RaceConfig, StrategyResult


class RaceEngineerProvider(Protocol):
    """Provider interface for deterministic or external explanation engines."""

    def generate_explanation(
        self,
        race_config: RaceConfig,
        strategy_result: StrategyResult,
        context: RaceContext | None,
    ) -> EngineerResponse:
        """Generate a grounded explanation from structured strategy data."""


class DeterministicRaceEngineerProvider:
    """Template-based fallback provider with no external dependency."""

    def generate_explanation(
        self,
        race_config: RaceConfig,
        strategy_result: StrategyResult,
        context: RaceContext | None,
    ) -> EngineerResponse:
        """Explain a strategy without calculating new race values."""
        recommended_compound = (
            strategy_result.stints[1].compound
            if len(strategy_result.stints) > 1
            else strategy_result.stints[0].compound
        )
        recommended_pit_lap = strategy_result.pit_laps[0] if strategy_result.pit_laps else None
        decision = (
            f"BOX FOR {recommended_compound.value}"
            if recommended_pit_lap is not None
            else f"STAY OUT ON {recommended_compound.value}"
        )
        urgency = self._urgency(strategy_result, context, recommended_pit_lap)
        key_factors = [
            f"Strategy engine ranks {strategy_result.strategy_id} P{strategy_result.projected_finish}.",
            f"Expected race time is {strategy_result.expected_race_time_seconds:.3f} seconds.",
            f"Confidence is {strategy_result.confidence:.3f} with {strategy_result.risk} risk.",
        ]
        if recommended_pit_lap is not None:
            key_factors.append(
                f"Recommended pit lap is {recommended_pit_lap} for {recommended_compound.value}."
            )
        if context is not None:
            key_factors.extend(
                [
                    f"Current lap is {context.current_lap}/{context.total_laps}.",
                    f"Track wetness is {context.track_wetness:.3f} with rain probability {context.rain_probability:.3f}.",
                    f"Current tyre is {context.current_compound.value} aged {context.tyre_age} laps.",
                ]
            )
            key_factors.extend(self._weather_factors(context, race_config))

        explanation = self._build_explanation(strategy_result, context, race_config)
        return EngineerResponse(
            decision=decision,
            urgency=urgency,
            explanation=explanation,
            key_factors=key_factors,
            estimated_time_gain_seconds=None,
            recommended_compound=recommended_compound,
            recommended_pit_lap=recommended_pit_lap,
            confidence=strategy_result.confidence,
            risk=strategy_result.risk,
        )

    @staticmethod
    def _weather_factors(context: RaceContext, race_config: RaceConfig) -> list[str]:
        """Return grounded weather-aware key factors from simulated variables only."""
        factors: list[str] = []
        avg_track = race_config.circuit.avg_track_temp
        temp_delta = context.track_temperature - avg_track

        if temp_delta >= 6.0:
            factors.append(
                f"Track temperature is elevated at {context.track_temperature:.1f}°C "
                f"({temp_delta:+.1f}°C above circuit average). "
                "Higher track temperature increases tyre degradation rate in this model."
            )
        elif temp_delta >= 3.0:
            factors.append(
                f"Track temperature is {context.track_temperature:.1f}°C "
                f"({temp_delta:+.1f}°C above average) — monitor tyre wear."
            )
        elif temp_delta <= -4.0:
            factors.append(
                f"Track temperature has dropped to {context.track_temperature:.1f}°C "
                f"({temp_delta:.1f}°C below average). "
                "Cooler conditions reduce degradation but may affect wet-tyre crossover threshold."
            )

        if context.rain_intensity >= 0.3:
            factors.append(
                f"Rain intensity is {context.rain_intensity:.2f}. "
                "Intermediate or Wet tyres may be required if track wetness continues to rise."
            )
        elif context.track_wetness >= 0.45:
            factors.append(
                f"Track wetness is {context.track_wetness:.2f}. "
                "Slick tyre performance is significantly penalised at this wetness level."
            )
        elif context.track_wetness >= 0.15:
            factors.append(
                f"Track wetness is {context.track_wetness:.2f} — "
                "slick tyres remain viable but monitor for further rain."
            )

        if context.air_temperature < avg_track - 8:
            factors.append(
                f"Air temperature is {context.air_temperature:.1f}°C. "
                "Cool air may slow track drying after rain."
            )

        return factors

    @staticmethod
    def _build_explanation(
        strategy_result: StrategyResult,
        context: RaceContext | None,
        race_config: RaceConfig,
    ) -> str:
        """Build a grounded explanation incorporating weather context."""
        base = (
            f"{strategy_result.strategy_id} is recommended because the deterministic "
            f"strategy engine projects it as the fastest available option. "
            f"{strategy_result.recommendation_reason}"
        )
        if context is None:
            return base

        avg_track = race_config.circuit.avg_track_temp
        temp_delta = context.track_temperature - avg_track

        if context.track_wetness >= 0.45 and context.current_compound.value in ("SOFT", "MEDIUM", "HARD"):
            return (
                f"{base} Track wetness of {context.track_wetness:.2f} is above the "
                "slick-tyre crossover threshold. The strategy engine accounts for the "
                "significant wetness penalty on dry-compound tyres."
            )
        if context.rain_intensity >= 0.3:
            return (
                f"{base} Current rain intensity ({context.rain_intensity:.2f}) is "
                "increasing track wetness. Monitor conditions for a potential compound change."
            )
        if temp_delta >= 6.0:
            return (
                f"{base} Elevated track temperature ({context.track_temperature:.1f}°C, "
                f"{temp_delta:+.1f}°C above average) increases tyre degradation in this model. "
                "The strategy engine has factored current tyre age into this recommendation."
            )
        return base

    @staticmethod
    def _urgency(
        strategy_result: StrategyResult,
        context: RaceContext | None,
        recommended_pit_lap: int | None,
    ) -> Urgency:
        """Derive deterministic urgency from pit timing, context, and risk."""
        if context is not None and recommended_pit_lap is not None:
            laps_until_pit = recommended_pit_lap - context.current_lap
            if laps_until_pit <= 0:
                return Urgency.CRITICAL
            if laps_until_pit <= 2:
                return Urgency.HIGH
        if strategy_result.risk == "HIGH":
            return Urgency.HIGH
        if strategy_result.risk == "MEDIUM":
            return Urgency.MEDIUM
        return Urgency.LOW


class OptionalLLMRaceEngineerProvider:
    """Optional provider boundary for future LLM integration."""

    def __init__(self, fallback: RaceEngineerProvider | None = None) -> None:
        self.fallback = fallback or DeterministicRaceEngineerProvider()

    def generate_explanation(
        self,
        race_config: RaceConfig,
        strategy_result: StrategyResult,
        context: RaceContext | None,
    ) -> EngineerResponse:
        """Fall back when no usable LLM configuration is available."""
        if not settings.llm_api_key or not settings.llm_model:
            return self.fallback.generate_explanation(
                race_config,
                strategy_result,
                context,
            )
        return self.fallback.generate_explanation(race_config, strategy_result, context)


class RaceEngineer:
    """Explain deterministic strategy outputs without overriding them."""

    def __init__(self, provider: RaceEngineerProvider | None = None) -> None:
        if provider is not None:
            self.provider = provider
        elif settings.ai_provider.lower() == "llm":
            self.provider = OptionalLLMRaceEngineerProvider()
        else:
            self.provider = DeterministicRaceEngineerProvider()

    def explain_strategy(
        self,
        race_config: RaceConfig,
        strategy_result: StrategyResult,
        context: RaceContext | None = None,
    ) -> EngineerResponse:
        """Explain a selected strategy using only structured engine output."""
        return self.provider.generate_explanation(race_config, strategy_result, context)
