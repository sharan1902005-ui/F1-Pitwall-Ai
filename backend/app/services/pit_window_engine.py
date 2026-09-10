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
class PitWindowDriverState:
    driver_name: str
    current_lap: int
    total_laps: int
    position: int
    compound: TyreCompound
    tyre_age: int
    base_lap_time_seconds: float
    degradation_per_lap: float
    gap_to_driver_ahead_seconds: float


@dataclass
class PitWindowOption:
    pit_lap: int
    projected_race_time_seconds: float
    projected_gain_seconds: float


@dataclass
class PitWindowAnalysis:
    earliest_lap: int
    optimal_lap: int
    latest_lap: int
    recommended_compound: TyreCompound
    projected_gain_seconds: float
    projected_race_time_seconds: float
    confidence: float
    recommendation: str
    options: list[PitWindowOption]


class PitWindowEngine:

    def __init__(self):

        self.compound_degradation = {
            "SOFT": 0.18,
            "MEDIUM": 0.11,
            "HARD": 0.07,
            "INTERMEDIATE": 0.12,
            "WET": 0.10,
        }

        self.compound_fresh_bonus = {
            "SOFT": 1.2,
            "MEDIUM": 0.8,
            "HARD": 0.5,
            "INTERMEDIATE": 0.6,
            "WET": 0.4,
        }

    def simulate_strategy(
        self,
        driver: PitWindowDriverState,
        pit_lap: int,
        pit_lane_time_loss_seconds: float,
        new_compound: TyreCompound,
    ) -> float:

        total_time = 0.0

        current_tyre_age = driver.tyre_age
        has_pitted = False

        for lap in range(
            driver.current_lap,
            driver.total_laps + 1,
        ):

            if lap == pit_lap:

                total_time += pit_lane_time_loss_seconds

                current_tyre_age = 0

                has_pitted = True

            if has_pitted:

                degradation_rate = (
                    self.compound_degradation[new_compound]
                )

                fresh_bonus = (
                    self.compound_fresh_bonus[new_compound]
                )

            else:

                degradation_rate = (
                    driver.degradation_per_lap
                )

                fresh_bonus = 0.0

            degradation_penalty = (
                current_tyre_age * degradation_rate
            )

            lap_time = (
                driver.base_lap_time_seconds
                + degradation_penalty
                - fresh_bonus
            )

            total_time += lap_time

            current_tyre_age += 1

        return total_time

    def analyze(
        self,
        driver: PitWindowDriverState,
        pit_lane_time_loss_seconds: float,
        earliest_pit_lap: int,
        latest_pit_lap: int,
        new_compound: TyreCompound = "HARD",
    ) -> PitWindowAnalysis:

        if earliest_pit_lap < driver.current_lap:
            raise ValueError(
                "earliest_pit_lap cannot be before current_lap"
            )

        if latest_pit_lap < earliest_pit_lap:
            raise ValueError(
                "latest_pit_lap must be >= earliest_pit_lap"
            )

        if latest_pit_lap > driver.total_laps:
            raise ValueError(
                "latest_pit_lap cannot exceed total_laps"
            )

        options = []

        baseline_time = self.simulate_strategy(
            driver=driver,
            pit_lap=earliest_pit_lap,
            pit_lane_time_loss_seconds=(
                pit_lane_time_loss_seconds
            ),
            new_compound=new_compound,
        )

        for pit_lap in range(
            earliest_pit_lap,
            latest_pit_lap + 1,
        ):

            race_time = self.simulate_strategy(
                driver=driver,
                pit_lap=pit_lap,
                pit_lane_time_loss_seconds=(
                    pit_lane_time_loss_seconds
                ),
                new_compound=new_compound,
            )

            projected_gain = (
                baseline_time - race_time
            )

            options.append(
                PitWindowOption(
                    pit_lap=pit_lap,
                    projected_race_time_seconds=round(
                        race_time,
                        3,
                    ),
                    projected_gain_seconds=round(
                        projected_gain,
                        3,
                    ),
                )
            )

        best_option = min(
            options,
            key=lambda option: (
                option.projected_race_time_seconds
            ),
        )

        best_gain = max(
            option.projected_gain_seconds
            for option in options
        )

        confidence = self.calculate_confidence(
            options=options,
            best_option=best_option,
        )

        recommendation = (
            f"OPTIMAL PIT LAP: {best_option.pit_lap}"
        )

        return PitWindowAnalysis(
            earliest_lap=earliest_pit_lap,
            optimal_lap=best_option.pit_lap,
            latest_lap=latest_pit_lap,
            recommended_compound=new_compound,
            projected_gain_seconds=round(
                best_gain,
                3,
            ),
            projected_race_time_seconds=(
                best_option.projected_race_time_seconds
            ),
            confidence=round(confidence, 3),
            recommendation=recommendation,
            options=options,
        )

    def calculate_confidence(
        self,
        options: list[PitWindowOption],
        best_option: PitWindowOption,
    ) -> float:

        if len(options) < 2:
            return 0.50

        sorted_options = sorted(
            options,
            key=lambda option: (
                option.projected_race_time_seconds
            ),
        )

        second_best = sorted_options[1]

        difference = (
            second_best.projected_race_time_seconds
            - best_option.projected_race_time_seconds
        )

        confidence = 0.55 + min(
            difference / 5.0,
            0.40,
        )

        return max(
            0.0,
            min(confidence, 0.95),
        )