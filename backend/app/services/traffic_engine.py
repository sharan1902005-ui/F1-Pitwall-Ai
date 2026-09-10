from dataclasses import dataclass


@dataclass
class TrafficDriverState:
    driver_name: str
    current_position: int
    current_lap: int
    base_lap_time_seconds: float


@dataclass
class CarAheadState:
    driver_name: str
    gap_seconds: float
    pace_delta_seconds: float
    overtaking_difficulty: float


@dataclass
class TrafficAnalysis:
    dirty_air_penalty_seconds: float
    projected_traffic_loss_seconds: float
    overtaking_difficulty: float
    traffic_risk: str
    recommendation: str


class TrafficEngine:

    def calculate_dirty_air_penalty(
        self,
        gap_seconds: float,
    ) -> float:

        if gap_seconds < 0.5:
            return 1.20

        if gap_seconds < 1.0:
            return 0.80

        if gap_seconds < 2.0:
            return 0.45

        if gap_seconds < 3.0:
            return 0.20

        return 0.0

    def calculate_traffic_loss(
        self,
        driver: TrafficDriverState,
        car_ahead: CarAheadState,
        laps_in_traffic: int,
    ) -> float:

        dirty_air_penalty = (
            self.calculate_dirty_air_penalty(
                car_ahead.gap_seconds
            )
        )

        pace_penalty = max(
            0.0,
            car_ahead.pace_delta_seconds,
        )

        difficulty_factor = (
            car_ahead.overtaking_difficulty
            * 0.5
        )

        loss_per_lap = (
            dirty_air_penalty
            + pace_penalty
            + difficulty_factor
        )

        return round(
            loss_per_lap * laps_in_traffic,
            3,
        )

    def get_traffic_risk(
        self,
        projected_loss: float,
    ) -> str:

        if projected_loss >= 8:
            return "HIGH"

        if projected_loss >= 3:
            return "MEDIUM"

        return "LOW"

    def get_recommendation(
        self,
        projected_loss: float,
        traffic_risk: str,
    ) -> str:

        if traffic_risk == "HIGH":
            return (
                "HIGH TRAFFIC RISK — CONSIDER "
                "DELAYING PIT STOP"
            )

        if traffic_risk == "MEDIUM":
            return (
                "MODERATE TRAFFIC RISK — PIT ONLY "
                "IF TYRE ADVANTAGE IS STRONG"
            )

        return (
            "CLEAR TRAFFIC WINDOW — PIT STOP "
            "IS STRATEGICALLY SAFE"
        )

    def analyze(
        self,
        driver: TrafficDriverState,
        car_ahead: CarAheadState,
        laps_in_traffic: int = 5,
    ) -> TrafficAnalysis:

        if laps_in_traffic < 1:
            raise ValueError(
                "laps_in_traffic must be at least 1"
            )

        dirty_air_penalty = (
            self.calculate_dirty_air_penalty(
                car_ahead.gap_seconds
            )
        )

        projected_loss = (
            self.calculate_traffic_loss(
                driver=driver,
                car_ahead=car_ahead,
                laps_in_traffic=laps_in_traffic,
            )
        )

        traffic_risk = self.get_traffic_risk(
            projected_loss
        )

        recommendation = self.get_recommendation(
            projected_loss=projected_loss,
            traffic_risk=traffic_risk,
        )

        return TrafficAnalysis(
            dirty_air_penalty_seconds=round(
                dirty_air_penalty,
                3,
            ),
            projected_traffic_loss_seconds=(
                projected_loss
            ),
            overtaking_difficulty=round(
                car_ahead.overtaking_difficulty,
                3,
            ),
            traffic_risk=traffic_risk,
            recommendation=recommendation,
        )