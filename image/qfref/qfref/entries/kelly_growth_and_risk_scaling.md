# Kelly growth, financing and risk scaling

Use this reference to distinguish log-optimal allocation from a covariance-based approximation, and to scale a fixed portfolio direction to a risk budget. It does not specify a trading signal, simulation ordering or performance aggregation convention.

**Quick checks before writing:** (1) drawdown series: with the initial capital as the first point (the reading when paths start at an initial capital and the task says nothing else) or period-end values only (when the task defines it on the equity curve from the first close); see "Each path's drawdown" below; (2) choose the account model for the wealth not held in the risky fractions (see "Account models" below): when the task describes no cash account, lending or financing rate for that remainder, the period return is the weighted sum f'R (the remainder earns nothing); add the cash leg r_f + f'(R - r_f) only when the task describes one. The financed growth factor G(f) below is the objective used to derive the Kelly fraction, not by itself the simulated return. Use the same period return for wealth, Sharpe ratio and drawdown; (3) a "var" output next to a VaR limit is value-at-risk, not variance; (4) the estimation window has two readings: the last N valid rows after removing invalid ones (the window is described as a count of valid rows, or cleaning comes before the window in the task's steps), or the last N rows of the raw table with invalid rows then dropped, which can leave fewer than N ("the last N days" stated before any cleaning step); decide from where the window appears in the task's step order; a count of valid observations is the number of rows that survive cleaning, not the number inside the window.

**Counts next to a window:** a field counting valid (clean) observations reports the rows that survive cleaning, before any estimation window is cut; the window length is a separate number (N, or fewer when fewer valid rows exist). Keep both as variables and write each from its own one:

```python
n_valid = len(clean)                      # rows left after removing invalid ones
est = clean.iloc[-N:] if N else clean      # the estimation window
n_window = len(est)
```

## Copy this to simulate a sizing scheme

One function for the period returns, the wealth path, the drawdown and the returns used for the Sharpe ratio, so all of them come from the same return series. The default account is the weighted sum of the risky returns. Change `account` only when the task describes where the rest of the wealth sits: "financed" when the remainder earns or pays the cash rate (a cash or financing account the task names), "excess" when the task asks for returns over the cash rate. G(f) above is the objective used to derive the Kelly fractions; it is not by itself the simulated return.

```python
def simulate_scheme(R, w, rf=0.0, account="weighted", capital=1.0):
    # R: (..., n_periods, n_assets) simple returns; w: risky weights; rf: cash return per period
    R = np.asarray(R, float); w = np.asarray(w, float)
    if account == "weighted":
        r = R @ w                                  # no cash account in the task
    elif account == "financed":
        r = rf + (R - rf) @ w                      # remainder 1 - sum(w) earns or pays rf
    elif account == "excess":
        r = (R - rf) @ w                           # returns over the cash rate
    else:
        raise ValueError(account)
    path = np.concatenate([np.full(r.shape[:-1] + (1,), capital), capital * np.cumprod(1.0 + r, axis=-1)], axis=-1)
    max_dd = (1.0 - path / np.maximum.accumulate(path, axis=-1)).max(axis=-1)   # initial capital is the first point
    return r, path, max_dd                         # r: the per-period returns for the Sharpe ratio
```

Compute the Sharpe ratio from the returned `r` with the task's own definition (mean over standard deviation, annualised by the task's periods per year; subtract rf first only when the task defines an excess-return Sharpe). If the task defines drawdown on period-end values only, drop the first point of `path`.

## Shared Foundations

Map returns, cash financing, units and horizon to the explicit definitions in the task. A stated approximation may deliberately differ from exact log optimization. Identify that distinction rather than labeling every inverse-covariance allocation an exact discrete-time Kelly portfolio.

Let R be the vector of risky simple returns over one period, $r_{f}$ the deterministic cash return, and f the risky fractions of current wealth. The remaining fraction $1-\sum (f)$ earns or pays $r_{f}$ under symmetric borrowing/lending. Short sales and leverage require separate feasibility assumptions.

The financed one-period wealth multiplier is:

$$
G(f) = 1 + r_{f} + f'\cdot (R-r_{f}\cdot 1)
$$

The exact discrete-time growth objective requires a positive wealth multiplier almost surely and a well-defined expectation.

$$
g(f) = \operatorname{E}[\ln (G(f))]
$$

Interior optimality, when differentiation under the expectation is justified, is:

$$
\operatorname{E}[(R-r_{f}\cdot 1)/G(f)] = 0
$$

Constraints can replace this condition with boundary optimality. With an unbounded Gaussian simple-return model, any portfolio with nonzero return variance has a positive probability of $G\le 0$. Its exact positive-wealth log objective therefore cannot be justified by ignoring rare simulated ruin.

## Covariance allocation and its scope

For continuous diffusion returns with constant excess drift vector $\mu$ and positive-definite instantaneous covariance $\Sigma$, the expected log-growth rate has the following form, by Ito's formula:

$$
\mathrm{growth}_{\mathrm{rate}}(f) = r_{f} + f'\cdot \mu  - (1/2)\cdot f'\cdot \Sigma \cdot f
$$

The unconstrained continuous-time optimum is:

$$
f_{\mathrm{growth}} = \Sigma ^{-1}\cdot \mu
$$

This same expression is often used as a small-return sizing approximation. The mean and covariance must refer to the same time unit. With singular $\Sigma$, a pseudoinverse is not automatically a finite optimum: a zero-variance direction with nonzero excess drift makes the unconstrained objective unbounded.

For comparison, let $x=R-r_{f}\cdot 1$ and $m=\operatorname{E}[x]$. Expanding discrete log wealth around the cash multiplier gives:

$$
\begin{gathered}
\operatorname{E}[\ln (G(f))] \approx  \ln (1+r_{f}) + f'\cdot m/(1+r_{f}) \\
- f'\cdot \operatorname{E}[x\cdot x']\cdot f/(2\cdot (1+r_{f})^{2})
\end{gathered}
$$

Its second moment is $\Sigma+mm'$, not $\Sigma$ alone. Dropping the mean outer product is an additional approximation. These expressions should not be silently interchanged when a task specifies one of them.

## Fractional sizing and a one-period risk limit

Fractional sizing preserves a chosen risky direction, with c between zero and one:

$$
f_{\mathrm{fractional}} = c\cdot f_{\mathrm{growth}}
$$

For Gaussian excess-return loss $L=-f'\cdot x$ at confidence $\alpha$, let $z_{\alpha}$ be the standard normal quantile. The positive-loss convention gives:

$$
\operatorname{VaR}_{\alpha}(f) = -f'\cdot m + z_{\alpha}\cdot \sqrt{f'\cdot \Sigma \cdot f}
$$

If this VaR is positive and the allowed loss fraction is $B\ge 0$, scaling only down along the same direction gives:

$$
c = \min (1, B/\operatorname{VaR}_{\alpha}(f))
$$

This follows from positive homogeneity for $c\ge 0$; it is not the solution of every constrained Kelly problem. Scaling to the budget exactly, $c=B/\operatorname{VaR}_{\alpha}(f)$, can also lever up; wording such as "comply with" or "not exceed" describes the scale-down rule, wording such as "scale to" or "target" the exact one. A zero-mean (relative) VaR drops the $-f'\cdot m$ term; the task's VaR definition decides whether the mean enters. If the unscaled VaR is nonpositive, division is not a valid rule. Including an unscaled cash return in total loss also changes the scaling equation. Currency risk uses wealth times the fractional loss; the budget must use matching units.

In code, keep the variance, the standard deviation and the value-at-risk under separate names, so that an output called "var" next to a VaR limit receives the value-at-risk:

```python
port_variance = f @ Sigma @ f                 # variance of the one-period portfolio return
sigma_p = np.sqrt(port_variance)              # its standard deviation
z = norm.ppf(level)                           # level: confidence level
var_full = z * sigma_p                        # value-at-risk (zero-mean form); add - f @ m for the mean-adjusted form
assert var_full > port_variance               # a daily VaR is far larger than a daily variance; equality of scale means the names were swapped
scale = min(1.0, var_limit / var_full)        # scale down only
f_var = scale * f
```

## Financed risk scaling and simulated paths

This section applies only when the task describes a cash or financing account for the wealth not held in the risky fractions (a lending or borrowing rate for that remainder). A risk-free rate used only for the Sharpe ratio, for excess returns or inside the Kelly derivation does not describe such an account; without one, the simulated period return is the weighted sum f'R (see "Account models" below), and the formulas here are not used for the simulated wealth.

The earlier VaR formula measures excess-return loss. If total funded return is $r_f+cf'x$, cash is not scaled down with the risky position. Let $v_{\mathrm{ex}}=-f'm+z_\alpha\sqrt{f'\Sigma f}$; for $c\ge0$, total-return VaR is:

$$
\operatorname{VaR}_{\mathrm{funded}}(c)=-r_f+c\,v_{\mathrm{ex}}
$$

If $v_{\mathrm{ex}}>0$ and $B+r_f\ge0$, the largest admissible scale in $[0,1]$ under this particular VaR constraint is:

$$
c_{\max}=\min\left(1,\frac{B+r_f}{v_{\mathrm{ex}}}\right)
$$

For other signs solve the affine inequality over the stated feasible interval; there can be no feasible scale, or an upper-bound rule may be inappropriate. This differs from scaling an excess-return loss directly by $B/v_{\mathrm{ex}}$. A money budget must first be compared to money VaR at the same wealth. Asymmetric borrowing and lending create a different financing equation.

For fixed fractions and a specified financing convention, wealth on simulated path $j$ compounds its own total funded period returns:

$$
W_{j,t+1}=W_{j,t}\left[1+r_{f,t}+f'(R_{j,t+1}-r_{f,t}\mathbf1)\right]
$$

Under this financed account the scheme's period return is that growth factor minus one, $r_{f,t}+f'(R_{j,t+1}-r_{f,t}\mathbf1)$. Drawing total risky returns and then adding the same risky mean again double-counts drift. Drawing excess returns and omitting an intended cash return changes the account model. Multiplying returns by fractions is rebalanced constant-fraction exposure, not fixed-share buy-and-hold. A negative or zero multiplier requires an explicit insolvency convention; normal simple-return shocks do not guarantee positive wealth.

### Account models

Three period returns are in use for risky fractions f and simple returns R. Weighted sum: $f'R$, the remaining $1-\sum(f)$ earns nothing and borrowing costs nothing. Financed: $r_f+f'(R-r_f\mathbf1)$, the remainder is lent or borrowed at the cash rate. Excess only: $f'(R-r_f\mathbf1)$. When the task describes no cash account or financing rate for the remainder, the weighted sum is the literal reading and a cash leg is an added assumption to state. A Sharpe ratio "without subtracting the risk-free rate" keeps whichever of these returns the account model gives. If the simulation draws excess returns, total asset returns are the draws plus $r_f$; drawing total returns and adding the mean again double-counts drift.

Including initial wealth, the path's positive high-water mark and maximum drawdown are:

$$
H_{j,t}=\max_{0\le u\le t}W_{j,u},\qquad
D_j=\max_t\left(1-\frac{W_{j,t}}{H_{j,t}}\right)
$$

When performance statistics are requested for simulated schemes, compute them from each scheme's own simulated period returns, the same returns that compound its wealth under the chosen account model, unless the task names another input. A plug-in ratio $f'm/\sqrt{f'\Sigma f}$ from the input moments is a model value, not a sample statistic of the paths, and subtracting a cash rate from the numerator changes it again; state which one is reported and keep the same definition for every scheme.

Each path's drawdown: Drawdown series, two readings: (a) the wealth series with the initial capital as its first point, so a loss in the first period counts (`W = np.hstack([np.full((n_paths, 1), W0), W0 * np.cumprod(1 + R, axis=1)])`); this is the reading when the task starts each path at an initial capital or wealth index and says nothing else; (b) only the period-end values `W0 * np.cumprod(1 + R, axis=1)`, when the task defines drawdown on the equity curve or cumulative return from the first period's close. Either way `dd = 1 - W / np.maximum.accumulate(W, axis=1)` and `dd.max(axis=1)` per path; state the reading used. A median of terminal wealths and a median of pathwise drawdowns are separate distributional summaries. Neither is obtained by taking drawdown of the median wealth path. Similarly, averaging pathwise Sharpe ratios differs from calculating one ratio after pooling all simulated periods. A stated seed alone does not specify random-stream ordering, covariance factorization or how schemes share shocks; those are reproducibility conventions rather than additional financial identities.

## Checks and Scope

In a task about value-at-risk limits and scaling, an abbreviation such as "var" in an output name means value-at-risk; report a variance only where the text says variance.


Gross exposure is $\sum ( \mathrm{abs}(f) )$; net exposure is $\sum (f)$. A leveraged long-short portfolio can have small net exposure. Leverage without a qualifier measures the size of the positions regardless of direction, that is gross exposure; a net figure is called net exposure or net leverage. Under fixed fractions and the same financing convention, successive wealth multipliers compound; negative wealth requires an explicit insolvency convention rather than continued interpretation as log growth.

A one-period VaR constraint does not bound maximum drawdown over many periods. Expected terminal wealth, median terminal wealth and average log growth are distinct. Fractional Kelly reduces exposure but does not create a universal drawdown guarantee. Performance statistics averaged over paths can differ from statistics computed from pooled observations.

## References

[Busseti, Ryu and Boyd (2016), Risk-Constrained Kelly Gambling](https://web.stanford.edu/~boyd/papers/pdf/kelly.pdf), Sections 2 and 6: log-growth objective and quadratic approximation using the raw second moment. The financing identity, continuous-diffusion first-order condition and positive-homogeneous VaR scaling above are direct derivations under the stated assumptions; the paper's drawdown-constrained optimization is not the VaR scaling rule given here.
