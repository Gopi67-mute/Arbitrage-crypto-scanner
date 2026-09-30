"""Logging initialises, honours the configured level, and does not duplicate output."""

from __future__ import annotations

import io
import logging

import pytest

from app.core.errors import ConfigurationError
from app.core.logging import (
    APP_LOGGER_NAME,
    LogLevel,
    configure_logging,
    get_logger,
    resolve_log_level,
)


def test_configure_logging_attaches_a_single_handler():
    stream = io.StringIO()
    logger = configure_logging(LogLevel.INFO, stream=stream)

    assert logger.name == APP_LOGGER_NAME
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1


def test_configure_logging_is_idempotent():
    configure_logging(LogLevel.INFO, stream=io.StringIO())
    stream = io.StringIO()
    logger = configure_logging(LogLevel.INFO, stream=stream)

    assert len(logger.handlers) == 1

    get_logger("app.test").info("single line")
    assert stream.getvalue().count("single line") == 1


def test_records_reach_the_stream_with_level_and_logger_name():
    stream = io.StringIO()
    configure_logging(LogLevel.INFO, stream=stream)

    get_logger("coindcx").warning("[COINDCX] rate limited")

    output = stream.getvalue()
    assert "WARNING" in output
    assert "app.coindcx" in output
    assert "[COINDCX] rate limited" in output


def test_failures_are_distinguishable_from_information():
    stream = io.StringIO()
    configure_logging(LogLevel.INFO, stream=stream)
    logger = get_logger("app.scan")

    logger.info("markets discovered")
    logger.error("exchange unreachable")

    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    assert any("INFO" in line and "markets discovered" in line for line in lines)
    assert any("ERROR" in line and "exchange unreachable" in line for line in lines)


def test_level_filters_lower_severity():
    stream = io.StringIO()
    configure_logging(LogLevel.WARNING, stream=stream)
    logger = get_logger("app.scan")

    logger.debug("noisy detail")
    logger.info("routine")
    logger.warning("attention")

    output = stream.getvalue()
    assert "noisy detail" not in output
    assert "routine" not in output
    assert "attention" in output


def test_string_level_is_accepted_case_insensitively():
    logger = configure_logging("debug", stream=io.StringIO())
    assert logger.level == logging.DEBUG


def test_unknown_level_raises_rather_than_defaulting():
    with pytest.raises(ConfigurationError, match="unknown log level"):
        configure_logging("VERBOSE", stream=io.StringIO())

    with pytest.raises(ConfigurationError):
        resolve_log_level("trace")


def test_log_level_numeric_values_match_stdlib():
    assert LogLevel.DEBUG.numeric == logging.DEBUG
    assert LogLevel.CRITICAL.numeric == logging.CRITICAL


def test_get_logger_keeps_everything_inside_the_app_namespace():
    assert get_logger().name == APP_LOGGER_NAME
    assert get_logger("app.main").name == "app.main"
    assert get_logger("kucoin").name == "app.kucoin"


def test_app_logger_does_not_propagate_to_root():
    logger = configure_logging(LogLevel.INFO, stream=io.StringIO())
    assert logger.propagate is False
