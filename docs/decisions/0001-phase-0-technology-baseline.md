# ADR 0001 — Phase 0 technology baseline

- **Status:** accepted
- **Phase:** 0
- **Date:** 2026-09-29

## Context

Phase 0 fixes the toolchain every later phase builds on. Choices made here are
expensive to reverse once adapters, engines and tests depend on them.

## Decisions

### Python 3.12+ (developed on 3.14.7)

`requires-python = ">=3.12"`. The pre-existing `.venv` in this repository is
Python 3.14.7, which satisfies it. Ruff targets `py312` and mypy checks against
`python_version = "3.12"`, so nothing 3.13/3.14-only can be introduced silently.

### Pydantic 2 + pydantic-settings

Typed models and typed configuration, with validation at the boundary. Chosen
over hand-rolled parsing because the settings and domain models need the same
validation machinery, and because `BeforeValidator` lets the Decimal rule be
enforced declaratively.

### httpx — declared, not yet used

Listed as a runtime dependency to pin the transport baseline for the Phase 1+
adapters (async support matters once markets are fetched concurrently). **No
Phase 0 module imports it**, and `tests/unit/test_startup.py` asserts in a
subprocess that importing `app.main` pulls in no HTTP client at all.

This is the one dependency declared ahead of use. The alternative — adding it in
Phase 1 — was rejected because the prompt's technology baseline names it, and
pinning it now avoids a version surprise mid-phase.

### No CCXT

Rejected as the exchange abstraction. CCXT normalises away precisely the
metadata this project exists to reason about: per-network withdrawal fees,
minimum deposit and withdrawal amounts, network enable/disable flags, memo/tag
requirements, per-pair fee tiers. A route is executable or not *because of* that
metadata. The abstraction is therefore this project's own, and adapters stay
thick.

### No FastAPI

Rejected. This is a scanner/CLI application. Nothing in Phases 0–19 requires an
HTTP server, and adding one would introduce a framework, an ASGI server and a
request lifecycle for no current consumer.

### No database, no WebSockets

Both deferred (AGENTS.md §76, §77). Domain models stay persistence-friendly;
the infrastructure arrives when opportunity history is a requirement. Public
REST endpoints are sufficient for correct market data.

### pytest + pytest-asyncio, Ruff, mypy strict

`pytest` runs with `-m "not live"` by default, so a normal test run cannot
contact an exchange; live read-only tests must be explicitly marked and
explicitly selected. mypy runs in `strict` mode with the Pydantic plugin. Ruff
covers `E,W,F,I,N,UP,B,C4,SIM,ANN,RUF` at line length 100.

`warn_unreachable` is intentionally **off**: several runtime guards
(`isinstance(value, Decimal)` in `validate_startup`) are unreachable according to
the annotations but are real defences against a code path that bypasses
validation. Enabling the flag would force their removal.

## Consequences

- A fourth exchange can be added as one adapter without touching the engine.
- No web framework, ORM or message broker is in the dependency tree.
- Ruff's `RUF032` rule turns out to enforce a project rule directly (it flags
  `Decimal(<float literal>)`), so lint is part of financial-correctness
  enforcement, not just style.

## Environment note (not a design decision)

The machine used for Phase 0 blocks mypy's compiled `mypyc` extension under a
Windows Application Control policy, so `python -m mypy` failed at import with
`ImportError: DLL load failed`. Resolved by reinstalling the **same version**
(2.3.1) from its source distribution, which produces a pure-Python
`py3-none-any` wheel with no native extension. No version change, no new
dependency. On a machine without that policy the standard wheel works and is
faster.
