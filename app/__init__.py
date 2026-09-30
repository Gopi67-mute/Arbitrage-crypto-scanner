"""Crypto Arbitrage Scanner.

A READ-ONLY, real-market, cross-exchange cryptocurrency arbitrage intelligence
and analysis system for CoinDCX, KuCoin and Binance.

This package never places orders, never withdraws, never deposits and never
modifies exchange balances. See AGENTS.md for the engineering constitution.
"""

__all__ = ["APP_NAME", "CURRENT_PHASE", "__version__"]

__version__ = "0.1.0"

APP_NAME = "Crypto Arbitrage Scanner"

CURRENT_PHASE = "PHASE 1 — exchange abstraction"
