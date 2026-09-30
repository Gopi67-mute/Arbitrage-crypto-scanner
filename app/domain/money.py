"""The Decimal boundary for all financial values.

AGENTS.md §14 is absolute: prices, quantities, balances, fees, taxes, spreads,
slippage, profit and ROI are ``decimal.Decimal``. Binary floating point never
touches a financial value, not even transiently while parsing an exchange
response.

:func:`parse_decimal` is the single gate through which external numeric data
enters the system, and it rejects ``float`` outright rather than converting it.
Rejecting it is the point: ``Decimal(0.1)`` is
``0.1000000000000000055511151231257827021181583404541015625``, and an exchange
response parsed through a float has already lost the exact value the exchange
sent.

``AssetSymbol`` is a normalised symbol, not a whitelist. There is no supported
asset list anywhere in this project (AGENTS.md §9); assets are discovered from
live markets.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

__all__ = ["AssetSymbol", "Money", "parse_decimal"]

# Exchange asset codes are upper-case alphanumerics; a few legitimately contain
# a separator (e.g. leveraged-token style codes). No asset names are enumerated.
_ALLOWED_SYMBOL_CHARS = frozenset(string.ascii_uppercase + string.digits + "._-")


def parse_decimal(value: object, *, field: str = "value") -> Decimal:
    """Convert external numeric data into an exact :class:`Decimal`.

    Accepts ``Decimal``, ``int`` and numeric ``str``. Raises :class:`ValueError`
    for ``float``, ``bool``, empty/unparseable strings, ``NaN`` and infinities.

    ``ValueError`` (rather than an ``ApplicationError``) is intentional: it is
    the Python contract for a parsing failure, and it lets this function be used
    directly as a pydantic validator.
    """
    # bool is an int subclass, so it must be rejected before the int branch.
    if isinstance(value, bool):
        raise ValueError(f"{field}: bool is not a valid financial value")

    if isinstance(value, float):
        raise ValueError(
            f"{field}: float is forbidden for financial values "
            f"(got {value!r}); pass a str, int or Decimal"
        )

    parsed: Decimal
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, int):
        parsed = Decimal(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{field}: empty string is not a valid financial value")
        try:
            parsed = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"{field}: {value!r} is not a valid decimal number") from exc
    else:
        raise ValueError(
            f"{field}: unsupported type {type(value).__name__} for a financial value"
        )

    if not parsed.is_finite():
        raise ValueError(f"{field}: {parsed} is not a finite decimal value")
    return parsed


@dataclass(frozen=True, slots=True)
class AssetSymbol:
    """A normalised asset or fiat currency code, e.g. ``INR``, ``USDT``, ``XRP``.

    Normalisation is case- and whitespace-insensitive so that symbols coming
    from different exchanges compare correctly. It carries no network, no
    precision and no market identity — an asset alone never identifies a
    transfer route (AGENTS.md §22).
    """

    code: str

    def __post_init__(self) -> None:
        normalised = self.code.strip().upper()
        if not normalised:
            raise ValueError("asset symbol must not be empty")
        invalid = sorted(set(normalised) - _ALLOWED_SYMBOL_CHARS)
        if invalid:
            raise ValueError(
                f"asset symbol {self.code!r} contains unsupported characters: "
                f"{''.join(invalid)}"
            )
        object.__setattr__(self, "code", normalised)

    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True, slots=True)
class Money:
    """An exact amount of one asset or currency.

    ``currency`` is any :class:`AssetSymbol` — fiat (``INR``) or crypto
    (``XRP``). Amounts of different currencies are never combined: INR, USDT and
    a crypto quantity are not interchangeable (AGENTS.md §12), and converting
    between them is a real economic operation handled by a later phase, not by
    this value object.

    Deliberately absent: division, rounding policy and currency conversion.
    Those need the exchange precision rules discovered in Phase 6, and guessing
    them now would bake in a wrong assumption.
    """

    amount: Decimal
    currency: AssetSymbol

    def __post_init__(self) -> None:
        # Guards against a float sneaking in at runtime despite the annotation.
        object.__setattr__(self, "amount", parse_decimal(self.amount, field="amount"))

    @classmethod
    def zero(cls, currency: AssetSymbol) -> Money:
        """A verified-zero amount. This is not the same thing as UNKNOWN."""
        return cls(Decimal(0), currency)

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    @property
    def is_positive(self) -> bool:
        return self.amount > 0

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"cannot combine {self.currency} and {other.currency}: "
                "different currencies require an explicit executable conversion"
            )

    def __add__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def scale(self, factor: Decimal) -> Money:
        """Multiply by a dimensionless Decimal factor (e.g. a fee rate)."""
        return Money(self.amount * parse_decimal(factor, field="factor"), self.currency)

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
