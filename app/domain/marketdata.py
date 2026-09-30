"""Market data an adapter reports: tickers and order books.

These are *transport-neutral results*, not venue payloads. Their fields come
from AGENTS.md §16-§17, which is normative for this project; none of them is a
guess about how CoinDCX, KuCoin or Binance shape a JSON response. Translating
those responses into these types is the job of each venue's adapter (Phases
2-4), and the engines that consume them arrive in Phases 7 and 12-13.

Prices and quantities are bare :class:`~decimal.Decimal`, not
:class:`~app.domain.money.Money`: the currency is already fixed structurally by
:attr:`OrderBook.market` — a price is in the market's quote currency, a quantity
is in its base asset. Repeating the currency per level would be redundant and
could disagree with the market it belongs to.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from app.domain.exchange import MarketRef
from app.domain.known import Maybe
from app.domain.money import parse_decimal, parse_maybe_decimal
from app.domain.provenance import DataProvenance

__all__ = ["OrderBook", "OrderBookLevel", "Ticker"]


def _require_matching_exchange(market: MarketRef, provenance: DataProvenance) -> None:
    """Reject a result whose provenance names a different venue than its market."""
    if provenance.exchange is not market.exchange:
        raise ValueError(
            f"provenance exchange {provenance.exchange.value} does not match "
            f"market exchange {market.exchange.value}"
        )


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    """One resting price level: ``quantity`` of the base asset offered at ``price``.

    Both values are exact Decimals. A level with a non-positive price or
    quantity is malformed data, not an empty level — an adapter that receives
    one must reject it rather than normalise it away.
    """

    price: Decimal
    quantity: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", parse_decimal(self.price, field="price"))
        object.__setattr__(
            self, "quantity", parse_decimal(self.quantity, field="quantity")
        )
        if self.price <= 0:
            raise ValueError(f"order-book level price must be positive, got {self.price}")
        if self.quantity <= 0:
            raise ValueError(
                f"order-book level quantity must be positive, got {self.quantity}"
            )

    @property
    def notional(self) -> Decimal:
        """``price * quantity`` — the quote-currency value resting at this level."""
        return self.price * self.quantity

    def __str__(self) -> str:
        return f"{self.quantity} @ {self.price}"


@dataclass(frozen=True, slots=True)
class OrderBook:
    """A depth snapshot of one market at one instant.

    ``bids`` descend in price and ``asks`` ascend, which is the order the Phase
    12 execution simulator consumes them in: a BUY walks ``asks``, a SELL walks
    ``bids`` (AGENTS.md §17). The ordering is validated on construction, because
    a mis-sorted book would silently produce a better-than-real average
    execution price.

    Either side may be empty. An empty side is verified absence of liquidity —
    genuine information, and the reason a route gets rejected as
    ``INSUFFICIENT_LIQUIDITY`` rather than being priced off the other side.

    Depth is whatever the adapter was asked for and the venue returned; this
    snapshot does not claim to be the complete book. Phase 12 must therefore
    treat exhausting the returned levels as insufficient depth, never as an
    excuse to extrapolate.
    """

    market: MarketRef
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    provenance: DataProvenance

    def __post_init__(self) -> None:
        _require_matching_exchange(self.market, self.provenance)
        object.__setattr__(self, "bids", tuple(self.bids))
        object.__setattr__(self, "asks", tuple(self.asks))
        _require_monotonic(self.bids, descending=True, side="bids")
        _require_monotonic(self.asks, descending=False, side="asks")

    @property
    def best_bid(self) -> OrderBookLevel | None:
        """Top of the bid side, or ``None`` when the side is empty.

        For inspection, logging and spread reporting only. AGENTS.md §17 and
        §83.13 forbid computing an opportunity from the top of book alone: the
        executable price at real capital comes from walking the levels.
        """
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> OrderBookLevel | None:
        """Top of the ask side, or ``None`` when the side is empty. See :attr:`best_bid`."""
        return self.asks[0] if self.asks else None

    def __str__(self) -> str:
        return f"{self.market} book({len(self.bids)} bids, {len(self.asks)} asks)"


def _require_monotonic(
    levels: tuple[OrderBookLevel, ...], *, descending: bool, side: str
) -> None:
    for previous, current in pairwise(levels):
        in_order = (
            previous.price > current.price if descending else previous.price < current.price
        )
        if not in_order:
            direction = "strictly descending" if descending else "strictly ascending"
            raise ValueError(
                f"order-book {side} must be {direction} in price; "
                f"got {previous.price} then {current.price}"
            )


@dataclass(frozen=True, slots=True)
class Ticker:
    """Top-of-book and last-trade summary for one market.

    Every price is :class:`~app.domain.known.Maybe` because a venue may simply
    not publish it. A missing bid is ``UNKNOWN``, never ``Decimal("0")``
    (AGENTS.md §63) — a zero bid would look like a real, catastrophic price.

    ``last`` is **informational only**. AGENTS.md §16 and §83.12 forbid using
    the last traded price as an execution price: it is a historical print, not
    something anyone can currently trade against. Execution prices come from
    :class:`OrderBook`.
    """

    market: MarketRef
    bid: Maybe[Decimal]
    ask: Maybe[Decimal]
    last: Maybe[Decimal]
    provenance: DataProvenance

    def __post_init__(self) -> None:
        _require_matching_exchange(self.market, self.provenance)
        for field in ("bid", "ask", "last"):
            value = parse_maybe_decimal(getattr(self, field), field=field)
            if isinstance(value, Decimal) and value <= 0:
                raise ValueError(f"ticker {field} must be positive, got {value}")
            object.__setattr__(self, field, value)

    def __str__(self) -> str:
        return f"{self.market} bid={self.bid} ask={self.ask} last={self.last}"
