# Absorption ratio (Kritzman et al. 2011), equal risk contribution (risk parity), portfolio CVaR, volatility targeting

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting
$R = T x N$ matrix of asset returns (rows = dates, simple returns for portfolio aggregation), w = N weights, $\Sigma$ = covariance of R
over the stated window and frequency. Portfolio return per date $r_{p,t} = R_{t} w$ (constant weights rebalanced every period).

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| window | number of recent observations retained for estimation | observations |
| half-life | number of observation steps over which an exponential weight halves | observations |
| k (paper: n) | number of eigenvectors in the absorption ratio, fixed, from the task | count |
| $\alpha$ | VaR/CVaR confidence level; 95% is 0.95 (tail probability 1 - $\alpha$) | none |
| $A$ | periods per year for annualization (from the task's calendar) | $1/\mathrm{year}$ |
| $\sigma _{\mathrm{target}}$ | target annualized volatility; 10% is 0.10 | $1/\sqrt{\mathrm{year}}$ |

## Absorption ratio and standardized shift

$$
\mathrm{AR} = \sum _{i=1}^{k} \lambda _{i} / \sum _{j=1}^{N} \Sigma _{jj}
$$

The numerator is the sum of the top $k$ eigenvalues of $\Sigma$; the denominator is $\operatorname{trace}(\Sigma )$.

- $\lambda _{i}$ = variance of the i-th eigenportfolio, eigenvalues sorted DESCENDING (numpy eigh returns ascending).
- The paper uses the COVARIANCE matrix, k fixed as a fraction of N (not chosen by a variance threshold), and exponentially
  weighted variances over a rolling window. With a correlation matrix the denominator is N; use it only if the task says so.
- Exponential weights: $v_{s} = 0.5^{\mathrm{age}_{s} / \mathrm{half}_{\mathrm{life}}}$, age 0 = newest row, normalized to sum to one; weighted mean $m = \sum  v_{s} R_{s}$;
  $\Sigma  = \sum  v_{s} (R_{s} - m)'(R_{s} - m)$ (normalization by $\sum  v_{s}$; a bias correction rescales $\Sigma$ but leaves AR unchanged).
- Rolling: $\mathrm{AR}_{t}$ uses only rows up to t. Standardized shift (paper eq. 2):

$$
\mathrm{dAR}_{t} = ( \mathrm{MA}_{\mathrm{short}}(\mathrm{AR})_{t} - \mathrm{MA}_{\mathrm{long}}(\mathrm{AR})_{t} ) / \operatorname{sd}_{\mathrm{long}}(\mathrm{AR})_{t}
$$

  MA = simple moving average of the AR series; $\operatorname{sd}_{\mathrm{long}}$ = standard deviation of AR over the long window. A spike is $\mathrm{dAR} \ge  +1$.
  The first valid value needs about window + long-MA observations; leave earlier values empty (NaN), do not back-fill.

## Marchenko–Pastur noise spectrum: a separate diagnostic

Let $X$ have $n$ independent rows and $p$ independent, zero-mean Gaussian coordinates, each of variance $s^2$. For the uncentered sample covariance $C=X'X/n$, and aspect ratio $c=p/n$, the asymptotic positive spectral bulk has endpoints:

$$
\lambda_-=s^2(1-\sqrt c)^2,\qquad
\lambda_+=s^2(1+\sqrt c)^2.
$$

The upper edge is a white-noise benchmark, not a chosen number of retained factors or a finite-sample significance level. Correlation-matrix noise has population scale $s^2=1$ under this null; its finite-sample standardization still differs from dividing observations by known population standard deviations.

Demeaning Gaussian rows leaves $\nu=n-1$ independent Gaussian degrees of freedom in the centered scatter matrix. For divisor $d$ in the sample covariance, the corresponding asymptotic edge convention uses $c=p/\nu$ and multiplies both edges by $\nu/d$. In particular, $d=n-1$ has no such scale factor; $d=n$ has factor $(n-1)/n$. These are asymptotic bulk approximations, not exact finite-sample bounds, and the requested sample/divisor convention controls the diagnostic.

When $p>\nu$, the centered covariance has at least $p-\nu$ zero eigenvalues. This zero mass is separate from the lower edge of the positive bulk. Serial dependence, cross-sectional population correlations, heterogeneous scales or exponential weighting violate this simple Gaussian white-noise setup; substituting a heuristic effective sample size does not make it an exact law.

AR remains the fraction explained by its specified top eigenvalues. A noise edge does not change that definition or determine regime thresholds.

Source: [Bandeira, MIT Topics in Mathematics of Data Science, §1.2](https://ocw.mit.edu/courses/18-s096-topics-in-mathematics-of-data-science-fall-2015/5f0f7205d1cf274e80d77345a7edbf2a_MIT18_S096F15_TenLec.pdf), noise spectrum and aspect ratio. Centering rank and divisor conversions follow from the Gaussian scatter representation and scalar rescaling.

## Risk contributions and equal risk contribution (ERC)

$$
\begin{gathered}
\sigma _{p} = \sqrt{w' \Sigma  w};   \mathrm{MRC}_{i} = (\Sigma  w)_{i} / \sigma _{p};   \mathrm{RC}_{i} = w_{i} (\Sigma  w)_{i} / \sigma _{p};   \sum _{i} \mathrm{RC}_{i} = \sigma _{p} \\
\text{percent contribution} \mathrm{PRC}_{i} = \mathrm{RC}_{i} / \sigma _{p} = w_{i} (\Sigma  w)_{i} / (w' \Sigma  w)\quad (\text{variance-share form}; \text{sums to} 1)
\end{gathered}
$$

- ERC (Maillard-Roncalli-Teiletche 2010): long-only w with $\mathrm{RC}_{i} = \sigma _{p} / N$ for all $i, \sum  w = 1$. Risk budgeting: $\mathrm{RC}_{i} = b_{i} \sigma _{p}$.
- Solve: minimize $0.5 y' \Sigma  y - \sum _{i} b_{i} \ln (y_{i})$ over $y>0$. A sufficient condition for a finite unique minimizer is positive-definite $\Sigma$ and strictly positive budgets $b_i$ with $\sum_i b_i=1$. Normalize the solution as $w=y/\sum_i y_i$. Singular covariance matrices and zero budgets need separate existence/boundary analysis; strict convexity alone does not ensure a finite minimizer. The minimizer satisfies
  $y_{i} (\Sigma  y)_{i} = b_{i}$. Cyclical coordinate descent (Griveau-Billion, Richard, Roncalli 2013) repeats until y stops changing:

$$
c_{i} = \sum _{j \ne  i} \Sigma _{ij} y_{j};   y_{i} = ( -c_{i} + \sqrt{c_{i}^{2} + 4 \Sigma _{ii} b_{i}} ) / (2 \Sigma _{ii})
$$

  Newton (Spinu 2013) or a generic solver on the same objective also work. Check: $\max_i |\mathrm{PRC}_i-b_i|$ near machine precision.
- For positive marginal volatilities, inverse-volatility weights give ERC precisely when the correlation matrix has equal row sums, assuming positive portfolio variance. Equal pairwise correlations are sufficient, not necessary. In other cases inverse-volatility weights need not satisfy ERC.
- Scaling w (leverage) does not change PRC; ERC weights are defined up to scale before the budget constraint.

## Portfolio VaR / CVaR (expected shortfall)

Use loss-sign quantities $L=-r_p$. Their tail risk values need not be nonnegative if the relevant outcomes are gains; do not take absolute values or clamp them without an explicit reporting convention.
- Historical: losses $L_{t} = -r_{p,t}$, sorted descending $L_{1} \ge  L_{2} \ge  \ldots ; n$ obs, tail mass $n(1-\alpha)$.
  Simple: $k = \operatorname{floor}(n(1 - \alpha ))$ worst losses, $\operatorname{CVaR} = \operatorname{mean}(L_{1\ldots k}), \operatorname{VaR} = L_{k}$ or the $\alpha$-quantile of L (choose per task).
  The largest-k average requires $k\ge1$ and is a separate convention. For integrated-quantile ES with $0<n(1-\alpha)<1$, the upper-tail average equals the maximum observed loss; it is not an interpolated VaR fallback.
  Exact discrete (Acerbi-Tasche / Rockafellar-Uryasev): with $j = \operatorname{floor}(n(1-\alpha )), f = n(1-\alpha ) - j$,
  $\operatorname{CVaR} = [ \sum _{i\le j} L_{i} + f L_{j+1} ] / (n(1-\alpha ))$ = $\min_c\{c+\operatorname{mean}(\max(L-c,0))/(1-\alpha)\}$.
  The largest-$k$ average and integrated-quantile CVaR coincide when $n(1-\alpha)=k$ is an integer with $k\ge1$, including ties. That statement does not equate different VaR definitions. In this integer-tail case, $L_k$ matches NumPy's `method='higher'`; default linear interpolation can differ. For noninteger tail mass, explicitly select the order-statistic or interpolated quantile rule rather than assuming this correspondence.
- Parametric normal with portfolio mean $\mu _{p} = w'm$ and sd $\sigma _{p} = \sqrt{w'\Sigma  w}, z = \Phi ^{-1}(\alpha )$, $\phi$ = normal pdf:

$$
\operatorname{VaR} = -\mu _{p} + z \sigma _{p};     \operatorname{CVaR} = -\mu _{p} + \sigma _{p} \phi (z) / (1 - \alpha )
$$

  Horizon h periods (i.i.d.): $\mu_p h$ and $\sigma _{p} \sqrt{h}$. Many tasks set $\mu _{p} = 0$; follow the task.
- Student-t ($\nu>2$) with sd $\sigma _{p}$: $s = \sigma _{p} \sqrt{(\nu  - 2)/\nu}, q = t_{\nu}^{-1}(\alpha )$,

$$
\operatorname{VaR} = -\mu _{p} + s q;   \operatorname{CVaR} = -\mu _{p} + s \cdot  f_{\nu}(q) / (1 - \alpha ) \cdot  (\nu  + q^{2}) / (\nu  - 1)
$$

- Sign: if the task reports VaR/CVaR as negative returns, flip the sign; never mix ($\operatorname{CVaR} \ge  \operatorname{VaR}$ as losses).

## Volatility targeting
- Ex-ante: $\sigma _{\mathrm{ex}} = \sqrt{w' \Sigma  w} \cdot  \sqrt{A}$ if $\Sigma$ is per-period (or with an annualized $\Sigma$ directly).
  Scale $s_{t} = \sigma _{\mathrm{target}} / \sigma_{\mathrm{ex},t}$, weights $s_t w$; the rest ($1 - s_{t} \sum  w$) is cash. Apply a leverage cap if given.
- Realized: $\sigma _{\mathrm{real}}$ = $\operatorname{std}(r_p)\sqrt{A}$ (over the window, with ddof per task). Ex-ante uses the covariance; realized uses the portfolio
  return series. They differ (correlation changes, estimation window); use the one the task names.
- No look-ahead: the scale for period t uses data up to t-1 only. Annualize with $\sqrt{A}$, never with A.
- Variant (Moreira-Muir 2017): exposure proportional to 1 / (previous-period realized VARIANCE), not volatility.

## Common mistakes and limits
- Eigenvalues ascending; correlation instead of covariance; k chosen per date by variance threshold; window including date t+1.
- RC computed with variance ($w_i(\Sigma w)_i$) but labeled as volatility contributions; unnormalized weights; inverse-vol for ERC.
- Log returns aggregated cross-sectionally with weights (use simple returns); VaR sign flipped against the task.
- ERC with short positions has several solutions; the convex method above gives the long-only one.

## Sources
Kritzman, Li, Page & Rigobon (2011) "Principal Components as a Measure of Systemic Risk", J. Portfolio Management 37(4):112-126;
Maillard, Roncalli & Teiletche (2010) "The Properties of Equally Weighted Risk Contribution Portfolios", JPM 36(4):60-70;
Griveau-Billion, Richard & Roncalli (2013) arXiv:1311.4057; Spinu (2013) SSRN 2297383; Rockafellar & Uryasev (2000) J. Risk 2(3);
Acerbi & Tasche (2002) J. Banking & Finance 26(7):1487-1503; Moreira & Muir (2017) J. Finance 72(4):1611-1644.
