"""Pure domain layer.

Rules for everything in this package:
  * no HTTP, no sockets, no exchange SDKs
  * no environment-variable or settings access
  * no dependency on ``app.exchanges``, ``app.services``, ``app.fees``,
    ``app.tax`` or ``app.transfers``
  * every financial value is ``decimal.Decimal`` — never ``float``
  * deterministic and directly unit-testable

The permitted inward dependency is ``app.core.errors``, which imports nothing
itself and therefore cannot create a cycle.

Modules present
---------------
Phase 0 — the financial primitives:

``money``
    ``parse_decimal``, ``parse_maybe_decimal``, ``AssetSymbol``, ``Money`` —
    the Decimal boundary.
``known``
    ``UNKNOWN`` / ``NOT_APPLICABLE`` sentinels enforcing the
    UNKNOWN-is-not-ZERO rule.

Phase 1 — the vocabulary the exchange adapter contract is expressed in:

``exchange``
    ``ExchangeId``, ``MarketRef`` — venue and market *identity*.
``provenance``
    ``DataSource``, ``DataProvenance`` — where a value came from, and when.
``marketdata``
    ``Ticker``, ``OrderBook``, ``OrderBookLevel``.
``fees``
    ``TradingFees`` as a venue reports them.
``transfer``
    ``NetworkInfo``, ``DepositInfo``, ``WithdrawalInfo``, keyed by asset AND
    network.

Every Phase 1 model above states only what a venue *reported*, with provenance,
and uses ``Maybe[...]`` for anything it may not report. None of them applies a
cost, decides executability or encodes a venue-specific payload shape.

Modules still deliberately absent
---------------------------------
``market`` (precision, status, limits, minimum notional), ``route`` and
``opportunity``. Their fields are determined by the real exchange payloads
discovered in Phases 2-6, and by how three different status and precision
vocabularies reconcile; writing them now would mean committing to speculative
fields. ``MarketRef`` is identity only, and Phase 6's ``MarketDefinition`` will
wrap it rather than replace it. See
``docs/decisions/0002-phase-0-domain-scope.md`` and
``docs/decisions/0003-phase-1-exchange-abstraction.md``.
"""
