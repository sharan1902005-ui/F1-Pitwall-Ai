from fastapi import APIRouter

from app.schemas.pit_window import (
    PitWindowRequest,
    PitWindowResponse,
    PitWindowOptionResponse,
)

from app.services.pit_window_engine import (
    PitWindowDriverState,
    PitWindowEngine,
)


router = APIRouter(
    prefix="/api/strategy",
    tags=["Strategy Intelligence"],
)


@router.post(
    "/pit-window",
    response_model=PitWindowResponse,
)
def analyze_pit_window(
    request: PitWindowRequest,
):

    engine = PitWindowEngine()

    driver = PitWindowDriverState(
        driver_name=request.driver.driver_name,
        current_lap=request.driver.current_lap,
        total_laps=request.driver.total_laps,
        position=request.driver.position,
        compound=request.driver.compound,
        tyre_age=request.driver.tyre_age,
        base_lap_time_seconds=(
            request.driver.base_lap_time_seconds
        ),
        degradation_per_lap=(
            request.driver.degradation_per_lap
        ),
        gap_to_driver_ahead_seconds=(
            request.driver.gap_to_driver_ahead_seconds
        ),
    )

    result = engine.analyze(
        driver=driver,
        pit_lane_time_loss_seconds=(
            request.pit_lane_time_loss_seconds
        ),
        earliest_pit_lap=request.earliest_pit_lap,
        latest_pit_lap=request.latest_pit_lap,
        new_compound=request.new_compound,
    )

    return PitWindowResponse(
        earliest_lap=result.earliest_lap,
        optimal_lap=result.optimal_lap,
        latest_lap=result.latest_lap,
        recommended_compound=(
            result.recommended_compound
        ),
        projected_gain_seconds=(
            result.projected_gain_seconds
        ),
        projected_race_time_seconds=(
            result.projected_race_time_seconds
        ),
        confidence=result.confidence,
        recommendation=result.recommendation,
        options=[
            PitWindowOptionResponse(
                pit_lap=option.pit_lap,
                projected_race_time_seconds=(
                    option.projected_race_time_seconds
                ),
                projected_gain_seconds=(
                    option.projected_gain_seconds
                ),
            )
            for option in result.options
        ],
    )