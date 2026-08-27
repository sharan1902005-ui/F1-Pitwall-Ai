"""Controlled deterministic what-if scenario analysis."""

from app.schemas.race_engineer import EngineerResponse, ScenarioRequest, ScenarioResponse
from app.schemas.simulation import StrategyAnalysisResponse, StrategyResult
from app.services.race_engineer import RaceEngineer
from app.services.strategy_engine import StrategyEngine


class ScenarioService:
    """Modify allowed simulation parameters and compare deterministic outputs."""

    def __init__(
        self,
        strategy_engine: StrategyEngine | None = None,
        race_engineer: RaceEngineer | None = None,
    ) -> None:
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.race_engineer = race_engineer or RaceEngineer()

    def analyze(self, request: ScenarioRequest) -> ScenarioResponse:
        """Run baseline and scenario strategy analysis, then explain the delta."""
        rain_multiplier, degradation_multiplier, key_changes = self._modifiers(request)
        baseline = self.strategy_engine.analyze(request.race_config)
        scenario = self.strategy_engine.analyze(
            request.race_config,
            rain_probability_multiplier=rain_multiplier,
            degradation_multiplier=degradation_multiplier,
        )
        baseline_best = self._require_strategy(baseline)
        scenario_best = self._require_strategy(scenario)
        time_difference = round(
            scenario_best.expected_race_time_seconds
            - baseline_best.expected_race_time_seconds,
            6,
        )
        strategy_changed = baseline_best.strategy_id != scenario_best.strategy_id
        key_changes.append(
            f"Scenario time delta is {time_difference:.3f} seconds."
        )
        if strategy_changed:
            key_changes.append(
                f"Strategy changed from {baseline_best.strategy_id} to {scenario_best.strategy_id}."
            )
        else:
            key_changes.append(f"Strategy remains {scenario_best.strategy_id}.")

        explanation = self.race_engineer.explain_strategy(
            request.race_config,
            scenario_best,
        )
        explanation = self._with_scenario_delta(explanation, time_difference)
        return ScenarioResponse(
            baseline_strategy=baseline_best.strategy_id,
            scenario_strategy=scenario_best.strategy_id,
            baseline_race_time=baseline_best.expected_race_time_seconds,
            scenario_race_time=scenario_best.expected_race_time_seconds,
            time_difference=time_difference,
            strategy_changed=strategy_changed,
            key_changes=key_changes,
            engineer_explanation=explanation,
        )

    @staticmethod
    def _require_strategy(analysis: StrategyAnalysisResponse) -> StrategyResult:
        """Return the recommended strategy or fail for impossible empty analysis."""
        if analysis.recommended_strategy is None:
            raise ValueError("No strategy candidates available")
        return analysis.recommended_strategy

    @staticmethod
    def _modifiers(request: ScenarioRequest) -> tuple[float, float, list[str]]:
        """Translate allowed scenario parameters into simulator modifiers."""
        params = request.scenario_parameters
        if request.scenario_type == "DEGRADATION_INCREASE":
            percent = float(params.get("percent", 0.10))
            if percent < 0:
                raise ValueError("percent must be non-negative")
            return 1.0, 1.0 + percent, [
                f"Tyre degradation increased by {percent * 100:.1f}%."
            ]
        if request.scenario_type == "RAIN_INTENSITY_INCREASE":
            percent = float(params.get("percent", 0.15))
            if percent < 0:
                raise ValueError("percent must be non-negative")
            return 1.0 + percent, 1.0, [
                f"Rain probability multiplier increased by {percent * 100:.1f}%."
            ]
        if request.scenario_type == "RAIN_ARRIVES_EARLIER":
            laps = int(params.get("laps", 5))
            if laps < 1:
                raise ValueError("laps must be at least 1")
            return 1.0 + min(0.5, laps * 0.03), 1.0, [
                f"Rain arrival pressure increased to approximate {laps} laps earlier."
            ]
        if request.scenario_type == "TRACK_WETNESS_STAYS_LOW":
            cap = float(params.get("cap", 0.30))
            if not 0.0 <= cap <= 1.0:
                raise ValueError("cap must be between 0 and 1")
            return max(0.1, cap), 1.0, [
                f"Rain probability reduced to keep wetness pressure near {cap:.2f}."
            ]
        raise ValueError("Unsupported scenario type")

    @staticmethod
    def _with_scenario_delta(
        explanation: EngineerResponse,
        time_difference: float,
    ) -> EngineerResponse:
        """Add scenario delta to the grounded response without changing decisions."""
        key_factors = list(explanation.key_factors)
        key_factors.append(f"Scenario changes race time by {time_difference:.3f} seconds.")
        return explanation.model_copy(update={"key_factors": key_factors})
