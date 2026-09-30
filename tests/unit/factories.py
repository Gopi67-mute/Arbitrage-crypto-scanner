"""Deterministic builders for the Phase 1 domain models.

Not a fixture module and not collected as tests. Everything here is fixed data:
no clock, no randomness, no network. The timestamp is a constant so that a test
asserting on provenance cannot pass or fail depending on when it ran.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.exchange import ExchangeId, MarketRef
from app.domain.money import AssetSymbol
from app.domain.provenance import DataProvenance, DataSource

FIXED_TIME = datetime(2026, 9, 30, 9, 15, 0, tzinfo=UTC)


def market(
    exchange: ExchangeId = ExchangeId.COINDCX,
    base: str = "XRP",
    quote: str = "INR",
    symbol: str = "XRPINR",
) -> MarketRef:
    return MarketRef(
        exchange=exchange,
        base=AssetSymbol(base),
        quote=AssetSymbol(quote),
        symbol=symbol,
    )


def provenance(
    exchange: ExchangeId = ExchangeId.COINDCX,
    source: DataSource = DataSource.LIVE_API,
    reference: str = "/exchange/v1/markets_details",
    retrieved_at: datetime = FIXED_TIME,
) -> DataProvenance:
    return DataProvenance(
        exchange=exchange,
        source=source,
        reference=reference,
        retrieved_at=retrieved_at,
    )
