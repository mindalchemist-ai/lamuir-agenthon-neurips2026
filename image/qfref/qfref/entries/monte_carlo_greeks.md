# Monte Carlo Greeks under Black–Scholes

## Check first: sign conventions, tolerances and Asian-versus-European order

**Two Theta conventions.** Calendar Theta is dV/dt with t the current date; for most long options it is negative (value decays). Many texts instead report the decay as a positive number, -dV/dt = dV/dT with T the time to maturity, or as the value lost over one day of remaining life. Before comparing two Theta estimates (finite difference against pathwise, Monte Carlo against Black-Scholes), put both on one convention: same sign, same time unit (per year or per day, and which day-count basis), same bump direction. A comparison that fails by about twice the size of both numbers is usually a sign mismatch, and a failure by a factor near 252 or 365 is a unit mismatch; fix the convention, not the tolerance.

**Relative versus absolute tolerance.** A check written as "within X% of" a reference is relative: |a - b| <= X/100 * |b|. A check written as "within ±c" or "differs by less than c" is absolute: |a - b| <= c. A check against a Monte Carlo estimate can also be stated in standard errors: |a - b| <= m * se. Use the form the text states for each check, and keep the reference value in the denominator of a relative check.

**Arithmetic-average Asian versus European.** With the same strike, maturity and volatility, and an average taken across the whole contract period, the arithmetic average of a lognormal path has less dispersion than the terminal price, so both the Asian call and the Asian put are usually cheaper than the matching European call and put, and the Asian delta is usually smaller in absolute value. A flag that tests "Asian price below European price" is therefore expected true for calls as well as puts; if it comes out false, first check that the comparison is written as asian < european and uses the same strike and maturity.

```python
import numpy as np

def decay_rate(V, tau, step):                 # value lost per unit of remaining life, positive when value falls
    shorter = V(tau - step)
    return (V(tau) - shorter) / step            # equals dV/dtau; calendar Theta dV/dt is the negative of this

def within_pct(a, b, pct):                    # "within pct% of b"
    return abs(a - b) <= pct / 100.0 * abs(b)

rng = np.random.default_rng(0)
S0, K, r, sig, T, m, n = 100.0, 100.0, 0.05, 0.2, 1.0, 252, 100_000
z = rng.standard_normal((n, m))
paths = S0 * np.exp(np.cumsum((r - 0.5 * sig**2) * (T / m) + sig * np.sqrt(T / m) * z, axis=1))
avg, ST, disc = paths.mean(axis=1), paths[:, -1], np.exp(-r * T)
asian_call, euro_call = disc * np.maximum(avg - K, 0).mean(), disc * np.maximum(ST - K, 0).mean()
asian_put, euro_put = disc * np.maximum(K - avg, 0).mean(), disc * np.maximum(K - ST, 0).mean()
assert asian_call < euro_call and asian_put < euro_put
assert within_pct(1.01, 1.0, 2) and not within_pct(1.05, 1.0, 2)
```

This reference covers sensitivities estimated by finite differences (FD), pathwise differentiation (PW/IPA), and likelihood ratios (LR). Map symbols by definition. Follow the requested contract, method and output convention; section order is not a task workflow. Mathematical notation below is not executable code.

## Contents

1. [Shared Foundations](#1-shared-foundations)
2. [Samples, Variance and Standard Error](#2-samples-variance-and-standard-error)
3. [Finite Differences](#3-finite-differences)
4. [Pathwise Estimators](#4-pathwise-estimators)
5. [Likelihood Ratio Estimators](#5-likelihood-ratio-estimators)
6. [Analytic Benchmarks and Checks](#6-analytic-benchmarks-and-checks)
7. [Numerical considerations and scope](#7-numerical-considerations-and-scope)
8. [References](#8-references)

## 1. Shared Foundations

Read these definitions once; revisit them when the contract or parameter convention changes. Symbols in other references may mean different things.

| Symbol | Definition |
|---|---|
| $S$ | Positive spot at valuation |
| $K$ | Positive fixed strike |
| $r, q$ | Constant annual continuously compounded domestic rate and dividend yield; for FX, q is the foreign rate |
| $\sigma$ | Positive annual volatility, expressed as a decimal |
| $t_{j}$ | Strictly increasing future observation times in years; $t_{0}=0$ |
| $T, T_{p}$ | Last observation time and payment time; $T_{p} \ge  T$ |
| $w_{j}$ | Deterministic nonnegative weights; include historical weights when normalizing the full average |
| $Z_{j}$ | Independent standard normal draws for one path |
| $D$ | Discount factor $\exp (-r\cdot T_{p})$ |
| $g$ | Undiscounted contractual payoff |
| $H$ | A single-path discounted payoff D*g |
| $M$ | Number of independent observations used to estimate a mean |
| $\Phi , \phi$ | Standard normal CDF and density |

For constant-parameter risk-neutral GBM, define $b=r-q-\sigma ^{2}/2$. Then
**Construct observation times, Brownian values and stock paths**

$$
\begin{gathered}
\mathrm{d}t_{j} = t_{j} - t_{j-1} \\
W_{j} = \sum _{k\le j}(\sqrt{\mathrm{d}t_{k}}\cdot Z_{k}) \\
S_{j} = S\cdot \exp (b\cdot t_{j} + \sigma \cdot W_{j})
\end{gathered}
$$

**Option value as an expected discounted payoff**

$$
V = \operatorname{E}[H]
$$

A log drift supplied as b already includes the variance correction. The Z array has one row per path and one column per future increment. European-only simulation can use one increment ending at T.

Greek definitions used here are $\Delta=\mathrm{d}V/\mathrm{d}S$, $\Gamma=\mathrm{d}^{2}V/\mathrm{d}S^{2}$, $\mathrm{Vega}=\mathrm{d}V/\mathrm{d}\sigma$ and $\mathrm{Rho}=\mathrm{d}V/\mathrm{d}r$. Other inputs stay fixed. These are derivatives per unit of the decimal input. Multiply Vega or Rho by 0.01 to quote the approximate change for a one-percentage-point increase; a 1% relative change in volatility is a different shock. Do not scale twice.

For a European option with payment at expiry, hold spot and other constant model inputs fixed. Let $T$ and $h$ be measured in years, with $0<h<T$. The backward difference below estimates maturity sensitivity:

$$
V_T=\frac{\partial V}{\partial T}
\approx-\frac{V(T-h)-V(T)}{h},
\qquad
\Theta=-V_T.
$$

Compare this difference with negative BS calendar Theta in the same annual units. A one-day bump $h=1/B$, where $B$ is the specified days-per-year basis, does not itself make the quotient a daily sensitivity. Divide both the estimate and its SE by $B$ only when converting to daily units; reversing the sign leaves SE unchanged. Follow explicitly specified formulas and scaling; distinguish their meaning from their labels.

Zero volatility or expired contracts need deterministic/limit handling; score formulas that divide by $\sigma$ or time do not apply there.

## 2. Samples, Variance and Standard Error

For every estimator, first compute one random contribution $G_{i}$ per independent observation. Then
**Estimation and standard error from independent path contributions**

$$
\begin{gathered}
\mathrm{estimate} = \operatorname{mean}(G_{i}) \\
\;\text{sample}\;_{\mathrm{variance}} = \sum _{i}((G_{i}-\mathrm{estimate})^{2})/(M-1) \\
\mathrm{SE} = \sqrt{\;\text{sample}\;_{\mathrm{variance}}/M}
\end{gathered}
$$

The variance of individual contributions is not the variance of their mean. A variance comparison must use the same level of aggregation for both methods. For antithetic sampling, average each pair before applying these formulas; M counts independent pairs. Do not use an IID standard error for correlated observations without accounting for dependence.

When comparing two estimates on shared paths, calculate paired differences $G_{i}$-$J_{i}$ and their SE; independent-error addition ignores their covariance. A confidence interval describes sampling uncertainty, not finite-difference bias, discretization error or a wrong contract.

## 3. Finite Differences

Use [Shared Foundations](#1-shared-foundations) for the derivative and [Section 2](#2-samples-variance-and-standard-error) for its SE.

For parameter a and bump $h>0$, evaluate discounted payoffs on the same base random draws at a+h, a and a-h:
**Central finite-difference contribution for a first derivative**

$$
G_{\mathrm{first},i} = (H_{i}(a+h)-H_{i}(a-h))/(2\cdot h)
$$

**Central finite-difference contribution for a second derivative**

$$
G_{\mathrm{second},i} = (H_{i}(a+h)-2\cdot H_{i}(a)+H_{i}(a-h))/h^{2}
$$

Their means estimate first and second derivatives. Their sample standard deviations give the SEs. Computing only the bumped price means loses the information needed for the paired SE; subtract the per-path payoffs first.

Common random numbers couple scenarios, reducing noise for many option sensitivities. Reusing a seed is insufficient if different branches consume different draws. Keep the same path index aligned across bumps. Recompute everything that depends on the bumped parameter, including drift, diffusion, discount factors and any affected fixing times; hold unrelated contract terms fixed.

Central differences have second-order bump bias when the price has the required smooth derivatives. Smaller h can increase sampling noise or floating-point cancellation, especially for $\Gamma$. Compare more than one sensible bump size when the result is suspect, without changing a bump explicitly prescribed by the task. For ordinary calendar Theta, a central maturity bump gives
**Calendar-Theta finite-difference contribution**

$$
G_{\theta,i} = -(H_{i}(T+h)-H_{i}(T-h))/(2\cdot h)
$$

This central approximation requires $T>h$ and the payment/observation-time convention defined in Section 1; apply the same convention to each path contribution.

## 4. Pathwise Estimators

Use PW for the supported continuous vanilla or arithmetic-average call/put payoffs below, when differentiation under expectation is valid. Keep the base normal draws fixed. First select call or put in the following definition; then select terminal or arithmetic-average dependence. These are separate decisions. A density score belongs to LR, not this block.

### Shared payoff and sign definition

For an average or terminal value U, define
**Call payoff and its pathwise derivative**

$$
g_{\mathrm{call}}(U) = \max (U-K,0);  g_{\mathrm{call},\mathrm{prime}}(U) = \operatorname{indicator}(U>K)
$$

**Put payoff and its pathwise derivative**

$$
g_{\mathrm{put}}(U)  = \max (K-U,0);  g_{\mathrm{put},\mathrm{prime}}(U)  = -\operatorname{indicator}(U<K)
$$

At a kink, almost-sure differentiation alone is not sufficient: exchanging differentiation and expectation also needs regularity/integrability. Ordinary GBM call/put first sensitivities satisfy the needed conditions away from degenerate cases. Digital payoffs and barrier indicators require separate treatment.

### Path derivatives used by both supported payoff branches

Differentiating $S_{j}$ and D yields
**Path sensitivity to initial spot**

$$
\mathrm{d}S_{j}/\mathrm{d}S = S_{j}/S
$$

**Path sensitivity to volatility**

$$
\mathrm{d}S_{j}/\mathrm{dsigma} = S_{j}\cdot (W_{j}-\sigma \cdot t_{j})
$$

**Path sensitivity to the interest rate**

$$
\mathrm{d}S_{j}/\mathrm{d}r = t_{j}\cdot S_{j}
$$

**Discount-factor sensitivity to the interest rate**

$$
\mathrm{d}D/\mathrm{d}r = -T_{p}\cdot D
$$

### Payoff depends only on the terminal stock price

For a European payoff $g(S_T)$, with fixed strike and payment date $T_{p} \ge  T$, use $W_{T}=\sqrt{T}\cdot Z$. The explicit pathwise contributions are
**European pathwise Delta contribution**

$$
G_{\Delta} = D\cdot g_{\mathrm{prime}}(S_{T})\cdot S_{T}/S
$$

**European pathwise vega contribution**

$$
G_{\mathrm{vega}} = D\cdot g_{\mathrm{prime}}(S_{T})\cdot S_{T}\cdot (\sqrt{T}\cdot Z - \sigma \cdot T)
$$

**European pathwise Rho contribution, including discounting**

$$
G_{\mathrm{Rho}} = D\cdot (g_{\mathrm{prime}}(S_{T})\cdot T\cdot S_{T} - T_{p}\cdot g(S_{T}))
$$

For a call, $g_{\mathrm{prime}}(S_{T})=\operatorname{indicator}(S_{T}>K)$; for a put, $g_{\mathrm{prime}}(S_{T})=-\operatorname{indicator}(S_{T}<K)$. For each Greek, apply Section 2 to its per-path contributions to obtain the mean and standard error, then apply any requested unit conversion to both.

### Payoff depends on a weighted arithmetic average

Use this block when several fixing prices enter the average. Retain the original full-contract weights and fixed history. For a weighted arithmetic average with already fixed observations,
**Arithmetic payoff underlying with known past fixings**

$$
U = a_{\mathrm{past}} + \sum _{\mathrm{future}}(w_{j}\cdot S_{j})
$$

**Arithmetic-average spot sensitivity**

$$
U_{S} = \sum _{\mathrm{future}}(w_{j}\cdot S_{j}/S)
$$

**Arithmetic-average volatility sensitivity**

$$
U_{\sigma} = \sum _{\mathrm{future}}(w_{j}\cdot S_{j}\cdot (W_{j}-\sigma \cdot t_{j}))
$$

**Arithmetic-average rate sensitivity**

$$
U_{r} = \sum _{\mathrm{future}}(w_{j}\cdot t_{j}\cdot S_{j})
$$

Here $a_{\mathrm{past}}$ is constant, and weights retain their original full-contract normalization. Future weights need not sum to one. Historical prices do not change when current spot is bumped. If the payoff explicitly contains today's spot as a variable, include that extra derivative instead of treating it as a frozen fixing.

The arithmetic-average single-path contributions, using U and its derivatives just above and the shared signed payoff derivative, are
**Asian pathwise Delta contribution**

$$
G_{\Delta} = D\cdot g_{\mathrm{prime}}(U)\cdot U_{S}
$$

**Asian pathwise vega contribution**

$$
G_{\mathrm{vega}} = D\cdot g_{\mathrm{prime}}(U)\cdot U_{\sigma}
$$

**Asian pathwise Rho contribution, including discounting**

$$
G_{\mathrm{Rho}} = D\cdot (g_{\mathrm{prime}}(U)\cdot U_{r} - T_{p}\cdot g(U))
$$

The negative discount term is necessary for Rho. Put Greeks require the negative put payoff derivative, not the call indicator.

PW differentiates the payoff along each simulated path; LR multiplies the payoff by a density score. Do not interchange these contributions. Differentiate discounting separately where required.

### Time sensitivity: select the schedule convention first

For a European option with $T_{p}=T$ and fixed Z,
**Terminal-stock maturity sensitivity**

$$
U_{T} = S_{T}\cdot (b + \sigma \cdot Z/(2\cdot \sqrt{T}))
$$

**European calendar-Theta contribution**

$$
G_{\Theta} = D\cdot (r\cdot g(S_{T}) - g_{\mathrm{prime}}(S_{T})\cdot U_{T})
$$

For a fresh Asian whose dates scale as $t_{j}=\lambda _{j}\cdot T$ and payment scales as $T_{p}=\lambda _{p}\cdot T$, keeping lambdas fixed,
**Average maturity sensitivity when fixing dates scale**

$$
U_{T} = \sum _{j}(w_{j}\cdot S_{j}\cdot (b\cdot \lambda _{j} + \sigma \cdot W_{j}/(2\cdot T)))
$$

**Negative maturity sensitivity with scaled payment time**

$$
G_{\mathrm{minus},\mathrm{maturity}} = D\cdot (r\cdot \lambda _{p}\cdot g(U) - g_{\mathrm{prime}}(U)\cdot U_{T})
$$

This is minus the derivative of that scaled-schedule family, not automatically calendar decay of a seasoned fixed-date contract.

Naively differentiating the vanilla pathwise $\Delta$ again gives an invalid $\Gamma$ estimator: it misses the exercise-boundary contribution. Use FD, LR, or a separately derived smoothing/hybrid method. Pathwise $\Gamma$ is not generally zero. A task may request that some otherwise computable sensitivities be left unavailable; distinguish a task restriction from a mathematical impossibility.

## 5. Likelihood Ratio Estimators

Use [Shared Foundations](#1-shared-foundations) and [Section 2](#2-samples-variance-and-standard-error).

Let X have density $p_{a}$(x), with a parameter-independent support and sufficient regularity to differentiate its integral. Hold x fixed when differentiating log density. Write $L_{a}=\partial _{a} \log  p_{a}(x)$. Then
**First-derivative likelihood-ratio identity**

$$
d/\mathrm{d}a \operatorname{E}_{a}[f(X,a)] = \operatorname{E}_{a}[\partial _{a} f(X,a) + f(X,a)\cdot L_{a}]
$$

For parameter-independent f, the second derivative uses
**Second-derivative likelihood-ratio identity**

$$
d^{2}/\mathrm{d}a^{2} \operatorname{E}_{a}[f(X)] = \operatorname{E}_{a}[f(X)\cdot (L_{a}^{2} + \partial _{a} L_{a})]
$$

A first-order score squared alone is not the second-order weight. Explicit parameter dependence in a payoff or discount factor adds derivative terms; it cannot be hidden inside a density score.

### European terminal density

Use this block when the payoff depends only on $S_{T}$ and the assumptions below hold. If several fixing prices affect the payoff, use the joint-path block instead.

For a payoff $g(S_T)$ with no explicit dependence on S, $\sigma$ or r, set $a=\sigma \cdot \sqrt{T}$, and
**Standardize the terminal log return**

$$
Z = (\ln (S_{T}/S)-b\cdot T)/a
$$

**Terminal-density spot score**

$$
L_{S} = Z/(S\cdot a)
$$

**Terminal-density volatility score**

$$
L_{\sigma} = (Z^{2}-1)/\sigma  - Z\cdot \sqrt{T}
$$

**Terminal-density rate score**

$$
L_{r} = Z\cdot \sqrt{T}/\sigma
$$

**Terminal-density second-spot-derivative weight**

$$
W_{\mathrm{SS}} = (Z^{2}-1-a\cdot Z)/(S^{2}\cdot a^{2})
$$

These follow by differentiating the lognormal log density: $-\ln (S_{T})-\ln (a)-Z^{2}/2$ plus a constant. For example, $\partial _{S} Z=-1/(S\cdot a)$; combining $\partial_SL_S$ with $L_{S}^{2}$ gives $W_{\mathrm{SS}}$.

**European LR Delta contribution**

$$
G_{\Delta} = D\cdot g(S_{T})\cdot L_{S}
$$

**European LR Gamma contribution**

$$
G_{\Gamma} = D\cdot g(S_{T})\cdot W_{\mathrm{SS}}
$$

**European LR vega contribution**

$$
G_{\mathrm{vega}} = D\cdot g(S_{T})\cdot L_{\sigma}
$$

**European LR Rho contribution, including discounting**

$$
G_{\mathrm{Rho}} = D\cdot g(S_{T})\cdot (L_{r}-T_{p})
$$

These weights are for derivatives with respect to S and $\sigma$, not $\log  S$ and $\log  \sigma$. Rho includes differentiation of discounting. This reference does not provide an LR time estimator; do not assume the time Greek is universally impossible.

### Discretely observed paths

Use this block when the payoff depends on multiple observed stock prices and has the supported parameter dependence below. Do not obtain an Asian estimator by changing only the payoff in the terminal-density formula. Use the joint density of all observations affecting the payoff. With $t_{1}>0$, define
**Standardized path transition innovations**

$$
Z_{j} = (\ln (S_{j}/S_{j-1})-b\cdot \mathrm{d}t_{j})/(\sigma \cdot \sqrt{\mathrm{d}t_{j}})
$$

**Joint density of the observed path**

$$
p(S_{1},\ldots ,S_{n} \vert  S) = \prod _{j} p(S_{j} \vert  S_{j-1})
$$

When observed prices are held fixed, initial S occurs only in the first transition. Consequently,
**Joint-path spot score**

$$
L_{S,\mathrm{path}} = Z_{1}/(S\cdot \sigma \cdot \sqrt{\mathrm{d}t_{1}})
$$

**Joint-path second-spot-derivative weight**

$$
W_{\mathrm{SS},\mathrm{path}} = (Z_{1}^{2}-1-\sigma \cdot \sqrt{\mathrm{d}t_{1}}\cdot Z_{1})/(S^{2}\cdot \sigma ^{2}\cdot \mathrm{d}t_{1})
$$

**Joint-path volatility score**

$$
L_{\sigma,\mathrm{path}} = \sum _{j}((Z_{j}^{2}-1)/\sigma  - Z_{j}\cdot \sqrt{\mathrm{d}t_{j}})
$$

**Joint-path rate score**

$$
L_{r,\mathrm{path}} = \sum _{j}(Z_{j}\cdot \sqrt{\mathrm{d}t_{j}}/\sigma )
$$

With g the full path payoff and $D=\exp (-r\cdot T_{p})$, the contributions are
**Path-dependent LR Delta contribution**

$$
G_{\Delta} = D\cdot g\cdot L_{S,\mathrm{path}}
$$

**Path-dependent LR Gamma contribution**

$$
G_{\Gamma} = D\cdot g\cdot W_{\mathrm{SS},\mathrm{path}}
$$

**Path-dependent LR vega contribution**

$$
G_{\mathrm{vega}} = D\cdot g\cdot L_{\sigma,\mathrm{path}}
$$

**Path-dependent LR Rho contribution, including discounting**

$$
G_{\mathrm{Rho}} = D\cdot g\cdot (L_{r,\mathrm{path}}-T_{p})
$$

Apply Section 2 to each contribution for its estimate and SE. These formulas cover a weighted arithmetic Asian with fixed historical contributions and no other explicit parameter dependence. For $n=1$ they reduce to the terminal formulas. An initial fixing that varies with S or a spot-linked strike introduces explicit payoff derivatives; use the general identity rather than these shortened products.

Very small first observation times can make LR spot weights noisy. The volatility score also accumulates contributions from all increments. Increasing the number of dates can increase LR variance; it does not automatically improve accuracy.

## 6. Analytic Benchmarks and Checks

Use [Shared Foundations](#1-shared-foundations); compare the same contract, units, payment date, derivative variable and sign convention. Convert both estimates to the same convention before comparing; maturity sensitivity and calendar Theta have opposite signs under the stated European convention.

For a European call/put with payment at T,
**Black–Scholes benchmark thresholds**

$$
\begin{gathered}
\mathrm{d1} = (\ln (S/K)+(r-q+\sigma ^{2}/2)\cdot T)/(\sigma \cdot \sqrt{T}) \\
\mathrm{d2} = \mathrm{d1}-\sigma \cdot \sqrt{T}
\end{gathered}
$$

**European call benchmark**

$$
C = S\cdot \exp (-q\cdot T)\cdot \Phi (\mathrm{d1})-K\cdot \exp (-r\cdot T)\cdot \Phi (\mathrm{d2})
$$

**European put benchmark**

$$
\operatorname{P} = K\cdot \exp (-r\cdot T)\cdot \Phi (-\mathrm{d2})-S\cdot \exp (-q\cdot T)\cdot \Phi (-\mathrm{d1})
$$

**Call Delta benchmark**

$$
\Delta _{C} = \exp (-q\cdot T)\cdot \Phi (\mathrm{d1})
$$

**Put Delta benchmark**

$$
\Delta _{\operatorname{P}} = \exp (-q\cdot T)\cdot (\Phi (\mathrm{d1})-1)
$$

**$\Gamma$ benchmark**

$$
\Gamma  = \exp (-q\cdot T)\cdot \phi (\mathrm{d1})/(S\cdot \sigma \cdot \sqrt{T})
$$

**Vega benchmark**

$$
\mathrm{Vega} = S\cdot \exp (-q\cdot T)\cdot \phi (\mathrm{d1})\cdot \sqrt{T}
$$

**Call Rho benchmark**

$$
\mathrm{Rho}_{C} = K\cdot T\cdot \exp (-r\cdot T)\cdot \Phi (\mathrm{d2})
$$

**Put Rho benchmark**

$$
\mathrm{Rho}_{\operatorname{P}} = -K\cdot T\cdot \exp (-r\cdot T)\cdot \Phi (-\mathrm{d2})
$$

**Call calendar-Theta benchmark**

$$
\begin{gathered}
\Theta _{C} = -S\cdot \exp (-q\cdot T)\cdot \phi (\mathrm{d1})\cdot \sigma /(2\cdot \sqrt{T}) \\
+ q\cdot S\cdot \exp (-q\cdot T)\cdot \Phi (\mathrm{d1})-r\cdot K\cdot \exp (-r\cdot T)\cdot \Phi (\mathrm{d2})
\end{gathered}
$$

**Put calendar-Theta benchmark**

$$
\begin{gathered}
\Theta _{\operatorname{P}} = -S\cdot \exp (-q\cdot T)\cdot \phi (\mathrm{d1})\cdot \sigma /(2\cdot \sqrt{T}) \\
- q\cdot S\cdot \exp (-q\cdot T)\cdot \Phi (-\mathrm{d1})+r\cdot K\cdot \exp (-r\cdot T)\cdot \Phi (-\mathrm{d2})
\end{gathered}
$$

For payment delayed to $T_{p}$, price is $\exp (-r\cdot (T_{p}-T))$ times the price payable at T. Differentiating that factor adds terms for rate or time sensitivities. Do not blindly multiply every Greek by the same factor.

Differentiating put-call parity at fixed T gives
**Greek identities obtained by differentiating European put-call parity**

$$
\begin{gathered}
\Delta _{C}-\Delta _{\operatorname{P}} = \exp (-q\cdot T) \\
\Gamma _{C}-\Gamma _{\operatorname{P}} = 0 \\
\mathrm{Vega}_{C}-\mathrm{Vega}_{\operatorname{P}} = 0 \\
\mathrm{Rho}_{C}-\mathrm{Rho}_{\operatorname{P}} = K\cdot T\cdot \exp (-r\cdot T) \\
\Theta _{C}-\Theta _{\operatorname{P}} = q\cdot S\cdot \exp (-q\cdot T)-r\cdot K\cdot \exp (-r\cdot T)
\end{gathered}
$$

For an Asian average, start from $C_{A}-\operatorname{P}_{A}=D\cdot (\operatorname{E}[A]-K)$ and differentiate its actual schedule and weights. European parity derivatives do not automatically apply.

For any LR score with fixed support, $\operatorname{E}[L_{a}]=0$; likewise $\operatorname{E}[W_{\mathrm{SS}}]=0$. Test these identities and simple payoffs with known derivatives. Passing them does not prove the whole pricer correct. Compare European Greeks with the analytic benchmark and Asian PW/FD estimates with paired errors, accounting for bump bias. For an exact geometric-average benchmark, use the same fixing schedule and payment date as the simulation.

Neither Asian versus European price or Delta ordering nor PW versus LR variance ordering is a universal law across contracts and parameters. Larger M reduces standard error at rate $1/\sqrt{M}$ for IID finite-variance estimators; individual estimates need not approach the truth monotonically.

## 7. Numerical considerations and scope

Uncertainty is computed from per-path estimator contributions. Counts, means and centered sums of squares suffice for batched variance estimation without retaining all paths. Stable variance accumulation and matched random draws across bumps preserve the intended estimator; estimates sharing draws are correlated.

An analytic Greek is not an MC estimator. An uncomputed estimator is distinct from a zero estimate or a mathematically unavailable Greek.

The formulas assume constant-parameter GBM, deterministic dates/weights and the stated payoff dependence. Stochastic volatility, jumps, continuous monitoring, early exercise, discontinuous payoffs or parameter-dependent support require separate derivations. For Asian pricing, seasoned reduction and geometric control prices, consult the Asian-options reference; the Monte Carlo arithmetic price itself does not require a Curran approximation.

## 8. References

- Broadie and Glasserman (1996), *Estimating Security Price Derivatives Using Simulation*, Management Science 42(2), 269–285. [Author-hosted paper](https://www.columbia.edu/~mnb2/broadie/Assets/bg_ms_1996.pdf).
- Martin Haugh, *Monte-Carlo Simulation: Estimating the Greeks*. [Columbia lecture slides](https://www.columbia.edu/~mh2078/MonteCarlo/MCS_Greeks_MasterSlides.pdf), sections on FD, pathwise estimators, joint-density scores and second derivatives.
- Glasserman (2004), *Monte Carlo Methods in Financial Engineering*, Chapter 7: sensitivity estimation and estimator variance.

The GBM formulas above are explicit differentiations of the displayed transition density and simulated path. They use the conventions stated here; particular task conventions must be mapped separately.
