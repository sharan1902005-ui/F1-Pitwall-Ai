"""SQLAlchemy models for championship season state."""

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Season(Base):
    """Persistent championship season state."""

    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season_name: Mapped[str] = mapped_column(String(120), index=True)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer)
    weather_seed: Mapped[int] = mapped_column(Integer)
    event_seed: Mapped[int] = mapped_column(Integer)
    points_system_json: Mapped[str] = mapped_column(Text)
    config_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="CREATED")

    races: Mapped[list["SeasonRace"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
        order_by="SeasonRace.round_number",
    )
    driver_standings: Mapped[list["SeasonDriverStanding"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
    )
    constructor_standings: Mapped[list["SeasonConstructorStanding"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
    )


class SeasonRace(Base):
    """One calendar round and its stored result."""

    __tablename__ = "season_races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, index=True)
    circuit_id: Mapped[int] = mapped_column(Integer, index=True)
    circuit_name: Mapped[str] = mapped_column(String(100))
    total_laps: Mapped[int] = mapped_column(Integer)
    base_lap_time_seconds: Mapped[float] = mapped_column(Float)
    pit_lane_time_loss_seconds: Mapped[float] = mapped_column(Float)
    avg_track_temp: Mapped[float] = mapped_column(Float)
    avg_air_temp: Mapped[float] = mapped_column(Float)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    winner_driver_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    winner_driver_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    points_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    season: Mapped[Season] = relationship(back_populates="races")


class SeasonDriverStanding(Base):
    """Accumulated driver championship standing."""

    __tablename__ = "season_driver_standings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    driver_id: Mapped[str] = mapped_column(String(24), index=True)
    driver_name: Mapped[str] = mapped_column(String(80))
    team_name: Mapped[str] = mapped_column(String(80), index=True)
    points: Mapped[float] = mapped_column(Float, default=0.0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    podiums: Mapped[int] = mapped_column(Integer, default=0)
    races: Mapped[int] = mapped_column(Integer, default=0)
    best_finish: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish_sum: Mapped[int] = mapped_column(Integer, default=0)
    total_race_time: Mapped[float] = mapped_column(Float, default=0.0)
    points_history_json: Mapped[str] = mapped_column(Text, default="[]")
    positions_history_json: Mapped[str] = mapped_column(Text, default="[]")

    season: Mapped[Season] = relationship(back_populates="driver_standings")


class SeasonConstructorStanding(Base):
    """Accumulated constructor championship standing."""

    __tablename__ = "season_constructor_standings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    team_name: Mapped[str] = mapped_column(String(80), index=True)
    points: Mapped[float] = mapped_column(Float, default=0.0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    podiums: Mapped[int] = mapped_column(Integer, default=0)
    races: Mapped[int] = mapped_column(Integer, default=0)
    points_history_json: Mapped[str] = mapped_column(Text, default="[]")

    season: Mapped[Season] = relationship(back_populates="constructor_standings")
