"""Failures an exchange adapter can raise.

All of these extend :class:`app.core.errors.ExchangeError`, so
``except ExchangeError`` in the Phase 5+ scanner isolates one venue's failure
without aborting the scan (AGENTS.md §42), while a caller that needs to
distinguish a timeout from a malformed response can.

The set is deliberately closed at five leaf types, one per distinction the
scanner actually has to act on:

============================  ======================================
``UnsupportedCapabilityError`` this adapter offers no such operation
``InvalidExchangeRequestError`` the caller asked for something this
                               adapter cannot address
``ExchangeTimeoutError``       the venue did not answer in time
``ExchangeRateLimitError``     the venue refused: too many requests
``MalformedExchangeResponseError`` the venue answered with something
                               unparseable
============================  ======================================

A sixth case — "the endpoint worked but this value is not available" — is
deliberately **not** an exception. That is ordinary, expected data, and it is
represented as ``UNKNOWN`` inside the returned model (:mod:`app.domain.known`).
Raising for it would push callers toward a ``try/except`` that swallows the
distinction and substitutes a zero, which is what AGENTS.md §62-§64 forbid.
:class:`app.core.errors.DataError` remains for the moment a caller *demands*
such a value via ``require_known()``.

No error in this module carries a recovery default. An adapter must never
convert a failure into ``Decimal("0")`` to keep a calculation going.
"""

from __future__ import annotations

from app.core.errors import ExchangeError
from app.domain.exchange import ExchangeId
from app.exchanges.capabilities import ExchangeCapability

__all__ = [
    "ExchangeRateLimitError",
    "ExchangeTimeoutError",
    "ExchangeTransportError",
    "InvalidExchangeRequestError",
    "MalformedExchangeResponseError",
    "UnsupportedCapabilityError",
]


class UnsupportedCapabilityError(ExchangeError):
    """The adapter does not offer this operation.

    This means the venue has no such endpoint — a permanent property of the
    adapter, not a transient failure and not missing data. Retrying cannot help,
    and the value is not ``UNKNOWN``: it was never obtainable here.
    """

    def __init__(self, exchange: ExchangeId, capability: ExchangeCapability) -> None:
        super().__init__(
            f"{exchange.value} does not support {capability.value}(); "
            f"check adapter.supports({capability!r}) before calling it"
        )
        self.exchange = exchange
        self.capability = capability


class InvalidExchangeRequestError(ExchangeError):
    """The request cannot be addressed to this adapter.

    Raised for a caller mistake — most often a :class:`~app.domain.exchange.MarketRef`
    belonging to a different venue. A programming error, not a venue failure.
    """


class ExchangeTransportError(ExchangeError):
    """The request did not complete: connection failure, HTTP error, timeout.

    The shared base for failures where *nothing usable came back*, so a caller
    that does not care why can catch this one type.
    """


class ExchangeTimeoutError(ExchangeTransportError):
    """The venue did not respond within the configured request timeout."""


class ExchangeRateLimitError(ExchangeTransportError):
    """The venue rejected the request for exceeding its rate limit.

    Distinct from a timeout because the correct response differs: back off and
    respect ``Retry-After`` rather than retry immediately (AGENTS.md §41). The
    retry policy itself, and any ``Retry-After`` payload this error might carry,
    belong to the phase that implements a real HTTP transport against a real
    rate-limit response — not to this contract.
    """


class MalformedExchangeResponseError(ExchangeError):
    """The venue responded, but the body could not be parsed or validated.

    Covers a schema change, a field that is not a number, a price of zero, a
    mis-sorted order book. The response is discarded; no part of it is salvaged
    into a partial result with invented gaps.
    """
