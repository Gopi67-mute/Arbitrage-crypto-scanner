"""Where a value came from, and when.

AGENTS.md §39 requires every market-data object to carry a timestamp, and §44
requires important financial inputs — fees, withdrawal fees, network
information, minimums — to retain their source, reference and retrieval time.
§21 adds that a value taken from published documentation rather than a live
endpoint must be *marked* as static rather than passed off as live.

Every result an :class:`~app.exchanges.base.ExchangeAdapter` returns therefore
carries a :class:`DataProvenance`. One uniform field satisfies both rules and
makes the later staleness gate (``MAX_DATA_AGE_SECONDS``) and the route
confidence model (§65) possible without retrofitting timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.exchange import ExchangeId

__all__ = ["DataProvenance", "DataSource"]


class DataSource(StrEnum):
    """How a value was obtained. Never inferred — always stated by the adapter."""

    LIVE_API = "live_api"
    """Read from the venue's API during this scan."""

    OFFICIAL_DOCUMENTATION = "official_documentation"
    """Transcribed from the venue's published documentation. Static, not live."""

    STATIC_CONFIGURATION = "static_configuration"
    """Supplied by operator configuration, e.g. an account-specific fee tier."""


@dataclass(frozen=True, slots=True)
class DataProvenance:
    """The audit trail attached to one adapter result.

    ``reference`` identifies the origin precisely enough to re-check it: an API
    endpoint path for :attr:`DataSource.LIVE_API`, a documentation URL for
    :attr:`DataSource.OFFICIAL_DOCUMENTATION`, a setting name for
    :attr:`DataSource.STATIC_CONFIGURATION`. It is required, because an
    unattributable fee is exactly what AGENTS.md §20 and §68 forbid.

    ``retrieved_at`` must be timezone-aware. A naive timestamp cannot be
    compared across venues, and cross-venue age comparison is the entire point
    of AGENTS.md §40.

    Deliberately absent: ``effective_at`` and a verification-status field. They
    matter for static fee schedules and tax rules, and are added by Phase 8/9
    and Phase 11 against real dated sources rather than guessed now.
    """

    exchange: ExchangeId
    source: DataSource
    reference: str
    retrieved_at: datetime

    def __post_init__(self) -> None:
        reference = self.reference.strip()
        if not reference:
            raise ValueError(
                "provenance reference must not be empty: every financial input "
                "must be attributable to an identifiable source (AGENTS.md §44)"
            )
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError(
                f"retrieved_at must be timezone-aware, got {self.retrieved_at!r}: "
                "naive timestamps cannot be compared across venues"
            )
        object.__setattr__(self, "reference", reference)

    @property
    def is_live(self) -> bool:
        """``True`` only for data read from the venue's API during this scan."""
        return self.source is DataSource.LIVE_API

    def __str__(self) -> str:
        return (
            f"{self.exchange.value}/{self.source.value}/{self.reference}"
            f"@{self.retrieved_at.isoformat()}"
        )
