"""Application startup succeeds, validates its invariants, and touches no network."""

from __future__ import annotations

import socket
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from app.config import Settings
from app.core.errors import ConfigurationError
from app.main import build_startup_report, main, validate_startup

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CREDENTIAL_WORDS = ("key", "secret", "token", "password", "passphrase")


# --------------------------------------------------------------------------- #
# Startup validation
# --------------------------------------------------------------------------- #
def test_validate_startup_accepts_valid_settings(isolated_env):
    validate_startup(Settings())


def test_validate_startup_rejects_float_financial_settings():
    """Guards the Decimal rule even against a path that bypasses validation."""
    settings = Settings.model_construct(initial_capital_inr=1000.25)

    with pytest.raises(ConfigurationError, match="must never be represented as float"):
        validate_startup(settings)


def test_validate_startup_rejects_non_positive_capital():
    settings = Settings.model_construct(initial_capital_inr=Decimal("0"))

    with pytest.raises(ConfigurationError, match="greater than zero"):
        validate_startup(settings)


def test_validate_startup_rejects_non_finite_capital():
    settings = Settings.model_construct(initial_capital_inr=Decimal("NaN"))

    with pytest.raises(ConfigurationError, match="finite Decimal"):
        validate_startup(settings)


def test_validate_startup_checks_max_data_age_too():
    settings = Settings.model_construct(max_data_age_seconds=Decimal("-1"))

    with pytest.raises(ConfigurationError, match="max_data_age_seconds"):
        validate_startup(settings)


# --------------------------------------------------------------------------- #
# Startup report
# --------------------------------------------------------------------------- #
def test_startup_report_states_read_only_mode_and_phase(isolated_env):
    report = "\n".join(build_startup_report(Settings()))

    assert "READ-ONLY" in report
    assert "PHASE 0" in report
    assert "no exchange API call was made" in report
    assert "INITIAL_CAPITAL_INR=1000 (Decimal)" in report


def test_startup_report_shows_exact_configured_capital(isolated_env, monkeypatch):
    monkeypatch.setenv("INITIAL_CAPITAL_INR", "12345.6789")

    report = "\n".join(build_startup_report(Settings()))

    assert "INITIAL_CAPITAL_INR=12345.6789 (Decimal)" in report


def test_startup_report_contains_no_credentials(isolated_env):
    report = "\n".join(build_startup_report(Settings())).lower()

    for word in CREDENTIAL_WORDS:
        assert word not in report


# --------------------------------------------------------------------------- #
# main()
# --------------------------------------------------------------------------- #
def test_main_succeeds(isolated_env, capsys):
    assert main() == 0
    assert "[STARTUP] ok" in capsys.readouterr().err


def test_main_returns_error_code_on_invalid_configuration(isolated_env, monkeypatch, capsys):
    monkeypatch.setenv("INITIAL_CAPITAL_INR", "-1")

    assert main() == 1
    assert "[STARTUP] FAILED" in capsys.readouterr().err


def test_main_rejects_arguments_in_phase_0(isolated_env, capsys):
    assert main(["--scan"]) == 2
    assert "no command-line arguments" in capsys.readouterr().err


def test_settings_define_no_credential_fields():
    """Phase 0 requires no API keys, so no credential setting may exist."""
    for name in Settings.model_fields:
        assert not any(word in name.lower() for word in CREDENTIAL_WORDS), name


# --------------------------------------------------------------------------- #
# No network access
# --------------------------------------------------------------------------- #
def test_startup_opens_no_network_connection(isolated_env, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("startup must not touch the network")

    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(socket.socket, "connect_ex", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    monkeypatch.setattr(socket, "create_connection", fail)

    assert main() == 0


def test_no_exchange_adapter_module_exists_yet():
    """Phase 0 must not contain an exchange implementation."""
    modules = sorted(path.name for path in (PROJECT_ROOT / "app" / "exchanges").glob("*.py"))

    assert modules == ["__init__.py"]


def test_entry_point_does_not_import_an_http_client():
    """Proof that importing the entry point cannot itself cause a network call."""
    probe = (
        "import app.main, sys; "
        "print(sorted(m for m in sys.modules "
        "if m.split('.')[0] in {'httpx', 'httpcore', 'requests', 'aiohttp', 'urllib3'}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]", result.stdout


def test_module_runs_as_a_script():
    """`python -m app.main` must exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "app.main"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "[STARTUP] ok" in result.stderr
