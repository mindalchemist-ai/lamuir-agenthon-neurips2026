# Structured notes: payoff units, participation and position risk

Use this note for a note assembled from debt and option exposure. The term sheet determines principal repayment, option direction, strike, barrier type, monitoring, rebate and settlement. Explicit definitions take precedence; a list of strikes and barriers alone does not specify a payoff.

## Payoff and participation units

Let $N$ be principal in currency, $S_{\mathrm{ref}}>0$ a fixed reference asset price, $p$ a dimensionless participation rate, and $g$ an option payoff in asset-price units. Suppose the contract repays $N$ plus $p$ times a normalized option payoff. Its maturity cashflow is:

$$
H_T=N+\frac{Np}{S_{\mathrm{ref}}}g
$$

Thus the option-unit count is $n=Np/S_{\mathrm{ref}}$, not $Np$, for this particular normalization. A contract normalized by strike, a return index or a price-per-hundred quote gives a different count. The normalization must come from the payoff definition, not from a desired output magnitude.

For a down-and-out call with zero rebate and its stated monitoring interval $\mathcal T$, the option payoff is:

$$
g=(S_T-K)^+\mathbf1\left\{\min_{u\in\mathcal T}S_u>B\right\}
$$

Here $K$ is strike and $B$ the barrier. Inclusive versus strict touching, discrete versus continuous monitoring, an already-breached barrier and any rebate change the contract. A knock-in uses the complementary barrier event; neither can be inferred from the word barrier alone.

The embedded option position is therefore $Np/S_{\mathrm{ref}}$ units of the option on one share, not N options and not a round count; check its value against N times p times the option's value per unit of $S_{\mathrm{ref}}$. A computed markup or issuer margin that comes out negative is a result to report, not a value to clip at zero.

## Component value and price basis

If principal is a default-free payment at $T$, with discount factor $D(t,T)$, and $v_g$ is the present value of one unit of $g$, the note value is:

$$
V=N D(t,T)+n v_g
$$

Credit-risky principal requires issuer credit/recovery treatment. Principal protection at maturity does not guarantee secondary-market value or eliminate default risk. Historical GARCH forecasts do not automatically identify risk-neutral pricing volatility; using one as a pricing input is a modelling assumption.

For issue price $P$, a markup over fair value and an issue-price margin have different denominators:

$$
\mathrm{markup}_{V}=\frac{P-V}{V},\qquad
\mathrm{margin}_{P}=\frac{P-V}{P}
$$

Neither is defined by a price label alone. Multiply a ratio by $100$ only for a percentage quote. A fair value per currency unit and a price per hundred principal also have different scales.

## Breakeven volatility

For a specified target price $P$ and all other terms fixed, a breakeven volatility solves:

$$
N D(t,T)+n v_g(\sigma)-P=0
$$

A barrier option can have nonmonotone value in volatility: greater volatility can increase the vanilla payoff while increasing knock-out probability. A breakeven can therefore be absent or nonunique. A root is meaningful only in its admissible volatility domain and under the stated payoff; a boundary optimizer or a residual minimum is not automatically a zero-price-error root.

## Fixed-position Greeks and losses

When $N,n$ are fixed contractual holdings and bond value has no spot dependence, note Delta is:

$$
\Delta_{\mathrm{note}}=n\Delta_g
$$

The denominator $S_{\mathrm{ref}}$ fixed at issuance is not recomputed whenever spot is bumped. Recalculating the unit count gives the sensitivity of a newly issued family, rather than the existing note. Bond rate sensitivity, option rate sensitivity and issuer credit sensitivity remain separate.

For horizon $h$ and an existing position held through that horizon, define loss using rolled value and interim cash distributions $C_h$:

$$
L_h=V_t-\left(V_{t+h}+C_h\right)
$$

Financing can add a separate cashflow under the chosen P&L convention. Full revaluation changes remaining maturity and preserves barrier history. A Delta/Gamma/Vega expansion is local; barrier crossings and discontinuities can invalidate it. VaR and ES use a physical loss distribution, not the risk-neutral probabilities used merely to price the note. Losses in currency, loss fractions of current value and loss fractions of principal are distinct quantities.

## References and limits

[SEC Investor Bulletin: Structured Notes](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-76), payoff terms, participation and issuer-credit limitations. The component, unit-count, markup and Greek expressions above are cashflow identities under the explicitly stated payoff. Analytic barrier valuation, conditional-volatility estimation and quadratic risk moments are separate methods; this note does not choose an unspecified contract for them.
