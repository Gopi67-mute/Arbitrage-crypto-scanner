"""Explicit representation of unverifiable data.

This module exists to make one class of bug impossible to write accidentally:

    fee = api_fee or Decimal("0")            # forbidden (AGENTS.md §64)
    withdrawal_fee = missing_fee or Decimal("0")
    tds = missing_tds or Decimal("0")

Three states must stay distinguishable for every financial input:

    Decimal("0")     verified to be zero
    UNKNOWN          could not be verified — the route is not executable
    NOT_APPLICABLE   the cost genuinely does not apply to this operation

A value that could not be verified must never be coerced into zero to keep a
calculation going. Later phases annotate their financial fields as
``Maybe[Decimal]`` and must call :func:`require_known` (or check
:func:`is_known`) before the value can take part in arithmetic.

Both sentinels raise on ``bool()`` so that the ``or``-fallback idiom above
fails loudly at runtime instead of quietly producing a fabricated zero.
"""

from __future__ import annotations

from typing import Final, TypeGuard, final

from app.core.errors import DataError

__all__ = [
    "NOT_APPLICABLE",
    "UNKNOWN",
    "Maybe",
    "NotApplicableType",
    "UnknownType",
    "is_known",
    "require_known",
]


class _Sentinel:
    """Base for the singleton markers below."""

    __slots__ = ()
    _label: str = "SENTINEL"

    def __repr__(self) -> str:
        return self._label

    def __str__(self) -> str:
        return self._label

    def __bool__(self) -> bool:
        raise TypeError(
            f"{self._label} has no truth value; a missing financial value must be "
            "handled explicitly and must never fall back to zero"
        )


@final
class UnknownType(_Sentinel):
    """The value could not be verified from an acceptable source."""

    __slots__ = ()
    _label = "UNKNOWN"


@final
class NotApplicableType(_Sentinel):
    """The value does not apply to this operation (verified, not missing)."""

    __slots__ = ()
    _label = "NOT_APPLICABLE"


UNKNOWN: Final = UnknownType()
NOT_APPLICABLE: Final = NotApplicableType()

type Maybe[T] = T | UnknownType | NotApplicableType
"""A value that is either verified, UNKNOWN, or NOT_APPLICABLE."""


def is_known[T](value: Maybe[T]) -> TypeGuard[T]:
    """Return ``True`` only when ``value`` is a real verified value."""
    return not isinstance(value, (UnknownType, NotApplicableType))


def require_known[T](value: Maybe[T], *, field: str) -> T:
    """Return the verified value, or raise :class:`DataError`.

    Call this at the point where a financial value must enter arithmetic. It is
    the intended alternative to inventing a default.
    """
    if isinstance(value, UnknownType):
        raise DataError(
            f"{field} is UNKNOWN: it could not be verified, so it must not be "
            "used in a financial calculation"
        )
    if isinstance(value, NotApplicableType):
        raise DataError(
            f"{field} is NOT_APPLICABLE and must not be used as a numeric value"
        )
    return value
