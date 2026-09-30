"""Pure domain layer.

Rules for everything in this package:
  * no HTTP, no sockets, no exchange SDKs
  * no environment-variable or settings access
  * no dependency on ``app.exchanges``, ``app.services``, ``app.fees``,
    ``app.tax`` or ``app.transfers``
  * every financial value is ``decimal.Decimal`` — never ``float``
  * deterministic and directly unit-testable

The permitted inward dependency is ``app.core.errors``, which imports nothing
itself and therefore cannot create a cycle.

Modules present in Phase 0
--------------------------
``money``
    ``parse_decimal``, ``AssetSymbol``, ``Money`` — the Decimal boundary.
``known``
    ``UNKNOWN`` / ``NOT_APPLICABLE`` sentinels enforcing the
    UNKNOWN-is-not-ZERO rule.

Modules deliberately absent in Phase 0
--------------------------------------
``market``, ``route``, ``opportunity`` and the order-book, fee, tax and
transfer models are NOT defined yet. Their shape is determined by the real
exchange payloads discovered in Phases 2-6; writing them now would mean
committing to speculative fields. See ``docs/decisions/0002-phase-0-domain-scope.md``.
"""
