pandas 3.0.5 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Parse dates, align labeled data and locate sessions

Parse strings with to_datetime before .dt; for mixed layouts in one column use format='mixed' (errors='coerce' silently gives NaT: count isna() first). Align labeled objects jointly (loc: labels, iloc: positions). searchsorted on sorted dates: side='left' gives the first not-earlier date, 'right' the first later one; position == length means none. Series uses .dt; DatetimeIndex/PeriodIndex expose fields directly; datetime64 scalars need pd.Timestamp(v).strftime. Convert timezones before taking dates; use supplied trading dates, not an invented calendar.

```python
import pandas as pd
s=pd.to_datetime(pd.Series(['2021-07-04','07/05/2021']),format='mixed'); assert s.notna().all()
assert s.searchsorted(pd.Timestamp('2021-07-04'),side='right')==1
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: string Series.dt -> to_datetime(series).dt. DatetimeIndex.dt.year -> index.year. PeriodIndex.dt.year -> index.year. datetime64.strftime -> pd.Timestamp(value).strftime(...).
