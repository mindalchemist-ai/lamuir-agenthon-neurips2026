# Official API description: pandas.DataFrame.ffill (pandas 3.0.5)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
pandas.DataFrame.ffill(self, *, axis: 'None | Axis' = None, inplace: 'bool' = False, limit: 'None | int' = None, limit_area: "Literal['inside', 'outside'] | None" = None) -> 'Self'

Fill NA/NaN values by propagating the last valid observation to next valid.

Parameters
----------
axis : {0 or 'index'} for Series, {0 or 'index', 1 or 'columns'} for DataFrame
    Axis along which to fill missing values. For `Series`
    this parameter is unused and defaults to 0.
inplace : bool, default False
    If True, fill in-place. Note: this will modify any
    other views on this object (e.g., a no-copy slice for a column in a
    DataFrame).
limit : int, default None
    If method is specified, this is the maximum number of consecutive
    NaN values to forward/backward fill. In other words, if there is
    a gap with more than this number of consecutive NaNs, it will only
    be partially filled. If method is not specified, this is the
    maximum number of entries along the entire axis where NaNs will be
    filled. Must be greater than 0 if not None.
limit_area : {`None`, 'inside', 'outside'}, default None
    If limit is specified, consecutive NaNs will be filled with this
    restriction.

    * ``None``: No fill restriction.
    * 'inside': Only fill NaNs surrounded by valid values
      (interpolate).
    * 'outside': Only fill NaNs outside valid values (extrapolate).

    .. versionadded:: 2.2.0

Returns
-------
Series/DataFrame
    Object with missing values filled.
```
