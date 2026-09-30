"""Exchange adapters: the seam between venue APIs and the generic engine.

Contents (Phase 1)
------------------
``base.py``
    ``ExchangeAdapter`` — the abstract read-only contract every venue implements.
``capabilities.py``
    ``ExchangeCapability`` — what an adapter declares it can answer.
``errors.py``
    The failures an adapter may raise, all under ``core.errors.ExchangeError``.

Planned
-------
``coindcx.py`` (Phase 2), ``kucoin.py`` (Phase 3), ``binance.py`` (Phase 4).
None exists yet, and no module in this package imports an HTTP client or
defines a credential.

Boundary rules
--------------
  * ALL exchange-specific API knowledge lives here and nowhere else. No
    ``if exchange == "kucoin":`` anywhere in generic code (AGENTS.md §8).
  * An adapter translates an exchange payload into normalised domain models; it
    does not calculate fees, taxes, routes or profit.
  * Capabilities are explicit. An exchange that cannot supply a value reports
    UNKNOWN (``app.domain.known``); it never fabricates one. A capability the
    adapter does not declare raises, rather than returning an empty result.
  * Read-only. No adapter will ever expose order placement, cancellation,
    withdrawal, deposit, transfer or balance operations.
"""
