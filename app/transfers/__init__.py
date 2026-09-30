"""Network, deposit and withdrawal compatibility (Phase 9). Empty by design in Phase 0.

Boundary rules:
  * a transfer is identified by ASSET + NETWORK, never by asset alone: USDT-TRC20
    and USDT-ERC20 are different transfer routes (AGENTS.md §22)
  * a transfer is executable only when the source supports the asset/network AND
    the destination supports it AND withdrawal is enabled AND deposit is enabled
    AND every minimum is satisfied
  * ``source quantity - withdrawal/network fee = destination quantity``, and the
    destination quantity must then clear the destination minimum deposit
  * a required memo / destination tag that cannot be verified makes the route
    CANNOT_VERIFY, never "probably fine" (AGENTS.md §27)
  * missing network data is MISSING_NETWORK_DATA, never a default network
"""
