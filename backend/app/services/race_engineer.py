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

        explanation = (
            f"{strategy_result.strategy_id} is recommended because the deterministic "
            f"strategy engine projects it as the fastest available option. "
            f"{strategy_result.recommendation_reason}"
        )
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
