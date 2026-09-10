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
class DriverUndercutState:
    driver_name: str
    position: int
    compound: TyreCompound
    tyre_age: int
    gap_to_driver_ahead_seconds: float
    current_lap: int
    base_lap_time_seconds: float
    degradation_per_lap: float


@dataclass
class UndercutAnalysis:
    undercut_available: bool
    projected_gain_seconds: float
    projected_gap_after_cycle_seconds: float
    projected_position: int
    confidence: float
    recommendation: str
    recommended_compound: TyreCompound
    analysis_laps: int


class UndercutEngine:
    """
    Phase 10.1

    Simulates whether the following driver can gain enough time
    by pitting earlier than the driver ahead.
    """

    COMPOUND_FRESH_TYRE_ADVANTAGE = {
        "SOFT": 1.20,
        "MEDIUM": 0.90,
        "HARD": 0.65,
        "INTERMEDIATE": 0.75,
        "WET": 0.60,
    }

    def calculate_tyre_penalty(
        self,
        tyre_age: int,
        degradation_per_lap: float,
    ) -> float:
        """
        Returns the current tyre degradation penalty in seconds.
        """

        return max(
            0.0,
            tyre_age * degradation_per_lap,
        )

    def simulate_lap_time(
        self,
        base_lap_time_seconds: float,
        tyre_age: int,
        degradation_per_lap: float,
        fresh_tyre_bonus: float = 0.0,
    ) -> float:
        degradation_penalty = self.calculate_tyre_penalty(
            tyre_age=tyre_age,
            degradation_per_lap=degradation_per_lap,
        )

        return (
            base_lap_time_seconds
            + degradation_penalty
            - fresh_tyre_bonus
        )

    def analyze(
        self,
        attacker: DriverUndercutState,
        defender: DriverUndercutState,
        pit_lane_time_loss_seconds: float,
        new_compound: TyreCompound = "HARD",
        defender_stays_out_laps: int = 2,
    ) -> UndercutAnalysis:
        """
        Compare:

        ATTACKER:
        pits now and receives fresh tyres

        DEFENDER:
        stays out for `defender_stays_out_laps`
        before pitting

        The result estimates whether the attacker gains enough
        time to overtake after the pit cycle.
        """

        if defender_stays_out_laps < 1:
            raise ValueError(
                "defender_stays_out_laps must be at least 1"
            )

        if attacker.position <= 1:
            return UndercutAnalysis(
                undercut_available=False,
                projected_gain_seconds=0.0,
                projected_gap_after_cycle_seconds=0.0,
                projected_position=attacker.position,
                confidence=0.0,
                recommendation="NO UNDERCUT NEEDED",
                recommended_compound=new_compound,
                analysis_laps=defender_stays_out_laps,
            )

        current_gap = attacker.gap_to_driver_ahead_seconds

        fresh_tyre_bonus = (
            self.COMPOUND_FRESH_TYRE_ADVANTAGE[new_compound]
        )

        attacker_time = pit_lane_time_loss_seconds
        defender_time = 0.0

        attacker_tyre_age = 0
        defender_tyre_age = defender.tyre_age

        for _ in range(defender_stays_out_laps):
            attacker_lap_time = self.simulate_lap_time(
                base_lap_time_seconds=attacker.base_lap_time_seconds,
                tyre_age=attacker_tyre_age,
                degradation_per_lap=attacker.degradation_per_lap,
                fresh_tyre_bonus=fresh_tyre_bonus,
            )

            defender_lap_time = self.simulate_lap_time(
                base_lap_time_seconds=defender.base_lap_time_seconds,
                tyre_age=defender_tyre_age,
                degradation_per_lap=defender.degradation_per_lap,
            )

            attacker_time += attacker_lap_time
            defender_time += defender_lap_time

            attacker_tyre_age += 1
            defender_tyre_age += 1

        # Defender eventually pits too.
        defender_time += pit_lane_time_loss_seconds

        # Positive = attacker gained time.
        projected_gain = (
            defender_time
            - attacker_time
        )

        projected_gap_after_cycle = (
            current_gap
            - projected_gain
        )

        undercut_success = projected_gap_after_cycle <= 0

        projected_position = (
            defender.position
            if undercut_success
            else attacker.position
        )

        confidence = self.calculate_confidence(
            projected_gain_seconds=projected_gain,
            current_gap_seconds=current_gap,
            undercut_success=undercut_success,
        )

        recommendation = self.get_recommendation(
            undercut_success=undercut_success,
            projected_gain_seconds=projected_gain,
            confidence=confidence,
        )

        return UndercutAnalysis(
            undercut_available=undercut_success,
            projected_gain_seconds=round(
                projected_gain,
                3,
            ),
            projected_gap_after_cycle_seconds=round(
                projected_gap_after_cycle,
                3,
            ),
            projected_position=projected_position,
            confidence=round(confidence, 3),
            recommendation=recommendation,
            recommended_compound=new_compound,
            analysis_laps=defender_stays_out_laps,
        )

    def calculate_confidence(
        self,
        projected_gain_seconds: float,
        current_gap_seconds: float,
        undercut_success: bool,
    ) -> float:
        """
        Simple deterministic confidence score.

        Later in Phase 10 we can replace this with simulation
        perturbations using weather, traffic and degradation risk.
        """

        if current_gap_seconds <= 0:
            return 0.0

        margin = abs(projected_gain_seconds) / max(
            current_gap_seconds,
            0.1,
        )

        if undercut_success:
            confidence = 0.60 + min(
                margin * 0.25,
                0.38,
            )
        else:
            confidence = 0.25 + min(
                max(projected_gain_seconds, 0.0)
                / max(current_gap_seconds, 0.1)
                * 0.20,
                0.20,
            )

        return max(
            0.0,
            min(confidence, 0.98),
        )

    def get_recommendation(
        self,
        undercut_success: bool,
        projected_gain_seconds: float,
        confidence: float,
    ) -> str:

        if (
            undercut_success
            and confidence >= 0.80
        ):
            return "BOX THIS LAP"

        if (
            undercut_success
            and confidence >= 0.60
        ):
            return "UNDERCUT OPPORTUNITY — CONSIDER PITTING"

        if projected_gain_seconds > 0:
            return "POSSIBLE UNDERCUT — WAIT FOR BETTER WINDOW"

        return "UNDERCUT NOT RECOMMENDED"