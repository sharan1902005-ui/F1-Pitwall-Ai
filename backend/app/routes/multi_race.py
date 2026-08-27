"""Multi-driver race simulation routes."""

from fastapi import APIRouter, HTTPException

from app.schemas.multi_race import (
    CounterfactualRequest,
    CounterfactualResult,
    MultiDriverRaceConfig,
    MultiDriverRaceResult,
    StrategyComparisonRequest,
    StrategyComparisonResponse,
)
from app.services.competitive_strategy_service import CompetitiveStrategyService


router = APIRouter(prefix="/api/multi-race", tags=["multi-race"])
service = CompetitiveStrategyService()


@router.post("/simulate", response_model=MultiDriverRaceResult)
def simulate_multi_driver_race(config: MultiDriverRaceConfig) -> MultiDriverRaceResult:
    """Run a complete deterministic multi-driver race."""
    try:
        return service.simulate(config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/compare-strategies", response_model=StrategyComparisonResponse)
def compare_strategies(
    request: StrategyComparisonRequest,
) -> StrategyComparisonResponse:
    """Compare strategy alternatives under identical race conditions."""
    try:
        return service.compare_strategies(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/counterfactual", response_model=CounterfactualResult)
def counterfactual(request: CounterfactualRequest) -> CounterfactualResult:
    """Run a controlled counterfactual strategy analysis."""
    try:
        return service.counterfactual(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
