# VaR and ES conventions: loss sign, quantile rules, tail means, weights, horizons, backtests, cleaning, Kelly sizing and simulation

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Decisions to settle before coding

**Purpose:** Fix every choice that changes a risk number, from the task's wording.

**When to use:** Any VaR, ES, backtest or sizing task. Most steps below have more than one standard reading: read the choice from the task; when it is open, pick one, write it in a comment, and use it in every output.

**How to implement:**

Step 1: Settle and print each item:

1. Observation counts (Topic 10): a count of valid observations is taken after cleaning and before any estimation window is cut; the window length is a different number.
2. Rows an estimate for day $t$ uses (Topic 11): an estimate that labels day $t$ or sets the weights earning day $t$'s return uses only rows before $t$; pandas `.rolling(W)` at row $t$ includes row $t$, so such an estimate is `.rolling(W).stat().shift(1)`, and a series of length $n$ then has $n-W$ estimates, not $n-W+1$.
3. Rebalances (Topic 11): count those actually executed (an estimate exists and a later day holds the weights), not calendar month ends.
4. Holdings before the first rebalance (Topic 11): an initial portfolio, cash, or start at the first rebalance; write the reading in a comment.
5. Uninvested wealth and leverage (Topics 12 and 17): the weighted sum unless the task describes a cash account; leverage without a qualifier is gross. An output named with "var" beside a VaR limit or scale factor is value-at-risk, not the variance $f^\top\Sigma f$.
6. VaR and ES rules (Topics 3 and 4): quantile rule and tail mean; a risk figure over a trailing window is one number from that window, not an average of rolling figures.

## Topic 2: Loss sign and confidence level

**Purpose:** Put the risky side in the upper tail of the loss.

**When to use:** Every VaR and ES computation.

**How to implement:**

Step 1: Loss $=-$ return (or $-$P&L); drop non-finite values.

Step 2: A confidence level such as 95% corresponds to the tail probability $1-\text{level}$. Some texts call the level $\alpha$, others the tail probability: decide from the numbers the task lists (0.95, 0.99 are levels; 0.05, 0.01 are tail probabilities).

**Double check:**

1. VaR and ES are reported as positive losses unless the task states another sign.

## Topic 3: Empirical VaR: the quantile rule

**Purpose:** Pick one of the several empirical quantiles.

**When to use:** Historical-simulation VaR on $n$ scenarios.

**How to implement:**

Step 1: Round the tail probability first ($1-0.95$ is $0.05000000000000004$ in floating point; when $n\cdot\text{tail}$ is a whole number a step rule would move one observation).

Step 2: Choose the rule:

1. $k$-th worst: sort losses worst first and take the $k$-th with $k=\lceil n\cdot\text{tail}\rceil$ (at least 1); the classical historical-simulation order statistic, equal to $-$`np.quantile(returns, tail, method="inverted_cdf")`.
2. A NumPy method on the losses at the level: `np.quantile(loss, level, method=...)` with `"linear"` (the default, interpolating), `"lower"`, `"higher"`, `"nearest"` or `"inverted_cdf"`.

**Limitations and cautions:**

1. "linear" is symmetric (the loss quantile at the level is minus the return quantile at the tail); the step rules are not: `np.quantile(loss, level, method="inverted_cdf")` is the $(k+1)$-th worst loss when $n\cdot\text{tail}$ is a whole number $k$.

## Topic 4: ES: the tail mean

**Purpose:** Pick one of the three tail means.

**When to use:** Expected shortfall or CVaR of an empirical or simulated loss.

**How to implement:**

Step 1: Choose by wording:

1. Strict, $E[L\mid L>\mathrm{VaR}]$: "losses exceeding VaR", "greater than VaR"; empty, hence undefined, when VaR is the largest loss.
2. Inclusive, $E[L\mid L\ge\mathrm{VaR}]$: "at or beyond VaR", "not smaller than VaR"; always contains the VaR scenario.
3. Tail mean (Acerbi-Tasche): the average of exactly the worst $\text{tail}\cdot n$ outcomes, taking only the needed fraction of the boundary scenario; equal to $\min_c\{c+E[\max(L-c,0)]/\text{tail}\}$: "integrated quantile", "average VaR over the tail", "coherent ES".

Step 2: Tail mean computation: with $m=n\cdot\text{tail}$ and $j=\lfloor m\rfloor$, ES $=\big(\sum_{i\le j}L_{(i)}+(m-j)L_{(j+1)}\big)/m$ over losses sorted worst first.

**Limitations and cautions:**

1. Wording about a conditional expected loss past the VaR is a conditional mean but does not separate strict from inclusive: state which one is used. For continuous data the three nearly agree; for losses on a grid many scenarios sit at the VaR and they can differ a lot.

**Double check:**

1. ES is at least VaR for the same level and method.

## Topic 5: Probability-weighted (age-weighted) VaR and ES

**Purpose:** Historical VaR and ES with more weight on recent scenarios.

**When to use:** The task gives a decay factor for scenario weights.

**How to implement:**

Step 1: Weight of scenario $i$: $\lambda^{\text{age}_i}/\sum\lambda^{\text{age}}$, age 0 for the newest observation; for a multi-period scenario, count the age from its last day.

Step 2: Sort the losses worst first and keep each weight with its scenario (`np.argsort(-loss, kind="stable")`).

Step 3: Accumulate weight from the worst loss until it reaches the tail probability (`np.cumsum`, `np.searchsorted` with a $10^{-12}$ tolerance): that loss is the VaR. Equal weights give the $k$-th-worst VaR of Topic 3.

Step 4: ES tail mean: (weighted sum of the losses before the VaR scenario + the remaining tail weight times the VaR loss) / tail; inclusive ES: weighted mean of the losses that are not below VaR.

**Limitations and cautions:**

1. Sorting returns ascending and averaging after the quantile position averages gains instead of losses.

**Double check:**

1. Both ES forms are at least VaR.

## Topic 6: Parametric VaR and ES

**Purpose:** Normal and Student-t VaR and ES.

**When to use:** The task asks for parametric (variance-covariance or fitted-distribution) risk.

**How to implement:**

Step 1: Normal, with $z=N^{-1}(\text{level})$ and tail $=1-\text{level}$:

$$\mathrm{VaR}=-\mu+\sigma z,\qquad \mathrm{ES}=-\mu+\sigma\frac{\phi(z)}{\text{tail}}$$

"Absolute" VaR keeps $\mu$; "relative" or "zero-mean" sets $\mu=0$. The standard deviation divisor is a separate choice (`ddof=1` unbiased, `ddof=0` maximum likelihood).

Step 2: Student-t: `scipy.stats.t.fit` returns $(\nu,\text{loc},\text{scale})$ by maximum likelihood with all three free (fix parameters with `floc`, `fscale`, `f0`). With $q=t_\nu^{-1}(\text{level})$:

$$\mathrm{VaR}=-m+\text{scale}\cdot q,\qquad \mathrm{ES}=-m+\text{scale}\frac{f_\nu(q)(\nu+q^2)}{(\nu-1)\,\text{tail}}$$

**Limitations and cautions:**

1. The t scale is not the standard deviation: $\text{sd}=\text{scale}\sqrt{\nu/(\nu-2)}$ for $\nu>2$; the ES formula needs $\nu>1$: check after fitting.

## Topic 7: EWMA covariance

**Purpose:** The RiskMetrics-style exponentially weighted covariance and the volatility it implies.

**When to use:** The task names a decay $\lambda$ for an EWMA covariance or volatility.

**How to implement:**

Step 1: Choose the mean convention (raw returns, zero mean, the RiskMetrics form; or demeaned) and the start: the first observation's outer product, the sample covariance of the first $m$ rows, or zero.

Step 2: Recursion over the remaining rows: $C_t=\lambda C_{t-1}+(1-\lambda)x_tx_t^\top$.

Step 3: The matrix after the last observation is the forecast for the next period ("current", "as of the last date").

Step 4: Annualized portfolio volatility $\sqrt{w^\top Cw\cdot P}$ with $P$ the periods per year the data frequency implies (252 trading days, 52 weeks, 12 months).

**Double check:**

1. For one series, the first-outer-product start with zero mean equals `pd.Series(x**2).ewm(alpha=1-lam, adjust=False).mean()`.

## Topic 8: Multi-period horizons

**Purpose:** Scale or build risk over $h$ periods.

**When to use:** A VaR or ES over more than one period.

**How to implement:**

Step 1: Square-root-of-time: multiply a one-period VaR or ES by $\sqrt h$ (exact for independent normal returns with zero mean); with a mean, the normal $h$-period VaR is $-h\mu+\sqrt h\,\sigma z$.

Step 2: Simulation-type methods: an $h$-period scenario is the sum of $h$ consecutive log returns, or the compounded product of $h$ simple returns (rolling sums of `log1p`, then `expm1`).

Step 3: Overlapping windows step one period ($n-h+1$ dependent scenarios); non-overlapping windows step $h$ periods (about $n/h$) and need an anchor, the first or the last observation.

## Topic 9: Backtesting a VaR forecast

**Purpose:** Count exceptions and test their frequency.

**When to use:** The task backtests a rolling or expanding VaR forecast.

**Constraints:**

1. The forecast for day $t$ uses data through day $t-1$ only.

**How to implement:**

Step 1: For each test day $t$ from the stated minimum number of observations: history = all earlier days (expanding) or the last $W$ (rolling); VaR from Topic 3.

Step 2: An exception is a loss above the forecast ("exceeds"); a loss equal to it counts only under an "at or above" wording.

Step 3: Kupiec proportion of failures with $T$ test days, $x$ exceptions and $p=1-\text{level}$: $LR=-2[\ell(p)-\ell(x/T)]$ with $\ell(q)=x\ln q+(T-x)\ln(1-q)$ (`scipy.special.xlogy` keeps it finite when $x=0$ or $x=T$); p-value `scipy.stats.chi2.sf(LR, 1)`.

## Topic 10: Cleaning a data feed and counting observations

**Purpose:** Build a clean return table and count it correctly.

**When to use:** The raw data may contain missing values, text in numeric columns, infinities, unparseable or repeated dates.

**Constraints:**

1. A return is a change: forward-filling a missing return repeats a move that did not happen, and filling with zero asserts that nothing moved; dropping each row with any invalid value keeps assets aligned on the same dates. A large but finite return is a data point unless the task gives a rule for it.

**How to implement:**

Step 1: Parse dates (`pd.to_datetime(..., errors="coerce")`) and values (`pd.to_numeric(..., errors="coerce")`, infinities to NaN); drop rows without a date.

Step 2: Remove repeated dates by the task's rule (`drop_duplicates(keep=...)`), sort by date.

Step 3: Apply the missing-value rule (drop the row, or the task's fill).

Step 4: The count of valid observations is the number of rows that survive; cut an estimation window of the latest $N$ rows from the cleaned table (`iloc[-N:]`; an unset $N$ means the full cleaned sample).

**Double check:**

1. Print the rows read and the rows kept; the window length is reported separately from the valid count.

## Topic 11: Rolling estimates, rebalance dates and holdings

**Purpose:** Time rolling estimates and rebalances so no future data enters.

**When to use:** Weights are set on rebalance dates from rolling-window estimates (see also the rolling-estimate workflow card).

**Constraints:**

1. An estimate that labels day $t$ or sets the weights that earn day $t$'s return uses rows $t-W$ to $t-1$; an estimate dated at the close of $t$ and acted on from $t+1$ may include row $t$. "Uses only data up to $t$" rules out future rows but does not say whether row $t$ enters.

**How to implement:**

Step 1: Windows: for each $t$, rows $t-W+1$ to $t$ (includes $t$) or $t-W$ to $t-1$ (earlier days only); `rolling` needs $W$ values by default (`min_periods` lowers it); "trailing $N$ returns" is the last $N$ values.

Step 2: Month-end rebalance date: the latest date of the month present in the data (group the dates by `to_period("M")` and take the maximum); when the data stop before the month ends, the final row is not that month's last trading day; the last data row has no later day to hold new weights.

Step 3: Holdings before the first rebalance: an initial portfolio from the first backtest day, cash until the first rebalance, or start the evaluated sample at the first rebalance. An inverse-volatility rule with no estimate yet has nothing to tilt the weights: its uninformed portfolio is equal weights $1/n$; a backtest over the whole sample with no cash account mentioned is fully invested from its first day.

Step 4: New weights set at the close of a rebalance date earn from the next day: hold the targets, shift by one day, forward-fill between rebalances.

**Double check:**

1. The number of estimates is $n-W$ (earlier days only) or $n-W+1$ (including $t$); the number of rebalances counts executed ones.

## Topic 12: Portfolio return, leverage and scaling to a risk limit

**Purpose:** Turn fractions of wealth into period returns and exposures.

**When to use:** Fractions $w$ of wealth in risky assets with simple returns $R$.

**Constraints:**

1. When the task describes no cash account or financing rate for the remainder, the weighted sum is the literal reading and a cash leg is an added assumption; state it if added.

**How to implement:**

Step 1: Account model:

1. Weighted sum: $R\,w$; the remainder $1-\sum w$ earns nothing.
2. Financed: $r_f+(R-r_f)\,w$; the remainder is lent or borrowed at the cash rate.
3. Excess only: $(R-r_f)\,w$.

Step 2: Gross exposure (leverage) $\sum\lvert w\rvert$; net exposure $\sum w$; "leverage" without a qualifier is gross.

Step 3: Per-period cash rate from an annual rate $r$: $r/P$ (simple) or $(1+r)^{1/P}-1$ (compounded).

Step 4: Scaling to a risk limit along a fixed direction: "comply with", "cap at", "not exceed" give $c=\min(1,\text{limit}/\text{risk})$ (down only); "scale to", "target" give $c=\text{limit}/\text{risk}$.

**Double check:**

1. The same period returns drive wealth, Sharpe ratio and drawdown.

## Topic 13: Random streams and losses on a grid

**Purpose:** Reproduce simulated losses and report grid quantiles honestly.

**When to use:** Simulated portfolio losses (factor and idiosyncratic draws).

**How to implement:**

Step 1: Generator: `np.random.seed(s)` with the legacy `np.random.*` functions (MT19937 RandomState) or `np.random.default_rng(s)` (PCG64); they give different streams for the same seed.

Step 2: Draw order: all factor draws then all idiosyncratic draws, the reverse, or one simulation at a time; use the one the task names, otherwise state the choice.

Step 3: For losses on a grid, print next to the reported quantile the empirical CDF at the VaR and at the next lower grid point: a quantile can move by one grid step between streams when the CDF at a grid point is close to the level.

## Topic 14: Group breakdowns of a portfolio loss

**Purpose:** Report group mean losses that add up correctly.

**When to use:** A loss table by group (sector, rating, region) that partitions the portfolio.

**How to implement:**

Step 1: Two figures per group: the mean over scenarios of the group's total loss, and the mean loss of a single member; they differ by the group size.

Step 2: "Per name", "per bond", "average member" point to the per-member figure; a table presented as the breakdown of a portfolio figure points to the group total; when both fit, write the choice in a comment.

**Double check:**

1. Group totals add up to the portfolio mean loss; per-member means times group sizes equal the group totals.

## Topic 15: After a correction, rewrite every file that used it

**Purpose:** Keep written files consistent with corrected code.

**When to use:** A function is fixed after its results were written.

**How to implement:**

Step 1: Recompute and rewrite every output that used it, then read the files back.

**Double check:**

1. Invariants that hold under every convention: ES $\ge$ VaR for the same level and method; VaR at a higher level $\ge$ VaR at a lower level for the same method; the expected number of rows and labels.

## Topic 16: Kelly fractions and leverage

**Purpose:** Estimate Kelly fractions from sample statistics.

**When to use:** The task sizes positions by the Kelly criterion from means and covariances, possibly scaled to a VaR limit and compared on simulated wealth paths.

**How to implement:**

Step 1: Clean and count (Topic 10); cut the estimation window from the cleaned table (its length is not the valid count).

Step 2: Per-period cash rate, converted from the annual figure the task gives (Topic 12, Step 3); excess means $\mu_e=\bar r-r_f$ and covariance $\Sigma$ (`np.cov(..., ddof=...)` as the task states) on the estimation window only.

Step 3: Full Kelly fractions: solve $\Sigma f=\mu_e$ (`np.linalg.solve`); $\lvert f\rvert$ above 1 is leverage.

Step 4: Exposure: gross $\sum\lvert f\rvert$ (the meaning of "leverage" or "total leverage" without a qualifier: a short borrows as much as a long of the same size) and net $\sum f$.

Step 5: Sizing schemes are fixed fraction vectors applied every period: full Kelly $f$; fractional Kelly $kf$ with $k$ from the wording ("half" 0.5, "quarter" 0.25, "20% Kelly" 0.2, "double" 2); risk-budgeted Kelly $cf$ with $c$ from Topic 17; equal weight $1/n$ fully invested. Under the quadratic approximation the expected log growth is about $k(2-k)$ times full Kelly while volatility and VaR scale with $k$; above $k=1$ growth falls.

## Topic 17: VaR of the fractions and the limit

**Purpose:** Measure and cap the VaR of a fraction vector.

**When to use:** Kelly fractions are scaled to a VaR limit.

**How to implement:**

Step 1: $z=N^{-1}(\text{level})$, $\sigma_p=\sqrt{f^\top\Sigma f}$.

Step 2: Relative (zero-mean) VaR $z\sigma_p$, the loss below the expected outcome; absolute VaR $z\sigma_p-f^\top\bar r$. Over one day the mean is small and estimated with a large error, so daily limits and "parametric VaR" without a stated mean term are usually the relative form; the absolute form is meant when the task writes the mean into the VaR formula or speaks of the loss relative to zero or initial value.

Step 3: Scale: "comply with", "not exceed": $c=\min(1,\text{limit}/\mathrm{VaR})$; "scale to", "target": $c=\text{limit}/\mathrm{VaR}$, which can also lever up; risk-budgeted fractions $cf$ keep the direction of $f$.

**Limitations and cautions:**

1. An output named with "var" beside a VaR limit or scale factor is value-at-risk, not the variance $f^\top\Sigma f$.

## Topic 18: Simulated wealth paths

**Purpose:** Compare sizing schemes on simulated paths.

**When to use:** After Topics 16 and 17.

**Constraints:**

1. One set of draws serves every scheme (common random numbers), so the schemes differ only in their fractions, unless the task says each scheme has its own seed or draws.
2. Use the generator and draw order the task names; with only a seed, pick one, state it, and use it for every scheme: `np.random.default_rng(seed)` (PCG64) and `np.random.seed(seed)` with `np.random.multivariate_normal` (legacy) give different streams; one call with `size=(paths, days)` fills paths in a different order from a loop per path or per day; `Generator.multivariate_normal` factorizes with `method="svd"` by default.

**How to implement:**

Step 1: Draw all simple asset returns at once, shape (paths, days, assets), from the window's means and covariance.

Step 2: For each scheme, period returns by the account model of Topic 12 (a matrix product of the draws with the fractions).

Step 3: Wealth per path: the starting capital times the cumulative product of $1+x$ along days (`np.cumprod(..., axis=1)`).

Step 4: Drawdown per path, by the reading the task supports: (a) with the starting capital as the first point (the default when each path starts at an initial capital and nothing else is said), or (b) on period-end values only; drawdown $=1-W/\text{running max}(W)$ (`np.maximum.accumulate`), its maximum per path as a positive magnitude; terminal wealth is the last value either way.

Step 5: Metrics per path from that scheme's period returns, then summarized across paths as the task states: Sharpe $\sqrt P\cdot\text{mean}/\text{sd}$ (`ddof` as stated); the mean and the median of terminal wealth are different numbers (the mean exceeds the median for compounded wealth): compute both when both are asked.

**Limitations and cautions:**

1. A risk-free rate can form the excess mean, be deducted in a Sharpe ratio, or be the return on a cash account; only the third creates a cash leg in the simulated returns. An instruction not to subtract it from the Sharpe numerator fixes the Sharpe formula under either account and is not evidence of a cash leg.
2. Under the weighted sum, scaling every fraction by $c>0$ leaves the Sharpe ratio unchanged; under the financed account it does not. Kelly growth derivations are written for the financed account; that is an assumption of the derivation, not a description of the task's account: the fractions are the same, and the simulated account is chosen from the task text.

## Topic 19: Task wording to API arguments

**Purpose:** Choose the arguments that silently change results.

**When to use:** Before calling any of these functions.

**How to implement:**

Step 1: Choose by wording:

| Call | Choice |
|---|---|
| `np.quantile`, `np.percentile` | `method="linear"` (default) interpolates; `"inverted_cdf"` is the step inverse of the empirical CDF; `"lower"`, `"higher"`, `"nearest"`, `"midpoint"` choose between neighbours; `weights=` only with `"inverted_cdf"`; `np.percentile` takes the level in percent |
| `scipy.stats` `dist.fit(x)` | estimates every parameter by maximum likelihood; `floc`, `fscale`, `f0` hold one fixed; returned order is shapes, loc, scale; `stats.norm.fit` returns the mean and the `ddof=0` standard deviation |
| standard deviation | `np.std`, `np.var` default to `ddof=0`; pandas `std` and `cov` to `ddof=1`; "unbiased" means `ddof=1`, "population" or "maximum likelihood" `ddof=0` |
| pandas `ewm` | `alpha=1-lam, adjust=False` is the recursion seeded with the first value; `adjust=True` divides by the weights used so far; `span=s` is $\alpha=2/(s+1)$, `halflife=h` is $\alpha=1-0.5^{1/h}$, `com=c` is $\alpha=1/(1+c)$ |
| pandas `rolling` | needs $W$ values by default; the window ends at and includes the current row; `.shift(1)` moves it to earlier rows |
| random numbers | legacy `np.random.seed` with `np.random.*` vs `np.random.default_rng`: different streams; `multivariate_normal` factorization `method="svd"` by default |
| `scipy.stats.chi2.sf(lr, 1)`, `scipy.special.xlogy(a, b)` | upper-tail p-value of a one-degree-of-freedom likelihood ratio; `xlogy` returns 0 when $a=0$ |
