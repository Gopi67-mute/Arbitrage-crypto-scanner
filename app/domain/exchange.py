"""Exchange and market *identity* — the vocabulary every layer shares.

This module answers "which venue?" and "which market?". It deliberately does
not answer "what are its precision rules, status vocabulary and limits?" — that
is :file:`docs/decisions/0002-phase-0-domain-scope.md`'s deferred
``MarketDefinition``, whose fields are determined by the real CoinDCX, KuCoin
and Binance payloads discovered in Phases 2-6.

Identity is separable from definition because identity is not payload-shaped:
every spot venue has a native symbol string that resolves to exactly one
(base, quote) pair. Phase 6 will wrap :class:`MarketRef`, not replace it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.money import AssetSymbol

__all__ = ["ExchangeId", "MarketRef"]


class ExchangeId(StrEnum):
    """The venues this scanner evaluates.

    An explicit enum, not a free string: a typo must fail at import time, and
    ``ExchangeId.COINDCX != ExchangeId.KUCOIN`` is the comparison that keeps a
    route's two legs from being confused.

    This is *not* the hardcoded-asset-list problem (AGENTS.md §9). Assets are
    discovered dynamically from live markets; venues are not discoverable and
    AGENTS.md §38 names this exact matrix. A fourth exchange costs one member
    here plus one adapter — no change to any generic engine.
    """

    COINDCX = "coindcx"
    KUCOIN = "kucoin"
    BINANCE = "binance"


@dataclass(frozen=True, slots=True)
class MarketRef:
    """Identifies one tradable spot market on one venue.

    ``XRP/INR`` on CoinDCX and ``XRP/USDT`` on KuCoin share a base asset and are
    *not* comparable prices (AGENTS.md §10, §11). Carrying ``quote`` structurally
    — rather than comparing symbol strings — is what makes that mistake
    impossible to write.

    ``symbol`` is the venue's own identifier, exactly as the venue spells it
    (``XRPINR``, ``XRP-USDT``, ``XRPUSDT``, …). It is **opaque**: generic code
    must never parse it, and two symbols from different venues must never be
    compared. It exists so an adapter can address its own API without a lookup
    table, which is why :meth:`ExchangeAdapter.require_market` rejects a
    ``MarketRef`` belonging to a different venue.

    Scope: spot markets only. V1 evaluates no futures or margin market, so no
    ``market_type`` field is invented here; Phase 6 adds one if normalising the
    three venues' market-type vocabularies turns out to require it.
    """

    exchange: ExchangeId
    base: AssetSymbol
    quote: AssetSymbol
    symbol: str

    def __post_init__(self) -> None:
        symbol = self.symbol.strip()
        if not symbol:
            raise ValueError("market symbol must not be empty")
        if self.base == self.quote:
            raise ValueError(
                f"market base and quote must differ, got {self.base} for both"
            )
        # Case is preserved: venue symbols are passed back to venue APIs verbatim.
        object.__setattr__(self, "symbol", symbol)

    @property
    def pair(self) -> str:
        """The human-readable pair, e.g. ``XRP/INR``. For display and logging."""
        return f"{self.base}/{self.quote}"

    def __str__(self) -> str:
        return f"{self.exchange.value}:{self.pair}"
