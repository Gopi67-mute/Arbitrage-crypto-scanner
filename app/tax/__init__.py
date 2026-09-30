"""Tax / TDS policy (Phase 11). Empty by design in Phase 0.

Tax policy is deliberately separate from exchange API clients: an exchange
client reports what the venue returns, a tax module encodes jurisdiction rules
(AGENTS.md §30).

Boundary rules:
  * no rate is hardcoded without an authoritative, dated, cited source. In
    particular "TDS = 1%" is NOT to be written into this package on the strength
    of a recollection (AGENTS.md §28)
  * every rule records jurisdiction, transaction type, effective date, source and
    verification date
  * the model must expose whether an amount is withheld by the exchange, already
    reflected in proceeds, an additional economic cost, or informational — so the
    profit engine cannot double-count it (AGENTS.md §29)
  * unknown tax treatment stays UNKNOWN
"""
