"""Static guard: binary floating point must not appear in application code.

AGENTS.md §14-§15 make Decimal mandatory for financial values and require the
test suite to protect that rule. Reviews miss a stray ``0.001`` or ``float(...)``;
this test does not.

The guard scans every module under ``app/`` with the ``ast`` module and fails on:
  * a float literal
  * a call to ``float(...)``
  * a call to ``round(...)``  — rounding policy belongs to the (later) precision
    engine, which must round Decimals with an explicit rounding mode
  * the ``or``-fallback idiom that silently turns missing data into zero

AGENTS.md §14 does permit ``float`` for timing and network values. No such value
exists in Phase 0, so the allowlists below are empty. When a genuine timing float
is introduced, add its module here with a comment explaining why it can never
reach a financial calculation — never by widening the rule.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[2] / "app"

# module path (posix, relative to repo root) -> reason it may use non-financial floats
FLOAT_ALLOWLIST: dict[str, str] = {}

FORBIDDEN_CALLS = ("float", "round")


def app_modules() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def test_the_guard_actually_sees_the_application():
    modules = app_modules()
    assert modules, "no application modules found; the guard would pass vacuously"
    assert (APP_ROOT / "main.py") in modules
    assert (APP_ROOT / "domain" / "money.py") in modules


@pytest.mark.parametrize("module", app_modules(), ids=lambda path: path.name)
def test_module_contains_no_float_literal(module):
    relative = module.relative_to(APP_ROOT.parent).as_posix()
    if relative in FLOAT_ALLOWLIST:
        pytest.skip(f"allowlisted: {FLOAT_ALLOWLIST[relative]}")

    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    offenders = [
        f"{relative}:{node.lineno} -> {node.value!r}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]

    assert not offenders, (
        "float literals are forbidden in application code; use Decimal(\"...\"):\n"
        + "\n".join(offenders)
    )


@pytest.mark.parametrize("module", app_modules(), ids=lambda path: path.name)
def test_module_does_not_call_float_or_round(module):
    relative = module.relative_to(APP_ROOT.parent).as_posix()
    if relative in FLOAT_ALLOWLIST:
        pytest.skip(f"allowlisted: {FLOAT_ALLOWLIST[relative]}")

    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    offenders = [
        f"{relative}:{node.lineno} -> {node.func.id}(...)"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FORBIDDEN_CALLS
    ]

    assert not offenders, (
        "float()/round() must not be applied to financial values; parse with "
        "app.domain.money.parse_decimal and round Decimals with an explicit "
        "rounding mode:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize("module", app_modules(), ids=lambda path: path.name)
def test_module_has_no_or_fallback_to_zero(module):
    """`fee = api_fee or Decimal("0")` is banned outright (AGENTS.md §64)."""
    relative = module.relative_to(APP_ROOT.parent).as_posix()
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))

    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BoolOp) or not isinstance(node.op, ast.Or):
            continue
        for value in node.values[1:]:
            if _is_zero_like(value):
                offenders.append(f"{relative}:{node.lineno}")

    assert not offenders, (
        "an `or` fallback must not supply a default for a possibly-missing "
        "financial value; leave it UNKNOWN (app.domain.known):\n" + "\n".join(offenders)
    )


def _is_zero_like(node: ast.expr) -> bool:
    """True for `0`, `"0"`, and `Decimal(0)` / `Decimal("0")` style literals."""
    if isinstance(node, ast.Constant):
        return node.value in (0, "0")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id != "Decimal" or not node.args:
            return False
        return _is_zero_like(node.args[0])
    return False
