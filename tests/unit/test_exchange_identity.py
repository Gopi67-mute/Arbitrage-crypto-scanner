"""Exchange and market identity, and the provenance attached to every result."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.exchange import ExchangeId, MarketRef
from app.domain.money import AssetSymbol
from app.domain.provenance import DataProvenance, DataSource
from tests.unit.factories import FIXED_TIME, market, provenance


# --------------------------------------------------------------------------- #
# ExchangeId
# --------------------------------------------------------------------------- #
def test_the_three_phase_1_venues_are_represented():
    assert {member.value for member in ExchangeId} == {"coindcx", "kucoin", "binance"}


def test_exchange_ids_are_distinct_and_comparable():
    assert ExchangeId.COINDCX != ExchangeId.KUCOIN
    assert ExchangeId("binance") is ExchangeId.BINANCE


def test_exchange_id_rejects_an_unknown_venue():
    """A typo must fail loudly rather than become a new silent venue."""
    with pytest.raises(ValueError):
        ExchangeId("coindxc")


# --------------------------------------------------------------------------- #
# MarketRef
# --------------------------------------------------------------------------- #
def test_market_ref_keeps_quote_currency_structural():
    """XRP/INR and XRP/USDT share a base asset and are not the same market."""
    inr = market(quote="INR", symbol="XRPINR")
    usdt = market(quote="USDT", symbol="XRPUSDT")

    assert inr != usdt
    assert inr.base == usdt.base
    assert inr.quote != usdt.quote


def test_same_pair_on_two_venues_is_two_markets():
    coindcx = market(exchange=ExchangeId.COINDCX)
    kucoin = market(exchange=ExchangeId.KUCOIN, symbol="XRP-INR")

    assert coindcx != kucoin


def test_market_ref_is_frozen_and_hashable():
    ref = market()

    assert {ref, market()} == {ref}
    with pytest.raises(AttributeError):
        ref.symbol = "OTHER"  # type: ignore[misc]


def test_market_ref_preserves_the_venue_symbol_verbatim():
    """The symbol is passed back to the venue's API, so its case must survive."""
    assert market(symbol="XRP-usdt").symbol == "XRP-usdt"


def test_market_ref_strips_surrounding_whitespace_from_symbol():
    assert market(symbol="  XRPINR  ").symbol == "XRPINR"


def test_market_ref_rejects_an_empty_symbol():
    with pytest.raises(ValueError, match="symbol must not be empty"):
        market(symbol="   ")


def test_market_ref_rejects_identical_base_and_quote():
    with pytest.raises(ValueError, match="base and quote must differ"):
        market(base="USDT", quote="USDT", symbol="USDTUSDT")


def test_market_ref_renders_venue_and_pair():
    assert str(market()) == "coindcx:XRP/INR"
    assert market().pair == "XRP/INR"


def test_market_ref_normalises_asset_case_through_asset_symbol():
    ref = MarketRef(
        exchange=ExchangeId.KUCOIN,
        base=AssetSymbol("xrp"),
        quote=AssetSymbol("usdt"),
        symbol="XRP-USDT",
    )

    assert ref.pair == "XRP/USDT"


# --------------------------------------------------------------------------- #
# DataProvenance
# --------------------------------------------------------------------------- #
def test_provenance_records_source_reference_and_time():
    record = provenance()

    assert record.exchange is ExchangeId.COINDCX
    assert record.source is DataSource.LIVE_API
    assert record.reference == "/exchange/v1/markets_details"
    assert record.retrieved_at == FIXED_TIME


def test_live_data_is_distinguishable_from_documented_data():
    """A figure transcribed from docs must never be presented as live."""
    live = provenance(source=DataSource.LIVE_API)
    documented = provenance(
        source=DataSource.OFFICIAL_DOCUMENTATION, reference="https://docs.example/fees"
    )
    configured = provenance(
        source=DataSource.STATIC_CONFIGURATION, reference="COINDCX_TAKER_FEE"
    )

    assert live.is_live
    assert not documented.is_live
    assert not configured.is_live


def test_provenance_requires_a_reference():
    with pytest.raises(ValueError, match="reference must not be empty"):
        provenance(reference="  ")


def test_provenance_rejects_a_naive_timestamp():
    """Naive timestamps cannot be compared across venues (AGENTS.md §40)."""
    with pytest.raises(ValueError, match="must be timezone-aware"):
        provenance(retrieved_at=datetime(2026, 9, 30, 9, 15, 0))


def test_provenance_accepts_a_non_utc_timezone():
    ist = timezone(timedelta(hours=5, minutes=30))
    record = provenance(retrieved_at=datetime(2026, 9, 30, 14, 45, 0, tzinfo=ist))

    assert record.retrieved_at.astimezone(UTC) == FIXED_TIME


def test_provenance_is_frozen():
    record = provenance()

    with pytest.raises(AttributeError):
        record.source = DataSource.STATIC_CONFIGURATION  # type: ignore[misc]


def test_provenance_renders_all_four_facts():
    rendered = str(provenance())

    assert "coindcx" in rendered
    assert "live_api" in rendered
    assert "markets_details" in rendered
    assert "2026-09-30T09:15:00+00:00" in rendered


def test_data_source_values_are_explicit():
    assert {member.value for member in DataSource} == {
        "live_api",
        "official_documentation",
        "static_configuration",
    }


def test_provenance_type_is_reusable_across_venues():
    assert provenance(exchange=ExchangeId.BINANCE).exchange is ExchangeId.BINANCE


def test_two_identical_provenance_records_compare_equal():
    assert DataProvenance(
        exchange=ExchangeId.KUCOIN,
        source=DataSource.LIVE_API,
        reference="/api/v2/symbols",
        retrieved_at=FIXED_TIME,
    ) == DataProvenance(
        exchange=ExchangeId.KUCOIN,
        source=DataSource.LIVE_API,
        reference="/api/v2/symbols",
        retrieved_at=FIXED_TIME,
    )
