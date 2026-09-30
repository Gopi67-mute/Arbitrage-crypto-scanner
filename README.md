# Crypto Arbitrage Scanner

A **READ-ONLY**, real-market, cross-exchange cryptocurrency arbitrage
intelligence and analysis system.

---

## ⚠️ READ-ONLY — WHAT THIS PROJECT DOES NOT DO

> **This project does NOT place trades.**
> **This project does NOT withdraw funds.**
> **This project does NOT deposit funds.**

It also does not transfer funds, cancel orders, or modify exchange balances in
any way. There is no code path to any of those operations, and none will be added
outside a separate, explicitly approved project phase.

It is an analytical tool. It reports calculated results based on available data
and explicitly stated assumptions. It does not guarantee profit, execution,
returns, successful transfer, or any tax outcome.

---

## Purpose

The system exists to answer one question:

> For ₹X of capital, using current real-market conditions, which valid route
> involving CoinDCX, KuCoin and/or Binance can produce the highest **verified
> executable net INR result** after all applicable costs?

"Applicable costs" is the hard part, and it is the whole point. A positive price
difference between two exchanges is not an opportunity. The answer must survive:

| | |
|---|---|
| market spread | order-book depth |
| slippage | trading fees |
| withdrawal fees | network costs |
| deposit constraints | withdrawal constraints |
| minimum order size | minimum deposit / withdrawal |
| quote-currency conversion cost | Indian TDS / tax treatment |
| liquidity limits | data freshness |

The governing principle is **correctness over number of opportunities**. The
system prefers reporting *no opportunity* over reporting a *false* one.

The full engineering constitution is in [AGENTS.md](AGENTS.md). It is normative;
this README summarises it.

---

## Supported exchanges

| Exchange | Region | Adapter status |
|---|---|---|
| CoinDCX | 🇮🇳 India | Not implemented (Phase 2) |
| KuCoin | 🌎 Global | Not implemented (Phase 3) |
| Binance | 🌎 Global | Not implemented (Phase 4) |

Route directions are evaluated in both directions for every pair
(CoinDCX ↔ KuCoin, CoinDCX ↔ Binance, KuCoin ↔ Binance). No direction and no
exchange is ever preferred by default — the market data decides.

---

## Current phase

**PHASE 0 — project setup + architecture foundation.**

Phase 0 contains **no exchange integration, no market data, and no arbitrage
calculation**. What exists today is configuration, logging, the error boundary,
the Decimal foundation, package boundaries, the test harness and an entry point
that starts up and exits.

See [Planned phases](#planned-phases) for the roadmap.

---

## Technology stack

| Purpose | Choice |
|---|---|
| Language | Python 3.12+ (developed on 3.14) |
| Models / validation | Pydantic 2 |
| Configuration | pydantic-settings |
| HTTP transport | httpx *(declared for Phase 1+; not yet imported)* |
| Tests | pytest, pytest-asyncio |
| Lint | Ruff |
| Types | mypy (strict) |
| Money | `decimal.Decimal` — never `float` |

Deliberately **not** used:

- **CCXT** — the exchange abstraction is this project's own. Each venue's
  deposit/withdrawal/network/fee metadata is exactly the detail a generic
  wrapper flattens away, and that detail is what decides whether a route is
  executable.
- **FastAPI** — this is a scanner/CLI application, not a web service. Nothing in
  the roadmap requires an HTTP server.
- **A database** — V1 keeps the domain model persistence-friendly without the
  infrastructure. One gets introduced when opportunity history becomes a
  requirement.
- **WebSockets** — public REST endpoints are sufficient until a phase says
  otherwise.

---

## Local setup

Requires Python 3.12 or newer.

```bash
# 1. create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell / cmd)
source .venv/bin/activate     # macOS / Linux

# 2. install the project plus dev tooling
pip install -e ".[dev]"

# 3. create your local configuration
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

`.env` is git-ignored and must never be committed. **No API credentials are
required** — Phase 0 defines no credential settings at all, and the scanner is
built around public read-only endpoints.

### Run it

```bash
python -m app.main
```

Expected output (to stderr, so stdout stays free for reports):

```
2026-09-30T15:32:10+0530 INFO     app.main :: [STARTUP] Crypto Arbitrage Scanner v0.1.0
2026-09-30T15:32:10+0530 INFO     app.main :: [STARTUP] phase: PHASE 0 — project setup + architecture foundation
2026-09-30T15:32:10+0530 INFO     app.main :: [STARTUP] mode: READ-ONLY — no orders, no deposits, no withdrawals, no transfers
2026-09-30T15:32:10+0530 INFO     app.main :: [CONFIG] APP_ENV=development
2026-09-30T15:32:10+0530 INFO     app.main :: [CONFIG] LOG_LEVEL=INFO
2026-09-30T15:32:10+0530 INFO     app.main :: [CONFIG] INITIAL_CAPITAL_INR=1000 (Decimal)
2026-09-30T15:32:10+0530 INFO     app.main :: [CONFIG] MAX_DATA_AGE_SECONDS=5 (Decimal)
2026-09-30T15:32:10+0530 INFO     app.main :: [STARTUP] exchange adapters implemented: 0 (CoinDCX/KuCoin/Binance arrive in Phase 2-4)
2026-09-30T15:32:10+0530 INFO     app.main :: [STARTUP] no exchange API call was made
2026-09-30T15:32:10+0530 INFO     app.main :: [STARTUP] ok
```

Exit codes: `0` success, `1` configuration/startup error, `2` unexpected
command-line arguments.

### Run the tests

```bash
pytest                 # deterministic unit tests only — no network access
pytest -m live         # live read-only integration tests (none exist yet)
```

`pytest` runs with `-m "not live"` by default, so a normal run can never contact
an exchange.

### Run lint

```bash
ruff check .
ruff check . --fix
```

### Run type checks

```bash
mypy app
```

---

## Configuration

Settings come from the process environment, falling back to `.env`, and are
validated on load. A misspelled key in `.env` is **rejected**, not ignored.

| Variable | Type | Default | Meaning |
|---|---|---|---|
| `APP_ENV` | `development` \| `staging` \| `production` | `development` | Deployment environment. No financial behaviour branches on it. |
| `LOG_LEVEL` | `DEBUG`…`CRITICAL` | `INFO` | Console log level. |
| `INITIAL_CAPITAL_INR` | Decimal, > 0 | `1000` | Starting capital for later-phase route evaluation. |
| `MAX_DATA_AGE_SECONDS` | Decimal, > 0 | `5` | Data older than this is `STALE_DATA`, never an opportunity. |

Capital is configuration, never a constant inside arbitrage logic. The same route
can be profitable at one capital level and unprofitable at another, because
liquidity, slippage, minimums and withdrawal costs do not scale linearly.

Settings that later engines will need — fee overrides, `MIN_NET_PROFIT_INR`,
`MIN_NET_ROI_PERCENT`, request timeouts, retry budgets — are added by the phase
that needs them, so that nothing in `config.py` is an unverified financial
assumption.

---

## High-level architecture

```
        ┌───────────────────────────────────────────────┐
        │  app/exchanges/   CoinDCX · KuCoin · Binance  │  ← all venue-specific
        │                   adapters (Phase 2-4)        │    API knowledge
        └───────────────────────────────────────────────┘
        ┌──────────────┬──────────────┬─────────────────┐
        │  app/fees/   │  app/tax/    │  app/transfers/ │  ← cost + constraint
        │  (Phase 8-9) │  (Phase 11)  │  (Phase 9)      │    policy
        └──────────────┴──────────────┴─────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────────────┐
        │  app/services/    orchestration (Phase 5+)    │  ← sequencing, I/O,
        └───────────────────────────────────────────────┘    failure isolation
                              │
                              ▼
        ┌───────────────────────────────────────────────┐
        │  app/domain/      pure models + calculations  │  ← Decimal, no I/O,
        └───────────────────────────────────────────────┘    deterministic

        app/core/    logging · errors   (cross-cutting, depends on nothing)
        app/config.py typed settings
```

Dependencies point **inward and downward only**. `domain` does no HTTP, reads no
environment variables, and imports nothing from `exchanges`, `services`, `fees`,
`tax` or `transfers`. That is what keeps the eventual arbitrage engine
exchange-agnostic and its financial functions unit-testable without a network.

### The eventual evaluation pipeline

Validation happens **before** profit, never after:

```
discover markets → normalise → validate route → validate network
   → validate withdrawal → validate deposit → check minimums
   → check liquidity → simulate order-book execution → calculate fees
   → calculate tax → calculate final INR → calculate net profit
```

### What exists today

| Module | Contents |
|---|---|
| `app/config.py` | `Settings`, `load_settings()`, `FinancialDecimal` |
| `app/core/errors.py` | `ApplicationError` → `ConfigurationError`, `ExchangeError`, `DataError`, `ValidationError` |
| `app/core/logging.py` | `configure_logging()`, `get_logger()`, `LogLevel` |
| `app/domain/money.py` | `parse_decimal()`, `AssetSymbol`, `Money` |
| `app/domain/known.py` | `UNKNOWN`, `NOT_APPLICABLE`, `is_known()`, `require_known()` |
| `app/main.py` | `main()`, `validate_startup()`, `build_startup_report()` |
| `app/exchanges/`, `app/services/`, `app/fees/`, `app/tax/`, `app/transfers/` | Documented boundaries only — no implementation |

`app/domain/market.py`, `route.py` and `opportunity.py` do **not** exist yet.
Their fields are determined by the real exchange payloads discovered in Phases
2–6; writing them now would mean committing to invented structure. See
[docs/decisions/0002-phase-0-domain-scope.md](docs/decisions/0002-phase-0-domain-scope.md).

---

## Architectural rules

These are binding. [AGENTS.md](AGENTS.md) is the full text.

| # | Rule |
|---|---|
| 1 | No live trading in V1. |
| 2 | No automatic withdrawals. |
| 3 | No automatic deposits. |
| 4 | No hardcoded asset whitelist — assets are discovered from live markets. |
| 5 | No fake or default financial assumptions. |
| 6 | `Decimal` for every financial calculation. |
| 7 | Order-book execution, not last-price arithmetic. |
| 8 | Network compatibility is **asset + network**, never asset alone. |
| 9 | Incomplete data means `UNKNOWN` / `DATA_UNAVAILABLE`, never an invented value. |
| 10 | Exchange-specific logic stays inside exchange adapters. |
| 11 | The arbitrage engine stays exchange-agnostic. |
| 12 | Correctness matters more than the number of detected opportunities. |

### Rule 6 in practice — why `float` is banned

`Decimal(0.1)` is `0.1000000000000000055511151231257827021181583404541015625`. An
exchange response parsed through a `float` has already lost the exact value the
exchange sent, before any fee is applied.

So `app.domain.money.parse_decimal()` is the single gate for incoming numeric
data, and it **rejects** `float` rather than converting it. This is enforced
three ways:

1. mypy strict — financial fields are annotated `Decimal`.
2. Ruff `RUF032` — flags `Decimal(<float literal>)`.
3. `tests/unit/test_decimal_discipline.py` — parses every module under `app/`
   with `ast` and fails on any float literal, any `float(...)` or `round(...)`
   call, and any `x or 0` fallback.

### Rule 9 in practice — `UNKNOWN` is not `0`

Three states must stay distinguishable for every financial input:

| Value | Meaning |
|---|---|
| `Decimal("0")` | verified to be zero |
| `UNKNOWN` | could not be verified — the route is **not** executable |
| `NOT_APPLICABLE` | the cost genuinely does not apply here |

`fee = api_fee or Decimal("0")` is the bug this prevents, so
`app.domain.known`'s sentinels raise `TypeError` on `bool()`: that idiom fails
loudly instead of fabricating a zero. Call `require_known()` at the point a value
must enter arithmetic.

---

## Planned phases

Phases are executed in order and one at a time. A phase is complete only when
its implementation exists, its tests exist and pass, limitations are documented,
and nothing unrelated was changed — not merely when the code runs.

| Phase | Scope | Status |
|---|---|---|
| **0** | Project initialization + architecture foundation | **current** |
| 1 | Exchange abstraction | planned |
| 2 | CoinDCX adapter | planned |
| 3 | KuCoin adapter | planned |
| 4 | Binance adapter | planned |
| 5 | Dynamic market discovery | planned |
| 6 | Market normalization | planned |
| 7 | Live ticker + order-book engine | planned |
| 8 | Trading-fee engine | planned |
| 9 | Deposit / withdrawal / network engine | planned |
| 10 | INR / USDT / USDC conversion | planned |
| 11 | India TDS / tax engine | planned |
| 12 | Order-book execution simulator | planned |
| 13 | Slippage engine | planned |
| 14 | Multi-exchange route engine | planned |
| 15 | Net INR profit engine | planned |
| 16 | Opportunity scanner | planned |
| 17 | Testing hardening | planned |
| 18 | Live read-only verification | planned |
| 19 | Final requirements audit | planned |

Future possibilities, explicitly **not** designed for yet: DEX / liquidity-source
abstraction, WebSocket market data, opportunity persistence and historical
analytics, alerting, portfolio management. Abstractions arrive with the phase
that needs them.

---

## Security

- No API keys, secrets, passwords or private keys in source. Ever.
- Configuration comes from environment variables; `.env` is git-ignored.
- `.env.example` contains placeholders only.
- Public endpoints are preferred. If an authenticated endpoint becomes necessary
  (e.g. an account-specific fee tier), it will be documented, use least
  privilege, and be read-only.
- **Withdrawal permission is never requested by this project.**

---

## Repository layout

```
.
├── AGENTS.md                 engineering constitution (normative)
├── README.md
├── .env.example              placeholders only — never real secrets
├── .gitignore
├── pyproject.toml            deps + pytest/ruff/mypy configuration
├── app/
│   ├── main.py               entry point: config → logging → validate → report
│   ├── config.py             typed settings (pydantic-settings)
│   ├── core/                 logging, errors
│   ├── domain/               pure Decimal-based models
│   ├── exchanges/            adapters (Phase 2-4)
│   ├── services/             orchestration (Phase 5+)
│   ├── fees/                 fee models (Phase 8-9)
│   ├── tax/                  TDS / tax policy (Phase 11)
│   └── transfers/            network / deposit / withdrawal (Phase 9)
├── docs/
│   ├── architecture/         layering, boundaries, pipeline
│   └── decisions/            architecture decision records
└── tests/
    ├── unit/                 deterministic, no network
    └── integration/          live read-only tests (empty in Phase 0)
```
