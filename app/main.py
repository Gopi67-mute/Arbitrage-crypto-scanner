"""Application entry point.

Phase 0 responsibility: prove that configuration, logging, the error boundary and
the Decimal invariants work together, then exit successfully.

This module MUST NOT contact an exchange, MUST NOT calculate arbitrage and MUST
NOT require API credentials. Run it with::

    python -m app.main
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from decimal import Decimal

from app import APP_NAME, CURRENT_PHASE, __version__
from app.config import Settings, load_settings
from app.core.errors import ApplicationError, ConfigurationError
from app.core.logging import configure_logging, get_logger

__all__ = ["build_startup_report", "main", "validate_startup"]

# Financial settings that the whole system depends on being exact Decimals.
_FINANCIAL_SETTINGS = ("initial_capital_inr", "max_data_age_seconds")


def validate_startup(settings: Settings) -> None:
    """Assert the invariants every later phase relies on, or raise.

    These checks are not redundant with pydantic validation: they also hold for a
    ``Settings`` produced by ``model_construct`` or by a future code path that
    bypasses validation. The Decimal rule is the project's cardinal rule, so it
    is re-asserted at the boundary rather than assumed.
    """
    for name in _FINANCIAL_SETTINGS:
        value = getattr(settings, name)
        if not isinstance(value, Decimal):
            raise ConfigurationError(
                f"{name} must be a Decimal, got {type(value).__name__}: "
                "financial values must never be represented as float"
            )
        if not value.is_finite():
            raise ConfigurationError(f"{name} must be a finite Decimal, got {value}")
        if value <= 0:
            raise ConfigurationError(f"{name} must be greater than zero, got {value}")


def build_startup_report(settings: Settings) -> list[str]:
    """The lines logged at startup. Returned as data so it can be asserted on.

    Contains no credentials: Phase 0 defines no credential settings at all.
    """
    return [
        f"[STARTUP] {APP_NAME} v{__version__}",
        f"[STARTUP] phase: {CURRENT_PHASE}",
        "[STARTUP] mode: READ-ONLY — no orders, no deposits, no withdrawals, no transfers",
        f"[CONFIG] APP_ENV={settings.app_env.value}",
        f"[CONFIG] LOG_LEVEL={settings.log_level.value}",
        f"[CONFIG] INITIAL_CAPITAL_INR={settings.initial_capital_inr} (Decimal)",
        f"[CONFIG] MAX_DATA_AGE_SECONDS={settings.max_data_age_seconds} (Decimal)",
        "[STARTUP] exchange adapters implemented: 0 (CoinDCX/KuCoin/Binance arrive in Phase 2-4)",
        "[STARTUP] no exchange API call was made",
        "[STARTUP] ok",
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Load configuration, initialise logging, validate startup, report, exit.

    Returns a process exit code: 0 on success, 1 on a handled application error.
    """
    if argv:
        print(
            f"{APP_NAME}: no command-line arguments are accepted in Phase 0; "
            f"got {list(argv)!r}",
            file=sys.stderr,
        )
        return 2

    try:
        settings = load_settings()
        configure_logging(settings.log_level)
        validate_startup(settings)
    except ApplicationError as exc:
        # Logging may not be configured yet, so report to stderr directly.
        print(f"[STARTUP] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # An explicit name, not __name__: under `python -m app.main` the module name
    # is "__main__", which would log as "app.__main__".
    logger = get_logger("main")
    for line in build_startup_report(settings):
        logger.info(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
