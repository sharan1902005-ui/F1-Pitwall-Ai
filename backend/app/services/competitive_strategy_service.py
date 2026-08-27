"""Competitive strategy comparison and counterfactual analysis."""

from app.schemas.multi_race import (
    CounterfactualDriverSummary,
    CounterfactualRequest,
    CounterfactualResult,
    DriverConfig,
    MultiDriverRaceConfig,
    MultiDriverRaceResult,
    StrategyComparisonRequest,
    StrategyComparisonResponse,
    StrategyComparisonResult,
)
from app.schemas.simulation import PitInstruction
from app.services.multi_driver_simulator import MultiDriverRaceSimulator
from app.services.race_environment import RaceEnvironmentService


class CompetitiveStrategyService:
    """Run controlled competitive what-if simulations with shared conditions."""

    def __init__(
        self,
        simulator: MultiDriverRaceSimulator | None = None,
        environment_service: RaceEnvironmentService | None = None,
    ) -> None:
        self.environment_service = environment_service or RaceEnvironmentService()
        self.simulator = simulator or MultiDriverRaceSimulator(
            environment_service=self.environment_service,
        )

    def simulate(self, config: MultiDriverRaceConfig) -> MultiDriverRaceResult:
        """Run a normal multi-driver simulation."""
        return self.simulator.run(config)

    def compare_strategies(
        self,
        request: StrategyComparisonRequest,
    ) -> StrategyComparisonResponse:
        """Compare scenarios against a baseline under identical weather/events."""
        self._ensure_strategy_laps(request.base_config.race_config.circuit.total_laps, [
            instruction
            for scenario in request.scenarios
            for instruction in scenario.strategy
        ])
        environment = self.environment_service.generate(
            request.base_config.race_config,
            request.base_config.event_seed_state,
        )
        baseline = self.simulator.run(request.base_config, environment=environment)
        results: list[StrategyComparisonResult] = []

        for scenario in request.scenarios:
            scenario_config = self._with_driver_strategy(
                request.base_config,
                scenario.driver_id,
                scenario.strategy,
            )
            scenario_result = self.simulator.run(scenario_config, environment=environment)
            baseline_entry = self._classification_entry(baseline, scenario.driver_id)
            scenario_entry = self._classification_entry(scenario_result, scenario.driver_id)
            results.append(
                StrategyComparisonResult(
                    scenario_name=scenario.scenario_name,
                    driver_id=scenario.driver_id,
                    final_position=scenario_entry.position,
                    total_race_time_seconds=scenario_entry.total_race_time_seconds,
                    gap_to_leader_seconds=scenario_entry.gap_to_leader_seconds,
                    strategy=scenario.strategy,
                    time_difference_seconds=round(
                        scenario_entry.total_race_time_seconds
                        - baseline_entry.total_race_time_seconds,
                        6,
                    ),
                    position_difference=baseline_entry.position - scenario_entry.position,
                )
            )

        return StrategyComparisonResponse(baseline=baseline, results=results)

    def counterfactual(self, request: CounterfactualRequest) -> CounterfactualResult:
        """Run a controlled counterfactual where only one driver strategy changes."""
        self._ensure_strategy_laps(
            request.base_config.race_config.circuit.total_laps,
            request.alternative_strategy,
        )
        environment = self.environment_service.generate(
            request.base_config.race_config,
            request.base_config.event_seed_state,
        )
        baseline = self.simulator.run(request.base_config, environment=environment)
        counterfactual_config = self._with_driver_strategy(
            request.base_config,
            request.driver_id,
            request.alternative_strategy,
        )
        counterfactual = self.simulator.run(counterfactual_config, environment=environment)
        baseline_entry = self._classification_entry(baseline, request.driver_id)
        counterfactual_entry = self._classification_entry(counterfactual, request.driver_id)

        return CounterfactualResult(
            driver_id=request.driver_id,
            baseline=CounterfactualDriverSummary(
                position=baseline_entry.position,
                race_time_seconds=baseline_entry.total_race_time_seconds,
                gap_to_leader_seconds=baseline_entry.gap_to_leader_seconds,
                strategy=baseline_entry.final_strategy,
            ),
            counterfactual=CounterfactualDriverSummary(
                position=counterfactual_entry.position,
                race_time_seconds=counterfactual_entry.total_race_time_seconds,
                gap_to_leader_seconds=counterfactual_entry.gap_to_leader_seconds,
                strategy=counterfactual_entry.final_strategy,
            ),
            time_difference_seconds=round(
                counterfactual_entry.total_race_time_seconds
                - baseline_entry.total_race_time_seconds,
                6,
            ),
            position_difference=baseline_entry.position - counterfactual_entry.position,
            weather_identical=(
                baseline.shared_weather_history == counterfactual.shared_weather_history
            ),
            events_identical=baseline.shared_events == counterfactual.shared_events,
        )

    @staticmethod
    def _with_driver_strategy(
        config: MultiDriverRaceConfig,
        driver_id: str,
        strategy: list[PitInstruction],
    ) -> MultiDriverRaceConfig:
        """Return a config where only one driver's strategy is changed."""
        if not any(driver.driver_id == driver_id for driver in config.drivers):
            raise ValueError(f"Driver not found: {driver_id}")
        drivers: list[DriverConfig] = []
        for driver in config.drivers:
            if driver.driver_id == driver_id:
                drivers.append(
                    driver.model_copy(
                        update={"strategy": strategy, "strategy_mode": "MANUAL"}
                    )
                )
            else:
                drivers.append(driver)
        return config.model_copy(update={"drivers": drivers})

    @staticmethod
    def _classification_entry(result: MultiDriverRaceResult, driver_id: str):
        """Find a classification entry by driver."""
        for entry in result.classification:
            if entry.driver_id == driver_id:
                return entry
        raise ValueError(f"Driver not found: {driver_id}")

    @staticmethod
    def _ensure_strategy_laps(total_laps: int, strategy: list[PitInstruction]) -> None:
        """Validate standalone scenario strategy lap ranges."""
        laps = [instruction.lap for instruction in strategy]
        if len(laps) != len(set(laps)):
            raise ValueError("Strategy cannot contain duplicate pit laps")
        if laps != sorted(laps):
            raise ValueError("Strategy pit laps must be sorted")
        if any(instruction.lap > total_laps for instruction in strategy):
            raise ValueError("Strategy pit lap exceeds race distance")
