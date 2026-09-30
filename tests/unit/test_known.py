"""UNKNOWN must never degrade into a fabricated zero."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.errors import DataError
from app.domain.known import (
    NOT_APPLICABLE,
    UNKNOWN,
    NotApplicableType,
    UnknownType,
    is_known,
    require_known,
)


def test_sentinels_are_distinct_from_each_other_and_from_zero():
    assert UNKNOWN is not NOT_APPLICABLE
    assert Decimal(0) != UNKNOWN
    assert Decimal(0) != NOT_APPLICABLE
    assert UNKNOWN is not None


def test_sentinel_types_do_not_overlap():
    assert isinstance(UNKNOWN, UnknownType)
    assert isinstance(NOT_APPLICABLE, NotApplicableType)
    assert not isinstance(UNKNOWN, NotApplicableType)
    assert not isinstance(NOT_APPLICABLE, UnknownType)


def test_sentinels_render_as_their_status_name():
    assert repr(UNKNOWN) == "UNKNOWN"
    assert str(UNKNOWN) == "UNKNOWN"
    assert repr(NOT_APPLICABLE) == "NOT_APPLICABLE"


def test_or_fallback_idiom_raises_instead_of_inventing_zero():
    """`fee = api_fee or Decimal("0")` is the exact bug this guards against."""
    api_fee = UNKNOWN
    with pytest.raises(TypeError, match="never fall back to zero"):
        _ = api_fee or Decimal("0")


def test_truthiness_of_not_applicable_also_raises():
    with pytest.raises(TypeError):
        bool(NOT_APPLICABLE)


def test_is_known_distinguishes_verified_values():
    assert is_known(Decimal("0"))
    assert is_known(Decimal("0.5"))
    assert not is_known(UNKNOWN)
    assert not is_known(NOT_APPLICABLE)


def test_require_known_returns_verified_zero_unchanged():
    """A verified zero is a legitimate value and must pass through."""
    assert require_known(Decimal("0"), field="withdrawal_fee") == Decimal("0")


def test_require_known_rejects_unknown():
    with pytest.raises(DataError, match="withdrawal_fee is UNKNOWN"):
        require_known(UNKNOWN, field="withdrawal_fee")


def test_require_known_rejects_not_applicable():
    with pytest.raises(DataError, match="tds is NOT_APPLICABLE"):
        require_known(NOT_APPLICABLE, field="tds")
