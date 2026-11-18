"""Persistence and lookup service for normalized external F1 reference data."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.f1_reference import F1Circuit, F1CircuitEvent, F1Constructor, F1Driver, F1DriverConstructorSeason, F1HistoricalLapTime, F1HistoricalPitStop, F1HistoricalRaceResult, F1QualifyingResult, F1StartingGrid
from app.services.f1_ingestion import F1Dataset, F1IngestionEngine, F1DataClient, IngestionRequest


class F1ReferenceNotFoundError(LookupError):
    """A requested provider-backed reference record does not exist."""


class F1ReferenceImportService:
    """Persist only validated normalized driver and constructor records."""

    def import_reference_data(self, client: F1DataClient, db: Session, season: int | None = None) -> dict[str, int | list[str]]:
        datasets = [F1Dataset.DRIVERS, F1Dataset.CONSTRUCTORS]
        if season is not None:
            datasets.append(F1Dataset.RACE_RESULTS)
        result = F1IngestionEngine(client).ingest(IngestionRequest(tuple(datasets), season=season))
        counts: dict[str, int | list[str]] = {"drivers": 0, "constructors": 0, "associations": 0, "rejected": result.rejected, "errors": []}
        errors: list[str] = counts["errors"]  # type: ignore[assignment]
        try:
            for report in result.reports.values():
                errors.extend(report.errors)
            for record in result.reports[F1Dataset.DRIVERS].records:
                self._upsert_driver(record.source, record.data, db)
                counts["drivers"] = int(counts["drivers"]) + 1
            for record in result.reports[F1Dataset.CONSTRUCTORS].records:
                self._upsert_constructor(record.source, record.data, db)
                counts["constructors"] = int(counts["constructors"]) + 1
            db.flush()
            if season is not None:
                for record in result.reports[F1Dataset.RACE_RESULTS].records:
                    if self._upsert_association(record.source, record.data, db):
                        counts["associations"] = int(counts["associations"]) + 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        return counts

    def import_circuit_data(self, client: F1DataClient, db: Session, season: int | None = None) -> dict[str, int | list[str]]:
        datasets = [F1Dataset.CIRCUITS]
        if season is not None:
            datasets.append(F1Dataset.RACE_EVENTS)
        result = F1IngestionEngine(client).ingest(IngestionRequest(tuple(datasets), season=season))
        counts: dict[str, int | list[str]] = {"circuits": 0, "events": 0, "rejected": result.rejected, "errors": []}
        errors: list[str] = counts["errors"]  # type: ignore[assignment]
        try:
            for report in result.reports.values(): errors.extend(report.errors)
            for record in result.reports[F1Dataset.CIRCUITS].records:
                self._upsert_circuit(record.source, record.data, db); counts["circuits"] = int(counts["circuits"]) + 1
            db.flush()
            if season is not None:
                for record in result.reports[F1Dataset.RACE_EVENTS].records:
                    if self._upsert_circuit_event(record.source, record.data, db): counts["events"] = int(counts["events"]) + 1
            db.commit()
        except Exception:
            db.rollback(); raise
        return counts

    def import_historical_results(self, client: F1DataClient, db: Session, season: int, round_number: int | None = None) -> dict[str, int | list[str]]:
        datasets = (F1Dataset.DRIVERS, F1Dataset.CONSTRUCTORS, F1Dataset.CIRCUITS, F1Dataset.RACE_EVENTS, F1Dataset.RACE_RESULTS)
        result = F1IngestionEngine(client).ingest(IngestionRequest(datasets, season=season, round_number=round_number))
        counts: dict[str, int | list[str]] = {"results": 0, "skipped": 0, "rejected": result.rejected, "errors": []}
        errors: list[str] = counts["errors"]  # type: ignore[assignment]
        try:
            for report in result.reports.values(): errors.extend(report.errors)
            for record in result.reports[F1Dataset.DRIVERS].records: self._upsert_driver(record.source, record.data, db)
            for record in result.reports[F1Dataset.CONSTRUCTORS].records: self._upsert_constructor(record.source, record.data, db)
            for record in result.reports[F1Dataset.CIRCUITS].records: self._upsert_circuit(record.source, record.data, db)
            db.flush()
            for record in result.reports[F1Dataset.RACE_EVENTS].records: self._upsert_circuit_event(record.source, record.data, db)
            db.flush()
            for record in result.reports[F1Dataset.RACE_RESULTS].records:
                if self._insert_historical_result(record.source, record.data, db): counts["results"] = int(counts["results"]) + 1
                else: counts["skipped"] = int(counts["skipped"]) + 1
            db.commit()
        except Exception:
            db.rollback(); raise
        return counts

    def import_qualifying_and_grids(self, client: F1DataClient, db: Session, season: int, round_number: int | None = None) -> dict[str, int | list[str]]:
        datasets = (F1Dataset.DRIVERS, F1Dataset.CONSTRUCTORS, F1Dataset.CIRCUITS, F1Dataset.RACE_EVENTS, F1Dataset.QUALIFYING_RESULTS, F1Dataset.STARTING_GRIDS)
        result = F1IngestionEngine(client).ingest(IngestionRequest(datasets, season=season, round_number=round_number))
        counts: dict[str, int | list[str]] = {"qualifying": 0, "grids": 0, "skipped": 0, "rejected": result.rejected, "errors": []}; errors: list[str] = counts["errors"]  # type: ignore[assignment]
        try:
            for report in result.reports.values(): errors.extend(report.errors)
            for record in result.reports[F1Dataset.DRIVERS].records: self._upsert_driver(record.source, record.data, db)
            for record in result.reports[F1Dataset.CONSTRUCTORS].records: self._upsert_constructor(record.source, record.data, db)
            for record in result.reports[F1Dataset.CIRCUITS].records: self._upsert_circuit(record.source, record.data, db)
            db.flush()
            # Race-result metadata supplies event identity and official grid values.
            for record in result.reports[F1Dataset.STARTING_GRIDS].records: self._upsert_circuit_event(record.source, record.data, db)
            for record in result.reports[F1Dataset.QUALIFYING_RESULTS].records: self._upsert_circuit_event(record.source, record.data, db)
            db.flush()
            for record in result.reports[F1Dataset.QUALIFYING_RESULTS].records:
                counts["qualifying"] = int(counts["qualifying"]) + int(self._insert_qualifying(record.source, record.data, db))
            for record in result.reports[F1Dataset.STARTING_GRIDS].records:
                inserted = self._insert_grid(record.source, record.data, db); counts["grids"] = int(counts["grids"]) + int(inserted); counts["skipped"] = int(counts["skipped"]) + int(not inserted)
            db.commit()
        except Exception:
            db.rollback(); raise
        return counts

    def import_laps_and_pit_stops(self, client: F1DataClient, db: Session, season: int, round_number: int) -> dict[str, int | list[str]]:
        datasets = (F1Dataset.DRIVERS, F1Dataset.CIRCUITS, F1Dataset.RACE_RESULTS, F1Dataset.LAP_TIMES, F1Dataset.PIT_STOPS)
        result = F1IngestionEngine(client).ingest(IngestionRequest(datasets, season=season, round_number=round_number))
        counts: dict[str, int | list[str]] = {"laps": 0, "pit_stops": 0, "skipped": 0, "rejected": result.rejected, "errors": []}; errors: list[str] = counts["errors"]  # type: ignore[assignment]
        try:
            for report in result.reports.values(): errors.extend(report.errors)
            for record in result.reports[F1Dataset.DRIVERS].records: self._upsert_driver(record.source, record.data, db)
            for record in result.reports[F1Dataset.CIRCUITS].records: self._upsert_circuit(record.source, record.data, db)
            db.flush()
            for record in result.reports[F1Dataset.RACE_RESULTS].records: self._upsert_circuit_event(record.source, record.data, db)
            db.flush()
            for record in result.reports[F1Dataset.LAP_TIMES].records:
                inserted = self._insert_lap(record.source, record.data, db); counts["laps"] = int(counts["laps"]) + int(inserted); counts["skipped"] = int(counts["skipped"]) + int(not inserted)
            for record in result.reports[F1Dataset.PIT_STOPS].records:
                inserted = self._insert_pit_stop(record.source, record.data, db); counts["pit_stops"] = int(counts["pit_stops"]) + int(inserted); counts["skipped"] = int(counts["skipped"]) + int(not inserted)
            db.commit()
        except Exception:
            db.rollback(); raise
        return counts

    @staticmethod
    def _upsert_driver(source: str, data: object, db: Session) -> F1Driver:
        values = dict(data)  # normalized ingestion data
        driver = db.scalar(select(F1Driver).where(F1Driver.source == source, F1Driver.provider_driver_id == values["provider_driver_id"]))
        if driver is None:
            driver = F1Driver(source=source, provider_driver_id=str(values["provider_driver_id"]), given_name=str(values["given_name"]), family_name=str(values["family_name"]))
            db.add(driver)
        # Keep observed identities stable; later imports only complete missing details.
        if driver.code is None: driver.code = _string(values.get("code"))
        if driver.permanent_number is None: driver.permanent_number = _integer(values.get("number"))
        if driver.date_of_birth is None: driver.date_of_birth = _date(values.get("date_of_birth"))
        if driver.nationality is None: driver.nationality = _string(values.get("nationality"))
        if driver.source_url is None: driver.source_url = _string(values.get("url"))
        return driver

    @staticmethod
    def _upsert_constructor(source: str, data: object, db: Session) -> F1Constructor:
        values = dict(data)
        constructor = db.scalar(select(F1Constructor).where(F1Constructor.source == source, F1Constructor.provider_constructor_id == values["provider_constructor_id"]))
        if constructor is None:
            constructor = F1Constructor(source=source, provider_constructor_id=str(values["provider_constructor_id"]), name=str(values["name"]))
            db.add(constructor)
        if constructor.nationality is None: constructor.nationality = _string(values.get("nationality"))
        if constructor.source_url is None: constructor.source_url = _string(values.get("url"))
        return constructor

    @staticmethod
    def _upsert_association(source: str, data: object, db: Session) -> bool:
        values = dict(data)
        driver = db.scalar(select(F1Driver).where(F1Driver.source == source, F1Driver.provider_driver_id == values["driver_id"]))
        constructor = db.scalar(select(F1Constructor).where(F1Constructor.source == source, F1Constructor.provider_constructor_id == values["constructor_id"]))
        if driver is None or constructor is None:
            return False
        season, round_number = int(values["season"]), int(values["round"])
        association = db.scalar(select(F1DriverConstructorSeason).where(F1DriverConstructorSeason.source == source, F1DriverConstructorSeason.season == season, F1DriverConstructorSeason.driver_id == driver.id, F1DriverConstructorSeason.constructor_id == constructor.id))
        if association is None:
            db.add(F1DriverConstructorSeason(source=source, season=season, driver_id=driver.id, constructor_id=constructor.id, first_seen_round=round_number, last_seen_round=round_number))
            return True
        association.first_seen_round = min(association.first_seen_round, round_number)
        association.last_seen_round = max(association.last_seen_round, round_number)
        return False

    @staticmethod
    def _upsert_circuit(source: str, data: object, db: Session) -> F1Circuit:
        values = dict(data)
        circuit = db.scalar(select(F1Circuit).where(F1Circuit.source == source, F1Circuit.provider_circuit_id == values["provider_circuit_id"]))
        if circuit is None:
            circuit = F1Circuit(source=source, provider_circuit_id=str(values["provider_circuit_id"]), name=str(values["name"]), country=str(values["country"])); db.add(circuit)
        if circuit.city is None: circuit.city = _string(values.get("city"))
        if circuit.latitude is None: circuit.latitude = _coordinate(values.get("latitude"))
        if circuit.longitude is None: circuit.longitude = _coordinate(values.get("longitude"))
        if circuit.source_url is None: circuit.source_url = _string(values.get("url"))
        return circuit

    @staticmethod
    def _upsert_circuit_event(source: str, data: object, db: Session) -> bool:
        values = dict(data)
        circuit = db.scalar(select(F1Circuit).where(F1Circuit.source == source, F1Circuit.provider_circuit_id == values["provider_circuit_id"]))
        if circuit is None: return False
        season, round_number = int(values["season"]), int(values["round"])
        event = db.scalar(select(F1CircuitEvent).where(F1CircuitEvent.source == source, F1CircuitEvent.season == season, F1CircuitEvent.round_number == round_number))
        if event is not None: return False
        db.add(F1CircuitEvent(source=source, circuit_id=circuit.id, season=season, round_number=round_number, race_name=str(values["race_name"]), race_date=date.fromisoformat(str(values["race_date"]))))
        return True

    @staticmethod
    def _insert_historical_result(source: str, data: object, db: Session) -> bool:
        values = dict(data)
        driver = db.scalar(select(F1Driver).where(F1Driver.source == source, F1Driver.provider_driver_id == values["driver_id"]))
        constructor = db.scalar(select(F1Constructor).where(F1Constructor.source == source, F1Constructor.provider_constructor_id == values["constructor_id"]))
        circuit = db.scalar(select(F1Circuit).where(F1Circuit.source == source, F1Circuit.provider_circuit_id == values["provider_circuit_id"]))
        if driver is None or constructor is None or circuit is None: return False
        event = db.scalar(select(F1CircuitEvent).where(F1CircuitEvent.source == source, F1CircuitEvent.circuit_id == circuit.id, F1CircuitEvent.season == int(values["season"]), F1CircuitEvent.round_number == int(values["round"])))
        if event is None: return False
        existing = db.scalar(select(F1HistoricalRaceResult).where(F1HistoricalRaceResult.source == source, F1HistoricalRaceResult.event_id == event.id, F1HistoricalRaceResult.driver_id == driver.id))
        if existing is not None: return False
        db.add(F1HistoricalRaceResult(source=source, event_id=event.id, driver_id=driver.id, constructor_id=constructor.id, position=_integer(values.get("position")), position_text=_string(values.get("position_text")), grid_position=_integer(values.get("grid_position")), points=_float(values.get("points")), laps_completed=_integer(values.get("laps")), status=_string(values.get("status")), race_time_millis=_integer(values.get("race_time_millis")), race_time_text=_string(values.get("race_time_text")), fastest_lap_rank=_integer(values.get("fastest_lap_rank")), fastest_lap_number=_integer(values.get("fastest_lap_number")), fastest_lap_time_seconds=_float(values.get("fastest_lap_time_seconds")), fastest_lap_speed_kph=_float(values.get("fastest_lap_speed_kph"))))
        return True

    @staticmethod
    def _result_references(source: str, values: dict[object, object], db: Session) -> tuple[F1Driver, F1Constructor, F1CircuitEvent] | None:
        driver = db.scalar(select(F1Driver).where(F1Driver.source == source, F1Driver.provider_driver_id == values["driver_id"])); constructor = db.scalar(select(F1Constructor).where(F1Constructor.source == source, F1Constructor.provider_constructor_id == values["constructor_id"])); circuit = db.scalar(select(F1Circuit).where(F1Circuit.source == source, F1Circuit.provider_circuit_id == values["provider_circuit_id"]))
        if driver is None or constructor is None or circuit is None: return None
        event = db.scalar(select(F1CircuitEvent).where(F1CircuitEvent.source == source, F1CircuitEvent.circuit_id == circuit.id, F1CircuitEvent.season == int(values["season"]), F1CircuitEvent.round_number == int(values["round"])))
        return (driver, constructor, event) if event is not None else None

    @classmethod
    def _insert_qualifying(cls, source: str, data: object, db: Session) -> bool:
        values = dict(data); references = cls._result_references(source, values, db)
        if references is None: return False
        driver, constructor, event = references
        if db.scalar(select(F1QualifyingResult).where(F1QualifyingResult.source == source, F1QualifyingResult.event_id == event.id, F1QualifyingResult.driver_id == driver.id)): return False
        db.add(F1QualifyingResult(source=source, event_id=event.id, driver_id=driver.id, constructor_id=constructor.id, position=int(values["position"]), q1_seconds=_float(values.get("q1_seconds")), q2_seconds=_float(values.get("q2_seconds")), q3_seconds=_float(values.get("q3_seconds"))))
        return True

    @classmethod
    def _insert_grid(cls, source: str, data: object, db: Session) -> bool:
        values = dict(data); references = cls._result_references(source, values, db)
        if references is None: return False
        driver, constructor, event = references
        if db.scalar(select(F1StartingGrid).where(F1StartingGrid.source == source, F1StartingGrid.event_id == event.id, F1StartingGrid.driver_id == driver.id)): return False
        db.add(F1StartingGrid(source=source, event_id=event.id, driver_id=driver.id, constructor_id=constructor.id, grid_position=int(values["grid_position"])))
        return True

    @staticmethod
    def _lap_references(source: str, values: dict[object, object], db: Session) -> tuple[F1Driver, F1CircuitEvent] | None:
        driver = db.scalar(select(F1Driver).where(F1Driver.source == source, F1Driver.provider_driver_id == values["driver_id"])); circuit = db.scalar(select(F1Circuit).where(F1Circuit.source == source, F1Circuit.provider_circuit_id == values["provider_circuit_id"]))
        if driver is None or circuit is None: return None
        event = db.scalar(select(F1CircuitEvent).where(F1CircuitEvent.source == source, F1CircuitEvent.circuit_id == circuit.id, F1CircuitEvent.season == int(values["season"]), F1CircuitEvent.round_number == int(values["round"])))
        return (driver, event) if event is not None else None

    @classmethod
    def _insert_lap(cls, source: str, data: object, db: Session) -> bool:
        values = dict(data); references = cls._lap_references(source, values, db)
        if references is None: return False
        driver, event = references
        if db.scalar(select(F1HistoricalLapTime).where(F1HistoricalLapTime.source == source, F1HistoricalLapTime.event_id == event.id, F1HistoricalLapTime.driver_id == driver.id, F1HistoricalLapTime.lap_number == int(values["lap_number"]))): return False
        db.add(F1HistoricalLapTime(source=source, event_id=event.id, driver_id=driver.id, lap_number=int(values["lap_number"]), position=int(values["position"]), lap_time_seconds=float(values["lap_time_seconds"])))
        return True

    @classmethod
    def _insert_pit_stop(cls, source: str, data: object, db: Session) -> bool:
        values = dict(data); references = cls._lap_references(source, values, db)
        if references is None: return False
        driver, event = references
        if db.scalar(select(F1HistoricalPitStop).where(F1HistoricalPitStop.source == source, F1HistoricalPitStop.event_id == event.id, F1HistoricalPitStop.driver_id == driver.id, F1HistoricalPitStop.stop_number == int(values["stop_number"]))): return False
        db.add(F1HistoricalPitStop(source=source, event_id=event.id, driver_id=driver.id, stop_number=int(values["stop_number"]), lap_number=int(values["lap_number"]), time=str(values["time"]), duration_seconds=float(values["duration_seconds"])))
        return True


class F1ReferenceService:
    """Read-only query surface for real, persisted reference data."""

    def list_drivers(self, db: Session, search: str | None, limit: int, offset: int) -> list[F1Driver]:
        statement = select(F1Driver).order_by(F1Driver.family_name, F1Driver.given_name)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(or_(F1Driver.given_name.ilike(pattern), F1Driver.family_name.ilike(pattern), F1Driver.provider_driver_id.ilike(pattern)))
        return list(db.scalars(statement.offset(offset).limit(limit)))

    def get_driver(self, driver_id: int, db: Session) -> F1Driver:
        driver = db.get(F1Driver, driver_id)
        if driver is None:
            raise F1ReferenceNotFoundError("Driver not found")
        return driver

    def list_constructors(self, db: Session, search: str | None, limit: int, offset: int) -> list[F1Constructor]:
        statement = select(F1Constructor).order_by(F1Constructor.name)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(or_(F1Constructor.name.ilike(pattern), F1Constructor.provider_constructor_id.ilike(pattern)))
        return list(db.scalars(statement.offset(offset).limit(limit)))

    def get_constructor(self, constructor_id: int, db: Session) -> F1Constructor:
        constructor = db.get(F1Constructor, constructor_id)
        if constructor is None:
            raise F1ReferenceNotFoundError("Constructor not found")
        return constructor

    def associations(self, season: int, db: Session, limit: int, offset: int) -> list[F1DriverConstructorSeason]:
        return list(db.scalars(select(F1DriverConstructorSeason).options(joinedload(F1DriverConstructorSeason.driver), joinedload(F1DriverConstructorSeason.constructor)).where(F1DriverConstructorSeason.season == season).order_by(F1DriverConstructorSeason.driver_id).offset(offset).limit(limit)))

    def drivers_by_season(self, season: int, db: Session, limit: int, offset: int) -> list[F1Driver]:
        statement = select(F1Driver).join(F1DriverConstructorSeason).where(F1DriverConstructorSeason.season == season).order_by(F1Driver.family_name, F1Driver.given_name).distinct()
        return list(db.scalars(statement.offset(offset).limit(limit)))

    def constructors_by_season(self, season: int, db: Session, limit: int, offset: int) -> list[F1Constructor]:
        statement = select(F1Constructor).join(F1DriverConstructorSeason).where(F1DriverConstructorSeason.season == season).order_by(F1Constructor.name).distinct()
        return list(db.scalars(statement.offset(offset).limit(limit)))

    def list_circuits(self, db: Session, search: str | None, country: str | None, limit: int, offset: int) -> list[F1Circuit]:
        statement = select(F1Circuit).order_by(F1Circuit.name)
        if search: statement = statement.where(F1Circuit.name.ilike(f"%{search.strip()}%"))
        if country: statement = statement.where(F1Circuit.country.ilike(country.strip()))
        return list(db.scalars(statement.offset(offset).limit(limit)))

    def get_circuit(self, circuit_id: int, db: Session) -> F1Circuit:
        circuit = db.get(F1Circuit, circuit_id)
        if circuit is None: raise F1ReferenceNotFoundError("Circuit not found")
        return circuit

    def get_circuit_by_provider_id(self, provider_circuit_id: str, db: Session) -> F1Circuit:
        circuit = db.scalar(select(F1Circuit).where(F1Circuit.provider_circuit_id == provider_circuit_id))
        if circuit is None: raise F1ReferenceNotFoundError("Circuit not found")
        return circuit

    def circuit_events(self, circuit_id: int, db: Session, season: int | None, limit: int, offset: int) -> list[F1CircuitEvent]:
        self.get_circuit(circuit_id, db)
        statement = select(F1CircuitEvent).where(F1CircuitEvent.circuit_id == circuit_id).order_by(F1CircuitEvent.season.desc(), F1CircuitEvent.round_number)
        if season is not None: statement = statement.where(F1CircuitEvent.season == season)
        return list(db.scalars(statement.offset(offset).limit(limit)))

    def events_by_season(self, season: int, db: Session, limit: int, offset: int) -> list[F1CircuitEvent]:
        statement = select(F1CircuitEvent).options(joinedload(F1CircuitEvent.circuit)).where(F1CircuitEvent.season == season)
        return list(db.scalars(statement.order_by(F1CircuitEvent.round_number).offset(offset).limit(limit)))

    def get_event(self, event_id: int, db: Session) -> F1CircuitEvent:
        event = db.scalar(select(F1CircuitEvent).options(joinedload(F1CircuitEvent.circuit)).where(F1CircuitEvent.id == event_id))
        if event is None:
            raise F1ReferenceNotFoundError("Historical event not found")
        return event

    def result_seasons(self, db: Session) -> list[tuple[int, int, int]]:
        return list(db.execute(select(F1CircuitEvent.season, func.count(func.distinct(F1CircuitEvent.id)), func.count(F1HistoricalRaceResult.id)).join(F1HistoricalRaceResult).group_by(F1CircuitEvent.season).order_by(F1CircuitEvent.season.desc())).all())

    def result_events(self, season: int, db: Session) -> list[F1CircuitEvent]:
        return list(db.scalars(select(F1CircuitEvent).join(F1HistoricalRaceResult).where(F1CircuitEvent.season == season).distinct().order_by(F1CircuitEvent.round_number)))

    def results(self, db: Session, event_id: int | None, driver_id: int | None, constructor_id: int | None, circuit_id: int | None, search: str | None, limit: int, offset: int, season: int | None = None) -> list[F1HistoricalRaceResult]:
        statement = select(F1HistoricalRaceResult).options(joinedload(F1HistoricalRaceResult.event), joinedload(F1HistoricalRaceResult.driver), joinedload(F1HistoricalRaceResult.constructor)).join(F1CircuitEvent)
        if event_id is not None: statement = statement.where(F1HistoricalRaceResult.event_id == event_id)
        if driver_id is not None: statement = statement.where(F1HistoricalRaceResult.driver_id == driver_id)
        if constructor_id is not None: statement = statement.where(F1HistoricalRaceResult.constructor_id == constructor_id)
        if circuit_id is not None: statement = statement.where(F1CircuitEvent.circuit_id == circuit_id)
        if season is not None: statement = statement.where(F1CircuitEvent.season == season)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.join(F1Driver).where(or_(F1Driver.given_name.ilike(pattern), F1Driver.family_name.ilike(pattern), F1CircuitEvent.race_name.ilike(pattern)))
        return list(db.scalars(statement.order_by(F1CircuitEvent.season.desc(), F1CircuitEvent.round_number.desc(), F1HistoricalRaceResult.position).offset(offset).limit(limit)))

    def get_result(self, result_id: int, db: Session) -> F1HistoricalRaceResult:
        result = db.scalar(select(F1HistoricalRaceResult).options(joinedload(F1HistoricalRaceResult.event), joinedload(F1HistoricalRaceResult.driver), joinedload(F1HistoricalRaceResult.constructor)).where(F1HistoricalRaceResult.id == result_id))
        if result is None: raise F1ReferenceNotFoundError("Historical result not found")
        return result

    def result_analytics(self, season: int, db: Session, driver_id: int | None, constructor_id: int | None) -> dict[str, int | float | None]:
        statement = select(F1HistoricalRaceResult).join(F1CircuitEvent).where(F1CircuitEvent.season == season)
        if driver_id is not None: statement = statement.where(F1HistoricalRaceResult.driver_id == driver_id)
        if constructor_id is not None: statement = statement.where(F1HistoricalRaceResult.constructor_id == constructor_id)
        rows = list(db.scalars(statement))
        event_ids = {row.event_id for row in rows}
        return {"season": season, "races_used": len(event_ids), "driver_id": driver_id, "constructor_id": constructor_id, "wins": sum(row.position == 1 for row in rows), "podiums": sum(row.position is not None and row.position <= 3 for row in rows), "points": sum(row.points or 0 for row in rows), "classified_results": sum(row.position is not None for row in rows)}

    def qualifying(self, season: int, db: Session, event_id: int | None, driver_id: int | None, limit: int, offset: int) -> list[F1QualifyingResult]:
        statement = select(F1QualifyingResult).options(joinedload(F1QualifyingResult.event), joinedload(F1QualifyingResult.driver), joinedload(F1QualifyingResult.constructor)).join(F1CircuitEvent).where(F1CircuitEvent.season == season)
        if event_id: statement = statement.where(F1QualifyingResult.event_id == event_id)
        if driver_id: statement = statement.where(F1QualifyingResult.driver_id == driver_id)
        return list(db.scalars(statement.order_by(F1CircuitEvent.round_number, F1QualifyingResult.position).offset(offset).limit(limit)))

    def grids(self, event_id: int, db: Session) -> list[F1StartingGrid]:
        self.get_event(event_id, db)
        return list(db.scalars(select(F1StartingGrid).options(joinedload(F1StartingGrid.event), joinedload(F1StartingGrid.driver), joinedload(F1StartingGrid.constructor)).where(F1StartingGrid.event_id == event_id).order_by(F1StartingGrid.grid_position)))

    def qualifying_analytics(self, season: int, db: Session, driver_id: int | None, constructor_id: int | None) -> dict[str, int | float | None]:
        statement = select(F1QualifyingResult).join(F1CircuitEvent).where(F1CircuitEvent.season == season)
        if driver_id: statement = statement.where(F1QualifyingResult.driver_id == driver_id)
        if constructor_id: statement = statement.where(F1QualifyingResult.constructor_id == constructor_id)
        rows = list(db.scalars(statement)); grid_by_key = {(row.event_id, row.driver_id): row.grid_position for row in db.scalars(select(F1StartingGrid))}
        return {"season": season, "driver_id": driver_id, "constructor_id": constructor_id, "samples": len(rows), "average_position": (sum(row.position for row in rows) / len(rows)) if rows else None, "poles": sum(row.position == 1 for row in rows), "grid_changes": sum(grid_by_key.get((row.event_id, row.driver_id)) not in (None, row.position) for row in rows)}

    def lap_times(self, event_id: int, db: Session, driver_id: int | None, lap_from: int | None, lap_to: int | None, limit: int, offset: int) -> list[F1HistoricalLapTime]:
        self.get_event(event_id, db)
        statement = select(F1HistoricalLapTime).options(joinedload(F1HistoricalLapTime.event), joinedload(F1HistoricalLapTime.driver)).where(F1HistoricalLapTime.event_id == event_id)
        if driver_id: statement = statement.where(F1HistoricalLapTime.driver_id == driver_id)
        if lap_from is not None: statement = statement.where(F1HistoricalLapTime.lap_number >= lap_from)
        if lap_to is not None: statement = statement.where(F1HistoricalLapTime.lap_number <= lap_to)
        return list(db.scalars(statement.order_by(F1HistoricalLapTime.lap_number, F1HistoricalLapTime.driver_id).offset(offset).limit(limit)))

    def pit_stops(self, event_id: int, db: Session, driver_id: int | None, limit: int, offset: int) -> list[F1HistoricalPitStop]:
        self.get_event(event_id, db)
        statement = select(F1HistoricalPitStop).options(joinedload(F1HistoricalPitStop.event), joinedload(F1HistoricalPitStop.driver)).where(F1HistoricalPitStop.event_id == event_id)
        if driver_id: statement = statement.where(F1HistoricalPitStop.driver_id == driver_id)
        return list(db.scalars(statement.order_by(F1HistoricalPitStop.lap_number, F1HistoricalPitStop.stop_number).offset(offset).limit(limit)))

    def performance_analytics(self, event_id: int, db: Session, driver_id: int | None) -> dict[str, int | float | None]:
        self.get_event(event_id, db)
        laps = list(db.scalars(select(F1HistoricalLapTime).where(F1HistoricalLapTime.event_id == event_id, *((F1HistoricalLapTime.driver_id == driver_id,) if driver_id else ()))))
        pits = list(db.scalars(select(F1HistoricalPitStop).where(F1HistoricalPitStop.event_id == event_id, *((F1HistoricalPitStop.driver_id == driver_id,) if driver_id else ()))))
        timings = [lap.lap_time_seconds for lap in laps]
        durations = [pit.duration_seconds for pit in pits]
        return {"event_id": event_id, "driver_id": driver_id, "lap_samples": len(timings), "average_lap_time_seconds": sum(timings) / len(timings) if timings else None, "fastest_lap_seconds": min(timings) if timings else None, "slowest_lap_seconds": max(timings) if timings else None, "pit_stop_samples": len(durations), "average_pit_stop_duration_seconds": sum(durations) / len(durations) if durations else None}


def _string(value: object) -> str | None:
    return str(value) if value is not None else None


def _integer(value: object) -> int | None:
    return int(value) if value is not None else None


def _float(value: object) -> float | None:
    return float(value) if value is not None else None


def _date(value: object) -> date | None:
    return date.fromisoformat(str(value)) if value is not None else None


def _coordinate(value: object) -> float | None:
    if value is None: return None
    result = float(value)
    if not -180 <= result <= 180: raise ValueError("circuit coordinate is outside valid bounds")
    return result
