# Collateralized cross-currency cashflows and resetting notionals

Use this note for multi-currency coupon streams, FX-reset principal and spread risk. Contractual exchange directions, reset dates, fixings, settlement and collateral currency determine the cashflows. Explicit task conventions take precedence. The deterministic formulas below are not a general stochastic reset-convexity model.

## Currency-consistent present value

Let domestic currency be collateral currency, $S$ instantaneous domestic units per foreign unit, $D_d(t,T)$ the domestic discount factor, and $F(t,T)$ the collateral-consistent FX forward. A known foreign cashflow $C_f$ paid at $T$ has domestic value:

$$
\mathrm{PV}_d(C_f,T)=D_d(t,T)F(t,T)C_f
$$

Define the foreign discount curve under domestic collateral by:

$$
D_{f\mid d}(t,T)=\frac{D_d(t,T)F(t,T)}S
$$

Then the same value is $S D_{f\mid d}(t,T)C_f$. A foreign domestic-collateral curve generally differs from that currency's own-collateral OIS curve. Using an observed FX forward and then applying an extra basis multiplier can count the same basis twice.

Implied cross-currency basis. With S in domestic units per foreign unit, the no-basis forward is $F_{\mathrm{CIP}}=S\,D_f/D_d$; the currency with the higher rate trades at a forward discount, and $S\,D_d/D_f$ is a direction error. Quoted as a continuous spread on the foreign leg, the basis is $b=-\ln(F_{\mathrm{mkt}}/F_{\mathrm{CIP}})/T$. A market forward above the no-basis forward gives a negative basis, and a widening basis means more negative. State the year fraction, and annualize before reporting in basis points.

For a random foreign cashflow, the domestic discounted expectation contains joint FX/cashflow dependence. Replacing both factors by separate forecasts is an additional deterministic approximation, not a universal no-arbitrage identity.

## Projected and already-fixed coupons

Let $P_f$ be a projection pseudo-discount curve and $\alpha_i$ the contractual year fraction for $[T_{i-1},T_i]$. An unfixed simple forward is:

$$
L_i(t)=\frac{P_f(t,T_{i-1})/P_f(t,T_i)-1}{\alpha_i}
$$

A foreign coupon with signed receiver/payer direction $s_f\in\{-1,1\}$, positive notional $N_i$ and spread $b$ is:

$$
C_{f,i}=s_fN_i\alpha_i(L_i+b)
$$

The coupon for $[T_{i-1},T_i]$ uses the notional in force during that interval. With a start-of-period reset, this is $N_{f,i-1}$, set at $T_{i-1}$; the reset at $T_i$ sets the next interval, unless the contract specifies otherwise. Once the fixing is known, its observed rate replaces the projected forward. A valuation roll can change which coupons are fixed. Projection and discount curves serve different purposes; the spread's currency leg and compounding are contractual.

## Reset exchanges

Suppose a domestic reference notional is $N_d$ and a foreign notional resets using domestic-per-foreign FX $X_i$. The equal-value foreign notional is:

$$
N_{f,i}=\frac{N_d}{X_i}
$$

For the side that originally lends foreign principal, increasing that principal requires an additional payment. A genuine cash-settled reset at its contractual exchange date therefore has cashflow:

$$
C_{\mathrm{reset},i}=N_{f,i-1}-N_{f,i}
$$

Initial lending is $-N_{f,0}$ and final repayment is $+N_{f,m}$. Principal cashflows telescope to zero in foreign units when all exchanges are included; their discounted domestic values need not cancel. The borrower has opposite signs. A bookkeeping notional reset without a principal payment is a different contract. Already-settled principal exchanges are not future cashflows.

Using $X_i=F(t,T_i)$ for unknown future resets is a deterministic-forward approximation. In general, expected reciprocal FX differs from reciprocal expected FX, and random notionals can correlate with coupons.

## All-in spread and risk

If all other cashflows, notionals and curves are held fixed and the spread enters coupons linearly, trade value is affine in that spread. The signed spread annuity is: For the foreign-leg formula below, the spread is paid on that foreign leg; a domestic-leg spread omits the FX-forward conversion.

$$
A_b=\sum_i s_fN_i\alpha_iD_d(t,T_i)F(t,T_i)
$$

For $A_b\ne0$, the total par spread is:

$$
b_{\mathrm{par}}=-\frac{\mathrm{PV}(0)}{A_b}
$$

At a current spread $b_0$, the incremental spread change to par is $-\mathrm{PV}(b_0)/A_b$; it is not the all-in spread unless added to $b_0$. If notionals or curves depend on the trial spread, the affine identity no longer applies.

A zero-rate bump with other curves frozen differs from a market-quote bump with recalibration. Holding quoted forwards fixed while moving OIS curves changes implied basis; holding basis fixed generally changes forwards. State which objects are independent before interpreting rate, basis or FX sensitivity. A central derivative divides by the bump; a signed one-basis-point P&L multiplies a rate derivative by $10^{-4}$, with any DV01 sign convention stated separately.

## References

[Fujii and Takahashi, A General Framework for the Benchmark Pricing in a Fully Collateralized Market](https://arxiv.org/html/1508.06339), collateral-dependent currency valuation. Cashflow signs, telescoping principal identity and affine spread formulas above follow directly from the stated deterministic contract, rather than specifying a universal reset-swap convention.
