Polars 1.44.1 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Evaluate expressions and lazy grouped transformations

Polars pl.col returns Expr evaluated in select/with_columns/group_by, without a pandas row index. Use group_by, not groupby; rolling_mean uses min_samples. Sort before shift().over(...). collect executes a LazyFrame. Validate join cardinality and output order. null differs from NaN: fill_null does not fill NaN.

```python
import polars as pl
f=pl.DataFrame({'key':['a','a','b'],'v':[2,3,7]})
r=f.lazy().group_by('key').agg(pl.col('v').sum()).sort('key').collect()
assert r['v'].to_list()==[5,7]
```

## Version check: forms that fail in this version

Removed: Polars DataFrame.groupby -> group_by. Expr.apply -> map_elements(...,return_dtype=...); prefer native expressions. min_periods is deprecated, still accepted; prefer min_samples.

Unavailable/wrong-object: none verified.
