"""Trading fees and transfer metadata: missing data stays missing."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.errors import DataError
from app.domain.exchange import ExchangeId
from app.domain.fees import TradingFees
from app.domain.known import NOT_APPLICABLE, UNKNOWN, is_known, require_known
from app.domain.money import AssetSymbol
from app.domain.transfer import DepositInfo, NetworkInfo, WithdrawalInfo
from tests.unit.factories import market, provenance

USDT = AssetSymbol("USDT")


def withdrawal(**overrides):
    defaults = {
        "asset": USDT,
        "network": "TRC20",
        "withdrawal_enabled": True,
        "withdrawal_fee": Decimal("1"),
        "minimum_withdrawal": Decimal("10"),
        "maximum_withdrawal": NOT_APPLICABLE,
        "provenance": provenance(),
    }
    return WithdrawalInfo(**{**defaults, **overrides})


def deposit(**overrides):
    defaults = {
        "asset": USDT,
        "network": "TRC20",
        "deposit_enabled": True,
        "minimum_deposit": Decimal("1"),
        "requires_memo": False,
        "provenance": provenance(),
    }
    return DepositInfo(**{**defaults, **overrides})


# --------------------------------------------------------------------------- #
# TradingFees
# --------------------------------------------------------------------------- #
def test_fees_are_fractions_of_notional():
    fees = TradingFees(
        market=market(),
        maker_rate=Decimal("0.001"),
        taker_rate=Decimal("0.002"),
        provenance=provenance(),
    )

    assert fees.taker_rate == Decimal("0.002")


def test_an_unverifiable_fee_is_unknown_not_zero():
    """AGENTS.md §20: a fee is never silently invented."""
    fees = TradingFees(
        market=market(), maker_rate=UNKNOWN, taker_rate=UNKNOWN, provenance=provenance()
    )

    assert fees.taker_rate is UNKNOWN
    assert fees.taker_rate != Decimal("0")
    with pytest.raises(TypeError, match="never fall back to zero"):
        _ = fees.taker_rate or Decimal("0")


def test_requiring_an_unknown_fee_raises_rather_than_defaulting():
    fees = TradingFees(
        market=market(), maker_rate=UNKNOWN, taker_rate=UNKNOWN, provenance=provenance()
    )

    with pytest.raises(DataError, match="taker_rate is UNKNOWN"):
        require_known(fees.taker_rate, field="taker_rate")


def test_a_verified_zero_fee_is_a_real_value_and_passes_through():
    fees = TradingFees(
        market=market(),
        maker_rate=Decimal("0"),
        taker_rate=Decimal("0"),
        provenance=provenance(),
    )

    assert is_known(fees.maker_rate)
    assert require_known(fees.maker_rate, field="maker_rate") == Decimal("0")


def test_a_percent_sized_rate_is_rejected_as_a_unit_mistake():
    """A 100%+ "fee" is the unambiguous signature of percent/fraction confusion."""
    with pytest.raises(ValueError, match="fraction of notional, not a percent"):
        TradingFees(
            market=market(),
            maker_rate=Decimal("0.1"),
            taker_rate=Decimal("2"),
            provenance=provenance(),
        )


def test_a_maker_rebate_is_permitted():
    fees = TradingFees(
        market=market(),
        maker_rate=Decimal("-0.0001"),
        taker_rate=Decimal("0.001"),
        provenance=provenance(),
    )

    assert fees.maker_rate == Decimal("-0.0001")


def test_a_negative_taker_rate_is_rejected():
    with pytest.raises(ValueError, match="taker_rate must not be negative"):
        TradingFees(
            market=market(),
            maker_rate=Decimal("0"),
            taker_rate=Decimal("-0.001"),
            provenance=provenance(),
        )


def test_fees_reject_a_float_rate():
    with pytest.raises(ValueError, match="float is forbidden"):
        TradingFees(
            market=market(),
            maker_rate=0.001,  # type: ignore[arg-type]
            taker_rate=UNKNOWN,
            provenance=provenance(),
        )


def test_fees_reject_provenance_from_another_venue():
    with pytest.raises(ValueError, match="does not match market exchange"):
        TradingFees(
            market=market(exchange=ExchangeId.COINDCX),
            maker_rate=UNKNOWN,
            taker_rate=UNKNOWN,
            provenance=provenance(exchange=ExchangeId.BINANCE),
        )


def test_fees_can_come_from_configuration_rather_than_an_endpoint():
    """An account-specific tier is configured, and provenance must say so."""
    from app.domain.provenance import DataSource

    fees = TradingFees(
        market=market(),
        maker_rate=Decimal("0.0005"),
        taker_rate=Decimal("0.001"),
        provenance=provenance(
            source=DataSource.STATIC_CONFIGURATION, reference="COINDCX_TAKER_FEE"
        ),
    )

    assert not fees.provenance.is_live


# --------------------------------------------------------------------------- #
# NetworkInfo — a transfer is ASSET + NETWORK
# --------------------------------------------------------------------------- #
def test_the_same_asset_on_two_networks_is_two_records():
    trc = NetworkInfo(
        asset=USDT, network="TRC20", confirmations_required=1, provenance=provenance()
    )
    erc = NetworkInfo(
        asset=USDT, network="ERC20", confirmations_required=12, provenance=provenance()
    )

    assert trc != erc
    assert trc.asset == erc.asset


def test_network_code_is_not_normalised_across_venues():
    """Reconciling TRC20 / Tron naming is Phase 9's job, not a guess made here."""
    assert NetworkInfo(
        asset=USDT, network="  Tron  ", confirmations_required=UNKNOWN,
        provenance=provenance(),
    ).network == "Tron"


def test_network_must_not_be_empty():
    with pytest.raises(ValueError, match="network must not be empty"):
        NetworkInfo(
            asset=USDT, network="  ", confirmations_required=UNKNOWN,
            provenance=provenance(),
        )


def test_unpublished_confirmation_count_is_unknown():
    info = NetworkInfo(
        asset=USDT, network="TRC20", confirmations_required=UNKNOWN,
        provenance=provenance(),
    )

    assert not is_known(info.confirmations_required)


def test_confirmations_must_be_an_int_block_count():
    with pytest.raises(ValueError, match="must be an int block count"):
        NetworkInfo(
            asset=USDT, network="TRC20", confirmations_required=Decimal("1"),
            provenance=provenance(),
        )


# --------------------------------------------------------------------------- #
# DepositInfo
# --------------------------------------------------------------------------- #
def test_deposit_info_records_minimum_and_memo_requirement():
    info = deposit(minimum_deposit=Decimal("0.5"), requires_memo=True)

    assert info.minimum_deposit == Decimal("0.5")
    assert info.requires_memo is True


def test_an_unverifiable_memo_requirement_stays_unknown():
    """Reading UNKNOWN as "no memo needed" loses the funds (AGENTS.md §27)."""
    info = deposit(requires_memo=UNKNOWN)

    assert info.requires_memo is UNKNOWN
    with pytest.raises(TypeError):
        if info.requires_memo:  # pragma: no branch - the raise is the assertion
            pass


def test_an_unverifiable_deposit_flag_cannot_be_read_as_enabled():
    info = deposit(deposit_enabled=UNKNOWN)

    assert info.deposit_enabled is not True
    assert not is_known(info.deposit_enabled)


def test_a_verified_zero_minimum_deposit_is_distinct_from_unknown():
    assert deposit(minimum_deposit=Decimal("0")).minimum_deposit == Decimal("0")
    assert not is_known(deposit(minimum_deposit=UNKNOWN).minimum_deposit)


def test_deposit_rejects_a_float_minimum():
    with pytest.raises(ValueError, match="float is forbidden"):
        deposit(minimum_deposit=0.5)


def test_deposit_rejects_a_negative_minimum():
    with pytest.raises(ValueError, match="minimum_deposit must not be negative"):
        deposit(minimum_deposit=Decimal("-1"))


def test_deposit_rejects_a_non_bool_availability_flag():
    with pytest.raises(ValueError, match="deposit_enabled must be a bool"):
        deposit(deposit_enabled="yes")


# --------------------------------------------------------------------------- #
# WithdrawalInfo
# --------------------------------------------------------------------------- #
def test_withdrawal_info_records_fee_and_limits():
    info = withdrawal(withdrawal_fee=Decimal("0.8"), minimum_withdrawal=Decimal("10"))

    assert info.withdrawal_fee == Decimal("0.8")
    assert info.minimum_withdrawal == Decimal("10")


def test_an_unverifiable_withdrawal_fee_stays_unknown():
    """Treating it as zero would overstate the arriving quantity (AGENTS.md §21)."""
    info = withdrawal(withdrawal_fee=UNKNOWN)

    assert info.withdrawal_fee is UNKNOWN
    assert info.withdrawal_fee != Decimal("0")
    with pytest.raises(DataError, match="withdrawal_fee is UNKNOWN"):
        require_known(info.withdrawal_fee, field="withdrawal_fee")


def test_a_verified_zero_withdrawal_fee_is_a_real_value():
    assert require_known(
        withdrawal(withdrawal_fee=Decimal("0")).withdrawal_fee, field="withdrawal_fee"
    ) == Decimal("0")


def test_no_withdrawal_cap_is_not_applicable_not_unknown():
    """A venue that imposes no cap differs from a cap we could not read."""
    uncapped = withdrawal(maximum_withdrawal=NOT_APPLICABLE)
    unreadable = withdrawal(maximum_withdrawal=UNKNOWN)

    assert uncapped.maximum_withdrawal is NOT_APPLICABLE
    assert unreadable.maximum_withdrawal is UNKNOWN
    assert uncapped.maximum_withdrawal is not unreadable.maximum_withdrawal


def test_withdrawal_rejects_a_float_fee():
    with pytest.raises(ValueError, match="float is forbidden"):
        withdrawal(withdrawal_fee=0.8)


def test_withdrawal_rejects_a_negative_fee():
    with pytest.raises(ValueError, match="withdrawal_fee must not be negative"):
        withdrawal(withdrawal_fee=Decimal("-1"))


def test_withdrawal_rejects_a_minimum_above_its_maximum():
    with pytest.raises(ValueError, match="exceeds maximum_withdrawal"):
        withdrawal(minimum_withdrawal=Decimal("100"), maximum_withdrawal=Decimal("10"))


def test_withdrawal_limits_may_both_be_unknown_without_a_range_check():
    info = withdrawal(minimum_withdrawal=UNKNOWN, maximum_withdrawal=UNKNOWN)

    assert not is_known(info.minimum_withdrawal)


def test_withdrawal_disabled_is_a_verified_fact_distinct_from_unknown():
    assert withdrawal(withdrawal_enabled=False).withdrawal_enabled is False
    assert withdrawal(withdrawal_enabled=UNKNOWN).withdrawal_enabled is UNKNOWN


def test_withdrawal_info_exposes_no_way_to_withdraw():
    """It is a metadata record. It reports; it does not act."""
    callables = [
        name
        for name in dir(withdrawal())
        if not name.startswith("_") and callable(getattr(withdrawal(), name))
    ]

    assert callables == []
