# Architecture overview

Normative source: [AGENTS.md](../../AGENTS.md). This document explains the
layering the code establishes and why the boundaries sit where they do.

Status: written in Phase 0. Layers below Phase 0 are described as intent, not as
existing code.

---

## 1. Layers

| Layer | Package | Responsibility | May depend on |
|---|---|---|---|
| Entry point | `app/main.py` | start up, validate, report, exit | everything |
| Configuration | `app/config.py` | typed settings from env / `.env` | `core`, `domain` |
| Cross-cutting | `app/core/` | logging, error hierarchy | nothing in-project |
| Adapters | `app/exchanges/` | venue APIs → normalised domain models | `core`, `domain` |
| Cost policy | `app/fees/`, `app/tax/`, `app/transfers/` | fees, tax, transfer constraints | `core`, `domain` |
| Orchestration | `app/services/` | sequencing, concurrency, failure isolation | all of the above |
| Domain | `app/domain/` | pure models + deterministic calculations | `core.errors` only |

The dependency graph points inward and downward. `app/core/errors.py` imports
nothing, so the single inward edge from `domain` to it cannot create a cycle.

```
 exchanges ──┐
 fees ───────┤
 tax ────────┼──► services ──► domain ──► core.errors
 transfers ──┘                    ▲
                                  │
                            config ┘
```

### Why `domain` is sealed

`domain` must not do HTTP, must not read environment variables, and must not
import any adapter. Two consequences follow, and both are the point:

1. **The arbitrage engine stays exchange-agnostic.** There is never an
   `if exchange == "kucoin":` in generic logic (AGENTS.md §8). Adding a fourth
   exchange must not require touching route or profit code.
2. **Financial calculations are testable without a network.** Given inputs, a
   pure function returns a result. Unit tests therefore never depend on a live
   exchange (AGENTS.md §49, §50).

### Why adapters are thick and the engine is thin

Everything venue-specific lives in one adapter: symbol formats, pagination, rate
limit headers, network naming, precision rules, which endpoint exposes a
withdrawal fee. An adapter *translates*; it does not calculate fees, taxes,
routes or profit. Adding an exchange means writing one adapter, not editing the
engine.

This is also why CCXT is not used. A generic wrapper normalises away exactly the
deposit/withdrawal/network/minimum metadata that decides whether a route is
actually executable.

---

## 2. Separation of concerns

These stay in separate modules, in this order:

```
Exchange API → Normalization → Market data → Execution simulation
   → Transfer validation → Fee calculation → Tax calculation
   → Quote conversion → Route calculation → Opportunity evaluation → Reporting
```

Specifically:

- API calls never happen inside a financial calculation function.
- Tax policy never lives inside an exchange client: a client reports what the
  venue returned, a tax module encodes jurisdiction rules (AGENTS.md §30).
- CLI formatting never mixes with financial calculation.

---

## 3. Evaluation pipeline — validation precedes profit

```
discover markets
  → normalise markets
  → validate route
  → validate network (asset + network, both directions)
  → validate withdrawal
  → validate deposit
  → validate minimums
  → check liquidity
  → simulate order-book execution
  → calculate fees
  → calculate tax
  → calculate final INR
  → calculate net profit
```

A promising-looking spread is never computed first and validated afterwards
(AGENTS.md §36). A route that fails any gate is rejected with a machine-readable
status, and the reason is always logged (AGENTS.md §55, §56).

---

## 4. Financial correctness invariants

These four invariants shape the whole codebase.

### 4.1 Decimal only

`decimal.Decimal` for prices, quantities, balances, fees, taxes, spreads,
slippage, profit and ROI. `float` never touches a financial value, not even
transiently while parsing a response — `Decimal(0.1)` is already wrong.

`app.domain.money.parse_decimal()` is the single entry gate for external numeric
data. It accepts `str`, `int` and `Decimal`; it rejects `float`, `bool`, `NaN`,
infinities and unparseable text. It preserves trailing zeros, because the
precision an exchange sends is itself information.

Enforcement is layered: mypy strict on annotations, Ruff `RUF032` on
`Decimal(<float>)`, and an AST scan over all of `app/` in
`tests/unit/test_decimal_discipline.py`.

`float` remains permitted for timing and network values (timeouts, elapsed time)
provided they never reach a financial calculation. No such value exists in
Phase 0.

### 4.2 UNKNOWN is not ZERO

| Value | Meaning |
|---|---|
| `Decimal("0")` | verified zero |
| `UNKNOWN` | unverifiable — route is not executable |
| `NOT_APPLICABLE` | verified not to apply |

Missing financial data stays missing. `app.domain.known`'s sentinels raise
`TypeError` on `bool()`, so `fee = api_fee or Decimal("0")` fails loudly rather
than fabricating a zero. `require_known()` is the intended way to demand a value
before arithmetic; it raises `DataError` rather than defaulting.

### 4.3 Asset + network, not asset

A transfer is identified by `ASSET + NETWORK`. `USDT-TRC20` and `USDT-ERC20` are
different transfer routes with different fees, minimums, confirmation times and
availability. `USDT → USDT` implies nothing about transferability.

A transfer is executable only when the source supports the asset/network **and**
the destination supports it **and** withdrawal is enabled **and** deposit is
enabled **and** every minimum is satisfied **and** any required memo/tag is
verified.

### 4.4 Quote currency is structural

`XRP/INR` and `XRP/USDT` share a base asset and are not comparable prices. A
market is `base_asset + quote_asset + exchange + symbol + market_type + status +
precision + limits`, never a string. Converting between quote currencies is a
real economic operation with spread, depth, slippage, fees and tax — not a
multiplication.

---

## 5. Data freshness

Every market-data object carries a timestamp, and `MAX_DATA_AGE_SECONDS` bounds
how old critical data may be. A fresh order book from one venue is never compared
against a stale one from another and called current; route evaluation uses a
bounded data-age window, and data that is too old yields `STALE_DATA` rather than
an opportunity.

---

## 6. Failure isolation

Exchange APIs are treated as rate-limited, partially available systems. One
failed market must never abort a scan. Timeouts, HTTP errors, rate limits,
`Retry-After`, bounded retries with backoff, concurrency limits, malformed
responses and partial results are represented explicitly and logged — never
silently swallowed, and never turned into a zero.

---

## 7. Deliberately deferred

Introduced only by the phase that needs them:

| Deferred | Reason |
|---|---|
| `domain/market.py`, `route.py`, `opportunity.py` | fields are determined by real exchange payloads (Phases 2–6); see [ADR 0002](../decisions/0002-phase-0-domain-scope.md) |
| Fee, tax, transfer models | require verified live data and cited sources |
| Order-book simulator, slippage, route, profit engines | Phases 12–15 |
| WebSockets | REST suffices; not "more advanced", just different trade-offs |
| Database | V1 keeps models persistence-friendly without the infrastructure |
| DEX / `LiquiditySource` abstraction | not until the centralized scanner is correct |
| Alerting, portfolio management, historical analytics | out of V1 scope |

Rounding policy is also deferred: `Money` deliberately has no division and no
rounding, because the correct precision and rounding mode come from exchange
metadata discovered in Phase 6. Guessing them now would bake in a wrong
assumption.
