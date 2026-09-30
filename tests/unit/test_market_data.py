"""Ticker and order-book models: exact Decimals, honest gaps, correct ordering."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.exchange import ExchangeId
from app.domain.known import NOT_APPLICABLE, UNKNOWN, is_known
from app.domain.marketdata import OrderBook, OrderBookLevel, Ticker
from tests.unit.factories import market, provenance


def level(price: str, quantity: str) -> OrderBookLevel:
    return OrderBookLevel(price=Decimal(price), quantity=Decimal(quantity))


def book(bids=(), asks=(), ref=None):
    ref = market() if ref is None else ref
    return OrderBook(
        market=ref,
        bids=tuple(bids),
        asks=tuple(asks),
        provenance=provenance(exchange=ref.exchange),
    )


# --------------------------------------------------------------------------- #
# OrderBookLevel
# --------------------------------------------------------------------------- #
def test_level_keeps_the_exact_decimal_the_venue_sent():
    parsed = OrderBookLevel(price="49.8700", quantity="150.0")  # type: ignore[arg-type]

    assert parsed.price == Decimal("49.8700")
    assert str(parsed.price) == "49.8700", "trailing precision is itself information"


def test_level_rejects_a_float_price():
    with pytest.raises(ValueError, match="float is forbidden"):
        OrderBookLevel(price=49.87, quantity=Decimal("1"))  # type: ignore[arg-type]


def test_level_rejects_a_float_quantity():
    with pytest.raises(ValueError, match="float is forbidden"):
        OrderBookLevel(price=Decimal("49.87"), quantity=1.5)  # type: ignore[arg-type]


@pytest.mark.parametrize("price", ["0", "-1"])
def test_level_rejects_a_non_positive_price(price):
    with pytest.raises(ValueError, match="price must be positive"):
        level(price, "1")


@pytest.mark.parametrize("quantity", ["0", "-1"])
def test_level_rejects_a_non_positive_quantity(quantity):
    with pytest.raises(ValueError, match="quantity must be positive"):
        level("10", quantity)


def test_level_notional_is_exact_decimal_arithmetic():
    assert level("0.1", "3").notional == Decimal("0.3")


# --------------------------------------------------------------------------- #
# OrderBook ordering — the invariant the execution simulator relies on
# --------------------------------------------------------------------------- #
def test_book_accepts_correctly_sorted_sides():
    snapshot = book(
        bids=[level("100", "2"), level("99", "5")],
        asks=[level("101", "2"), level("102", "10")],
    )

    assert snapshot.best_bid == level("100", "2")
    assert snapshot.best_ask == level("101", "2")


def test_book_rejects_bids_that_are_not_descending():
    """A mis-sorted book would yield a better-than-real average execution price."""
    with pytest.raises(ValueError, match="bids must be strictly descending"):
        book(bids=[level("99", "1"), level("100", "1")])


def test_book_rejects_asks_that_are_not_ascending():
    with pytest.raises(ValueError, match="asks must be strictly ascending"):
        book(asks=[level("102", "1"), level("101", "1")])


def test_book_rejects_duplicate_price_levels():
    with pytest.raises(ValueError, match="strictly descending"):
        book(bids=[level("100", "1"), level("100", "2")])


def test_an_empty_side_is_valid_and_means_no_liquidity():
    """Verified absence of liquidity is data, not an error and not a zero price."""
    snapshot = book(bids=[level("100", "1")], asks=[])

    assert snapshot.asks == ()
    assert snapshot.best_ask is None
    assert snapshot.best_bid is not None


def test_a_completely_empty_book_is_valid():
    snapshot = book()

    assert snapshot.best_bid is None
    assert snapshot.best_ask is None


def test_book_normalises_sequences_to_tuples():
    snapshot = OrderBook(
        market=market(),
        bids=[level("100", "1")],  # type: ignore[arg-type]
        asks=[],  # type: ignore[arg-type]
        provenance=provenance(),
    )

    assert isinstance(snapshot.bids, tuple)


def test_book_rejects_provenance_from_another_venue():
    """Guards against pricing one leg of a route against the wrong venue."""
    with pytest.raises(ValueError, match="does not match market exchange"):
        OrderBook(
            market=market(exchange=ExchangeId.COINDCX),
            bids=(),
            asks=(),
            provenance=provenance(exchange=ExchangeId.KUCOIN),
        )


def test_book_carries_the_retrieval_time_for_the_staleness_gate():
    assert book().provenance.retrieved_at.tzinfo is not None


# --------------------------------------------------------------------------- #
# Ticker
# --------------------------------------------------------------------------- #
def test_ticker_holds_exact_decimals():
    ticker = Ticker(
        market=market(),
        bid=Decimal("49.87"),
        ask=Decimal("49.92"),
        last=Decimal("49.90"),
        provenance=provenance(),
    )

    assert ticker.bid == Decimal("49.87")
    assert isinstance(ticker.last, Decimal)


def test_a_missing_ticker_price_is_unknown_not_zero():
    """A zero bid would look like a real, catastrophic price (AGENTS.md §63)."""
    ticker = Ticker(
        market=market(), bid=UNKNOWN, ask=UNKNOWN, last=UNKNOWN, provenance=provenance()
    )

    assert ticker.bid is UNKNOWN
    assert ticker.bid != Decimal("0")
    assert not is_known(ticker.bid)


def test_unknown_ticker_price_cannot_be_or_defaulted_to_zero():
    ticker = Ticker(
        market=market(), bid=UNKNOWN, ask=UNKNOWN, last=UNKNOWN, provenance=provenance()
    )

    with pytest.raises(TypeError, match="never fall back to zero"):
        _ = ticker.bid or Decimal("0")


def test_ticker_accepts_not_applicable_separately_from_unknown():
    ticker = Ticker(
        market=market(),
        bid=Decimal("49.87"),
        ask=Decimal("49.92"),
        last=NOT_APPLICABLE,
        provenance=provenance(),
    )

    assert ticker.last is NOT_APPLICABLE
    assert ticker.last is not UNKNOWN


def test_ticker_rejects_a_float_price():
    with pytest.raises(ValueError, match="float is forbidden"):
        Ticker(
            market=market(),
            bid=49.87,  # type: ignore[arg-type]
            ask=UNKNOWN,
            last=UNKNOWN,
            provenance=provenance(),
        )


def test_ticker_rejects_a_non_positive_price():
    with pytest.raises(ValueError, match="bid must be positive"):
        Ticker(
            market=market(),
            bid=Decimal("0"),
            ask=UNKNOWN,
            last=UNKNOWN,
            provenance=provenance(),
        )


def test_ticker_rejects_provenance_from_another_venue():
    with pytest.raises(ValueError, match="does not match market exchange"):
        Ticker(
            market=market(exchange=ExchangeId.BINANCE, symbol="XRPUSDT", quote="USDT"),
            bid=UNKNOWN,
            ask=UNKNOWN,
            last=UNKNOWN,
            provenance=provenance(exchange=ExchangeId.KUCOIN),
        )
