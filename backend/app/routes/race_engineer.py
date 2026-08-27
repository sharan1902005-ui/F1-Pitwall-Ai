"""Race engineer explanation routes."""

from fastapi import APIRouter, HTTPException

from app.schemas.race_engineer import (
    DecisionRequest,
    EngineerResponse,
    ExplainStrategyRequest,
    ScenarioRequest,
    ScenarioResponse,
)
from app.services.race_engineer import RaceEngineer
from app.services.scenario_service import ScenarioService
from app.services.strategy_engine import StrategyEngine


router = APIRouter(prefix="/api/race-engineer", tags=["race-engineer"])
strategy_engine = StrategyEngine()
race_engineer = RaceEngineer()
scenario_service = ScenarioService()


@router.post("/explain-strategy", response_model=EngineerResponse)
def explain_strategy(request: ExplainStrategyRequest) -> EngineerResponse:
    """Explain a selected or recommended strategy from deterministic analysis."""
    analysis = strategy_engine.analyze(request.race_config)
    if analysis.recommended_strategy is None:
        raise HTTPException(status_code=404, detail="No strategy candidates available")

    strategy = analysis.recommended_strategy
    if request.strategy_id is not None:
        strategy = next(
            (
                candidate
                for candidate in analysis.strategies
                if candidate.strategy_id == request.strategy_id
            ),
            None,
        )
        if strategy is None:
            raise HTTPException(status_code=404, detail="Requested strategy not found")

    return race_engineer.explain_strategy(
        request.race_config,
        strategy,
        request.context,
    )


@router.post("/decision", response_model=EngineerResponse)
def current_decision(request: DecisionRequest) -> EngineerResponse:
    """Return a grounded current-race recommendation from structured context."""
    analysis = strategy_engine.analyze(request.race_config)
    if analysis.recommended_strategy is None:
        raise HTTPException(status_code=404, detail="No strategy candidates available")
    return race_engineer.explain_strategy(
        request.race_config,
        analysis.recommended_strategy,
        request.context,
    )


@router.post("/scenario", response_model=ScenarioResponse)
def analyze_scenario(request: ScenarioRequest) -> ScenarioResponse:
    """Run deterministic what-if analysis and explain the result."""
    try:
        return scenario_service.analyze(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
