# AGENTS.md

# Crypto Arbitrage Scanner — Engineering Constitution

This document defines the architecture, engineering standards, safety
constraints, financial correctness rules, development workflow, and
implementation boundaries for this project.

Claude Code and any other coding agent working on this repository MUST
follow these rules.

---

# 1. PROJECT IDENTITY

Project name:

    Crypto Arbitrage Scanner

Primary exchanges:

    CoinDCX
    KuCoin
    Binance

Primary objective:

    Build a READ-ONLY, real-market, cross-exchange cryptocurrency
    arbitrage intelligence and analysis system.

The system must determine whether a cross-exchange route can produce
a REALISTIC, EXECUTABLE NET INR PROFIT after applicable:

- market spread
- order-book depth
- slippage
- trading fees
- withdrawal fees
- network costs
- deposit constraints
- withdrawal constraints
- minimum order requirements
- minimum deposit requirements
- minimum withdrawal requirements
- quote-currency conversion costs
- applicable Indian TDS/tax treatment
- data freshness limitations
- liquidity constraints
- other measurable transaction costs

The fundamental principle is:

    CORRECTNESS > NUMBER OF OPPORTUNITIES

Do not optimize for displaying many opportunities.

Do not manufacture opportunities.

---

# 2. CURRENT PROJECT SCOPE

The initial system is strictly READ-ONLY.

The project MUST NOT:

- place live trades
- create live orders
- cancel live orders
- withdraw funds
- deposit funds
- transfer funds
- modify exchange balances
- execute financial transactions
- request withdrawal permissions
- request trading permissions unless explicitly required for
  read-only account information in a future approved phase

The current system is:

    MARKET DATA
        +
    MARKET ANALYSIS
        +
    ROUTE VALIDATION
        +
    EXECUTION SIMULATION
        +
    COST CALCULATION
        +
    NET PROFIT CALCULATION

Any future execution functionality must be designed and implemented
as a separate explicitly approved project phase.

---

# 3. PRIMARY ENGINEERING PRINCIPLE

Always follow:

    INSPECT
       ↓
    PLAN
       ↓
    IMPLEMENT
       ↓
    TEST
       ↓
    VERIFY
       ↓
    REPORT

Never skip inspection.

Never start coding immediately when the task involves modifying
existing architecture.

Before changing a module:

1. Read the relevant implementation.
2. Understand its responsibilities.
3. Identify dependencies.
4. Identify existing tests.
5. Determine the smallest required change.
6. Implement only that change.
7. Run targeted tests.
8. Run the relevant broader test suite.
9. Report exactly what changed.

---

# 4. DEVELOPMENT DISCIPLINE

Use incremental development.

DO NOT:

- perform broad rewrites
- restructure unrelated modules
- rename large portions of the project without justification
- replace working architecture unnecessarily
- introduce unnecessary frameworks
- add speculative abstractions
- implement future phases prematurely
- modify unrelated files
- remove tests simply because they fail after a change
- weaken assertions to make tests pass
- hide failures
- silently change financial assumptions

Prefer:

    smallest correct change

over:

    largest possible refactor

---

# 5. PROJECT PHASE CONTROL

The project is developed in controlled phases.

The current phase must always be explicitly identified.

Current phase:

    PHASE 0 — PROJECT SETUP + ARCHITECTURE FOUNDATION

Claude MUST NOT implement functionality belonging to later phases
unless explicitly instructed.

Planned phases:

    PHASE 0
        Project setup + architecture foundation

    PHASE 1
        Exchange abstraction

    PHASE 2
        CoinDCX adapter

    PHASE 3
        KuCoin adapter

    PHASE 4
        Binance adapter

    PHASE 5
        Dynamic market discovery

    PHASE 6
        Market normalization

    PHASE 7
        Live ticker + order-book engine

    PHASE 8
        Trading-fee engine

    PHASE 9
        Deposit / withdrawal / network engine

    PHASE 10
        INR / USDT / USDC conversion

    PHASE 11
        India TDS / tax engine

    PHASE 12
        Order-book execution simulator

    PHASE 13
        Slippage engine

    PHASE 14
        Multi-exchange route engine

    PHASE 15
        Net INR profit engine

    PHASE 16
        Opportunity scanner

    PHASE 17
        Testing and hardening

    PHASE 18
        Live read-only verification

    PHASE 19
        Final architecture + requirements audit

Do not skip phases without explaining why.

Do not silently combine multiple major phases.

If implementation reveals that the phase structure should change,
stop and explain the architectural reason before proceeding.

---

# 6. EXCHANGE ARCHITECTURE

Initial exchanges:

    CoinDCX
    KuCoin
    Binance

The system MUST use exchange adapters.

Conceptually:

    app/
        exchanges/
            base.py
            coindcx.py
            kucoin.py
            binance.py

The arbitrage engine MUST NOT contain exchange-specific API logic.

Exchange-specific implementation belongs inside the corresponding
adapter.

The core engine should operate through exchange-agnostic interfaces.

The architecture must allow another exchange to be added later
without rewriting the arbitrage engine.

---

# 7. EXCHANGE ABSTRACTION

The common exchange interface should expose capabilities such as:

- market discovery
- market metadata
- ticker retrieval
- order-book retrieval
- trading-fee retrieval
- withdrawal information
- deposit information
- network information
- market status
- precision information
- limits

Future capabilities may include:

- authenticated balances
- account-specific fees
- account configuration

but these are NOT part of the initial read-only implementation
unless explicitly approved.

Do not force every exchange to support capabilities that its API
does not provide.

Capabilities should be explicit.

If an exchange cannot provide a piece of information:

    UNKNOWN

must be represented explicitly.

Never fabricate a value.

---

# 8. NO EXCHANGE-SPECIFIC LOGIC IN CORE ENGINE

Avoid patterns such as:

    if exchange == "kucoin":
        ...

inside generic arbitrage logic.

Instead:

    ExchangeAdapter
        ↓
    normalized domain data
        ↓
    generic arbitrage engine

Exchange adapters translate exchange-specific API responses into
common domain models.

---

# 9. DYNAMIC ASSET DISCOVERY

Never hardcode a small asset list.

DO NOT create:

    SUPPORTED_ASSETS = ["XRP", "TRX", "SOL"]

Assets must be discovered dynamically from active exchange markets.

The system should be capable of discovering new assets without
requiring source-code changes.

Example:

    CoinDCX markets
          +
    KuCoin markets
          +
    Binance markets
          ↓
    normalized markets
          ↓
    common assets
          ↓
    route candidates

Specific assets such as XRP, TRX, SOL, BTC, ETH, USDT and USDC are
examples only.

---

# 10. MARKET NORMALIZATION

Exchange symbols must never be compared blindly.

A market must be represented structurally.

Conceptually:

    base_asset
    quote_asset
    exchange
    symbol
    market_type
    status
    price_precision
    quantity_precision
    minimum_quantity
    maximum_quantity
    minimum_notional

Example:

    XRP/INR

and:

    XRP/USDT

are NOT the same execution market.

They share the same base asset but have different quote currencies.

Never treat them as directly comparable prices.

---

# 11. QUOTE CURRENCY

Supported quote currencies may include:

- INR
- USDT
- USDC
- BTC
- ETH
- other exchange-supported spot quote currencies

The system MUST explicitly model quote currency.

Do not compare:

    XRP/INR

directly against:

    XRP/USDT

without an executable quote conversion.

Quote conversion itself may involve:

- bid/ask spread
- order-book depth
- slippage
- trading fees
- applicable tax/TDS
- liquidity constraints

Quote conversion must therefore be treated as an actual economic
operation, not a mathematical shortcut.

---

# 12. INR AS PRIMARY ACCOUNTING CURRENCY

INR is the primary reporting/accounting currency for V1.

Every complete arbitrage opportunity should ultimately be expressible as:

    Initial INR
    Final INR
    Net INR Profit
    Net ROI %

All intermediate currencies must remain explicitly represented.

Never mix:

    INR
    USDT
    USDC
    crypto assets

as though they were interchangeable.

---

# 13. CAPITAL

Capital must be configurable.

Do NOT hardcode:

    ₹800

Use configuration such as:

    INITIAL_CAPITAL_INR

Examples:

    800
    1000
    5000
    10000
    50000

The exact configured value belongs in configuration/environment,
not in arbitrage logic.

The same route may have different profitability at different
capital levels because of:

- liquidity
- slippage
- minimums
- fees
- withdrawal constraints

---

# 14. DECIMAL — ABSOLUTE REQUIREMENT

ALL financial calculations MUST use:

    decimal.Decimal

Never use binary floating point for:

- prices
- quantities
- balances
- fees
- trading costs
- withdrawal costs
- network costs
- TDS
- spreads
- slippage
- profit
- ROI
- order-book calculations
- quote conversions

Never do:

    float(price)

for financial computation.

Never do:

    round(float(...))

for financial computation.

Never store financial values internally as float.

External API numeric values must be parsed safely.

If an API returns numeric JSON values, preserve exact decimal
representation.

Python timing/network values may use float where appropriate, but
they MUST NEVER enter financial calculations.

---

# 15. DECIMAL TESTING

The test suite MUST protect the Decimal requirement.

Tests should detect accidental conversion of financial values to
float.

Financial domain models should preferably use:

    Decimal

directly.

Do not weaken Decimal requirements merely because an exchange API
returns JSON numbers.

---

# 16. MARKET DATA

Market data should collect, where available:

- bid
- ask
- last price
- order book
- available quantity
- timestamp
- exchange
- symbol
- quote currency
- base currency
- market status
- precision
- minimum quantity
- maximum quantity
- minimum notional

Last traded price is informational only.

Last price MUST NOT be used as the executable trade price.

---

# 17. ORDER-BOOK EXECUTION

For BUY operations:

    consume ASK levels

For SELL operations:

    consume BID levels

The system must simulate actual execution.

Example:

    ASK
    100 × 2 XRP
    101 × 5 XRP
    102 × 10 XRP

If capital requires more than 2 XRP, continue consuming deeper
levels.

The simulator must calculate:

- executable quantity
- quote amount spent
- average execution price
- remaining quantity
- liquidity consumed
- slippage
- partial fills

Never calculate arbitrage using only:

    best_bid
    best_ask

---

# 18. SLIPPAGE

Slippage must be explicitly modeled.

Distinguish:

    quoted price

from:

    executable average price

and:

    slippage

A route that appears profitable at the top of the order book may
become unprofitable after consuming deeper levels.

The scanner must calculate the latter.

---

# 19. LIQUIDITY

Every route must be evaluated against actual available liquidity.

Check:

- order-book depth
- available quantity
- minimum order
- maximum order
- minimum notional
- capital size
- transfer quantity
- withdrawal limits
- deposit limits

Do not report theoretical opportunities that cannot execute at the
configured capital size.

---

# 20. TRADING FEES

Trading fees must be exchange-specific.

Support:

- CoinDCX fees
- KuCoin fees
- Binance fees

Where applicable, support:

- maker
- taker
- pair-specific fees
- asset-specific fees
- account-tier-dependent fees
- exchange discounts

Do not blindly assume a universal fee.

Prefer official exchange APIs.

If an exchange requires authentication for the user's exact fee
tier, support explicit configuration.

Never silently invent a fee.

Every fee used in profitability calculations should have an identifiable
source/configuration origin.

---

# 21. WITHDRAWAL FEES

Withdrawal fees are route-specific.

Model:

- source exchange
- asset
- network
- withdrawal fee
- minimum withdrawal
- maximum withdrawal where relevant
- withdrawal availability
- destination compatibility
- fee source
- fee timestamp
- data freshness

Prefer official live exchange data.

If only official static documentation is available:

- mark the value as static
- timestamp it
- identify the source
- allow configuration where appropriate
- do not pretend it is live

Never use an invented withdrawal fee.

---

# 22. NETWORK IDENTITY

A transfer is identified by:

    ASSET + NETWORK

not merely:

    ASSET

Examples:

    USDT + TRC20

    USDT + ERC20

    XRP + XRP Ledger

are different transfer routes.

A transfer is executable only when:

    source supports asset/network

AND

    destination supports asset/network

AND

    withdrawal is enabled

AND

    deposit is enabled

AND

    required constraints are satisfied

---

# 23. NETWORK COMPATIBILITY

Never assume:

    USDT → USDT

means a transferable route.

Network compatibility must be explicitly checked.

The same asset may exist on multiple networks with different:

- withdrawal fees
- deposit requirements
- minimums
- confirmation times
- availability

---

# 24. DEPOSIT REQUIREMENTS

Model, where available:

- minimum deposit
- deposit availability
- supported network
- confirmation requirements
- address requirements
- memo/tag requirements
- destination constraints

If a destination requires:

    address + memo/tag

the route model must represent that requirement.

Never assume an address alone is sufficient.

---

# 25. WITHDRAWAL REQUIREMENTS

Model:

- minimum withdrawal
- maximum withdrawal
- withdrawal fee
- network
- availability
- precision
- destination compatibility
- memo/tag requirements
- estimated transfer time where available

If:

    transferable quantity < minimum withdrawal

the route is invalid.

---

# 26. TRANSFER CALCULATION

The basic transfer calculation is:

    source quantity
        -
    withdrawal/network fee
        =
    destination quantity

Then:

    destination quantity >= destination minimum deposit

must be verified.

If this fails:

    route = INVALID

Do not calculate a fake profit for the route.

---

# 27. MEMO / TAG

Some assets may require:

- memo
- destination tag
- payment ID
- similar destination metadata

The route model must represent this requirement.

If required destination metadata cannot be safely verified:

    route = CANNOT_VERIFY

or:

    route = INSUFFICIENT_DATA

Do not assume it is unnecessary.

---

# 28. TDS / INDIAN TAX

Indian tax/TDS handling must be treated as a separate subsystem.

Do NOT hardcode:

    TDS = 1%

without current authoritative verification.

The tax subsystem must distinguish:

- transaction type
- applicable rate
- who deducts it
- when it is deducted
- whether the exchange already withholds it
- whether it applies to the transaction
- thresholds/exemptions where relevant
- jurisdiction
- effective date
- source
- verification date

TDS must never be silently combined with trading fees.

---

# 29. TDS DOUBLE-COUNTING

The system must explicitly prevent double-counting.

If an exchange already deducts a tax/TDS amount from the transaction,
the profitability engine must not subtract the same amount again as
an independent cost.

The tax calculation should expose enough metadata to determine whether
the amount is:

- withheld
- already reflected in proceeds
- an additional economic cost
- informational only

Unknown tax treatment must remain:

    UNKNOWN

Do not guess.

---

# 30. TAX ARCHITECTURE

Tax logic must not be embedded directly into exchange API clients.

Conceptually:

    app/
        taxes/
            base.py
            india.py
            coindcx.py
            kucoin.py
            binance.py

The exact structure may evolve during architecture implementation,
but the principle remains:

    exchange API
        ≠
    tax policy

---

# 31. INR ENTRY

If a route begins with INR:

Do NOT calculate:

    INR / displayed_price

alone.

The entry calculation must account for:

- order-book execution
- spread
- slippage
- trading fee
- applicable TDS
- other verified costs

The result should provide an effective acquisition cost.

---

# 32. INR EXIT

When the route exits into INR:

Calculate:

    gross INR proceeds
        -
    trading fee
        -
    applicable TDS
        -
    slippage
        -
    other verified costs
        =
    final net INR

This final INR value is the important output.

---

# 33. PROFIT

The fundamental calculation is:

    NET PROFIT
        =
    FINAL NET INR
        -
    INITIAL INR

And:

    NET ROI %
        =
    NET PROFIT / INITIAL INR × 100

Use Decimal throughout.

Do not calculate ROI from floating-point values.

---

# 34. PROFITABILITY THRESHOLDS

The system should support configurable filters such as:

    MIN_NET_PROFIT_INR
    MIN_NET_ROI_PERCENT

A positive gross spread is NOT sufficient.

Example:

    Gross spread = positive

but:

    fees + TDS + transfer + slippage > spread

Then:

    route = NEGATIVE_AFTER_FEES

---

# 35. ROUTE ENGINE

The route engine must support both directions.

Examples:

    CoinDCX → KuCoin
    KuCoin → CoinDCX

    CoinDCX → Binance
    Binance → CoinDCX

    KuCoin → Binance
    Binance → KuCoin

Do not hardcode a preferred direction.

The market data determines the economically viable direction.

A route should contain:

- entry exchange
- entry market
- entry quote
- entry asset
- entry execution
- transfer asset
- transfer network
- withdrawal
- destination exchange
- destination market
- exit execution
- final quote
- quote conversion if required
- final INR value

---

# 36. ROUTE VALIDATION BEFORE PROFIT

Route validation MUST happen before profitability calculation.

Conceptually:

    Discover market
        ↓
    Normalize market
        ↓
    Validate route
        ↓
    Validate network
        ↓
    Validate withdrawal
        ↓
    Validate deposit
        ↓
    Validate minimums
        ↓
    Check liquidity
        ↓
    Simulate execution
        ↓
    Calculate fees
        ↓
    Calculate tax
        ↓
    Calculate final INR
        ↓
    Calculate profit

Do not calculate a positive-looking profit first and validate
constraints afterward.

---

# 37. MARKET DISCOVERY

Market discovery must be dynamic.

Pipeline:

    Exchange markets
          ↓
    normalized market models
          ↓
    active spot markets
          ↓
    common assets
          ↓
    quote-compatible candidates
          ↓
    route candidates

Do not hardcode assets.

Do not hardcode exchange market lists.

---

# 38. MULTI-EXCHANGE ROUTES

The initial exchange matrix is:

    CoinDCX ↔ KuCoin
    CoinDCX ↔ Binance
    KuCoin ↔ Binance

Every valid direction should be evaluated.

The scanner must not globally rank exchanges.

Routes are evaluated independently.

---

# 39. DATA FRESHNESS

Every market-data object MUST include:

    timestamp

Where possible also include:

    source
    received_at
    exchange
    symbol
    data_type

Support:

    MAX_DATA_AGE_SECONDS

If critical data is too old:

    STALE_DATA

Do not display stale routes as executable opportunities.

---

# 40. SYNCHRONIZATION

Cross-exchange arbitrage requires comparing data from multiple venues.

The engine should track data timestamps separately.

Do not compare:

    fresh KuCoin order book

against:

    stale CoinDCX order book

and call the result current.

Where possible, route evaluation should use a bounded data-age
window.

---

# 41. API RATE LIMITING

Exchange APIs must be treated as rate-limited systems.

Implement/plan for:

- request timeouts
- connection errors
- HTTP errors
- rate-limit responses
- Retry-After
- exponential backoff
- bounded retries
- concurrency limits
- partial failures

Do not hammer public exchange APIs.

Avoid unnecessary requests.

Cache data where appropriate without compromising freshness.

---

# 42. FAILURE ISOLATION

One failed market MUST NOT crash the entire scanner.

Handle:

- exchange downtime
- timeout
- rate limit
- malformed response
- missing market
- missing order book
- missing fee
- missing withdrawal data
- unavailable network
- stale data
- authentication failure
- partial exchange response

Failures should be represented explicitly and logged.

---

# 43. NO FAKE DATA

NEVER guess:

- price
- fee
- TDS
- withdrawal fee
- network fee
- minimum deposit
- minimum withdrawal
- network availability
- liquidity
- transfer time

If information cannot be verified:

    DATA_UNAVAILABLE

or:

    CANNOT_VERIFY

A false negative is preferable to a fake opportunity.

---

# 44. DATA SOURCE PROVENANCE

Important financial inputs should retain provenance.

Where practical, record:

    source
    endpoint/documentation
    retrieved_at
    effective_at
    live/static
    verification status

This is especially important for:

- fees
- withdrawal fees
- network information
- tax rules
- minimums

---

# 45. SECURITY

Never hardcode:

- API keys
- API secrets
- passwords
- private keys
- withdrawal credentials

Use environment variables.

Provide:

    .env.example

Never commit:

    .env

or real secrets.

The initial project should prefer public APIs.

If authentication is required later:

- use least privilege
- prefer read-only permissions
- document required permissions
- never request withdrawal permission for the scanner

---

# 46. CONFIGURATION

Runtime configuration belongs in configuration/environment handling.

Examples:

    INITIAL_CAPITAL_INR
    MIN_NET_PROFIT_INR
    MIN_NET_ROI_PERCENT
    MAX_DATA_AGE_SECONDS
    REQUEST_TIMEOUT_SECONDS
    MAX_RETRIES

Do not scatter configuration constants throughout business logic.

Do not hardcode user-specific capital inside algorithms.

---

# 47. MODELS

Domain models should be explicit and strongly typed.

Prefer immutable/value-oriented models where appropriate.

Financial fields should use:

    Decimal

Important model categories include:

- Exchange
- MarketDefinition
- Asset
- QuoteCurrency
- OrderBook
- OrderBookLevel
- TradeExecution
- Fee
- TaxRule
- Withdrawal
- Deposit
- Network
- TransferRoute
- Route
- RouteValidation
- RouteExecution
- Opportunity

Exact names may evolve.

Do not create models that exist only to satisfy a speculative future feature.

---

# 48. SEPARATION OF CONCERNS

Keep these concerns separate:

    Exchange API
        ↓
    Normalization
        ↓
    Market data
        ↓
    Execution simulation
        ↓
    Transfer validation
        ↓
    Fee calculation
        ↓
    Tax calculation
        ↓
    Quote conversion
        ↓
    Route calculation
        ↓
    Opportunity evaluation
        ↓
    Reporting

Do not put all logic inside exchange adapters.

Do not put API calls inside financial calculation functions.

Do not mix CLI formatting with financial calculations.

---

# 49. PURE FINANCIAL FUNCTIONS

Where practical, financial calculations should be implemented as
pure deterministic functions.

Given:

    inputs

they should return:

    result

without making network requests.

This makes financial calculations easy to test.

---

# 50. LIVE API VS UNIT TESTS

Unit tests MUST NOT depend on live exchange APIs.

Use deterministic fixtures/mocks for:

- order books
- markets
- fees
- taxes
- withdrawal data
- deposit data
- network data

Live APIs belong only in explicit integration tests.

---

# 51. TESTING REQUIREMENTS

The test suite must eventually cover:

### Decimal

- Decimal arithmetic
- no financial float usage
- precision behavior

### Markets

- market normalization
- symbol normalization
- quote separation
- active/inactive markets

### Order books

- buy execution
- sell execution
- multiple levels
- partial fills
- insufficient liquidity
- exact fills

### Slippage

- quoted price
- executable price
- slippage calculation
- deep-book impact

### Fees

- trading fees
- withdrawal fees
- maker/taker
- missing fee data

### Tax

- TDS calculation
- transaction types
- withholding
- double-count prevention
- unknown tax treatment

### Transfers

- minimum withdrawal
- minimum deposit
- withdrawal fee
- network matching
- unavailable network
- memo/tag requirement

### Routes

- valid route
- invalid route
- both directions
- missing markets
- incompatible quote currencies

### Profit

- positive profit
- negative profit
- zero profit
- ROI
- capital-size differences

### Freshness

- fresh data
- stale data
- mixed-age data

### Failures

- API failure
- timeout
- rate limit
- malformed response
- partial response

---

# 52. TEST INTEGRITY

Never make a test pass by weakening or deleting the assertion.

Never remove a failing test without an explicit architectural reason.

When behavior changes intentionally:

1. Explain why.
2. Update the implementation.
3. Update the test.
4. Preserve coverage.

Tests are part of the architecture.

---

# 53. LIVE INTEGRATION TESTS

Live integration tests may be used for:

- API connectivity
- market discovery
- real market schema verification
- read-only order books
- public exchange endpoints

They MUST NOT:

- place orders
- withdraw
- deposit
- modify balances

Live tests should be clearly separated from deterministic unit tests.

---

# 54. CLI / REPORTING

The reporting layer should clearly distinguish:

    GROSS SPREAD

from:

    EXECUTABLE RESULT

and:

    NET PROFIT

Example:

    XRP
    ─────────────────────────

    Direction:
        CoinDCX → KuCoin

    Initial Capital:
        ₹1,000

    Entry:
        ...

    Executable Entry:
        ...

    Quantity:
        ...

    Trading Fees:
        ...

    TDS:
        ...

    Withdrawal:
        ...

    Destination Quantity:
        ...

    Exit:
        ...

    Slippage:
        ...

    Quote Conversion:
        ...

    Final INR:
        ...

    NET PROFIT:
        ...

    NET ROI:
        ...

    Status:
        EXECUTABLE

Do not display theoretical spread as though it were realized profit.

---

# 55. STATUS VALUES

Use explicit machine-readable statuses.

Examples:

    EXECUTABLE
    NEGATIVE_AFTER_FEES
    INSUFFICIENT_LIQUIDITY
    NETWORK_UNAVAILABLE
    BELOW_MIN_WITHDRAWAL
    BELOW_MIN_DEPOSIT
    STALE_DATA
    MISSING_FEE_DATA
    MISSING_TAX_DATA
    MISSING_NETWORK_DATA
    INVALID_ROUTE
    API_ERROR
    DATA_UNAVAILABLE
    CANNOT_VERIFY

Avoid vague statuses such as:

    "probably profitable"

---

# 56. LOGGING

Logging should explain what the scanner is doing.

Example:

    [COINDCX]
    Markets discovered: ...

    [KUCOIN]
    Markets discovered: ...

    [BINANCE]
    Markets discovered: ...

    [MATCHING]
    Common assets: ...

    [ROUTES]
    Candidate routes: ...

    [FILTER]
    Rejected: insufficient liquidity: ...

    [FILTER]
    Rejected: network unavailable: ...

    [FILTER]
    Rejected: stale data: ...

    [FILTER]
    Rejected: negative after fees: ...

    [OPPORTUNITY]
    Asset: XRP
    Direction: CoinDCX → KuCoin
    NET PROFIT: ...
    ROI: ...

Never hide why a route was rejected.

---

# 57. HISTORICAL OPPORTUNITY DESIGN

V1 does not require a database unless explicitly approved.

However, opportunity models should be designed so they can eventually
be persisted.

Potential future fields:

- timestamp
- asset
- route
- market prices
- order-book snapshot metadata
- fees
- TDS
- withdrawal cost
- slippage
- final INR
- net profit
- ROI
- status

Do not introduce unnecessary database infrastructure prematurely.

---

# 58. DEX FUTURE COMPATIBILITY

Future DEX support may be considered.

Do not implement DEX support in V1.

Avoid architecture that makes future liquidity-source abstraction
impossible.

Where appropriate, distinguish concepts such as:

    Venue
    Exchange
    Market
    LiquiditySource

But do not over-engineer this before the centralized-exchange
scanner works correctly.

---

# 59. DOCUMENTATION

Important architectural decisions should be documented.

Use:

    docs/

for architecture and design documentation.

Potential documents:

    docs/architecture/
    docs/exchanges/
    docs/decisions/

Do not create excessive documentation for trivial code.

Document decisions that affect correctness, financial assumptions,
or system architecture.

---

# 60. DEPENDENCY DISCIPLINE

Do not add dependencies casually.

Before adding a package:

1. Determine whether the standard library is sufficient.
2. Determine whether an existing dependency already provides the
   required functionality.
3. Check whether the dependency is actively maintained.
4. Explain why it is required.
5. Keep the dependency scope minimal.

Avoid unnecessary frameworks.

---

# 61. CODE QUALITY

Prefer:

- explicit types
- small functions
- deterministic calculations
- meaningful names
- clear domain models
- narrow interfaces
- isolated side effects
- testable logic

Avoid:

- giant functions
- hidden global state
- magic numbers
- silent defaults
- implicit currency conversion
- implicit network assumptions
- exchange-specific conditionals in generic code

---

# 62. ERROR HANDLING

Errors should preserve useful context.

A financial calculation should not silently return:

    0

when data is missing.

Missing data should be distinguishable from an actual zero value.

For example:

    fee = 0

and:

    fee = UNKNOWN

are NOT equivalent.

Never convert missing financial information into zero merely to
continue the calculation.

---

# 63. UNKNOWN VS ZERO

This is a critical financial correctness rule.

These are different:

    ZERO

    UNKNOWN

    NOT_APPLICABLE

For example:

    withdrawal_fee = 0

means:

    verified withdrawal fee is zero.

Whereas:

    withdrawal_fee = UNKNOWN

means:

    withdrawal fee could not be verified.

Never substitute one for another.

---

# 64. NO SILENT FALLBACKS

Do not implement:

    fee = api_fee or Decimal("0")

unless zero is explicitly verified as the correct fallback.

Do not implement:

    withdrawal_fee = missing_fee or Decimal("0")

Do not implement:

    tds = missing_tds or Decimal("0")

Do not implement:

    network = missing_network or "default"

Missing financial data must remain missing.

---

# 65. ROUTE CONFIDENCE

The scanner should distinguish:

    fully verified route

from:

    partially verified route

and:

    insufficient data

Do not label a route:

    EXECUTABLE

unless all required executable conditions are verified.

---

# 66. REAL-MARKET CORRECTNESS

The goal is NOT:

    biggest theoretical spread

The goal is:

    executable transfer-compatible route
    with sufficient liquidity
    after real costs
    producing verified net INR profit

This principle overrides optimization for speed or opportunity count.

---

# 67. NO FINANCIAL ADVICE CLAIMS

The software is an analytical tool.

Do not build language that guarantees:

- profit
- execution
- returns
- successful transfer
- tax outcomes

The scanner reports calculated results based on available data and
explicit assumptions.

---

# 68. SOURCE VERIFICATION

For exchange-specific information, prefer:

1. Official exchange API
2. Official exchange documentation
3. Official regulatory/government source for tax
4. Other sources only when necessary and clearly identified

Never silently rely on an unofficial source for a critical financial
assumption when an official source is available.

---

# 69. CURRENT PHASE — PHASE 0

The project is currently in:

    PHASE 0 — PROJECT SETUP + ARCHITECTURE FOUNDATION

Phase 0 responsibilities:

- initialize repository
- create Python project
- establish package structure
- establish configuration system
- establish environment template
- establish testing infrastructure
- establish lint/type-check tooling as appropriate
- create AGENTS.md
- create initial README
- document architecture
- establish Git baseline
- verify clean project setup

Phase 0 MUST NOT implement:

- exchange API integrations
- arbitrage calculations
- live trading
- withdrawals
- deposits
- profitability engine
- TDS calculation
- route execution
- opportunity ranking

unless explicitly approved as part of a revised phase plan.

---

# 70. PHASE COMPLETION REQUIREMENTS

A phase is complete only when:

1. Required implementation exists.
2. Relevant tests exist.
3. Tests pass.
4. Relevant validation has been performed.
5. No unrelated changes were introduced.
6. Known limitations are documented.
7. The implementation matches the phase definition.
8. The result has been reported clearly.

Do not say:

    "Phase complete"

merely because:

    "the code runs."

---

# 71. PHASE REPORT FORMAT

At the end of every phase, report:

## What changed

List the implementation changes.

## Files changed

List every added/modified/deleted file.

## Why

Explain the architectural reason.

## Tests added

List relevant tests.

## Tests executed

Report exact commands and results.

## Live verification

If applicable, explain exactly what was verified.

## Remaining limitations

List known limitations.

## Next phase

State the next planned phase.

Do not claim anything was verified if it was not actually verified.

---

# 72. VERIFICATION BEFORE COMPLETION

Before claiming a task is complete:

- run the relevant tests
- inspect failures
- verify expected behavior
- inspect the final diff
- check for accidental changes
- check for debug code
- check for secrets
- check for financial floats
- check for silent defaults
- check for unrelated modifications

Evidence comes before completion claims.

---

# 73. GIT DISCIPLINE

Use Git checkpoints at meaningful milestones.

Before major implementation:

    git status

After a validated phase:

    review diff
    run tests
    create an intentional commit

Do not commit:

- secrets
- .env files
- generated credentials
- temporary debugging files

Commit messages should describe the actual change.

---

# 74. SECRET SAFETY

Before every commit, verify that the repository does not contain:

- API keys
- API secrets
- passwords
- private keys
- authentication tokens
- exchange credentials

The `.env.example` file may contain placeholders.

The actual `.env` file MUST NOT be committed.

---

# 75. PERFORMANCE

Do not optimize prematurely.

Correctness comes first.

When performance becomes relevant, measure first.

Potential future optimizations may include:

- concurrent market requests
- order-book batching
- caching
- WebSockets
- incremental updates

Do not introduce these before the architecture requires them.

---

# 76. WEBSOCKETS

WebSockets may eventually be useful for high-frequency market data.

They are NOT required for the initial architecture unless a phase
explicitly calls for them.

Start with reliable REST/public market-data endpoints where practical.

Do not introduce WebSockets merely because they sound more advanced.

---

# 77. DATABASE

Do not introduce a database merely because future history may require one.

V1 should remain as simple as practical.

A database can be introduced when:

- opportunity history becomes a requirement
- persistence becomes necessary
- analytics requires historical storage

Until then, keep the domain model persistence-friendly without
unnecessary infrastructure.

---

# 78. API CREDENTIALS

Public market-data endpoints should be preferred.

If an authenticated endpoint is required for:

- account-specific fees
- balances
- private configuration

then:

- document why
- use environment variables
- request minimum permissions
- never request withdrawal permissions
- never request trading permissions unless explicitly approved

---

# 79. CAPITAL LOCATION

Do not assume the same capital exists simultaneously on all exchanges.

Future architecture should support:

    capital location

such as:

    INR on CoinDCX
    USDT on KuCoin
    USDT on Binance

For V1, capital location may be configuration-driven.

Do not implement live balance management until explicitly approved.

---

# 80. ARBITRAGE DIRECTION

Never hardcode:

    Buy on KuCoin
    Sell on CoinDCX

or:

    Buy on CoinDCX
    Sell on KuCoin

The scanner must evaluate both directions.

Likewise:

    CoinDCX ↔ Binance
    KuCoin ↔ Binance

must be evaluated.

The market determines the direction.

---

# 81. OPPORTUNITY DEFINITION

A route is an opportunity only when:

- required markets exist
- required market data is fresh
- order-book liquidity is sufficient
- execution can be simulated
- required fees are known
- required transfer data is known
- network compatibility is verified
- minimums are satisfied
- destination requirements are satisfied
- quote conversion is executable where needed
- applicable tax treatment is sufficiently verified
- final INR result can be calculated

If critical information is missing:

    do not manufacture an opportunity.

---

# 82. MOST IMPORTANT QUESTION

The scanner ultimately exists to answer:

    "For ₹X of capital, using current real-market conditions,
     which valid route involving CoinDCX, KuCoin and/or Binance
     can produce the highest VERIFIED executable NET INR result
     after all applicable costs?"

The answer must be based on:

- executable prices
- order-book depth
- slippage
- trading fees
- TDS
- withdrawal costs
- network costs
- deposit requirements
- withdrawal requirements
- minimums
- quote conversion
- liquidity
- freshness

Not merely displayed price differences.

---

# 83. ABSOLUTE PROHIBITIONS

Claude MUST NOT:

1. Place live orders.
2. Withdraw funds.
3. Deposit funds.
4. Transfer funds.
5. Modify exchange balances.
6. Hardcode financial assumptions.
7. Use float for financial calculations.
8. Invent missing fees.
9. Invent missing tax rates.
10. Invent network availability.
11. Treat missing data as zero.
12. Use last price as execution price.
13. Use best bid/ask alone for meaningful capital calculations.
14. Hardcode a tiny asset list.
15. Assume one arbitrage direction.
16. Treat different quote currencies as identical.
17. Ignore withdrawal costs.
18. Ignore network compatibility.
19. Ignore minimum deposits.
20. Ignore minimum withdrawals.
21. Ignore stale data.
22. Hide route rejection reasons.
23. Remove tests to make the suite pass.
24. Weaken financial correctness to improve performance.
25. Perform broad rewrites without explicit architectural justification.
26. Implement future phases prematurely.
27. Commit secrets.
28. Claim verification that was not performed.
29. Claim profitability based on incomplete data.
30. Manufacture an arbitrage opportunity.

---

# 84. DEFAULT DECISION RULE

When uncertain between:

    more opportunities

and:

    more correctness

choose:

    more correctness.

When uncertain between:

    guessed value

and:

    UNKNOWN

choose:

    UNKNOWN.

When uncertain between:

    broad rewrite

and:

    smallest correct change

choose:

    smallest correct change.

When uncertain between:

    premature implementation

and:

    explicit architectural decision

choose:

    architectural decision first.

When uncertain between:

    theoretical profit

and:

    executable verified profit

choose:

    executable verified profit.

---

# 85. FINAL PRINCIPLE

This project is not a "spread finder."

It is not a trading bot.

It is not a price comparison script.

It is a:

    READ-ONLY
    REAL-MARKET
    CROSS-EXCHANGE
    EXECUTION-AWARE
    COST-AWARE
    TRANSFER-AWARE
    TAX-AWARE
    LIQUIDITY-AWARE
    NET-PROFIT
    ARBITRAGE INTELLIGENCE SYSTEM.

The system must prefer:

    NO OPPORTUNITY

over:

    FALSE OPPORTUNITY.

Build for correctness first.
Build incrementally.
Verify everything.
Never invent financial data.

💯
