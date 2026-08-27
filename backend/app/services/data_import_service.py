"""Development-friendly historical data import layer."""

from abc import ABC, abstractmethod
from datetime import date
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.historical import Circuit, HistoricalLap, HistoricalPitStop, HistoricalRace


class CircuitSeed(TypedDict):
    """Seed shape for development circuit defaults."""

    name: str
    country: str
    city: str
    total_laps: int
    base_lap_time_seconds: float
    pit_lane_time_loss_seconds: float
    avg_track_temp: float
    avg_air_temp: float
    track_length_km: float
    tyre_wear_factor: float
    overtaking_difficulty: float
    safety_car_factor: float


class RaceDataProvider(ABC):
    """Provider interface for future historical data sources."""

    @abstractmethod
    def get_circuits(self) -> list[CircuitSeed]:
        """Return circuit defaults."""

    @abstractmethod
    def get_races(self) -> list[dict[str, object]]:
        """Return historical race samples."""


class LocalSeedDataProvider(RaceDataProvider):
    """Static local seed data that needs no API key or network access."""

    def get_circuits(self) -> list[CircuitSeed]:
        """Return approximate development defaults for three circuits."""
        return [
            {
                "name": "Monza",
                "country": "Italy",
                "city": "Monza",
                "total_laps": 57,
                "base_lap_time_seconds": 85.0,
                "pit_lane_time_loss_seconds": 22.0,
                "avg_track_temp": 35.0,
                "avg_air_temp": 28.0,
                "track_length_km": 5.793,
                "tyre_wear_factor": 0.92,
                "overtaking_difficulty": 0.35,
                "safety_car_factor": 0.85,
            },
            {
                "name": "Silverstone",
                "country": "United Kingdom",
                "city": "Silverstone",
                "total_laps": 52,
                "base_lap_time_seconds": 91.5,
                "pit_lane_time_loss_seconds": 20.5,
                "avg_track_temp": 29.0,
                "avg_air_temp": 22.0,
                "track_length_km": 5.891,
                "tyre_wear_factor": 1.12,
                "overtaking_difficulty": 0.45,
                "safety_car_factor": 1.0,
            },
            {
                "name": "Monaco",
                "country": "Monaco",
                "city": "Monte Carlo",
                "total_laps": 78,
                "base_lap_time_seconds": 74.0,
                "pit_lane_time_loss_seconds": 19.0,
                "avg_track_temp": 31.0,
                "avg_air_temp": 25.0,
                "track_length_km": 3.337,
                "tyre_wear_factor": 0.82,
                "overtaking_difficulty": 0.95,
                "safety_car_factor": 1.35,
            },
        ]

    def get_races(self) -> list[dict[str, object]]:
        """Return small historical samples for API development."""
        return [
            {
                "circuit_name": "Monza",
                "season": 2025,
                "race_name": "Italian Grand Prix",
                "race_date": date(2025, 9, 7),
                "total_laps": 57,
                "weather_summary": "Dry development seed sample",
                "safety_car_count": 0,
                "vsc_count": 1,
                "laps": [
                    ("VER", 1, 88.4, "MEDIUM", 1, 1),
                    ("VER", 2, 87.9, "MEDIUM", 2, 1),
                    ("VER", 26, 86.8, "HARD", 1, 1),
                    ("NOR", 1, 88.9, "MEDIUM", 1, 2),
                ],
                "pit_stops": [("VER", 26, 22.4, "HARD"), ("NOR", 25, 22.7, "HARD")],
            },
            {
                "circuit_name": "Silverstone",
                "season": 2025,
                "race_name": "British Grand Prix",
                "race_date": date(2025, 7, 6),
                "total_laps": 52,
                "weather_summary": "Mixed conditions development seed sample",
                "safety_car_count": 1,
                "vsc_count": 0,
                "laps": [
                    ("HAM", 1, 95.1, "INTERMEDIATE", 1, 3),
                    ("HAM", 18, 93.2, "MEDIUM", 1, 2),
                    ("LEC", 1, 95.8, "INTERMEDIATE", 1, 4),
                ],
                "pit_stops": [("HAM", 18, 20.9, "MEDIUM")],
            },
        ]


class DataImportService:
    """Seed local development data through a provider abstraction."""

    def __init__(self, provider: RaceDataProvider | None = None) -> None:
        self.provider = provider or LocalSeedDataProvider()

    def seed_defaults(self, db: Session) -> None:
        """Create or update default circuits and lightweight race samples."""
        circuits_by_name: dict[str, Circuit] = {}
        for seed in self.provider.get_circuits():
            circuit = db.scalar(select(Circuit).where(Circuit.name == seed["name"]))
            if circuit is None:
                circuit = Circuit(**seed)
                db.add(circuit)
            else:
                for key, value in seed.items():
                    setattr(circuit, key, value)
            circuits_by_name[seed["name"]] = circuit
        db.flush()

        for race_seed in self.provider.get_races():
            race = db.scalar(
                select(HistoricalRace).where(
                    HistoricalRace.season == race_seed["season"],
                    HistoricalRace.race_name == race_seed["race_name"],
                )
            )
            circuit = circuits_by_name[str(race_seed["circuit_name"])]
            if race is None:
                race = HistoricalRace(
                    season=int(race_seed["season"]),
                    race_name=str(race_seed["race_name"]),
                    circuit_id=circuit.id,
                    race_date=race_seed["race_date"],
                    total_laps=int(race_seed["total_laps"]),
                    weather_summary=str(race_seed["weather_summary"]),
                    safety_car_count=int(race_seed["safety_car_count"]),
                    vsc_count=int(race_seed["vsc_count"]),
                )
                db.add(race)
                db.flush()
                self._seed_laps_and_pits(db, race.id, race_seed)
        db.commit()

    @staticmethod
    def _seed_laps_and_pits(
        db: Session,
        race_id: int,
        race_seed: dict[str, object],
    ) -> None:
        """Insert lightweight lap and pit-stop samples for a race."""
        for driver_code, lap_number, lap_time, compound, tyre_age, position in race_seed["laps"]:
            db.add(
                HistoricalLap(
                    race_id=race_id,
                    driver_code=driver_code,
                    lap_number=lap_number,
                    lap_time_seconds=lap_time,
                    compound=compound,
                    tyre_age=tyre_age,
                    position=position,
                )
            )
        for driver_code, lap_number, duration, new_compound in race_seed["pit_stops"]:
            db.add(
                HistoricalPitStop(
                    race_id=race_id,
                    driver_code=driver_code,
                    lap_number=lap_number,
                    duration_seconds=duration,
                    new_compound=new_compound,
                )
            )
