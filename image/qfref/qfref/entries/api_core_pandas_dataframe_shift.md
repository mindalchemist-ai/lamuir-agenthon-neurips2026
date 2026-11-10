# Official API description: pandas.DataFrame.shift (pandas 3.0.5)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
pandas.DataFrame.shift(self, periods: 'int | Sequence[int]' = 1, freq: 'Frequency | None' = None, axis: 'Axis' = 0, fill_value: 'Hashable' = <no_default>, suffix: 'str | None' = None) -> 'DataFrame'

Shift index by desired number of periods with an optional time `freq`.

When `freq` is not passed, shift the index without realigning the data.
If `freq` is passed (in this case, the index must be date or datetime,
or it will raise a `NotImplementedError`), the index will be
increased using the periods and the `freq`. `freq` can be inferred
when specified as "infer" as long as either freq or inferred_freq
attribute is set in the index.

Parameters
----------
periods : int or Sequence
    Number of periods to shift. Can be positive or negative.
    If an iterable of ints, the data will be shifted once by each int.
    This is equivalent to shifting by one value at a time and
    concatenating all resulting frames. The resulting columns will have
    the shift suffixed to their column names. For multiple periods,
    axis must not be 1.
freq : DateOffset, tseries.offsets, timedelta, or str, optional
    Offset to use from the tseries module or time rule (e.g. 'EOM').
    If `freq` is specified then the index values are shifted but the
    data is not realigned. That is, use `freq` if you would like to
    extend the index when shifting and preserve the original data.
    If `freq` is specified as "infer" then it will be inferred from
    the freq or inferred_freq attributes of the index. If neither of
    those attributes exist, a ValueError is thrown.
axis : {0 or 'index', 1 or 'columns', None}, default None
    Shift direction. For `Series` this parameter is unused and defaults to 0.
fill_value : object, optional
    The scalar value to use for newly introduced missing values.
    the default depends on the dtype of `self`.
    For Boolean and numeric NumPy data types, ``np.nan`` is used.
    For datetime, timedelta, or period data, etc. :attr:`NaT` is used.
    For extension dtypes, ``self.dtype.na_value`` is used.
suffix : str, optional
    If str and periods is an iterable, this is added after the column
    name and before the shift value for each shifted column name.
    For `Series` this parameter is unused and defaults to `None`.

Returns
-------
DataFrame
    Copy of input object, shifted.
```
