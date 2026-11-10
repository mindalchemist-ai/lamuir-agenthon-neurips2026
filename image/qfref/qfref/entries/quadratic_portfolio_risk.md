# Delta-gamma-vega risk: units, covariance and variance allocation

Use a local price expansion to relate market-factor shocks to portfolio P&L. Explicit contract definitions determine shock horizon, units and allocation convention. A local expansion is unreliable across a barrier crossing, discontinuity or large market move.

## Local portfolio response

For factor increments $x$, define $a$ as portfolio first derivatives, symmetric $G$ as portfolio second derivatives, and $c$ as deterministic carry. Derivatives include signed position sizes. The second-order P&L approximation is:

$$
Y=c+a'x+\frac12x'Gx
$$

For spot and annualized volatility as separate factors, their linear coefficients are position-scaled Delta and Vega. The spot diagonal of $G$ is position-scaled Gamma. A return shock must first be converted to a spot increment, approximately $\Delta S=S r$ for a small simple return. A volatility shock is an absolute change in annualized decimal volatility, not a percent return on volatility.

## Gaussian shock moments

When the task names the model volatility as the input for pricing and risk, take the spot shock from it: for a one-day horizon $\sigma_{S} = S\,\sigma_{\mathrm{model}}/\sqrt{252}$ with an annualized $\sigma_{\mathrm{model}}$. Sample moments of historical price changes are a different input. Under the Gaussian model below the gamma term contributes $\operatorname{Var}(\tfrac12\Gamma\Delta S^{2}) = \tfrac12\Gamma^{2}\sigma_{S}^{4}$; an empirical variance of $\Delta S^{2}$ from fat-tailed history is larger and changes every variance share.

Assume $x\sim N(m,C)$ and set $b=a+Gm$. Gaussian odd centered moments vanish; paired fourth moments give the mean and variance:

$$
\operatorname{E}[Y]=c+a'm+\frac12m'Gm+\frac12\sum_i(GC)_{ii}
$$

$$
\operatorname{Var}(Y)=b'Cb+\frac12\sum_i(GCGC)_{ii}
$$

With centered spot and volatility shocks, $\operatorname{Cov}((\Delta S)^2,\Delta S)=\operatorname{Cov}((\Delta S)^2,\Delta\sigma)=0$ under joint normality. Linear Delta and Vega components can still covary. Non-Gaussian shocks can introduce all these covariances.

## Component allocation

Let $Y_j$ denote a specified additive P&L component and $Y=\sum_jY_j$; constant carry has zero variance. Covariance allocation splits every pair covariance equally between its two components:

$$
A_j=\operatorname{Cov}(Y_j,Y),\qquad
\sum_j A_j=\operatorname{Var}(Y)
$$

For strictly positive total variance, its shares sum to one:

$$
p_j=\frac{A_j}{\operatorname{Var}(Y)}
$$

A share can be negative when a component hedges the others. Standalone ratios $\operatorname{Var}(Y_j)/\operatorname{Var}(Y)$ need not sum to one. Under this convention, Euler contributions to portfolio standard deviation are $A_j/\operatorname{sd}(Y)$. They differ from variance allocations and from generic quantile allocations; an explicitly specified alternative must retain its own definition.

## Horizon and quantiles

If $v_t$ is an annualized conditional-volatility series observed daily, $\operatorname{sd}(v_t-v_{t-1})$ already measures daily shocks in annualized-volatility units. Annualizing that shock standard deviation by $\sqrt{B}$ and converting back to a one-day shock divides by the same $\sqrt{B}$; do not apply the second conversion to a quantity never annualized.

A moment-matched normal approximation for loss $L=-Y$ gives:

$$
\operatorname{VaR}_q(L)\approx-\operatorname{E}[Y]+\Phi^{-1}(q)\sqrt{\operatorname{Var}(Y)}
$$

A quadratic function of normal factors is generally not normal. This quantile is an approximation, not an exact consequence of the moment formulas. Fitted physical variance, risk-neutral pricing volatility and volatility-shock variance are different quantities.

## References

[Tasche, Capital Allocation: the Euler Principle](https://arxiv.org/abs/0708.2542), homogeneous risk allocation. Gaussian moments above are direct consequences of the stated local model and normal second/fourth moments; covariance closure follows by bilinearity, without assuming independence.
