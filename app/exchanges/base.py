"""The exchange-agnostic adapter contract.

This is the seam AGENTS.md §6-§8 require::

    arbitrage engine  →  ExchangeAdapter  →  CoinDCX | KuCoin | Binance

Everything venue-specific — symbol format, pagination, auth-free endpoint
choice, rate-limit headers, network naming, precision conventions — lives
behind this interface, in one adapter per venue. Generic code never branches on
which venue it is talking to, so a fourth exchange costs one adapter and no
change to any engine.

An adapter **translates**. It does not calculate fees, taxes, slippage, routes
or profit, and it does not decide whether a route is executable. It reports
what its venue said, with provenance, and reports ``UNKNOWN`` for what its
venue did not say.

Read-only, permanently
----------------------
There is no method here to place an order, cancel one, withdraw, deposit,
transfer funds, or read a balance, and none will be added. V1 is an analysis
system (AGENTS.md §2, §83); execution, if it is ever built, is a separate
approved phase with its own interface. ``tests/unit/test_exchange_adapter.py``
asserts that no such method appears on this class.

Asynchronous
------------
The methods are ``async`` because the scanner's dominant cost is waiting on
three venues' HTTP endpoints, and a route needs both legs sampled inside one
bounded freshness window (AGENTS.md §40). Sequential I/O would widen that
window by the sum of the latencies. See
``docs/decisions/0003-phase-1-exchange-abstraction.md``.

No implementation exists yet. This module makes no network request, imports no
HTTP client, and defines no credential. CoinDCX, KuCoin and Binance adapters
arrive in Phases 2, 3 and 4.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.exchange import ExchangeId, MarketRef
from app.domain.fees import TradingFees
from app.domain.marketdata import OrderBook, Ticker
from app.domain.money import AssetSymbol
from app.domain.transfer import DepositInfo, NetworkInfo, WithdrawalInfo
from app.exchanges.capabilities import ExchangeCapability
from app.exchanges.errors import (
    InvalidExchangeRequestError,
    UnsupportedCapabilityError,
)

__all__ = ["ExchangeAdapter"]


class ExchangeAdapter(ABC):
    """Read-only access to one exchange's public market data.

    Implementations must satisfy these contract rules:

    1. **Declare capabilities honestly.** :attr:`capabilities` lists only what
       the venue can actually answer. A method whose capability is absent must
       raise :class:`~app.exchanges.errors.UnsupportedCapabilityError` — call
       :meth:`require_capability` first and the base class does it for you.
    2. **Never invent a value.** A field the venue did not supply is ``UNKNOWN``
       (:mod:`app.domain.known`). It is never ``Decimal("0")``, never a
       plausible default, never the value another venue reported (AGENTS.md
       §43, §63, §64).
    3. **Never swallow a failure.** Transport problems, rate limits and
       unparseable bodies raise (:mod:`app.exchanges.errors`). A failed request
       never returns a partial result with the gaps filled in.
    4. **Attach provenance to everything.** Every returned model carries a
       :class:`~app.domain.provenance.DataProvenance` naming the source,
       reference and retrieval time, so later phases can gate on staleness
       (AGENTS.md §39, §44).
    5. **Address only your own venue.** Reject a ``MarketRef`` belonging to
       another exchange — :meth:`require_market` does this.
    6. **Spot only, and no side effects.** Discovery returns spot markets; no
       method changes anything on the venue.

    Deliberately absent: a ``close()`` / async-context-manager lifecycle. Phase
    1 owns no resources, and whether the HTTP client is owned by the adapter or
    injected into it is a Phase 2 decision that should be made against a real
    transport rather than pre-empted here. Adding it later is additive.
    """

    # ----------------------------------------------------------------- #
    # Identity and capabilities
    # ----------------------------------------------------------------- #
    @property
    @abstractmethod
    def exchange_id(self) -> ExchangeId:
        """Which venue this adapter speaks for."""

    @property
    @abstractmethod
    def capabilities(self) -> frozenset[ExchangeCapability]:
        """Exactly the operations this adapter can answer.

        Declaring a capability the venue cannot serve is a contract violation:
        the scanner uses this set to decide whether a route can be verified at
        all, and an over-claim turns into a runtime failure mid-scan instead of
        an honest "this venue cannot tell us".
        """

    def supports(self, capability: ExchangeCapability) -> bool:
        """Whether :attr:`capabilities` includes ``capability``."""
        return capability in self.capabilities

    def require_capability(self, capability: ExchangeCapability) -> None:
        """Raise :class:`UnsupportedCapabilityError` unless the capability is declared.

        Implementations call this at the top of each operation, so an
        unsupported call fails immediately and explicitly rather than returning
        something empty that a caller might read as "no fee" or "no networks".
        """
        if not self.supports(capability):
            raise UnsupportedCapabilityError(self.exchange_id, capability)

    def require_market(self, market: MarketRef) -> None:
        """Raise :class:`InvalidExchangeRequestError` if ``market`` is another venue's.

        Guards the mistake that matters most in a cross-exchange scanner:
        pricing one leg of a route against the wrong venue's book. Silently
        accepting a foreign ``MarketRef`` would produce a plausible number that
        is entirely wrong.
        """
        if market.exchange is not self.exchange_id:
            raise InvalidExchangeRequestError(
                f"{market} belongs to {market.exchange.value}, but this adapter "
                f"serves {self.exchange_id.value}"
            )

    # ----------------------------------------------------------------- #
    # Market discovery
    # ----------------------------------------------------------------- #
    @abstractmethod
    async def discover_markets(self) -> Sequence[MarketRef]:
        """Every spot market this venue currently lists.

        Discovery is dynamic. There is no supported-asset list anywhere in this
        project (AGENTS.md §9, §37): the tradable universe is whatever the three
        venues return, and a newly listed asset must appear with no code change.

        Returns identity only. Precision, status vocabulary, limits and minimum
        notional are normalised in Phase 6, once all three venues' real payloads
        can be reconciled rather than guessed
        (``docs/decisions/0002-phase-0-domain-scope.md``).
        """

    # ----------------------------------------------------------------- #
    # Market data
    # ----------------------------------------------------------------- #
    @abstractmethod
    async def get_ticker(self, market: MarketRef) -> Ticker:
        """Top-of-book and last-trade summary for one market.

        For monitoring, spread screening and logging. It is **not** sufficient
        to price a route: the executable price at real capital comes from
        :meth:`get_order_book`, and the last traded price is never an execution
        price (AGENTS.md §16, §83.12-13).
        """

    @abstractmethod
    async def get_order_book(self, market: MarketRef, *, depth: int) -> OrderBook:
        """Depth snapshot for one market, up to ``depth`` levels per side.

        ``depth`` is required rather than defaulted: how deep the book must be
        read depends on the configured capital, and a hidden default would be a
        magic number silently deciding how much slippage the scanner can see
        (AGENTS.md §46, §61).

        A venue may return fewer levels than requested. That is a real depth
        limit, and Phase 12 must treat exhausting them as insufficient
        liquidity — never as licence to extrapolate deeper levels.
        """

    # ----------------------------------------------------------------- #
    # Costs and constraints
    # ----------------------------------------------------------------- #
    @abstractmethod
    async def get_trading_fees(self, market: MarketRef) -> TradingFees:
        """Maker and taker rates for one market, as the venue reports them.

        A rate the venue does not expose publicly is ``UNKNOWN``, which makes
        the route non-executable until it is configured explicitly. It is never
        filled in from another venue's schedule or from a remembered figure
        (AGENTS.md §20).
        """

    @abstractmethod
    async def get_network_info(self, asset: AssetSymbol) -> Sequence[NetworkInfo]:
        """Every chain on which this venue lists ``asset``.

        One asset, several networks: a transfer is ``ASSET + NETWORK``
        (AGENTS.md §22). Listing a network says only that the venue knows it —
        :meth:`get_deposit_info` and :meth:`get_withdrawal_info` say whether
        funds can actually move over it.

        An empty sequence means the venue verifiably lists no network for this
        asset, which is different from the request failing (that raises).
        """

    @abstractmethod
    async def get_deposit_info(self, asset: AssetSymbol) -> Sequence[DepositInfo]:
        """Deposit constraints for ``asset``, one entry per network.

        Includes the minimum deposit that a transfer's arriving quantity must
        clear, and whether a memo / destination tag is required. An
        unverifiable memo requirement is ``UNKNOWN`` and makes the route
        ``CANNOT_VERIFY``; it is never read as "not required" (AGENTS.md §27).
        """

    @abstractmethod
    async def get_withdrawal_info(self, asset: AssetSymbol) -> Sequence[WithdrawalInfo]:
        """Withdrawal constraints and fees for ``asset``, one entry per network.

        This reports what the venue charges and permits. It does **not** and
        will never initiate a withdrawal: the adapter has no such method, and
        the scanner has no such capability (AGENTS.md §2, §83).

        A withdrawal fee that could not be read is ``UNKNOWN``. Treating it as
        zero would overstate the arriving quantity and manufacture profit that
        does not exist (AGENTS.md §21, §64).
        """
