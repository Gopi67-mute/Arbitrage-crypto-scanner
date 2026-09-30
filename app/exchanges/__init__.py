"""Exchange adapters (Phase 1+). Empty by design in Phase 0.

Planned contents:

    base.py       the exchange-agnostic adapter interface + capability model
    coindcx.py    CoinDCX adapter
    kucoin.py     KuCoin adapter
    binance.py    Binance adapter

Boundary rules:
  * ALL exchange-specific API knowledge lives here and nowhere else. No
    ``if exchange == "kucoin":`` anywhere in generic code (AGENTS.md §8).
  * An adapter translates an exchange payload into normalised domain models; it
    does not calculate fees, taxes, routes or profit.
  * Capabilities are explicit. An exchange that cannot supply a value reports
    UNKNOWN (``app.domain.known``); it never fabricates one.
  * Read-only. No adapter will ever expose order placement, withdrawal, deposit
    or transfer operations.

No adapter exists yet, and no networking code is present anywhere in the
package. Phase 0 makes zero API calls.
"""
