# Spread options: Kirk (1995) approximation and Margrabe (1978) exchange option

Use this reference to choose and evaluate Margrabe exchange pricing or the Kirk approximation for a European spread option.

Map task quantities to these definitions by meaning and units, not by letter, before the first calculation; recheck when inputs or conventions change.

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Payoff and model
- Spread call payoff at expiry T: $\max (\mathrm{F1}(T) - \mathrm{F2}(T) - K, 0)$. Leg 1 is the leg you are long. Put payoff: $\max (K + \mathrm{F2}(T) - \mathrm{F1}(T), 0)$.
- Model: F1, F2 are forward/futures prices that follow correlated driftless geometric Brownian motions
  (Black-76 world): constant lognormal vols sigma1, sigma2, constant correlation $\rho$ of the log returns,
  constant rate, European exercise, no jumps, no smile. Then the spread itself is NOT lognormal, so
  for $K \ne  0$ there is no exact closed form. Kirk is an approximation; Margrabe ($K = 0$) is exact in this model.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| F1, F2 | forward or futures prices of the two legs for delivery at (or after) T | price units |
| $K$ | fixed strike of the spread, same price units (can be 0 or negative) | price units |
| sigma1, sigma2 | annualized lognormal (percentage) vols of F1, F2; 30% is `0.30` | $1/\sqrt{\mathrm{year}}$ |
| $\rho$ | correlation of the two log returns, in [-1, 1] | none |
| $T$ | time to expiry in years (day count from the task; often days/365) | years |
| $r$ | continuously compounded rate for discounting the payoff; $\mathrm{DF} = \exp (-r T)$ | $1/\mathrm{year}$ |

## Margrabe (K = 0, exact)
**Margrabe relative volatility**

$$
\sigma  = \sqrt{\mathrm{sigma1}^{2} - 2 \rho  \mathrm{sigma1} \mathrm{sigma2} + \mathrm{sigma2}^{2}}
$$

**Exchange-option exercise thresholds**

$$
\mathrm{d1} = [\ln (\mathrm{F1}/\mathrm{F2}) + \sigma ^{2} T / 2] / (\sigma  \sqrt{T}),   \mathrm{d2} = \mathrm{d1} - \sigma  \sqrt{T}
$$

**Margrabe exchange-call price**

$$
C  = \mathrm{DF} \cdot  [\mathrm{F1} N(\mathrm{d1}) - \mathrm{F2} N(\mathrm{d2})]
$$

Spot form with continuous yields q1, q2: $C = \mathrm{S1} e^{-\mathrm{q1} T} N(\mathrm{d1}) - \mathrm{S2} e^{-\mathrm{q2} T} N(\mathrm{d2})$ with

$\ln (\mathrm{S1} e^{-\mathrm{q1} T} / (\mathrm{S2} e^{-\mathrm{q2} T}))$ in d1. Without yields the price does not depend on r (Margrabe 1978).

## Kirk (K != 0, approximation; requires F2 + K > 0)
Treat $\mathrm{F2} + K$ as one lognormal "strike asset" and price a Margrabe/Black-76 call on F1 against it:

**Kirk second-leg weight**

$$
w       = \mathrm{F2} / (\mathrm{F2} + K)
$$

**Kirk effective volatility**

$$
\sigma _{K} = \sqrt{\mathrm{sigma1}^{2} - 2 \rho  \mathrm{sigma1} \mathrm{sigma2} w + \mathrm{sigma2}^{2} w^{2}}
$$

**Kirk exercise thresholds**

$$
\mathrm{d1} = [\ln (\mathrm{F1} / (\mathrm{F2} + K)) + \sigma _{K}^{2} T / 2] / (\sigma _{K} \sqrt{T}),   \mathrm{d2} = \mathrm{d1} - \sigma _{K} \sqrt{T}
$$

**Kirk spread-call approximation**

$$
C  = \mathrm{DF} \cdot  [\mathrm{F1} N(\mathrm{d1}) - (\mathrm{F2} + K) N(\mathrm{d2})]
$$

**Spread-put approximation by parity**

$$
\operatorname{P}  = C - \mathrm{DF} \cdot  (\mathrm{F1} - \mathrm{F2} - K)\quad (\;\text{put}\;-\;\text{call}\; \;\text{parity}\;; \;\text{equals}\; \mathrm{DF}\cdot [(\mathrm{F2}+K)N(-\mathrm{d2}) - \mathrm{F1} N(-\mathrm{d1})])
$$

At $K = 0, w = 1$ and Kirk equals Margrabe exactly.

## Spot inputs (rates, dividend yields, cost of carry)
- Convert each leg to a forward first: $F_{i} = S_{i} \cdot  \exp ((r - q_{i}) T)$ or, with cost of carry $b_{i}$, $F_{i} = S_{i} \cdot  \exp (b_{i} T)$
  ($q_{i}$ = dividend yield / foreign rate / convenience yield net of storage). Then use the formulas above with $\mathrm{DF} = \exp (-r T)$.
Equivalent spot form: $C = \mathrm{S1} e^{-\mathrm{q1} T} N(\mathrm{d1}) - (\mathrm{S2} e^{-\mathrm{q2} T} + K e^{-r T}) N(\mathrm{d2})$, with

  $w = \mathrm{S2} e^{-\mathrm{q2} T} / (\mathrm{S2} e^{-\mathrm{q2} T} + K e^{-r T})$. Do NOT plug raw spot S2/(S2+K) into w when carry is non-zero.
- Futures inputs: use futures prices as $F_{i}$ directly (no carry adjustment); discount with $\exp (-r T)$ to the payment date.
  If the option itself is futures-style margined (no upfront premium), the task may want $\mathrm{DF} = 1$.

## Common variants
- Quantities / heat rates: payoff $a \mathrm{F1} - b \mathrm{F2} - K$ (e.g. spark spread with heat rate b): use `a F1`, `b F2` as the legs; vols and $\rho$ unchanged.
- Leg order: payoff $(F_2-F_1-K)^+$ is a call on the swapped legs with strike $K$. The original spread put $(K+F_2-F_1)^+$ instead requires swapped legs with strike $-K$ (swap sigma1/sigma2 too; $\rho$ stays).
- Negative strike: direct Kirk is defined while $\mathrm{F2} + K > 0 (w > 1)$. If $\mathrm{F2} + K \le  0$ Kirk is undefined
  (log of a non-positive number); price the put $\max (\mathrm{F2}(T) - \mathrm{F1}(T) - (-K), 0)$ as a Kirk call on the swapped legs with strike -K, then
  $C = \operatorname{P} + \mathrm{DF} (\mathrm{F1} - \mathrm{F2} - K)$. This is plain parity, not a published refinement.
- Refinements: modified Kirk of Alos & Leon (2016) adds a skew correction to $\sigma _{K}$ and targets
  $\rho$ near 1; Bjerksund & Stensland (2014) give a closed-form lower bound reported more accurate than Kirk;
  Deng, Li & Zhou (2008) give another closed-form approximation with Greeks. Use one only if the task asks for it.

## Applicability and known limits
- Literature: Kirk is accurate for small K relative to F2 and degrades when $\rho$ is close to 1
  (Alos & Leon 2016; Harutyunyan & Masip Borras 2018). Bjerksund & Stensland (2014) report their bound is much more precise than Kirk.
- Approximation error depends on both volatilities, maturity, strike and correlation. No universal percentage tolerance follows from the model; relative error is particularly unstable when the true option value is small.
- So when a task asks for Kirk, a gap between Kirk and a Monte Carlo price is expected and is not by itself a bug in the Kirk code. The Monte Carlo itself can still be checked: at K = 0 Margrabe is exact for the same two lognormal prices, so the discounted Monte Carlo price at K = 0 on the same paths must match Margrabe within a few standard errors; a larger gap is a bug in the simulation (most often a missing discount factor or a wrong drift).
```python
pay0 = np.maximum(x_end - y_end, 0.0)        # x_end, y_end: simulated terminal prices of the two assets; mc0 = np.exp(-r * T) * pay0.mean(); se0 = np.exp(-r * T) * pay0.std(ddof=1) / np.sqrt(len(pay0))
assert abs(mc0 - margrabe_price) < 4 * se0, (mc0, margrabe_price, se0)
```
- Kirk cannot be used with $\mathrm{F2} + K \le  0, \rho$ outside [-1, 1], or a zero ratio vol (then the price is the discounted intrinsic value).
- Assumption failures (smile, jumps, mean reversion, legs with different delivery dates and a term structure of vols, negative prices) are not fixed by Kirk.

## Sources
Margrabe (1978) J. Finance 33(1):177-186; Kirk (1995) in R. Jameson (ed.) Managing Energy Price Risk, Risk Publications & Enron, pp. 71-78
(formula as reproduced in the literature and in QuantLib's KirkEngine); Black (1976) J. Financial Economics 3:167-179;
Carmona & Durrleman (2003) SIAM Review 45(4):627-685.
