"""Tests for external F1 data ingestion preparation."""

from __future__ import annotations

import pytest

from app.integrations.f1.errors import F1ProviderConnectionError
from app.services.f1_ingestion import F1Dataset, F1IngestionEngine, IngestionRequest, UnsupportedDatasetError


def _race(driver_id: str = "max_verstappen", grid: str = "1") -> dict[str, object]:
    return {"season": "2024", "round": "1", "raceName": "Bahrain Grand Prix", "date": "2024-03-02", "time": "15:00:00Z", "Circuit": {"circuitId": "bahrain", "circuitName": "Bahrain International Circuit", "Location": {"country": "Bahrain"}}, "Results": [{"Driver": {"driverId": driver_id}, "Constructor": {"constructorId": "red_bull"}, "position": "1", "positionText": "1", "points": "25", "grid": grid, "laps": "57", "status": "Finished"}]}


class FakeClient:
    provider_name = "jolpica"

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.seasons = [{"season": "2024"}]
        self.circuits = [{"circuitId": "bahrain", "circuitName": "Bahrain International Circuit", "Location": {"lat": "26.0325", "long": "50.5106", "country": "Bahrain"}}]
        self.drivers = [{"driverId": "max_verstappen", "code": "VER", "givenName": "Max", "familyName": "Verstappen", "dateOfBirth": "1997-09-30"}]
        self.constructors = [{"constructorId": "red_bull", "name": "Red Bull", "nationality": "Austrian"}]
        self.results = [_race()]
        self.qualifying = [{**_race(), "QualifyingResults": [{"Driver": {"driverId": "max_verstappen"}, "Constructor": {"constructorId": "red_bull"}, "position": "1", "Q1": "1:30.031", "Q3": "1:29.179"}]}]
        self.laps = [{**_race(), "Laps": [{"number": "1", "Timings": [{"driverId": "max_verstappen", "position": "1", "time": "1:35.123"}]}]}]
        self.pits = [{**_race(), "PitStops": [{"driverId": "max_verstappen", "stop": "1", "lap": "17", "time": "16:02:01", "duration": "22.500"}]}]

    def list_seasons(self): self.calls.append("seasons"); return self.seasons
    def list_circuits(self): self.calls.append("circuits"); return self.circuits
    def list_drivers(self): self.calls.append("drivers"); return self.drivers
    def list_constructors(self): self.calls.append("constructors"); return self.constructors
    def list_race_results(self, season, round_number=None): self.calls.append("results"); return self.results
    def list_qualifying_results(self, season, round_number=None): self.calls.append("qualifying"); return self.qualifying
    def list_laps(self, season, round_number): self.calls.append("laps"); return self.laps
    def list_pit_stops(self, season, round_number): self.calls.append("pits"); return self.pits


def test_retrieves_and_normalizes_supported_metadata() -> None:
    result = F1IngestionEngine(FakeClient()).ingest(IngestionRequest((F1Dataset.SEASONS, F1Dataset.CIRCUITS, F1Dataset.DRIVERS, F1Dataset.CONSTRUCTORS)))
    circuit = result.reports[F1Dataset.CIRCUITS].records[0]
    assert result.imported == 4
    assert circuit.data["latitude"] == pytest.approx(26.0325)
    assert circuit.raw["circuitId"] == "bahrain"


def test_one_result_request_feeds_events_results_and_starting_grids() -> None:
    client = FakeClient()
    result = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.RACE_EVENTS, F1Dataset.RACE_RESULTS, F1Dataset.STARTING_GRIDS), season=2024))
    assert client.calls == ["results"]
    assert result.reports[F1Dataset.RACE_EVENTS].records[0].data["start_at"] == "2024-03-02T15:00:00+00:00"
    assert result.reports[F1Dataset.RACE_RESULTS].records[0].data["points"] == 25.0
    assert result.reports[F1Dataset.STARTING_GRIDS].records[0].data["grid_position"] == 1


def test_normalizes_qualifying_laps_and_pit_stops_by_event() -> None:
    result = F1IngestionEngine(FakeClient()).ingest(IngestionRequest((F1Dataset.QUALIFYING_RESULTS, F1Dataset.LAP_TIMES, F1Dataset.PIT_STOPS), season=2024, round_number=1))
    assert result.reports[F1Dataset.QUALIFYING_RESULTS].records[0].data["q3_seconds"] == pytest.approx(89.179)
    assert result.reports[F1Dataset.LAP_TIMES].records[0].data["lap_time_seconds"] == pytest.approx(95.123)
    assert result.reports[F1Dataset.PIT_STOPS].records[0].data["duration_seconds"] == pytest.approx(22.5)


def test_optional_fields_remain_none() -> None:
    client = FakeClient(); client.drivers[0].pop("code")
    report = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.DRIVERS,))).reports[F1Dataset.DRIVERS]
    assert report.records[0].data["code"] is None


def test_malformed_record_is_rejected_without_being_discarded() -> None:
    client = FakeClient(); client.circuits = [{"circuitId": "broken"}]
    report = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.CIRCUITS,))).reports[F1Dataset.CIRCUITS]
    assert report.imported == 0 and report.rejected == 1
    assert report.rejected_records[0].raw["circuitId"] == "broken"


def test_invalid_date_is_rejected() -> None:
    client = FakeClient(); broken = _race(); broken["date"] = "not-a-date"; client.results = [broken]
    report = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.RACE_RESULTS,), season=2024)).reports[F1Dataset.RACE_RESULTS]
    assert "invalid ISO date" in report.rejected_records[0].reason


def test_duplicates_in_a_batch_are_skipped() -> None:
    client = FakeClient(); client.circuits *= 2
    report = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.CIRCUITS,))).reports[F1Dataset.CIRCUITS]
    assert report.imported == 1 and report.skipped == 1


def test_empty_provider_response_is_distinct_from_zero_values() -> None:
    client = FakeClient(); client.seasons = []
    report = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.SEASONS,))).reports[F1Dataset.SEASONS]
    assert report.empty and report.errors == []


def test_provider_failure_allows_partial_operation_completion() -> None:
    class PartialFailure(FakeClient):
        def list_circuits(self): raise F1ProviderConnectionError("provider offline")
    result = F1IngestionEngine(PartialFailure()).ingest(IngestionRequest((F1Dataset.CIRCUITS, F1Dataset.DRIVERS)))
    assert result.reports[F1Dataset.CIRCUITS].errors == ["provider offline"]
    assert result.reports[F1Dataset.DRIVERS].imported == 1


def test_event_scoped_data_requires_a_round() -> None:
    result = F1IngestionEngine(FakeClient()).ingest(IngestionRequest((F1Dataset.LAP_TIMES,), season=2024))
    assert result.reports[F1Dataset.LAP_TIMES].errors == ["round_number is required for this dataset"]


def test_historical_weather_is_explicitly_unsupported() -> None:
    report = F1IngestionEngine(FakeClient()).ingest(IngestionRequest((F1Dataset.HISTORICAL_WEATHER,), season=2024)).reports[F1Dataset.HISTORICAL_WEATHER]
    assert report.unsupported_reason is not None


def test_unknown_dataset_is_rejected_before_requests() -> None:
    with pytest.raises(UnsupportedDatasetError):
        IngestionRequest(("telemetry",)).selected_datasets()


def test_large_batch_normalization() -> None:
    client = FakeClient(); client.circuits = [{"circuitId": f"track-{index}", "circuitName": f"Track {index}", "Location": {"country": "Test"}} for index in range(1000)]
    report = F1IngestionEngine(client).ingest(IngestionRequest((F1Dataset.CIRCUITS,))).reports[F1Dataset.CIRCUITS]
    assert report.imported == 1000 and report.rejected == 0
