# Credit portfolio: one-factor Gaussian copula / Vasicek ASRF, Basel IRB, Euler risk contributions

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

**Before writing the stressed default probability (VaR, granularity adjustment, any formula with a quantile of the factor):** the number fed to the normal quantile is either the confidence level q (for example 0.999) or the tail probability 1 − q (0.001), and which one depends on the sign in front of the factor term:

| Formula as written | Quantile to use | Stressed factor |
|---|---|---|
| `Phi((Phi^-1(PD) + sqrt(rho) * Phi^-1(x)) / sqrt(1 - rho))` (high factor is bad) | x = q | `Phi^-1(q)`, a large positive number |
| `Phi((Phi^-1(PD) - sqrt(rho) * z) / sqrt(1 - rho))` with z the factor (low factor is bad) | z = `Phi^-1(1 - q)` | a large negative number |

A task or paper that writes the factor quantile with a symbol such as alpha may mean either; read the sign in its formula and check the result rather than the symbol name. The same quantile goes into every formula that evaluates the worst-case factor (conditional PD, its derivatives in a granularity adjustment, the conditional variance).

```python
from scipy.stats import norm
def stressed_pd(pd_, rho, q):                      # high-factor-is-bad form, q = confidence level
    return norm.cdf((norm.ppf(pd_) + np.sqrt(rho) * norm.ppf(q)) / np.sqrt(1 - rho))
levels = np.array([0.9, 0.975, 0.995])
p = stressed_pd(0.01, 0.12, levels)
assert (p > 0.01).all() and (np.diff(p) > 0).all()   # stressed PD above PD, and VaR rises with the confidence level
```

## Model and assumptions
- Obligor i has latent asset return $A_{i} = \sqrt{\rho _{i}} Z + \sqrt{1 - \rho _{i}} \mathrm{eps}_{i}$, with Z (systematic factor) and $\mathrm{eps}_{i}$ i.i.d. N(0, 1).
  Default over the horizon iff $A_{i} < c_{i} = \Phi ^{-1}(\mathrm{PD}_{i})$. Here LOW Z is the bad state. $\rho _{i}$ is the ASSET correlation, not the default correlation.
- Conditional on $Z = z$, defaults are independent with

$$
p_{i}(z) = \Phi ( (\Phi ^{-1}(\mathrm{PD}_{i}) - \sqrt{\rho _{i}} z) / \sqrt{1 - \rho _{i}} )
$$

  Some texts write $+ \sqrt{\rho} z$ with HIGH z bad (Z replaced by -Z); then the stressed factor is $z = \Phi ^{-1}(q)$ instead of $\Phi^{-1}(1-q)$. Same numbers.
- Loss $L = \sum _{i} \mathrm{EAD}_{i} \cdot  \mathrm{LGD}_{i} \cdot  1\{\mathrm{default}_{i}\}$; EAD, LGD deterministic unless the task says otherwise. Horizon is usually one year.
- ASRF (asymptotic single risk factor): infinitely many small exposures, so $L \to  \operatorname{E}[L \vert  Z] = \sum _{i} \mathrm{EAD}_{i} \mathrm{LGD}_{i} p_{i}(Z)$, a monotone function of Z.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $\mathrm{PD}_{i}$ | unconditional default probability over the horizon (1% is 0.01) | none |
| $\rho _{i} (R)$ | asset correlation parameter: $\operatorname{Corr}(A_i,Z)=\sqrt{\rho_i}$ and $\operatorname{Corr}(A_i,A_j)=\sqrt{\rho_i\rho_j}$ for distinct names, $0 < \rho  < 1$ | none |
| $\mathrm{EAD}_{i}, \mathrm{LGD}_{i}$ | exposure at default; loss given default as a fraction of EAD | currency, none |
| $q$ | confidence level (99.9% is 0.999) | none |
| $M$ | effective maturity for the Basel maturity adjustment | years |

## Vasicek large homogeneous pool (same PD, rho; default fraction L in [0, 1])

$$
\operatorname{P}(L \le  x) = \Phi ( (\sqrt{1 - \rho} \Phi ^{-1}(x) - \Phi ^{-1}(\mathrm{PD})) / \sqrt{\rho} )
$$

$$
\operatorname{VaR}_{q}(L) = \Phi ( (\Phi ^{-1}(\mathrm{PD}) + \sqrt{\rho} \cdot  \Phi ^{-1}(q)) / \sqrt{1 - \rho} )
$$

$q$ is the confidence level. A positive normal quantile by itself does not imply that the loss quantile exceeds the mean. Compare the displayed quantile with PD under the specified parameters. The stressed factor in the low-factor-is-bad convention is $\Phi^{-1}(1-q)$.

$$
\operatorname{E}[L] = \mathrm{PD}
$$

$$
\operatorname{Var}[L] = \mathrm{Phi2}(c, c; \rho ) - \mathrm{PD}^{2}
$$

Default correlation:

$$
(\mathrm{Phi2}(c, c; \rho ) - \mathrm{PD}^{2}) / (\mathrm{PD} (1 - \mathrm{PD}))
$$

$$
\operatorname{ES}_{q}(L) = \mathrm{Phi2}( \Phi ^{-1}(\mathrm{PD}), \Phi ^{-1}(1 - q); \sqrt{\rho} ) / (1 - q)
$$

$\mathrm{Phi2}(a, b; r)$ is the bivariate normal CDF with correlation $r$. Loss in currency: multiply by $\mathrm{EAD}_{\mathrm{total}}$ * LGD. Heterogeneous ASRF: $\operatorname{VaR}_{q} = \sum _{i} \mathrm{EAD}_{i} \mathrm{LGD}_{i} \Phi ( (\Phi ^{-1}(\mathrm{PD}_{i}) + \sqrt{\rho _{i}} \cdot  \Phi ^{-1}(q)) / \sqrt{1 - \rho _{i}} )$ (same q, same sign), $\operatorname{ES}_{q} = \sum _{i} \mathrm{EAD}_{i} \mathrm{LGD}_{i} \mathrm{Phi2}(c_{i}, \Phi ^{-1}(1 - q); \sqrt{\rho _{i}}) / (1 - q)$.
Finite homogeneous pool of n names: $\operatorname{P}(D = k) = \int  C(n, k) p(z)^{k} (1 - p(z))^{n - k} \phi (z) \mathrm{d}z$ (quadrature over z).

## Basel II IRB (BCBS 2005 explanatory note; ASRF at q = 0.999, regulatory constants below)
Capital per unit EAD, UL only:

$$
K = [ \mathrm{LGD} \cdot  \Phi ( (\Phi ^{-1}(\mathrm{PD}) + \sqrt{R} \Phi ^{-1}(0.999)) / \sqrt{1 - R} ) - \mathrm{PD} \cdot  \mathrm{LGD} ] \cdot  \mathrm{MA}
$$

Corporate/bank/sovereign maturity adjustment ($\mathrm{MA} = 1$ at $M = 1$):

$$
\mathrm{MA} = (1 + (M - 2.5) b) / (1 - 1.5 b)
$$

$$
b = (0.11852 - 0.05478 \ln (\mathrm{PD}))^{2}
$$

$$
\mathrm{RWA} = 12.5 \cdot  K \cdot  \mathrm{EAD}
$$

Corporate correlation:

$$
R = 0.12 w + 0.24 (1 - w)
$$

$$
w = (1 - \exp (-50 \mathrm{PD})) / (1 - \exp (-50))
$$

For SMEs, subtract $0.04 (1 - (S - 5)/45)$, where $S$ is sales in EUR mn clipped to $[5, 50]$. Retail uses no MA: residential mortgage $R = 0.15$, qualifying revolving $R = 0.04$; other retail uses the corporate expression with 0.03, 0.16 and 35 in place of 0.12, 0.24 and 50. Variant without MA: set $\mathrm{MA} = 1$. The Basel II Annex 5 illustrative risk weights are reproduced with $\mathrm{RWA} = 12.5 K \mathrm{EAD}$ and no extra scaling factor; PD floors or scaling only if the task states them.

## Monte Carlo of correlated defaults
Per scenario s: draw $Z_{s}$, $\mathrm{eps}_{i,s}\sim N(0,1)$; $D_{i,s} = 1\{ \sqrt{\rho _{i}} Z_{s} + \sqrt{1 - \rho _{i}} \mathrm{eps}_{i,s} < \Phi ^{-1}(\mathrm{PD}_{i}) \}$; $L_{i,s} = \mathrm{EAD}_{i} \mathrm{LGD}_{i} D_{i,s}$, $L_{s} = \sum _{i} L_{i,s}$.
Homogeneous shortcut: draw $Z_{s}$, then $D_{s} \sim \operatorname{Binomial}(n, p(Z_{s}))$. Keep the per-obligor losses if contributions are needed.
- $\operatorname{VaR}_{q}$ = empirical q-quantile of $L_{s}$ (state the convention: order statistic `L_(ceil(N q))` ascending, or interpolated).
- Integrated-quantile ES uses exactly upper-tail mass $1-q$, including fractional mass at the cutoff; a largest-k average or a conditional tail mean is a separate convention. Follow an explicit task definition and label it accordingly.
- $\mathrm{EL} = \sum _{i} \mathrm{EAD}_{i} \mathrm{LGD}_{i} \mathrm{PD}_{i}$. Economic capital (unexpected loss) = $\operatorname{VaR}_q-\mathrm{EL}$ (or $\operatorname{ES}_q-\mathrm{EL}$). Some texts call sd(L) "unexpected loss"; follow the task.

## Several correlated systematic factors (for example sector factors)
When each obligor loads on one of k systematic factors with correlation matrix R (k x k), `C = np.linalg.cholesky(R)` is
lower triangular with `C @ C.T = R`. With one row of independent standard normals per scenario, `Z` of shape
(n_scenarios, k), the correlated factors are `F = Z @ C.T` (each row is C z). `Z @ C` has covariance `C.T @ C`, which is
not R; check the sample correlation and unit variances of F before using it. Obligor i in factor s(i) then has
$A_{i} = \sqrt{\rho _{i}} F_{s(i)} + \sqrt{1 - \rho _{i}} \mathrm{eps}_{i}$. In a Student-t copula one mixing draw
$W \sim \chi^2_{\nu}/\nu$ per scenario divides both parts of every obligor in that scenario, and the default threshold is
$t_{\nu}^{-1}(\mathrm{PD}_{i})$.

An (n_scenarios, n_obligors) float64 array takes 8 bytes per cell (0.8 GB for 1e5 x 1e3), and one vectorised step
often holds several such arrays. Simulate in consecutive scenario batches and keep the per-scenario portfolio loss plus
only the per-obligor quantities needed later. Drawing the small arrays for all scenarios first and then the large
idiosyncratic array batch by batch from the same generator reproduces the unbatched stream when the unbatched code drew
them in that order (arrays fill row by row); otherwise results differ by Monte Carlo noise only.

Reduce what is stored, not its precision: keep losses and running sums in float64. float32 keeps about seven significant digits (its spacing near 1e8 is 8), so a portfolio total passed through float32 can differ between two output files by several units. Batching keeps the draws only if each batch takes the next rows of the same arrays: a loop that draws a factor and then names for every batch, after a whole run that drew all factors first, gives different numbers; check batched against unbatched on a small case before the full run.

```python
def factor_losses(rng, C, sector, rho, threshold, loss_given_default, n_scenarios, batch=10_000):
    F = rng.standard_normal((n_scenarios, C.shape[0])) @ C.T            # correlated factors, rows are scenarios
    assert np.allclose(np.corrcoef(F, rowvar=False), C @ C.T, atol=0.05)
    losses = np.empty(n_scenarios)
    for lo in range(0, n_scenarios, batch):
        hi = min(lo + batch, n_scenarios)
        eps = rng.standard_normal((hi - lo, len(rho)))
        A = np.sqrt(rho) * F[lo:hi, sector] + np.sqrt(1 - rho) * eps
        losses[lo:hi] = (A < threshold) @ loss_given_default            # per-scenario portfolio loss
    return losses
```

## Risk contributions (Euler allocation; risk measure homogeneous of degree 1 in exposures w_i)

$$
\mathrm{RC}_{i} = w_{i} \cdot  \mathrm{d}R/\mathrm{d}w_{i}
$$

$$
\sum _{i} \mathrm{RC}_{i} = R(L)
$$

For a continuous loss distribution with no atom at its quantile and suitable differentiability, ES components are tail conditional means. For losses with atoms, select only the needed probability at the boundary.

Let $v=\inf\{x:F_L(x)\ge q\}$ and $a=1-q$. The fraction of the boundary atom included in the upper tail is:

$$
\eta=\frac{a-\Pr(L>v)}{\Pr(L=v)}
$$

This definition applies when the denominator is positive; otherwise the boundary term vanishes. The component allocation, using the same boundary fraction for every component, is:

$$
\mathrm{RC}_i^{\mathrm{ES}}=\frac{\mathrm{E}[L_i\mathbf{1}_{L>v}]+\eta\,\mathrm{E}[L_i\mathbf{1}_{L=v}]}{a}
$$

The allocations sum to integrated-quantile ES because scenario losses sum across components. In an equally weighted sample, allocate fractional mass at the cutoff rather than taking every tied scenario. Averaging all losses above or equal to VaR is a different quantity when excess probability enters through ties. Tail mass below one scenario gives the largest scenario loss; component selection at a tie need not be unique, although total ES is.

For a continuous distribution, under regularity, VaR Euler contributions can be expressed by conditional component losses at the quantile. A finite discrete portfolio need not have a differentiable VaR. A window average is a smoothing approximation; rescaling it to match total VaR is a normalization, not proof of correct marginal allocation.

When the total risk measure is estimated by Monte Carlo, compute the contributions from the same simulated scenarios (tail conditional means), so that they add up to the simulated total; check that their sum divided by the total is 1 within simulation noise. The ASRF formulas below are for the analytic one-factor model and do not add up to a simulated portfolio total.

ASRF allocations:

$$
\mathrm{RC}_{i}^{\operatorname{VaR}} = \mathrm{EAD}_{i} \mathrm{LGD}_{i} p_{i}(\Phi ^{-1}(1 - q))
$$

$$
\mathrm{RC}_{i}^{\operatorname{ES}} = \mathrm{EAD}_{i} \mathrm{LGD}_{i} \mathrm{Phi2}(c_{i}, \Phi ^{-1}(1 - q); \sqrt{\rho _{i}}) / (1 - q)
$$

Marginal ES of obligor i = dES$/\mathrm{dEAD}_{i} = \mathrm{RC}_{i}^{\operatorname{ES}} / \mathrm{EAD}_{i}$. Capital contributions net of EL: $\mathrm{RC}_{i}$ - $\mathrm{EAD}_{i}$ $\mathrm{LGD}_{i}$ $\mathrm{PD}_{i}$.

## Applicability and known limits
- ASRF/Basel ignore name concentration (fix: MC) and sector concentration (single factor). Gaussian copula has no tail dependence.
- Common mistakes: using $+ \sqrt{\rho} \Phi ^{-1}(1 - q)$ (for $\mathrm{PD}<0.5$ and $q>0.5$, gives a value below EL); using default correlation as $\rho$; forgetting $- \mathrm{PD}\cdot \mathrm{LGD}$ in Basel K; applying MA to retail.
- MC tail estimates at q near 1 need many scenarios (only N (1 - q) tail points); report the seed and N. VaR is not subadditive; ES is.

Choose one loss convention and confidence level for each calculation. Use that same convention for total loss, components, units and diagnostics; a sign conversion changes all of them together.

## Sources
Vasicek (2002) The distribution of loan portfolio value, Risk 15(12):160-162; Gordy (2003) J. Financial Intermediation 12(3):199-232;
Gordy & Lutkebohmert (2013) Int. J. Central Banking 9(3):33-72; Emmer & Tasche (2005) J. Risk 7(2):85-101;
Tasche (2008) Capital allocation to business units and sub-portfolios: the Euler principle, arXiv:0708.2542;
BCBS (2005) An Explanatory Note on the Basel II IRB Risk Weight Functions; BCBS (2006) Basel II comprehensive version, Annex 5.
