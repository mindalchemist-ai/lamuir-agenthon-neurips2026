# Discount curves, projection curves and interest-rate cash flows

This reference explains the valuation of deposits, fixed and floating swap legs, and curve sensitivities when discounting and rate projection use different curves. It also covers the single-curve limit and the dependence of bootstrapping on interpolation. It does not specify market calendars, quote corrections or a universal currency convention.

## 1. Shared Foundations

Map the task's notation to economic quantities and units. Explicit definitions of accrual, curve time, settlement and shocks take precedence. If requirements conflict, state the ambiguity and interpretation; do not infer conventions from a currency or field name alone.

Let v be the valuation date and $\operatorname{P}_{d}$(v,t) the discount factor for a payment at t, under the chosen collateral/funding convention. $Q_{x}$(v,t) is a positive projection-curve parameter for index tenor x; it need not be a tradable zero-coupon bond price. N denotes notional, k a fixed coupon rate, and b a spread, all rates in decimals. A basis point of rate is 0.0001. The curve coordinate u(t) is a year fraction measured from v; coupon accrual fractions are separate quantities.

For a positive discount factor and $u(t)>0$, the continuously compounded zero rate is:

$$
\begin{gathered}
z_{d}(t) = -\ln (\operatorname{P}_{d}(v,t))/u(t) \\
\operatorname{P}_{d}(v,v) = 1
\end{gathered}
$$

Positive discount factors need not decrease with maturity when forward rates can be negative. At $u=0$ a quoted zero rate requires a limiting or short-end convention; the logarithmic quotient is undefined.

## 2. Rate projection and known fixings

For a simple rate accruing from a to c with index accrual $\delta _{x}$(a,c), the projection-curve definition is:

$$
F_{x}(v;a,c) = (Q_{x}(v,a)/Q_{x}(v,c)-1)/\delta _{x}(a,c)
$$

The reverse relation recovers an end-date projection factor from a forward quote and a known start-date factor.

$$
Q_{x}(v,c) = Q_{x}(v,a)/(1+\delta _{x}(a,c)\cdot F_{x}(v;a,c))
$$

The denominator must be positive. A simple deposit discount identity uses the same algebra only when the quoted instrument's start/end values and relevant curve justify it. At $a=v$, the start factor is one. A spot-starting instrument has a later start date, so setting its start factor to one is a distinct assumption.

For an already fixed coupon, its rate is the contractual fixing, not the forward currently implied by the curve. If fixing is still ahead, $F_{x}$ denotes the model's projected rate appropriate to that payment. In a full stochastic multiple-curve model, measure changes may require adjustments; the curve-ratio formula alone is not a universal expectation under every measure. The conventional cash-flow framework separates projection from discounting [1].

## 3. Fixed and floating leg values

For fixed payments on dates $t_{i}$ with fixed-leg accrual fractions $\alpha _{i}$, the discounted annuity per unit notional is:

$$
A_{d} = \sum _{i} \alpha _{i}\cdot \operatorname{P}_{d}(v,t_{i})
$$

For a constant fixed coupon k, the fixed-leg value before assigning the holder's receive/pay sign is:

$$
\mathrm{PV}_{\mathrm{fixed}} = N\cdot k\cdot A_{d}
$$

For floating accrual intervals ($a_{j}$,$c_{j}$), payment dates $p_{j}$, accrual fractions $\delta _{j}$ and rates $H_{j}$ (known fixings or projected rates), the floating-leg value before assigning the holder's receive/pay sign is:

$$
\mathrm{PV}_{\mathrm{float}} = N\cdot \sum _{j} \delta _{j}\cdot (H_{j}+b)\cdot \operatorname{P}_{d}(v,p_{j})
$$

The two legs may use different accrual bases, frequencies and dates. Payment lag changes the discount date, not the accrual interval. Principal exchanges, amortization and accrued-interest treatment are contractual additions; an ordinary fixed-for-floating swap does not acquire principal exchanges merely because a bond representation is useful.

From the holder's perspective, paying fixed and receiving floating gives:

$$
\begin{gathered}
V_{\mathrm{pay},\mathrm{fixed}} = \mathrm{PV}_{\mathrm{float}}-\mathrm{PV}_{\mathrm{fixed}} \\
V_{\mathrm{receive},\mathrm{fixed}} = -V_{\mathrm{pay},\mathrm{fixed}}
\end{gathered}
$$

The par fixed rate sets this value to zero, assuming a nonzero annuity and the floating-leg spread already included.

$$
k_{\mathrm{par}} = \mathrm{PV}_{\mathrm{float}}/(N\cdot A_{d})
$$

In the single-curve case only, with $Q_{x}=\operatorname{P}_{d}$, consecutive accrual intervals, payment at each interval end and no floating spread, algebra makes the floating coupons telescope:

$$
\mathrm{PV}_{\mathrm{float}} = N\cdot (\operatorname{P}_{d}(v,a_{1})-\operatorname{P}_{d}(v,c_{\mathrm{last}}))
$$

Using this expression with distinct curves, historical off-market fixings, payment lag or nonconcatenating intervals generally changes the valuation.

## 4. Overnight coupons and product definitions

An overnight compounded coupon over observations l, with annualized overnight fixings $r_l$ published daily and accrual fractions $d_l$ (for example, elapsed days divided by 360), has a realized accumulation factor [2]. Nonbusiness days may enter through a multi-day $d_{l}$; observation shifts and lookbacks are contract-specific.

$$
\begin{gathered}
G_{\mathrm{ON}} = \prod _{l} (1+r_{l}\cdot d_{l}) \\
\mathrm{coupon}_{\mathrm{ON}} = N\cdot (G_{\mathrm{ON}}-1)
\end{gathered}
$$

The equivalent simple coupon rate over an accrual $\delta$ is:

$$
R_{\mathrm{ON}} = (G_{\mathrm{ON}}-1)/\delta
$$

An arithmetic overnight average is another payoff. A simple single-payment instrument can be defined instead of a compounded OIS; its stated payoff determines its pricing equation. The word OIS by itself does not make every quoted pillar a deposit or impose one fixed accrual schedule. Adding a contractual spread outside compounding differs from compounding the spread with each daily rate.

## 5. Interpolation and calibration equations

A curve fitted to quotes must value every instrument with its contractual cash flows and the same interpolant. Let $\theta$ contain curve parameters, $q_{j}$ a market quote and $\mathrm{model}_{\mathrm{quote},j}$ the corresponding par rate or price. Exact calibration requires:

$$
\mathrm{model}_{\mathrm{quote},j}(\theta ) = q_{j}
$$

For a par coupon bond with unit redemption at $T_{n}$, coupons $c\alpha_j$, and payment dates on already determined knots except for the final date, the last factor solves:

$$
\operatorname{P}_{d}(v,T_{n}) = (1-c\cdot \sum _{j<n} \alpha _{j}\cdot \operatorname{P}_{d}(v,t_{j}))/(1+c\cdot \alpha _{n})
$$

If earlier coupon dates lie between the previous and new knots, their interpolated factors may depend on the new unknown. The equation is then implicit. A nonlocal interpolant can also change earlier intervals when later knots are added; fitting one knot at a time does not by itself establish final repricing.

For two knots $u_{a}<u_{b}$ and weight $w=(u-u_{a})/(u_{b}-u_{a})$, interpolation linear in log discount factors gives:

$$
\ln (\operatorname{P}_{d}(u)) = (1-w)\cdot \ln (\operatorname{P}_{d}(u_{a}))+w\cdot \ln (\operatorname{P}_{d}(u_{b}))
$$

Interpolation linear in continuous zero rates gives a different curve:

$$
\begin{gathered}
z_{d}(u) = (1-w)\cdot z_{d}(u_{a})+w\cdot z_{d}(u_{b}) \\
\operatorname{P}_{d}(u) = \exp (-u\cdot z_{d}(u))
\end{gathered}
$$

The first has a constant instantaneous forward on each interval. A spline applied to the exponent $g(u)=u\cdot z_{d}(u)$ is yet another choice. Positivity of factors, calibration and local shape are separate properties; a smooth interpolant does not guarantee nonnegative forwards.

The continuously compounded average forward over a curve-coordinate interval is:

$$
f_{\mathrm{average}}(a,c) = \ln (\operatorname{P}_{d}(v,a)/\operatorname{P}_{d}(v,c))/(u(c)-u(a))
$$

This is not the instantaneous forward except in a constant-forward interval. The instantaneous forward, where differentiable, is:

$$
f_{\mathrm{instant}}(u) = -d \ln (\operatorname{P}_{d}(u))/\mathrm{d}u
$$

## 6. Risk definitions and checks

Let $V(\theta)$ be value and e specify the shocked curve/risk factor. The central sensitivity to an absolute rate change h is:

$$
\mathrm{d}V_{\mathrm{dtheta},e} \approx  (V(\theta +h\cdot e)-V(\theta -h\cdot e))/(2\cdot h)
$$

The signed change for a positive one-basis-point bump is distinct from a derivative or its absolute value:

$$
\mathrm{change}_{\mathrm{up},1\mathrm{bp}} = V(\theta +0.0001\cdot e)-V(\theta )
$$

A projection-zero shock at coordinate u changes $Q_{x}$ by a factor $\exp (-h\cdot u)$ while an unshocked discount curve stays fixed. A market-quote shock instead changes an input quote and recalibrates affected curves. These are different risks, and recalibration may change multiple parameters. Risk terminology alone does not identify the shock definition.

Useful identities are zero PV at the par fixed rate, opposite signs for opposite swap positions, single-curve telescoping under its conditions, and recovery of the original forward after converting to factor ratios and back. Repricing checks must include earlier quotes when a nonlocal interpolant changes. Small residuals do not validate a wrong day-count or cash-flow model.

This reference does not cover stochastic basis calibration, caplet volatility stripping, FX-reset notionals, or historical short-rate estimation. LIBOR is an index label in historical models here, not a recommendation for a present-day trading convention.

When a task defines a swap's NPV from the perspective of the fixed payer or receiver → compute it from the two leg values by that direction and check its sign:

```python
value = (pv_float - pv_fixed) if payer else (pv_fixed - pv_float)      # payer: pays fixed, receives floating
assert (value > 0) == ((pv_float > pv_fixed) == payer)
```

A provided script that computes the NPV another way is checked against this before its output is used.

When curves are bootstrapped from quotes (by your code or a provided script) → reprice every input instrument on the finished curves and stop on any residual above the task's stated tolerance (without one, report the residuals and fix only clear errors); a nonzero residual means a remaining error in the bootstrap (pillar dates, day count, which curve discounts, the order the curves are built in):

```python
worst = max(abs(model_rate(q) - q.rate) for q in quotes) * 1e4      # in basis points, the unit of the check
assert worst < tolerance_bp, f"input quotes do not reprice: {worst:.3g} bp"   # the tolerance the task states
```

## References

[1] Ametrano and Bianchetti (2009), Bootstrapping the Illiquidity: Multiple Yield Curves Construction for Market Coherent Forward Rates Estimation, Sections 2–5. [Author manuscript](https://www.bianchetti.org/finance/bootstrappingtheilliquidity-v1.0.pdf). Bianchetti (2009), Two Curves, One Price, distinguishes forwarding/discounting measures and possible quanto adjustments. [Author paper](https://arxiv.org/abs/0905.2770).

[2] Alternative Reference Rates Committee (2019), A User's Guide to SOFR, discussion of simple versus compound averaging. [Official guide hosted by the New York Fed](https://www.newyorkfed.org/medialibrary/Microsites/arrc/files/2019/Users_Guide_to_SOFR.pdf). Actual contractual calendars and accrual conventions govern a trade.
