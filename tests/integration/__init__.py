"""Integration tests that may contact live, read-only public exchange endpoints.

Empty in Phase 0 — there are no exchange adapters to integrate with yet.

When tests land here they must:
  * be marked ``@pytest.mark.live`` so the default ``pytest`` run skips them
  * use public read-only endpoints only
  * never place an order, withdraw, deposit or modify any balance

Deterministic unit tests stay in ``tests/unit`` and must never depend on a live
API (AGENTS.md §50, §53).
"""
