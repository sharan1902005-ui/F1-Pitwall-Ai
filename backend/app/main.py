"""FastAPI application entry point for PitWall AI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes.circuits import router as circuits_router
from app.routes.live_race import router as live_race_router
from app.routes.multi_race import router as multi_race_router
from app.routes.race_engineer import router as race_engineer_router
from app.routes.races import router as races_router
from app.routes.seasons import router as seasons_router
from app.routes.simulation import router as simulation_router
from app.routes.strategy import router as strategy_router
from app.routes import undercut
from app.routes import overcut
from app.routes import pit_window
from app.routes import opponent_prediction
from app.routes import traffic
from app.routes import strategy_risk


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize development database tables and seed data."""
    init_db(seed=True)
    yield


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation_router)
app.include_router(strategy_router)
app.include_router(circuits_router)
app.include_router(races_router)
app.include_router(race_engineer_router)
app.include_router(live_race_router)
app.include_router(multi_race_router)
app.include_router(seasons_router)
app.include_router(undercut.router)
app.include_router(overcut.router)
app.include_router(pit_window.router)
app.include_router(opponent_prediction.router)
app.include_router(traffic.router)
app.include_router(strategy_risk.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return service health for deployment and smoke checks."""
    return {"status": "ok"}
