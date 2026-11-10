# Official API description: pandas.DataFrame.dropna (pandas 3.0.5)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
pandas.DataFrame.dropna(self, *, axis: 'Axis' = 0, how: 'AnyAll | lib.NoDefault' = <no_default>, thresh: 'int | lib.NoDefault' = <no_default>, subset: 'IndexLabel | AnyArrayLike | None' = None, inplace: 'bool' = False, ignore_index: 'bool' = False) -> 'DataFrame | None'

Remove missing values.

See the :ref:`User Guide <missing_data>` for more on which values are
considered missing, and how to work with missing data.

Parameters
----------
axis : {0 or 'index', 1 or 'columns'}, default 0
    Determine if rows or columns which contain missing values are
    removed.

    * 0, or 'index' : Drop rows which contain missing values.
    * 1, or 'columns' : Drop columns which contain missing value.

    Only a single axis is allowed.

how : {'any', 'all'}, default 'any'
    Determine if row or column is removed from DataFrame, when we have
    at least one NA or all NA.

    * 'any' : If any NA values are present, drop that row or column.
    * 'all' : If all values are NA, drop that row or column.

thresh : int, optional
    Require that many non-NA values. Cannot be combined with how.
subset : column label or iterable of labels, optional
    Labels along other axis to consider, e.g. if you are dropping rows
    these would be a list of columns to include.
inplace : bool, default False
    Whether to modify the DataFrame rather than creating a new one.
ignore_index : bool, default ``False``
    If ``True``, the resulting axis will be labeled 0, 1, …, n - 1.

    .. versionadded:: 2.0.0

Returns
-------
DataFrame or None
    DataFrame with NA entries dropped from it or None if ``inplace=True``.
```
