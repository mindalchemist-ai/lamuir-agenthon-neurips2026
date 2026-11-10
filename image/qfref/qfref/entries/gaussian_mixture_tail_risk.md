# Gaussian mixtures and kernel-density tail risk

Use this document for VaR and expected shortfall of Gaussian mixtures or a univariate Gaussian kernel-density estimate (KDE). It complements normal/Student-t risk formulas; it does not define a portfolio strategy or a simulation design.

## Conventions

Map the task's loss sign, confidence level, bandwidth and estimation conventions before applying these identities. Explicit task definitions take precedence. Here L is loss, c in (0,1) is confidence, $q_{c}$ is loss VaR, and $\operatorname{ES}_{c}$ is upper-tail expected loss. $\Phi$ and $\phi$ denote the standard-normal CDF and density. Each Gaussian component j has probability $p_{j} \ge  0, \operatorname{mean} \mu _{j}$ and standard deviation $s_{j} > 0$; probabilities sum to one. A component's variance is $s_{j}^{2}$, not $s_{j}$.

## Mixture distribution

Standardized distance from a component mean to a loss threshold x:

$$
z_{j}(x) = (x - \mu _{j})/s_{j}
$$

Mixture cumulative probability, with a weighted sum of probabilities rather than quantiles:

$$
F_{L}(x) = \sum _{j} p_{j} \cdot  \Phi (z_{j}(x))
$$

Loss quantile defined by the mixture CDF:

$$
F_{L}(q_{c}) = c
$$

Mixture VaR is generally not the probability-weighted average of component VaRs. Positive component scales make the CDF continuous and strictly increasing.

The unnormalized upper-tail first moment of one component follows by substituting a standard normal and integrating $z\phi(z)$:

$$
M_{j}(q) = \mu _{j} \cdot  (1 - \Phi (z_{j}(q))) + s_{j} \cdot  \phi (z_{j}(q))
$$

Continuous-mixture expected shortfall, using the same quantile for every component:

$$
\operatorname{ES}_{c} = \sum _{j} p_{j} \cdot  M_{j}(q_{c}) / (1-c)
$$

This identity is an analytic check on tail quadrature, not a substitute when a task explicitly requires a particular numerical estimator. Integrating only to a finite upper bound omits tail mass and its first moment. With degenerate components or other atoms, conditional tail means and quantile-integrated ES can differ; the continuous formula above assumes all $s_{j} > 0$.

## Gaussian KDE as a mixture

For observations $x_{i}$ with nonnegative normalized weights $w_{i}$, and a common positive bandwidth h in loss units, each kernel is a Gaussian component with mean $x_{i}$ and standard deviation h.

KDE density:

$$
f_{h}(x) = \sum _{i} w_{i} \cdot  \phi ((x-x_{i})/h) / h
$$

KDE CDF:

$$
F_{h}(x) = \sum _{i} w_{i} \cdot  \Phi ((x-x_{i})/h)
$$

KDE upper-tail first moment:

$$
M_{h}(q) = \sum _{i} w_{i} \cdot  [x_{i}\cdot (1-\Phi ((q-x_{i})/h)) + h\cdot \phi ((q-x_{i})/h)]
$$

KDE expected shortfall at its own continuous quantile:

$$
\begin{gathered}
F_{h}(q_{c}) = c \\
\operatorname{ES}_{c} = M_{h}(q_{c})/(1-c)
\end{gathered}
$$

A smoothed distribution is distinct from the empirical sample. Averaging only observations above the KDE quantile is not the KDE tail expectation.

A bandwidth factor is dimensionless; h is not. For an unweighted, one-dimensional Gaussian KDE using the covariance-scaling convention, let $s_{\mathrm{sample}}$ be the sample standard deviation (divisor n-1) and b the selected factor.

Kernel standard deviation in the same units as the observations:

$$
h = b \cdot  s_{\mathrm{sample}}
$$

SciPy's unweighted univariate Silverman factor:

$$
b = (3\cdot n/4)^{-1/5}
$$

This is not interchangeable with every univariate rule called “Silverman's rule”. Weighted data change effective sample size and covariance conventions. A zero sample variance makes this KDE construction singular; an arbitrary positive bandwidth changes the model.

## Checks and scope

A one-component mixture reduces to the normal distribution. For continuous integrable losses, $\operatorname{ES}_{c} \ge  q_{c}$. Under a positive rescaling a and shift b0, both risk measures transform as a times the original plus b0. Mixture probabilities, not realized sample frequencies, define theoretical mixture risk. Fitting or sampling a mixture is separate from evaluating its distribution.

## Source and derivation

[SciPy gaussian_kde documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html), Notes and covariance attributes: Gaussian kernels, covariance scaling and Silverman-factor convention. The mixture CDF and tail-moment expressions above are derived directly by conditioning on a Gaussian component and integrating its density; the same distribution defines both the quantile and its tail moment.
