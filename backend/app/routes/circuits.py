"""Circuit metadata routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.circuit import CircuitConfig
from app.schemas.historical import CircuitRead
from app.services.circuit_service import CircuitService


router = APIRouter(prefix="/api/circuits", tags=["circuits"])
service = CircuitService()


@router.get("", response_model=list[CircuitRead])
def list_circuits(db: Session = Depends(get_db)) -> list[CircuitRead]:
    """Return all development circuit metadata."""
    return service.get_all_circuits(db)


@router.get("/{circuit_id}", response_model=CircuitRead)
def get_circuit(circuit_id: int, db: Session = Depends(get_db)) -> CircuitRead:
    """Return one circuit by ID."""
    circuit = service.get_circuit_by_id(circuit_id, db)
    if circuit is None:
        raise HTTPException(status_code=404, detail="Circuit not found")
    return circuit


@router.get("/{circuit_id}/config", response_model=CircuitConfig)
def get_circuit_config(
    circuit_id: int,
    db: Session = Depends(get_db),
) -> CircuitConfig:
    """Return a simulation-ready CircuitConfig for a stored circuit."""
    circuit = service.get_circuit_by_id(circuit_id, db)
    if circuit is None:
        raise HTTPException(status_code=404, detail="Circuit not found")
    return service.to_circuit_config(circuit)
