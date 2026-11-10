# Cleaning time series: sort, de-duplicate, fill, in a defined order

Use this when input rows must be sorted by time and duplicates removed before returns or signals are computed.

Before filtering timestamped rows by a date-only bound: an inclusive end date covers that whole day, so the cut is the
start of the next day, not 00:00 of the end date.

```python
end_excl = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)        # the time zone of the data's timestamps
kept = df[(df["ts"] >= pd.Timestamp(start_date, tz="UTC")) & (df["ts"] < end_excl)]
assert kept["ts"].max() >= pd.Timestamp(end_date, tz="UTC") or df["ts"].max() < pd.Timestamp(end_date, tz="UTC")  # records later on the end day are kept
print(kept["ts"].min(), kept["ts"].max(), len(df) - len(kept))            # first and last kept times, rows removed
```

## Duplicates and "keep the last record"

- "Keep the last occurrence" refers to the order in which the records appear in the input. A sort only preserves that order among equal keys when it is stable: `df.sort_values("date", kind="stable")` (or `"mergesort"`). The pandas default (`kind="quicksort"`) may reorder rows with the same date, and `drop_duplicates("date", keep="last")` then keeps an arbitrary one of them.
- Equivalent alternatives: keep the original row number (`df.reset_index(names="row")`) and sort by `["date", "row"]`, or de-duplicate first (`df.drop_duplicates("date", keep="last")` on the input order) and sort afterwards. Use whichever matches the task's stated order of operations.
- With several keys (date and ticker), apply the same rule to the full key.

## Order of operations

Follow the task's stated sequence (for example sort, de-duplicate, forward-fill, drop remaining gaps). Forward-filling before removing duplicates, or dropping rows before filling, gives different prices on the affected dates and changes every return computed from them.

## Check

Count the rows removed as duplicates and compare with the number of repeated keys in the input. For a repeated key, print the input rows and the kept row, and confirm that the kept row is the last one in input order.

## Timestamps

- Keep the time of day. Parse timestamps with their time and zone (`pd.to_datetime(col, utc=True)`); flooring to dates (`.dt.date`, `.dt.normalize()`, `.dt.floor("D")`) or reading only the date part merges rows from the same day and moves an endpoint such as 16:00 to 00:00.
- Date-only bounds on timestamped data: an inclusive range `[start, end]` given as dates covers the whole end day. Comparing timestamps with `ts <= pd.Timestamp(end)` stops at 00:00 of the end day and drops its later records; use `ts < pd.Timestamp(end) + pd.Timedelta(days=1)` (and `ts >= pd.Timestamp(start)`), with both sides in the same time zone.
- Durations come from the full timestamps: `(t_end - t_start).total_seconds() / 86400` days, then the day-count basis the task states. Counting whole calendar days drops the hours.
- Writing a UTC timestamp as text: `ts.strftime("%Y-%m-%dT%H:%M:%SZ")` after converting to UTC. `ts.isoformat()` already ends in `+00:00`; appending `"Z"` to it gives an invalid `+00:00Z`. Copy timestamps that the task passes through unchanged (input values echoed in an output) as the original strings.
- Check after cleaning: the row count equals the input count minus the rows the task says to remove (print each removal reason with its count), and the first and last timestamps match the input's, including the time of day.

A window of the last N usable observations is built by removing invalid rows (missing or non-finite values in the columns used) first, then keeping the last N. Slicing the last N rows first and dropping invalid ones afterwards leaves fewer than N and shifts the window start. Check the count after selection.

A month's final trading date is the latest date observed in that month in the data (for example `df.groupby(df.index.to_period('M')).tail(1)` or the index maximum per month). Calendar month-end labels from `resample('ME')` fall on weekends or holidays, and matching them against the data's dates drops those months.
