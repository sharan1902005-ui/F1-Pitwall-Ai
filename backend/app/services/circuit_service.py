"""Circuit metadata access and circuit intelligence helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.circuit import CircuitConfig
from app.models.historical import Circuit


class CircuitNotFoundErrorLookup(LookupError):
    """Raised when requested circuit metadata is missing."""


class CircuitService:
    """Read circuit metadata and convert it into simulator inputs."""

    def get_all_circuits(self, db: Session) -> list[Circuit]:
        """Return all stored circuits ordered by name."""
        return list(db.scalars(select(Circuit).order_by(Circuit.name)).all())

    def get_circuit_by_id(self, circuit_id: int, db: Session) -> Circuit | None:
        """Return a circuit by primary key."""
        return db.get(Circuit, circuit_id)

    def get_circuit_by_name(self, circuit_name: str, db: Session) -> Circuit | None:
        """Return a circuit by case-insensitive name."""
        return db.scalar(
            select(Circuit).where(Circuit.name.ilike(circuit_name)).limit(1)
        )

    def get_circuit_config(self, circuit_name: str, db: Session) -> CircuitConfig:
        """Convert stored circuit defaults into a simulation CircuitConfig."""
        circuit = self.get_circuit_by_name(circuit_name, db)
        if circuit is None:
            raise CircuitNotFoundErrorLookup(f"Circuit not found: {circuit_name}")
        return self.to_circuit_config(circuit)

    def to_circuit_config(self, circuit: Circuit) -> CircuitConfig:
        """Map a database Circuit into the existing simulation contract."""
        return CircuitConfig(
            circuit_name=circuit.name,
            total_laps=circuit.total_laps,
            base_lap_time_seconds=circuit.base_lap_time_seconds,
            pit_lane_time_loss_seconds=circuit.pit_lane_time_loss_seconds,
            avg_track_temp=circuit.avg_track_temp,
            avg_air_temp=circuit.avg_air_temp,
        )

    @staticmethod
    def adjusted_safety_car_probability(
        base_probability: float,
        safety_car_factor: float,
    ) -> float:
        """Apply circuit safety-car factor and clamp to [0, 1]."""
        return max(0.0, min(1.0, base_probability * safety_car_factor))
