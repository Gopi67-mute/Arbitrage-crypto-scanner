# ADR 0002 — What the Phase 0 domain layer does and does not contain

- **Status:** accepted
- **Phase:** 0
- **Date:** 2026-09-29

## Context

The Phase 0 brief sketches a domain package containing `market.py`, `money.py`,
`route.py` and `opportunity.py`. The same brief also says the structure is
"a proposed boundary, not permission to create unnecessary placeholder code" and
"do not create fake implementations merely to populate directories". AGENTS.md
§47 adds: "do not create models that exist only to satisfy a speculative future
feature", and §84 resolves ties in favour of an explicit architectural decision
over premature implementation.

Those two readings conflict for three of the four files, so the conflict is
recorded here rather than resolved silently.

## Decision

**Created in Phase 0** — concepts that are fundamental, already needed, and
whose shape does not depend on any exchange payload:

| Module | Contents | Why now |
|---|---|---|
| `domain/money.py` | `parse_decimal()`, `AssetSymbol`, `Money` | The Decimal boundary is the project's cardinal rule (AGENTS.md §14). It is used by `config.py` today, and having it under test now prevents float from entering anywhere later. |
| `domain/known.py` | `UNKNOWN`, `NOT_APPLICABLE`, `is_known()`, `require_known()` | The UNKNOWN-is-not-ZERO rule (§62–§64) is the one invariant every later engine must obey. Establishing the type now makes the banned `x or Decimal(0)` idiom fail at runtime rather than depending on review vigilance. |

**Not created in Phase 0** — `domain/market.py`, `domain/route.py`,
`domain/opportunity.py`.

## Rationale for the omission

A `MarketDefinition` needs `base_asset`, `quote_asset`, `market_type`, `status`,
`price_precision`, `quantity_precision`, `minimum_quantity`, `maximum_quantity`
and `minimum_notional`. Every one of those fields is shaped by what CoinDCX,
KuCoin and Binance actually return, and by how their three different status
vocabularies and precision conventions reconcile. That is Phase 6's job
(market normalization), informed by Phases 2–4.

Writing those models now would mean inventing the structure, and then either
carrying wrong fields forward or rewriting them in Phase 6 — the "broad rewrite"
AGENTS.md §4 exists to prevent. A file containing only a docstring or a bare
`class Route: ...` would be placeholder code of exactly the kind the brief
prohibits, and would falsely signal that the model had been designed.

`Money` also deliberately omits division, rounding and currency conversion, for
the same reason: the correct precision and rounding mode come from exchange
metadata, and conversion between quote currencies is a real economic operation
(order book + spread + slippage + fees + tax), not an arithmetic operator.

## Where the boundary is recorded instead

The layering intent is not lost by omitting the files:

- `app/domain/__init__.py` documents the domain rules and names the deferred
  modules explicitly.
- `app/exchanges/`, `app/services/`, `app/fees/`, `app/tax/` and
  `app/transfers/` each carry a module docstring stating their responsibility,
  their boundary rules and the phase that fills them.
- `docs/architecture/overview.md` records the dependency direction and the
  evaluation pipeline.

## Consequences

- Phase 0 ships no speculative model and no field that has not been verified
  against a real exchange response.
- Phase 6 designs `MarketDefinition` against real payloads from three venues
  rather than against a Phase 0 guess.
- `app/domain/` currently has two modules rather than four. This is intentional
  and is the reason this ADR exists.

## If this is not wanted

This is the one place where Phase 0 deviates from the literal file list in the
brief. If the intent was to create the three files as documented stubs, say so
and they will be added as docstring-only modules describing their planned fields
— without invented attributes.
