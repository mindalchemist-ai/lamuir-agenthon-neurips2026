# Event-study conventions: event time, market model, CAR/CAAR, cross-event tests

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Event time as a row position

**Purpose:** Locate event day 0 and every window on the data's trading-day index.

**When to use:** Any study of returns or rate changes around dated events.

**Constraints:**

1. Day 0 is a row of the merged return index, not a calendar date plus $k$ days; every other offset is a row offset.

**How to implement:**

Step 1: Resolve "the event date, or the next trading day" against the date column: the position of the first row dated on or after the event date (`DatetimeIndex.searchsorted(date, side="left")`).

Step 2: Estimation window rows $\text{pos}+e_{lo},\dots,\text{pos}+e_{hi}$ and event window rows $\text{pos}+w_{lo},\dots,\text{pos}+w_{hi}$, with the relative days the task sets.

Step 3: Apply the task's validity rule to events whose windows run past the data's ends.

Step 4: A change across event days (of a level, a rate, or a spread between two series) is one series read at two row offsets: convert that series to the reporting unit once (for example percent to basis points), then take the difference of the two rows.

**Double check:**

1. The estimation window ends before the event window starts; the row found in Step 1 is dated on or after the event date.
2. A change in Step 4 equals the change of the raw series times the unit factor; subtracting a raw-unit value from a converted series mixes units.

## Topic 2: Pre-event features

**Purpose:** Pick the rows that features defined "before the event" use.

**When to use:** The panel includes values, changes or statistics measured before each event.

**Constraints:**

1. Rows are positions on the filtered valid-row index of the underlying daily series (the yield, price or return table), not on the table of events: "the $w$ valid dates before the event" are $w$ daily rows, however many earlier events fall in them.

**How to implement:**

Step 1: Find the event's position pos on the filtered valid-row index (`Index.get_loc`).

Step 2: Read each feature from the rows its definition names:

| Definition says | Rows |
|---|---|
| the value $k$ valid rows before the event | pos $-k$ (the day before is pos $-1$) |
| a change from $k$ rows before to $m$ rows before ($k>m$) | $x_{\text{pos}-m}-x_{\text{pos}-k}$ |
| a statistic over the $w$ rows immediately before | rows pos $-w$ to pos $-1$; the value it standardises comes from its own stated row |
| a regression of $y_j$ on $y_{j-1}$ for $j=a,\dots,b$ | pairs built on the full series, then rows $a$ to $b$ kept: $b-a+1$ pairs |

Step 3: A trailing statistic of a pre-event quantity (for example a z-score of the level on the day before): take the value from its stated row (pos $-1$) and the window from its stated rows (pos $-w$ to pos $-1$); reading a rolling column at the event row instead standardises the event-day value against a window shifted by one.

Step 4: A lagged regression over a stated range: build the lag on the full series (`shift(1)`), then keep rows $a$ to $b$ of both; slicing first and lagging inside the slice loses the pair at $j=a$.

**Double check:**

1. For the first event, print the dates of the rows each feature uses (its value row, its window ends, the two rows of each change) next to the event date, and compare every one with its definition; the number of regression pairs is $b-a+1$.

## Topic 3: Market model, abnormal returns, CAR and CAAR

**Purpose:** Estimate normal returns and accumulate abnormal returns.

**When to use:** Abnormal returns relative to a market model.

**How to implement:**

Step 1: On the estimation window, fit the security return on a constant plus the market return (ordinary least squares, for example `np.linalg.lstsq` on a design that includes a column of ones, or `statsmodels` OLS after `add_constant`): intercept $\alpha$, slope $\beta$, residuals $e$.

Step 2: Abnormal returns on the event window: $AR_t=R_t-(\alpha+\beta R_{m,t})$.

Step 3: Stack the valid events' abnormal returns as an $N\times M$ matrix: $CAR_i$ is a row sum, $CAAR(t)$ a column mean (cumulated over the window as the task defines).

**Double check:**

1. The residuals sum to zero and are orthogonal to the market return (to about $10^{-10}$); the sum of the column means equals the mean of the row sums.

## Topic 4: Standardized tests and cross-correlation

**Purpose:** Test abnormal returns across events with standardized statistics.

**When to use:** Patell, BMP or Kolari-Pynnonen tests.

**How to implement:**

Step 1: Per event, $s_i^2=\sum e^2/(L_i-2)$, with $L_i$ estimation days.

Step 2: Prediction-error correction on each event day:

$$C_{it}=1+\frac1{L_i}+\frac{(R_{m,t}-\bar R_m)^2}{\sum(R_m-\bar R_m)^2}$$

(sums over the estimation window).

Step 3: Standardized abnormal returns $SAR_{it}=AR_{it}/(s_i\sqrt{C_{it}})$ and the window value $CSAR_i=\sum_tSAR_{it}/\sqrt M$.

Step 4: BMP statistic: $t_{BMP}=\sqrt N\cdot\text{mean}/\text{sd}$ over events, using the cross-sectional sample standard deviation (`ddof=1`).

Step 5: Average cross-correlation $\bar\rho$: the mean pairwise Pearson correlation of estimation residuals matched on the calendar dates both series share (index each residual series by its dates and intersect; never align by row number).

Step 6: Dependence adjustment, by the reading the task names: (i) $t_{BMP}/\sqrt{1+(N-1)\bar\rho}$; (ii) Kolari-Pynnonen, $t_{BMP}\sqrt{(1-\bar\rho)/(1+(N-1)\bar\rho)}$, whose extra $\sqrt{1-\bar\rho}$ undoes the shrinkage that correlation causes in the BMP cross-sectional variance.

## Topic 5: Rank test across events

**Purpose:** A nonparametric test of abnormal returns.

**When to use:** The task asks for a rank (Corrado-type) test.

**How to implement:**

Step 1: Per event, pool the estimation residuals with the window abnormal returns, rank them jointly with midranks for ties (`scipy.stats.rankdata`, default `"average"`), and set $U=\text{rank}/(T_i+1)$, $d=U-\tfrac12$.

Step 2: Reading A, portfolio time-series standard deviation (Corrado 1989): $D_t$ is the mean over events of $d$ on pooled day $t$; $S=\sqrt{\text{mean of }D_t^2}$ over all pooled days; day statistic $D_t/S$; window statistic $\sum_tD_t/(\sqrt M\,S)$. Needs one pooled-day grid (equal $T_i$).

Step 3: Reading B, per-event standardization aggregated across events: $sd_i=\sqrt{\text{mean}(d_i^2)}$ over that event's own days, $\theta_{it}=d_{it}/sd_i$; day statistic $\sqrt N\cdot\text{mean}_i\theta_{it}$; window statistic $\sum_t(\text{day statistic})/\sqrt M$.

**Limitations and cautions:**

1. Both readings share the numerator; only the denominator differs, so state which one is used.

**Double check:**

1. Without ties, the mean of $d^2$ over $T$ pooled days equals $(T-1)/(12(T+1))$.

## Topic 6: Sign-flip and permutation p-values

**Purpose:** Exact or randomization p-values for a regression coefficient.

**When to use:** The task asks for a sign-flip or permutation test.

**Constraints:**

1. The draw that reproduces the observed sample (all signs $+1$, the identity permutation) counts as a hit.
2. Compare with a roundoff margin: a draw is a hit when $\lvert b^*\rvert\ge\lvert b_{obs}\rvert(1-10^{-12})$; an exact $\ge$ can drop the identity draw by floating-point noise and change the p-value by one draw.

**How to implement:**

Step 1: Keep the design fixed across draws and precompute its pseudo-inverse (`np.linalg.pinv`).

Step 2: Build all sign vectors (the first sign fixed at $+1$ when the statistic is symmetric; `itertools.product`) as a matrix, form every resampled response as fitted values plus signed residuals, and get all coefficients at once by one matrix product with the pseudo-inverse.

Step 3: Mark hits with the roundoff margin, as a vector over all draws:

$$\text{hit}_d=\Big(\lvert b^*_d\rvert\ \ge\ \lvert b_{obs}\rvert\,(1-10^{-12})\Big)$$

Never compare $\lvert b^*_d\rvert\ge\lvert b_{obs}\rvert$ exactly: the identity draw reproduces $b_{obs}$ only up to floating-point noise, so an exact comparison can miss it and moves the p-value by one draw.

Step 4: p-value: the share of draws that are hits (the mean of the hit vector).

**Double check:**

1. Assert that the identity draw (all signs $+1$) is a hit before reporting the p-value; if it is not, the comparison has no margin: apply Step 3.

## Topic 7: Full panel versus regression subset

**Purpose:** Report summary fields from the rows their definitions name.

**When to use:** The panel is summarized and some regressions use a subset of it.

**Constraints:**

1. A summary field without a subset qualifier, reported beside an unqualified count, ranges over the same rows as that count; a count and a first or last date reported side by side come from the same frame.

**How to implement:**

Step 1: Keep the full panel and each regression sample under different names.

Step 2: Take every summary field from the frame its definition names.

Step 3: When several regressions run on the same sample, each takes its own left-hand column from its own equation; a left-hand variable left over from the previous fit silently regresses the wrong series. Print each fit's left- and right-hand columns.

Step 4: When the task says to round the panel and use the rounded values as inputs, read the written panel back and regress on that, after checking that every numeric column is a float (a cell such as `[0.3133]` is a one-element array written as text, and rounding skipped it). If the panel changes after a regression ran, rerun the regressions.

**Double check:**

1. The reported count equals the number of rows in the frame its definition names, and the first and last dates come from the same frame.

## Topic 8: Task wording to API arguments

**Purpose:** Choose the arguments that silently change results.

**When to use:** Before calling any of the functions below.

**How to implement:**

Step 1: Choose by the task's wording:

| Call | Choice and wording |
|---|---|
| `DatetimeIndex.searchsorted(v, side=...)` | `"left"`: first row dated on or after $v$ ("on or after", "the event date or the next trading day"); `"right"`: first row dated after $v$ ("strictly after"); `searchsorted(v, side="right") - 1`: last row dated on or before $v$ ("on or before", "as of") |
| `pd.merge_asof(..., direction=..., allow_exact_matches=...)` | `"backward"` (default): last key at or before $v$ ("most recent as of"); `"forward"`: first key at or after $v$ ("next available"); `allow_exact_matches=False` makes either strict; both frames sorted on the key |
| `Series.shift(k)` | $k>0$ takes the value $k$ rows earlier ("previous", "lagged"); after filtering to valid rows, $k$ counts valid rows ("valid dates, not calendar days": filter first, then shift) |
| `Series.rolling(w, min_periods=...)` | the window ends at and includes the current row; "the $w$ rows before the event" is `shift(1).rolling(w)`; `min_periods=1` uses all available rows if fewer |
| standard deviation | `np.std` defaults to `ddof=0`, pandas `.std` to `ddof=1`; a "sample" standard deviation means `ddof=1` |
| `np.linalg.lstsq`, `sm.OLS` | add no intercept; `sm.add_constant` with the default `has_constant="skip"` adds nothing when a constant column exists, `"add"` always adds one |
| `OLS(...).fit(cov_type="HAC", cov_kwds={"maxlags": L})` | Bartlett weights $1-l/(L+1)$; `use_correction=False` (default) leaves the sandwich unscaled, `True` multiplies it by $n/(n-k)$; `"nonrobust"` is $s^2(X'X)^{-1}$ with $s^2=SSE/(n-k)$ |
| `scipy.stats.rankdata(a, method=...)` | `"average"` (default) gives midranks to ties; `"min"` and `"ordinal"` rank ties differently |
| `scipy.stats.ttest_1samp(a, 0, alternative=...)` | uses `ddof=1`; two-sided p is $2\,t.\mathrm{sf}(\lvert t\rvert,n-1)$; `"greater"` gives $t.\mathrm{sf}(t,n-1)$ |
| `DataFrame.corr()` vs `np.corrcoef` | `corr` drops missing values pairwise; `corrcoef` returns NaN if any value is missing, so align on common dates first |
