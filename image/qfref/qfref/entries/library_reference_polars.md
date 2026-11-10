Polars 1.44.1 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: Polars: expressions, grouping and lazy execution

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import polars as pl
frame=pl.DataFrame({'key':['a','a','b'],'value':[2.,3.,7.],'date':['2021-04-01','2021-04-02','2021-04-03']})
```

- `pl.col(name)` returns Expr, evaluated in select/with_columns/group_by contexts. `select(*exprs)` returns a DataFrame; `with_columns(*exprs)` returns a new DataFrame without modifying the original. There is no implicit pandas-style row index.
```python
out=frame.with_columns((pl.col('value')*2).alias('double')); assert out['double'].to_list()==[4.,6.,14.] and 'double' not in frame.columns
```
- `group_by(*by,maintain_order=False).agg(*exprs)` returns a DataFrame. Use group_by, not groupby. Make output ordering explicit with sort or maintain_order.
```python
agg=frame.group_by('key').agg(pl.col('value').sum()).sort('key'); assert agg['value'].to_list()==[5.,7.]
```
- `Expr.str.to_date(format=None,strict=True)` returns an Expr producing a Date column. `Expr.shift(n=1)` shifts in current row order. `Expr.rolling_mean(window_size,min_samples=None,center=False)` uses min_samples, renamed from min_periods.
```python
out=frame.with_columns(pl.col('date').str.to_date().alias('date'),pl.col('value').rolling_mean(window_size=2,min_samples=2).alias('avg')); assert out.schema['date']==pl.Date; assert out['avg'].to_list()==[None,2.5,5.]
```
- `Expr.over(partition_by,order_by=None)` returns a window Expr preserving row count. Sort explicitly before within-group lags rather than trusting arbitrary file order.
```python
out=frame.sort(['key','date']).with_columns(pl.col('value').shift(1).over('key').alias('lag')); assert out['lag'].to_list()==[None,2.,None]
```
- `lazy()` returns LazyFrame and `collect()` returns DataFrame. scan_csv/scan_parquet defer reads; optimized execution happens at collect. `join(other,on=...,how=...,validate=...)` returns DataFrame/LazyFrame; check for many-to-many expansion.
```python
out=frame.lazy().filter(pl.col('value')>2).select('key','value').collect(); assert out.height==2; assert frame.join(pl.DataFrame({'key':['a','b'],'scale':[2,4]}),on='key',how='left',validate='m:1').height==3
```
null and NaN are distinct: fill_null does not handle NaN; use is_null/is_nan separately. Row positions do not correspond to a pandas index; preserve business keys during conversion.
```python
out=pl.DataFrame({'x':[None,float('nan'),1.]}).select(pl.col('x').fill_nan(0).fill_null(0)); assert out['x'].to_list()==[0.,0.,1.]
```

## Version check: forms that fail in this version

### Removed or renamed forms
- Polars DataFrame.groupby -> group_by.
- Expr.apply -> map_elements(...,return_dtype=...); prefer native expressions.
min_periods is still accepted with a deprecation warning; prefer min_samples. It is not a removed API.

### Unavailable or wrong-object forms
None among the verified calls shown.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
