"""Deterministic race strategy generation and ranking."""

import random
import statistics
from dataclasses import dataclass

from app.schemas.simulation import (
    PitInstruction,
    RaceConfig,
    StrategyAnalysisResponse,
    StrategyResult,
    StrategyStint,
    TyreCompound,
)
from app.services.simulator import RaceSimulator
from app.services.tyre_crossover import TyreCrossoverEngine
from app.services.tyre_model import TyrePerformanceModel


@dataclass(frozen=True)
class Perturbation:
    """Deterministic perturbation factors used for confidence simulations."""

    rain_probability_multiplier: float
    degradation_multiplier: float


@dataclass(frozen=True)
class CandidateStrategy:
    """Internal strategy candidate before simulation ranking."""

    strategy_id: str
    stints: tuple[StrategyStint, ...]
    recommendation_reason: str


class StrategyEngine:
    """Generate, simulate, rank, and score candidate race strategies."""

    perturbation_runs: int = 20

    def __init__(
        self,
        simulator: RaceSimulator | None = None,
        crossover_engine: TyreCrossoverEngine | None = None,
        tyre_model: TyrePerformanceModel | None = None,
    ) -> None:
        self.simulator = simulator or RaceSimulator()
        self.crossover_engine = crossover_engine or TyreCrossoverEngine()
        self.tyre_model = tyre_model or TyrePerformanceModel()
        self.last_perturbation_counts: dict[str, int] = {}

    def prepare(self, config: RaceConfig) -> RaceConfig:
        """Return a validated config for future candidate strategy generation."""
        return config

    def analyze(
        self,
        config: RaceConfig,
        rain_probability_multiplier: float = 1.0,
        degradation_multiplier: float = 1.0,
    ) -> StrategyAnalysisResponse:
        """Analyze and rank deterministic candidate strategies."""
        candidates = self.generate_candidate_strategies(
            config,
            rain_probability_multiplier=rain_probability_multiplier,
            degradation_multiplier=degradation_multiplier,
        )
        results: list[StrategyResult] = []
        self.last_perturbation_counts = {}

        for candidate in candidates:
            pit_plan = self._pit_plan_from_stints(candidate.stints)
            race_result = self.simulator.run(
                config,
                pit_plan=pit_plan,
                rain_probability_multiplier=rain_probability_multiplier,
                degradation_multiplier=degradation_multiplier,
            )
            confidence = self.calculate_confidence(
                config,
                candidate,
                rain_probability_multiplier=rain_probability_multiplier,
                degradation_multiplier=degradation_multiplier,
            )
            risk = self._risk_for_strategy(candidate, confidence)
            results.append(
                StrategyResult(
                    strategy_id=candidate.strategy_id,
                    stints=list(candidate.stints),
                    pit_laps=[instruction.lap for instruction in pit_plan],
                    expected_race_time_seconds=race_result.final_race_time_seconds,
                    pit_stop_count=len(pit_plan),
                    projected_finish=0,
                    confidence=confidence,
                    risk=risk,
                    recommendation_reason=candidate.recommendation_reason,
                )
            )

        results.sort(key=lambda result: result.expected_race_time_seconds)
        ranked = [
            result.model_copy(update={"projected_finish": index})
            for index, result in enumerate(results, start=1)
        ]
        return StrategyAnalysisResponse(
            recommended_strategy=ranked[0] if ranked else None,
            strategies=ranked,
        )

    def generate_candidate_strategies(
        self,
        config: RaceConfig,
        rain_probability_multiplier: float = 1.0,
        degradation_multiplier: float = 1.0,
    ) -> list[CandidateStrategy]:
        """Generate a compact set of plausible dry and weather-aware strategies."""
        total_laps = config.circuit.total_laps
        start = config.starting_compound
        candidates: list[CandidateStrategy] = [
            CandidateStrategy(
                strategy_id=f"{start.value}-NO-STOP",
                stints=(StrategyStint(compound=start, start_lap=1, end_lap=total_laps),),
                recommendation_reason="Baseline no-stop strategy on the starting tyre.",
            )
        ]

        candidates.extend(self._dry_candidates(config))
        candidates.extend(
            self._weather_candidates(
                config,
                rain_probability_multiplier=rain_probability_multiplier,
                degradation_multiplier=degradation_multiplier,
            )
        )
        return self._deduplicate_candidates(candidates)

    def calculate_confidence(
        self,
        config: RaceConfig,
        candidate: CandidateStrategy,
        rain_probability_multiplier: float = 1.0,
        degradation_multiplier: float = 1.0,
    ) -> float:
        """Run exactly 20 perturbed simulations and apply the required formula."""
        pit_plan = self._pit_plan_from_stints(candidate.stints)
        race_times: list[float] = []

        for perturbation in self.generate_perturbations(config, candidate.strategy_id):
            result = self.simulator.run(
                config,
                pit_plan=pit_plan,
                rain_probability_multiplier=(
                    rain_probability_multiplier
                    * perturbation.rain_probability_multiplier
                ),
                degradation_multiplier=(
                    degradation_multiplier * perturbation.degradation_multiplier
                ),
            )
            race_times.append(result.final_race_time_seconds)

        self.last_perturbation_counts[candidate.strategy_id] = len(race_times)
        mean_race_time = statistics.mean(race_times)
        std_dev = statistics.pstdev(race_times)
        confidence = 1 - (std_dev / mean_race_time)
        return round(max(0.0, min(1.0, confidence)), 6)

    def generate_perturbations(
        self,
        config: RaceConfig,
        strategy_id: str,
    ) -> list[Perturbation]:
        """Create deterministic +/-15% rain and +/-10% degradation factors."""
        rng = random.Random(self._stable_seed(config.weather_seed_state, strategy_id))
        perturbations: list[Perturbation] = []
        for _ in range(self.perturbation_runs):
            rain_multiplier = 0.85 + rng.random() * 0.30
            degradation_multiplier = 0.90 + rng.random() * 0.20
            perturbations.append(
                Perturbation(
                    rain_probability_multiplier=round(
                        max(0.0, min(1.0e9, rain_multiplier)),
                        6,
                    ),
                    degradation_multiplier=round(max(0.0, degradation_multiplier), 6),
                )
            )
        return perturbations

    def _dry_candidates(self, config: RaceConfig) -> list[CandidateStrategy]:
        """Generate a small set of plausible dry tyre strategies."""
        total = config.circuit.total_laps
        start = config.starting_compound
        dry_compounds = (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)
        if start not in dry_compounds:
            dry_compounds = (TyreCompound.MEDIUM, TyreCompound.HARD)

        candidates: list[CandidateStrategy] = []
        start_life = self.tyre_model.characteristics[start].max_useful_life_laps
        one_stop_lap = max(2, min(total, int(min(start_life, total * 0.55)) + 1))

        for compound in dry_compounds:
            if compound == start or one_stop_lap > total:
                continue
            candidates.append(
                CandidateStrategy(
                    strategy_id=f"{start.value}-{compound.value}-{one_stop_lap}",
                    stints=(
                        StrategyStint(
                            compound=start,
                            start_lap=1,
                            end_lap=one_stop_lap - 1,
                        ),
                        StrategyStint(
                            compound=compound,
                            start_lap=one_stop_lap,
                            end_lap=total,
                        ),
                    ),
                    recommendation_reason=(
                        "One-stop dry strategy based on useful tyre life."
                    ),
                )
            )

        if total >= 45 and start in dry_compounds:
            first_pit = max(2, total // 3 + 1)
            second_pit = max(first_pit + 1, (2 * total) // 3 + 1)
            if second_pit <= total:
                middle = TyreCompound.MEDIUM if start != TyreCompound.MEDIUM else TyreCompound.HARD
                end = TyreCompound.SOFT if start != TyreCompound.SOFT else TyreCompound.MEDIUM
                candidates.append(
                    CandidateStrategy(
                        strategy_id=f"{start.value}-{middle.value}-{end.value}-TWO-STOP",
                        stints=(
                            StrategyStint(compound=start, start_lap=1, end_lap=first_pit - 1),
                            StrategyStint(compound=middle, start_lap=first_pit, end_lap=second_pit - 1),
                            StrategyStint(compound=end, start_lap=second_pit, end_lap=total),
                        ),
                        recommendation_reason="Two-stop dry strategy for tyre-life coverage.",
                    )
                )

        return candidates

    def _weather_candidates(
        self,
        config: RaceConfig,
        rain_probability_multiplier: float = 1.0,
        degradation_multiplier: float = 1.0,
    ) -> list[CandidateStrategy]:
        """Use crossover detection to generate plausible wet-weather strategies."""
        total = config.circuit.total_laps
        baseline = self.simulator.run(
            config,
            rain_probability_multiplier=rain_probability_multiplier,
            degradation_multiplier=degradation_multiplier,
        )
        weather = baseline.weather_history
        if not weather or max(state.track_wetness for state in weather) < 0.18:
            return []

        candidates: list[CandidateStrategy] = []
        alternatives = (TyreCompound.INTERMEDIATE, TyreCompound.WET)
        if config.starting_compound in alternatives:
            alternatives = (TyreCompound.MEDIUM, TyreCompound.INTERMEDIATE, TyreCompound.WET)

        for compound in alternatives:
            if compound == config.starting_compound:
                continue
            crossover = self.crossover_engine.find_crossover_lap(
                current_compound=config.starting_compound,
                alternative_compound=compound,
                current_tyre_age=0,
                current_lap=2,
                remaining_laps=total - 1,
                predicted_weather=weather[1:],
                circuit_config=config.circuit,
            )
            if not crossover.crossover_detected or crossover.recommended_pit_lap is None:
                continue

            pit_lap = max(2, min(total, crossover.recommended_pit_lap))
            candidates.append(
                CandidateStrategy(
                    strategy_id=f"{config.starting_compound.value}-{compound.value}-XOVER-{pit_lap}",
                    stints=(
                        StrategyStint(
                            compound=config.starting_compound,
                            start_lap=1,
                            end_lap=pit_lap - 1,
                        ),
                        StrategyStint(compound=compound, start_lap=pit_lap, end_lap=total),
                    ),
                    recommendation_reason=crossover.reason,
                )
            )

        return candidates

    @staticmethod
    def _pit_plan_from_stints(stints: tuple[StrategyStint, ...] | list[StrategyStint]) -> list[PitInstruction]:
        """Convert stint boundaries into simulator pit instructions."""
        return [
            PitInstruction(lap=stint.start_lap, compound=stint.compound)
            for stint in stints[1:]
        ]

    @staticmethod
    def _deduplicate_candidates(
        candidates: list[CandidateStrategy],
    ) -> list[CandidateStrategy]:
        """Remove candidates with identical stint structures."""
        seen: set[tuple[tuple[TyreCompound, int, int], ...]] = set()
        unique: list[CandidateStrategy] = []
        for candidate in candidates:
            key = tuple(
                (stint.compound, stint.start_lap, stint.end_lap)
                for stint in candidate.stints
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    @staticmethod
    def _stable_seed(seed: int, strategy_id: str) -> int:
        """Build a process-stable deterministic seed."""
        return seed * 10_000 + sum(
            (index + 1) * ord(character)
            for index, character in enumerate(strategy_id)
        )

    @staticmethod
    def _risk_for_strategy(candidate: CandidateStrategy, confidence: float) -> str:
        """Classify simple deterministic risk from stops, weather tyres, and confidence."""
        wet_tyres = {TyreCompound.INTERMEDIATE, TyreCompound.WET}
        uses_wet_tyre = any(stint.compound in wet_tyres for stint in candidate.stints)
        pit_stops = max(0, len(candidate.stints) - 1)
        if confidence < 0.985 or pit_stops >= 2 or uses_wet_tyre:
            return "HIGH"
        if confidence < 0.995 or pit_stops == 1:
            return "MEDIUM"
        return "LOW"
