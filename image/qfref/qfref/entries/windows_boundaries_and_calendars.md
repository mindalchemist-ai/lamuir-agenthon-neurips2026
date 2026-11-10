# Windows, boundaries and calendars: endpoints, trailing windows, trading versus calendar days, time zones, resampling

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Endpoints of a date or time range

**Purpose:** Decide whether each end of a range is kept.

**When to use:** The task cuts data by dates or times, or compares a value with a threshold.

**Constraints:**

1. Write the inequality the task states: on discrete data `>=` and `>` give different counts whenever a value equals the threshold.

**How to implement:**

Step 1: Read the wording and choose the endpoints:

| Wording | Endpoints |
|---|---|
| "from A to B inclusive", "through B", "on or before B", "between A and B" with dates | both A and B kept |
| "strictly", "before B", "after A", "up to but not including" | that endpoint excluded |
| a date-only end bound on timestamped rows | the whole end day kept: cut at the start of the next day |
| silent | both ends kept for date ranges; say so in a comment |

Step 2: Slice accordingly: label slicing `df.loc[a:b]` keeps both labels; position slicing `df.iloc[i:j]` excludes position $j$.

**Double check:**

1. Print the first and last kept date and the row count; compare them with the endpoints chosen in Step 1, and re-slice if an end is off by one.

## Topic 2: Trailing and rolling windows

**Purpose:** Build windows that include or exclude the current row as the task means.

**When to use:** A statistic over the last $N$ rows or days (rolling mean, volatility, beta, quantile).

**Constraints:**

1. A statistic used to trade or forecast at $t$ must not see $t$'s own value: shift before rolling, `x.shift(1).rolling(N)`.

**How to implement:**

Step 1: Choose each option from the wording:

| Choice | Options | Pick by |
|---|---|---|
| Current row | included ("trailing N days up to and including t", "over the last N days") or excluded ("prior N days", "before t", "lagged", "known at t" for a forecast used at t) | the wording, and Constraint 1 |
| Incomplete windows | NaN until N rows exist, or computed on fewer rows (`min_periods`) | the task's minimum count; silent: NaN until the window is full, and drop those rows downstream |
| Window count | N rows of data, or N calendar days (`rolling("30D")`) | "N observations", "N trading days", "N rows": rows; "N calendar days", "30D": time-based |

**Double check:**

1. At one row $t$, recompute the statistic by hand from the slice it should cover (the $N$ rows before $t$, or ending at $t$) and compare with the rolling value; a mismatch means the window includes or excludes the wrong row.

## Topic 3: Trading days and calendar days

**Purpose:** Move between dates as the task counts them.

**When to use:** "k days later", "next trading day", holding periods, annualization.

**How to implement:**

Step 1: "k trading days later", "next trading day" and "k rows" move along the dates present in the data: look the date up in the data's date column (`DatetimeIndex.searchsorted`, `side="right"` for the next one) and step by position.

Step 2: "k calendar days" uses date differences; apply a business-day rule (following, modified following) only when the task names one.

Step 3: Annual counts follow the same split: about 252 trading days, 365 calendar days.

**Limitations and cautions:**

1. Calendar arithmetic (adding one day) lands on weekends and holidays; the next trading day after a Friday is the following Monday only if it is in the data.

**Double check:**

1. Every date produced by Step 1 is in the data's date column.

## Topic 4: Timestamps and time zones

**Purpose:** Parse numeric and zoned timestamps correctly and take calendar dates in the right zone.

**When to use:** Inputs carry Unix times or times in a stated zone, or the task defines sessions in exchange local time.

**Constraints:**

1. A timestamp used to compute a duration (time to maturity, holding period) does not change how a date or expiry field is written in the outputs. Write such a field in the form the task's own files use for it (the labels listed in a rules file, a schema example, an identifier such as an instrument name), and write a raw timestamp only in a column that asks for one. Reason: readers join and compare outputs by those labels; a field rewritten as milliseconds no longer matches any of them.

**How to implement:**

Step 1: List the time columns. For each one, print a sample value and record its unit and zone: an integer near $1.7\times10^{9}$ is seconds and near $1.7\times10^{12}$ milliseconds; text with an offset or "Z" is zoned; text without one is naive, and the task text says which zone it is in.

Step 2: Parse each column once into aware datetimes: `pd.to_datetime(x, unit="s", utc=True)` or `unit="ms"` for Unix times; `pd.to_datetime(x, utc=True)` for zoned text; `pd.to_datetime(x).dt.tz_localize(zone)` for naive text in a known zone (`tz_localize` attaches a zone; it does not shift the clock).

Step 3: Convert to the zone in which the task defines dates or sessions with `.dt.tz_convert(zone)` (this shifts the clock and keeps the instant).

Step 4: Only after Step 3, take calendar dates with `.dt.normalize()` or `.dt.date`, and cut sessions defined in exchange local time.

Step 5: Compute durations from the parsed instants (for example `(expiry - valuation).dt.total_seconds()` divided by the year length the task states).

Step 6: Write each date or expiry field in the form of Constraint 1; keep the parsed values only for computation.

**Double check:**

1. Print one timestamp in UTC and in the session zone with its date; a time late in the UTC day can be the previous evening in a western zone.
2. Compare the distinct values of each written date or expiry column with the labels the task's files use for it; if the column holds large integers or a different format, rewrite it in that form.

## Topic 5: Resampling to bars or month ends

**Purpose:** Aggregate to a coarser frequency with the right value, label and treatment of empty bars.

**When to use:** Monthly, weekly or intraday bars are built from finer data.

**How to implement:**

Step 1: Choose each option from the wording:

| Choice | Options | Pick by |
|---|---|---|
| Month-end value | last valid observation `.resample("ME").last()` (skips NaN), the value on the calendar month end, or the month mean `.mean()` | "month-end", "last observation of the month": last; "monthly average": mean |
| Label | the bar's start or its end (`label=` and `closed=`) | the task's bar description |
| Empty bars | `sum` / `count` give 0, `first` / `last` / `max` / `min` give NaN | keep, fill or drop as the task says; identify empty bars by the count, not by a zero sum |

**Double check:**

1. Check the first written timestamp against the bar description (start or end label), and count the empty bars by `count() == 0` before deciding how to treat them.
