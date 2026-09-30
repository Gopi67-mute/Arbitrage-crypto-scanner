"""Application-level orchestration (Phase 5+). Empty by design in Phase 0.

Services wire the layers together: discover markets through adapters, normalise
them, validate routes, run the execution simulation, then evaluate
opportunities. They own sequencing, concurrency limits, failure isolation and
data-freshness gating.

Boundary rules:
  * a service may depend on ``exchanges``, ``fees``, ``tax``, ``transfers`` and
    ``domain``; nothing may depend back on a service
  * services perform I/O; the financial calculations they call must stay pure
  * one failed market must never abort a whole scan (AGENTS.md §42)
"""
