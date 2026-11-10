# Security events, earnings comparisons and contingent claims

Use this note to interpret financial quantities before applying a prescribed data recipe. Explicit contract and data definitions determine adjustment, classification and settlement. These concepts do not replace a supplied algorithm or invent an undefined business metric.

## Splits, dividends and share units

For a split with ratio $R>0$ new shares per old share, economic ownership is unchanged by the split itself. The share-count and theoretical ex-split price transformations are:

$$
n_{\mathrm{new}}=Rn_{\mathrm{old}},\qquad
P_{\mathrm{new}}=P_{\mathrm{old}}/R
$$

Historical volume expressed in new-share units changes by the inverse price factor. A dividend per old share and a dividend per new share cannot be added without a common share basis. A cash dividend moves value from the company to the shareholder; its ex-date, record date and payment date are distinct. A backward-adjusted price is a constructed series, not the historical transaction price. Vendor formulas can use different reference prices and reinvestment assumptions.

For one share held across an interval with no split, initial price $P_0$, final price $P_1$ and cash dividend $D$, the simple holding-period return before costs is:

$$
R=\frac{P_1+D-P_0}{P_0}
$$

With splits, first express the final holding and all distributions in consistent units. Summing raw dividend labels is not automatically the cash received per original share.

## Earnings surprise

Let $A$ be reported EPS and $E$ a comparable consensus estimate. Their unscaled surprise is:

$$
U=A-E
$$

The EPS definition, share basis, currency, fiscal period and information date must agree. Dividing by analyst-estimate dispersion and dividing by the historical variability of seasonal earnings changes produce different standardized surprises. Neither denominator is automatically the standard error of the consensus mean. A zero denominator does not mathematically define a finite standardized score; a stipulated fallback remains a reporting convention. Percentage surprise with a near-zero benchmark is unstable, even when a deterministic classification rule is provided.

## Complementary event claims

Let $I$ indicate a defined event. A unit YES claim pays $I$ and its truly complementary NO claim pays $1-I$ at the same settlement date. Their combined payoff is:

$$
I+(1-I)=1
$$

With discount factor $D(t,T)$, matched settlement and no costs or counterparty friction, combined value is $D(t,T)$. Different event definitions, cancellation terms, settlement currencies or payment dates can break the apparent complementarity. Quote dislocation is not automatically executable arbitrage: fees, liquidity, funding, outcome disputes and venue credit risk can matter. Trading close time, event resolution time and cash settlement time are different clocks. A settled receivable is not necessarily immediately reusable cash.

## Debt and equity offering sizes

An offering announced with an underwriters' or initial purchasers' option (over-allotment, greenshoe) has a base size and a final size. When a filing says the total issued "includes" an amount sold under the full or partial exercise of that option, the base size is the total minus the exercised amount. Report the size the task asks for (base, before over-allotment, or total, including it) and quote the sentence that splits them.

## Availability and measurement

A filing's fiscal period identifies what it measures; publication time identifies when it can first enter a contemporaneous information set. An amendment changes available knowledge from its own availability date, unless the analysis explicitly uses a revised-history dataset. Same-period facts with different units, consolidation scope or duration do not become comparable merely by sharing a label. Signal dates, active positions and realized return periods must refer to the same economic timeline.

## References

[Investor.gov, Stock Split](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock-split), unchanged proportional ownership. [SEC, EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), submissions and structured fact context. The holding-return and complementary-payoff identities are direct cashflow accounting.
