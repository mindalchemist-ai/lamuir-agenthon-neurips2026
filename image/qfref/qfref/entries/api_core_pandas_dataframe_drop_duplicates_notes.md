# Official API description: pandas.DataFrame.drop_duplicates (pandas 3.0.5)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
pandas.DataFrame.drop_duplicates(self, subset: 'Hashable | Iterable[Hashable] | None' = None, *, keep: 'DropKeep' = 'first', inplace: 'bool' = False, ignore_index: 'bool' = False) -> 'DataFrame | None'

Return DataFrame with duplicate rows removed.

Considering certain columns is optional. Indexes, including time indexes
are ignored.

Parameters
----------
subset : column label or iterable of labels, optional
    Only consider certain columns for identifying duplicates, by
    default use all of the columns.
keep : {'first', 'last', ``False``}, default 'first'
    Determines which duplicates (if any) to keep.

    - 'first' : Drop duplicates except for the first occurrence.
    - 'last' : Drop duplicates except for the last occurrence.
    - ``False`` : Drop all duplicates.

inplace : bool, default ``False``
    Whether to modify the DataFrame rather than creating a new one.
ignore_index : bool, default ``False``
    If ``True``, the resulting axis will be labeled 0, 1, …, n - 1.

Returns
-------
DataFrame or None
    DataFrame with duplicates removed or None if ``inplace=True``.

Notes
-----
This method requires columns specified by ``subset`` to be of hashable type.
Passing unhashable columns will raise a ``TypeError``.
```
