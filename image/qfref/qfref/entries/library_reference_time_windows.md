NumPy 2.5.3; pandas 3.0.5 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: Time series: rolling windows, lag pairing and trading dates

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
import pandas as pd
s=pd.Series([2.,5.,3.,8.,6.,9.],index=pd.date_range('2021-03-01',periods=6))
```

- `rolling(window,min_periods=None,center=False).mean()` returns a Series/DataFrame with the same labels. Integer windows require a full window by default and include the current row. `shift(periods=1,freq=None)` moves values; passing freq moves time labels, a different operation.
```python
m=s.rolling(3,min_periods=3).mean(); assert m.iloc[:2].isna().all(); assert m.iloc[2]==s.iloc[:3].mean(); assert m.shift(1).iloc[3]==m.iloc[2]
```
- `pct_change(periods=1,fill_method=None)` returns fractional changes, not percentages. `std(ddof=1)` is sample standard deviation; pandas defaults to ddof=1, whereas NumPy defaults to 0.
```python
assert np.isclose(s.pct_change(fill_method=None).iloc[1],1.5); assert np.isclose(s.std(ddof=1),np.std(s.to_numpy(),ddof=1))
```
For AR pairing, first construct response=s and lag=s.shift(1) on the complete timeline, then restrict by response date and jointly drop missing pairs. Slicing before shifting loses the first response's valid predecessor outside the window. Preserve calendar gaps; do not independently drop missing values and splice the two sides by position.
```python
pairs=pd.concat({'response':s,'lag':s.shift(1)},axis=1); win=pairs.loc[s.index[2]:s.index[4]].dropna(); assert len(win)==3; assert win.iloc[0]['lag']==s.iloc[1]
```
- `DatetimeIndex.searchsorted(value,side='left')` returns an insertion position and requires ascending dates. left selects the first date not earlier than the target; right selects strictly later. A position equal to the length means no next trading day exists and cannot be passed to iloc. Timezones must agree.
```python
calendar=pd.DatetimeIndex(['2021-03-05','2021-03-08','2021-03-09']); pos=calendar.searchsorted(pd.Timestamp('2021-03-06'),side='left'); assert pos<len(calendar) and calendar[pos]==pd.Timestamp('2021-03-08'); assert calendar.searchsorted(calendar[-1],side='right')==len(calendar)
```
- `resample(rule,label=...,closed=...).agg(...)` produces a resampler, then a Series/DataFrame. Specify interval closure and labels. Use ME for month-end, not the obsolete M alias; MS denotes month-start.
```python
assert len(s.resample('ME',label='right',closed='right').sum())==1
```
Window pairing and strategy execution have distinct clocks. If an engine reads the preceding signal row, do not shift the whole signal again. First label when each column becomes knowable, then choose windows and execution times.

## Additional explicitly named APIs

- `Series.ewm(span=...,adjust=True,min_periods=0,ignore_na=False).mean()` returns a Series on the same index. adjust=False uses a recursion with alpha=2/(span+1), initialized at the first valid observation. adjust=True normalizes finite-history weights, producing different short-sample results. ignore_na controls whether missing positions affect weighting; do not interchange EMA defaults.
```python
recursive=s.ewm(span=3,adjust=False).mean(); assert recursive.iloc[0]==s.iloc[0]; assert np.isclose(recursive.iloc[1],.5*s.iloc[1]+.5*s.iloc[0]); assert not np.isclose(recursive.iloc[1],s.ewm(span=3,adjust=True).mean().iloc[1])
```

## Version check: forms that fail in this version

### Removed or renamed forms
- fillna(method=...) -> ffill()/bfill().
- to_numeric(errors='ignore') -> errors='raise' or 'coerce'; handle invalid values explicitly.
- np.math -> Python math.
- groupby(axis=1) -> df.T.groupby(...).agg(...).T; check dtypes.
- resample('M') -> resample('ME'); to_period('M') still uses M.
- resample('Q') -> resample('QE').
- resample('Y') -> resample('YE').
- DataFrame.applymap -> DataFrame.map.
- np.trapz -> np.trapezoid.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- pd.random -> the specified NumPy RNG interface.
- s.get_loc(label) -> s.index.get_loc(label).
- Series.to_series() -> omit it, or copy(); Index.to_series is valid.
- expanding().shift(...) -> aggregate before shift; ordering follows the definition.
- string Series.dt -> to_datetime(series).dt.
- ndarray.values -> the array itself.
- DatetimeIndex.dt.year -> index.year.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).
- PeriodIndex.dt.year -> index.year.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
