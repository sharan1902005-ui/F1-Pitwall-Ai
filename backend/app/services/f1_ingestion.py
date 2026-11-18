"""Provider-agnostic preparation of external F1 data for later persistence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any, Protocol

from app.integrations.f1.errors import F1ProviderError

JsonObject = dict[str, Any]


class F1Dataset(StrEnum):
    SEASONS = "seasons"
    RACE_EVENTS = "race_events"
    DRIVERS = "drivers"
    CONSTRUCTORS = "constructors"
    CIRCUITS = "circuits"
    RACE_RESULTS = "race_results"
    QUALIFYING_RESULTS = "qualifying_results"
    STARTING_GRIDS = "starting_grids"
    LAP_TIMES = "lap_times"
    PIT_STOPS = "pit_stops"
    HISTORICAL_WEATHER = "historical_weather"


class F1DataClient(Protocol):
    """Subset of the Phase 11.2 client required for ingestion preparation."""

    provider_name: str

    def list_seasons(self) -> list[JsonObject]: ...
    def list_circuits(self) -> list[JsonObject]: ...
    def list_drivers(self) -> list[JsonObject]: ...
    def list_constructors(self) -> list[JsonObject]: ...
    def list_race_results(self, season: int, round_number: int | None = None) -> list[JsonObject]: ...
    def list_qualifying_results(self, season: int, round_number: int | None = None) -> list[JsonObject]: ...
    def list_laps(self, season: int, round_number: int) -> list[JsonObject]: ...
    def list_pit_stops(self, season: int, round_number: int) -> list[JsonObject]: ...


class F1WeatherDataClient(Protocol):
    """The documented capability required from a weather-specific provider."""

    provider_name: str

    def list_weather(self, session_key: int) -> list[JsonObject]: ...


class IngestionValidationError(ValueError):
    """A provider record cannot be safely normalized."""


class UnsupportedDatasetError(ValueError):
    """A caller selected an unknown dataset name."""


@dataclass(frozen=True)
class IngestionRequest:
    """Explicit scope for a non-persistent ingestion operation."""

    datasets: tuple[F1Dataset | str, ...]
    season: int | None = None
    round_number: int | None = None
    session_key: int | None = None

    def __post_init__(self) -> None:
        if self.season is not None and self.season < 1950:
            raise ValueError("season must be 1950 or later")
        if self.round_number is not None and self.round_number <= 0:
            raise ValueError("round_number must be positive")
        if self.round_number is not None and self.season is None:
            raise ValueError("round_number requires a season")
        if self.session_key is not None and self.session_key <= 0:
            raise ValueError("session_key must be positive")
        if not self.datasets:
            raise ValueError("at least one dataset must be selected")

    def selected_datasets(self) -> tuple[F1Dataset, ...]:
        selected: list[F1Dataset] = []
        for dataset in self.datasets:
            try:
                normalized = F1Dataset(dataset)
            except ValueError as exc:
                raise UnsupportedDatasetError(f"Unknown F1 dataset: {dataset}") from exc
            if normalized not in selected:
                selected.append(normalized)
        return tuple(selected)


@dataclass(frozen=True)
class NormalizedRecord:
    """A validated provider record ready for a future persistence mapper."""

    dataset: F1Dataset
    source: str
    provider_identifier: str
    data: Mapping[str, object]
    raw: Mapping[str, object]


@dataclass(frozen=True)
class RejectedRecord:
    dataset: F1Dataset
    reason: str
    raw: Mapping[str, object]


@dataclass
class DatasetIngestionReport:
    dataset: F1Dataset
    retrieved: int = 0
    imported: int = 0
    skipped: int = 0
    rejected: int = 0
    records: list[NormalizedRecord] = field(default_factory=list)
    rejected_records: list[RejectedRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unsupported_reason: str | None = None

    @property
    def empty(self) -> bool:
        return self.retrieved == 0 and not self.errors and self.unsupported_reason is None


@dataclass(frozen=True)
class IngestionResult:
    provider: str
    request: IngestionRequest
    reports: Mapping[F1Dataset, DatasetIngestionReport]

    @property
    def imported(self) -> int:
        return sum(report.imported for report in self.reports.values())

    @property
    def skipped(self) -> int:
        return sum(report.skipped for report in self.reports.values())

    @property
    def rejected(self) -> int:
        return sum(report.rejected for report in self.reports.values())


class F1IngestionEngine:
    """Retrieve, normalize, and report external F1 data without persistence."""

    def __init__(self, client: F1DataClient | F1WeatherDataClient) -> None:
        self.client = client

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        selected = request.selected_datasets()
        reports = {dataset: DatasetIngestionReport(dataset) for dataset in selected}
        retrieved: dict[str, list[JsonObject] | Exception] = {}
        for dataset in selected:
            report = reports[dataset]
            if dataset == F1Dataset.HISTORICAL_WEATHER and not hasattr(self.client, "list_weather"):
                report.unsupported_reason = f"{self.client.provider_name} does not provide historical weather or track-condition records."
                continue
            source_records = self._retrieve(self._source_for(dataset), request, retrieved)
            if isinstance(source_records, Exception):
                report.errors.append(str(source_records))
                continue
            self._normalize_dataset(dataset, source_records, report)
        return IngestionResult(self.client.provider_name, request, reports)

    def _retrieve(self, source: str, request: IngestionRequest, cache: dict[str, list[JsonObject] | Exception]) -> list[JsonObject] | Exception:
        if source in cache:
            return cache[source]
        try:
            if source == "seasons":
                records = self.client.list_seasons()
            elif source == "circuits":
                records = self.client.list_circuits()
            elif source == "drivers":
                records = self.client.list_drivers()
            elif source == "constructors":
                records = self.client.list_constructors()
            elif source == "race_results":
                records = self.client.list_race_results(self._season(request), request.round_number)
            elif source == "qualifying_results":
                records = self.client.list_qualifying_results(self._season(request), request.round_number)
            elif source == "lap_times":
                records = self.client.list_laps(self._season(request), self._round(request))
            elif source == "pit_stops":
                records = self.client.list_pit_stops(self._season(request), self._round(request))
            elif source == "historical_weather":
                weather_client = self.client
                if not hasattr(weather_client, "list_weather"):
                    raise ValueError("provider does not support historical weather")
                records = weather_client.list_weather(self._session_key(request))
            else:
                raise AssertionError(f"Unexpected source: {source}")
        except (F1ProviderError, ValueError) as exc:
            cache[source] = exc
        else:
            cache[source] = records
        return cache[source]

    @staticmethod
    def _season(request: IngestionRequest) -> int:
        if request.season is None:
            raise ValueError("season is required for this dataset")
        return request.season

    @staticmethod
    def _round(request: IngestionRequest) -> int:
        if request.round_number is None:
            raise ValueError("round_number is required for this dataset")
        return request.round_number

    @staticmethod
    def _session_key(request: IngestionRequest) -> int:
        if request.session_key is None:
            raise ValueError("session_key is required for historical_weather")
        return request.session_key

    @staticmethod
    def _source_for(dataset: F1Dataset) -> str:
        return {
            F1Dataset.SEASONS: "seasons", F1Dataset.CIRCUITS: "circuits", F1Dataset.DRIVERS: "drivers",
            F1Dataset.CONSTRUCTORS: "constructors", F1Dataset.RACE_EVENTS: "race_results",
            F1Dataset.RACE_RESULTS: "race_results", F1Dataset.STARTING_GRIDS: "race_results",
            F1Dataset.QUALIFYING_RESULTS: "qualifying_results", F1Dataset.LAP_TIMES: "lap_times",
            F1Dataset.PIT_STOPS: "pit_stops",
            F1Dataset.HISTORICAL_WEATHER: "historical_weather",
        }[dataset]

    def _normalize_dataset(self, dataset: F1Dataset, records: Sequence[JsonObject], report: DatasetIngestionReport) -> None:
        normalizers = {
            F1Dataset.SEASONS: self._season_record, F1Dataset.CIRCUITS: self._circuit_record,
            F1Dataset.DRIVERS: self._driver_record, F1Dataset.CONSTRUCTORS: self._constructor_record,
            F1Dataset.RACE_EVENTS: self._race_event_records, F1Dataset.RACE_RESULTS: self._result_records,
            F1Dataset.STARTING_GRIDS: self._grid_records, F1Dataset.QUALIFYING_RESULTS: self._qualifying_records,
            F1Dataset.LAP_TIMES: self._lap_records, F1Dataset.PIT_STOPS: self._pit_stop_records,
            F1Dataset.HISTORICAL_WEATHER: self._weather_record,
        }
        seen: set[str] = set()
        for raw in records:
            try:
                normalized = normalizers[dataset](raw)
            except IngestionValidationError as exc:
                report.rejected += 1
                report.rejected_records.append(RejectedRecord(dataset, str(exc), raw))
                continue
            for record in normalized if isinstance(normalized, list) else [normalized]:
                report.retrieved += 1
                if record.provider_identifier in seen:
                    report.skipped += 1
                else:
                    seen.add(record.provider_identifier)
                    report.records.append(record)
                    report.imported += 1

    def _record(self, dataset: F1Dataset, identifier: str, data: Mapping[str, object], raw: Mapping[str, object]) -> NormalizedRecord:
        return NormalizedRecord(dataset, self.client.provider_name, identifier, data, raw)

    def _season_record(self, raw: JsonObject) -> NormalizedRecord:
        season = _positive_int(raw, "season")
        return self._record(F1Dataset.SEASONS, str(season), {"season": season}, raw)

    def _circuit_record(self, raw: JsonObject) -> NormalizedRecord:
        location, identifier = _mapping(raw, "Location"), _text(raw, "circuitId")
        latitude, longitude = _optional_float(location, "lat"), _optional_float(location, "long")
        if latitude is not None and not -90 <= latitude <= 90: raise IngestionValidationError("latitude is outside valid bounds")
        if longitude is not None and not -180 <= longitude <= 180: raise IngestionValidationError("longitude is outside valid bounds")
        return self._record(F1Dataset.CIRCUITS, identifier, {"provider_circuit_id": identifier, "name": _text(raw, "circuitName"), "url": _optional_text(raw, "url"), "latitude": latitude, "longitude": longitude, "city": _optional_text(location, "locality"), "country": _text(location, "country")}, raw)

    def _driver_record(self, raw: JsonObject) -> NormalizedRecord:
        identifier = _text(raw, "driverId")
        return self._record(F1Dataset.DRIVERS, identifier, {"provider_driver_id": identifier, "code": _optional_text(raw, "code"), "number": _optional_int(raw, "permanentNumber"), "given_name": _text(raw, "givenName"), "family_name": _text(raw, "familyName"), "date_of_birth": _optional_date(raw, "dateOfBirth"), "nationality": _optional_text(raw, "nationality"), "url": _optional_text(raw, "url")}, raw)

    def _constructor_record(self, raw: JsonObject) -> NormalizedRecord:
        identifier = _text(raw, "constructorId")
        return self._record(F1Dataset.CONSTRUCTORS, identifier, {"provider_constructor_id": identifier, "name": _text(raw, "name"), "nationality": _optional_text(raw, "nationality"), "url": _optional_text(raw, "url")}, raw)

    def _race_event_records(self, raw: JsonObject) -> NormalizedRecord:
        event = _race_data(raw)
        return self._record(F1Dataset.RACE_EVENTS, f"{event['season']}:{event['round']}", event, raw)

    def _result_records(self, raw: JsonObject) -> list[NormalizedRecord]:
        event = _race_data(raw)
        return [self._record(F1Dataset.RACE_RESULTS, f"{event['season']}:{event['round']}:{_text(item, 'Driver', 'driverId')}", {**event, "driver_id": _text(item, "Driver", "driverId"), "constructor_id": _text(item, "Constructor", "constructorId"), "position": _optional_int(item, "position"), "position_text": _optional_text(item, "positionText"), "points": _optional_float(item, "points"), "grid_position": _non_negative_int(item, "grid"), "laps": _optional_int(item, "laps"), "status": _optional_text(item, "status"), **_result_timing(item)}, item) for item in _list(raw, "Results")]

    def _grid_records(self, raw: JsonObject) -> list[NormalizedRecord]:
        event = _race_data(raw)
        return [self._record(F1Dataset.STARTING_GRIDS, f"{event['season']}:{event['round']}:{_text(item, 'Driver', 'driverId')}", {**event, "driver_id": _text(item, "Driver", "driverId"), "constructor_id": _text(item, "Constructor", "constructorId"), "grid_position": _non_negative_int(item, "grid")}, item) for item in _list(raw, "Results")]

    def _qualifying_records(self, raw: JsonObject) -> list[NormalizedRecord]:
        event = _race_data(raw)
        return [self._record(F1Dataset.QUALIFYING_RESULTS, f"{event['season']}:{event['round']}:{_text(item, 'Driver', 'driverId')}", {**event, "driver_id": _text(item, "Driver", "driverId"), "constructor_id": _text(item, "Constructor", "constructorId"), "position": _positive_int(item, "position"), "q1_seconds": _optional_duration(item, "Q1"), "q2_seconds": _optional_duration(item, "Q2"), "q3_seconds": _optional_duration(item, "Q3")}, item) for item in _list(raw, "QualifyingResults")]

    def _lap_records(self, raw: JsonObject) -> list[NormalizedRecord]:
        event, records = _race_data(raw), []
        for lap in _list(raw, "Laps"):
            number = _positive_int(lap, "number")
            for timing in _list(lap, "Timings"):
                driver_id = _text(timing, "driverId")
                records.append(self._record(F1Dataset.LAP_TIMES, f"{event['season']}:{event['round']}:{driver_id}:{number}", {**event, "driver_id": driver_id, "lap_number": number, "position": _positive_int(timing, "position"), "lap_time_seconds": _duration(_text(timing, "time"))}, timing))
        return records

    def _pit_stop_records(self, raw: JsonObject) -> list[NormalizedRecord]:
        event = _race_data(raw)
        return [self._record(F1Dataset.PIT_STOPS, f"{event['season']}:{event['round']}:{_text(item, 'driverId')}:{_positive_int(item, 'stop')}", {**event, "driver_id": _text(item, "driverId"), "stop_number": _positive_int(item, "stop"), "lap_number": _positive_int(item, "lap"), "time": _time(_text(item, "time")), "duration_seconds": _positive_float(item, "duration")}, item) for item in _list(raw, "PitStops")]

    def _weather_record(self, raw: JsonObject) -> NormalizedRecord:
        observed_at = _utc_timestamp(_text(raw, "date"))
        meeting_key = _positive_int(raw, "meeting_key")
        session_key = _positive_int(raw, "session_key")
        return self._record(
            F1Dataset.HISTORICAL_WEATHER,
            f"{session_key}:{observed_at}",
            {
                "provider_meeting_key": meeting_key,
                "provider_session_key": session_key,
                "observed_at": observed_at,
                "air_temperature_celsius": _optional_float(raw, "air_temperature"),
                "track_temperature_celsius": _optional_float(raw, "track_temperature"),
                "humidity_percent": _bounded_optional_float(raw, "humidity", 0, 100),
                "pressure_mbar": _optional_float(raw, "pressure"),
                "wind_speed_mps": _optional_float(raw, "wind_speed"),
                "wind_direction_degrees": _bounded_optional_float(raw, "wind_direction", 0, 359),
                "rainfall": _optional_rainfall(raw),
            },
            raw,
        )


def _race_data(raw: JsonObject) -> dict[str, object]:
    circuit, race_date = _mapping(raw, "Circuit"), _date(_text(raw, "date"))
    location, start_time = _mapping(circuit, "Location"), _optional_text(raw, "time")
    return {"season": _positive_int(raw, "season"), "round": _positive_int(raw, "round"), "race_name": _text(raw, "raceName"), "race_date": race_date.isoformat(), "start_at": _timestamp(race_date, start_time), "provider_circuit_id": _text(circuit, "circuitId"), "circuit_name": _text(circuit, "circuitName"), "country": _text(location, "country")}


def _mapping(record: Mapping[str, object], *path: str) -> Mapping[str, object]:
    current: object = record
    for key in path:
        if not isinstance(current, Mapping) or not isinstance(current.get(key), Mapping):
            raise IngestionValidationError(f"missing required object: {'.'.join(path)}")
        current = current[key]
    return current


def _list(record: Mapping[str, object], key: str) -> list[JsonObject]:
    value = record.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise IngestionValidationError(f"missing required list: {key}")
    return value


def _text(record: Mapping[str, object], *path: str) -> str:
    current: object = record
    for key in path:
        if not isinstance(current, Mapping):
            raise IngestionValidationError(f"missing required field: {'.'.join(path)}")
        current = current.get(key)
    if not isinstance(current, str) or not current.strip():
        raise IngestionValidationError(f"missing required field: {'.'.join(path)}")
    return current.strip()


def _optional_text(record: Mapping[str, object], key: str) -> str | None:
    value = record.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _integer(record: Mapping[str, object], key: str) -> int:
    try:
        return int(str(record.get(key)))
    except (TypeError, ValueError) as exc:
        raise IngestionValidationError(f"invalid integer field: {key}") from exc


def _positive_int(record: Mapping[str, object], key: str) -> int:
    value = _integer(record, key)
    if value <= 0:
        raise IngestionValidationError(f"{key} must be positive")
    return value


def _non_negative_int(record: Mapping[str, object], key: str) -> int:
    value = _integer(record, key)
    if value < 0:
        raise IngestionValidationError(f"{key} cannot be negative")
    return value


def _optional_int(record: Mapping[str, object], key: str) -> int | None:
    return None if record.get(key) in (None, "") else _integer(record, key)


def _positive_float(record: Mapping[str, object], key: str) -> float:
    value = _optional_float(record, key)
    if value is None or value <= 0:
        raise IngestionValidationError(f"{key} must be a positive number")
    return value


def _optional_float(record: Mapping[str, object], key: str) -> float | None:
    value = record.get(key)
    if value in (None, ""):
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError) as exc:
        raise IngestionValidationError(f"invalid numeric field: {key}") from exc


def _bounded_optional_float(record: Mapping[str, object], key: str, minimum: float, maximum: float) -> float | None:
    value = _optional_float(record, key)
    if value is not None and not minimum <= value <= maximum:
        raise IngestionValidationError(f"{key} is outside valid bounds")
    return value


def _optional_rainfall(record: Mapping[str, object]) -> bool | None:
    value = record.get("rainfall")
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    raise IngestionValidationError("rainfall must be boolean or 0/1")


def _utc_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IngestionValidationError("invalid ISO observation timestamp") from exc
    if parsed.tzinfo is None:
        raise IngestionValidationError("observation timestamp must include a UTC offset")
    return parsed.isoformat()


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise IngestionValidationError("invalid ISO date") from exc


def _optional_date(record: Mapping[str, object], key: str) -> str | None:
    value = _optional_text(record, key)
    return _date(value).isoformat() if value is not None else None


def _time(value: str) -> str:
    try:
        return time.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError as exc:
        raise IngestionValidationError("invalid ISO time") from exc


def _timestamp(race_date: date, value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(f"{race_date.isoformat()}T{value.replace('Z', '+00:00')}").isoformat()
    except ValueError as exc:
        raise IngestionValidationError("invalid race start timestamp") from exc


def _duration(value: str) -> float:
    try:
        parts = [float(part) for part in value.split(":")]
    except ValueError as exc:
        raise IngestionValidationError("invalid timing value") from exc
    if not 1 <= len(parts) <= 3 or any(part < 0 for part in parts):
        raise IngestionValidationError("invalid timing value")
    seconds = parts[-1] + (parts[-2] * 60 if len(parts) >= 2 else 0) + (parts[0] * 3600 if len(parts) == 3 else 0)
    return seconds


def _optional_duration(record: Mapping[str, object], key: str) -> float | None:
    value = _optional_text(record, key)
    return _duration(value) if value is not None else None


def _result_timing(record: Mapping[str, object]) -> dict[str, object]:
    race_time = record.get("Time")
    fastest_lap = record.get("FastestLap")
    timing: dict[str, object] = {"race_time_millis": None, "race_time_text": None, "fastest_lap_rank": None, "fastest_lap_number": None, "fastest_lap_time_seconds": None, "fastest_lap_speed_kph": None}
    if race_time is not None:
        if not isinstance(race_time, Mapping): raise IngestionValidationError("invalid Time object")
        timing["race_time_millis"] = _optional_int(race_time, "millis")
        timing["race_time_text"] = _optional_text(race_time, "time")
    if fastest_lap is not None:
        if not isinstance(fastest_lap, Mapping): raise IngestionValidationError("invalid FastestLap object")
        timing["fastest_lap_rank"] = _optional_int(fastest_lap, "rank")
        timing["fastest_lap_number"] = _optional_int(fastest_lap, "lap")
        fastest_time = fastest_lap.get("Time")
        if fastest_time is not None:
            if not isinstance(fastest_time, Mapping): raise IngestionValidationError("invalid FastestLap.Time object")
            value = _optional_text(fastest_time, "time")
            timing["fastest_lap_time_seconds"] = _duration(value) if value else None
        speed = fastest_lap.get("AverageSpeed")
        if speed is not None:
            if not isinstance(speed, Mapping): raise IngestionValidationError("invalid FastestLap.AverageSpeed object")
            timing["fastest_lap_speed_kph"] = _optional_float(speed, "speed")
    return timing
