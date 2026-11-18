"""Structured errors raised by external Formula 1 data providers."""


class F1ProviderError(RuntimeError):
    """Base error for a provider request that cannot be safely used."""


class F1ProviderConnectionError(F1ProviderError):
    """The provider could not be reached."""


class F1ProviderTimeoutError(F1ProviderError):
    """The provider did not respond before the configured timeout."""


class F1ProviderHTTPError(F1ProviderError):
    """The provider returned a non-success HTTP response."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"F1 provider returned HTTP {status_code}")


class F1ProviderRateLimitError(F1ProviderHTTPError):
    """The provider rejected a request because its rate limit was reached."""

    def __init__(self, retry_after_seconds: float | None) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(429)


class F1ProviderPayloadError(F1ProviderError):
    """The provider response does not match the documented payload shape."""
