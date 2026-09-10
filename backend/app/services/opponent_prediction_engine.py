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
class OpponentState:
    driver_name: str
    position: int
    compound: TyreCompound
    tyre_age: int
    current_lap: int
    total_laps: int
    base_lap_time_seconds: float
    degradation_per_lap: float
    pit_stops_completed: int
    weather_risk: float


@dataclass
class PitProbability:
    lap: int
    probability: float


@dataclass
class OpponentPrediction:
    driver_name: str
    most_likely_pit_lap: int
    most_likely_probability: float
    confidence: float
    recommendation: str
    predictions: list[PitProbability]


class OpponentPredictionEngine:

    TYRE_LIFE = {
        "SOFT": 18,
        "MEDIUM": 30,
        "HARD": 42,
        "INTERMEDIATE": 25,
        "WET": 30,
    }

    def calculate_probability(
        self,
        opponent: OpponentState,
        predicted_lap: int,
    ) -> float:

        laps_until_pit = (
            predicted_lap - opponent.current_lap
        )

        projected_tyre_age = (
            opponent.tyre_age + laps_until_pit
        )

        expected_tyre_life = (
            self.TYRE_LIFE[opponent.compound]
        )

        tyre_usage_ratio = (
            projected_tyre_age
            / expected_tyre_life
        )

        # Base probability grows as tyres approach
        # their estimated useful life.
        probability = tyre_usage_ratio * 100

        # Higher degradation increases pit likelihood.
        degradation_factor = min(
            opponent.degradation_per_lap * 100,
            20,
        )

        probability += degradation_factor

        # Near the end of the race, pitting becomes
        # less attractive.
        remaining_laps = (
            opponent.total_laps - predicted_lap
        )

        if remaining_laps < 5:
            probability *= 0.60

        elif remaining_laps < 10:
            probability *= 0.80

        # Previous pit stops reduce the chance slightly
        # because the driver may already be on a strategy
        # with fewer remaining stops.
        probability -= (
            opponent.pit_stops_completed * 5
        )

        # Weather uncertainty can increase the chance
        # of a strategy change or tyre switch.
        probability += (
            opponent.weather_risk * 20
        )

        return max(
            0.0,
            min(probability, 100.0),
        )

    def analyze(
        self,
        opponent: OpponentState,
        prediction_window_laps: int = 5,
    ) -> OpponentPrediction:

        if prediction_window_laps < 1:
            raise ValueError(
                "prediction_window_laps must be at least 1"
            )

        predictions = []

        final_lap = min(
            opponent.current_lap + prediction_window_laps,
            opponent.total_laps,
        )

        for lap in range(
            opponent.current_lap + 1,
            final_lap + 1,
        ):

            probability = self.calculate_probability(
                opponent=opponent,
                predicted_lap=lap,
            )

            predictions.append(
                PitProbability(
                    lap=lap,
                    probability=round(probability, 2),
                )
            )

        most_likely = max(
            predictions,
            key=lambda prediction: prediction.probability,
        )

        confidence = self.calculate_confidence(
            predictions=predictions,
            most_likely=most_likely,
        )

        recommendation = self.get_recommendation(
            most_likely=most_likely,
            confidence=confidence,
        )

        return OpponentPrediction(
            driver_name=opponent.driver_name,
            most_likely_pit_lap=most_likely.lap,
            most_likely_probability=(
                most_likely.probability
            ),
            confidence=round(confidence, 3),
            recommendation=recommendation,
            predictions=predictions,
        )

    def calculate_confidence(
        self,
        predictions: list[PitProbability],
        most_likely: PitProbability,
    ) -> float:

        if len(predictions) == 1:
            return 0.50

        sorted_predictions = sorted(
            predictions,
            key=lambda prediction: prediction.probability,
            reverse=True,
        )

        second_best = sorted_predictions[1]

        separation = (
            most_likely.probability
            - second_best.probability
        )

        confidence = 0.55 + min(
            separation / 30,
            0.40,
        )

        return max(
            0.0,
            min(confidence, 0.95),
        )

    def get_recommendation(
        self,
        most_likely: PitProbability,
        confidence: float,
    ) -> str:

        if most_likely.probability >= 75:
            return (
                f"OPPONENT LIKELY TO PIT ON "
                f"LAP {most_likely.lap}"
            )

        if most_likely.probability >= 50:
            return (
                f"MONITOR OPPONENT PIT WINDOW "
                f"AROUND LAP {most_likely.lap}"
            )

        return "OPPONENT PIT STOP NOT IMMINENT"