# Hull-White one-factor short-rate model (extended Vasicek): bonds, bond options, caps, Jamshidian swaptions, trinomial tree

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Implementation checks (read before coding)

Curve: add the point (0, 1) to the discount-curve interpolant (internal only) before using the closed forms, and take the instantaneous forward from the same interpolant. When the task names no interpolant, common choices are linear in continuously compounded zero rates (forwards continuous inside each segment) and linear in log discount factors (piecewise-flat forwards); they give prices that differ by a few basis points at dates between curve nodes. Whichever is chosen, build one curve function and use it in every step: the calibration objective, the reported model prices, the tree fit and the analytic (Jamshidian) prices. If the interpolant is changed after calibrating, calibrate again and recompute everything downstream; parameters fitted on one curve and prices reported on another give calibration residuals that grow with maturity and tree-versus-analytic mismatches. Check: recompute the reported caplet prices from the final curve function and the final (a, σ) and confirm they equal the prices the optimiser minimised. The model bond price at time zero, with the short rate at the time-zero forward, then reproduces every market discount factor exactly for any mean reversion and volatility. A residual in that check is a curve-construction error, not a parameter effect; a constant relative error at every maturity points at a curve whose value at time zero is not one. The point (0, 1) is not a market quote: a curve table written as an output keeps the input maturities as its rows, in their order, so build that table from the input rows, not from the interpolant's knots. Every row needs a finite forward: at the last maturity a forward difference has no next point, so take the forward from the interpolant's last segment (with log-linear discount factors, the flat forward of the last interval), not a blank or NaN.

Jamshidian's critical rate: the coupon-bond value is strictly decreasing in the short rate, so bracket the rate wide (for example from −100 % to +100 %), check that the two ends give opposite signs, and solve with a bracketing routine that has an iteration cap (`scipy.optimize.brentq` with `maxiter`, or a fixed count of about sixty halvings). Never loop until a residual or an interval width falls below a tolerance without a cap: once the width reaches the floating-point spacing of the rate the interval stops shrinking, and a mis-signed update never reaches the tolerance. Bound any per-step drift solve in a tree the same way; the Arrow–Debreu shift has a closed form and needs no iteration.

An exercise boundary marks nodes where the exercise value is positive and at least the continuation value; where both are zero (deep out of the money) the node is not an exercise node, so a test written as `exercise >= continuation` alone marks the whole bottom of the tree.

Value and payoff arrays on the tree hold floats: create them with `np.zeros(n_nodes)`, not `np.zeros_like(j)` when `j` is the integer node-index array, which keeps the integer dtype and truncates every assigned price to 0. For a co-terminal Bermudan swaption the exercise schedule begins at the option expiry (index zero) and ends one coupon period before the final payment. The payment dates start one period after the expiry, so slicing them (all but the last) gives a schedule that starts one period late and misses the expiry; build the exercise dates from the expiry instead.

```python
exercise_dates = [T0 + k * delta for k in range(n_payments)]     # T0, T0 + delta, ..., Tn - delta
assert abs(exercise_dates[0] - T0) < 1e-12 and abs(exercise_dates[-1] - (Tn - delta)) < 1e-12
assert len(exercise_dates) == n_payments                            # one exercise date per coupon period
```

Trinomial tree as arrays: per node one probability triple and one triple of target indices (edge rows use their up- or down-branching targets). Each forward Arrow–Debreu step adds the origin-discounted mass into the targets with an indexed add (`np.add.at`); each backward step is the discount at the origin node times a probability-weighted gather; at an exercise date value all nodes against all remaining coupon dates in one broadcast. A full set of builds and repricings then takes milliseconds, so a cell that runs for minutes has an unterminated loop, not a large tree.

A DV01 or other bump revaluation holds the contract's fixed strike; re-striking at the bumped at-the-money rate measures a different instrument. Store the base strike once and pass it to the repricing; a pricing function that derives the at-the-money rate from the curve it is given re-strikes silently. A payer swaption gains when rates rise, so its DV01 for an upward bump is positive and of the order of the annuity times the probability of exercise; a small negative value means the strike moved with the curve.

```python
K_fixed = {name: atm_rate[name] for name in swaptions}                    # base-curve strikes, frozen
dv01 = {n: (price_on(curve_up, n, strike=K_fixed[n]) - price_on(curve, n, strike=K_fixed[n])) * 1e4 for n in swaptions}
assert all(v > 0 for v in dv01.values()), dv01                            # payer value rises with rates
```

## Tolerance for a tree-versus-analytical consistency flag

When the task asks for a flag saying the tree agrees with the analytical price but gives no tolerance, measure the tree's own discretisation error instead of picking a round number: price the same instrument with N, 2N (and, if cheap, N/2) time steps over the same horizon, so $\Delta t$ halves with each refinement (adding steps at the same $\Delta t$ only extends the tree and changes nothing); the change between successive refinements estimates the remaining error of the finest tree. Set the tolerance to a small multiple of that estimate (state the multiple), compare the analytical-minus-tree gap with it, and record the step counts and the estimate next to the flag. A gap that keeps shrinking as N grows is discretisation, not a bug; a gap that does not shrink points to a mismatch in the payoff, the exercise dates or the discounting.
Use this tolerance only after the tree passes its own checks (it reprices the zero-coupon bonds, and step 0 is the valuation date): backward induction ends once, at step 0, and is never continued past the root. A tolerance measured on a broken tree is as large as the error and hides it.
If the N-step and 2N-step prices are identical, the refinement did not take effect ($\Delta t$ did not change, or a later line reset the step count): fix that before computing the tolerance; a tolerance of zero is never valid.

```python
prices = {n: tree_price(n) for n in (n_steps // 2, n_steps, 2 * n_steps)}
err_est = abs(prices[2 * n_steps] - prices[n_steps])          # remaining error of the finer tree, roughly
tol = 3 * max(err_est, abs(prices[n_steps] - prices[n_steps // 2]) / 2)
ok = abs(analytical - prices[2 * n_steps]) <= tol
print(prices, err_est, tol, ok)
```

## Model and assumptions
- Risk-neutral short rate: $\mathrm{d}r = (\theta (t) - a r) \mathrm{d}t + \sigma  \mathrm{d}W$, constant $a > 0$(mean-reversion speed) and $\sigma$ (normal vol).
  $\theta$(t) is chosen so the model reprices today's discount curve P(0,T) exactly. r is Gaussian, so negative rates are possible.
- Equivalently $r(t) = x(t) + \phi (t)$, $\mathrm{d}x = -a x \mathrm{d}t + \sigma  \mathrm{d}W$, $x(0) = 0$, $\phi (t) = f(0,t) + \sigma ^{2}/(2a^{2}) (1 - e^{-a t})^{2}$.
- Inputs needed: the initial curve P(0,T) for all T (one interpolated curve, chosen as in the Curve check above, with f taken from it), a, $\sigma$.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| P(0,T) | today's discount factor to time T (from the given zero / swap curve) | none |
| $f(0,t)$ | instantaneous forward rate $-\mathrm{d}\ln  \operatorname{P}(0,t)/\mathrm{d}t$, continuously compounded | $1/\mathrm{year}$ |
| $a$ | mean-reversion speed (not a rate level) | $1/\mathrm{year}$ |
| $\sigma$ | ABSOLUTE (normal, basis-point) vol of the short rate; 1% = `0.01`. Not a Black/lognormal vol | $1/\sqrt{\mathrm{year}}$ in rate units |
| $t, T, S$ | times in years from today (day count of the curve, often ACT/365) | years |
| $\tau$ | accrual fraction of a coupon / caplet period (day count of the instrument, e.g. ACT/360, 30/360) | years |

## Fitting theta(t) to the curve

$$
\theta (t) = \mathrm{d}f(0,t)/\mathrm{d}t + a f(0,t) + \sigma ^{2}/(2a) (1 - e^{-2 a t})
$$

$r(0) = f(0,0)$(the instantaneous short rate). In practice nobody needs $\theta$ explicitly: the closed forms below and the tree
calibration ($\alpha _{i}$) use P(0,T) directly.

## Zero-coupon bond P(t,T) = A(t,T) exp(-B(t,T) r(t))
The bond loading uses $a$ only, never $\sigma$:

$$
B(t,T) = (1 - e^{-a (T - t)}) / a
$$

$$
\ln  A(t,T) = \ln ( \operatorname{P}(0,T) / \operatorname{P}(0,t) ) + B(t,T) f(0,t) - \sigma ^{2}/(4a) (1 - e^{-2 a t}) B(t,T)^{2}
$$

Here r(t) is the INSTANTANEOUS short rate. If the state is instead the $\Delta t$ period rate R (continuously compounded over
$[t,t+\Delta t]$, which is what the tree node rate is), use $\operatorname{P}(t,T) = \mathrm{Ahat} \exp (-\mathrm{Bhat} R)$ with

$$
\begin{gathered}
\mathrm{Bhat} = B(t,T) \Delta  t / B(t,t+\Delta  t) \\
\ln  \mathrm{Ahat} = \ln (\operatorname{P}(0,T)/\operatorname{P}(0,t)) - [B(t,T)/B(t,t+\Delta  t)] \ln (\operatorname{P}(0,t+\Delta  t)/\operatorname{P}(0,t)) - \sigma ^{2}/(4a) (1 - e^{-2 a t}) B(t,T) (B(t,T) - B(t,t+\Delta  t))
\end{gathered}
$$

## European option on a zero-coupon bond (option expiry T, bond maturity S > T, strike K per unit face, face L)
Total standard deviation of $\ln  \operatorname{P}(T,S)$, not annualized:

$$
\sigma _{\operatorname{P}} = (\sigma  / a) (1 - e^{-a (S - T)}) \sqrt{(1 - e^{-2 a T}) / (2a)}
$$

$$
h = (1 / \sigma _{\operatorname{P}}) \ln ( \operatorname{P}(0,S) / (K \operatorname{P}(0,T)) ) + \sigma _{\operatorname{P}} / 2
$$

$$
\;\text{Call}\; = L [\operatorname{P}(0,S) N(h) - K \operatorname{P}(0,T) N(h - \sigma _{\operatorname{P}})]
$$

$$
\;\text{Put}\; = L [K \operatorname{P}(0,T) N(-h + \sigma _{\operatorname{P}}) - \operatorname{P}(0,S) N(-h)]
$$

$K$ is the price per unit face, not a rate; the total strike payment is $LK$. Parity is $\mathrm{Call}-\mathrm{Put}=L[\operatorname{P}(0,S)-K\operatorname{P}(0,T)]$.

## Caplets / floorlets (reset t_k, payment t_{k+1}, accrual tau, cap rate X, notional N, simple forward rate)
A caplet paying $N \tau  \max (R - X, 0)$ at $t_{k+1}$ equals $N (1 + X \tau )$ European PUTS expiring $t_{k}$ on the zero maturing $t_{k+1}$ (each option has unit face, $L=1$)
with strike $K = 1 / (1 + X \tau )$. A floorlet is the same number of CALLS. A cap (floor) value is the sum over its caplets (floorlets)
(the first period whose rate is already fixed is usually excluded or valued as a known cash flow; follow the task).

### Code for the bond option and the caplet

Name arguments by role (option expiry, bond maturity), not by letter. The option formula uses today's discount
factors to both dates; A(t,T) and B(t,T) belong to the bond price at a future date and do not enter h. Put-call parity
holds for any h, so it cannot test h; the at-the-money and zero-volatility limits can.

```python
import numpy as np
from scipy.stats import norm

def zcb_put(a, sigma, T, S, K, P):                     # option expiry T, bond maturity S, strike K per unit face
    sp = sigma / a * (1 - np.exp(-a * (S - T))) * np.sqrt((1 - np.exp(-2 * a * T)) / (2 * a))
    h = np.log(P(S) / (K * P(T))) / sp + sp / 2          # today's discount factors only, never A(T, S)
    return K * P(T) * norm.cdf(-h + sp) - P(S) * norm.cdf(-h), sp

def caplet(a, sigma, t_reset, t_pay, X, tau, P):       # N = 1; calibrate on (model - market) * 1e4, not raw prices
    K = 1 / (1 + X * tau)
    return (1 + X * tau) * zcb_put(a, sigma, t_reset, t_pay, K, P)[0]

def check_caplet_pricer(a, sigma, t_reset, t_pay, tau, P, price=caplet):
    X_atm = (P(t_reset) / P(t_pay) - 1) / tau          # forward rate: strike bond price = forward bond price
    sp = sigma / a * (1 - np.exp(-a * (t_pay - t_reset))) * np.sqrt((1 - np.exp(-2 * a * t_reset)) / (2 * a))
    approx = P(t_pay) * (2 * norm.cdf(sp / 2) - 1) * (1 + X_atm * tau)   # at the money h = sp/2 exactly
    assert np.isclose(price(a, sigma, t_reset, t_pay, X_atm, tau, P), approx, rtol=1e-8)
    deep = price(a, 1e-6, t_reset, t_pay, X_atm - 0.01, tau, P)         # near-zero vol: intrinsic value
    assert np.isclose(deep, P(t_pay) * tau * 0.01, rtol=1e-3)
```

## European swaption: Jamshidian (1989) decomposition
Swap starts at option expiry T, fixed payment dates $t_{1}$..$t_{n}$, accruals $\tau _{i}$, fixed rate X, notional N.
Coupons $c_{i} = X \tau _{i}$ for $i < n$ and $c_{n} = 1 + X \tau _{n}$ (per unit notional).
1. Solve for $r^{*}$ (1-D root, monotone in r; use a bracketed solver): $\sum _{i} c_{i} A(T,t_{i}) \exp (-B(T,t_{i}) r^{*}) = 1$.
2. Strikes $K_{i} = A(T,t_{i}) \exp (-B(T,t_{i}) r^{*})$ (bond prices at T when r(T) = $r^{*}$).
3. Receiver swaption (right to receive fixed) = call on the coupon bond with strike 1:
   $N \sum _{i} c_{i} \;\text{Call}\;(T, t_{i}, K_{i})$. Payer swaption (right to pay fixed) = put: $N \sum _{i} c_{i} \;\text{Put}\;(T, t_{i}, K_{i})$.
The standard decomposition requires a common monotone exercise region. Nonnegative coupon weights $c_i$, with at least one positive weight and positive bond loadings, provide this condition. Signed coupons can destroy monotonicity or produce multiple roots; a root alone does not justify decomposition into bond options. These formulas also assume the stated single-curve swap representation, settlement and per-unit-face strikes; a multi-curve or cash-settled swaption can require a different payoff. The one-factor argument does not extend directly to two factors.

## Trinomial tree (Hull-White 1994) for Bermudan / American exercise
Stage 1, tree for $x (\mathrm{d}x = -a x \mathrm{d}t + \sigma  \mathrm{d}W, x(0)=0)$, time step $\Delta$ t:
- $M = -a \Delta  t$, $V = \sigma ^{2} \Delta  t$ (textbook) or exact $M = e^{-a \Delta  t} - 1$, $V = \sigma ^{2} (1 - e^{-2a \Delta  t})/(2a)$.
- Spacing $\Delta  x = \sqrt{3 V}$; node (i,j) has $x = j \Delta  x$; $j_{\mathrm{max}}$ = smallest integer > $0.184 / (-M)$ (equal to $0.184/(a\Delta t)$ only for the textbook $M=-a\Delta t$).
- With $m = j M$ the probabilities (up, middle, down) are:
  - normal branching (to j+1, j, j-1), |j| < $j_{\mathrm{max}}$: $\mathrm{pu} = 1/6 + (m^{2} + m)/2$, $\mathrm{pm} = 2/3 - m^{2}$, $\mathrm{pd} = 1/6 + (m^{2} - m)/2$
  - up branching at $j = -j_{\mathrm{max}}$(to j+2, j+1, j): $\mathrm{pu} = 1/6 + (m^{2} - m)/2$, $\mathrm{pm} = -1/3 - m^{2} + 2m$, $\mathrm{pd} = 7/6 + (m^{2} - 3m)/2$
  - down branching at $j = +j_{\mathrm{max}}$(to j, j-1, j-2): $\mathrm{pu} = 7/6 + (m^{2} + 3m)/2$, $\mathrm{pm} = -1/3 - m^{2} - 2m$, $\mathrm{pd} = 1/6 + (m^{2} + m)/2$
Stage 2, shift to fit the curve with Arrow-Debreu prices $Q_{i,j} (Q_{0,0} = 1)$; node rate $R_{i,j} = \alpha _{i} + j \Delta  x$:

$$
\begin{gathered}
\alpha _{i}     = [ \ln ( \sum _{j} Q_{i,j} e^{-j \Delta  x \Delta  t} ) - \ln  \operatorname{P}(0, (i+1) \Delta  t) ] / \Delta  t \\
Q_{i+1,k}   = \sum _{j} Q_{i,j} q(j,k) \exp ( -(\alpha _{i} + j \Delta  x) \Delta  t )
\end{gathered}
$$

Check: $\sum _{j} Q_{i,j} = \operatorname{P}(0, i \Delta  t)$ for every i. Value by backward induction, discounting each step with
$\exp ( -R_{i,j} \Delta  t )$; at exercise dates take $\max ( \mathrm{continuation}, \mathrm{exercise} \mathrm{value} )$. An exercise node needs a positive exercise value at least equal to continuation; nodes where both are zero are not exercise nodes, so the boundary is the lowest node of that set, and its short rate sits where exercise first pays. Exercise values of bonds / swaps at a node
can come from rolling bonds back in the tree or from the Ahat/Bhat formula with the node's R.

### Swap and swaption values on the tree

The value at time T0 of a payer swap (pay fixed X, receive floating) per unit notional is the floating leg, worth 1 at a reset date, minus the coupon bond:

```
payer(T0) = 1 - sum_i c_i P(T0, t_i),   c_i = X tau_i (i < n),   c_n = 1 + X tau_n
          = 1 - P(T0, t_n) - X sum_i tau_i P(T0, t_i)
```

The final principal belongs to the coupon bond; dropping it (writing 1 - X sum tau P) gives values near 1 instead of a few percent. A receiver swap is the negative. At a later exercise date t_k only payments strictly after t_k remain in the sum.

Array skeleton (Hull-White 1994 geometry with textbook M = -a dt; the edge rows use the up- and down-branching probabilities above). Bond prices at a node come from rolling a unit payment back through the tree.

```python
import numpy as np

def hw_tree(a, sigma, dt, n_steps, P0):                 # P0(t): market discount factor at time t
    M = -a * dt; dx = sigma * np.sqrt(3 * dt)
    jmax = max(1, int(np.ceil(0.184 / (a * dt))))
    j = np.arange(-jmax, jmax + 1); m = j * M
    prob = np.stack([1/6 + (m*m + m)/2, 2/3 - m*m, 1/6 + (m*m - m)/2], 1)
    tgt = np.stack([j + 1, j, j - 1], 1) + jmax         # target rows: up, middle, down
    lo, hi = 0, 2 * jmax
    prob[lo] = [1/6 + (m[lo]**2 - m[lo])/2, -1/3 - m[lo]**2 + 2*m[lo], 7/6 + (m[lo]**2 - 3*m[lo])/2]
    tgt[lo] = [lo + 2, lo + 1, lo]                      # up branching at the bottom
    prob[hi] = [7/6 + (m[hi]**2 + 3*m[hi])/2, -1/3 - m[hi]**2 - 2*m[hi], 1/6 + (m[hi]**2 + m[hi])/2]
    tgt[hi] = [hi, hi - 1, hi - 2]                      # down branching at the top
    Q = np.zeros((n_steps + 1, j.size)); Q[0, jmax] = 1.0
    alpha = np.zeros(n_steps + 1)
    for n in range(n_steps + 1):
        alpha[n] = (np.log(np.sum(Q[n] * np.exp(-j * dx * dt))) - np.log(P0((n + 1) * dt))) / dt
        if n < n_steps:
            w = Q[n] * np.exp(-(alpha[n] + j * dx) * dt)
            np.add.at(Q[n + 1], tgt.ravel(), (w[:, None] * prob).ravel())
    return dict(j=j, dx=dx, dt=dt, alpha=alpha, Q=Q, prob=prob, tgt=tgt, jmax=jmax)

def step_back(tr, n, v_next):                           # values at step n from values at step n + 1
    r = tr['alpha'][n] + tr['j'] * tr['dx']
    return np.exp(-r * tr['dt']) * np.sum(tr['prob'] * v_next[tr['tgt']], 1)

def zcb_at(tr, n_from, n_to):                           # P(t_from, t_to) at every node of step n_from
    v = np.ones(tr['j'].size)
    for n in range(n_to - 1, n_from - 1, -1):
        v = step_back(tr, n, v)
    return v

def payer_swaption_tree(tr, n0, n_pay, c, exercise_steps=None):
    ex = [n0] if exercise_steps is None else sorted(exercise_steps)   # European if only n0
    bonds = {(ne, i): zcb_at(tr, ne, ni) for ne in ex for i, ni in enumerate(n_pay) if ni > ne}
    v = np.zeros(tr['j'].size)
    for n in range(max(ex), -1, -1):
        if n < max(ex):
            v = step_back(tr, n, v)
        if n in ex:
            cb = sum(c[i] * bonds[(n, i)] for i, ni in enumerate(n_pay) if ni > n)
            v = np.maximum(v, np.maximum(1.0 - cb, 0.0))
    return v[tr['jmax']]

def bermudan_payer_tree(tr, n_ex, n_pay, c):            # price and exercise boundary, one entry per exercise step
    v = np.zeros(tr['j'].size); boundary = []
    for n in range(max(n_ex), -1, -1):
        if n < max(n_ex):
            v = step_back(tr, n, v)                     # continuation value at step n
        if n in n_ex:
            cb = sum(ci * zcb_at(tr, n, ni) for ci, ni in zip(c, n_pay) if ni > n)   # payments strictly after t_n
            exercise = np.maximum(1.0 - cb, 0.0)
            hit = (exercise > 0) & (exercise >= v)      # both zero deep out of the money: not an exercise node
            j_low = int(tr['j'][hit].min()) if hit.any() else None                  # lowest-rate exercise node
            rate = None if j_low is None else tr['alpha'][n] + j_low * tr['dx']
            boundary.append((n * tr['dt'], j_low, rate))  # time from today (not from expiry), node, short rate
            v = np.maximum(v, exercise)
    return v[tr['jmax']], boundary[::-1]                # boundary in date order
```

Checks, in this order:

```python
tr = hw_tree(a, sigma, dt, n_steps, P0)
assert all(abs(tr['Q'][n].sum() - P0(n * dt)) < 1e-10 for n in range(n_steps + 1))
x = tr['j'] * tr['dx']; xt = x[tr['tgt']]                       # x at the three targets of every row
mean = (tr['prob'] * xt).sum(1); var = (tr['prob'] * xt**2).sum(1) - mean**2
assert tr['tgt'].min() >= 0 and tr['tgt'].max() == 2 * tr['jmax']
assert np.allclose(mean, x * (1 - a * dt), atol=1e-12)          # E[x_next] = x + M x on every row, edges included
assert np.allclose(var, sigma**2 * dt, rtol=1e-9)               # Var[x_next] = dx**2 / 3 = sigma**2 dt
swap0 = tr['Q'][n0] @ (1.0 - sum(ci * zcb_at(tr, n0, ni) for ci, ni in zip(c, n_pay)))
assert abs(swap0 - (P0(n0 * dt) - sum(ci * P0(ni * dt) for ci, ni in zip(c, n_pay)))) < 1e-10
eur = payer_swaption_tree(tr, n0, n_pay, c)
assert abs(eur - jamshidian_payer) * 1e4 < 5                   # a few bp of discretisation error
n_ex = [n0] + list(n_pay[:-1])                                  # expiry first, then every coupon date but the last payment
assert n_ex[0] == n0 and len(n_ex) == len(n_pay)                # one exercise date per coupon period, expiry included
ber, boundary = bermudan_payer_tree(tr, n_ex, n_pay, c)
assert abs(ber - payer_swaption_tree(tr, n0, n_pay, c, exercise_steps=n_ex)) < 1e-12 and ber >= eur - 1e-12
assert len(boundary) == len(n_ex) and all(j is not None and r > 0 for _, j, r in boundary)   # check, then inspect any failure
```

The swap check needs no option: the state-price-weighted swap value at T0 equals the time-zero forward swap value, which is zero at the at-the-money rate. The curve check and the swap check hold for any branch wiring, because alpha is refitted to the curve at every step; only the moment check tests where each row's three branches land. Read the failures in order: a moment-check failure is in the branch targets or probabilities (a target written as j instead of the row index j + jmax sends negative rows to the far end of the array); a swap-check failure is in the bond values or the swap formula; a swaption far from the closed form with all three checks passing is in the payoff or the exercise dates.

Sources: Hull & White (1994), Numerical procedures for implementing term structure models I, J. Derivatives 2(1):7-16 (tree, branching, Arrow-Debreu fitting); Hull, Options, Futures, and Other Derivatives, 9th ed., ch. 31 (short-rate trees, Bermudan swaptions); Brigo & Mercurio (2006), Interest Rate Models, 2nd ed., sec. 3.3 (Jamshidian swaption in Hull-White) and sec. 1.5 (swap as coupon bond); NumPy reference for numpy.add.at.


## Common mistakes
- $\sigma$ is the normal vol of r; $\sigma _{\operatorname{P}}$ is the vol of the bond price over the option life. Do not plug a Black cap / swaption
  vol in as $\sigma$, and do not annualize $\sigma _{\operatorname{P}}$ again (it already contains the time to expiry).
- B uses a, not $\sigma ; a \to  0$ gives $B = T - t$ and $\sigma _{\operatorname{P}} = \sigma  (S - T) \sqrt{T}$(Ho-Lee limit). Never divide by $a = 0$.
- Using the tree's $\Delta$ t rate R in the instantaneous A/B formula (use Ahat/Bhat), or a zero rate instead of f(0,t) in $\ln  A$.
- In Jamshidian, forgetting the notional in the last coupon, or calling payer = call (payer is a PUT on the coupon bond).
- Caplet: strike is 1/(1+X $\tau$) and the option count is (1+X $\tau$); option expiry is the reset date, bond maturity the payment date.
- Tree: choose $\Delta$ t so every exercise / reset / payment date sits on a node; time 0 is step 0, so n steps span n $\Delta$ t;
  calibrating $\alpha _{i}$ needs P(0,(i+1)$\Delta$ t), i.e. the curve must extend one step past the last node used.
- Mixing day counts: model time uses the curve's year fraction; $\tau$ uses the instrument's accrual convention.

## Applicability and known limits
- European ZCB options, caps/floors and swaptions have exact closed forms in this model; the tree is for early exercise
  (Bermudan swaptions, callable / putable bonds, American bond options) and converges to the closed forms as $\Delta  t \to  0$.
- One factor: instantaneous diffusion shocks to rates driven by this factor are collinear; this does not imply unit sample correlation of all yield levels; constant a, $\sigma$ cannot fit a whole cap / swaption vol surface or a smile.
  Calibrate a, $\sigma$ to a few instruments the task names; a time-dependent $\sigma$(t) changes the formulas (not covered here).
- Gaussian rates can go negative; that is a model feature, not a bug.


## Sources
Hull & White (1990) Pricing interest-rate-derivative securities, Review of Financial Studies 3(4):573-592;
Hull & White (1993) One-factor interest-rate models and the valuation of interest-rate derivative securities, JFQA 28(2):235-254;
Hull & White (1994) Numerical procedures for implementing term structure models I: single-factor models, J. Derivatives 2(1):7-16;
Jamshidian (1989) An exact bond option formula, J. Finance 44(1):205-209; Vasicek (1977) J. Financial Economics 5(2):177-188;
Brigo & Mercurio (2006) Interest Rate Models - Theory and Practice, 2nd ed., Springer; Hull, Options, Futures, and Other Derivatives (Pearson).
