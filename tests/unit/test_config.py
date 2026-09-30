"""Configuration loads, preserves exact Decimals, and rejects bad input."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.config import AppEnv, Settings, load_settings
from app.core.errors import ConfigurationError
from app.core.logging import LogLevel


def test_defaults_load_without_env_or_dotenv(isolated_env):
    settings = load_settings()

    assert settings.app_env is AppEnv.DEVELOPMENT
    assert settings.log_level is LogLevel.INFO
    assert settings.initial_capital_inr == Decimal("1000")
    assert settings.max_data_age_seconds == Decimal("5")


def test_financial_settings_are_decimal_not_float(isolated_env):
    settings = load_settings()

    assert isinstance(settings.initial_capital_inr, Decimal)
    assert isinstance(settings.max_data_age_seconds, Decimal)
    assert not isinstance(settings.initial_capital_inr, float)
    assert not isinstance(settings.max_data_age_seconds, float)


def test_capital_from_env_keeps_exact_decimal_representation(isolated_env, monkeypatch):
    """A value that no float can represent must survive parsing bit-exactly."""
    raw = "1234.5678901234567890123456789"
    monkeypatch.setenv("INITIAL_CAPITAL_INR", raw)

    settings = load_settings()

    assert settings.initial_capital_inr == Decimal(raw)
    assert str(settings.initial_capital_inr) == raw
    # The float route would have silently destroyed the tail digits.
    assert settings.initial_capital_inr != Decimal(str(float(raw)))


def test_capital_that_a_float_cannot_represent_is_exact(isolated_env, monkeypatch):
    monkeypatch.setenv("INITIAL_CAPITAL_INR", "0.1")

    settings = load_settings()

    assert settings.initial_capital_inr == Decimal("0.1")
    assert settings.initial_capital_inr * 3 == Decimal("0.3")


def test_dotenv_file_is_read(isolated_env):
    (isolated_env / ".env").write_text(
        "APP_ENV=production\nLOG_LEVEL=WARNING\nINITIAL_CAPITAL_INR=50000\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.app_env is AppEnv.PRODUCTION
    assert settings.log_level is LogLevel.WARNING
    assert settings.initial_capital_inr == Decimal("50000")


def test_env_var_overrides_dotenv(isolated_env, monkeypatch):
    (isolated_env / ".env").write_text("INITIAL_CAPITAL_INR=800\n", encoding="utf-8")
    monkeypatch.setenv("INITIAL_CAPITAL_INR", "7500.50")

    assert load_settings().initial_capital_inr == Decimal("7500.50")


def test_env_values_are_case_insensitive(isolated_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "  Production ")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = load_settings()

    assert settings.app_env is AppEnv.PRODUCTION
    assert settings.log_level is LogLevel.DEBUG


@pytest.mark.parametrize("value", ["0", "-1", "-0.01"])
def test_non_positive_capital_is_rejected(isolated_env, monkeypatch, value):
    monkeypatch.setenv("INITIAL_CAPITAL_INR", value)

    with pytest.raises(ConfigurationError):
        load_settings()


@pytest.mark.parametrize("value", ["0", "-5"])
def test_non_positive_max_data_age_is_rejected(isolated_env, monkeypatch, value):
    monkeypatch.setenv("MAX_DATA_AGE_SECONDS", value)

    with pytest.raises(ConfigurationError):
        load_settings()


@pytest.mark.parametrize("value", ["", "abc", "1,000", "1000 INR", "NaN", "Infinity"])
def test_unparseable_capital_is_rejected(isolated_env, monkeypatch, value):
    monkeypatch.setenv("INITIAL_CAPITAL_INR", value)

    with pytest.raises(ConfigurationError):
        load_settings()


def test_unknown_log_level_is_rejected(isolated_env, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")

    with pytest.raises(ConfigurationError):
        load_settings()


def test_unknown_app_env_is_rejected(isolated_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod-ish")

    with pytest.raises(ConfigurationError):
        load_settings()


def test_unknown_dotenv_key_is_rejected_not_ignored(isolated_env):
    """A typo must fail loudly rather than be silently dropped."""
    (isolated_env / ".env").write_text("INITIAL_CAPITAL_INRR=1000\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_settings()


def test_float_capital_passed_directly_is_rejected(isolated_env):
    """Even in-process construction cannot introduce a float financial value."""
    with pytest.raises(PydanticValidationError) as excinfo:
        Settings(initial_capital_inr=1000.25)  # type: ignore[arg-type]

    assert "float is forbidden" in str(excinfo.value)


def test_bool_capital_is_rejected(isolated_env):
    with pytest.raises(PydanticValidationError):
        Settings(initial_capital_inr=True)  # type: ignore[arg-type]


def test_settings_are_frozen(isolated_env):
    settings = load_settings()

    with pytest.raises(PydanticValidationError):
        settings.initial_capital_inr = Decimal("2000")  # type: ignore[misc]
