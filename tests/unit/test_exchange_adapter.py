"""The ExchangeAdapter contract.

Nothing here touches a network: the only implementation is the in-test
:class:`FakeAdapter` below. It exists to prove the interface is implementable
and to exercise the capability and validation behaviour the base class
provides. It is not, and must never become, a stand-in for a real venue.
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from app.core.errors import ApplicationError, ExchangeError
from app.domain.exchange import ExchangeId, MarketRef
from app.domain.fees import TradingFees
from app.domain.known import UNKNOWN, is_known
from app.domain.marketdata import OrderBook, OrderBookLevel, Ticker
from app.domain.money import AssetSymbol
from app.domain.transfer import DepositInfo, NetworkInfo, WithdrawalInfo
from app.exchanges.base import ExchangeAdapter
from app.exchanges.capabilities import ExchangeCapability
from app.exchanges.errors import (
    ExchangeRateLimitError,
    ExchangeTimeoutError,
    ExchangeTransportError,
    InvalidExchangeRequestError,
    MalformedExchangeResponseError,
    UnsupportedCapabilityError,
)
from tests.unit.factories import market, provenance

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Every data-returning operation on the contract, paired with its capability.
DATA_METHODS = tuple(capability.value for capability in ExchangeCapability)


# --------------------------------------------------------------------------- #
# A minimal in-memory adapter — the only implementation that exists
# --------------------------------------------------------------------------- #
class FakeAdapter(ExchangeAdapter):
    """Returns fixed data. No I/O, no clock, no venue."""

    def __init__(
        self,
        exchange: ExchangeId = ExchangeId.COINDCX,
        capabilities: frozenset[ExchangeCapability] | None = None,
    ) -> None:
        self._exchange = exchange
        self._capabilities = (
            frozenset(ExchangeCapability) if capabilities is None else capabilities
        )

    @property
    def exchange_id(self) -> ExchangeId:
        return self._exchange

    @property
    def capabilities(self) -> frozenset[ExchangeCapability]:
        return self._capabilities

    def _market(self) -> MarketRef:
        return market(exchange=self._exchange)

    async def discover_markets(self):
        self.require_capability(ExchangeCapability.DISCOVER_MARKETS)
        return (self._market(),)

    async def get_ticker(self, market_ref):
        self.require_capability(ExchangeCapability.GET_TICKER)
        self.require_market(market_ref)
        return Ticker(
            market=market_ref,
            bid=Decimal("49.87"),
            ask=Decimal("49.92"),
            last=UNKNOWN,
            provenance=provenance(exchange=self._exchange),
        )

    async def get_order_book(self, market_ref, *, depth):
        self.require_capability(ExchangeCapability.GET_ORDER_BOOK)
        self.require_market(market_ref)
        levels = [
            OrderBookLevel(price=Decimal("100"), quantity=Decimal("2")),
            OrderBookLevel(price=Decimal("99"), quantity=Decimal("5")),
        ]
        return OrderBook(
            market=market_ref,
            bids=tuple(levels[:depth]),
            asks=(),
            provenance=provenance(exchange=self._exchange),
        )

    async def get_trading_fees(self, market_ref):
        self.require_capability(ExchangeCapability.GET_TRADING_FEES)
        self.require_market(market_ref)
        return TradingFees(
            market=market_ref,
            maker_rate=UNKNOWN,
            taker_rate=UNKNOWN,
            provenance=provenance(exchange=self._exchange),
        )

    async def get_network_info(self, asset):
        self.require_capability(ExchangeCapability.GET_NETWORK_INFO)
        return (
            NetworkInfo(
                asset=asset,
                network="TRC20",
                confirmations_required=UNKNOWN,
                provenance=provenance(exchange=self._exchange),
            ),
        )

    async def get_deposit_info(self, asset):
        self.require_capability(ExchangeCapability.GET_DEPOSIT_INFO)
        return (
            DepositInfo(
                asset=asset,
                network="TRC20",
                deposit_enabled=UNKNOWN,
                minimum_deposit=UNKNOWN,
                requires_memo=UNKNOWN,
                provenance=provenance(exchange=self._exchange),
            ),
        )

    async def get_withdrawal_info(self, asset):
        self.require_capability(ExchangeCapability.GET_WITHDRAWAL_INFO)
        return (
            WithdrawalInfo(
                asset=asset,
                network="TRC20",
                withdrawal_enabled=UNKNOWN,
                withdrawal_fee=UNKNOWN,
                minimum_withdrawal=UNKNOWN,
                maximum_withdrawal=UNKNOWN,
                provenance=provenance(exchange=self._exchange),
            ),
        )


# --------------------------------------------------------------------------- #
# The contract is abstract and complete
# --------------------------------------------------------------------------- #
def test_the_base_class_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ExchangeAdapter()  # type: ignore[abstract]


def test_every_required_method_exists_on_the_contract():
    expected = {"exchange_id", "capabilities", *DATA_METHODS}

    assert expected <= set(dir(ExchangeAdapter))


def test_every_data_method_is_abstract():
    """A default implementation would be a fabricated venue answer."""
    abstract = ExchangeAdapter.__abstractmethods__

    assert set(DATA_METHODS) | {"exchange_id", "capabilities"} == set(abstract)


def test_an_incomplete_adapter_cannot_be_instantiated():
    class Partial(ExchangeAdapter):
        @property
        def exchange_id(self):
            return ExchangeId.KUCOIN

        @property
        def capabilities(self):
            return frozenset()

    with pytest.raises(TypeError, match="abstract"):
        Partial()  # type: ignore[abstract]


def test_a_fake_adapter_can_implement_the_whole_contract():
    adapter = FakeAdapter()

    assert isinstance(adapter, ExchangeAdapter)
    assert adapter.exchange_id is ExchangeId.COINDCX


# --------------------------------------------------------------------------- #
# Asynchronous by design
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", DATA_METHODS)
def test_every_data_method_is_a_coroutine_function(name):
    assert inspect.iscoroutinefunction(getattr(ExchangeAdapter, name)), (
        f"{name} must be async: the scanner samples three venues concurrently "
        "inside one bounded freshness window"
    )


@pytest.mark.parametrize("name", ("supports", "require_capability", "require_market"))
def test_pure_helpers_stay_synchronous(name):
    assert not inspect.iscoroutinefunction(getattr(ExchangeAdapter, name))


@pytest.mark.asyncio
async def test_awaiting_the_contract_returns_domain_models():
    adapter = FakeAdapter()
    ref = (await adapter.discover_markets())[0]

    assert isinstance(ref, MarketRef)
    assert isinstance(await adapter.get_ticker(ref), Ticker)
    assert isinstance(await adapter.get_order_book(ref, depth=1), OrderBook)
    assert isinstance(await adapter.get_trading_fees(ref), TradingFees)


@pytest.mark.asyncio
async def test_depth_is_a_required_keyword_argument():
    """A defaulted depth would be a magic number deciding visible slippage."""
    adapter = FakeAdapter()
    ref = (await adapter.discover_markets())[0]

    with pytest.raises(TypeError):
        await adapter.get_order_book(ref)  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_a_venue_may_return_less_depth_than_requested():
    adapter = FakeAdapter()
    ref = (await adapter.discover_markets())[0]

    book = await adapter.get_order_book(ref, depth=50)

    assert len(book.bids) == 2, "fewer levels than asked for is a real depth limit"


# --------------------------------------------------------------------------- #
# Capabilities
# --------------------------------------------------------------------------- #
def test_each_capability_names_the_method_it_gates():
    for capability in ExchangeCapability:
        assert hasattr(ExchangeAdapter, capability.value)


def test_no_data_method_lacks_a_capability():
    """Adding a method without a capability would make it ungated."""
    declared = {capability.value for capability in ExchangeCapability}
    on_class = {
        name
        for name in ExchangeAdapter.__abstractmethods__
        if name not in {"exchange_id", "capabilities"}
    }

    assert on_class == declared


def test_an_adapter_reports_exactly_what_it_supports():
    adapter = FakeAdapter(capabilities=frozenset({ExchangeCapability.DISCOVER_MARKETS}))

    assert adapter.supports(ExchangeCapability.DISCOVER_MARKETS)
    assert not adapter.supports(ExchangeCapability.GET_TRADING_FEES)


@pytest.mark.asyncio
async def test_an_undeclared_capability_raises_rather_than_returning_empty():
    """An empty result would read as "no fee" / "no networks" — a fabricated answer."""
    adapter = FakeAdapter(capabilities=frozenset({ExchangeCapability.DISCOVER_MARKETS}))
    ref = (await adapter.discover_markets())[0]

    with pytest.raises(UnsupportedCapabilityError) as raised:
        await adapter.get_trading_fees(ref)

    assert raised.value.capability is ExchangeCapability.GET_TRADING_FEES
    assert raised.value.exchange is ExchangeId.COINDCX
    assert "does not support get_trading_fees()" in str(raised.value)


@pytest.mark.asyncio
async def test_an_adapter_with_no_capabilities_is_representable():
    """A venue that publishes nothing is a legitimate, honest state."""
    adapter = FakeAdapter(capabilities=frozenset())

    assert adapter.capabilities == frozenset()
    with pytest.raises(UnsupportedCapabilityError):
        await adapter.discover_markets()


def test_unsupported_capability_is_not_the_same_as_unknown_data():
    """Three distinct states; collapsing any two is AGENTS.md §62-§63's bug."""
    supported = FakeAdapter()
    unsupported = FakeAdapter(capabilities=frozenset())

    assert supported.supports(ExchangeCapability.GET_WITHDRAWAL_INFO)
    assert not unsupported.supports(ExchangeCapability.GET_WITHDRAWAL_INFO)
    with pytest.raises(UnsupportedCapabilityError):
        unsupported.require_capability(ExchangeCapability.GET_WITHDRAWAL_INFO)


@pytest.mark.asyncio
async def test_a_supported_capability_may_still_report_unknown_values():
    """Endpoint reachable, value unverifiable — UNKNOWN, not zero, not unsupported."""
    adapter = FakeAdapter()
    info = (await adapter.get_withdrawal_info(AssetSymbol("USDT")))[0]

    assert adapter.supports(ExchangeCapability.GET_WITHDRAWAL_INFO)
    assert info.withdrawal_fee is UNKNOWN
    assert not is_known(info.withdrawal_fee)
    assert info.withdrawal_fee != Decimal("0")


@pytest.mark.asyncio
async def test_unknown_adapter_output_cannot_be_defaulted_to_zero():
    adapter = FakeAdapter()
    fees = await adapter.get_trading_fees(market())

    with pytest.raises(TypeError, match="never fall back to zero"):
        _ = fees.taker_rate or Decimal("0")


# --------------------------------------------------------------------------- #
# Requests are validated against the adapter's own venue
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_a_market_from_another_venue_is_rejected():
    adapter = FakeAdapter(exchange=ExchangeId.COINDCX)
    foreign = market(exchange=ExchangeId.KUCOIN, symbol="XRP-USDT", quote="USDT")

    with pytest.raises(InvalidExchangeRequestError, match="belongs to kucoin"):
        await adapter.get_ticker(foreign)


def test_require_market_accepts_the_adapters_own_market():
    adapter = FakeAdapter(exchange=ExchangeId.BINANCE)

    adapter.require_market(market(exchange=ExchangeId.BINANCE, symbol="XRPUSDT", quote="USDT"))


@pytest.mark.asyncio
async def test_results_carry_provenance_naming_the_adapters_venue():
    adapter = FakeAdapter(exchange=ExchangeId.KUCOIN)
    ref = (await adapter.discover_markets())[0]

    ticker = await adapter.get_ticker(ref)

    assert ticker.provenance.exchange is ExchangeId.KUCOIN
    assert ticker.provenance.retrieved_at.tzinfo is not None


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "error",
    [
        InvalidExchangeRequestError,
        ExchangeTransportError,
        ExchangeTimeoutError,
        ExchangeRateLimitError,
        MalformedExchangeResponseError,
    ],
)
def test_every_adapter_error_is_catchable_as_an_exchange_error(error):
    """One `except ExchangeError` isolates a venue failure without ending the scan."""
    assert issubclass(error, ExchangeError)
    assert issubclass(error, ApplicationError)


def test_unsupported_capability_is_also_an_exchange_error():
    assert issubclass(UnsupportedCapabilityError, ExchangeError)


def test_timeout_and_rate_limit_are_distinguishable_transport_failures():
    """They call for different responses: retry vs back off and respect Retry-After."""
    assert issubclass(ExchangeTimeoutError, ExchangeTransportError)
    assert issubclass(ExchangeRateLimitError, ExchangeTransportError)
    assert not issubclass(ExchangeTimeoutError, ExchangeRateLimitError)


def test_a_malformed_response_is_not_a_transport_failure():
    assert not issubclass(MalformedExchangeResponseError, ExchangeTransportError)


def test_no_adapter_error_carries_a_numeric_fallback():
    """An error must never hand the caller a substitute value to continue with."""
    for error in (
        ExchangeTransportError("boom"),
        ExchangeTimeoutError("slow"),
        MalformedExchangeResponseError("bad json"),
    ):
        assert not any(
            isinstance(getattr(error, name, None), Decimal) for name in dir(error)
        )


# --------------------------------------------------------------------------- #
# READ-ONLY scope
# --------------------------------------------------------------------------- #
# Verbs that would mean acting on an account rather than reading market data.
# `get_deposit_info` / `get_withdrawal_info` are reads *about* transfers, so the
# check targets action names, not the words "deposit" and "withdrawal".
FORBIDDEN_MEMBERS = (
    "place_order",
    "create_order",
    "submit_order",
    "cancel_order",
    "cancel_all_orders",
    "buy",
    "sell",
    "withdraw",
    "deposit",
    "transfer",
    "get_balance",
    "get_balances",
    "get_account",
    "get_open_orders",
    "sign_request",
    "authenticate",
)


@pytest.mark.parametrize("name", FORBIDDEN_MEMBERS)
def test_the_contract_exposes_no_write_operation(name):
    assert not hasattr(ExchangeAdapter, name), (
        f"{name} must never exist on the adapter contract: V1 is read-only "
        "(AGENTS.md §2, §83)"
    )


@pytest.mark.parametrize("name", FORBIDDEN_MEMBERS)
def test_no_capability_authorises_a_write_operation(name):
    assert name not in {capability.value for capability in ExchangeCapability}


def test_the_contract_has_no_public_members_beyond_the_documented_surface():
    """A new public method must be a deliberate, reviewed contract change."""
    expected = {
        "exchange_id",
        "capabilities",
        "supports",
        "require_capability",
        "require_market",
        *DATA_METHODS,
    }
    public = {name for name in vars(ExchangeAdapter) if not name.startswith("_")}

    assert public == expected


# --------------------------------------------------------------------------- #
# No venue implementation, and no network, exists yet
# --------------------------------------------------------------------------- #
def test_no_venue_adapter_module_exists_yet():
    """Phase 1 is the contract only; CoinDCX/KuCoin/Binance arrive in Phases 2-4."""
    modules = sorted(path.name for path in (PROJECT_ROOT / "app" / "exchanges").glob("*.py"))

    assert modules == ["__init__.py", "base.py", "capabilities.py", "errors.py"]


def test_importing_the_contract_pulls_in_no_http_client():
    """Proof that the abstraction itself cannot cause a network call."""
    probe = (
        "import app.exchanges.base, sys; "
        "print(sorted(m for m in sys.modules "
        "if m.split('.')[0] in {'httpx', 'httpcore', 'requests', 'aiohttp', 'urllib3', 'socket'}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]", result.stdout


def test_the_exchanges_package_defines_no_credential():
    credential_words = ("api_key", "api_secret", "passphrase", "password", "token")
    sources = (PROJECT_ROOT / "app" / "exchanges").glob("*.py")

    for path in sources:
        text = path.read_text(encoding="utf-8").lower()
        for word in credential_words:
            assert word not in text, f"{path.name} mentions {word}"
