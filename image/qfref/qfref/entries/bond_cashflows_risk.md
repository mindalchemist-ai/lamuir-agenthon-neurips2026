# Bond cashflows, curve sensitivities and liability hedging

Use this reference for coupon-bond valuation, yield versus curve duration, key-rate risk and cashflow immunization. It also distinguishes fixed coupons, known floating coupons and callable cashflows. It does not specify a stochastic callable-bond model or a statistical factor-estimation method.

Map notation to the contract before applying a formula. Explicit definitions of rates, price basis, day counts, risk shocks and holding conventions govern the calculation; a familiar label alone does not determine them. Rates below are decimals, times are years, and one basis point is 0.0001.

## 1. Cashflow value and price basis

Let F be principal, $C_{j}$ an entitled payment at date $t_{j}$ after valuation, and $\operatorname{P}_d(t_j)$ its discount factor. Dates used for discounting and accrual can have different year fractions. Already paid coupons do not belong to the remaining cashflow stream. Settlement-date entitlement, ex-coupon treatment and business-day adjustments follow the contract.

Present value of the remaining payments, on a full-price basis:

$$
\operatorname{P}_{\mathrm{dirty}} = \sum _{j} C_{j} \cdot  \operatorname{P}_{d}(t_{j})
$$

A fixed coupon with contractual accrual $\alpha _{j}$ and annual rate c:

$$
\mathrm{coupon}_{j} = F \cdot  c \cdot  \alpha _{j}
$$

The principal redemption is an additional payment, including when a coupon is paid on the same date. For regular k-times-yearly equal coupons, $\alpha _{j} = 1/k$; this is not a universal stub convention.

Accrued interest for a simple accrual convention, with $\alpha _{\mathrm{elapsed}}$ measured from the coupon-period start to settlement:

$$
\mathrm{AI} = F \cdot  c \cdot  \alpha _{\mathrm{elapsed}}
$$

Clean-price quotation (cash settlement uses the dirty price, $P_{\mathrm{dirty}}=P_{\mathrm{clean}}+\mathrm{AI}$):

$$
\operatorname{P}_{\mathrm{clean}} = \operatorname{P}_{\mathrm{dirty}} - \mathrm{AI}
$$

For conventions based on a fraction of a scheduled coupon, AI is that coupon times the specified elapsed/full-period fraction. These conventions coincide only with compatible accrual definitions. Face scaling must be consistent for price, cashflow, AI and risk.

## 2. Curve calibration and rates

A par coupon quote is not a zero rate. For a unit-principal par instrument with coupon accruals $\alpha _{j}$, rate $c_{n}$ and redemption at $t_{n}$, its cashflows imply the following equation [1].

Par-price constraint:

$$
1 = c_{n} \cdot  \sum _{j=1}^{n} \alpha _{j} \cdot  \operatorname{P}_{d}(t_{j}) + \operatorname{P}_{d}(t_{n})
$$

Terminal factor when all earlier coupon factors are already known:

$$
\operatorname{P}_{d}(t_{n}) = (1 - c_{n} \cdot  \sum _{j<n} \alpha _{j} \cdot  \operatorname{P}_{d}(t_{j})) / (1 + c_{n} \cdot  \alpha _{n})
$$

For a general bond, terminal-factor recovery uses its dirty price and final total cashflow:

$$
\operatorname{P}_{d}(t_{n}) = (\operatorname{P}_{\mathrm{dirty}} - \sum _{j<n} C_{j} \cdot  \operatorname{P}_{d}(t_{j})) / C_{n}
$$

When intermediate coupon discounts depend on an unknown curve node through interpolation, that node enters the whole price equation. A nonlocal interpolant can also change previously priced maturities. The final curve, not just each provisional step, must satisfy the calibration equations. An exact fit requires a compatible instrument/node specification; an overdetermined fit may instead have residuals. Interpolation of zero rates, log discounts or discounts defines different curves [1].

Continuously compounded zero rate and exponent g, for $t > 0$:

$$
z(t) = -\ln (\operatorname{P}_{d}(t)) / t
$$

$$
g(t) = t \cdot  z(t) = -\ln (\operatorname{P}_{d}(t))
$$

At the valuation origin $\operatorname{P}_{d}(0)=1$ and $g(0)=0$. Positive discounts are required; negative rates can make discounts increase, so monotonic decrease is not a universal no-arbitrage test.

Average continuous forward over a nonzero interval:

$$
f_{\mathrm{avg}}(a,b) = (g(b) - g(a)) / (b-a)
$$

Instantaneous forward, where the curve is differentiable:

$$
f_{\mathrm{inst}}(t) = \mathrm{d}g(t)/\mathrm{d}t
$$

A simple forward for accrual $\delta$, distinct from the continuous average:

$$
F_{\mathrm{simple}}(a,b) = (\operatorname{P}_{d}(a)/\operatorname{P}_{d}(b) - 1) / \delta
$$

This single-curve relation does not replace a separate projection curve when one is specified. A zero-coupon claim has $\operatorname{P}_{d}=\operatorname{P}_{\mathrm{dirty}}/F$. A simple deposit quote R gives $\operatorname{P}_{d}=1/(1+R\cdot \delta )$, whereas a bank-discount quote d gives $\operatorname{P}_{d}=1-d\cdot \delta$; they are different quote conventions.

## 3. Yield-based versus curve-based risk

For fixed positive cashflows, a k-periodic yield y satisfies the following pricing relation under a fractional-period convention. Other market yield conventions may treat stubs differently. Its domain is $1+y/k > 0$; a yield need not be positive.

Yield price:

$$
\operatorname{P}(y) = \sum _{j} C_{j} \cdot  (1+y/k)^{-k\cdot t_{j}}
$$

Yield-weighted Macaulay duration:

$$
D_{\mathrm{Mac}} = \sum _{j} t_{j} \cdot  C_{j} \cdot  (1+y/k)^{-k\cdot t_{j}} / \operatorname{P}(y)
$$

Modified duration, the normalized negative yield derivative:

$$
D_{\mathrm{mod}} = D_{\mathrm{Mac}} / (1+y/k) = -(\mathrm{d}P/\mathrm{d}y)/\operatorname{P}
$$

Yield convexity, the normalized second derivative:

$$
\mathrm{Conv}_{y} = \sum _{j} C_{j} \cdot  t_{j} \cdot  (t_{j}+1/k) \cdot  (1+y/k)^{-k\cdot t_{j}-2} / \operatorname{P}
$$

If a definition instead weights times using the calibrated curve, it produces a curve-weighted duration. Dividing that quantity by 1+y/k is not generally the actual yield derivative; retain the stated definition without confusing it with the derivative identity.

Fisher–Weil duration for a parallel additive shift of continuous zero rates and fixed cashflows:

$$
D_{\mathrm{FW}} = \sum _{j} t_{j} \cdot  C_{j} \cdot  \operatorname{P}_{d}(t_{j}) / \operatorname{P}_{\mathrm{dirty}}
$$

Convexity for the same continuous-zero shift:

$$
\mathrm{Conv}_{\mathrm{FW}} = \sum _{j} t_{j}^{2} \cdot  C_{j} \cdot  \operatorname{P}_{d}(t_{j}) / \operatorname{P}_{\mathrm{dirty}}
$$

A zero-coupon claim has $D_{\mathrm{FW}}$ equal to its payment time. Continuously compounded yield duration has this same weighted-time form with yield discounting.

Price effect of a small scalar rate shock h, with D and Conv defined for that same shock:

$$
\Delta _{\operatorname{P}} = -\operatorname{P} \cdot  D \cdot  h + 0.5 \cdot  \operatorname{P} \cdot  \mathrm{Conv} \cdot  h^{2} + \mathrm{higher}_{\mathrm{order},\mathrm{terms}}
$$

Positive-loss DV01 convention for a positive-duration long position [2]:

$$
\mathrm{DV01} = \operatorname{P} \cdot  D \cdot  0.0001
$$

The signed first-order price change for an upward basis point is -DV01. A signed-PV01 convention may use that negative quantity instead.

For prices $\operatorname{P}_{\mathrm{minus}}$ and $\operatorname{P}_{\mathrm{plus}}$ revalued under negative/positive h shocks, effective duration is:

$$
D_{\mathrm{eff}} = (\operatorname{P}_{\mathrm{minus}} - \operatorname{P}_{\mathrm{plus}}) / (2\cdot h\cdot \operatorname{P}_{\mathrm{base}})
$$

Effective convexity under the same repricing convention:

$$
\mathrm{Conv}_{\mathrm{eff}} = (\operatorname{P}_{\mathrm{minus}} + \operatorname{P}_{\mathrm{plus}} - 2\cdot \operatorname{P}_{\mathrm{base}}) / (h^{2}\cdot \operatorname{P}_{\mathrm{base}})
$$

Callable or floating cashflows may change under the shock, so fixed-cashflow duration is not their effective duration. At a switching point, finite-difference risk can depend materially on h.

## 4. Key rates, quote risk and spread risk

A key-rate direction $b_{m}$(t) describes how a continuous-zero curve changes for unit shock h in bucket m. Local triangular profiles, isolated node changes and market-quote changes followed by recalibration are distinct definitions. An isolated node bump affects other times only through the chosen interpolation; it is not automatically a triangular bump.

Directional key-rate duration for fixed cashflows:

$$
\mathrm{KRD}_{m} = \sum _{j} t_{j} \cdot  b_{m}(t_{j}) \cdot  C_{j} \cdot  \operatorname{P}_{d}(t_{j}) / \operatorname{P}
$$

Central-difference estimate for any specified bucket repricing:

$$
\mathrm{KRD}_{m}(h) = (\operatorname{P}_{\mathrm{minus},m} - \operatorname{P}_{\mathrm{plus},m}) / (2\cdot h\cdot \operatorname{P}_{\mathrm{base}})
$$

Forward-difference alternative when a one-sided sensitivity is defined:

$$
\mathrm{KRD}_{m,\mathrm{forward}}(h) = (\operatorname{P}_{\mathrm{base}} - \operatorname{P}_{\mathrm{plus},m}) / (h\cdot \operatorname{P}_{\mathrm{base}})
$$

When $\sum _{m} b_{m}(t)=1$ at every payment time, the derivative KRDs sum to $D_{\mathrm{FW}}$. Finite central differences differ by truncation terms; a subset of nodes or quote-recalibrated risks need not sum to a parallel-zero duration. Curve construction is part of a quote sensitivity, not a disposable preliminary step.

For quote vector q and calibrated zero-node vector z(q), chain-rule quote exposure:

$$
\mathrm{d}P/\mathrm{d}q = (\mathrm{d}P/\mathrm{d}z) \cdot  (\mathrm{d}z/\mathrm{d}q)
$$

These are row gradient and calibration Jacobian respectively. The formula includes all coupon/payment dependence in P. It does not imply that the calibration Jacobian is diagonal.

A constant continuous z-spread s is defined by a price equation:

$$
\operatorname{P}_{\mathrm{market}} = \sum _{j} C_{j} \cdot  \operatorname{P}_{d}(t_{j}) \cdot  \exp (-s\cdot t_{j})
$$

It is not an option-adjusted spread. For a price generated from the same curve and cashflows, $s=0$ solves the equation.

## 5. Floating and callable cashflows

For a floating coupon whose rate $H_{j}$ has already fixed, changing today's projection curve does not change $H_{j}$. For an unfixed coupon, $H_{j}$ is the contract's projected rate. With spread m, accrual $\alpha _{j}$ and principal F:

$$
\mathrm{coupon}_{j} = F \cdot  \alpha _{j} \cdot  (H_{j} + m)
$$

A par floater's short reset exposure is a consequence of resetting and compatible projection/discounting assumptions, not permission to replace every floater price by principal. Known next coupons, accrued interest, spreads, credit and basis can all matter.

For a deterministic assumed call date u with redemption $R_{u}$, the truncated cashflow value is:

$$
\operatorname{P}_{\mathrm{truncated}}(u) = \sum _{t_{j}\le u} \mathrm{coupon}_{j} \cdot  \operatorname{P}_{d}(t_{j}) + R_{u} \cdot  \operatorname{P}_{d}(u)
$$

This assumes the listed coupons include any coupon payable on exercise and $R_{u}$ excludes that coupon. Other redemption conventions change that accounting. A specified deterministic issuer-choice approximation takes the minimum of the no-call value and the allowed truncated values. It is not a general stochastic callable-bond valuation: a true issuer exercise decision is conditional on future information. Under nonnegative issuer-option value, the callable value cannot exceed the otherwise identical noncallable value.

## 6. Portfolio hedge and scenario meaning

Let $x_{i}$ be units, $\operatorname{P}_{i}$ price per unit and V the portfolio value. Current value weights $w_{i}$ differ from units and principal weights.

Value and current value weights:

$$
V = \sum _{i} x_{i} \cdot  \operatorname{P}_{i}
$$

$$
w_{i} = x_{i} \cdot  \operatorname{P}_{i} / V
$$

Portfolio exposure to a common normalized risk direction $\operatorname{E}_{i}$:

$$
\operatorname{E}_{\mathrm{portfolio}} = \sum _{i} w_{i} \cdot  \operatorname{E}_{i}
$$

For liability PV L and normalized exposure $\operatorname{E}_{L}$, exact value and dollar-exposure matching require:

$$
\sum _{i} x_{i} \cdot  \operatorname{P}_{i} = L
$$

$$
\sum _{i} x_{i} \cdot  \operatorname{P}_{i} \cdot  \operatorname{E}_{i} = L \cdot  \operatorname{E}_{L}
$$

Long-only feasibility requires the target normalized exposure vector to lie in the convex hull of the asset vectors; position bounds narrow that set. A solver termination flag alone does not establish financial feasibility.

For two assets with durations $D_{1} < D_{L} < D_{2}$, the value weight in the first asset is:

$$
w_{1} = (D_{2}-D_{L})/(D_{2}-D_{1})
$$

The second weight is $1-w_1$. A target outside this interval requires a short position for exact two-asset matching.

For matched value and first derivative, the local surplus after a parallel scalar shock h is:

$$
\mathrm{Surplus}(h) = 0.5 \cdot  L \cdot  (\mathrm{Conv}_{A}-\mathrm{Conv}_{L}) \cdot  h^{2} + \mathrm{higher}_{\mathrm{order},\mathrm{terms}}
$$

Greater asset convexity gives local protection under the stated shift, not a guarantee for arbitrary curve twists. For a single fixed liability at horizon H, nonnegative fixed asset payments matched in PV and Fisher–Weil duration have an additional global property for additive continuous-zero shifts: Jensen's inequality gives $\sum _{j} w_{j}\cdot \exp (-h\cdot t_{j}) \ge  \exp (-h\cdot H)$. Short weights invalidate this argument.

A frozen-unit portfolio drifts in value weights as prices change. Holding old weights fixed describes a different comparison convention. Scenario loss or gain must use the declared holding rule, remaining cashflows and a consistent liability valuation date. Passage of time, payments and financing are not themselves instantaneous rate shocks. Rebalancing can improve an objective without improving every scenario.

### Bounded hedge optimization and numerical scaling

Assume positive instrument prices $P_i$ and liability present value $L>0$. If $x_i$ are units and $d_i$ are currency allocations, budget-normalized weights satisfy:

$$
d_i=P_i x_i=Lw_i,\qquad x_i=\frac{Lw_i}{P_i}.
$$

Under exact value matching, $\sum_i w_i=1$. A row of normalized asset exposures $E_{j,i}$ matches liability exposure $e^L_j$ through $\sum_i E_{j,i}w_i=e^L_j$. In units the same constraint is $\sum_i E_{j,i}P_i x_i=Le^L_j$; these are not interchangeable without their price and value factors.

Some risks are exact constraints; others are an objective. For exposure matrix $E$, positive diagonal residual weights $W$, chosen target $e^L$, reference allocation $w_{\mathrm{ref}}$ and penalty $\lambda\ge0$, a convex example is:

$$
\min_w\ \frac12\lVert W(Ew-e^L)\rVert_2^2+
\frac\lambda2\lVert w-w_{\mathrm{ref}}\rVert_2^2,
\qquad Aw=b,\quad l\le w\le u.
$$

The rows of $A$ contain exact budget or risk restrictions. The objective does not promise zero residual when matching is infeasible. The problem's specified risk weights and penalty govern the trade-off; no universal weight combines duration, PCA and stress risk. This quadratic form presumes those exposures are fixed linear functions of allocation. Nonlinear costs or position-dependent repricing require their own objective.

Its gradient uses:

$$
H=E'W'WE+\lambda I,\quad
f=-E'W'We^L-\lambda w_{\mathrm{ref}},\quad
\nabla F(w)=Hw+f.
$$

The Hessian is positive semidefinite; positive definiteness gives at most one minimizer on a nonempty convex feasible set. A pseudoinverse alone does not impose bounds. For finite bounds, KKT diagnostics at a candidate use equality multiplier $\nu$ and nonnegative lower/upper multipliers $\eta,\zeta$:

$$
Hw+f+A'\nu-\eta+\zeta=0,\qquad
\eta_i(w_i-l_i)=0,\qquad
\zeta_i(u_i-w_i)=0.
$$

Together with feasibility and dual nonnegativity these certify optimality for this convex problem. Dependent equalities can make multipliers nonunique. Do not manufacture multipliers or claim a certificate from a solver status alone.

Scaling an equality row and its right side by the same nonzero factor preserves exact feasibility. Positive row scales chosen from meaningful units can prevent large monetary constraints dominating small normalized risks in stopping criteria. Changing $W$ instead changes the objective. Check feasibility back in original units, including budget, bounds and every risk residual. If allocations use negative or zero prices, or the budget denominator vanishes, the normalized-weight interpretation above is unavailable.

For SLSQP, a small objective change or a success flag alone does not establish economic matching; compare constraint residuals, objective and termination reason. Its tolerance controls several numerical conditions, not one financial error in isolation. A feasible starting allocation helps but does not make an infeasible target attainable.

Source: [SciPy SLSQP documentation](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html) for solver stopping and result semantics. The matrices, gradient and KKT relations here are derived from the displayed convex quadratic.

## 7. Scope and sources

The identities for duration, convexity, risk matching and Jensen protection follow by differentiating discounted cashflows; their assumptions are stated locally. Full day-count calendars, curve-factor estimation, credit/default models and stochastic exercise models require their own specifications.

[1] Hagan and West (2006), Interpolation Methods for Curve Construction, pp. 90–93: calibration and interpolation dependence. [Paper](https://bank.uni-hohenheim.de/uploads/media/Hagan_and_West__2006__-_Interpolation_Methods_for_Curve_Construction.pdf).

[2] CME Group, How Can You Measure Risk in Treasuries?: DV01 and modified-duration units. [CME explanation](https://www.cmegroup.com/education/courses/introduction-to-treasuries/how-can-you-measure-risk-in-treasuries).

[3] U.S. Treasury, Buying a Treasury Marketable Security: accrued interest is part of the amount paid and recovered in a subsequent coupon. [Treasury explanation](https://www.treasurydirect.gov/marketable-securities/buying-a-marketable-security/). This does not prescribe the accrual convention of a different instrument.
