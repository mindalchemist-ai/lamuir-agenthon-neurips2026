# Cross-sectional signals, financed returns and factor-adjusted performance

Use this note to distinguish a return signal, the portfolio formed from it and the factor regression used to evaluate that portfolio. Explicit definitions determine the economic signal, information lag, cash benchmark and performance aggregation. Recent-return behavior does not name a unique signal.

## Signals are economic models

For one asset with simple returns $R_u$ over an admitted historical window $\mathcal W$, compounded return and arithmetic mean measure different things:

$$
s_{\mathrm{compound}}=\prod_{u\in\mathcal W}(1+R_u)-1,\qquad
s_{\mathrm{mean}}=\frac1{|\mathcal W|}\sum_{u\in\mathcal W}R_u
$$

A momentum signal assigns greater scores to stronger past performance; a reversal signal can deliberately reverse that direction. Risk-normalizing, excluding the most recent observations, or using factor residuals defines another signal. A ranking is not specified until the return measure, direction, window and admitted information are specified. A rolling statistic over a window that contains a missing value is missing for every date whose window covers it, so apply the stated missing-value treatment to returns before computing rolling signals, and check that every score being ranked is finite (reindexing a frame built on an integer index to a date index, for example, returns all NaN). A score vector that is all equal or all zero carries no ranking; selecting from it picks names by column order. Rank only from the first date on which the full lookback is available and trading is allowed. In pandas use `rolling(w, min_periods=w)`, so a partial window gives NaN, and drop those dates; `min_periods=1` followed by `fillna(0)` turns a warm-up into spurious signal days.

For asset scores $s_i$ across an eligible universe $\mathcal U$, standardization uses that date's cross-sectional mean $\bar s$ and its chosen standard-deviation divisor:

$$
z_i=\frac{s_i-\bar s}{\operatorname{sd}_{\mathcal U}(s)}
$$

Positive affine transformations preserve the ranking when dispersion is nonzero; a negative transformation reverses it. Zero dispersion gives no standardized ranking signal. Missing-data policy changes the universe and possibly the ranking; imputing a missing return as zero asserts an economic return rather than merely filling a data slot.

## Portfolio exposure and financing

Let $w_i$ be signed risky fractions and $r_f$ the period's cash return, with symmetric financing. The funded portfolio return before costs is:

$$
R_p=r_f+\sum_i w_i(R_i-r_f)
$$

A zero-net-investment long-short basket and a fully funded account with that basket have different cash benchmarks. Gross exposure is $\sum_i|w_i|$; net exposure is $\sum_iw_i$. A gross cap and a per-position cap impose different restrictions. With a proportional charge $c$ on each unit of traded notional, cost is $c\sum_i|\Delta w_i|$. A reported one-way turnover statistic may be $\tfrac12\sum_i|\Delta w_i|$; that reporting choice does not halve the economic cost. If a rate is explicitly quoted per unit of the one-way statistic, apply that separately defined rate to that statistic.

Trades compare target weights with pre-trade drifted holdings under the chosen rebalance convention. Subtracting the last target weights is not generally the same quantity. A close-derived signal cannot earn returns before it was observable. Position formation, risk estimation and return measurement must share a consistent information timeline.

## Alpha and residual beta

For admitted portfolio returns $y_t$ and matching factor vector $f_t$, an intercept regression decomposes realized return as:

$$
y_t=\alpha+\beta'f_t+e_t
$$

The fitted $\beta$ describes the portfolio's exposure; it need not be zero because the portfolio is called hedged or residual-alpha. In an unpenalized same-sample OLS fit with an intercept and full rank, $\sum_te_t=0$ and $\sum_tf_te_t=0$. Regressing those same residuals on the same factors therefore gives zero slopes, a different diagnostic from reporting the original portfolio's fitted betas. Out-of-sample residuals need not be orthogonal.

If $A$ is observations per year and $s_e$ is residual standard deviation under its specified divisor, the conventional annualized intercept and residual volatility are:

$$
\alpha_{\mathrm{ann}}=A\alpha,\qquad
\mathrm{TE}_{\mathrm{ann}}=\sqrt A\,s_e
$$

The corresponding alpha-to-residual-risk ratio is:

$$
\mathrm{IR}=\frac{\alpha_{\mathrm{ann}}}{\mathrm{TE}_{\mathrm{ann}}}
=\sqrt A\frac\alpha{s_e}
$$

This is not the portfolio Sharpe ratio unless its numerator and risk denominator coincide. Intercept annualization is arithmetic, not compounded growth. Square-root annualization assumes an appropriate uncorrelated-return approximation. Residual sample standard deviation and regression residual standard error use different degrees-of-freedom conventions.

Whether $y$ is total return, excess return or a self-financing spread matters. An already excess market factor is not reduced by the cash return again. Transaction costs belong in the return series being evaluated when net performance is requested; changing the regression's covariance estimator changes inference, not its OLS coefficients.

## References and scope

[Sharpe (1994), The Sharpe Ratio](https://web.stanford.edu/~wfsharpe/art/sr/SR.htm), differential-return ratios and time aggregation. Regression, financing and ranking identities above are direct derivations under their stated definitions. This note does not choose an unspecified momentum/reversal rule or guarantee that a named strategy is factor-neutral.
