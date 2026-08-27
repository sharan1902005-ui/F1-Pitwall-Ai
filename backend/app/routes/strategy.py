"""Strategy analysis routes."""

from fastapi import APIRouter

from app.schemas.simulation import RaceConfig, StrategyAnalysisResponse
from app.services.strategy_engine import StrategyEngine


router = APIRouter(prefix="/api/strategy", tags=["strategy"])
strategy_engine = StrategyEngine()


@router.post("/analyze", response_model=StrategyAnalysisResponse)
def analyze_strategy(config: RaceConfig) -> StrategyAnalysisResponse:
    """Analyze and rank deterministic race strategies."""
    return strategy_engine.analyze(config)
