from fastapi import APIRouter

from app.schemas.undercut import (
    DriverUndercutRequest,
    UndercutRequest,
    UndercutResponse,
)

from app.services.undercut_engine import (
    DriverUndercutState,
    UndercutEngine,
)


router = APIRouter(
    prefix="/api/strategy",
    tags=["Strategy Intelligence"],
)


@router.post(
    "/undercut",
    response_model=UndercutResponse,
)
def analyze_undercut(
    request: UndercutRequest,
):
    engine = UndercutEngine()

    attacker = DriverUndercutState(
        driver_name=request.attacker.driver_name,
        position=request.attacker.position,
        compound=request.attacker.compound,
        tyre_age=request.attacker.tyre_age,
        gap_to_driver_ahead_seconds=(
            request.attacker.gap_to_driver_ahead_seconds
        ),
        current_lap=request.attacker.current_lap,
        base_lap_time_seconds=(
            request.attacker.base_lap_time_seconds
        ),
        degradation_per_lap=(
            request.attacker.degradation_per_lap
        ),
    )

    defender = DriverUndercutState(
        driver_name=request.defender.driver_name,
        position=request.defender.position,
        compound=request.defender.compound,
        tyre_age=request.defender.tyre_age,
        gap_to_driver_ahead_seconds=(
            request.defender.gap_to_driver_ahead_seconds
        ),
        current_lap=request.defender.current_lap,
        base_lap_time_seconds=(
            request.defender.base_lap_time_seconds
        ),
        degradation_per_lap=(
            request.defender.degradation_per_lap
        ),
    )

    result = engine.analyze(
        attacker=attacker,
        defender=defender,
        pit_lane_time_loss_seconds=(
            request.pit_lane_time_loss_seconds
        ),
        new_compound=request.new_compound,
        defender_stays_out_laps=(
            request.defender_stays_out_laps
        ),
    )

    return UndercutResponse(
        undercut_available=result.undercut_available,
        projected_gain_seconds=(
            result.projected_gain_seconds
        ),
        projected_gap_after_cycle_seconds=(
            result.projected_gap_after_cycle_seconds
        ),
        projected_position=result.projected_position,
        confidence=result.confidence,
        recommendation=result.recommendation,
        recommended_compound=(
            result.recommended_compound
        ),
        analysis_laps=result.analysis_laps,
    )