"""The Decimal boundary: parse_decimal, AssetSymbol and Money."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.money import AssetSymbol, Money, parse_decimal

INR = AssetSymbol("INR")
USDT = AssetSymbol("USDT")


# --------------------------------------------------------------------------- #
# parse_decimal
# --------------------------------------------------------------------------- #
def test_parses_string_exactly():
    """Every digit survives, including beyond 64-bit float precision."""
    raw = "0.000000123456789012345678"
    parsed = parse_decimal(raw)

    assert parsed == Decimal(raw)
    # as_tuple() compares the stored digits and exponent, not the display form
    # (Decimal renders small exponents in scientific notation).
    assert parsed.as_tuple() == Decimal(raw).as_tuple()


def test_parses_large_capital_string_without_reformatting():
    raw = "1234.5678901234567890123456789"
    assert str(parse_decimal(raw)) == raw


def test_parses_int_and_decimal():
    assert parse_decimal(1000) == Decimal("1000")
    assert parse_decimal(Decimal("12.50")) == Decimal("12.50")


def test_preserves_trailing_zeros_from_exchange_payloads():
    """Exchanges send fixed-precision strings; the precision is information."""
    assert str(parse_decimal("12.5000")) == "12.5000"


@pytest.mark.parametrize("value", [0.1, 1.0, -2.5, 1e-9])
def test_rejects_float(value):
    with pytest.raises(ValueError, match="float is forbidden"):
        parse_decimal(value)


@pytest.mark.parametrize("value", [True, False])
def test_rejects_bool(value):
    with pytest.raises(ValueError, match="bool is not a valid"):
        parse_decimal(value)


@pytest.mark.parametrize("value", ["", "   ", "abc", "1,000", "12.3.4", "1 000"])
def test_rejects_unparseable_strings(value):
    with pytest.raises(ValueError):
        parse_decimal(value)


@pytest.mark.parametrize("value", ["NaN", "-NaN", "Infinity", "-Infinity"])
def test_rejects_nan_and_infinity(value):
    with pytest.raises(ValueError):
        parse_decimal(value)


def test_rejects_unsupported_types():
    with pytest.raises(ValueError, match="unsupported type"):
        parse_decimal(None)
    with pytest.raises(ValueError, match="unsupported type"):
        parse_decimal([1])


def test_error_message_names_the_field():
    with pytest.raises(ValueError, match="withdrawal_fee"):
        parse_decimal(0.5, field="withdrawal_fee")


def test_float_conversion_would_have_been_lossy():
    """Documents precisely why float is banned rather than merely discouraged.

    The ``noqa`` is the one deliberate exception in the repository: ruff's RUF032
    rule bans ``Decimal(<float>)``, and this assertion exists to demonstrate the
    corruption that rule prevents.
    """
    assert Decimal(0.1) != Decimal("0.1")  # noqa: RUF032
    assert str(Decimal(0.1)).startswith("0.1000000000000000055")  # noqa: RUF032
    assert parse_decimal("0.1") == Decimal("0.1")


# --------------------------------------------------------------------------- #
# AssetSymbol
# --------------------------------------------------------------------------- #
def test_symbol_is_normalised_and_compares_across_exchanges():
    assert AssetSymbol(" usdt ") == AssetSymbol("USDT")
    assert AssetSymbol("xrp").code == "XRP"


def test_symbol_allows_digits_and_separators():
    assert AssetSymbol("1inch").code == "1INCH"
    assert AssetSymbol("btc3l").code == "BTC3L"


@pytest.mark.parametrize("value", ["", "   ", "US DT", "USDT/INR", "us$dt"])
def test_invalid_symbols_are_rejected(value):
    with pytest.raises(ValueError):
        AssetSymbol(value)


def test_symbol_is_immutable_and_hashable():
    symbol = AssetSymbol("INR")
    with pytest.raises(AttributeError):
        symbol.code = "USDT"  # type: ignore[misc]
    assert {AssetSymbol("inr"), AssetSymbol("INR")} == {AssetSymbol("INR")}


# --------------------------------------------------------------------------- #
# Money
# --------------------------------------------------------------------------- #
def test_money_addition_and_subtraction():
    assert Money(Decimal("100.25"), INR) + Money(Decimal("0.75"), INR) == Money(
        Decimal("101.00"), INR
    )
    assert Money(Decimal("100"), INR) - Money(Decimal("40"), INR) == Money(Decimal("60"), INR)


def test_money_arithmetic_is_exact():
    """The classic float failure: 0.1 + 0.2 != 0.3."""
    total = Money(Decimal("0.1"), INR) + Money(Decimal("0.2"), INR)
    assert total == Money(Decimal("0.3"), INR)


def test_money_rejects_mixing_currencies():
    with pytest.raises(ValueError, match="different currencies"):
        Money(Decimal("100"), INR) + Money(Decimal("1"), USDT)
    with pytest.raises(ValueError, match="different currencies"):
        Money(Decimal("100"), INR) - Money(Decimal("1"), USDT)


def test_money_rejects_float_amount_at_runtime():
    with pytest.raises(ValueError, match="float is forbidden"):
        Money(100.25, INR)  # type: ignore[arg-type]


def test_money_scale_uses_decimal_factor():
    fee = Money(Decimal("1000"), INR).scale(Decimal("0.001"))
    assert fee == Money(Decimal("1.000"), INR)

    with pytest.raises(ValueError, match="float is forbidden"):
        Money(Decimal("1000"), INR).scale(0.001)  # type: ignore[arg-type]


def test_money_zero_is_a_verified_zero():
    zero = Money.zero(INR)
    assert zero.is_zero
    assert not zero.is_positive
    assert not zero.is_negative
    assert zero.amount == Decimal(0)


def test_money_sign_properties():
    assert Money(Decimal("1"), INR).is_positive
    assert Money(Decimal("-1"), INR).is_negative
    assert (-Money(Decimal("1"), INR)) == Money(Decimal("-1"), INR)


def test_money_is_immutable():
    amount = Money(Decimal("10"), INR)
    with pytest.raises(AttributeError):
        amount.amount = Decimal("20")  # type: ignore[misc]


def test_money_str_names_the_currency():
    assert str(Money(Decimal("1234.50"), INR)) == "1234.50 INR"
