from fastapi import APIRouter

from app.schemas.strategy_risk import (
    StrategyRiskRequest,
    StrategyRiskResponse,
)

from app.services.strategy_risk_engine import (
    StrategyRiskState,
    StrategyRiskEngine,
)


router = APIRouter(
    prefix="/api/strategy",
    tags=["Strategy Intelligence"],
)


@router.post(
    "/risk",
    response_model=StrategyRiskResponse,
)
def analyze_strategy_risk(
    request: StrategyRiskRequest,
):

    engine = StrategyRiskEngine()

    state = StrategyRiskState(
        weather_risk=request.weather_risk,
        traffic_risk=request.traffic_risk,
        tyre_age=request.tyre_age,
        estimated_tyre_life=(
            request.estimated_tyre_life
        ),
        degradation_per_lap=(
            request.degradation_per_lap
        ),
        safety_car_probability=(
            request.safety_car_probability
        ),
        opponent_pit_probability=(
            request.opponent_pit_probability
        ),
        pit_lane_time_loss_seconds=(
            request.pit_lane_time_loss_seconds
        ),
    )

    result = engine.analyze(state)

    return StrategyRiskResponse(
        overall_risk_score=(
            result.overall_risk_score
        ),
        risk_level=result.risk_level,
        weather_risk_score=(
            result.weather_risk_score
        ),
        traffic_risk_score=(
            result.traffic_risk_score
        ),
        tyre_risk_score=(
            result.tyre_risk_score
        ),
        safety_car_risk_score=(
            result.safety_car_risk_score
        ),
        opponent_risk_score=(
            result.opponent_risk_score
        ),
        recommendation=result.recommendation,
    )