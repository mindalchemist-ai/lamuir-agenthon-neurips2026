# Forward-start and cliquet pricing under deterministic-coefficient GBM

Map task quantities to these definitions by meaning and units, not by letter, before the first calculation; recheck when inputs or conventions change.

Use this document for future-reset strikes and cliquet coupons: Black–Scholes building blocks, local cap/floor decomposition, and additive versus globally constrained contracts. Choose payoff units and payment dates first. It is not a stochastic-volatility or cash-dividend cliquet pricing formula.

Explicit task definitions, contract conventions and required input handling take precedence. Map them to the assumptions here; if they differ, these formulas may not apply unchanged. Identify unresolved ambiguity rather than silently mixing conventions.

## Contents

1. [Definitions and method selection](#1-definitions-and-method-selection)
2. [Normalized option block](#2-normalized-option-block)
3. [Future reset: price and return coupons](#3-future-reset-price-and-return-coupons)
4. [Local and global constraints](#4-local-and-global-constraints)
5. [A reset already observed](#5-a-reset-already-observed)
6. [Calculation and checks](#6-calculation-and-checks)
7. [Scope and references](#7-scope-and-references)

## 1. Definitions and method selection

Time zero is the valuation date. Spot S0 is positive. Constant r and q are continuously compounded domestic rate and dividend/carry yield; $\sigma  \ge  0$ is annualized volatility. Rates and volatility are decimals, times are years. Ncdf denotes the standard normal CDF. Q is a fixed cash notional, not a probability measure. Let $0 \le  s \le  e \le  p$ be reset, final fixing, and payment times. The strike multiplier $\alpha$ is dimensionless. Let $\tau  = e-s$.

| Observable contract feature | Calculation |
|---|---|
| Pays $\max (  S_{e} - \alpha \cdot S_{s} , 0 )$, with s in the future | Price-unit block in §3 |
| Pays $Q\max(S_e/S_s-\alpha,0)$ | Return-unit block in §3 |
| Sum of individually capped/floored returns | Decompose each coupon using §4, then add present values |
| Cap/floor applied to the whole sum | Path-level calculation in §4; do not cap a sum of expected values |
| $S_{s}$ has already been observed | Fixed-strike block in §5 |

An ATM reset uses $\alpha =1$. A strike k on a simple return uses $\alpha =1+k$. A ratchet whose strike only moves upward, depends on an average, or remembers a running maximum requires additional state; it is not the plain reset contract above. Follow explicit contract definitions rather than the product label alone.

## 2. Normalized option block

Use this block for one period of length $\tau$. c and u are respectively call and put values at the period start on unit spot, with payoff fixed and paid at the period end. For $\alpha >0$ and $\sigma \cdot \sqrt{\tau}>0$:

**Total volatility and normalized pricing thresholds**

$$
\begin{gathered}
x = \sigma \cdot \sqrt{\tau} \\
\mathrm{d1} = (-\log (\alpha ) + (r-q)\cdot \tau  + x\cdot x/2)/x \\
\mathrm{d2} = \mathrm{d1}-x
\end{gathered}
$$

**Normalized call price**

$$
c(\alpha ,\tau ) = \exp (-q\cdot \tau )\cdot \mathrm{Ncdf}(\mathrm{d1}) - \alpha \cdot \exp (-r\cdot \tau )\cdot \mathrm{Ncdf}(\mathrm{d2})
$$

**Normalized put price**

$$
u(\alpha ,\tau ) = \alpha \cdot \exp (-r\cdot \tau )\cdot \mathrm{Ncdf}(-\mathrm{d2}) - \exp (-q\cdot \tau )\cdot \mathrm{Ncdf}(-\mathrm{d1})
$$

At zero variance, evaluate the deterministic payoff instead of dividing by x. This also handles $\tau =0$. Nonpositive $\alpha$ is handled by linearity, not $\log (\alpha )$.

**Deterministic growth factor**

$$
f = \exp ((r-q)\cdot \tau )
$$

**Zero-variance call price**

$$
\mathrm{zero}_{\mathrm{variance},\mathrm{call}} = \exp (-r\cdot \tau )\cdot \max (f-\alpha ,0)
$$

**Zero-variance put price**

$$
\mathrm{zero}_{\mathrm{variance},\mathrm{put}}  = \exp (-r\cdot \tau )\cdot \max (\alpha -f,0)
$$

**Nonpositive-strike branch**

If $\alpha  \le  0$:

$$
c = \exp (-q\cdot \tau )-\alpha \cdot \exp (-r\cdot \tau )
$$

$$
u = 0
$$

A negative volatility or negative period length is invalid input, not a zero-variance case.

## 3. Future reset: price and return coupons

Use the price-unit block when the payoff contains $S_e-\alpha S_s$. Homogeneity makes its value at s equal to $S_sc$. Under GBM the discounted expected $S_{s}$ contributes the pre-reset dividend factor.

**Price-unit forward-start call value**

$$
\mathrm{price}_{\mathrm{call},0} = \exp (-r\cdot (p-e))\cdot \mathrm{S0}\cdot \exp (-q\cdot s)\cdot c(\alpha ,\tau )
$$

**Price-unit forward-start put value**

$$
\mathrm{price}_{\mathrm{put},0}  = \exp (-r\cdot (p-e))\cdot \mathrm{S0}\cdot \exp (-q\cdot s)\cdot u(\alpha ,\tau )
$$

**Price-unit put-call parity**

$$
\begin{gathered}
\mathrm{price}_{\mathrm{call},0}-\mathrm{price}_{\mathrm{put},0} = \exp (-r\cdot (p-e))\cdot \mathrm{S0}\cdot \exp (-q\cdot s) \\
\cdot  (\exp (-q\cdot \tau )-\alpha \cdot \exp (-r\cdot \tau ))
\end{gathered}
$$

Use the return-unit block when the payoff contains $S_e/S_s-\alpha$. Independent GBM increments remove $S_{s}$ from that ratio. Q is fixed, not equal to the random reset spot.

**Return-unit forward-start call value**

$$
\mathrm{return}_{\mathrm{call},0} = Q\cdot \exp (-r\cdot (p-e))\cdot \exp (-r\cdot s)\cdot c(\alpha ,\tau )
$$

**Return-unit forward-start put value**

$$
\mathrm{return}_{\mathrm{put},0}  = Q\cdot \exp (-r\cdot (p-e))\cdot \exp (-r\cdot s)\cdot u(\alpha ,\tau )
$$

The normalized block already discounts the period. Do not use $\exp (-r\cdot s)$ for a price-unit coupon; do not multiply a return-unit coupon by S0 unless its notional is explicitly S0. Delayed payment contributes only $\exp (-r\cdot (p-e))$, since the cash amount is fixed at e and assumed not to accrue before payment.

For a plain additive cliquet with reset dates $t_{0}=0 < \ldots  < t_{n}$, apply the correct block to each ($s=t_{i-1}, e=t_{i}, p=p_{i}$) and sum its time-zero values. The first price-unit period is an ordinary option with strike $\alpha S_0$. Equal interval lengths do not imply equal price-unit present values when q is nonzero. Payment at each fixing and common payment at final maturity are distinct contracts.

## 4. Local and global constraints

For a local return $R=S_{e}/S_{s}-1$ with floor L and cap $U, L\le U$, use the following pathwise identities. The normalized block also supports L or $U \le  -1$ via its nonpositive-strike branch.

**Local cap-and-floor payoff decomposition**

$$
\mathrm{clipped}_{\mathrm{return}} = L + \max (R-L,0) - \max (R-U,0)
$$

**Floor-only payoff decomposition**

$$
\operatorname{floor}_{\mathrm{only}} = L + \max (R-L,0)
$$

**Cap-only payoff decomposition**

$$
\mathrm{cap}_{\mathrm{only}} = R - \max (R-U,0)
$$

**Present value of the locally clipped return**

$$
\begin{gathered}
\mathrm{PV}_{\mathrm{clipped}} = Q\cdot \exp (-r\cdot p)\cdot L \\
+ Q\cdot \exp (-r\cdot (p-e))\cdot \exp (-r\cdot s)\cdot (c(1+L,\tau )-c(1+U,\tau ))
\end{gathered}
$$

**Present value of the uncapped return**

$$
\mathrm{PV}_{\mathrm{plain},\mathrm{return}} = Q\cdot \exp (-r\cdot p)\cdot (\exp ((r-q)\cdot \tau )-1)
$$

**Present value of a cap-only return**

$$
\mathrm{PV}_{\mathrm{cap},\mathrm{only}} = \mathrm{PV}_{\mathrm{plain},\mathrm{return}}-Q\cdot \exp (-r\cdot (p-e))\cdot \exp (-r\cdot s)\cdot c(1+U,\tau )
$$

If a global constraint acts on the aggregate, simulate the joint fixing schedule, compute each realized coupon, aggregate on each path, apply the global function, then discount to its payment date. Independent period increments do not justify moving a nonlinear cap/floor outside expectation. For a reverse cliquet, translate its coupon-minus-losses rule and any aggregate floor literally; do not assume that every reverse contract has the same payoff.

**Simulate one log-return increment**

$$
\log (S_{ti}/S_{\mathrm{tprev}}) = (r-q-\sigma \cdot \sigma /2)\cdot \mathrm{d}t_{i} + \sigma \cdot \sqrt{\mathrm{d}t_{i}}\cdot Z_{i}
$$

**Convert to a simple return**

$$
R_{i} = \exp (\log (S_{ti}/S_{\mathrm{tprev}}))-1
$$

**Apply local coupon limits**

$$
\mathrm{local}_{i} = \min (U_{i},\max (L_{i},R_{i}))
$$

**Apply the global payoff and discount**

$$
Y = Q\cdot \exp (-r\cdot p)\cdot \min (U_{\mathrm{global}},\max (L_{\mathrm{global}},\sum _{i} \mathrm{local}_{i}))
$$

**Monte Carlo price estimate**

$$
\mathrm{price} = \operatorname{mean}(Y)
$$

**Standard error across independent paths**

$$
\mathrm{SE} = \;\text{sample}\;_{\mathrm{sd}}(Y)/\sqrt{\mathrm{number}_{\mathrm{of},\mathrm{independent},\mathrm{paths}}}
$$

Use independent standard normals across intervals. For antithetic sampling, average each pair first and estimate SE across independent pairs. The displayed global example is a capped/floored sum paid once; different global rules require their own payoff function.

## 5. A reset already observed

If the reset price H is known today and the end fixing is still in the future, the strike is fixed. With remaining end time e and payment time p, use today's S0 and $K=\alpha \cdot H$, not a fresh future-reset formula. $\mathrm{BS}_{\mathrm{call}}$(S,K,T) and $\mathrm{BS}_{\mathrm{put}}$(S,K,T) denote ordinary European Black–Scholes values payable at expiry, using the same r, q and $\sigma$. They are mathematical price functions, not a required software API. For $H>0$:

**Price-unit call after its reset is known**

$$
\mathrm{price}_{\mathrm{coupon},0} = \exp (-r\cdot (p-e))\cdot \mathrm{BS}_{\mathrm{call}}(\mathrm{S0},\alpha \cdot H,e)
$$

**Return-unit call after its reset is known**

$$
\mathrm{return}_{\mathrm{coupon},0} = (Q/H)\cdot \exp (-r\cdot (p-e))\cdot \mathrm{BS}_{\mathrm{call}}(\mathrm{S0},\alpha \cdot H,e)
$$

Use $\mathrm{BS}_{\mathrm{put}}$ for puts. A coupon whose end fixing has already occurred is known cash: discount that amount to its unpaid payment date. Paid coupons are excluded. If a global constraint remains, keep the known accumulated coupons as state inside the final payoff instead of valuing them independently.

## 6. Calculation and checks

Historical volatility estimation and risk-neutral pricing use different quantities: a historical return mean does not replace the pricing drift r-q.

For additive period payoffs, present values sum over periods with their own reset, fixing and payment dates. A fixed-strike European option and a reset-strike contract are different payoffs; changing reset frequency has no universal monotonic effect on value.

Check reset-at-zero against ordinary BS, put-call parity, scaling in S0 for price coupons and in Q for return coupons, and independence from S0 for future return coupons with fixed Q. Check zero volatility and zero period length. Local capped returns lie between L and U pathwise, so their PV lies between $Q\cdot \exp (-r\cdot p)\cdot L$ and $Q\cdot \exp (-r\cdot p)\cdot U$ for positive Q. Validate a synthetic period against direct lognormal integration or simulation, including nonzero q and $p>e$.

## 7. Scope and references

For deterministic time-varying parameters replace $r\tau$, $q\tau$ and $\sigma^2\tau$ by the corresponding period integrals, the pre-reset yield factor by $\exp (-\int _{0}^{s} q)$, and all bond factors by their interval rate integrals. These replacements rely on independent Gaussian increments and deterministic discounting.

Discrete cash dividends break multiplicative GBM. If no cash dividend lies inside the reset period, homogeneity conditional on $S_{s}$ can still be useful, but the pre-reset factor becomes $\exp (-r\cdot s)\cdot \operatorname{E}[S_{s}]$, evaluated under the actual dividend model. It is not generally S0 minus dividend PV when q is nonzero or cash jumps are capped at zero. Cash dividends inside the period require another pricing method. Stochastic volatility, smile dynamics, jumps, and stochastic rates are outside these exact blocks.

Before a future reset the price-unit formula is linear in S0, giving zero spot $\gamma$ under these assumptions. Once the strike is known, ordinary fixed-strike Greeks apply. Do not infer that every Greek must jump at every reset.

The single-period blocks follow directly from Black–Scholes homogeneity and independent lognormal increments; the derivation is stated above. Rubinstein (1991), “Pay Now, Choose Later,” is historical attribution, not a newly verified original source here. For local/global cliquet definitions and model sensitivity, see Windcliff, Forsyth and Vetzal (2006), §4.1–4.2, [Numerical Methods and Volatility Models for Valuing Cliquet Options](https://cs.uwaterloo.ca/~paforsyt/cliquet.pdf). The formulas above do not implement that paper's full PIDE method.
