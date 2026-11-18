"""Isolated client for OpenF1's documented historical weather endpoints."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from app.config import OpenF1Settings
from app.integrations.f1.errors import (
    F1ProviderConnectionError,
    F1ProviderError,
    F1ProviderHTTPError,
    F1ProviderPayloadError,
    F1ProviderRateLimitError,
    F1ProviderTimeoutError,
)
from app.integrations.f1.jolpica_client import ProviderHealth

JsonObject = dict[str, Any]


class OpenF1WeatherClient:
    """Read documented OpenF1 sessions and historical weather observations."""

    provider_name = "openf1"
    transient_status_codes = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        settings: OpenF1Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or OpenF1Settings.from_environment()
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=self.settings.base_url,
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(
                connect=self.settings.connect_timeout_seconds,
                read=self.settings.read_timeout_seconds,
                write=self.settings.read_timeout_seconds,
                pool=self.settings.connect_timeout_seconds,
            ),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def health_check(self) -> ProviderHealth:
        """Verify connectivity with a safe documented sessions request."""
        try:
            self.list_sessions(2023)
        except F1ProviderError as exc:
            return ProviderHealth(self.provider_name, False, str(exc))
        return ProviderHealth(self.provider_name, True, "OpenF1 sessions endpoint responded with a valid payload.")

    def list_sessions(self, season: int) -> list[JsonObject]:
        if season < 2023:
            raise ValueError("OpenF1 historical coverage starts in 2023")
        return self._request_records("/v1/sessions", {"year": season})

    def list_weather(self, session_key: int) -> list[JsonObject]:
        if session_key <= 0:
            raise ValueError("session_key must be positive")
        return self._request_records("/v1/weather", {"session_key": session_key})

    def _request_records(self, path: str, params: Mapping[str, int]) -> list[JsonObject]:
        last_error: F1ProviderError | None = None
        for attempt in range(self.settings.retry_limit + 1):
            try:
                response = self._client.get(path, params=params)
            except httpx.ConnectTimeout as exc:
                last_error = F1ProviderTimeoutError("OpenF1 connection timed out"); last_error.__cause__ = exc
            except httpx.TimeoutException as exc:
                last_error = F1ProviderTimeoutError("OpenF1 read timed out"); last_error.__cause__ = exc
            except httpx.RequestError as exc:
                last_error = F1ProviderConnectionError("Unable to connect to OpenF1"); last_error.__cause__ = exc
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
                        raise F1ProviderPayloadError("OpenF1 returned invalid JSON") from exc
                    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
                        raise F1ProviderPayloadError("OpenF1 returned a non-list JSON payload")
                    return payload
            if attempt >= self.settings.retry_limit:
                assert last_error is not None
                raise last_error
            self._sleep(self._retry_delay(last_error, attempt))
        raise AssertionError("unreachable")

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        try:
            return max(0.0, float(response.headers["Retry-After"]))
        except (KeyError, ValueError):
            return None

    def _retry_delay(self, error: F1ProviderError | None, attempt: int) -> float:
        if isinstance(error, F1ProviderRateLimitError) and error.retry_after_seconds is not None:
            return min(error.retry_after_seconds, self.settings.max_retry_delay_seconds)
        return min(0.25 * (2**attempt), self.settings.max_retry_delay_seconds)
