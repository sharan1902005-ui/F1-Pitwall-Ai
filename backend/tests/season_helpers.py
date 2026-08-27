from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.historical import Circuit
from app.schemas.multi_race import DriverConfig
from app.schemas.season import SeasonCalendarRound, SeasonCreateRequest
from app.schemas.simulation import PitInstruction, TyreCompound
from app.services.data_import_service import DataImportService


@pytest.fixture()
def season_db() -> Generator[Session, None, None]:
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


def season_request(db: Session, rounds: int = 3) -> SeasonCreateRequest:
    circuits = list(db.scalars(select(Circuit).order_by(Circuit.id)).all())[:rounds]
    return SeasonCreateRequest(
        season_name="2026 PitWall Championship",
        calendar=[
            SeasonCalendarRound(round_number=index, circuit_id=circuit.id)
            for index, circuit in enumerate(circuits, start=1)
        ],
        weather_seed=77,
        event_seed=9,
        safety_car_base_probability=0.2,
        drivers=[
            DriverConfig(
                driver_id="a",
                driver_name="Driver A",
                team_name="Red Racing",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=100,
                pace_factor=0.985,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=25, compound=TyreCompound.HARD)],
            ),
            DriverConfig(
                driver_id="b",
                driver_name="Driver B",
                team_name="Blue Motorsport",
                starting_compound=TyreCompound.SOFT,
                starting_fuel_kg=100,
                pace_factor=1.0,
                degradation_factor=1.03,
                strategy=[
                    PitInstruction(lap=18, compound=TyreCompound.MEDIUM),
                    PitInstruction(lap=36, compound=TyreCompound.HARD),
                ],
            ),
            DriverConfig(
                driver_id="c",
                driver_name="Driver C",
                team_name="Red Racing",
                starting_compound=TyreCompound.HARD,
                starting_fuel_kg=100,
                pace_factor=1.01,
                degradation_factor=0.96,
                strategy=[PitInstruction(lap=30, compound=TyreCompound.MEDIUM)],
            ),
        ],
    )
