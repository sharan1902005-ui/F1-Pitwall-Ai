from dataclasses import dataclass


@dataclass
class StrategyRiskState:
    weather_risk: float
    traffic_risk: str
    tyre_age: int
    estimated_tyre_life: int
    degradation_per_lap: float
    safety_car_probability: float
    opponent_pit_probability: float
    pit_lane_time_loss_seconds: float


@dataclass
class StrategyRiskAnalysis:
    overall_risk_score: float
    risk_level: str
    weather_risk_score: float
    traffic_risk_score: float
    tyre_risk_score: float
    safety_car_risk_score: float
    opponent_risk_score: float
    recommendation: str


class StrategyRiskEngine:

    def calculate_weather_risk(
        self,
        weather_risk: float,
    ) -> float:

        return max(
            0.0,
            min(weather_risk * 100, 100.0),
        )

    def calculate_traffic_risk(
        self,
        traffic_risk: str,
    ) -> float:

        risk_map = {
            "LOW": 25.0,
            "MEDIUM": 60.0,
            "HIGH": 90.0,
        }

        return risk_map.get(
            traffic_risk.upper(),
            50.0,
        )

    def calculate_tyre_risk(
        self,
        tyre_age: int,
        estimated_tyre_life: int,
        degradation_per_lap: float,
    ) -> float:

        if estimated_tyre_life <= 0:
            return 100.0

        age_ratio = (
            tyre_age / estimated_tyre_life
        )

        age_score = min(
            age_ratio * 70,
            70.0,
        )

        degradation_score = min(
            degradation_per_lap * 100,
            30.0,
        )

        return min(
            age_score + degradation_score,
            100.0,
        )

    def calculate_safety_car_risk(
        self,
        safety_car_probability: float,
    ) -> float:

        return max(
            0.0,
            min(
                safety_car_probability * 100,
                100.0,
            ),
        )

    def calculate_opponent_risk(
        self,
        opponent_pit_probability: float,
    ) -> float:

        return max(
            0.0,
            min(
                opponent_pit_probability,
                100.0,
            ),
        )

    def calculate_overall_risk(
        self,
        weather: float,
        traffic: float,
        tyre: float,
        safety_car: float,
        opponent: float,
    ) -> float:

        score = (
            weather * 0.20
            + traffic * 0.20
            + tyre * 0.25
            + safety_car * 0.15
            + opponent * 0.20
        )

        return round(
            min(max(score, 0.0), 100.0),
            2,
        )

    def get_risk_level(
        self,
        score: float,
    ) -> str:

        if score >= 70:
            return "HIGH"

        if score >= 40:
            return "MEDIUM"

        return "LOW"

    def get_recommendation(
        self,
        risk_level: str,
    ) -> str:

        if risk_level == "HIGH":
            return (
                "HIGH RISK STRATEGY — CONSIDER "
                "A MORE CONSERVATIVE PIT WINDOW"
            )

        if risk_level == "MEDIUM":
            return (
                "MODERATE STRATEGY RISK — "
                "MONITOR LIVE RACE CONDITIONS"
            )

        return (
            "LOW STRATEGY RISK — "
            "CURRENT PLAN IS STABLE"
        )

    def analyze(
        self,
        state: StrategyRiskState,
    ) -> StrategyRiskAnalysis:

        weather_score = (
            self.calculate_weather_risk(
                state.weather_risk
            )
        )

        traffic_score = (
            self.calculate_traffic_risk(
                state.traffic_risk
            )
        )

        tyre_score = (
            self.calculate_tyre_risk(
                tyre_age=state.tyre_age,
                estimated_tyre_life=(
                    state.estimated_tyre_life
                ),
                degradation_per_lap=(
                    state.degradation_per_lap
                ),
            )
        )

        safety_car_score = (
            self.calculate_safety_car_risk(
                state.safety_car_probability
            )
        )

        opponent_score = (
            self.calculate_opponent_risk(
                state.opponent_pit_probability
            )
        )

        overall_score = (
            self.calculate_overall_risk(
                weather=weather_score,
                traffic=traffic_score,
                tyre=tyre_score,
                safety_car=safety_car_score,
                opponent=opponent_score,
            )
        )

        risk_level = self.get_risk_level(
            overall_score
        )

        recommendation = self.get_recommendation(
            risk_level
        )

        return StrategyRiskAnalysis(
            overall_risk_score=overall_score,
            risk_level=risk_level,
            weather_risk_score=round(
                weather_score,
                2,
            ),
            traffic_risk_score=round(
                traffic_score,
                2,
            ),
            tyre_risk_score=round(
                tyre_score,
                2,
            ),
            safety_car_risk_score=round(
                safety_car_score,
                2,
            ),
            opponent_risk_score=round(
                opponent_score,
                2,
            ),
            recommendation=recommendation,
        )