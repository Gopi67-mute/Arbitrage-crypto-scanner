"""Network, deposit and withdrawal metadata as a venue reports it.

A transfer is identified by **ASSET + NETWORK**, never by asset alone
(AGENTS.md §22): ``USDT`` on TRC20 and ``USDT`` on ERC20 have different fees,
minimums, confirmation counts and availability, and one being enabled says
nothing about the other.

Every model here is therefore keyed by ``(asset, network)`` and scoped to one
venue through its :class:`~app.domain.provenance.DataProvenance`. Deciding
whether a source venue's withdrawal network matches a destination venue's
deposit network is *not* done here — network naming differs between venues and
reconciling it is Phase 9's job, against real data from all three.

Every numeric and boolean field is :class:`~app.domain.known.Maybe`. An
unverifiable withdrawal fee stays ``UNKNOWN``; a withdrawal-enabled flag that
could not be read stays ``UNKNOWN`` and must not be assumed ``True``
(AGENTS.md §43, §63, §64).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.known import Maybe, is_known
from app.domain.money import AssetSymbol, parse_maybe_decimal
from app.domain.provenance import DataProvenance

__all__ = ["DepositInfo", "NetworkInfo", "WithdrawalInfo"]


def _normalise_network(network: str) -> str:
    """Validate a venue's network code without normalising its spelling.

    Deliberately only strips whitespace. Upper-casing or mapping ``TRC20`` and
    ``Tron`` onto a canonical name would be cross-venue network reconciliation,
    which is Phase 9's job and cannot be done correctly without seeing what all
    three venues actually return. Until then these codes are venue-local and
    must not be compared across venues.
    """
    stripped = network.strip()
    if not stripped:
        raise ValueError(
            "network must not be empty: a transfer is identified by asset AND "
            "network (AGENTS.md §22)"
        )
    return stripped


def _parse_non_negative(value: object, *, field: str) -> Maybe[Decimal]:
    parsed = parse_maybe_decimal(value, field=field)
    if isinstance(parsed, Decimal) and parsed < 0:
        raise ValueError(f"{field} must not be negative, got {parsed}")
    return parsed


@dataclass(frozen=True, slots=True)
class NetworkInfo:
    """A chain on which one venue supports one asset.

    This is the *existence* record: it says the venue lists this asset on this
    network. Whether funds can actually move is answered by :class:`DepositInfo`
    and :class:`WithdrawalInfo`, which must both be checked — a venue can list a
    network while having deposits or withdrawals suspended on it.

    ``confirmations_required`` is a block count, not a financial value, so it is
    ``int``. It stays ``Maybe`` because not every venue publishes it.
    """

    asset: AssetSymbol
    network: str
    confirmations_required: Maybe[int]
    provenance: DataProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "network", _normalise_network(self.network))
        confirmations = self.confirmations_required
        if is_known(confirmations):
            if isinstance(confirmations, bool) or not isinstance(confirmations, int):
                raise ValueError(
                    f"confirmations_required must be an int block count, got "
                    f"{confirmations!r}"
                )
            if confirmations < 0:
                raise ValueError(
                    f"confirmations_required must not be negative, got {confirmations}"
                )

    def __str__(self) -> str:
        return f"{self.asset}-{self.network}"


@dataclass(frozen=True, slots=True)
class DepositInfo:
    """What one venue requires to receive one asset on one network.

    ``requires_memo`` covers the memo / destination tag / payment ID family
    (AGENTS.md §27). ``UNKNOWN`` here means the requirement could not be
    verified, which makes the route ``CANNOT_VERIFY`` — it must never be read as
    "no memo needed". Sending a memo-requiring asset without one loses the
    funds, so this is the field where guessing is most expensive.

    ``minimum_deposit`` is what the destination quantity must clear after the
    withdrawal fee has been subtracted (AGENTS.md §26).
    """

    asset: AssetSymbol
    network: str
    deposit_enabled: Maybe[bool]
    minimum_deposit: Maybe[Decimal]
    requires_memo: Maybe[bool]
    provenance: DataProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "network", _normalise_network(self.network))
        object.__setattr__(
            self,
            "minimum_deposit",
            _parse_non_negative(self.minimum_deposit, field="minimum_deposit"),
        )
        _require_maybe_bool(self.deposit_enabled, field="deposit_enabled")
        _require_maybe_bool(self.requires_memo, field="requires_memo")

    def __str__(self) -> str:
        return f"deposit {self.asset}-{self.network} enabled={self.deposit_enabled}"


@dataclass(frozen=True, slots=True)
class WithdrawalInfo:
    """What one venue charges and requires to send one asset on one network.

    ``withdrawal_fee`` is denominated in ``asset``, not in the quote currency:
    ``source quantity - withdrawal fee = destination quantity`` (AGENTS.md §26).
    A verified ``Decimal("0")`` fee is legitimate and distinct from ``UNKNOWN``.

    ``maximum_withdrawal`` is ``NOT_APPLICABLE`` on a venue that imposes no cap
    — which is different from ``UNKNOWN``, meaning the cap could not be read.
    """

    asset: AssetSymbol
    network: str
    withdrawal_enabled: Maybe[bool]
    withdrawal_fee: Maybe[Decimal]
    minimum_withdrawal: Maybe[Decimal]
    maximum_withdrawal: Maybe[Decimal]
    provenance: DataProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "network", _normalise_network(self.network))
        for field in ("withdrawal_fee", "minimum_withdrawal", "maximum_withdrawal"):
            object.__setattr__(
                self, field, _parse_non_negative(getattr(self, field), field=field)
            )
        _require_maybe_bool(self.withdrawal_enabled, field="withdrawal_enabled")

        low, high = self.minimum_withdrawal, self.maximum_withdrawal
        if isinstance(low, Decimal) and isinstance(high, Decimal) and low > high:
            raise ValueError(
                f"minimum_withdrawal {low} exceeds maximum_withdrawal {high}"
            )

    def __str__(self) -> str:
        return (
            f"withdraw {self.asset}-{self.network} "
            f"enabled={self.withdrawal_enabled} fee={self.withdrawal_fee}"
        )


def _require_maybe_bool(value: Maybe[bool], *, field: str) -> None:
    """Reject a non-bool masquerading as an availability flag.

    Note that ``value`` is never truth-tested: the sentinels raise on ``bool()``
    by design, which is exactly what stops ``if deposit_enabled:`` from reading
    UNKNOWN as "disabled" (AGENTS.md §64).
    """
    if is_known(value) and not isinstance(value, bool):
        raise ValueError(f"{field} must be a bool, UNKNOWN or NOT_APPLICABLE, got {value!r}")
