# One-period VaR and Expected Shortfall: historical, normal, Student-t, Cornish-Fisher; scaling; Kupiec and Christoffersen backtests

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting and conventions
- X = one-period return (or P&L) of the position, $L = -X$ the loss. Confidence level c and tail probability $\alpha  = 1 - c$:
  "99% VaR" means $c = 0.99$; "VaR at the 1% level" usually means $\alpha  = 0.01$. Read which one the task gives.
- Loss-positive convention (default here): $\operatorname{VaR}_{c} = -q_{\alpha}(X)$, a positive number for a loss.
  Return-quantile convention: report $q_{\alpha}$(X) itself (negative). Money VaR = position value * return VaR.
- $\operatorname{ES}_{c}$ (also CVaR, expected tail loss$) = \operatorname{E}[L \vert  L \ge  \operatorname{VaR}_{c}] = (1/\alpha ) \cdot  \int _{0}^{\alpha} \operatorname{VaR}_{1-u} \mathrm{d}u ($continuous X). $\operatorname{ES} \ge  \operatorname{VaR}$.

## Inputs and units
| symbol | meaning | units |
|---|---|---|
| $\mu$, $\sigma$ | mean and standard deviation of X over one period (2% is `0.02`) | per period |
| $\nu$ | Student-t degrees of freedom | none |
| $S, K$ | skewness and EXCESS kurtosis of X (excess = raw kurtosis - 3) | none |
| $h$ | horizon in periods for scaling | periods |
| $T, x$ | backtest days and number of exceptions | count |

## Formulas
Historical (sample $x_{1}$..$x_{n}$ of returns, sorted $x_{1} \le  \ldots  \le  x_{n}$):

$$
\operatorname{VaR} = -x_{k}
$$

$$
k = \operatorname{ceil}(n \cdot  \alpha )
$$

$$
\operatorname{ES} = -(1/m) \cdot  \sum _{j=1}^{m} x_{j}
$$

m is the number of worst returns averaged for ES, and it is a choice that must be stated. With n returns and tail probability alpha:
- m = k = ceil(n*alpha): the same scenarios that set the VaR order statistic, so ES is the mean of the k worst returns and always contains the VaR scenario. This is the inclusive mean of section 3 in var_es_return_series when there are no ties at VaR.
- m = floor(n*alpha): the count some texts and tools use. When n*alpha is not a whole number it leaves out the VaR scenario, so it is at least as large as the k-worst mean.
- fractional: average the floor(n*alpha) worst returns, add the fraction n*alpha - floor(n*alpha) of the next one, and divide by n*alpha. This is the tail_mean rule (integrated quantile, Acerbi and Tasche 2002).
- all returns at or below -VaR: the inclusive tail conditional expectation. It equals the k-worst mean unless returns tie at VaR.
When n*alpha is a whole number, the first three coincide. They differ only when it is not, for example n = 250 and alpha = 0.01, where n*alpha = 2.5, k = 3 and floor = 2.
Choose by the task text. A formula or a named rule decides. "Average of the losses at or beyond VaR" includes the VaR scenario, so use the same k as the VaR. "Coherent", "integrated quantile" or "average VaR over the tail" means the fractional rule. If the text names no rule, use m = k so that VaR and ES come from the same order statistics. Print n*alpha, k and m next to the result.

$\operatorname{Normal}, z_{c} = \Phi ^{-1}(c)$, $\phi$ = standard normal pdf:

$$
\begin{gathered}
\operatorname{VaR} = -\mu  + \sigma  z_{c}                         \mathrm{zero}-\operatorname{mean} \mathrm{version}: \operatorname{VaR} = \sigma  z_{c} \\
\operatorname{ES}  = -\mu  + \sigma  \phi (z_{c}) / \alpha
\end{gathered}
$$

Student-t, $X=\mu+sT_\nu$ with $T_{\nu}$ standard $t, q = t_{\nu}^{-1}(c) > 0$, $f_{\nu}$ = standard t pdf:
If $\sigma$ is the standard deviation of $X$ (unit-variance t; needs $\nu  > 2$):

$$
s = \sigma  \cdot  \sqrt{(\nu  - 2)/\nu}
$$

If $\sigma$ is the t scale parameter (e.g. a fitted loc/scale t):

$$
s = \sigma
$$

$$
\operatorname{VaR} = -\mu  + s q
$$

For $\nu  > 1$:

$$
\operatorname{ES} = -\mu  + s \cdot  f_{\nu}(q) \cdot  (\nu  + q^{2}) / ((\nu  - 1) \cdot  \alpha )
$$

Cornish-Fisher (modified$) \operatorname{VaR}, z = \Phi ^{-1}(\alpha ) ($the NEGATIVE lower-tail quantile):

$$
\begin{gathered}
z_{\mathrm{cf}} = z + (z^{2} - 1) S/6 + (z^{3} - 3z) K/24 - (2z^{3} - 5z) S^{2}/36 \\
\operatorname{VaR}_{\mathrm{CF}} = -(\mu  + \sigma  z_{\mathrm{cf}})
\end{gathered}
$$

Horizon h (iid normal returns, per-period $\mu$, $\sigma$):

$$
\operatorname{VaR}_{h} = -h \mu  + \sqrt{h} \sigma  z_{c}
$$

$$
\operatorname{ES}_{h} = -h \mu  + \sqrt{h} \sigma  \phi (z_{c})/\alpha
$$

The scaling $\sqrt{h} \cdot  \operatorname{VaR}_{1}$ applies only when $\mu  = 0$.Backtests (exception $I_{t} = 1$ if the realized loss on day t exceeds that day's VaR forecast; $p = \alpha$):
Kupiec, with $0^{0} = 1$:

$$
\mathrm{LR}_{\mathrm{POF}} = -2 \ln [ (1-p)^{T-x} p^{x} ] + 2 \ln [ (1 - x/T)^{T-x} (x/T)^{x} ] \sim \mathrm{chi2}(1)
$$

$n_{ij}$ counts days $t = 2\ldots T$ with $I_{t-1} = i$ and $I_{t} = j$.

$$
\mathrm{pi01} = \mathrm{n01}/(\mathrm{n00} + \mathrm{n01})
$$

$$
\mathrm{pi11} = \mathrm{n11}/(\mathrm{n10} + \mathrm{n11})
$$

$$
\pi  = (\mathrm{n01} + \mathrm{n11})/(\mathrm{n00} + \mathrm{n01} + \mathrm{n10} + \mathrm{n11})
$$

Christoffersen:

$$
\mathrm{LR}_{\mathrm{ind}} = -2 \ln [ (1-\pi )^{\mathrm{n00}+\mathrm{n10}} \pi ^{\mathrm{n01}+\mathrm{n11}} ] + 2 \ln [ (1-\mathrm{pi01})^{\mathrm{n00}} \mathrm{pi01}^{\mathrm{n01}} (1-\mathrm{pi11})^{\mathrm{n10}} \mathrm{pi11}^{\mathrm{n11}} ] \sim \mathrm{chi2}(1)
$$

$$
\mathrm{LR}_{\mathrm{cc}} = \mathrm{LR}_{\mathrm{POF}} + \mathrm{LR}_{\mathrm{ind}} \sim \mathrm{chi2}(2)
$$

Reject when LR exceeds the chi2 quantile at the test's confidence level; p-value = 1 - $F_{\mathrm{chi2}}$(LR).
If $\mathrm{n10} + \mathrm{n11} = 0$(no exception before day T), drop the pi11 terms; terms with a zero count contribute 0.

## Common variants and mistakes
- Sign and level: c vs $\alpha$ swapped, quantile reported with the wrong sign, percent vs decimal.
- Mean: "VaR relative to the mean" / zero-mean VaR drops $\mu$; "absolute VaR" keeps -$\mu$. $\sigma$ with $\mathrm{ddof} = 1$ vs 0.
- Student-t: if the task gives a volatility (standard deviation) use the scaled s; if it gives a fitted t scale use it
  directly. The two differ by $\sqrt{\nu /(\nu  - 2)}$, large for small $\nu$.
- Positions: a portfolio VaR is the VaR of the whole position. Scale the Greeks (or the per-unit P&L standard deviation) by the number of contracts or units before applying the quantile; the variance shares of the components are unchanged by this scaling, the VaR is not.
- Student-t maximum likelihood for a location-scale t estimates $\nu$, $\mu$ and $s$ jointly. `scipy.stats.t.fit(x)` returns them in the order `(df, loc, scale)`, and its `scale` is $s$, not the standard deviation. Fixing the location at the sample mean or the scale at the sample standard deviation and fitting $\nu$ alone is a different estimator. Compute every quantity that depends on the fit (VaR and ES at every level and horizon, and any check built on them) from the same returned triple.
- Cornish-Fisher: K must be EXCESS kurtosis. Use $z = \Phi ^{-1}(\alpha ) < 0$; plugging $z_{c} > 0$ into the polynomial
  and then negating flips the sign of the skew terms. Sample skew/kurtosis: biased (scipy default) vs adjusted
  (pandas skew()/kurt()) estimators give different numbers. There is no standard CF ES; "modified ES" is the
  Boudt-Peterson-Croux (2008) construction, use it only if asked.
- Historical: the quantile rule changes the number (order statistic ceil(n $\alpha$) vs interpolated quantiles such as
  numpy's default linear rule); ES may average the floor(n $\alpha$) or ceil(n $\alpha$) worst returns, or all returns
  <= -VaR. Use the task's rule; the VaR and ES windows must be the same sample.
- Christoffersen: transitions use T - 1 pairs. $\mathrm{LR}_{\mathrm{cc}} = \mathrm{LR}_{\mathrm{POF}} + \mathrm{LR}_{\mathrm{ind}}$ is exact when $\mathrm{LR}_{\mathrm{POF}}$ is computed on the same
  T - 1 days (Christoffersen conditions on the first day); with $\mathrm{LR}_{\mathrm{POF}}$ on all T days it is the usual approximation.
  Exception definition strict (>) vs non-strict (>=), and which day's forecast is compared, change x.

## Applicability and known limits
- Square-root-of-time is exact only for iid normal returns with zero mean; with a mean use $-h \mu  + \sqrt{h} \sigma  z_{c}$.
  It is wrong under autocorrelation (positive autocorrelation: understates), volatility clustering, and for
  fat-tailed iid returns (a sum of t variables is not t; at high c, scaling the 1-period t VaR overstates the h-period quantile).
- Cornish-Fisher is an expansion: accurate for small |S| and K, poor deep in the tail of very fat-tailed data
  (it can overstate badly), and the map $z \to  z_{\mathrm{cf}}$ can become non-monotone for large |S| or K, making it invalid.
- Normal VaR/ES understate fat-tailed losses at high c; ES needs $\nu  > 1$, the unit-variance t needs $\nu  > 2$.
- The chi2 approximations of the LR tests are poor for small T * $\alpha$ (few expected exceptions): actual size can be
  far from nominal; simulated or exact p-values are an alternative if the task allows.

## Sources
Kupiec (1995) J. Derivatives 3(2):73-84; Christoffersen (1998) International Economic Review 39(4):841-862;
Cornish & Fisher (1938) Revue de l'Institut International de Statistique 5(4):307-320; Boudt, Peterson & Croux (2008)
J. Risk 11:79-103; Acerbi & Tasche (2002) J. Banking & Finance 26(7):1487-1503; McNeil, Frey & Embrechts,
Quantitative Risk Management, Princeton UP (2005; revised ed. 2015).
