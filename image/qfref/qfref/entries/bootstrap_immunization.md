# Zero-curve bootstrapping, duration / convexity / key-rate durations, and Redington immunization

## Bootstrap rules (read before writing the bootstrap)
- If any coupon date of a bond is not already a solved node, you MUST solve that bond's new node together with those in-between dates: write the bond's pricing equation with every cash-flow date valued from the curve as the task interpolates it, including the trial value of the new node, and solve it for the new node with a 1-D root finder (`scipy.optimize.brentq` on a bracket where the equation changes sign). Do not use the node-only closed form below for such a bond, do not interpolate those dates from the nodes solved so far (that holds the curve flat or extends the last segment), and never fill a missing discount factor with 0 or 1.
- Only when every coupon date of a bond is already a solved node may you use the closed form in "Bootstrapping" below.
- Before writing any output, reprice every input bond from the finished curve: each must return its input price (par, 1 per unit face, for a par bond) to rounding level. A miss that starts after the bonds whose coupon dates are all nodes means the rule above was not followed.

```python
import numpy as np
from scipy.optimize import brentq
maturities, coupons, freq = [1, 2, 3, 5], [0.040, 0.042, 0.044, 0.046], 1   # synthetic par bonds; 4 is not a node
nodes = {}                                                                  # maturity -> zero rate (continuous)
def df(t, curve):                                                           # linear in zero rate, flat before the first node
    ks = sorted(curve); return np.exp(-np.interp(t, ks, [curve[k] for k in ks]) * t)
def par_gap(z, T, c, curve):                                                # bond price minus par with trial zero rate z at T
    trial = {**curve, T: z}; times = np.arange(1, int(round(T * freq)) + 1) / freq
    return (c / freq) * sum(df(t, trial) for t in times) + df(T, trial) - 1.0
for T, c in zip(maturities, coupons):
    nodes[T] = brentq(par_gap, -0.5, 0.5, args=(T, c, nodes))
assert all(abs(par_gap(nodes[T], T, c, nodes)) < 1e-12 for T, c in zip(maturities, coupons))   # every input bond reprices at par
```

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting and assumptions
- Bonds $i = 1\ldots N$ with maturity $T_{i}$, annual coupon rate $c_{i}$, k coupons per year, face F, full (dirty) price $\operatorname{P}_{i}$
  (clean price + accrued interest). Cash flows: F $c_{i}$ / k at each coupon date $t_{ij}$ (counted back from $T_{i}$ in steps of 1/k), plus F at $T_{i}$.
- A compatible bootstrap solves calibration equations for curve nodes. An exact final fit requires sufficient degrees of freedom and consistent quotes/interpolation; a nonlocal interpolant can change earlier provisional fits. More quotes than free parameters can instead require a best fit.
- Duration / immunization formulas describe local sensitivity to a specified shift. Yield duration differentiates a bond's yield-to-maturity price representation; Fisher-Weil duration differentiates a parallel continuous zero-curve shift. These need not coincide for a nonflat curve.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $t$ | time from valuation date (task day count, e.g. days/365) | years |
| DF(t) | discount factor, price today of 1 paid at t | none |
| z(t) | zero rate; $\mathrm{DF} = \exp (-z t)$ (continuous) or $(1 + z/k)^{-k t}$ (k-periodic) | $\mathrm{decimal} (4\% = 0.04)$ |
| $y$ | yield to maturity of one bond, in the bond's own compounding k | decimal |
| shift | $1 \mathrm{bp} = 0.0001$ | decimal |

## Bootstrapping (sort bonds by maturity, solve one at a time)
- Coupon dates that coincide with earlier knots: $\mathrm{DF}(T_{i}) = [\operatorname{P}_{i} - \sum _{t_{ij} < T_{i}} \mathrm{CF}_{ij} \mathrm{DF}(t_{ij})] / \mathrm{CF}_{i,\mathrm{last}}$ (closed form).
- Par bonds ($\operatorname{P} = F$), coupon dates on the knot grid: $\mathrm{DF}_{n} = (1 - (c_{n}/k) \sum _{j<n} \mathrm{DF}_{j}) / (1 + c_{n}/k)$.
- Coupon dates BETWEEN knots: their DF comes from interpolation between the previous knot and the NEW unknown knot, so solve
  $\sum _{j} \mathrm{CF}_{ij} \mathrm{DF}(t_{ij}; x) = \operatorname{P}_{i}$ for $x = z(T_{i})$ with a 1-D root finder (bracket, e.g. Brent).
- State which quantity is interpolated; results differ between choices:
  (a) linear in zero rate z(t) (common default); (b) linear in ln DF(t) = piecewise-constant forward (the forward is flat between knots);
  (c) linear in DF (avoid: kinked forwards). Before the first knot: flat z; after the last knot: no extrapolation unless asked.
- T-bills / zero-coupon instruments: $\mathrm{DF} = \operatorname{P}/F$ directly (money-market quotes: $\mathrm{DF} = 1/(1 + r t)$ simple; discount basis $\mathrm{DF} = 1 - d t$).
- Check: reprice every input bond from the curve; the error must be at rounding level.

## Rates from discount factors
- Zero: continuous $z = -\ln  \mathrm{DF} / t$; k-periodic $z_{k} = k (\mathrm{DF}^{-1/(k t)} - 1)$; annual $\mathrm{DF}^{-1/t} - 1$. Convert:
  $z_{\mathrm{cont}} = k \ln (1 + z_{k}/k)$.
- Forward between $\mathrm{t1} < \mathrm{t2}$: continuous $F = \ln (\mathrm{DF1}/\mathrm{DF2})/(\mathrm{t2} - \mathrm{t1}) = (\mathrm{z2} \mathrm{t2} - \mathrm{z1} \mathrm{t1})/(\mathrm{t2} - \mathrm{t1})$;
  simple (money market) $F = (\mathrm{DF1}/\mathrm{DF2} - 1)/(\mathrm{t2} - \mathrm{t1})$; k-periodic $F = k [(\mathrm{DF1}/\mathrm{DF2})^{1/(k (\mathrm{t2} - \mathrm{t1}))} - 1]$.

## Duration and convexity (price $P=\sum_j\mathrm{CF}_j\mathrm{DF}_j$, weights $w_j=\mathrm{CF}_j\mathrm{DF}_j/P$)
- Macaulay $D_{\mathrm{mac}} = \sum _{j} t_{j} w_{j}$ (years; = T for a zero-coupon bond).
- Yield-based, k-periodic yield y: $\mathrm{DF}_{j} = (1 + y/k)^{-k t_{j}}$, $D_{\mathrm{mod}} = D_{\mathrm{mac}} / (1 + y/k)$ = -(1/P) dP/dy,
  $\mathrm{Conv} = \sum _{j} \mathrm{CF}_{j} t_{j} (t_{j} + 1/k) (1 + y/k)^{-k t_{j} - 2} / \operatorname{P}$. Continuous y: $D_{\mathrm{mod}} = D_{\mathrm{mac}}$, $\mathrm{Conv} = \sum _{j} t_{j}^{2} w_{j}$.
- Curve-based (Fisher-Weil): $\mathrm{DF}_{j}$ from the zero curve; duration $\sum _{j} t_{j} w_{j}$ and convexity $\sum _{j} t_{j}^{2} w_{j}$ are the
  sensitivities to a PARALLEL shift of continuous zero rates.
- Dollar duration $\mathrm{DD} = D_{\mathrm{mod}} \operatorname{P}$; DV01 (PV01, PVBP) $= D_{\mathrm{mod}} \operatorname{P} \cdot  0.0001$ (price change per 1 bp; per 100 face unless the task scales).
- Price change: $\mathrm{d}P \approx -D_{\mathrm{mod}} \operatorname{P} \mathrm{d}y + (1/2) \mathrm{Conv} \operatorname{P} \mathrm{d}y^{2}$.
- Effective (finite difference, shift h of the whole curve or of y): $D_{\mathrm{eff}} = (\operatorname{P}_{-} - \operatorname{P}_{+})/(2 \operatorname{P} h)$, $C_{\mathrm{eff}} = (\operatorname{P}_{+} + \operatorname{P}_{-} - 2\operatorname{P})/(\operatorname{P} h^{2})$.
- Key-rate durations (Ho 1992): choose key tenors $K_{1} < \ldots  < K_{n}$; add $h\Lambda_m(t)$ to the continuous zero rate at every cash-flow time $t$, where $\Lambda_m$ is one at $K_m$, zero at adjacent keys and linear between them (flat beyond an end key); reprice; $\mathrm{KRD}_{m} = (\operatorname{P}_{-} - \operatorname{P}_{+})/(2 \operatorname{P} h)$.
  If the profiles sum to one, the infinitesimal key-rate derivatives sum to the parallel-shift derivative. Finite central differences generally agree only up to bump-size error because repricing is nonlinear. A zero-node bump and a par-quote bump with recalibration are distinct sensitivities; follow the specified risk definition.

## Redington immunization (assets A vs liabilities L, same curve, same shift)
- Conditions: (1) $\mathrm{PV}_{A} = \mathrm{PV}_{L}$; (2) $D_{A} = D_{L}$ (equivalently equal dollar durations / DV01s); (3) $\mathrm{Conv}_{A} > \mathrm{Conv}_{L}$
  (asset cash flows more dispersed around D than the liabilities). Then surplus $S = \mathrm{PV}_{A} - \mathrm{PV}_{L}$ has a local MINIMUM at the
  current rate: $\mathrm{d}S \approx (1/2)(\mathrm{Conv}_{A} - \mathrm{Conv}_{L}) \mathrm{PV}_{L} \mathrm{d}y^{2} \ge  0$ for a small parallel shift dy.
- Two-bond barbell for a liability of duration $D_{L}$ with bonds of durations $D_{1} < D_{L} < D_{2}$(PV weights):
  $w_{1} = (D_{2} - D_{L})/(D_{2} - D_{1})$, $w_{2} = 1 - w_{1}$; amount in bond $i = w_{i} \mathrm{PV}_{L}$; face/units = that amount / bond price.
  Use the same duration type (Macaulay with Macaulay, modified with modified, Fisher-Weil with Fisher-Weil) for all positions.
  $D_{L}$ outside [$D_{1}$, $D_{2}$] needs a short position.
- Single fixed liability (Fisher & Weil 1971): nonnegative fixed asset cash flows with $\mathrm{PV}=\mathrm{PV}_L$ and Fisher-Weil duration equal to the liability horizon provide global protection under an additive parallel shift of the same continuous zero curve. Nonnegative present-value weights are needed for the Jensen argument; a signed/short portfolio does not inherit this guarantee.

## What breaks it
- Non-parallel shifts: a barbell against a bullet liability can LOSE under a slope change (e.g. a steepener pivoting at the
  liability date); matching KRDs bucket by bucket hedges this:
  $\mathrm{d}S \approx -\sum _{m} (\mathrm{KRD}_{A,m} \mathrm{PV}_{A} - \mathrm{KRD}_{L,m} \mathrm{PV}_{L}) \mathrm{d}z_{m}$.
- Large shifts (higher-order terms), passage of time and rate changes (durations drift at different speeds) -> rebalance.
- Defaults, calls, prepayment, liabilities whose cash flows depend on rates.

## Common mistakes
- Using clean prices in the bootstrap; forgetting the final coupon in the last cash flow; using coupon c instead of c/k.
- Discounting all cash flows of a bond at its own YTM inside a bootstrap (that is YTM, not zero rates).
- Mixing compounding (periodic zero in $\exp ( -z t )$); reporting $D_{\mathrm{mac}}$ where $D_{\mathrm{mod}}$ is asked (they differ by 1 + y/k).
- Convexity in the k-periodic case without the (t + 1/k)/(1 + y/k)^2 terms; DV01 sign or scale (per 1 bp, not per 1%).
- Reusing one result name (`res`, say) for the immunization solve and a later curve fit: outputs written afterwards read the curve parameters as allocations. Give each solve its own name and write each output from its own result.
- A scenario shift built from an integer maturity array (`np.full_like(T, 0.01)` with integer T) is all zeros. Build shifts as floats and check each scenario: the shift array differs from zero where the scenario says, the scenario curve differs from the base curve, and each instrument is repriced from its own cash flows under it. For an instrument with nonnegative cash flows at positive future times, a parallel rise lowers its PV, so an unchanged PV there means the shift was not applied.

## Sources
Macaulay (1938) Some Theoretical Problems Suggested by the Movements of Interest Rates, Bond Yields and Stock Prices in the
United States since 1856, NBER; Redington (1952) "Review of the Principles of Life-Office Valuations", J. Institute of Actuaries
78:286-340; Fisher & Weil (1971) "Coping with the Risk of Interest-Rate Fluctuations", J. Business 44(4):408-431;
Ho (1992) "Key Rate Durations: Measures of Interest Rate Risks", J. Fixed Income (Sept.):29-44;
Hagan & West (2006) "Interpolation Methods for Curve Construction", Applied Mathematical Finance 13(2):89-129;
Hull, Options, Futures, and Other Derivatives, 9th ed., Pearson, ch. 4 "Interest Rates".

Par quotes shorter than one coupon period pay a single amount $1+yT$ at maturity (simple accrual over T), so the bootstrap discount factor is $1/(1+yT)$. Pricing such a quote as principal only forces DF = 1 and a zero rate of 0. Check that every short zero rate sits within a few basis points of its quote.
