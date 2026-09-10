from dataclasses import dataclass
from typing import Literal


TyreCompound = Literal[
    "SOFT",
    "MEDIUM",
    "HARD",
    "INTERMEDIATE",
    "WET",
]


@dataclass
class DriverOvercutState:
    driver_name: str
    position: int
    compound: TyreCompound
    tyre_age: int
    gap_to_driver_ahead_seconds: float
    current_lap: int
    base_lap_time_seconds: float
    degradation_per_lap: float


@dataclass
class OvercutOption:
    stay_out_laps: int
    projected_advantage_seconds: float
    projected_gap_after_cycle_seconds: float


@dataclass
class OvercutAnalysis:
    overcut_available: bool
    best_stay_out_laps: int
    projected_advantage_seconds: float
    projected_gap_after_cycle_seconds: float
    projected_position: int
    confidence: float
    recommendation: str
    options: list[OvercutOption]


class OvercutEngine:
    """
    Phase 10.2

    Compare pitting immediately against staying out for
    multiple laps after the opponent pits.
    """

    def simulate_lap_time(
        self,
        base_lap_time_seconds: float,
        tyre_age: int,
        degradation_per_lap: float,
    ) -> float:
        degradation_penalty = tyre_age * degradation_per_lap

        return (
            base_lap_time_seconds
            + degradation_penalty
        )

    def analyze(
        self,
        driver: DriverOvercutState,
        opponent: DriverOvercutState,
        pit_lane_time_loss_seconds: float,
        max_stay_out_laps: int = 3,
    ) -> OvercutAnalysis:

        if max_stay_out_laps < 1:
            raise ValueError(
                "max_stay_out_laps must be at least 1"
            )

        current_gap = driver.gap_to_driver_ahead_seconds

        options = []

        # Baseline:
        # Driver pits immediately.
        pit_now_time = pit_lane_time_loss_seconds

        # Opponent has already pitted and is now on fresh tyres.
        opponent_fresh_tyre_age = 0

        for stay_out_laps in range(1, max_stay_out_laps + 1):

            driver_time = 0.0
            opponent_time = 0.0

            driver_tyre_age = driver.tyre_age
            opponent_tyre_age = opponent_fresh_tyre_age

            # Driver stays out while opponent pushes on fresh tyres.
            for _ in range(stay_out_laps):

                driver_lap = self.simulate_lap_time(
                    base_lap_time_seconds=driver.base_lap_time_seconds,
                    tyre_age=driver_tyre_age,
                    degradation_per_lap=driver.degradation_per_lap,
                )

                opponent_lap = self.simulate_lap_time(
                    base_lap_time_seconds=opponent.base_lap_time_seconds,
                    tyre_age=opponent_tyre_age,
                    degradation_per_lap=opponent.degradation_per_lap,
                )

                driver_time += driver_lap
                opponent_time += opponent_lap

                driver_tyre_age += 1
                opponent_tyre_age += 1

            # Driver finally pits.
            driver_time += pit_lane_time_loss_seconds

            # Compare against immediate pit baseline.
            #
            # Positive advantage means staying out generated
            # a better result than pitting immediately.
            projected_advantage = (
                pit_now_time
                - (driver_time - opponent_time)
            )

            projected_gap_after_cycle = (
                current_gap
                - projected_advantage
            )

            options.append(
                OvercutOption(
                    stay_out_laps=stay_out_laps,
                    projected_advantage_seconds=round(
                        projected_advantage,
                        3,
                    ),
                    projected_gap_after_cycle_seconds=round(
                        projected_gap_after_cycle,
                        3,
                    ),
                )
            )

        best_option = max(
            options,
            key=lambda option: option.projected_advantage_seconds,
        )

        overcut_available = (
            best_option.projected_advantage_seconds > 0
        )

        projected_position = (
            opponent.position
            if best_option.projected_gap_after_cycle_seconds <= 0
            else driver.position
        )

        confidence = self.calculate_confidence(
            projected_advantage_seconds=(
                best_option.projected_advantage_seconds
            ),
            current_gap_seconds=current_gap,
            overcut_available=overcut_available,
        )

        recommendation = self.get_recommendation(
            overcut_available=overcut_available,
            stay_out_laps=best_option.stay_out_laps,
            confidence=confidence,
        )

        return OvercutAnalysis(
            overcut_available=overcut_available,
            best_stay_out_laps=best_option.stay_out_laps,
            projected_advantage_seconds=(
                best_option.projected_advantage_seconds
            ),
            projected_gap_after_cycle_seconds=(
                best_option.projected_gap_after_cycle_seconds
            ),
            projected_position=projected_position,
            confidence=round(confidence, 3),
            recommendation=recommendation,
            options=options,
        )

    def calculate_confidence(
        self,
        projected_advantage_seconds: float,
        current_gap_seconds: float,
        overcut_available: bool,
    ) -> float:

        if not overcut_available:
            return 0.0

        margin = (
            projected_advantage_seconds
            / max(current_gap_seconds, 1.0)
        )

        confidence = 0.55 + min(
            margin * 0.25,
            0.40,
        )

        return max(
            0.0,
            min(confidence, 0.95),
        )

    def get_recommendation(
        self,
        overcut_available: bool,
        stay_out_laps: int,
        confidence: float,
    ) -> str:

        if not overcut_available:
            return "PIT NOW"

        if confidence >= 0.80:
            return (
                f"OVERCUT AVAILABLE — "
                f"STAY OUT {stay_out_laps} LAP(S)"
            )

        if confidence >= 0.60:
            return (
                f"POSSIBLE OVERCUT — "
                f"STAY OUT {stay_out_laps} LAP(S)"
            )

        return "PIT NOW"