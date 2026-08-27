import time
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.historical import Circuit
from app.services.circuit_service import CircuitNotFoundErrorLookup, CircuitService
from app.services.data_import_service import DataImportService
from app.services.simulator import CircuitIntelligence, RaceSimulator
from tests.test_simulator import default_config


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        DataImportService().seed_defaults(db)
        yield db
    finally:
        db.close()


def test_retrieve_circuit_successfully(db_session: Session) -> None:
    service = CircuitService()

    circuit = service.get_circuit_by_name("Monza", db_session)

    assert circuit is not None
    assert circuit.name == "Monza"


def test_convert_database_circuit_to_circuit_config(db_session: Session) -> None:
    service = CircuitService()
    circuit = db_session.scalar(select(Circuit).where(Circuit.name == "Silverstone"))

    assert circuit is not None
    config = service.to_circuit_config(circuit)

    assert config.circuit_name == "Silverstone"
    assert config.total_laps == circuit.total_laps
    assert config.base_lap_time_seconds == circuit.base_lap_time_seconds


def test_missing_circuit_returns_none_and_config_raises(db_session: Session) -> None:
    service = CircuitService()

    assert service.get_circuit_by_name("Atlantis", db_session) is None
    with pytest.raises(CircuitNotFoundErrorLookup):
        service.get_circuit_config("Atlantis", db_session)


def test_direct_simulator_still_runs_without_database() -> None:
    start = time.perf_counter()

    result = RaceSimulator().run(default_config())

    elapsed = time.perf_counter() - start
    assert result.completed_laps == 57
    assert elapsed < 2.0


def test_higher_tyre_wear_factor_increases_degradation_effect() -> None:
    config = default_config()
    simulator = RaceSimulator()

    low_wear = simulator.run(
        config,
        circuit_intelligence=CircuitIntelligence(tyre_wear_factor=0.8),
    )
    high_wear = simulator.run(
        config,
        circuit_intelligence=CircuitIntelligence(tyre_wear_factor=1.4),
    )

    assert high_wear.final_race_time_seconds > low_wear.final_race_time_seconds


def test_safety_car_probability_adjustment_is_clamped() -> None:
    service = CircuitService()

    assert service.adjusted_safety_car_probability(0.2, 1.5) == pytest.approx(0.3)
    assert service.adjusted_safety_car_probability(0.9, 2.0) == 1.0
    assert service.adjusted_safety_car_probability(-0.2, 1.0) == 0.0
