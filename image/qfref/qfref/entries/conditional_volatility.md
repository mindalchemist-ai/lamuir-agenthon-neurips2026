# Conditional volatility: GARCH forecasts and dynamic correlations

This note defines changing return variances and covariances for risk forecasts. It distinguishes fitted variance, future variance and long-run variance; it does not define trading signals or regulatory capital rules.

**Fitting GARCH with arch:** use the two-case recipe at the top of the garch_fitting entry: percent returns converted back where the task leaves units open, a reparameterized native-unit MLE where the task fixes native units. Do not silence warnings, and check that the estimates moved away from arch's starting values.

## Shared Foundations

Map notation by economic meaning and units. Explicit task conventions determine return scaling, mean model, initialization, forecast horizon and likelihood normalization. Identify conflicting conventions rather than silently changing them.

Here t indexes observations, $r_{t}$ is a return, $m_{t}$ its conditional mean, and $F_{t}$ the information available through t. Innovations have zero conditional mean. All covariance quantities use the same observation frequency.

## Univariate conditional variance

The innovation removes the specified mean, which may be zero.

$$
\epsilon _{t} = r_{t} - m_{t}
$$

GARCH(1,1) specifies variance known before observing $r_{t}$. Here $\omega  > 0, \alpha  \ge  0$ and $\beta  \ge  0; z_{t}$ has conditional mean zero and variance one.

$$
\begin{gathered}
h_{t} = \omega  + \alpha \cdot \epsilon _{t-1}^{2} + \beta \cdot h_{t-1} \\
\epsilon _{t} = \sqrt{h_{t}}\cdot z_{t}
\end{gathered}
$$

Gaussian conditional negative log likelihood, for a fixed initialization and included sample of N observations, is:

$$
\mathrm{NLL} = (1/2)\cdot \sum _{t} [\ln (2\cdot \pi ) + \ln (h_{t}) + \epsilon _{t}^{2}/h_{t}]
$$

With non-Gaussian innovations this is a Gaussian quasi-likelihood, not their exact likelihood. Removing constants does not change an optimizer but changes the reported objective. Initialization and sample inclusion also matter.

The finite unconditional variance, when $\alpha  + \beta  < 1$ and the model assumptions hold, is:

$$
\bar{h} = \omega /(1-\alpha -\beta )
$$

This finite-second-moment condition is not a necessary condition for every form of strict stationarity. At $\alpha  + \beta  = 1$ the formula above is unavailable.

## Scale and horizon

Multiplying returns and their mean by a positive factor c changes dimensional parameters as follows; $\alpha$ and $\beta$ are unchanged.

$$
\begin{gathered}
\epsilon _{\mathrm{scaled}} = c\cdot \epsilon \\
h_{\mathrm{scaled}} = c^{2}\cdot h \\
\omega _{\mathrm{scaled}} = c^{2}\cdot \omega
\end{gathered}
$$

Thus percent-return variance is converted to decimal-return variance by dividing by $100^2$; standard deviation is divided by 100. Under the same transformed initialization the Gaussian NLL changes by $N\cdot \ln (c)$. Numerical fitting tolerances need not be invariant to scaling.

The next-observation variance forecast includes the latest observed innovation; it is not the final in-sample $h_{t}$.

$$
h_{t+1\vert t} = \omega  + \alpha \cdot \epsilon _{t}^{2} + \beta \cdot h_{t}
$$

For $k \ge  2$, conditional expectations give the multi-step forecast:

$$
h_{t+k\vert t} = \omega  + (\alpha +\beta )\cdot h_{t+k-1\vert t}
$$

For $\alpha  + \beta  < 1$ its equivalent closed form is:

$$
h_{t+k\vert t} = \bar{h} + (\alpha +\beta )^{k-1}\cdot (h_{t+1\vert t}-\bar{h})
$$

With martingale-difference innovations and finite second moments, the variance of the cumulative innovation over H observations is:

$$
\operatorname{Var}(\sum _{k=1}^{H} \epsilon _{t+k} \vert  F_{t}) = \sum _{k=1}^{H} h_{t+k\vert t}
$$

It equals H times the one-step forecast only under an additional flat-variance assumption. Annualizing a daily standard deviation by $\sqrt{A}$, where A is observations per year, is a reporting convention; it does not replace the horizon recursion. A nontrivial mean model can add forecast uncertainty to cumulative returns.

## Dynamic conditional correlation

Use DCC for a vector of innovations with separate univariate conditional variances. Marginal standardization removes scale, not cross-sectional dependence. $D_{t}$ is diagonal with positive standard deviations.

$$
\begin{gathered}
D_{t} = \operatorname{diag}(\sqrt{h_{1,t}}, \ldots , \sqrt{h_{n,t}}) \\
z_{t} = D_{t}^{-1}\cdot \epsilon _{t}
\end{gathered}
$$

The scalar DCC recursion uses nonnegative a,b with $a+b<1$, a positive-definite target $\bar{Q}$, and positive-definite initial Q. A zero-mean standardized second-moment target and a demeaned sample covariance are distinct finite-sample conventions.

$$
Q_{t} = (1-a-b)\cdot \bar{Q} + a\cdot z_{t-1}\cdot z_{t-1}' + b\cdot Q_{t-1}
$$

The correlation normalization makes each diagonal entry one. $Q_{t}$ itself is not generally a correlation matrix.

$$
R_{i,j,t} = Q_{i,j,t}/\sqrt{Q_{i,i,t}\cdot Q_{j,j,t}}
$$

The conditional covariance restores each asset's scale.

$$
H_{t} = D_{t}\cdot R_{t}\cdot D_{t}
$$

The correlation part of the Gaussian log likelihood, after fixing the univariate fits, is:

$$
\mathrm{logL}_{\mathrm{corr}} = -(1/2)\cdot \sum _{t} [\ln (\det (R_{t})) + z_{t}'\cdot R_{t}^{-1}\cdot z_{t} - z_{t}'\cdot z_{t}]
$$

Omitting the last term leaves the same correlation estimates but a different reported log likelihood. The full multivariate likelihood also includes marginal variance and Gaussian normalization terms.

## Checks and Scope

Positive-definite Q and positive diagonal h imply positive-definite H; R must be symmetric with unit diagonal. For portfolio weights w, conditional variance is w'*H*w, not a weighted average of marginal variances. With $a=b=0$, the correlation is the normalization of $\bar{Q}$.

Empirical standardized residual rows can still be correlated. Resampling complete rows preserves their empirical contemporaneous dependence; multiplying those already correlated rows by another correlation factor generally changes it. Whitening and subsequent recoloring is a different construction. Serial block resampling and independent resampling also represent different dependence assumptions.

Forecast origin, variance estimation window and parameter estimation window are separate concepts. A lagged position does not remove future information from full-sample fitted parameters. A one-step risk estimate is not automatically a risk-neutral option volatility or a regulatory capital formula.

## Constrained likelihood fitting and numerical diagnostics

Separate the economic parameter domain from the optimizer's coordinate system. Box bounds on two persistence parameters do not enforce a bound on their sum. One strictly interior parameterization, applicable to either a nonnegative GARCH pair or a scalar DCC pair with sum below one, is:

$$
p_1=\frac{e^{u_1}}{1+e^{u_1}+e^{u_2}},\qquad
p_2=\frac{e^{u_2}}{1+e^{u_1}+e^{u_2}}.
$$

Evaluate the denominator with log-sum-exp. In exact real arithmetic, finite coordinates give strictly positive parameters and positive slack; floating-point exponentials can underflow or round the sum to one. After mapping, explicitly verify finite values, positive intercept/variances and the requested strict persistence inequality. Reject an infeasible objective evaluation or use documented bounded coordinates; silently clipping the result changes the parameterization. exact zero coefficients or unit persistence are boundary cases outside this interior map. Do not force a stationary interior model when another domain is explicitly requested. For a positive variance intercept, a positive fixed reference variance $h_{\mathrm{ref}}$ allows $\omega=h_{\mathrm{ref}}e^v$; changing parameter coordinates is different from rescaling the observed returns. Preserve the specified input units, likelihood initialization, sample and allowed optimization method.

Finite-difference gradients are sensitive to coordinate scale. With a fixed mean and a parameter-independent seed $h_0$, useful analytic derivatives follow the same recursion as the variance:

$$
\partial_\omega h_t=1+\beta\partial_\omega h_{t-1},\qquad
\partial_\alpha h_t=\epsilon_{t-1}^2+\beta\partial_\alpha h_{t-1},\qquad
\partial_\beta h_t=h_{t-1}+\beta\partial_\beta h_{t-1}.
$$

Their initial values are zero only under that fixed-seed assumption. A seed defined by long-run variance, or a fitted mean affecting innovations, needs the corresponding derivatives too. For the Gaussian NLL with fixed innovations, the gradient is:

$$
\partial_\theta\mathrm{NLL}
=\frac12\sum_t\left(\frac1{h_t}-\frac{\epsilon_t^2}{h_t^2}\right)\partial_\theta h_t.
$$

For a positive-definite DCC correlation matrix $R_t=L_tL_t'$ with lower triangular Cholesky factor $L_t$, solve $L_t y_t=z_t$. Then:

$$
\log\det R_t=2\sum_i\log(L_{t,ii}),\qquad
z_t'R_t^{-1}z_t=y_t'y_t.
$$

A linear solve avoids forming the inverse. Cholesky failure can reveal infeasible parameters or numerical loss of definiteness; an arbitrary diagonal adjustment changes the fitted objective. Nearly singular feasible matrices also need numerical scrutiny.

A fitted model needs finite likelihood, feasible parameters, positive filtered variances and a documented termination reason. Compare the objective at the returned parameters and the start, the gradient where meaningful, and small feasible perturbations. Zero optimizer iterations can indicate a genuine optimum or a scale/stopping problem; it is not by itself proof of either. Multiple admissible starts can expose local optima when allowed, but do not establish a global optimum. Rescaling returns, clipping parameters and changing initialization are different changes and must not be substituted silently for diagnosis.

Sources: [arch estimation results](https://arch.readthedocs.io/en/stable/univariate/generated/arch.univariate.base.ARCHModelResult.html) exposes convergence, optimization result and scale; [arch model settings](https://arch.readthedocs.io/en/stable/univariate/introduction.html) describes mean and rescaling choices. The derivative and Cholesky identities follow from the variance recursion and matrix factorization.

## References

[arch documentation: forecasting](https://arch.readthedocs.io/en/latest/univariate/forecasting.html), conditional GARCH forecast recursions. Scale, cumulative-variance and likelihood-shift identities above follow directly from the stated model.

[Engle, Dynamic Conditional Correlation (2002), author manuscript](https://archive.nyu.edu/bitstream/2451/26482/2/02-38.pdf), Sections III–IV, correlation recursion and likelihood decomposition. Definiteness and scale checks are direct matrix identities.
