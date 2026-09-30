"""Logging foundation.

Standard library logging, configured once, scoped to the ``app`` logger
namespace so the scanner never hijacks third-party loggers.

Design constraints (AGENTS.md §56):
  * the level is configurable
  * console output is readable by a human watching a scan
  * warnings/errors are visually distinguishable from information
  * nothing secret is ever formatted into a log record by this module
  * calling ``configure_logging`` twice does not duplicate output
"""

from __future__ import annotations

import logging
import sys
from enum import StrEnum
from typing import TextIO

from app.core.errors import ConfigurationError

__all__ = [
    "APP_LOGGER_NAME",
    "LogLevel",
    "configure_logging",
    "get_logger",
    "resolve_log_level",
]

APP_LOGGER_NAME = "app"

_HANDLER_NAME = "crypto-arbitrage-console"
_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s :: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class LogLevel(StrEnum):
    """Log levels accepted by configuration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @property
    def numeric(self) -> int:
        """The stdlib numeric level for this name."""
        return logging.getLevelNamesMapping()[self.value]


def resolve_log_level(level: LogLevel | str) -> LogLevel:
    """Normalise a log level, raising rather than falling back to a default.

    An unrecognised level is a configuration error, not something to silently
    replace with INFO.
    """
    if isinstance(level, LogLevel):
        return level
    try:
        return LogLevel(level.strip().upper())
    except ValueError as exc:
        permitted = ", ".join(item.value for item in LogLevel)
        raise ConfigurationError(
            f"unknown log level {level!r}; expected one of: {permitted}"
        ) from exc


def configure_logging(
    level: LogLevel | str = LogLevel.INFO,
    *,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Attach a single console handler to the ``app`` logger and return it.

    Idempotent: repeated calls replace this module's handler instead of adding
    another one, so log lines are never emitted twice.

    Records go to stderr by default, leaving stdout free for report output.
    """
    resolved = resolve_log_level(level)
    logger = logging.getLogger(APP_LOGGER_NAME)

    for existing in list(logger.handlers):
        if existing.name == _HANDLER_NAME:
            logger.removeHandler(existing)
            existing.close()

    handler = logging.StreamHandler(sys.stderr if stream is None else stream)
    handler.name = _HANDLER_NAME
    handler.setLevel(resolved.numeric)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    logger.addHandler(handler)
    logger.setLevel(resolved.numeric)
    # The scanner owns its namespace; do not also emit through the root logger.
    logger.propagate = False
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger guaranteed to sit inside the configured ``app`` namespace.

    ``get_logger(__name__)`` from anywhere in the package works as expected; a
    bare name such as ``get_logger("coindcx")`` is prefixed automatically.
    """
    if name is None or name == APP_LOGGER_NAME:
        return logging.getLogger(APP_LOGGER_NAME)
    if not name.startswith(f"{APP_LOGGER_NAME}."):
        name = f"{APP_LOGGER_NAME}.{name}"
    return logging.getLogger(name)
