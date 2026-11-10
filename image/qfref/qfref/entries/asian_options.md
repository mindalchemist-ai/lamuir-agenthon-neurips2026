# Asian Options under Black–Scholes

Asian options depend on an average of observed prices. Identify the averaging rule, fixing dates, exercise style and payment date before selecting a method. Follow the task's prescribed steps; this reference's section order is not an execution plan.

## Contents

1. [Shared Foundations](#1-shared-foundations)
2. [Contract and Fixing Schedule](#2-contract-and-fixing-schedule)
3. [Geometric Average: Exact Pricing](#3-geometric-average-exact-pricing)
4. [Arithmetic Average: Moments and Levy Approximation](#4-arithmetic-average-moments-and-levy-approximation)
5. [Curran Geometric-Conditioning Approximation](#5-curran-geometric-conditioning-approximation)
6. [Seasoned and Floating-Strike Contracts](#6-seasoned-and-floating-strike-contracts)
7. [Monte Carlo and Control Variates](#7-monte-carlo-and-control-variates)
8. [Checks and Scope](#8-checks-and-scope)
9. [References](#9-references)

## 1. Shared Foundations

Map quantities by meaning and units, not by letter; revisit the mapping when inputs or contract conventions change.

| Symbol | Definition |
|---|---|
| $S$ | Current underlying price, strictly positive |
| $r, q$ | Constant annual continuous risk-free rate and dividend yield |
| $\sigma$ | Annual volatility in decimal units |
| $t_{i}$ | Time in years from valuation to fixing i |
| $w_{i}$ | Nonnegative fixing weight, with $\sum  w_{i} = 1$ |
| $T$ | Final fixing time (end of the averaging window), in years |
| $T_{p}$ | Time in years to payment, $T_{p} \ge  T$ |
| $K$ | Fixed strike, positive unless handled separately |
| $A, G$ | Arithmetic and geometric averages |
| $\Phi , \phi$ | Standard normal CDF and density |

Notation: $\sum_i$ sums over fixing indices; $\cdot$ denotes multiplication. $\operatorname{Normal}(  \mu , v )$ uses variance v, not standard deviation. Displayed formulas are mathematical notation, not executable Python.

All expectations below are risk-neutral. Under constant-parameter GBM,
**Risk-neutral stock dynamics**

$$
\mathrm{d}S_{t} / S_{t} = (r - q) \cdot  \mathrm{d}t + \sigma  \cdot  \mathrm{d}W_{t}
$$

**Log-price solution**

$$
\ln (S_{t}) = \ln (S) + (r - q - \sigma ^{2} / 2) \cdot  t + \sigma  \cdot  W_{t}
$$

Write $\nu  = r - q - \sigma ^{2} / 2$. A supplied log drift already includes the Itô correction. For FX, q is the foreign rate; historical mean returns do not replace the risk-neutral drift.

For future fixings, let $X_{i} = \ln (S(t_{i}))$; these log prices are jointly normal.

**Mean of the log price at fixing date $t_{i}$**

$\mu _{i}$ is the risk-neutral expectation of $X_{i}$.

$$
\mu _{i} = \ln (S) + \nu  \cdot  t_{i}
$$

**Covariance between log fixings**

$$
\Sigma _{ij} = \sigma ^{2} \cdot  \min (t_{i}, t_{j})
$$

Set $\mathrm{disc} = \exp (-r \cdot  T_{p})$. Discount a terminal payoff once: $V = \mathrm{disc} \cdot  \operatorname{E}[\;\text{payoff}\;]$. For zero volatility or fully known fixings, evaluate the deterministic payoff instead of dividing by a zero variance.

## 2. Contract and Fixing Schedule

**Discrete arithmetic average**

$$
A = \sum _{i}(w_{i} \cdot  S(t_{i}))
$$

**Discrete geometric average**

$$
G = \exp (\sum _{i}(w_{i} \cdot  \ln (S(t_{i}))))
$$

| Contract | Call payoff | Put payoff |
|---|---|---|
| Fixed-strike arithmetic | $\max ( A-K, 0 )$ | $\max ( K-A, 0 )$ |
| Fixed-strike geometric | $\max ( G-K, 0 )$ | $\max ( K-G, 0 )$ |
| Floating-strike arithmetic | $\max (  S_{T} -A, 0 )$ | $\max ( A- S_{T} , 0 )$ |

Here $\max ( x, 0 )$ denotes the positive part. Floating-strike terminology can differ: the specified payoff controls.

Build the actual fixing vector, not a generic time grid. Equal spacing with n future fixings and no initial fixing means $t_{i} = i \cdot  T / n$, $i=1,\ldots ,n$, and $w_{i}=1/n$. Including today's price changes both weights and moments. Payment may occur after averaging ends. Historical observations already fixed are constants, not resimulated prices.

Continuous averaging is a different contract. For a fresh uniform window [0,T],
**Continuous arithmetic average**

$$
A = (1 / T) \cdot  \int_{0}^{T}(S_{t}) \mathrm{d}t
$$

**Continuous geometric average**

$$
\ln (G) = (1 / T) \cdot  \int_{0}^{T}(\ln (S_{t})) \mathrm{d}t
$$

Discrete formulas approximate these integrals only as an explicitly chosen numerical approximation.

## 3. Geometric Average: Exact Pricing

Use [Shared Foundations](#1-shared-foundations) and the fixing schedule in Section 2.

Because a linear combination of jointly normal variables is normal,
**Normal distribution of the log geometric average**

$$
\begin{gathered}
Y = \ln (G) \sim \operatorname{Normal}(\mu _{G}, v_{G}) \\
\mu _{G} = \sum _{i}(w_{i} \cdot  \mu _{i}) \\
v_{G} = \sum _{i} \sum _{j}(w_{i} \cdot  w_{j} \cdot  \Sigma _{ij})
\end{gathered}
$$

Define $F_{G} = \exp (\mu _{G} + v_{G} / 2)$,
**Standardized geometric-option thresholds**

$$
\begin{gathered}
d_{2} = (\mu _{G} - \ln (K)) / \sqrt{v_{G}} \\
d_{1} = d_{2} + \sqrt{v_{G}}
\end{gathered}
$$

Integrating the normal density over $Y > \ln  K$ gives
**Exact geometric-average call price**

$$
C_{G} = \mathrm{disc} \cdot  (F_{G} \cdot  \Phi (d_{1}) - K \cdot  \Phi (d_{2}))
$$

**Exact geometric-average put price**

$$
\operatorname{P}_{G} = \mathrm{disc} \cdot  (K \cdot  \Phi (-d_{2}) - F_{G} \cdot  \Phi (-d_{1}))
$$

These are exact for the specified geometric average under GBM. The total log variance is $v_{G}$, not an annual volatility to multiply by T again.

For n equally weighted future fixings at iT/n,
**Log-geometric moments for equally spaced fixings**

$$
\begin{gathered}
\mu _{G} = \ln (S) + \nu  \cdot  T \cdot  (n + 1) / (2 \cdot  n) \\
v_{G} = \sigma ^{2} \cdot  T \cdot  (n + 1) \cdot  (2 \cdot  n + 1) / (6 \cdot  n^{2})
\end{gathered}
$$

For continuous averaging over [0,T], the covariance integral gives
**Log-geometric moments for continuous averaging**

$$
\begin{gathered}
\mu _{G} = \ln (S) + \nu  \cdot  T / 2 \\
v_{G} = \sigma ^{2} \cdot  T / 3
\end{gathered}
$$

Use the general sums for irregular dates or unequal weights.

## 4. Arithmetic Average: Moments and Levy Approximation

Section 3 supplies the lognormal payoff integral.

A sum of correlated lognormal variables is generally not lognormal. Its first two moments are nevertheless exact:
**First moment of the arithmetic average**

$$
M_{1} = \operatorname{E}[A] = \sum _{i}(w_{i} \cdot  S \cdot  \exp ((r - q) \cdot  t_{i}))
$$

**Second moment of the arithmetic average**

$$
\begin{gathered}
M_{2} = \operatorname{E}[A^{2}] = \sum _{i} \sum _{j}(w_{i} \cdot  w_{j} \cdot  S^{2} \\
\cdot  \exp ((r - q) \cdot  (t_{i} + t_{j}) + \sigma ^{2} \cdot  \min (t_{i}, t_{j})))
\end{gathered}
$$

The second formula follows by taking the expectation of $\exp (X_{i}+X_{j})$. It includes the covariance between observations.

The two-moment lognormal approximation replaces A with $\exp (Z)$, choosing
**Moment-matched lognormal parameters**

$$
\begin{gathered}
v_{A} = \ln (M_{2} / M_{1}^{2}) \\
\mu _{A} = \ln (M_{1}) - v_{A} / 2
\end{gathered}
$$

**Standardized moment-matching thresholds**

$$
\begin{gathered}
h_{2} = (\mu _{A} - \ln (K)) / \sqrt{v_{A}} \\
h_{1} = h_{2} + \sqrt{v_{A}}
\end{gathered}
$$

**Moment-matched arithmetic call price**

$$
C_{\mathrm{MM}} = \mathrm{disc} \cdot  (M_{1} \cdot  \Phi (h_{1}) - K \cdot  \Phi (h_{2}))
$$

**Moment-matched arithmetic put price**

$$
\operatorname{P}_{\mathrm{MM}} = \mathrm{disc} \cdot  (K \cdot  \Phi (-h_{2}) - M_{1} \cdot  \Phi (-h_{1}))
$$

This is the Levy-style moment-matching construction for the chosen schedule. Distinguish this discrete implementation from a specified continuous-average Levy formula. Matching moments does not make the option price exact.

For continuous uniform averaging, replace the sums by
**Continuous-average first moment**

$$
M_{1} = (S / T) \cdot  \int_{0}^{T}(\exp ((r - q) \cdot  t)) \mathrm{d}t
$$

**Continuous-average second moment**

$$
M_2=\frac{S^2}{T^2}\int_0^T\int_0^T\exp\big((r-q)(s+t)+\sigma^2\min(s,t)\big)\,\mathrm{d}t\,\mathrm{d}s
$$

Evaluate limiting cases or stable quadrature rather than divide by a nearly zero carry rate. Compute $v_{A}$ as $\operatorname{log1p}(\operatorname{Var}(A)/M_1^2)$ when useful; materially negative variance indicates an error.

## 5. Curran Geometric-Conditioning Approximation

Use [Shared Foundations](#1-shared-foundations) and Section 3's Y, $\mu _{G}$ and $v_{G}$.

Conditioning is different from substituting geometric variance into an arithmetic pricing formula. For $v_{G} > 0$, define
**Gaussian conditioning coefficients and residual covariance**

$$
\begin{gathered}
c_{i} = \operatorname{Cov}(X_{i}, Y) = \sum _{j}(\Sigma _{ij} \cdot  w_{j}) \\
b_{i} = c_{i} / v_{G} \\
R_{ij} = \Sigma _{ij} - c_{i} \cdot  c_{j} / v_{G}
\end{gathered}
$$

Conditional normality gives
**Conditional mean of a log fixing**

$$
a_{i}(y) = \mu _{i} + b_{i} \cdot  (y - \mu _{G})
$$

**Conditional mean of the arithmetic average**

$$
m(y) = \operatorname{E}[A \vert  Y=y] = \sum _{i}(w_{i} \cdot  \exp (a_{i}(y) + R_{ii} / 2))
$$

**Conditional second moment of the arithmetic average**

$$
\begin{gathered}
m_{2}(y) = \operatorname{E}[A^{2} \vert  Y=y] \\
= \sum _{i} \sum _{j}(w_{i} \cdot  w_{j} \\
\cdot  \exp (a_{i}(y) + a_{j}(y) + (R_{ii} + R_{jj} + 2 \cdot  R_{ij}) / 2))
\end{gathered}
$$

The exact identity is $C_{A} = \mathrm{disc} \cdot  \operatorname{E}[\operatorname{E}[\max (A - K, 0) \vert  Y]]$. Taking a positive part after a conditional mean loses conditional uncertainty:
**Conditional-expectation lower bound for the arithmetic call**

$$
C_{\mathrm{LB}} = \mathrm{disc} \cdot  \operatorname{E}[\max (m(Y) - K, 0)] \le  C_{A}
$$

**Selected method: Curran (1994), Section 2.3, naive approximation.** This is the version used for the Asian results in the paper's Section 3. It is a lower-bound approximation, not an exact arithmetic price. The implementation below evaluates its exercise threshold numerically; it does not substitute an approximate strike threshold.

First apply Section 6 to remove past fixings and any known initial fixing. For positive remaining weights at strictly positive times and $\sigma  > 0, m(y)$ is strictly increasing from zero to infinity, so there is exactly one root $m(y_{\mathrm{star}})=K$ for $K > 0$. Weighted AM–GM implies $m(\ln  K) \ge  K$, giving an upper bracket. Expand the lower bracket until $m(y_{\mathrm{low}}) < K$, then solve with a bracketed root finder. Use log-sum-exp for $\log  m(y)$ to avoid overflow. Do not interpret an arbitrary finite lower bracket as minus infinity. With $F_{i} = \exp (\mu _{i} + \Sigma _{ii} / 2)$,
**Curran naive call value at the solved threshold**

$$
\begin{gathered}
C_{\mathrm{LB}} = \mathrm{disc} \cdot  (\sum _{i}(w_{i} \cdot  F_{i} \cdot  \Phi ((\mu _{G} + c_{i} - y_{\mathrm{star}}) / \sqrt{v_{G}})) \\
- K \cdot  \Phi ((\mu _{G} - y_{\mathrm{star}}) / \sqrt{v_{G}}))
\end{gathered}
$$

**Truncated asset moment used in the conditional lower bound**

$$
\operatorname{E}[\exp (X_{i}) \cdot  \operatorname{indicator}(Y > h)] = F_{i} \cdot  \Phi ((\mu _{G} + c_{i} - h) / \sqrt{v_{G}})
$$

explains the price formula: integrate the conditional payoff only where $m(y)>K$. No extra time factor belongs in $\sqrt{v_{G}}$.

**Conditional-pricing calculation:** construct dates and weights; compute $\mu _{i}$, $\Sigma$, $\mu _{G}$, $v_{G}$ and $c_{i}$; solve $\log  m(y_{\mathrm{star}})=\log  K$; evaluate the truncated expectations; discount once. Record the root residual. Obtain the corresponding approximate put from parity with the exact arithmetic mean M1. The parity identity is exact, but the resulting put retains the call's approximation error.

**Boundary handling:** if all prices are known or $\sigma =0$, evaluate the deterministic average directly. If the effective strike after seasoned-contract reduction is nonpositive, the call payoff is linear and the put is zero. This exact statement concerns the contractual effective strike. An approximate geometric threshold such as $\hat{K}=2K-m(\ln  K)$ is a different object: $\hat{K}\le 0$ does not prove that the actual payoff is always positive. Fall back to the root calculation, not an asserted exact linear price.

The original paper also presents a refined residual-moment variant. This reference implements only the selected naive variant; it does not supply the refined algorithm.

Use the selected naive variant unless a different conditioning variant is specified. State which variant was implemented; do not substitute Levy or geometric pricing under the Curran name.

## 6. Seasoned and Floating-Strike Contracts

Use [Shared Foundations](#1-shared-foundations); retain Section 2's original weights.

For arithmetic averaging with past fixings, write
**Known-past and future-average decomposition**

$$
\begin{gathered}
A = a_{\mathrm{past}} + W_{f} \cdot  A_{f} \\
a_{\mathrm{past}} = \sum _{\mathrm{past}}(w_{i} \cdot  S_{i}) \\
W_{f} = \sum _{\mathrm{future}}(w_{i}) \\
A_{f} = \sum _{\mathrm{future}}((w_{i} / W_{f}) \cdot  S_{i})
\end{gathered}
$$

For $W_{f} > 0$, set $K_{f}=(K-a_{\mathrm{past}})/W_{f}$. A fixed-strike call is $W_{f}$ times a call on $A_{f}$ with strike $K_{f}$, discounted to the original payment date. If $K_{f} \le  0$, its payoff is linear: $\mathrm{price}=\mathrm{disc}(a_{\mathrm{past}}+W_f\operatorname{E}[A_f]-K)$, and the put is zero. If $W_{f}=0$, all payoffs are known.

For geometric averaging, add past contributions to $\mu _{G}$ as $\sum _{\mathrm{past}} w_{i} \ln  S_{i}$; only future fixings contribute covariance. This preserves the original averaging weights.

For a floating-strike arithmetic payoff, simulate the joint pair ($S_{T}$,A); replacing the random strike by E[A] changes the contract. The geometric floating-strike call has an exact joint-lognormal benchmark. Let $X=\ln  S_{T}, Y=\ln  G$, means $\mu _{X}$,$\mu _{Y}$, variances $v_{X}$,$v_{Y}$, covariance $c_{\mathrm{XY}}$, and $v_{\mathrm{diff}}=v_{X}+v_{Y}-2\cdot c_{\mathrm{XY}}$. For $v_{\mathrm{diff}}>0$,
**Expected positive difference of two jointly lognormal variables**

$$
\begin{gathered}
\operatorname{E}[\max (\exp (X) - \exp (Y), 0)] \\
= \exp (\mu _{X} + v_{X} / 2) \cdot  \Phi ((\mu _{X} - \mu _{Y} + v_{X} - c_{\mathrm{XY}}) / \sqrt{v_{\mathrm{diff}}}) \\
- \exp (\mu _{Y} + v_{Y} / 2) \cdot  \Phi ((\mu _{X} - \mu _{Y} + c_{\mathrm{XY}} - v_{Y}) / \sqrt{v_{\mathrm{diff}}})
\end{gathered}
$$

Multiply by disc; obtain the put from the corresponding expectation difference. Compute $c_{\mathrm{XY}}$ from the actual fixing schedule, including any past constants. Handle $v_{\mathrm{diff}}=0$ as a deterministic log ratio.

## 7. Monte Carlo and Control Variates

Use [Shared Foundations](#1-shared-foundations) and the contractual dates in Section 2.

At successive future fixings, use exact GBM transitions:
**Exact GBM stepping between fixing dates**

$$
\ln (S(t_{i})) = \ln (S(t_{i-1})) + \nu  \cdot  \mathrm{d}t_{i} + \sigma  \cdot  \sqrt{\mathrm{d}t_{i}} \cdot  Z_{i}
$$

$$
\mathrm{d}t_{i} = t_{i} - t_{i-1}
$$

The $Z_{i}$ are independent standard normal draws.
Compute the contractual average on each path, then the payoff, then discount. Averaging option payoffs over dates is a different operation. Process paths in batches when storing the entire path matrix is unnecessary.

For discounted arithmetic payoff $U_{A}$ and matching discounted geometric payoff $U_{G}$ with exact mean $V_{G}$, use
**Geometric control-variate estimator and coefficient**

$$
\begin{gathered}
U_{\mathrm{CV}} = U_{A} - \beta  \cdot  (U_{G} - V_{G}) \\
\beta  = \operatorname{Cov}(U_{A}, U_{G}) / \operatorname{Var}(U_{G})
\end{gathered}
$$

Estimate $\beta$ on a separate pilot sample, then hold it fixed on independent pricing paths. If $\operatorname{Var}(U_{G})=0$, omit that control. Dates, weights, historical fixings, strike and payment date of the control must match its analytic benchmark.

Report $\operatorname{mean}(U_{\mathrm{CV}})$ and $\mathrm{sample\_std}(U_{\mathrm{CV}})/\sqrt{M}$ for M independent observations. For antithetic paths, average each pair first and compute standard error across independent pairs. A price approximation can differ from MC by more than sampling error because it has approximation bias; an exact geometric benchmark should agree within sampling uncertainty and implementation accuracy.

## 8. Checks and Scope

Use [Shared Foundations](#1-shared-foundations); compare identical contracts and payment dates.

For a nonnegative average A and positive K,
**Bounds for the arithmetic-average call**

$$
\mathrm{disc} \cdot  \max (\operatorname{E}[A] - K, 0) \le  C_{A} \le  \mathrm{disc} \cdot  \operatorname{E}[A]
$$

**Arithmetic-average put-call parity**

$$
C_{A} - \operatorname{P}_{A} = \mathrm{disc} \cdot  (\operatorname{E}[A] - K)
$$

For identical nonnegative weights, $A\ge G$ pathwise, so $C_{A}\ge C_{G}$ and $\operatorname{P}_{A}\le \operatorname{P}_{G}$. A one-fixing contract reduces to an ordinary option on that fixing; discount to the specified payment date. These are checks of the true prices: approximations and finite MC estimates need suitable error allowances.

Check dates and moments before comparing prices. Test the zero-volatility limit, single fixing, irregular dates and known past fixings. Use exact geometric pricing to validate the path simulation; use a separate MC implementation to assess arithmetic approximations. Parity or bounds alone do not establish method identity or price accuracy.

The displayed analytic formulas assume European payoffs, constant-parameter GBM and deterministic nonnegative weights. Continuous arithmetic averages need integration or a converged discretization; early exercise, stochastic volatility, jumps and negative weights require appropriate extensions. Do not silently reuse these approximations outside their assumptions.

## 9. References

- Curran (1994), [Valuing Asian and Portfolio Options by Conditioning on the Geometric Mean Price](https://doi.org/10.1287/mnsc.40.12.1705): Sections 2.2–2.3, pp. 1706–1709; Section 3 uses the naive variant for Asians.
- Levy (1992), *Pricing European average rate currency options*, Journal of International Money and Finance 11(5), 474–491: lognormal moment-matching approximation.
- [QuantLib discrete geometric Asian implementation](https://github.com/lballabio/QuantLib/blob/master/ql/pricingengines/asian/analytic_discr_geom_av_price.cpp): a separately implemented geometric benchmark.
- Kyriakou (2010), [Efficient valuation of exotic derivatives with path-dependence and early exercise features](https://openaccess.city.ac.uk/id/eprint/23459/), Section 4.6.2: distinction between strike-frozen and pointwise conditional-moment approximations. The pointwise variant is not implemented in this reference.
