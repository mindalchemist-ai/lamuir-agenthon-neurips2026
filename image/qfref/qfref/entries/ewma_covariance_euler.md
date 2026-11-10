# EWMA Covariance and Euler Portfolio Risk Decomposition

Use this document to estimate exponentially weighted return covariance and attribute a linear portfolio's volatility or normal VaR to its assets. It distinguishes conditional EWMA forecasts from centered weighted sample covariance, and marginal risk from component risk. It does not cover nonlinear portfolio revaluation or risk-parity optimization.

## Contents

1. [Shared Foundations](#1-shared-foundations)
2. [EWMA Covariance and Estimation Conventions](#2-ewma-covariance-and-estimation-conventions)
3. [Portfolio Volatility and Normal VaR](#3-portfolio-volatility-and-normal-var)
4. [Euler Risk Decomposition](#4-euler-risk-decomposition)
5. [Checks and Scope](#5-checks-and-scope)
6. [References](#6-references)

## 1. Shared Foundations

Map the task's notation, definitions and units to the quantities here. Explicit task conventions take precedence; if they conflict or leave an estimator unspecified, identify the ambiguity and state the interpretation. A parameter's name alone does not define its statistical role.

| Symbol | Meaning |
| --- | --- |
| n; i, j | Number of assets; asset indices |
| $t$ | Observation index, increasing from oldest to newest |
| $r_{t}$ | Column vector of simultaneous one-period returns, in decimals |
| $m_{t}$ | Conditional mean of $r_{t}$, specified using information available before t |
| $e_{t}$ | Return innovation $r_{t}$ - $m_{t}$ |
| $C_{t}$ | Covariance forecast after incorporating observation t, for the next period |
| $\lambda$ | Decay factor, normally $0 < \lambda  < 1$ |
| $w$ | Asset weights, in exactly the same order as $C_{t}$'s rows and columns |
| $C; \mu$ | Covariance matrix and mean-return vector for the risk horizon being measured |
| $\sigma _{p}$ | Portfolio volatility in return units |
| $\alpha$; $\Phi$ | Confidence probability in (0,1); standard normal cumulative distribution |
| $A$ | Number of observation periods per year |

For simple returns and beginning-of-period weights, the portfolio return is the weighted asset return. A weighted sum of log returns is generally only an approximation to a portfolio's log return.

$$
r_{p,t} = w^{T} r_{t}
$$

Here superscript T means transpose. Changes from decimal returns to percentage-point returns multiply covariance by $100^2$ and volatility by 100. Asset order, units and observation dates must agree before combining covariance with weights. Missing observations require a specified policy; they are not zero returns.

## 2. EWMA Covariance and Estimation Conventions

### Conditional covariance forecast

Use this branch for a RiskMetrics-style conditional forecast. Under the zero-conditional-mean approximation, $e_{t} = r_{t}$. If a nonzero conditional mean model is specified, use its innovations. Subtracting the full sample mean instead defines a different estimator and can introduce future information into historical forecasts.

The innovation outer product supplies one variance or covariance update for each asset pair; it is an n-by-n matrix, not the scalar sum of squared innovations.

The $(i,j)$ entry of $e_{t} e_{t}^{T}$ is $e_{t,i} \cdot  e_{t,j}$.

The covariance forecast weights the previous forecast and the latest outer product.

$$
C_{t} = \lambda \cdot C_{t-1} + (1-\lambda )\cdot e_{t} e_{t}^{T}
$$

Given an initial forecast $C_{0}$ before the m observations being incorporated, expanding the recursion gives its finite-history form.

$$
C_{m} = \lambda ^{m}\cdot C_{0} + (1-\lambda )\cdot \sum _{j=1}^{m}[\lambda ^{m-j}\cdot e_{j} e_{j}^{T}]
$$

The initial condition remains with weight $\lambda^{m}$. A zero matrix, a first-observation outer product and an initial sample covariance are distinct seeds; EWMA alone does not choose between them. When the input includes code to be repaired (a template or starter script the task asks you to fix), the seed, window and normalization that this code already uses are the chosen convention unless the task lists one of them as a defect: keep them, and change only the lines that correspond to a stated defect. A first-observation seed already incorporates that observation, so the next update incorporates the next observation. A sample-covariance seed also requires its own sample interval, centering and divisor conventions.

**Estimation window and initialization window are different.** A trailing estimation window selects which recent observations enter an estimate at a particular date. An initialization window supplies a starting matrix, after which subsequent observations update it. An expanding recursive history retains older information through the previous matrix. Neither a window length nor a decay factor specifies all three choices. Preserve the stated sample interval, seed and normalization together.

### Recursive EWMA over an estimation window

This block is the first-observation-seeded convention, as in `ewm(adjust=False)`, applied to the most recent $L$ observations. Use it only when that initialization is selected; a window length and decay factor alone do not choose the seed. A zero-seed finite-history alternative is $C=(1-\lambda)\sum_{k=0}^{L-1}\lambda^k e_{t-k}e_{t-k}^T$, which is not renormalized and gives a different oldest-observation weight.

Window from oldest to newest: $e_{t-L+1}, \ldots , e_{t}$.

$$
C = e_{t-L+1} e_{t-L+1}^{T}
$$

For $s = t-L+2, \ldots , t$:

$$
C = \lambda \cdot C + (1-\lambda )\cdot e_{s} e_{s}^{T}
$$

The result is the forecast after the newest observation. It is not centered, renormalized or divided by $(1-\lambda^L)$. A window length given in the configuration applies even when existing code ignores it; observations older than the window do not enter.

### Normalized finite-window moments

Use this branch only when the specification explicitly requests exponentially weighted moments whose weights sum to one. A window length for a recursive EWMA does not by itself request this branch. Let k be the age of an observation ($k=0$ is newest), and L the window length.

The normalized observation weight is:

$$
p_k=\frac{\lambda^k}{\sum_{a=0}^{L-1}\lambda^a},\qquad k=0,\ldots,L-1
$$

For a zero-mean model, the finite-window second moment is:

$$
C_{\mathrm{zero}} = \sum _{k=0}^{L-1}[p_{k}\cdot r_{t-k} r_{t-k}^{T}]
$$

If instead a centered weighted sample covariance is requested, first define the weighted sample mean.

$$
\bar{r} = \sum _{k=0}^{L-1}[p_{k}\cdot r_{t-k}]
$$

The centered population-form weighted covariance is:

$$
C_{\mathrm{centered}} = \sum _{k=0}^{L-1}[p_{k}\cdot (r_{t-k}-\bar{r})\cdot (r_{t-k}-\bar{r})^{T}]
$$

For fixed deterministic weights and independent observations with a common mean and covariance, the usual unbiased correction divides $C_{\mathrm{centered}}$ by $1-\sum (p_{k}^{2})$, when positive. That correction is not part of the conditional EWMA recursion. The normalization and centering choices in a statistical covariance routine cannot be assumed to match a requested forecast.

With zero initialization, uncentered recursion over L observations equals $(1-\lambda^L)C_{\mathrm{zero}}$. Dividing a recursion with a nonzero seed by this factor does not remove the seed and is not the same finite-window estimator.

## 3. Portfolio Volatility and Normal VaR

For a linear portfolio, variance is the covariance quadratic form.

$$
v_{p} = w^{T} C w
$$

Portfolio volatility is its nonnegative square root.

$$
\sigma _{p} = \sqrt{v_{p}}
$$

The normal quantile is determined by the confidence probability, not by a fixed rounded constant.

$$
z_{\alpha} = \Phi ^{-1}(\alpha )
$$

When loss is minus return, the normal loss quantile includes the portfolio mean. A zero-mean specification sets $\mu$ to zero. Here $\mu$ is the conditional mean forecast that goes with $C$. The RiskMetrics EWMA method takes the conditional mean of daily returns as zero, consistent with its uncentered recursion, so with an EWMA covariance a full-sample average return is not $\mu$ unless the task says to use one.

$$
\operatorname{VaR}_{\alpha} = z_{\alpha}\cdot \sigma _{p} - w^{T} \mu
$$

This is a return-unit quantile; for a positive portfolio value P, currency VaR is $P\operatorname{VaR}_\alpha$. A convention that floors VaR at zero is an additional convention, not part of this formula.

Under the conventional unchanged per-period covariance and uncorrelated additive-return assumptions, annualized volatility is:

$$
\sigma _{\mathrm{annual}} = \sqrt{A}\cdot \sigma _{p}
$$

The corresponding annualized covariance is A*C. These are horizon-scaling assumptions, not exact laws for compounded returns or serially correlated returns. An already annualized covariance must not be annualized again.

## 4. Euler Risk Decomposition

Use this block for attribution of volatility with C fixed and $\sigma _{p} > 0$. Derivatives vary one weight while holding other weights fixed; renormalizing weights during differentiation measures a different sensitivity.

The covariance exposure vector has one element per asset.

$$
b = C\cdot w
$$

Marginal risk is the derivative of portfolio volatility with respect to an asset weight.

$$
\mathrm{MRC}_{i} = \partial (\sigma _{p})/\partial (w_{i}) = b_{i}/\sigma _{p}
$$

Component risk multiplies that derivative by the position's weight.

$$
\mathrm{RC}_{i} = w_{i}\cdot \mathrm{MRC}_{i}
$$

Fractional contribution divides component risk by total volatility; multiply by 100 only when reporting percent rather than a fraction.

$$
\mathrm{PRC}_{i} = \mathrm{RC}_{i}/\sigma _{p} = w_{i}\cdot b_{i}/v_{p}
$$

Euler's identity for the degree-one volatility function gives full allocation.

$$
\sum _{i} \mathrm{RC}_{i} = \sigma _{p};  \sum _{i} \mathrm{PRC}_{i} = 1
$$

Negative contributions can represent hedging and need not be clipped. Weights need not all be positive or sum to one for the algebraic identity to hold. Replacing them by absolute values changes the portfolio.

If the requested risk measure is variance, an additive variance allocation has different units.

$$
\mathrm{VC}_{i} = w_{i}\cdot b_{i};  \sum _{i} \mathrm{VC}_{i} = v_{p}
$$

Variance is homogeneous of degree two, so its literal Euler derivative contributions sum to twice the variance; they are not the volatility components above.

$$
\partial (v_{p})/\partial (w_{i}) = 2\cdot b_{i}
$$

For normal VaR with fixed C and $\mu$, the component allocation also includes the mean term.

$$
\mathrm{RC}_{\mathrm{VaR}},i = w_{i}\cdot (z_{\alpha}\cdot \mathrm{MRC}_{i} - \mu _{i})
$$

These components sum to $\operatorname{VaR}_{\alpha}$. With zero mean they are $z_{\alpha}$ times the volatility components. Multiplication by a positive portfolio value converts them to currency; it does not change fractional contributions when the total is nonzero. A zero total VaR has no defined percentage allocation.

## 5. Checks and Scope

A common $\lambda$ and a positive-semidefinite seed preserve symmetry and positive semidefiniteness in exact arithmetic. Applying unrelated decay factors separately to matrix entries need not do so. Materially negative eigenvalues or variance indicate a problem; small roundoff negatives require a scale-aware tolerance rather than arbitrary changes to the estimate.

The expanded-history formula checks the recursion, including the seed and observation order. With $\lambda =0$ the next forecast is the latest outer product; with $\lambda =1$ it remains the seed. Finite-window normalization and the unbiased correction have separate edge cases; one observation has no unbiased centered covariance estimate.

The Euler sum identities check allocation algebra **but cannot establish that the covariance estimator, window, asset ordering or horizon is correct**. Independent checks include a diagonal covariance case, consistent asset permutations, the expanded-history result, and volatility derivatives with C held fixed. A scalar rank-one update cannot reproduce differing asset variances and cross-covariances.

If $\sigma _{p}=0$, the displayed MRC and PRC ratios are undefined; adding an arbitrary positive denominator changes their meaning. A singular covariance can still produce positive portfolio volatility, in which case these formulas remain valid.

EWMA responds to squared innovations; it does not by itself establish normal tails, remove serial dependence, or describe a nonlinear payoff. Quantile risk and volatility attribution are distinct from identifying equal-risk portfolio weights.

## 6. References

J.P. Morgan / Reuters, *RiskMetrics — Technical Document*, fourth edition (1996), §5.2.1 and §5.2.1.1: exponential variance and covariance forecasts. The matrix expansion and estimator distinctions above follow by algebra under the explicitly stated seed and mean conventions. [Publisher PDF](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a).

Dirk Tasche, *Capital Allocation to Business Units and Sub-Portfolios: the Euler Principle*, arXiv:0708.2542, revised 2008, §2 and §3.1: homogeneous risk allocation and standard-deviation contributions. The weight-coordinate and normal-quantile forms above follow by differentiation. [Author paper](https://arxiv.org/abs/0708.2542).
