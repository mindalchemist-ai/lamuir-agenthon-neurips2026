# Black-Litterman (1992) posterior returns, He-Litterman (1999) Omega and Idzorek confidence views

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Model and assumptions
- N assets, returns $r\sim N(\mu,\Sigma)$ with $\Sigma$ known. The unknown mean $\mu$ has a prior centred on the market equilibrium:
  $\mu  \sim N(\pi , \tau  \Sigma )$ ($\tau$ $\Sigma$ is the uncertainty of the MEAN, not of returns).
- K views: $P\mu+\mathrm{eps}=Q$, $\mathrm{eps} \sim N(0, \Omega )$, independent of the prior. Posterior = Gaussian (Bayes / Theil mixed estimation).
- All returns are EXCESS returns over the risk-free rate unless the task says otherwise; add $r_{f}$ back only if total returns are asked for.

## Parameters and units
| symbol | meaning | shape / units |
|---|---|---|
| $\Sigma$ | covariance of asset returns over the chosen period (annual or monthly, as given) | N x N, return^2 per period |
| $w_{\mathrm{mkt}}$ | market-cap weights, summing to 1 | $N$ |
| $\delta$ | risk-aversion coefficient; implied by the market: $\delta  = (\operatorname{E}[r_{m}] - r_{f}) / \sigma _{m}^{2}$ ($\mathrm{Sharpe}_{m}$ / $\sigma _{m}$) | none if premium and variance use the same period |
| $\pi$ | implied equilibrium excess returns | N, decimal (5% is 0.05) |
| $\tau$ | scalar shrinking $\Sigma$ to the uncertainty of the mean; given by the task | none |
| $\operatorname{P}$ | view-pick matrix; row k = one view | K x N |
| $Q$ | view returns, same period and units as $\pi$ | $K$ |
| $\Omega$ | covariance of view errors, usually diagonal | K x K, return^2 per period |

## Formulas
Reverse optimization:

$$
\pi  = \delta  \Sigma  w_{\mathrm{mkt}}
$$

Master form:

$$
\mu _{\mathrm{BL}} = [ (\tau  \Sigma )^{-1} + \operatorname{P}' \Omega ^{-1} \operatorname{P} ]^{-1} [ (\tau  \Sigma )^{-1} \pi  + \operatorname{P}' \Omega ^{-1} Q ]
$$

Update form; with zero view noise, the displayed inverse requires full row rank of the view matrix and positive-definite prior covariance:

$$
\mu _{\mathrm{BL}} = \pi  + \tau  \Sigma  \operatorname{P}' (\operatorname{P} \tau  \Sigma  \operatorname{P}' + \Omega )^{-1} (Q - \operatorname{P} \pi )
$$

$$
M = [ (\tau  \Sigma )^{-1} + \operatorname{P}' \Omega ^{-1} \operatorname{P} ]^{-1} = \tau  \Sigma  - \tau  \Sigma  \operatorname{P}' (\operatorname{P} \tau  \Sigma  \operatorname{P}' + \Omega )^{-1} \operatorname{P} \tau  \Sigma
$$

The precision expression for $M$ requires invertible $\Omega$. With zero or singular view noise, use the covariance-update expression under its stated rank/compatibility conditions, rather than inverting $\Omega$.

Covariance of next-period returns (He–Litterman):

$$
\Sigma _{\mathrm{BL}} = \Sigma  + M
$$

Unconstrained mean-variance weights:

$$
w^{*} = (\delta  \Sigma _{\mathrm{BL}})^{-1} \mu _{\mathrm{BL}}
$$

- Check M: it is no larger than $\tau\Sigma$, so every diagonal entry of M is positive and at most the matching entry of $\tau\Sigma$. A sign error in the update ($+$ instead of $-$ in the second form above) gives entries larger than $\tau\Sigma$.
- M is the posterior covariance of the MEAN; $\Sigma _{\mathrm{BL}}$ is the predictive covariance of RETURNS. Say which one the task asks for.
- He-Litterman decomposition: with $\Sigma _{\mathrm{BL}}$ in the optimizer, $w^{*} = w_{\mathrm{mkt}}/(1+\tau ) + \operatorname{P}' \Lambda$ for some K-vector $\Lambda$;
  with no views $w^{*} = w_{\mathrm{mkt}}/(1+\tau )$. If the optimizer uses $\Sigma$ instead of $\Sigma _{\mathrm{BL}}$, no views give exactly $w_{\mathrm{mkt}}$.
- For certain views and positive-definite prior covariance, full-row-rank $P$ makes $P(\tau\Sigma)P'$ invertible and gives $P\mu_{\mathrm{BL}}=Q$. Redundant exact views require consistency: $Q-P\pi$ must lie in the range of $P(\tau\Sigma)P'$. For compatible redundancy, its Moore-Penrose inverse gives the Gaussian conditional mean and covariance. Contradictory exact views do not define a posterior; a generalized inverse cannot make them mutually true.
- Weights not summing to 1 is normal in the unconstrained solution; normalize or add constraints only if the task says so.

## Choosing Omega
- He-Litterman (1999): $\Omega  = \operatorname{diag}( \operatorname{P} (\tau  \Sigma ) \operatorname{P}' )$, i.e. $\omega _{k} = \tau  p_{k} \Sigma  p_{k}'$. Then the ratio $\Omega/\tau$ is fixed
  and $\mu _{\mathrm{BL}}$ does NOT depend on $\tau$ (M and $\Sigma _{\mathrm{BL}}$ still do). Off-diagonal terms are dropped (independent views).
- Idzorek (2007) confidence $C_{k}$ in (0, 1]: choose $\omega _{k}$ so that the single-view tilt of the weights equals $C_{k}$ times the
  100%-confidence tilt: $w_{k} = w_{\mathrm{mkt}} + C_{k} (w_{100,k} - w_{\mathrm{mkt}})$, with weights $(\delta  \Sigma )^{-1} \mu$. Idzorek solves $\omega _{k}$ numerically
  (minimize squared weight distance). For an unconstrained optimizer this equals the closed form (Walters):
  $\omega _{k} = ((1 - C_{k}) / C_{k}) \cdot  p_{k} (\tau  \Sigma ) p_{k}'$. $C_{k} = 1$ gives $\omega _{k} = 0; C_{k} = 0$ means ignore the view.
- Other choices: $\Omega$ given directly by the task (variances of view returns, i.e. squared standard errors), or
  $\Omega$ proportional to P $\Sigma$ P' with an explicit confidence scalar. Use the task's.

## View matrix conventions
- Absolute view "asset i returns q": row with 1 in column i.
- Relative view "i outperforms j by q": +1 at i, -1 at j (row sums to 0). With baskets, legs are split equally (1/n each) or
  by market-cap weight within each leg (Idzorek); the two give different P, so follow the task's wording.

## Common mistakes
- Using $\Sigma$ instead of $\tau$ $\Sigma$ in the prior / in P $\tau$ $\Sigma$ P'. $\Omega$ under He-Litterman includes $\tau$.
- Inverting $\Omega$ in the update form, or using $\Omega$ instead of $\Omega^{-1}$ in the master form.
- Mixing periods: $\Sigma$, $\pi$, Q, $r_{f}$, $\Omega$ must all be annual or all monthly (e.g. monthly $\Sigma$ with an annual Q).
  $\delta$ is the same for any period when its premium and variance use one period; $\pi$ then scales with $\Sigma$.
- Using total returns for Q while $\pi$ is in excess returns (or vice versa).
- Optimizing with $\Sigma$ when the task says posterior covariance $(\Sigma+M)$, or the reverse.
- $\delta$ from sample ($\mathrm{ddof}=1$) vs population variance of the market: follow the task; $\pi$ scales with $\delta$.
- Treating Q - P $\pi$ as the view: Q is the view itself; the "surprise" Q - P $\pi$ only appears in the update form.

## Applicability and limits
- Assumes normality and known $\Sigma$; $\tau$ has no agreed value (practice ranges widely) and only matters through M, $\Sigma _{\mathrm{BL}}$
  and the relative weight of prior vs views when $\Omega$ is not proportional to $\tau$.
- Long-only or budget constraints break the closed-form $w^{*}$ and the He-Litterman decomposition; then optimize $\mu _{\mathrm{BL}}$ numerically.

## Sources
Black & Litterman (1992) "Global Portfolio Optimization", Financial Analysts Journal 48(5):28-43;
He & Litterman (1999) "The Intuition Behind Black-Litterman Model Portfolios", Goldman Sachs Investment Management Research (SSRN 334304);
Idzorek (2007) "A Step-by-Step Guide to the Black-Litterman Model: Incorporating User-Specified Confidence Levels", in S. Satchell (ed.),
Forecasting Expected Returns in the Financial Markets, Academic Press, pp. 17-38; Walters, "The Black-Litterman Model in Detail", SSRN 1314585.
