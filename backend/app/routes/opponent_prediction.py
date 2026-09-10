from fastapi import APIRouter

from app.schemas.opponent_prediction import (
    OpponentPredictionRequest,
    OpponentPredictionResponse,
    PitProbabilityResponse,
)

from app.services.opponent_prediction_engine import (
    OpponentState,
    OpponentPredictionEngine,
)


router = APIRouter(
    prefix="/api/strategy",
    tags=["Strategy Intelligence"],
)


@router.post(
    "/opponent-prediction",
    response_model=OpponentPredictionResponse,
)
def predict_opponent_strategy(
    request: OpponentPredictionRequest,
):

    engine = OpponentPredictionEngine()

    opponent = OpponentState(
        driver_name=request.driver_name,
        position=request.position,
        compound=request.compound,
        tyre_age=request.tyre_age,
        current_lap=request.current_lap,
        total_laps=request.total_laps,
        base_lap_time_seconds=(
            request.base_lap_time_seconds
        ),
        degradation_per_lap=(
            request.degradation_per_lap
        ),
        pit_stops_completed=(
            request.pit_stops_completed
        ),
        weather_risk=request.weather_risk,
    )

    result = engine.analyze(
        opponent=opponent,
        prediction_window_laps=(
            request.prediction_window_laps
        ),
    )

    return OpponentPredictionResponse(
        driver_name=result.driver_name,
        most_likely_pit_lap=(
            result.most_likely_pit_lap
        ),
        most_likely_probability=(
            result.most_likely_probability
        ),
        confidence=result.confidence,
        recommendation=result.recommendation,
        predictions=[
            PitProbabilityResponse(
                lap=prediction.lap,
                probability=prediction.probability,
            )
            for prediction in result.predictions
        ],
    )