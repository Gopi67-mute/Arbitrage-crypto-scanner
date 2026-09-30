"""Application error boundary.

A deliberately small hierarchy. Its purpose is to give every layer one
consistent base type to catch, not to enumerate every future failure mode.

    ApplicationError
        ConfigurationError   invalid / unusable configuration
        ExchangeError        an exchange interaction failed (Phase 1+)
        DataError            required data is missing, stale or unusable
        ValidationError      a domain rule or route constraint was violated

Grow this only when a caller genuinely needs to distinguish a new case.

Note on `DataError`: it is the error raised when code demands a financial value
that could not be verified. Missing financial data must never be quietly turned
into zero (AGENTS.md §62-§64) — it either stays explicitly UNKNOWN or it raises.
"""

__all__ = [
    "ApplicationError",
    "ConfigurationError",
    "DataError",
    "ExchangeError",
    "ValidationError",
]


class ApplicationError(Exception):
    """Base class for every error raised deliberately by this application."""


class ConfigurationError(ApplicationError):
    """Configuration is missing, malformed or internally inconsistent."""


class ExchangeError(ApplicationError):
    """An exchange interaction failed (transport, rate limit, bad response)."""


class DataError(ApplicationError):
    """Required data is unavailable, unverifiable or too old to rely on."""


class ValidationError(ApplicationError):
    """A domain rule or route constraint was violated."""
