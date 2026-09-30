"""Shared fixtures for the deterministic unit tests."""

from __future__ import annotations

import logging

import pytest

from app.core.logging import APP_LOGGER_NAME

# Every environment variable Settings reads. Cleared so that a developer's real
# shell environment or .env file cannot change a test outcome.
SETTINGS_ENV_VARS = (
    "APP_ENV",
    "LOG_LEVEL",
    "INITIAL_CAPITAL_INR",
    "MAX_DATA_AGE_SECONDS",
)


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """Run in an empty directory with no settings environment variables set.

    Returns the directory, so a test can write its own ``.env`` there.
    """
    for name in SETTINGS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _restore_app_logger():
    """Leave the ``app`` logger exactly as it was found.

    ``configure_logging`` mutates process-wide logging state, so tests that call
    it (directly or through ``main``) must not leak that into other tests.
    """
    logger = logging.getLogger(APP_LOGGER_NAME)
    handlers = list(logger.handlers)
    level = logger.level
    propagate = logger.propagate
    yield
    for handler in list(logger.handlers):
        if handler not in handlers:
            logger.removeHandler(handler)
            handler.close()
    logger.handlers = handlers
    logger.setLevel(level)
    logger.propagate = propagate
