# Range-based (OHLC) volatility: Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Model and setting
- During trading the log price is a Brownian motion with constant vol $\sigma$ and drift $\mu$ (geometric Brownian motion for the price),
  monitored continuously. Each period $i$ (usually a day) has open $O_{i}$, high $H_{i}$, low $L_{i}$, close $C_{i}$; $C_{i-1}$ is the previous close.
- Between $C_{i-1}$ and $O_{i}$ the market is closed. Each log return is named by its start and end price (cc = previous close to close, co = previous close to open, oc = open to close):
  close-to-close return $r_{cc,i} = \ln (C_{i} / C_{i-1})$;
  overnight (opening-jump) return $r_{co,i} = \ln (O_{i} / C_{i-1})$;
  open-to-close (intraday) return $r_{oc,i} = \ln (C_{i} / O_{i})$.
  Identity for every period: $r_{cc,i} = r_{co,i} + r_{oc,i}$. So $r_{oc,i} = r_{cc,i}$ only when there is no opening gap ($O_{i} = C_{i-1}$); on real data they differ every day.
- Normalized high and low relative to the open: $u_{i} = \ln (H_{i}/O_{i}) \ge  0$, $d_{i} = \ln (L_{i}/O_{i}) \le  0$.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $O, H, L, C$ | open, high, low, close of one period (prices, not returns) | price |
| $r_{cc}, r_{co}, r_{oc}, u, d$ | log ratios defined above (natural log) | log units |
| $n$ | number of periods in the window ($r_{cc}$ and $r_{co}$ need the previous close, so the first row has none) | count |
| $f$ | fraction of the full period (close to close) during which the market is closed | none |
| $\operatorname{P}$ | periods per year for annualization (from the task; commonly 252 for daily bars) | $1/\mathrm{year}$ |

## Per-period variance estimators
Close-to-close (the classical benchmark; uses closes only, includes the overnight part):

$$
r_{cc}^{2}, \quad r_{cc} = \ln (C_{i}/C_{i-1}) \quad \text{(not } r_{oc} = \ln (C_{i}/O_{i})\text{)}
$$

Window form: either the zero-mean form $(1/n) \sum_{i} r_{cc,i}^{2}$ or the sample variance $(1/(n-1)) \sum_{i} (r_{cc,i} - \operatorname{mean}(r_{cc}))^{2}$; use the one the task describes.

The range estimators below (Parkinson, Garman-Klass, Rogers-Satchell) estimate the variance of the open-to-close return $r_{oc}$ only; they use the same-period open, never the previous close.

Parkinson (1980):

$$
\sigma ^{2}_{\operatorname{P}} = (u - d)^{2} / (4 \ln  2) = [\ln (H/L)]^{2} / (4 \ln  2)
$$

Garman–Klass (1980), practical:

$$
\sigma ^{2}_{\mathrm{GK}} = 0.5 (u - d)^{2} - (2 \ln  2 - 1) r_{oc}^{2}
$$

Garman–Klass best analytic:

$$
\sigma ^{2}_{\mathrm{GK}^{*}} = 0.511 (u - d)^{2} - 0.019 [r_{oc} (u + d) - 2 u d] - 0.383 r_{oc}^{2}
$$

Rogers–Satchell (1991):

$$
\sigma ^{2}_{\mathrm{RS}} = u (u - r_{oc}) + d (d - r_{oc}) = \ln (H/C) \ln (H/O) + \ln (L/C) \ln (L/O)
$$

Garman-Klass with an opening jump (targets the full close-to-close variance; overnight treated as diffusion over fraction $f$):

$$
\sigma ^{2}_{\mathrm{GKo}} = a r_{co}^{2} / f + (1 - a) \sigma ^{2}_{\mathrm{GK}^{*}} / (1 - f)
$$

Variance-minimizing weight from Garman–Klass:

$$
a = 0.12
$$

## Multi-period estimate and annualization
- Window of $n$ periods: $\sigma ^{2} = (1/n) \sum _{i} \sigma ^{2}_{i}$ (mean of the per-period VARIANCES), annualized variance = $P\sigma^2$,
  annualized vol = $\sqrt{\operatorname{P} \cdot \sigma ^{2}}$. Do not average per-period volatilities, and do not annualize with $\operatorname{P}$ instead of $\sqrt{\operatorname{P}}$ on a vol.
- Yang-Zhang (2000), window of $n \ge  2$ periods, estimates the variance of the full close-to-close return (overnight + intraday):
Overnight returns, demeaned:

$$
V_{O} = (1/(n-1)) \sum _{i} (r_{co,i} - \operatorname{mean}(r_{co}))^{2}
$$

Open-to-close returns, demeaned:

$$
V_{C} = (1/(n-1)) \sum _{i} (r_{oc,i} - \operatorname{mean}(r_{oc}))^{2}
$$

$$
V_{\mathrm{RS}} = (1/n) \sum _{i} \sigma ^{2}_{\mathrm{RS},i}
$$

$$
k = (\alpha  - 1) / (\alpha  + (n + 1)/(n - 1))
$$

Yang–Zhang suggest $\alpha  = 1.34$, i.e.

$$
k = 0.34 / (1.34 + (n+1)/(n-1))
$$

$$
\sigma ^{2}_{\mathrm{YZ}} = V_{O} + k V_{C} + (1 - k) V_{\mathrm{RS}}
$$

  Rolling windows apply the whole formula (with its own means and $k$) inside each window.

## Properties (continuous monitoring; verified by simulation, see Applicability)
| estimator | unbiased, no drift | unbiased with drift | handles opening jump | efficiency vs close-to-close $r_{cc}^{2}$ (no drift, no gap) |
|---|---|---|---|---|
| Parkinson | yes | no (biased up) | no | about 4.9 (often quoted 5.2) |
| Garman-Klass (both forms) | yes | no (biased up, less than Parkinson) | no | about 7.4 |
| Rogers-Satchell | yes | yes | no | about 6.0 |
| Garman-Klass with jump | yes | no | yes (needs $f$) | about 8.4 |
| Yang-Zhang | yes | yes | yes | about 7 to 8 vs the demeaned close-to-close sample variance |
Efficiency = Var(benchmark) / Var(estimator) for the same number of periods.

Efficiency compares estimators of the variance. With rolling windows, form for every estimator the series of window variance estimates $\sigma^{2}_{w}$ (all on the same scale, daily or annualized), then $\mathrm{Efficiency} = \operatorname{Var}(\sigma^{2}_{w,\mathrm{benchmark}}) / \operatorname{Var}(\sigma^{2}_{w,\mathrm{estimator}})$, using the same windows and the same sample-variance definition for each series. The same ratio computed on the rolling volatility series $\sigma_{w} = \sqrt{\sigma^{2}_{w}}$ is a different number ($\operatorname{Var}(\sqrt{X}) \approx \operatorname{Var}(X) / (4 \operatorname{E}[X])$ brings in each estimator's mean level), so it does not replace the variance-based ratio. Rolling volatility is the series to report or plot; the efficiency uses the variance series.

## Variants and common mistakes
- Parkinson uses $\ln (H/L)$ of the SAME period, squared, divided by $4 \ln  2 (= 2.7726\ldots )$; not $\ln (H/O)$, not log10, not divided inside a square root twice.
- Two different returns, never interchangeable: the close-to-close estimator uses $r_{cc} = \ln (C_{i}/C_{i-1})$ (previous close); Garman-Klass and Rogers-Satchell use $r_{oc} = \ln (C_{i}/O_{i})$ (same-period open). Rogers-Satchell needs all four prices of the same period.
- Check in your code: (1) each estimator reads the return its formula names: close-to-close and the Yang-Zhang overnight term need a shift of the close series by one row, Garman-Klass, Rogers-Satchell and the Yang-Zhang open-to-close term do not; (2) one variable or column name per return ($r_{cc}$, $r_{co}$, $r_{oc}$), never one name such as `c` reused for two of them; (3) on the data, $r_{cc}$ equals $r_{co} + r_{oc}$ row by row and differs from $r_{oc}$ on days with an opening gap; if your close-to-close series equals your open-to-close series, it was built from the wrong prices.
- Opening gaps: Parkinson, Garman-Klass and Rogers-Satchell measure only open-to-close variance. If the target is close-to-close vol, add the overnight part (Yang-Zhang, or Garman-Klass with an opening jump);
  otherwise vol is understated by the overnight share of variance.
- Yang-Zhang: $n$ is the number of periods (overnight returns), not the number of prices; $V_{O}$ and $V_{C}$ are demeaned with $n-1$; $V_{\mathrm{RS}}$ is a plain mean.
  Some sources write $k$ with $T/(T-2)$ where $T$ counts prices; check which count the task uses.
- Yang-Zhang weights: $k$ multiplies $V_{C}$ and $1-k$ multiplies $V_{\mathrm{RS}}$; $V_{O}$ enters with weight 1. With $\alpha = 1.34$, $k$ rises from 0.078 at $n = 2$ toward $0.34/2.34 \approx 0.145$ as $n$ grows, so $V_{\mathrm{RS}}$ always carries most of the intraday weight.
  Two slips put a weight near 1 on $V_{C}$ and make Yang-Zhang about as noisy as close-to-close (its rolling efficiency can then fall below 1):
  writing $k = (n-1)/n$, and swapping $k$ and $1-k$ (that is, $k V_{\mathrm{RS}} + (1-k) V_{C}$). Also check the inputs: $V_{C}$ is built from $r_{oc}$, not $r_{cc}$, and the overnight term uses the previous close, $\ln(O_{i}/C_{i-1})$, not the previous open.
- Rogers-Satchell pairs each extreme with itself: $\ln(H/C)\ln(H/O) + \ln(L/C)\ln(L/O) \ge 0$ for every period. The cross pairing $\ln(H/O)\ln(L/O) + \ln(H/C)\ln(L/C)$ is $\le 0$ and is not a variance.
- Sanity check after computing rolling efficiencies: on ordinary daily data every range estimator, Yang-Zhang included, is expected to have a smaller rolling variance than close-to-close. A ratio below 1 for one of them almost always means its formula was built wrongly; recheck it before writing outputs.
- Output units: per-period vs annualized, variance vs volatility, decimal vs percent (30% is 0.30).

## Applicability and known limits
- All formulas assume continuous monitoring. Highs/lows from a finite number of trades or bars understate the true range, so range estimators are
  biased DOWN (simulation with a GBM sampled at only a few hundred points per period: about 6 to 9% low; with fewer points, more).
- Drift bias of Parkinson and Garman-Klass grows with $(\mu/\sigma)^2$ per period: negligible for daily bars of ordinary assets, large for long periods or strong trends.
- Simulation check (exact Brownian-bridge highs/lows): every estimator was within 0.4% of its target in the cases where the table says unbiased;
  Parkinson / Garman-Klass were +9% / +3.5% high at drift 0.5 $\sigma$ per period and +38% / +14% at drift 1 $\sigma$; Rogers-Satchell stayed within 0.2%;
  intraday-only estimators missed exactly the overnight share; the variance-minimizing $k$ from simulation matched the formula $k$ within 0.02.
- Stochastic volatility, jumps inside the period, and bid-ask bounce in $H$ and $L$ are not handled.

## Sources
Parkinson (1980) J. Business 53(1):61-65; Garman & Klass (1980) J. Business 53(1):67-78; Rogers & Satchell (1991)
Annals of Applied Probability 1(4):504-512; Yang & Zhang (2000) J. Business 73(3):477-491.
