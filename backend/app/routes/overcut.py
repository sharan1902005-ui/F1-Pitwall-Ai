from fastapi import APIRouter

from app.schemas.overcut import (
    OvercutRequest,
    OvercutResponse,
    OvercutOptionResponse,
)

from app.services.overcut_engine import (
    DriverOvercutState,
    OvercutEngine,
)


router = APIRouter(
    prefix="/api/strategy",
    tags=["Strategy Intelligence"],
)


@router.post(
    "/overcut",
    response_model=OvercutResponse,
)
def analyze_overcut(
    request: OvercutRequest,
):

    engine = OvercutEngine()

    driver = DriverOvercutState(
        driver_name=request.driver.driver_name,
        position=request.driver.position,
        compound=request.driver.compound,
        tyre_age=request.driver.tyre_age,
        gap_to_driver_ahead_seconds=(
            request.driver.gap_to_driver_ahead_seconds
        ),
        current_lap=request.driver.current_lap,
        base_lap_time_seconds=(
            request.driver.base_lap_time_seconds
        ),
        degradation_per_lap=(
            request.driver.degradation_per_lap
        ),
    )

    opponent = DriverOvercutState(
        driver_name=request.opponent.driver_name,
        position=request.opponent.position,
        compound=request.opponent.compound,
        tyre_age=request.opponent.tyre_age,
        gap_to_driver_ahead_seconds=(
            request.opponent.gap_to_driver_ahead_seconds
        ),
        current_lap=request.opponent.current_lap,
        base_lap_time_seconds=(
            request.opponent.base_lap_time_seconds
        ),
        degradation_per_lap=(
            request.opponent.degradation_per_lap
        ),
    )

    result = engine.analyze(
        driver=driver,
        opponent=opponent,
        pit_lane_time_loss_seconds=(
            request.pit_lane_time_loss_seconds
        ),
        max_stay_out_laps=request.max_stay_out_laps,
    )

    return OvercutResponse(
        overcut_available=result.overcut_available,
        best_stay_out_laps=result.best_stay_out_laps,
        projected_advantage_seconds=(
            result.projected_advantage_seconds
        ),
        projected_gap_after_cycle_seconds=(
            result.projected_gap_after_cycle_seconds
        ),
        projected_position=result.projected_position,
        confidence=result.confidence,
        recommendation=result.recommendation,
        options=[
            OvercutOptionResponse(
                stay_out_laps=option.stay_out_laps,
                projected_advantage_seconds=(
                    option.projected_advantage_seconds
                ),
                projected_gap_after_cycle_seconds=(
                    option.projected_gap_after_cycle_seconds
                ),
            )
            for option in result.options
        ],
    )