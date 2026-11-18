"""Persistent, provider-sourced Formula 1 reference data."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class F1Driver(Base):
    """One real driver identity from an external provider."""

    __tablename__ = "f1_drivers"
    __table_args__ = (UniqueConstraint("source", "provider_driver_id", name="uq_f1_driver_source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    provider_driver_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    permanent_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    given_name: Mapped[str] = mapped_column(String(80))
    family_name: Mapped[str] = mapped_column(String(80), index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    constructor_associations: Mapped[list["F1DriverConstructorSeason"]] = relationship(back_populates="driver")


class F1Constructor(Base):
    """One real constructor identity from an external provider."""

    __tablename__ = "f1_constructors"
    __table_args__ = (UniqueConstraint("source", "provider_constructor_id", name="uq_f1_constructor_source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    provider_constructor_id: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    nationality: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    driver_associations: Mapped[list["F1DriverConstructorSeason"]] = relationship(back_populates="constructor")


class F1DriverConstructorSeason(Base):
    """A provider-observed driver/constructor association in one real season."""

    __tablename__ = "f1_driver_constructor_seasons"
    __table_args__ = (
        UniqueConstraint("source", "season", "driver_id", "constructor_id", name="uq_f1_season_driver_constructor"),
        Index("ix_f1_association_season_driver", "season", "driver_id"),
        Index("ix_f1_association_season_constructor", "season", "constructor_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("f1_drivers.id"), index=True)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("f1_constructors.id"), index=True)
    first_seen_round: Mapped[int] = mapped_column(Integer)
    last_seen_round: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    driver: Mapped[F1Driver] = relationship(back_populates="constructor_associations")
    constructor: Mapped[F1Constructor] = relationship(back_populates="driver_associations")


class F1Circuit(Base):
    """One real circuit identity from an external provider, not a simulation config."""

    __tablename__ = "f1_circuits"
    __table_args__ = (UniqueConstraint("source", "provider_circuit_id", name="uq_f1_circuit_source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    provider_circuit_id: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(120), index=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    events: Mapped[list["F1CircuitEvent"]] = relationship(back_populates="circuit", cascade="all, delete-orphan")


class F1CircuitEvent(Base):
    """A real provider-observed event at a circuit in a particular season and round."""

    __tablename__ = "f1_circuit_events"
    __table_args__ = (UniqueConstraint("source", "season", "round_number", name="uq_f1_circuit_event"), Index("ix_f1_circuit_event_circuit_season", "circuit_id", "season"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    circuit_id: Mapped[int] = mapped_column(ForeignKey("f1_circuits.id"), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    race_name: Mapped[str] = mapped_column(String(160), index=True)
    race_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    circuit: Mapped[F1Circuit] = relationship(back_populates="events")
    results: Mapped[list["F1HistoricalRaceResult"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    weather_observations: Mapped[list["F1HistoricalWeatherObservation"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class F1HistoricalRaceResult(Base):
    """One immutable provider-sourced classification entry for a real event."""

    __tablename__ = "f1_historical_race_results"
    __table_args__ = (UniqueConstraint("source", "event_id", "driver_id", name="uq_f1_result_event_driver"), Index("ix_f1_result_driver_event", "driver_id", "event_id"), Index("ix_f1_result_constructor_event", "constructor_id", "event_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("f1_circuit_events.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("f1_drivers.id"), index=True)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("f1_constructors.id"), index=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_text: Mapped[str | None] = mapped_column(String(30), nullable=True)
    grid_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[float | None] = mapped_column(nullable=True)
    laps_completed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    race_time_millis: Mapped[int | None] = mapped_column(Integer, nullable=True)
    race_time_text: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fastest_lap_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fastest_lap_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fastest_lap_time_seconds: Mapped[float | None] = mapped_column(nullable=True)
    fastest_lap_speed_kph: Mapped[float | None] = mapped_column(nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped[F1CircuitEvent] = relationship(back_populates="results")
    driver: Mapped[F1Driver] = relationship()
    constructor: Mapped[F1Constructor] = relationship()


class F1QualifyingResult(Base):
    """Provider-backed qualifying classification; session times are optional."""
    __tablename__ = "f1_qualifying_results"
    __table_args__ = (UniqueConstraint("source", "event_id", "driver_id", name="uq_f1_qualifying_event_driver"), Index("ix_f1_qualifying_driver_event", "driver_id", "event_id"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("f1_circuit_events.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("f1_drivers.id"), index=True)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("f1_constructors.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    q1_seconds: Mapped[float | None] = mapped_column(nullable=True)
    q2_seconds: Mapped[float | None] = mapped_column(nullable=True)
    q3_seconds: Mapped[float | None] = mapped_column(nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    event: Mapped[F1CircuitEvent] = relationship()
    driver: Mapped[F1Driver] = relationship()
    constructor: Mapped[F1Constructor] = relationship()


class F1StartingGrid(Base):
    """Official grid position reported in race-result data, distinct from qualifying."""
    __tablename__ = "f1_starting_grids"
    __table_args__ = (UniqueConstraint("source", "event_id", "driver_id", name="uq_f1_grid_event_driver"), Index("ix_f1_grid_driver_event", "driver_id", "event_id"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("f1_circuit_events.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("f1_drivers.id"), index=True)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("f1_constructors.id"), index=True)
    grid_position: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    event: Mapped[F1CircuitEvent] = relationship()
    driver: Mapped[F1Driver] = relationship()
    constructor: Mapped[F1Constructor] = relationship()


class F1HistoricalLapTime(Base):
    """One provider-observed driver lap; Jolpica does not provide sectors here."""
    __tablename__ = "f1_historical_lap_times"
    __table_args__ = (UniqueConstraint("source", "event_id", "driver_id", "lap_number", name="uq_f1_lap_event_driver_number"), Index("ix_f1_lap_event_driver_number", "event_id", "driver_id", "lap_number"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("f1_circuit_events.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("f1_drivers.id"), index=True)
    lap_number: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)
    lap_time_seconds: Mapped[float] = mapped_column()
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    event: Mapped[F1CircuitEvent] = relationship()
    driver: Mapped[F1Driver] = relationship()


class F1HistoricalPitStop(Base):
    """One provider-observed pit stop, distinct from simulated pit-lane loss."""
    __tablename__ = "f1_historical_pit_stops"
    __table_args__ = (UniqueConstraint("source", "event_id", "driver_id", "stop_number", name="uq_f1_pit_event_driver_stop"), Index("ix_f1_pit_event_driver", "event_id", "driver_id"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("f1_circuit_events.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("f1_drivers.id"), index=True)
    stop_number: Mapped[int] = mapped_column(Integer)
    lap_number: Mapped[int] = mapped_column(Integer)
    time: Mapped[str] = mapped_column(String(30))
    duration_seconds: Mapped[float] = mapped_column()
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    event: Mapped[F1CircuitEvent] = relationship()
    driver: Mapped[F1Driver] = relationship()


class F1HistoricalWeatherObservation(Base):
    """Immutable OpenF1 weather sample; never simulation-generated weather."""

    __tablename__ = "f1_historical_weather_observations"
    __table_args__ = (
        UniqueConstraint("source", "provider_session_key", "observed_at", name="uq_f1_weather_source_session_time"),
        Index("ix_f1_weather_event_session_time", "event_id", "provider_session_key", "observed_at"),
        Index("ix_f1_weather_session_time", "provider_session_key", "observed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("f1_circuit_events.id"), index=True)
    provider_meeting_key: Mapped[int] = mapped_column(Integer, index=True)
    provider_session_key: Mapped[int] = mapped_column(Integer, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    air_temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    track_temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_mbar: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped[F1CircuitEvent] = relationship(back_populates="weather_observations")
