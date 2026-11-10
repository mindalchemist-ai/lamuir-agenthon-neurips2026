# Degree-day indices and temperature-option valuation

Use this note for temperature-index contracts, historical burn valuation and seasonal Gaussian temperature models. Match the observation calendar, temperature scale, index unit and cash multiplier to the contract. Its explicit definitions govern; a convention from another city or exchange is not interchangeable.

## Index and payoff

CME degree-day contracts quote the reference temperature in Fahrenheit (65 F); when the observations are in Celsius or tenths of a degree, convert the reference temperature to that scale before computing daily degree-days (65 F is about 18.33 C).

Let $T_{j}$ be the specified daily temperature statistic, b the reference temperature, and J the set of covered days. Heating degree-days measure temperatures below b.

$$
H_{j} = \max (b-T_{j}, 0)
$$

Cooling degree-days measure temperatures above b.

$$
C_{j} = \max (T_{j}-b, 0)
$$

The heating index accumulates the daily contributions, rather than taking the positive part of a monthly temperature difference.

$$
H = \sum _{j \in  J} H_{j}
$$

A call on the index, with strike K in degree-days and multiplier m in currency per degree-day, pays at its settlement date.

$$
\;\text{payoff}\; = m\cdot \max (H-K, 0)
$$

Temperature conversion changes the index unit as well as the base. Celsius conversion for a temperature level is affine.

$$
T_{C} = (5/9)\cdot (T_{F}-32)
$$

When both temperature and base are converted consistently, degree-day differences scale linearly.

$$
H_{C} = (5/9)\cdot H_{F}
$$

Which unit to compute in, and what happens to strike and multiplier:

| Situation | What to do |
|---|---|
| The contract (or the task) states the index unit | compute the index in that unit and use the strike and multiplier as given |
| The task says to compute in another unit than the contract's | convert the index, the strike and the multiplier together: $K_{C}=(5/9)\cdot K_{F}$ and $m_{C}=(9/5)\cdot m_{F}$ (and the reverse); converting only one or two of them changes the contract |
| The strike has no stated unit | use it as written, in the unit of the index being computed; do not rescale it |
| Only the base is given in another unit (for example a Fahrenheit base for Celsius data) | convert the base temperature (affine, above) to the unit of the computation; this does not by itself convert the strike or the multiplier |

A contract explicitly denominated in Celsius degree-days already has its own strike and multiplier; it is not a Fahrenheit contract merely because the base was supplied in Fahrenheit. Decide the unit once, before the first payoff, and do not switch it in a later step; an earlier correct burn value overwritten by a "corrected" one in another unit is a common error.

Check: compute one season's payoff in both units, with the index, strike and multiplier converted together; the two amounts must be equal. Then check that each year's payoff equals max(index − strike, 0) · multiplier with all three in the unit actually used.

Summary fields named after the monthly index (a mean or standard deviation of monthly HDD, say) are statistics of the per-year monthly totals, the same numbers as the yearly table, not of the daily contributions; check that such a mean lies within the range of the yearly totals. Rounded regional base conventions are not exact unit conversion.

When the task asks for the target month's data to be cleaned and the temperature model fitted on that month's sample → the cleaned daily data, seasonal means, the fit, the simulation and the daily output file are restricted to that month's days in each year, and adjacent-day pairs are formed within the same month and year → check that the daily row count is about the number of years times the month's length. A task that calibrates on the whole year keeps the whole year.

## Historical and model valuations

For Y comparable historical seasons, $H_{y}$ denotes each complete index. Discounted burn value averages each season's option payoff; D is the discount factor to payment.

$$
V_{\mathrm{burn}} = D\cdot m\cdot \sum _{y=1}^{Y} \max (H_{y}-K, 0)/Y
$$

This is generally different from an option payoff on the average index. Missing observations and climate trends change comparability; a partial season is not automatically a complete low-index season. Weather itself is not a traded replicating asset, so a physical historical expectation is a valuation convention, not a uniquely forced no-arbitrage price. State the probability measure or premium assumption when one is specified.

Write temperature as a deterministic seasonal curve s(t) plus a residual $x_{t}$. For a Gaussian OU residual with reversion level $\theta$, speed $\kappa >0$ and diffusion scale $\sigma$, a gap h has the following conditional mean.

$$
\operatorname{E}[x_{t+h} \vert  x_{t}] = \theta  + (x_{t}-\theta )\cdot \exp (-\kappa \cdot h)
$$

Its conditional variance uses the same time unit as $\kappa$ and $\sigma$.

$$
\operatorname{Var}[x_{t+h} \vert  x_{t}] = \sigma ^{2}\cdot (1-\exp (-2\cdot \kappa \cdot h))/(2\cdot \kappa )
$$

Observations of the same residual path are dependent. The first observation date may coincide with the known initial state or occur later; that distinction changes the index distribution. Exact OU transitions do not make Euler-based calibration an exact maximum-likelihood fit.

For independent simulated season payoffs $\operatorname{P}_{i}$, the Monte Carlo standard error is sampling uncertainty, not weather-model uncertainty.

$$
\mathrm{SE} = D\cdot \;\text{sample}\;_{\mathrm{std}}(\operatorname{P}_{i})/\sqrt{\mathrm{number}_{\mathrm{of},\mathrm{paths}}}
$$

A sensitivity is a derivative with respect to the bumped quantity. For a relative parameter bump e, the denominator in a central difference with respect to parameter a is 2*e*a, not 2*e. A zero parameter needs an absolute bump convention. Paired scenarios using common innovations reduce noise in the difference.

## Checks and sources

Heating-call payoff is nonincreasing when all temperatures rise and nonincreasing in strike. Calendar and unit conversion should preserve the same economic contract. Historical and model prices need not coincide when their distributions differ.

[CME, Temperature Based Indexes](https://www.cmegroup.com/trading/weather/temperature-based-indexes.html) describes HDD/CDD/CAT and regional conventions. Index unit scaling, payoff aggregation and OU moments above follow directly from their definitions and the linear SDE solution; this is not a claim that all exchange contracts share one base or multiplier.
