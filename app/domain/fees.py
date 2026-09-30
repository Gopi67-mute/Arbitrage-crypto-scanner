"""Trading fees as a venue reports them.

This is the *reported* fee, not the *applied* cost. AGENTS.md §30 keeps policy
out of the reporting layer: an adapter states what the venue charges and where
that came from; the Phase 8 fee engine decides which side of a trade is maker
or taker, applies discounts, and combines it with the execution result. Tax and
TDS are a separate subsystem entirely (§28) and are never folded in here.

Both rates are :class:`~app.domain.known.Maybe`. An unverifiable fee stays
``UNKNOWN`` and makes the route non-executable; it never becomes zero
(AGENTS.md §20, §63, §64).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.exchange import MarketRef
from app.domain.known import Maybe
from app.domain.money import parse_maybe_decimal
from app.domain.provenance import DataProvenance

__all__ = ["TradingFees"]

# A rate at or beyond ±100% is not a fee schedule, it is a percent/fraction mix-up.
_IMPLAUSIBLE_RATE = Decimal(1)


@dataclass(frozen=True, slots=True)
class TradingFees:
    """Maker and taker rates for one market, as fractions of notional.

    Rates are **fractions, not percents**: 0.1% is ``Decimal("0.001")``. The
    constructor rejects any magnitude at or above 1, because a value like
    ``Decimal("0.1")`` meaning "0.1 percent" would silently overstate costs a
    hundredfold, and one at or above 1 is the unambiguous signature of that
    mistake.

    A negative ``maker_rate`` is permitted and meaningful: some venues rebate
    makers. A negative ``taker_rate`` is not.

    Fees are per-market because AGENTS.md §20 allows pair-specific pricing; an
    adapter whose venue prices account-wide simply returns the same rates for
    every market, with provenance saying so. Account-tier and discount handling
    belongs to Phase 8, against a real fee endpoint.
    """

    market: MarketRef
    maker_rate: Maybe[Decimal]
    taker_rate: Maybe[Decimal]
    provenance: DataProvenance

    def __post_init__(self) -> None:
        if self.provenance.exchange is not self.market.exchange:
            raise ValueError(
                f"provenance exchange {self.provenance.exchange.value} does not "
                f"match market exchange {self.market.exchange.value}"
            )
        for field in ("maker_rate", "taker_rate"):
            value = parse_maybe_decimal(getattr(self, field), field=field)
            if isinstance(value, Decimal):
                if abs(value) >= _IMPLAUSIBLE_RATE:
                    raise ValueError(
                        f"{field} must be a fraction of notional, not a percent; "
                        f"got {value} (0.1% is Decimal('0.001'))"
                    )
                if field == "taker_rate" and value < 0:
                    raise ValueError(f"taker_rate must not be negative, got {value}")
            object.__setattr__(self, field, value)

    def __str__(self) -> str:
        return f"{self.market} maker={self.maker_rate} taker={self.taker_rate}"
