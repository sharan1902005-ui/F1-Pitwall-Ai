"""Simulation validation routes."""

from fastapi import APIRouter

from app.schemas.simulation import RaceConfig, RaceResult
from app.services.simulator import RaceSimulator


router = APIRouter(prefix="/api/simulation", tags=["simulation"])
simulator = RaceSimulator()


@router.post("/validate")
def validate_simulation_config(config: RaceConfig) -> dict[str, object]:
    """Validate a race configuration and echo key structured fields."""
    return {
        "valid": True,
        "circuit": config.circuit.circuit_name,
        "total_laps": config.circuit.total_laps,
        "starting_compound": config.starting_compound.value,
    }


@router.post("/run", response_model=RaceResult)
def run_simulation(config: RaceConfig) -> RaceResult:
    """Run a complete deterministic race simulation."""
    return simulator.run(config)
