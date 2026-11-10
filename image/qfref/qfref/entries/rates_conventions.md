# Rate curves and swaps: working conventions

Use this as a checklist when a task builds discount or projection curves, converts rates, shocks curves or values swaps. Where a task leaves a choice open, the common readings are listed with what each computes; pick one deliberately and say which.

## 1. Units and shifts

One basis point is 0.0001, so 100 bp is 0.01. Build every shift as a float array and check its extreme values before repricing.

```python
import numpy as np
bp = 1e-4
T = np.arange(1, 11)                                   # integer maturities: an int array
shift = np.full(T.shape, 100 * bp, dtype=float)        # dtype=float, or full_like(T, ...) truncates to 0
tilt = np.interp(T, [2, 10], [25 * bp, -25 * bp])      # linear between key points, flat outside
assert shift.dtype == float and np.allclose(shift, 0.01)
assert np.isclose(tilt.max(), 0.0025) and np.isclose(tilt.min(), -0.0025)
```

Before repricing any scenario, check the shock itself and the direction of the result. `np.full_like(template, value)` and slice assignment `arr[:] = value` keep the template's dtype, so an integer maturity array turns a 0.01 shift into 0 with no error. Positive cash flows lose value when every rate rises.

```python
def check_scenario(shift, pv, base_curve):
    shift = np.asarray(shift)
    assert shift.dtype.kind == "f" and np.abs(shift).max() > 0       # float and non-zero
    return pv(base_curve + shift)
up = np.full(T.shape, 100 * bp, dtype=float)
pv = lambda z: np.sum(5.0 * np.exp(-z * T)) + 100 * np.exp(-z[-1] * T[-1])
z0 = np.full(T.shape, 0.03)
assert check_scenario(up, pv, z0) < pv(z0) < check_scenario(-up, pv, z0)
```

## 2. Rates from discount factors

Continuous zero rate z(t) = -ln P(t) / t. Continuous forward over (t1, t2]: ln(P(t1)/P(t2)) / (t2 - t1). Simple forward: (P(t1)/P(t2) - 1) / accrual.

A forward column with one row per maturity T has two readings that give different numbers:
- A: the period ending at T, (T_prev, T], where the first row uses P(0) = 1 and equals z of the first maturity.
- B: the period starting at T, (T, T_next], so the last row needs a factor beyond the curve.

With one row per maturity and no reading stated in the task, A (the period ending at T) is the usual one: it needs no point beyond the curve and fills every row. B leaves the last row undefined unless the task supplies or prescribes an extension.

If the chosen reading leaves a required cell empty, decide how to fill it (the other reading or a stated extrapolation) instead of writing NaN.

```python
P = np.exp(-0.04 * T)
z = -np.log(P) / T
Pe, Te = np.r_[1.0, P], np.r_[0.0, T]
f_end = np.log(Pe[:-1] / Pe[1:]) / np.diff(Te)         # reading A
f_start = np.full(T.shape, np.nan)
f_start[:-1] = np.log(P[:-1] / P[1:]) / np.diff(T)     # reading B
assert np.isclose(f_end[0], z[0]) and np.isnan(f_start[-1])
```

## 3. Bootstrapping par quotes

Price each par instrument on its full coupon schedule, not only on the supplied maturities. A coupon date between two knots takes its factor from the interpolant, so the new knot appears on both sides and must be solved with a 1-D root finder (see bootstrap_immunization). A par instrument shorter than one coupon period pays once: P(T) = 1 / (1 + y T).

With a non-local interpolant (cubic spline), two readings: (a) solve knots in order with a local rule for in-between dates, then fit the spline through the knots; (b) solve all knots jointly so the final spline reprices every quote. Always reprice every quote from the final curve on its full schedule. Zero rates tens of bp away from par yields on a gently sloped curve usually mean coupons were skipped.

## 4. Swaps

Fixed leg PV = N k Σ α_i P_d(t_i) with the fixed-leg day count and frequency. Float leg PV = N Σ α_j F_j P_d(s_j), F_j = (Q(s_{j-1})/Q(s_j) - 1)/α_j, with the float-leg day count. Discount factors P_d come from the discount (collateral) curve; forwards come from the projection curve Q. Build the discount curve first, then solve the projection curve with the discount curve held fixed. Payer (pay fixed) = float - fixed.

A compounded overnight leg on the discount curve itself has PV = P(s_0) - P(s_n), so its par rate is (P(s_0) - P(s_n)) / Σ α_i P(t_i); a single-payment pillar gives P(e) = P(s) / (1 + r α). For spot-starting quotes, two anchors: curve time from the valuation date with P(v) = 1 and P(s_0) < 1, or P(s_0) = 1 at the start date. They differ by the factor from v to s_0.

FX spot settles on the spot date s_0, so covered parity compares the two currencies over the same period from s_0 to delivery T: F(T) = S · P_f(s_0, T) / P_d(s_0, T). Some references write the spot value date as v; here v is the valuation date. With curves anchored at the valuation date, P_c(s_0, T) = P_c(v, T) / P_c(v, s_0). Using P_c(v, T) directly multiplies the forward by P_f(v, s_0) / P_d(v, s_0), which is not one when the two currencies' overnight rates or day counts differ. An implied basis annualised from the same forward uses a year fraction over the same period [s_0, T].

```python
def cip_forward(S, Pf, Pd, s0, T):                      # Pf, Pd: discount functions with P(v) = 1
    return S * (Pf(T) / Pf(s0)) / (Pd(T) / Pd(s0))
```

```python
from scipy.optimize import brentq
kt, kg = [0.0], [0.0]                                  # knot times from the valuation date, g = -ln P
def Pd(t):
    t = np.atleast_1d(np.asarray(t, float))
    z_last = kg[-1] / kt[-1] if kt[-1] > 0 else 0.0     # flat zero rate beyond the last knot
    return np.exp(-np.where(t <= kt[-1], np.interp(t, kt, kg), z_last * t))
def par_ois(s0, pay, alpha):
    return (Pd(s0)[0] - Pd(pay[-1])[0]) / np.sum(alpha * Pd(pay))
for s0, pay, alpha, quote in ois_quotes:               # sorted by final payment date
    def err(g):
        kt.append(pay[-1]); kg.append(g)
        e = par_ois(s0, pay, alpha) - quote
        kt.pop(); kg.pop()
        return e
    g_new = brentq(err, -1.0, 5.0)
    kt.append(pay[-1]); kg.append(g_new)
assert max(abs(par_ois(*q[:3]) - q[3]) for q in ois_quotes) < 1e-12
```

The value at a later date T0 of a payer swap paying fixed K per unit notional is 1 - Σ c_i P(T0, t_i) with c_i = K α_i and c_n = 1 + K α_n: the final principal is part of the coupon bond. At time 0 the same expression with P(0, ·) is P(0, T0) - Σ c_i P(0, t_i), which is zero at the at-the-money rate.

## 5. Fixing a supplied pricing script

Read the whole file once, then list per function: day count, frequency, which curve each call receives, sign, build order and output path, against the convention contract. Write edits to a new writable file by exact text replacement and confirm each replacement matched. Keep the output directory the task names. After each run, reprice every input quote and look at the worst residual.

## 6. Task wording → API arguments

Arguments that silently change results, with the task phrases they usually answer to.

- `scipy.optimize.brentq(f, a, b, xtol=2e-12, rtol=8.9e-16, maxiter=100)`: "solve on the interval [lo, hi]" means a = lo, b = hi; f(a) and f(b) must differ in sign or it raises ValueError. Widen a bracket only when the task fixes none. xtol is absolute, so the default suits rates; a non-converged run raises RuntimeError.
- `scipy.optimize.newton(func, x0, fprime=None, tol=1.48e-8, maxiter=50)`: "starting from" gives x0. Without fprime it runs the secant method; with fprime, Newton. It has no bracket and can leave the economic range, so check the root.
- `scipy.optimize.least_squares(fun, x0, bounds=(-inf, inf), loss='linear', ftol=xtol=gtol=1e-8)`: "least squares" or "squared errors" is loss='linear'; 'soft_l1' or 'huber' answer "robust". fun returns the residual vector, not its square.
- `scipy.optimize.minimize(fun, x0, method, bounds, constraints, options)`: name the method the task names. L-BFGS-B takes options ftol, gtol, maxiter; SLSQP takes ftol and maxiter (default 100). "Positive parameter" is a bound (small epsilon, None). Read res.success and res.message; "retry with a looser tolerance" means a second call.
- `numpy.interp(x, xp, fp, left=None, right=None)`: xp must increase; outside the range it returns the end values of fp. The interpolated quantity is the argument fp: "log-linear in discount factors" means fp = ln P; "linear in zero rates" means fp = z; "linear in g(T) = -ln P" means fp = g. Flat ln P beyond the end is a zero forward, not a flat zero rate; "flat zero-rate extrapolation" means extending z, so P = exp(-z_end t).
- `scipy.interpolate.interp1d(x, y, kind='linear', fill_value=...)`: fill_value='extrapolate' continues the last segment's slope; that is a stated extrapolation choice.
- `scipy.interpolate.CubicSpline(x, y, bc_type='not-a-knot')`: "not-a-knot" is the default; "natural" is bc_type='natural'; "clamped" fixes the end slopes. A task point such as g(0) = 0 must be passed as a node, and adding it changes the whole spline. `.derivative()(t)` of g gives the instantaneous forward.
- Day counts have no library default; write each one. ACT/360 = days/360; ACT/365F = days/365; ACT/365.25 = days/365.25. 30/360 variants differ at month ends: Bond Basis sets D1 = 30 if D1 = 31, and D2 = 30 if D2 = 31 and D1 >= 30; 30/360 US also treats the last day of February as 30; 30E/360 caps both days at 30. "Time in years ACT/365" is the curve coordinate for discounting; the accrual day count only sizes the coupon.
- Schedules: "generated backward from maturity" steps months back from the maturity date; "unadjusted" means no business-day roll. Month arithmetic (`pandas.DateOffset(months=n)`, `dateutil.relativedelta`) clips the 31st to the month end.

## Sources

Hull, Options, Futures, and Other Derivatives, 9th ed., ch. 4 (interest rates), ch. 7 (swaps), ch. 9 (OIS discounting); Ametrano & Bianchetti (2013), Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping, SSRN 2219548, sec. 2-4; Hagan & West (2006), Interpolation Methods for Curve Construction, Applied Mathematical Finance 13(2), sec. 2-3; Andersen & Piterbarg, Interest Rate Modeling vol. 1 (2010), ch. 5-6; ISDA 2006 Definitions sec. 4.16 (day count fractions); SciPy 1.x reference pages for optimize.brentq, optimize.newton, optimize.least_squares, optimize.minimize (L-BFGS-B, SLSQP), interpolate.interp1d, interpolate.CubicSpline; NumPy reference for numpy.interp and numpy.full.
