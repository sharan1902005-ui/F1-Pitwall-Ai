"""Unit tests for the isolated Jolpica provider client."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from app.config import JolpicaSettings
from app.integrations.f1.errors import (
    F1ProviderHTTPError,
    F1ProviderPayloadError,
    F1ProviderTimeoutError,
)
from app.integrations.f1.jolpica_client import JolpicaClient


def _settings(**overrides: object) -> JolpicaSettings:
    values: dict[str, object] = {
        "base_url": "https://jolpica.test",
        "user_agent": "PitWallAI-tests/1.0",
        "connect_timeout_seconds": 0.1,
        "read_timeout_seconds": 0.1,
        "retry_limit": 0,
        "max_retry_delay_seconds": 5.0,
        "page_size": 100,
        "max_pages": 5,
    }
    values.update(overrides)
    return JolpicaSettings(**values)  # type: ignore[arg-type]


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    settings: JolpicaSettings | None = None,
    delays: list[float] | None = None,
) -> JolpicaClient:
    return JolpicaClient(
        settings or _settings(),
        transport=httpx.MockTransport(handler),
        sleep=(delays if delays is not None else []).append,
    )


def _seasons_payload(records: list[dict[str, str]], total: int | None = None) -> dict[str, object]:
    return {
        "MRData": {
            "total": str(len(records) if total is None else total),
            "SeasonTable": {"Seasons": records},
        }
    }


def test_health_check_and_list_seasons_use_documented_route() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ergast/f1/seasons/"
        assert request.headers["User-Agent"] == "PitWallAI-tests/1.0"
        assert "Authorization" not in request.headers
        assert request.url.params["limit"] in {"1", "100"}
        return httpx.Response(200, json=_seasons_payload([{"season": "2024"}]), request=request)

    client = _client(handler)

    health = client.health_check()
    assert health.available is True
    assert client.list_seasons() == [{"season": "2024"}]


def test_connection_timeout_returns_unavailable_health_and_structured_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = _client(handler)

    health = client.health_check()
    assert health.available is False
    assert "timed out" in health.detail.lower()
    with pytest.raises(F1ProviderTimeoutError):
        client.list_seasons()


def test_non_transient_http_error_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, request=request)

    client = _client(handler, settings=_settings(retry_limit=2))

    with pytest.raises(F1ProviderHTTPError, match="HTTP 404"):
        client.list_seasons()
    assert calls == 1


def test_rate_limit_honors_retry_after_then_retries() -> None:
    calls = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, request=request)
        return httpx.Response(200, json=_seasons_payload([{"season": "2024"}]), request=request)

    client = _client(handler, settings=_settings(retry_limit=1), delays=delays)

    assert client.list_seasons() == [{"season": "2024"}]
    assert calls == 2
    assert delays == [2.0]


def test_transient_http_error_retries_with_bounded_backoff() -> None:
    calls = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, json=_seasons_payload([{"season": "2024"}]), request=request)

    client = _client(handler, settings=_settings(retry_limit=1), delays=delays)

    assert client.list_seasons() == [{"season": "2024"}]
    assert calls == 2
    assert delays == [0.25]


def test_unexpected_payload_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"MRData": {"SeasonTable": {}}}, request=request)

    client = _client(handler)

    with pytest.raises(F1ProviderPayloadError, match="MRData.SeasonTable.Seasons"):
        client.list_seasons()
    assert client.health_check().available is False


def test_provider_unavailability_is_reported_without_claiming_health() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("provider offline", request=request)

    health = _client(handler).health_check()

    assert health.available is False
    assert "unable to connect" in health.detail.lower()


def test_pagination_uses_offsets_until_documented_total_is_reached() -> None:
    first_page = [{"season": str(1950 + index)} for index in range(100)]
    second_page = [{"season": "2050"}]
    offsets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = request.url.params["offset"]
        offsets.append(offset)
        records = first_page if offset == "0" else second_page
        return httpx.Response(200, json=_seasons_payload(records, total=101), request=request)

    seasons = _client(handler).list_seasons()

    assert len(seasons) == 101
    assert offsets == ["0", "100"]


def test_environment_configuration_is_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOLPICA_BASE_URL", "https://example.test")
    monkeypatch.setenv("JOLPICA_RETRY_LIMIT", "3")
    monkeypatch.setenv("JOLPICA_PAGE_SIZE", "50")

    settings = JolpicaSettings.from_environment()
    assert settings.base_url == "https://example.test"
    assert settings.retry_limit == 3
    assert settings.page_size == 50

    with pytest.raises(ValueError, match="between 1 and 100"):
        JolpicaSettings(page_size=101)

    monkeypatch.setenv("JOLPICA_RETRY_LIMIT", "9")
    with pytest.raises(ValueError, match="between 0 and 5"):
        JolpicaSettings.from_environment()
