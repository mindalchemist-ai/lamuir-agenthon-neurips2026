NumPy 2.5.3; pandas 3.0.5 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: pandas: types, labels, joins and grouped sums

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import io
import numpy as np
import pandas as pd
df=pd.DataFrame({'key':['a','a','b'],'value':[2.,3.,7.]},index=[11,14,19])
```

- `read_csv(filepath_or_buffer, dtype=None, parse_dates=None)` returns a DataFrame. Check the actual date dtype before using `.dt`; strings cannot use it directly. `to_datetime(arg,errors='raise',utc=False)` returns a Series, DatetimeIndex or timestamp depending on the input. For mixed formats, use format='mixed' and specify the timezone policy.
```python
raw=pd.read_csv(io.StringIO('date,value\n2021-02-01,2\n')); dates=pd.to_datetime(raw['date'],errors='raise'); assert dates.dt.year.iloc[0]==2021
```
- `to_numeric(arg,errors='raise')` returns a Series/ndarray. pandas 3 no longer supports errors='ignore': raise explicitly or use errors='coerce' and check missing values. A string column need not have object dtype.
```python
num=pd.to_numeric(pd.Series(['2','bad']),errors='coerce'); assert num.iloc[0]==2 and pd.isna(num.iloc[1])
```
- `.loc[label]` selects labels and `.iloc[position]` selects positions. Series `s[0]` does not mean the first item. Filtering preserves original labels; NumPy delete/take accept positions only.
```python
sub=df.loc[df['value']>2]; assert sub.iloc[0].name==14; assert sub.loc[14,'value']==3.; assert np.delete(sub['value'].to_numpy(),0).tolist()==[7.]
```
- A `.loc` label slice includes both end labels: `.loc[:d]` and `.loc[a:b]` contain the rows labelled `d` and `b`. To stop before a label, use a boolean mask `index < d` or positions `.iloc[:i]`; choose the rule from the definition of the window, then check the first and last kept dates.
```python
w=pd.Series(1.,index=pd.to_datetime(['2024-01-02','2024-01-03','2024-01-04'])); d=pd.Timestamp('2024-01-03')
a=w.copy(); a.loc[:d]=0.; assert a.tolist()==[0.,0.,1.]; b=w.copy(); b.loc[b.index<d]=0.; assert b.tolist()==[0.,1.,1.]; assert len(w.loc['2024-01-02':'2024-01-03'])==2
```
- `groupby(by,sort=True,dropna=True,observed=True).sum()` returns a Series/DataFrame and combines repeated keys. Explicitly decide whether unobserved categories and missing keys form groups. `transform` preserves alignment to the original rows.
```python
g=df.groupby('key',sort=True,dropna=False)['value'].sum(); assert g.to_dict()=={'a':5.,'b':7.}; assert df.groupby('key')['value'].transform('sum').tolist()==[5.,5.,7.]
```
- `merge(right,on=None,how='inner',validate=None)` returns a DataFrame. Validate join cardinality before duplicate keys expand rows into a Cartesian product; null keys can match each other. `concat(objs,axis=0)` returns a Series/DataFrame; do not use the removed append method.
```python
joined=df.merge(pd.DataFrame({'key':['a','b'],'scale':[2.,4.]}),on='key',how='left',validate='many_to_one'); assert len(joined)==3; assert len(pd.concat([df,df]))==6
```
- `reindex(index=None,columns=None)` aligns labels. Arithmetic also aligns labels; do not silently convert mismatches into NaNs and fill them with zero. `sort_values(by,kind='stable')` preserves the original order of ties; explicitly list every tie-breaking key for multi-column sorts.
```python
assert df['value'].reindex([19,11]).tolist()==[7.,2.]; assert df.sort_values('key',kind='stable').index.tolist()==[11,14,19]
```
pandas 3 uses Copy-on-Write: chained assignment cannot reliably modify the original table. Use one `.loc[mask,col]=value` assignment. `.to_numpy()` may return a read-only view; request copy=True if modifying it. Missing-return treatment follows the definition; do not forward-fill by default.
```python
cp=df.copy(); cp.loc[cp['key']=='a','value']=0.; assert cp['value'].tolist()==[0.,0.,7.]; arr=df['value'].to_numpy(copy=True); arr[0]=99.; assert df.iloc[0]['value']==2.
```

## Additional explicitly named APIs

- `DataFrame.drop_duplicates(subset=None,keep='first',ignore_index=False)` returns a new table by default. keep='last' retains the last occurrence in the current order, so define sorting and ties first. `Series/DataFrame.ffill(axis=None,limit=None)` returns a new object, propagating past observations along sorted time. Do not backfill future information or fill across different securities.
```python
dup=pd.DataFrame({'date':['2022-02-01','2022-02-01','2022-02-02'],'price':[3.,4.,np.nan]}); kept=dup.drop_duplicates(subset=['date'],keep='last'); assert kept['price'].ffill().tolist()==[4.,4.]
```
- `Series.sum(axis=None,skipna=True,min_count=0)` returns a scalar. An all-missing input can default to zero; use min_count=1 when it must stay missing. `Series.cumprod(skipna=True)` and `Series.cumsum(skipna=True)` return Series with the same labels and handle missing values differently from NumPy.
```python
assert pd.isna(pd.Series([np.nan]).sum(min_count=1)); vals=pd.Series([1.,2.,3.]); assert vals.cumsum().tolist()==[1.,3.,6.] and vals.cumprod().tolist()==[1.,2.,6.]
```
- `pd.Timestamp(...).date()` returns a Python datetime.date. `Series.dt.date` is a Series of dates, not a method call. Establish the timezone before conversion; UTC and local calendar dates may differ.
```python
stamp=pd.Timestamp('2022-02-03 06:30',tz='UTC'); assert stamp.date().isoformat()=='2022-02-03'; assert pd.Series([stamp]).dt.date.iloc[0]==stamp.date()
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

### Changed behavior that fails later, not at the call
- df.groupby(key).apply(f): f receives each group without the grouping column(s) and the result does not contain them (with group_keys=False they are lost; with the default they sit in the index), so a later df['key'] raises KeyError. Use groupby(key)[col].rank()/transform()/agg() and assign the result back to the original frame.

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
