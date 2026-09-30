# ADR 0003 — The Phase 1 exchange abstraction

- **Status:** accepted
- **Phase:** 1
- **Date:** 2026-09-30

## Context

Phase 1 defines the contract that the CoinDCX, KuCoin and Binance adapters
(Phases 2–4) will implement:

```
arbitrage engine  →  ExchangeAdapter  →  CoinDCX | KuCoin | Binance
```

Its purpose is AGENTS.md §6–§8: keep every venue-specific detail behind one
interface so that generic code never branches on which exchange it is talking
to, and a fourth venue costs one adapter rather than an engine rewrite.

Phase 1 implements **no venue**. It makes no HTTP request, imports no HTTP
client, and defines no credential.

## Decision 1 — The interface is asynchronous

`ExchangeAdapter`'s seven data operations are `async def`.

A scan's cost is almost entirely time spent waiting on three venues' HTTP
endpoints. The decisive constraint is AGENTS.md §40: a route compares two legs,
and those legs must be sampled inside one bounded freshness window. Sequential
I/O widens that window by the *sum* of the venues' latencies, which directly
worsens the thing `MAX_DATA_AGE_SECONDS` exists to bound — it is a correctness
problem, not only a speed one.

`asyncio` rather than threads: the work is I/O-bound, the concurrency limits and
`Retry-After` backoff that §41 requires are easier to express with async
primitives, and `httpx` (pinned in Phase 0, ADR 0001) supports both styles from
one API. `pytest-asyncio` is already configured in `strict` mode.

Cost: every caller up the stack becomes async. Accepted — the orchestration
layer that would be affected (Phase 5+) does not exist yet, so this is the
cheapest moment to decide it.

The pure helpers (`supports`, `require_capability`, `require_market`) stay
synchronous. They compute, they do not wait.

## Decision 2 — Capabilities are a `frozenset` on the adapter

`ExchangeCapability` is a `StrEnum` with one member per read operation, and each
adapter exposes a `frozenset` of the ones it can answer. `require_capability()`
raises `UnsupportedCapabilityError` for the rest.

This is deliberately not a framework: no registry, no descriptor objects, no
dynamic dispatch. An adapter declares a set; the base class checks membership.

Each member's **value is the name of the method it gates**
(`GET_TICKER = "get_ticker"`). That keeps the enum and the contract from
drifting, and `tests/unit/test_exchange_adapter.py` asserts the correspondence
in both directions — adding a method without a capability, or the reverse,
fails the suite.

### Why this does not duplicate `UNKNOWN`

Three states must stay distinct, and Phase 1 keeps them in three different
mechanisms:

| State | Meaning | Mechanism |
|---|---|---|
| capability absent | the venue has no such endpoint; it was never obtainable | `UnsupportedCapabilityError` |
| `UNKNOWN` | the endpoint answered, but this value could not be verified | `app.domain.known` |
| `NOT_APPLICABLE` | the endpoint answered, and the value genuinely does not apply | `app.domain.known` |

Collapsing any two of these is the failure AGENTS.md §62–§63 exists to prevent.
Phase 1 therefore reuses the Phase 0 sentinels for missing *data* and introduces
a capability set only for missing *operations*. No second unknown-data mechanism
was created.

## Decision 3 — Unavailable data is `Maybe[...]`, never an exception

Every field an adapter might not be able to fill is typed `Maybe[T]`: both
trading-fee rates, every withdrawal and deposit figure, every availability flag,
every ticker price.

"The endpoint worked but this value is not published" is ordinary, expected
data, not a failure. Raising for it would push callers toward a `try/except`
that swallows the distinction and substitutes a zero — exactly AGENTS.md §64.
`DataError` remains for the moment a caller *demands* such a value through
`require_known()`.

Because the sentinels raise on `bool()`, `fee = api_fee or Decimal("0")` and
`if deposit_enabled:` both fail loudly rather than silently reading UNKNOWN as
zero or as "disabled".

## Decision 4 — Five adapter errors, all under `ExchangeError`

`app/exchanges/errors.py` adds exactly the distinctions the scanner must act on:
`UnsupportedCapabilityError`, `InvalidExchangeRequestError`,
`ExchangeTimeoutError`, `ExchangeRateLimitError` (both under a shared
`ExchangeTransportError`), and `MalformedExchangeResponseError`.

All extend the existing `app.core.errors.ExchangeError`, so `except
ExchangeError` in the Phase 5+ scanner isolates one venue's failure without
aborting the scan (§42), while a caller that needs to tell a timeout from a rate
limit can. Timeout and rate limit are separated because the correct response
differs: retry versus back off and respect `Retry-After` (§41).

They live in `app/exchanges/` rather than `app/core/errors.py` to keep `core`
free of layer-specific knowledge. No error carries a recovery default.

## Decision 5 — No new configuration in Phase 1

`REQUEST_TIMEOUT_SECONDS` and `MAX_RETRIES` were **not** added.

The Phase 1 contract performs no I/O, so nothing in it reads a timeout. Adding
the settings now would mean choosing values before seeing a real venue's
latency and rate-limit behaviour, and `app/config.py` already states the
project's rule: settings belonging to later engines are added by the phase that
needs them. Phase 2 adds them, with values justified against a real endpoint.

## Decision 6 — Which domain types Phase 1 creates, and which it still defers

An interface whose methods return nothing typed is not a contract, so Phase 1
creates the result models. The line drawn is:

> Model what **AGENTS.md** normatively requires. Defer what a **venue payload**
> determines.

**Created** (`app/domain/`): `ExchangeId`, `MarketRef`, `DataSource`,
`DataProvenance`, `Ticker`, `OrderBook`, `OrderBookLevel`, `TradingFees`,
`NetworkInfo`, `DepositInfo`, `WithdrawalInfo`.

Every field traces to a normative section — §16–§17 for market data, §20 for
fees, §21–§27 for transfers, §39 and §44 for provenance — not to an assumption
about how any exchange shapes its JSON. None of these is a CoinDCX, KuCoin or
Binance response model.

Two properties make them robust to what Phases 2–4 actually discover:

1. **Optional fields are `Maybe[...]`.** A venue that does not publish a
   confirmation count or a withdrawal cap is representable today, honestly,
   without changing the model.
2. **Later phases extend rather than replace.** Adding a field to a frozen
   dataclass is additive; it is not the broad rewrite AGENTS.md §4 prohibits.

**Still deferred**, consistent with [ADR 0002](0002-phase-0-domain-scope.md):

- `MarketDefinition` — price/quantity precision, status vocabulary, minimum
  quantity, maximum quantity, minimum notional. These are exactly the fields
  whose shape depends on reconciling three venues' conventions, which is Phase
  6's job. `MarketRef` carries **identity only** (exchange, base, quote, native
  symbol), and Phase 6's `MarketDefinition` will *wrap* it, not replace it.
- `market_type` — V1 is spot-only; inventing an enum with one member now would
  be speculative.
- Cross-venue network normalisation. `NetworkInfo.network` holds the venue's own
  code, whitespace-stripped and otherwise untouched. Deciding that CoinDCX's
  spelling and KuCoin's spelling denote the same chain is Phase 9's job and
  cannot be done correctly without seeing all three. Until then these codes are
  venue-local and must not be compared across venues.
- `route.py`, `opportunity.py`, and every engine.
- `effective_at` and a verification-status field on `DataProvenance` — they
  matter for static fee schedules and tax rules, and belong to Phases 8/9 and 11
  with real dated sources.
- Adapter lifecycle (`close()` / async context manager). Phase 1 owns no
  resources, and whether the HTTP client is owned by the adapter or injected
  into it should be decided against a real transport in Phase 2. Adding it later
  is additive.

## Decision 7 — Read-only is enforced, not merely documented

The contract has no method to place or cancel an order, withdraw, deposit,
transfer funds, or read a balance, and none will be added: execution, if ever
built, is a separate approved phase with its own interface (AGENTS.md §2, §83).

`get_deposit_info` and `get_withdrawal_info` are reads *about* transfer
constraints. They report what a venue charges and permits; they move nothing.

This is enforced three ways in `tests/unit/test_exchange_adapter.py`: no
forbidden member name exists on the class, no capability authorises one, and the
class's public surface is asserted to equal the documented set — so a new public
method is a deliberate, reviewed contract change rather than an accident.

## Consequences

- Phase 2 can implement `ExchangeAdapter` for CoinDCX without any further
  interface design, and without touching a generic engine.
- Both route directions and every quote currency are supported structurally:
  `MarketRef` carries `quote`, so `XRP/INR` and `XRP/USDT` cannot be compared by
  accident, and no direction is privileged anywhere in the contract.
- Every adapter result carries provenance, so the Phase 5+ staleness gate and
  the §65 route-confidence model can be built without retrofitting timestamps.
- One Phase 0 test was intentionally replaced. `test_no_exchange_adapter_module_exists_yet`
  asserted that `app/exchanges/` contained only `__init__.py`, which Phase 1
  invalidates by design. The property that mattered — no venue implementation and
  no API call — is preserved by
  `test_startup_still_makes_no_exchange_call_in_phase_1` and, more strictly, by
  `test_no_venue_adapter_module_exists_yet` and
  `test_importing_the_contract_pulls_in_no_http_client`. No assertion was
  weakened and no coverage was lost.
- `parse_maybe_decimal()` was added to `app/domain/money.py` so that optionality
  cannot become a loophole in the Decimal rule: a `float` is rejected whether or
  not the field was optional.
