"""SQLAlchemy models for historical data and circuit metadata."""

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Circuit(Base):
    """Stored circuit metadata and simulation defaults."""

    __tablename__ = "circuits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(80))
    total_laps: Mapped[int] = mapped_column(Integer)
    base_lap_time_seconds: Mapped[float] = mapped_column(Float)
    pit_lane_time_loss_seconds: Mapped[float] = mapped_column(Float)
    avg_track_temp: Mapped[float] = mapped_column(Float)
    avg_air_temp: Mapped[float] = mapped_column(Float)
    track_length_km: Mapped[float] = mapped_column(Float)
    tyre_wear_factor: Mapped[float] = mapped_column(Float, default=1.0)
    overtaking_difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    safety_car_factor: Mapped[float] = mapped_column(Float, default=1.0)

    races: Mapped[list["HistoricalRace"]] = relationship(
        back_populates="circuit",
        cascade="all, delete-orphan",
    )


class HistoricalRace(Base):
    """Lightweight historical race record."""

    __tablename__ = "historical_races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    race_name: Mapped[str] = mapped_column(String(120), index=True)
    circuit_id: Mapped[int] = mapped_column(ForeignKey("circuits.id"), index=True)
    race_date: Mapped[date] = mapped_column(Date)
    total_laps: Mapped[int] = mapped_column(Integer)
    weather_summary: Mapped[str] = mapped_column(Text)
    safety_car_count: Mapped[int] = mapped_column(Integer, default=0)
    vsc_count: Mapped[int] = mapped_column(Integer, default=0)

    circuit: Mapped[Circuit] = relationship(back_populates="races")
    laps: Mapped[list["HistoricalLap"]] = relationship(
        back_populates="race",
        cascade="all, delete-orphan",
    )
    pit_stops: Mapped[list["HistoricalPitStop"]] = relationship(
        back_populates="race",
        cascade="all, delete-orphan",
    )


class HistoricalLap(Base):
    """Historical lap-time sample."""

    __tablename__ = "historical_laps"
    __table_args__ = (
        Index("ix_historical_laps_race_driver_lap", "race_id", "driver_code", "lap_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("historical_races.id"), index=True)
    driver_code: Mapped[str] = mapped_column(String(5), index=True)
    lap_number: Mapped[int] = mapped_column(Integer)
    lap_time_seconds: Mapped[float] = mapped_column(Float)
    compound: Mapped[str] = mapped_column(String(20))
    tyre_age: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)

    race: Mapped[HistoricalRace] = relationship(back_populates="laps")


class HistoricalPitStop(Base):
    """Historical pit-stop sample."""

    __tablename__ = "historical_pit_stops"
    __table_args__ = (
        Index("ix_historical_pit_stops_race_driver_lap", "race_id", "driver_code", "lap_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("historical_races.id"), index=True)
    driver_code: Mapped[str] = mapped_column(String(5), index=True)
    lap_number: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float] = mapped_column(Float)
    new_compound: Mapped[str] = mapped_column(String(20))

    race: Mapped[HistoricalRace] = relationship(back_populates="pit_stops")
