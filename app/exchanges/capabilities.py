"""What an adapter can be asked for.

AGENTS.md §7 requires capabilities to be explicit and forbids forcing every
exchange to support what its API does not provide. This module is the smallest
representation that achieves that: one enum member per read-only operation on
:class:`~app.exchanges.base.ExchangeAdapter`, and a ``frozenset`` of them on
each adapter.

There is deliberately no capability *framework* — no registry, no per-capability
descriptor object, no dynamic dispatch. An adapter declares a set; the base
class checks membership.

Crucially, a capability is **not** a data-availability answer:

===========================  ==========================================
``capability not in set``    the venue offers no such endpoint at all;
                             calling the method raises
                             ``UnsupportedCapabilityError``
``UNKNOWN`` in a result      the endpoint exists and was called, but this
                             particular value could not be verified
``NOT_APPLICABLE`` in a      the endpoint exists and the value genuinely
result                       does not apply
===========================  ==========================================

Collapsing those three would be the exact failure AGENTS.md §62-§63 forbids, so
capabilities use the type system and missing values use
:mod:`app.domain.known`. They are never substituted for one another.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["ExchangeCapability"]


class ExchangeCapability(StrEnum):
    """One read-only operation an adapter may support.

    Each member's *value is the name of the method it gates*. That coupling is
    intentional: it keeps the enum and the contract from drifting apart, it
    makes ``require_capability`` messages self-explanatory, and
    ``tests/unit/test_exchange_adapter.py`` asserts the correspondence in both
    directions, so adding a method without a capability (or the reverse) fails
    the suite.

    Every member is a *read*. There is no member for placing an order,
    cancelling one, withdrawing, depositing or transferring, and none will be
    added: those operations are outside V1 scope entirely (AGENTS.md §2, §83).
    """

    DISCOVER_MARKETS = "discover_markets"
    GET_TICKER = "get_ticker"
    GET_ORDER_BOOK = "get_order_book"
    GET_TRADING_FEES = "get_trading_fees"
    GET_DEPOSIT_INFO = "get_deposit_info"
    GET_WITHDRAWAL_INFO = "get_withdrawal_info"
    GET_NETWORK_INFO = "get_network_info"
