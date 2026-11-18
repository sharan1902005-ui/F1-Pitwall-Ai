"""Isolated client for the documented Jolpica F1 API."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import JolpicaSettings
from app.integrations.f1.errors import (
    F1ProviderConnectionError,
    F1ProviderError,
    F1ProviderHTTPError,
    F1ProviderPayloadError,
    F1ProviderRateLimitError,
    F1ProviderTimeoutError,
)


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ProviderHealth:
    """Connectivity result without exposing provider internals or credentials."""

    provider: str
    available: bool
    detail: str


class JolpicaClient:
    """Fetch documented Jolpica resources with bounded retries and pagination."""

    provider_name = "jolpica"
    transient_status_codes = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        settings: JolpicaSettings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or JolpicaSettings.from_environment()
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=self.settings.base_url,
            headers={"User-Agent": self.settings.user_agent, "Accept": "application/json"},
            timeout=httpx.Timeout(
                connect=self.settings.connect_timeout_seconds,
                read=self.settings.read_timeout_seconds,
                write=self.settings.read_timeout_seconds,
                pool=self.settings.connect_timeout_seconds,
            ),
            transport=transport,
        )

    def close(self) -> None:
        """Close the underlying HTTP client when the caller owns its lifecycle."""
        self._client.close()

    def health_check(self) -> ProviderHealth:
        """Verify provider connectivity through the documented seasons endpoint."""
        try:
            payload = self._request_json("/ergast/f1/seasons/", {"limit": 1, "offset": 0})
            self._records(payload, ("MRData", "SeasonTable", "Seasons"))
        except F1ProviderError as exc:
            return ProviderHealth(
                provider=self.provider_name,
                available=False,
                detail=str(exc),
            )
        return ProviderHealth(
            provider=self.provider_name,
            available=True,
            detail="Jolpica seasons endpoint responded with a valid payload.",
        )

    def list_seasons(self) -> list[JsonObject]:
        """Return documented season records from `/ergast/f1/seasons/`."""
        return self._paginated("/ergast/f1/seasons/", ("MRData", "SeasonTable", "Seasons"))

    def list_circuits(self) -> list[JsonObject]:
        """Return documented circuit records from `/ergast/f1/circuits/`."""
        return self._paginated("/ergast/f1/circuits/", ("MRData", "CircuitTable", "Circuits"))

    def list_drivers(self) -> list[JsonObject]:
        """Return documented driver records from `/ergast/f1/drivers/`."""
        return self._paginated("/ergast/f1/drivers/", ("MRData", "DriverTable", "Drivers"))

    def list_constructors(self) -> list[JsonObject]:
        """Return documented constructor records from `/ergast/f1/constructors/`."""
        return self._paginated(
            "/ergast/f1/constructors/",
            ("MRData", "ConstructorTable", "Constructors"),
        )

    def list_race_results(self, season: int, round_number: int | None = None) -> list[JsonObject]:
        """Return race records containing documented result data."""
        return self._race_collection(season, round_number, "results")

    def list_qualifying_results(self, season: int, round_number: int | None = None) -> list[JsonObject]:
        """Return race records containing documented qualifying data."""
        return self._race_collection(season, round_number, "qualifying")

    def list_laps(self, season: int, round_number: int) -> list[JsonObject]:
        """Return race records containing documented lap data for one round."""
        return self._race_collection(season, round_number, "laps")

    def list_pit_stops(self, season: int, round_number: int) -> list[JsonObject]:
        """Return race records containing documented pit-stop data for one round."""
        return self._race_collection(season, round_number, "pitstops")

    def _race_collection(
        self,
        season: int,
        round_number: int | None,
        resource: str,
    ) -> list[JsonObject]:
        if season < 1950:
            raise ValueError("season must be 1950 or later")
        if round_number is not None and round_number <= 0:
            raise ValueError("round_number must be positive")
        route = f"/ergast/f1/{season}/"
        if round_number is not None:
            route += f"{round_number}/"
        return self._paginated(f"{route}{resource}/", ("MRData", "RaceTable", "Races"))

    def _paginated(self, path: str, records_path: tuple[str, ...]) -> list[JsonObject]:
        records: list[JsonObject] = []
        offset = 0

        for _ in range(self.settings.max_pages):
            payload = self._request_json(
                path,
                {"limit": self.settings.page_size, "offset": offset},
            )
            page = self._records(payload, records_path)
            records.extend(page)
            total = self._pagination_total(payload)

            if not page or len(page) < self.settings.page_size:
                return records
            if total is not None and len(records) >= total:
                return records
            offset += self.settings.page_size

        raise F1ProviderPayloadError("Jolpica pagination exceeded the configured page limit")

    def _request_json(self, path: str, params: Mapping[str, int]) -> JsonObject:
        last_error: F1ProviderError | None = None

        for attempt in range(self.settings.retry_limit + 1):
            try:
                response = self._client.get(path, params=params)
            except httpx.ConnectTimeout as exc:
                last_error = F1ProviderTimeoutError("F1 provider connection timed out")
                last_error.__cause__ = exc
            except httpx.TimeoutException as exc:
                last_error = F1ProviderTimeoutError("F1 provider read timed out")
                last_error.__cause__ = exc
            except httpx.RequestError as exc:
                last_error = F1ProviderConnectionError("Unable to connect to F1 provider")
                last_error.__cause__ = exc
            else:
                if response.status_code == 429:
                    last_error = F1ProviderRateLimitError(self._retry_after(response))
                elif response.status_code >= 400:
                    error = F1ProviderHTTPError(response.status_code)
                    if response.status_code not in self.transient_status_codes:
                        raise error
                    last_error = error
                else:
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise F1ProviderPayloadError("F1 provider returned invalid JSON") from exc
                    if not isinstance(payload, dict):
                        raise F1ProviderPayloadError("F1 provider returned a non-object JSON payload")
                    return payload

            if attempt >= self.settings.retry_limit:
                assert last_error is not None
                raise last_error
            self._sleep(self._retry_delay(last_error, attempt))

        raise AssertionError("unreachable")

    @staticmethod
    def _records(payload: JsonObject, path: tuple[str, ...]) -> list[JsonObject]:
        current: Any = payload
        for key in path:
            if not isinstance(current, dict) or key not in current:
                raise F1ProviderPayloadError(
                    f"F1 provider payload is missing expected field: {'.'.join(path)}"
                )
            current = current[key]
        if not isinstance(current, list) or not all(isinstance(item, dict) for item in current):
            raise F1ProviderPayloadError(
                f"F1 provider field {'.'.join(path)} must be a list of objects"
            )
        return current

    @staticmethod
    def _pagination_total(payload: JsonObject) -> int | None:
        metadata = payload.get("MRData")
        if not isinstance(metadata, dict):
            return None
        value = metadata.get("total")
        if value is None:
            return None
        try:
            total = int(value)
        except (TypeError, ValueError) as exc:
            raise F1ProviderPayloadError("F1 provider MRData.total must be an integer") from exc
        if total < 0:
            raise F1ProviderPayloadError("F1 provider MRData.total cannot be negative")
        return total

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return None

    def _retry_delay(self, error: F1ProviderError | None, attempt: int) -> float:
        if isinstance(error, F1ProviderRateLimitError) and error.retry_after_seconds is not None:
            return min(error.retry_after_seconds, self.settings.max_retry_delay_seconds)
        return min(0.25 * (2**attempt), self.settings.max_retry_delay_seconds)
