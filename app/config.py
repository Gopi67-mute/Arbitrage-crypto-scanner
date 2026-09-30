"""Typed application configuration.

Configuration is the only place where runtime values such as capital size live.
They are never hardcoded inside arbitrage logic (AGENTS.md §13, §46).

Phase 0 defines only the settings that are actually used now. Settings belonging
to later engines — fee overrides, profitability thresholds, request timeouts,
retry budgets — are added by the phase that needs them, so that no value in this
file is an unverified financial assumption.

Financial settings are parsed through :func:`app.domain.money.parse_decimal`,
which rejects ``float`` outright. ``INITIAL_CAPITAL_INR=1000.25`` read from the
environment arrives as the string ``"1000.25"`` and becomes exactly
``Decimal("1000.25")``, never a float.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BeforeValidator, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigurationError
from app.core.logging import LogLevel
from app.domain.money import parse_decimal

__all__ = ["AppEnv", "FinancialDecimal", "Settings", "load_settings"]


class AppEnv(StrEnum):
    """Deployment environment. No financial behaviour branches on this value."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


def _normalise_app_env(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


def _normalise_log_level(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


FinancialDecimal = Annotated[Decimal, BeforeValidator(parse_decimal)]
"""A Decimal that refuses float input. Use for every monetary setting."""


class Settings(BaseSettings):
    """Runtime settings, read from the process environment and ``.env``.

    ``extra="forbid"`` means a misspelled key in ``.env`` fails loudly instead of
    being silently ignored. ``frozen=True`` means settings cannot drift at
    runtime.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
        frozen=True,
        validate_default=True,
    )

    app_env: Annotated[AppEnv, BeforeValidator(_normalise_app_env)] = AppEnv.DEVELOPMENT

    log_level: Annotated[LogLevel, BeforeValidator(_normalise_log_level)] = LogLevel.INFO

    initial_capital_inr: FinancialDecimal = Field(
        default=Decimal("1000"),
        gt=Decimal(0),
        description="Starting capital in INR, used by later-phase route evaluation.",
    )

    max_data_age_seconds: FinancialDecimal = Field(
        default=Decimal("5"),
        gt=Decimal(0),
        description="Market data older than this must be reported as STALE_DATA.",
    )


def load_settings() -> Settings:
    """Load and validate settings, or raise :class:`ConfigurationError`.

    Translating pydantic's ``ValidationError`` into the application's own error
    type keeps the startup path behind a single error boundary.
    """
    try:
        return Settings()
    except ValidationError as exc:
        raise ConfigurationError(f"invalid configuration:\n{exc}") from exc
