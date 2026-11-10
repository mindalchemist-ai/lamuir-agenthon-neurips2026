# Realized variance with microstructure noise: Bandi-Russell noise variance and optimal sampling, bipower variation, two-scales RV

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Model and setting
- Observed log price = efficient log price + noise: $y_{t} = x_{t} + \eta _{t}$. x is a continuous semimartingale with integrated variance
  

$$
\mathrm{IV} = \int  \sigma _{s}^{2} \mathrm{d}s
$$

 over the period (usually one trading day). $\eta$ is iid, mean 0, variance $\sigma _{\eta}^{2}$, independent of x.
- Intraday return j of day i: $r_{j} = y_{t_{j}} - y_{t_{j-1}} = (x_{t_{j}} - x_{t_{j-1}}) + \mathrm{eps}_{j}$, $\mathrm{eps}_{j} = \eta _{j} - \eta _{j-1}$.
  So $\operatorname{E}(\mathrm{eps}^{2}) = 2 \sigma _{\eta}^{2}$ and $\operatorname{Cov}(\mathrm{eps}_{j}, \mathrm{eps}_{j-1}) = -\sigma _{\eta}^{2}$: noise makes high-frequency returns negatively autocorrelated (MA(1)).
- Use LOG returns of consecutive prices inside one day. Do not include the overnight return or the jump from day i's last price to
  day i+1's first price. M = number of returns in the day = number of prices in the day minus 1 (zero returns count).

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $r_{j}, j = 1\ldots M$ | intraday log returns of one day at the chosen sampling frequency | log units |
| $M$ | returns per day; $M^{*}$ = optimal count; interval = (trading-day length) / M | count |
| IV, Q | integrated variance and integrated quarticity $\int  \sigma ^{4} \mathrm{d}s$ of one day | per day, per day^2 |
| $\sigma _{\eta}^{2}$ | variance of the noise in the $\log  \mathrm{PRICE}$ | log units^2 |
| $\operatorname{E}(\mathrm{eps}^{2}), \operatorname{E}(\mathrm{eps}^{4})$ | 2nd / 4th moment of the noise in RETURNS; $\operatorname{E}(\mathrm{eps}^{2}) = 2 \sigma _{\eta}^{2}$ | log units^2, ^4 |
| $N_{d}$ | number of days pooled | count |

## Formulas
Realized variance of one day: $\mathrm{RV} = \sum _{j=1}^{M} r_{j}^{2}$. On a fixed efficient-price grid define $\mathrm{RV}_x=\sum_{j=1}^M(x_j-x_{j-1})^2$. Conditional on that path and independent price noise, the exact expectation is $\mathrm{E}[\mathrm{RV}\mid x]=\mathrm{RV}_x+2M\sigma_\eta^2$. For a continuous Ito process, $\mathrm{RV}_x$ converges to IV as the mesh vanishes, but need not equal it on a finite grid. Accordingly $\mathrm{E}[\widehat\sigma_\eta^2\mid x]=\sigma_\eta^2+\mathrm{RV}_x/(2M)$ for the estimator below. Adjacent return-noise covariance is $-\sigma_\eta^2$; non-iid or endogenous price noise changes these identities.

Bandi-Russell noise moments, from returns at the HIGHEST available frequency (every price change / tick):
Per day:

$$
\widehat{\mathrm{E}}(\mathrm{eps}^{2}) = \mathrm{RV} / M
$$

$$
\hat{\sigma}_{\eta}^{2} = \mathrm{RV} / (2 M)
$$

Pooled:

$$
\widehat{\mathrm{E}}(\mathrm{eps}^{2}) = \sum _{i} \sum _{j} r_{ij}^{2} / \sum _{i} M_{i}
$$

The denominator equals $N_{d} M$ when every day has $M$ returns.

$$
\widehat{\mathrm{E}}(\mathrm{eps}^{4}) = \sum _{i} \sum _{j} r_{ij}^{4} / \sum _{i} M_{i}
$$

$$
\hat{\sigma}_{\eta}^{2} = \widehat{\mathrm{E}}(\mathrm{eps}^{2}) / 2
$$

Conditional on the efficient path, $\mathrm{E}[\mathrm{RV}/(2M)\mid x]-\sigma_\eta^2=\mathrm{RV}_x/(2M)$. This is an upward conditional-mean bias, not an inequality for every random estimate. For a continuous efficient price, $\mathrm{RV}_x$ approaches $\mathrm{IV}$ as sampling becomes fine, so this bias vanishes.

Quarticity (Barndorff-Nielsen & Shephard), per day, from LOWER-frequency returns (Bandi & Russell 2006 use 15-minute returns), $M_{q}$ returns:

$$
\widehat Q= (M_{q} / 3) \cdot  \sum _{j=1}^{M_{q}} r_{j}^{4}
$$

MSE-optimal number of returns per day (Bandi & Russell 2006 Prop. 3; 2008):

$$
\mathrm{MSE}(M) \approx 2 Q / M + M \beta  + M^{2} \alpha
$$

$$
\alpha  = (\operatorname{E}(\mathrm{eps}^{2}))^{2}
$$

$$
\beta  = 2 \operatorname{E}(\mathrm{eps}^{4}) - 3 (\operatorname{E}(\mathrm{eps}^{2}))^{2}
$$

$M^{*}$ solves the exact first-order condition:

$$
2 M^{3} \alpha  + M^{2} \beta  - 2 Q = 0
$$

Rule of thumb (Prop. 4; good when $M^{*}$ is large):

$$
M^{*} \approx ( Q / (\operatorname{E}(\mathrm{eps}^{2}))^{2} )^{1/3}
$$

For one $M^{*}$ over many days, use the average of the daily Q^ (or compute M*_i per day with Q^_i). Optimal interval = day length / $M^{*}$.

Bipower variation (Barndorff-Nielsen & Shephard 2004), per day:

$$
\mathrm{BV} = \mathrm{mu1}^{-2} \cdot  \sum _{j=2}^{M} \vert r_{j}\vert  \vert r_{j-1}\vert ,   \mathrm{mu1} = \operatorname{E}\vert Z\vert  = \sqrt{2/\pi},  \mathrm{so} \mathrm{mu1}^{-2} = \pi /2
$$

Jump part of quadratic variation: $\mathrm{RV} - \mathrm{BV}$ (often floored at 0). Without noise and jumps, BV and RV both estimate IV.

Two-scales realized variance (Zhang, Mykland & Ait-Sahalia 2005), one day with log prices $y_{0}$..$y_{n}$ (n returns):

$$
\mathrm{RV}_{\mathrm{all}} = \sum _{j=1}^{n} (y_{j} - y_{j-1})^{2}
$$

$\mathrm{RV}^{(k)}$ sums squared differences over consecutive points of subgrid $k$.

$$
\mathrm{subgrid}_{k} = \{y_{k-1}, y_{k-1+K}, y_{k-1+2K}, \ldots \}
$$

For $k = 1\ldots K$.

$$
\mathrm{RV}_{\mathrm{avg}} = (1/K) \sum _{k} \mathrm{RV}^{(k)}
$$

$$
\bar{n} = (n - K + 1) / K
$$

$$
\mathrm{TSRV} = \mathrm{RV}_{\mathrm{avg}} - (\bar{n} / n) \mathrm{RV}_{\mathrm{all}}
$$

Small-sample adjusted:

$$
\mathrm{TSRV}_{\mathrm{adj}} = \mathrm{TSRV} / (1 - \bar{n} / n)
$$

Noise variance (ZMA), same as Bandi–Russell per day:

$$
\hat{\sigma}_{\eta}^{2} = \mathrm{RV}_{\mathrm{all}} / (2 n)
$$

$K$ grows like $c n^{2/3}$.
Annualization: annual variance = (periods per year from the task, commonly 252 trading days) * mean of daily estimates;
volatility = sqrt of that. Average VARIANCES across days, then take the square root. Daily vol = $\sqrt{\text{daily RV}}$.

## Variants and common mistakes
- Price noise vs return noise: "noise variance" usually means $\sigma _{\eta}^{2} = \mathrm{RV}/(2M); \operatorname{E}(\mathrm{eps}^{2}) = \mathrm{RV}/M$ is twice that. The rule of thumb
  uses E(eps^2); plugging $\sigma _{\eta}^{2}$ instead makes $M^{*}$ too large by a factor 4^(1/3).
- n / M counts RETURNS, not prices. Pooled estimates divide the pooled sum by the total number of returns, not by days times a nominal M.
- Per-day vs pooled: per-day RV/(2M) gives one noise estimate per day; pooled (Prop. 1b) assumes the noise is iid across days. Use what the task asks.
- Q^ from the highest frequency is dominated by noise; compute it from sparse returns. Do not use $Q = \mathrm{RV}^{2}$ unless the task says so.
- BV and RV from the same returns are of the same size: by Cauchy-Schwarz $\sum|r_j||r_{j-1}| \le \mathrm{RV}$, so $\mathrm{BV} \le (\pi/2)\,\mathrm{RV}$; BV close to $(\pi/2)\,\mathrm{RV}$ on most days means the products are $|r_j|^2$. In pandas, `s.iloc[1:] * s.iloc[:-1]` aligns on index labels and multiplies each value by itself; use `np.abs(r.to_numpy())` slices or `s * s.shift(1)`.
- BV constant is $\pi/2$, not $2/\pi$. Some papers multiply BV by M/(M-1) (finite-sample variant). BV is robust to jumps, NOT to noise: compute it at a sparse frequency.
- Sparse RV at M returns: sample every (day length / M) using the last price at or before each grid time (previous tick), starting at the open.
- Simple returns, percentage returns, or including the overnight return all change the number.

## Applicability and known limits
- iid noise independent of the price is assumed. Serially dependent noise or noise correlated with x breaks RV/(2M) and the $M^{*}$ formula.
- With finite M a jump J still inflates BV by about $\vert J\vert  \sqrt{2 \pi  \mathrm{IV} / M}; \mathrm{RV} - \mathrm{BV}$ is then a noisy jump estimate.
- TSRV subgrids lose up to $K-1$ edge intervals. With driftless constant intraday volatility and an equidistant grid,

$$
\mathrm{E}[\mathrm{TSRV}]
=\mathrm{IV}\frac{(n-K+1)(K-1)}{nK}.
$$

  The unadjusted relative downward bias is about $K/n+1/K$, not just $K/n$. For the adjusted estimator,

$$
\mathrm{E}[\mathrm{TSRV}_{\mathrm{adj}}]
=\mathrm{IV}\frac{n-K+1}{n+1},
$$

  whose relative downward bias is $K/(n+1)$. These finite-grid expectations use the stated constant-volatility setup; changing endpoint handling changes the edge terms.
- In a simulation, separate the realized efficient-grid quantity from its continuous target: conditional on $x$, $\mathrm{E}[\mathrm{RV}\mid x]-\mathrm{RV}_x=M\mathrm{E}(\mathrm{eps}^2)$. Comparing against $\mathrm{IV}$ adds efficient-price discretization error; it is not an exact pathwise identity.

## Sources
Bandi & Russell (2006) "Separating microstructure noise from volatility", J. Financial Economics 79(3):655-692;
Bandi & Russell (2008) "Microstructure noise, realized variance, and optimal sampling", Review of Economic Studies 75(2):339-369;
Barndorff-Nielsen & Shephard (2004) "Power and bipower variation with stochastic volatility and jumps", J. Financial Econometrics 2(1):1-37;
Zhang, Mykland & Ait-Sahalia (2005) "A tale of two time scales", J. American Statistical Association 100(472):1394-1411.
