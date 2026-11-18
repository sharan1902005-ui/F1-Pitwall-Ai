"""Persistence and lookup support for verified OpenF1 historical weather."""

from __future__ import annotations

from datetime import date, datetime
import re

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.integrations.f1.openf1_weather_client import OpenF1WeatherClient
from app.models.f1_reference import F1CircuitEvent, F1HistoricalWeatherObservation
from app.services.f1_ingestion import F1Dataset, F1IngestionEngine, IngestionRequest
from app.services.f1_reference_service import F1ReferenceNotFoundError


class F1WeatherImportService:
    """Import only session observations that safely associate to an imported event."""

    def import_event_weather(self, client: OpenF1WeatherClient, db: Session, event_id: int) -> dict[str, int | list[str]]:
        event = db.scalar(select(F1CircuitEvent).options(joinedload(F1CircuitEvent.circuit)).where(F1CircuitEvent.id == event_id))
        if event is None:
            raise F1ReferenceNotFoundError(f"F1 event {event_id} was not found")
        if event.season < 2023:
            return {"sessions": 0, "observations": 0, "skipped": 0, "rejected": 0, "errors": ["OpenF1 historical weather coverage starts in 2023."]}

        sessions = self._event_sessions(client.list_sessions(event.season), event.race_date, event.circuit.country)
        counts: dict[str, int | list[str]] = {"sessions": len(sessions), "observations": 0, "skipped": 0, "rejected": 0, "errors": []}
        errors: list[str] = counts["errors"]  # type: ignore[assignment]
        try:
            for session in sessions:
                session_key = int(session["session_key"])
                result = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.HISTORICAL_WEATHER,), session_key=session_key))
                report = result.reports[F1Dataset.HISTORICAL_WEATHER]
                counts["rejected"] = int(counts["rejected"]) + report.rejected
                errors.extend(report.errors)
                for record in report.records:
                    if self._insert_observation(event.id, record.source, record.data, db):
                        counts["observations"] = int(counts["observations"]) + 1
                    else:
                        counts["skipped"] = int(counts["skipped"]) + 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        return counts

    @staticmethod
    def _event_sessions(sessions: list[dict[str, object]], race_date: date, country: str) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        for session in sessions:
            try:
                session_date = datetime.fromisoformat(str(session["date_start"]).replace("Z", "+00:00")).date()
                session_country = str(session["country_name"])
                session_key = int(session["session_key"])
            except (KeyError, TypeError, ValueError):
                continue
            if session_key > 0 and _same_country(country, session_country) and 0 <= (race_date - session_date).days <= 5:
                candidates.append(session)
        return candidates

    @staticmethod
    def _insert_observation(event_id: int, source: str, data: object, db: Session) -> bool:
        if not isinstance(data, dict):
            return False
        session_key, observed_at = int(data["provider_session_key"]), datetime.fromisoformat(str(data["observed_at"]))
        exists = db.scalar(select(F1HistoricalWeatherObservation.id).where(
            F1HistoricalWeatherObservation.source == source,
            F1HistoricalWeatherObservation.provider_session_key == session_key,
            F1HistoricalWeatherObservation.observed_at == observed_at,
        ))
        if exists is not None:
            return False
        db.add(F1HistoricalWeatherObservation(
            source=source, event_id=event_id, provider_meeting_key=int(data["provider_meeting_key"]),
            provider_session_key=session_key, observed_at=observed_at,
            air_temperature_celsius=_float(data.get("air_temperature_celsius")),
            track_temperature_celsius=_float(data.get("track_temperature_celsius")),
            humidity_percent=_float(data.get("humidity_percent")), pressure_mbar=_float(data.get("pressure_mbar")),
            wind_speed_mps=_float(data.get("wind_speed_mps")), wind_direction_degrees=_float(data.get("wind_direction_degrees")),
            rainfall=data.get("rainfall") if isinstance(data.get("rainfall"), bool) else None,
        ))
        return True


class F1WeatherReferenceService:
    def observations(self, db: Session, event_id: int, session_key: int | None, observed_from: datetime | None, observed_to: datetime | None, limit: int, offset: int) -> list[F1HistoricalWeatherObservation]:
        statement = select(F1HistoricalWeatherObservation).options(joinedload(F1HistoricalWeatherObservation.event)).where(F1HistoricalWeatherObservation.event_id == event_id)
        if session_key is not None: statement = statement.where(F1HistoricalWeatherObservation.provider_session_key == session_key)
        if observed_from is not None: statement = statement.where(F1HistoricalWeatherObservation.observed_at >= observed_from)
        if observed_to is not None: statement = statement.where(F1HistoricalWeatherObservation.observed_at <= observed_to)
        return list(db.scalars(statement.order_by(F1HistoricalWeatherObservation.observed_at).offset(offset).limit(limit)))

    def summary(self, db: Session, event_id: int, session_key: int | None) -> dict[str, object]:
        filters = [F1HistoricalWeatherObservation.event_id == event_id]
        if session_key is not None:
            filters.append(F1HistoricalWeatherObservation.provider_session_key == session_key)
        row = db.execute(select(
            func.count(F1HistoricalWeatherObservation.id), func.min(F1HistoricalWeatherObservation.observed_at), func.max(F1HistoricalWeatherObservation.observed_at),
            func.avg(F1HistoricalWeatherObservation.air_temperature_celsius), func.avg(F1HistoricalWeatherObservation.track_temperature_celsius),
            func.coalesce(func.sum(case((F1HistoricalWeatherObservation.rainfall.is_(True), 1), else_=0)), 0),
        ).where(*filters)).one()
        return {"event_id": event_id, "provider_session_key": session_key, "observations": int(row[0]), "first_observed_at": row[1], "last_observed_at": row[2], "average_air_temperature_celsius": row[3], "average_track_temperature_celsius": row[4], "rainfall_observations": int(row[5])}


def _same_country(left: str, right: str) -> bool:
    return re.sub(r"[^a-z]", "", left.casefold()) == re.sub(r"[^a-z]", "", right.casefold())


def _float(value: object) -> float | None:
    return float(value) if value is not None else None
