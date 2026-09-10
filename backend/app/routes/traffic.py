from fastapi import APIRouter

from app.schemas.traffic import (
    TrafficRequest,
    TrafficResponse,
)

from app.services.traffic_engine import (
    TrafficDriverState,
    CarAheadState,
    TrafficEngine,
)


router = APIRouter(
    prefix="/api/strategy",
    tags=["Strategy Intelligence"],
)


@router.post(
    "/traffic",
    response_model=TrafficResponse,
)
def analyze_traffic(
    request: TrafficRequest,
):

    engine = TrafficEngine()

    driver = TrafficDriverState(
        driver_name=request.driver.driver_name,
        current_position=(
            request.driver.current_position
        ),
        current_lap=request.driver.current_lap,
        base_lap_time_seconds=(
            request.driver.base_lap_time_seconds
        ),
    )

    car_ahead = CarAheadState(
        driver_name=request.car_ahead.driver_name,
        gap_seconds=request.car_ahead.gap_seconds,
        pace_delta_seconds=(
            request.car_ahead.pace_delta_seconds
        ),
        overtaking_difficulty=(
            request.car_ahead.overtaking_difficulty
        ),
    )

    result = engine.analyze(
        driver=driver,
        car_ahead=car_ahead,
        laps_in_traffic=request.laps_in_traffic,
    )

    return TrafficResponse(
        dirty_air_penalty_seconds=(
            result.dirty_air_penalty_seconds
        ),
        projected_traffic_loss_seconds=(
            result.projected_traffic_loss_seconds
        ),
        overtaking_difficulty=(
            result.overtaking_difficulty
        ),
        traffic_risk=result.traffic_risk,
        recommendation=result.recommendation,
    )