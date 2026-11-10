# Backtest of a portfolio rebalanced from rolling estimates (regimes, inverse volatility, risk metrics): workflow

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Choices to settle before coding

**Purpose:** Fix every choice that changes the numbers, from the task's wording.

**When to use:** Weights are set on scheduled dates from rolling-window estimates (correlation eigenvalues, a regime label, volatilities) and the realised strategy is then evaluated. Read the scenario table in the VaR and ES conventions card first: it says which rebalance dates, initial holdings and earning day fit the task's wording.

**How to implement:**

Step 1: Settle each row of this table from the task text and print the choices:

| Topic | Choice | Options and the wording that selects them |
|---|---|---|
| 3 | Matrix for the eigenvalues | correlation (unit-free, trace $n$) or covariance (keeps scale, trace = total variance); "correlation" / "covariance" in the text decides |
| 3 | Estimate window | equal-weighted rolling window of $W$ rows, or exponentially weighted with a stated half-life; expanding window when the text says "all data to date" |
| 3 | Rows an estimate for day $t$ uses | rows before $t$ when it sets day $t$'s regime or weights; rows through $t$ when it is dated at the close of $t$ and used from $t+1$ |
| 3 | Regime rule | fixed thresholds with the stated comparison signs; thresholds that move with the indicator's own moving average and dispersion; a standardized shift (short minus long average over a long standard deviation); the text names which |
| 3 | Weights | inverse volatility $1/\sigma$, inverse variance $1/\sigma^2$, equal risk contribution, or equal weight; then scaled by a regime budget, by a volatility target, or not scaled. A budget below 1 leaves cash that earns nothing unless the text gives a cash rate |
| 4 | Rebalance calendar | month-end rows, month-start rows, weekly, every $N$ rows, or on regime changes; dates are rows present in the data |
| 4 | Last data row | excluded when weights set at a close earn from the next day; included when the text rebalances at the open of the same day |
| 5 | Holdings before the first rebalance | equal weights, cash, the first estimate, or start the evaluation at the first rebalance (scenario table) |
| 5 | When new weights earn | from the next day (set at a close) or the same day (set at the open); never both a loop delay and an extra shift |
| 5 | Costs | none unless stated; a proportional cost charges turnover $\sum_i\lvert w_i^{new}-w_i^{old}\rvert$ at each rebalance |
| 6 | Annualised return | arithmetic mean times periods per year, or geometric $(1+R_{total})^{P/n}-1$; "mean daily return x 252" or "CAGR" in the text |
| 6 | Sharpe ratio | zero risk-free rate unless given; `ddof` as stated |
| 6 | Drawdown | on the wealth path, as a positive magnitude unless the text reports it negative |
| 6 | VaR / CVaR of the strategy | one trailing window, the full evaluated sample, or a rolling series (then the text says which statistic of it); quantile rule and tail mean per the VaR and ES conventions card |
| 6 | Average weight of an asset | over all evaluated days (held weights) or over rebalance dates (target weights); "average weight" without a qualifier is the time average of the held weights |

## Topic 2: Cleaning, counting and the estimation window

**Purpose:** Build the return table that every later step uses, and count it correctly.

**When to use:** Always first.

**How to implement:**

Step 1: Clean the raw returns with the rules of the VaR and ES conventions card (duplicate dates, missing values) and keep the cleaned table.

Step 2: The count of valid observations is the number of rows after cleaning.

Step 3: Cut the estimation window from the cleaned table (the last rows the task names, or all of them).

**Double check:**

1. The count of valid observations is at least the window length; a reported count of valid observations is the cleaned row count, not the window length.

## Topic 3: Rolling estimates known before each day

**Purpose:** Estimate, for each evaluated day, the indicator, the regime and the target weights from data available at that time.

**When to use:** After Topic 2.

**Constraints:**

1. An estimate that sets day $t$'s regime or weights uses rows $t-W,\dots,t-1$ only.

**How to implement:**

Step 1: For each day $t$ from $W$ to the end, take the window of the previous $W$ rows.

Step 2: Eigenvalues of the window's correlation (or covariance) matrix with a symmetric solver (`np.linalg.eigvalsh`), sorted largest first; the share of the top $k$:

$$\mathrm{AR}_t=\frac{\sum_{i\le k}\lambda_i}{\sum_i\lambda_i}$$

Step 3: Regime from the indicator with the thresholds and comparison signs exactly as the task states.

Step 4: Weights, for inverse volatility $w_i\propto1/\sigma_i$ (standard deviation with the task's `ddof`), normalized to sum to one, then times the regime budget.

Step 5: Random-matrix reference, when asked: the Marchenko-Pastur upper edge for a $W\times n$ correlation matrix,

$$\lambda_{+}=\left(1+\sqrt{n/W}\right)^2$$

**Double check:**

1. The number of evaluated days equals the number of rows minus $W$; the trace of each correlation matrix is $n$; $\lambda_+>1$. Summary statistics of these series use the task's `ddof` consistently.

## Topic 4: Rebalance dates

**Purpose:** Choose rebalance dates that are rows of the data.

**When to use:** Scheduled rebalancing (month ends and similar).

**Constraints:**

1. Rebalance dates are dates present in the data and among the evaluated days; a calendar month end that is a weekend, or later than the last row, is not one.

**How to implement:**

Step 1: Put the evaluated dates in a Series indexed by themselves and, per calendar month (`dt.to_period("M")`), keep the date equal to the group maximum (`groupby(...).transform("max")`). On a DatetimeIndex, `groupby` returns a plain dict of labels, so wrap the dates in a Series first.

Step 2: If `resample` is used instead, take its values, `resample("ME").last().dropna()`, which are the last dates present in each month, not its index, whose labels are calendar month ends.

Step 3: Drop the last data row when weights set at a close earn from the next day.

**Double check:**

1. Every rebalance date is an evaluated day; the number of rebalances is at most the number of calendar months in the evaluated period.

## Topic 5: Holdings and the daily return loop

**Purpose:** Compute one return per evaluated day, with weights applied at the right time.

**When to use:** After Topics 3 and 4.

**Constraints:**

1. Delay the new weights exactly once: the loop below already applies them from the next day; no extra shift or forward fill on top.

**How to implement:**

Step 1: Holdings before the first rebalance, by the reading the task supports (write it in a comment): equal weights; cash (zero weights); the first estimate; or start the evaluation after the first rebalance with its weights.

Step 2: Loop over the evaluated days in order:

1. record the weights held at the start of the day;
2. the day's return is the sum of held weights times that day's asset returns;
3. if the day is a rebalance date, replace the held weights by that day's target weights (they earn from the next day);
4. with a proportional cost, subtract the cost rate times the turnover on the rebalance day.

**Double check:**

1. The return series has one value per evaluated day.

## Topic 6: Performance and risk of the strategy

**Purpose:** Summarize the realised strategy.

**When to use:** After Topic 5.

**How to implement:**

Step 1: Annualised return (mean times periods per year, or geometric by Topic 1) and volatility (standard deviation with the task's `ddof` times $\sqrt{P}$); Sharpe ratio as their ratio with the stated risk-free rate.

Step 2: Wealth $W_t=\prod(1+r)$ (`cumprod`) and maximum drawdown $\max_t(1-W_t/\max_{s\le t}W_s)$, as a positive magnitude.

Step 3: VaR and CVaR on the sample Topic 1 chose (for one trailing window, its last rows of realised returns), with the quantile rule and tail mean of the VaR and ES conventions card.

Step 4: Win rate as the share of days with a positive return; average weights by the reading in Topic 1.

**Double check:**

1. The trailing window has the stated length; as losses, CVaR is at least VaR and VaR is positive; with a short window and a high level the tail may hold one observation, so state the quantile rule used.

## Topic 7: Writing the deliverables

**Purpose:** Write results that match the task's schema.

**When to use:** At the end of each stage that completes a deliverable.

**How to implement:**

Step 1: Write each file as soon as its values are computed.

Step 2: Read every file back.

**Double check:**

1. Every requested key is present, counts are integers, and magnitudes are reported as the task states (positive losses and drawdowns).
