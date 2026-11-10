# Intraday bars: complete trading days and lag-weighted volume profiles
The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

`DataFrame.resample` returns one row for every interval of the whole time range, also for intervals with no observation (the afternoon of a half-day, nights, holidays, weekends). Those rows have a missing open, high, low and close and a volume of $0$, so counting rows per day makes every day look complete.

```text
Input: timestamped observations (price, volume); the session bar starts; the number of bars a full day has.
Output: per-day bar table of complete days, the list of excluded days, and a profile per test day.

1. Resample to the bar size with left labels and left-closed intervals, e.g.
   resample('5min', label='left', closed='left').agg({open: 'first', high: 'max', low: 'min', close: 'last', volume: 'sum'}).
2. Drop the empty intervals before counting: keep only rows whose first price is not missing
   (the interval had at least one observation).
3. Keep the session bars by bar start time; count bars per calendar date.
4. A complete day has exactly the full count. Excluded days are the dates that have observations but fewer
   (or more) bars; a date with no observation at all is not a trading day and is not listed.
5. Daily shares: s[d, b] = V[d, b] / sum_b V[d, b], on complete days only.
6. Rolling window: for each test day, the previous K complete days, ordered oldest to most recent.
7. Lag weights: the most recent day has lag 0. With the window index i = 0..K-1 (oldest first),
   lag = K - 1 - i and w = exp(-ln(2) * lag / h). Build the lags once; reversing both the lags and the weights
   puts the largest weight on the oldest day.
8. profile[b] = sum_i w_i * s[i, b] / sum_i w_i, then rescale so the profile sums to 1.
```

Checks:
- Every excluded day has observations and a bar count different from the full count; known half-days are among them; no weekend date is listed.
- In the weight vector ordered oldest to most recent, the last weight is the largest.
- Each profile sums to $1$, and the number of test days equals the number of complete days minus $K$.
