"""Trading and withdrawal fee models (Phase 8-9). Empty by design in Phase 0.

Boundary rules:
  * no universal fee is ever assumed; fees are exchange-specific and, where the
    API supports it, pair- and tier-specific (AGENTS.md §20)
  * every fee used in a profit calculation carries provenance: source, endpoint,
    retrieved_at, live-or-static (AGENTS.md §44)
  * a fee that cannot be verified is UNKNOWN, never zero (AGENTS.md §63)
  * withdrawal fees are keyed by asset AND network, never asset alone
  * tax/TDS is a separate subsystem and is never folded into a fee here
"""
