# Official API description: pandas.to_numeric (pandas 3.0.5)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
pandas.to_numeric(arg, errors: 'DateTimeErrorChoices' = 'raise', downcast: "Literal['integer', 'signed', 'unsigned', 'float'] | None" = None, dtype_backend: 'DtypeBackend | lib.NoDefault' = <no_default>)

Convert argument to a numeric type.

If the input is already of a numeric dtype, the dtype will be preserved.
For non-numeric inputs, the default return dtype is `float64` or `int64`
depending on the data supplied. Use the `downcast` parameter
to obtain other dtypes.

Please note that precision loss may occur if really large numbers
are passed in. Due to the internal limitations of `ndarray`, if
numbers smaller than `-9223372036854775808` (np.iinfo(np.int64).min)
or larger than `18446744073709551615` (np.iinfo(np.uint64).max) are
passed in, it is very likely they will be converted to float so that
they can be stored in an `ndarray`. These warnings apply similarly to
`Series` since it internally leverages `ndarray`.

Parameters
----------
arg : scalar, list, tuple, 1-d array, or Series
    Argument to be converted.

errors : {'raise', 'coerce'}, default 'raise'
    - If 'raise', then invalid parsing will raise an exception.
    - If 'coerce', then invalid parsing will be set as NaN.

downcast : str, default None
    Can be 'integer', 'signed', 'unsigned', or 'float'.
    If not None, and if the data has been successfully cast to a
    numerical dtype (or if the data was numeric to begin with),
    downcast that resulting data to the smallest numerical dtype
    possible according to the following rules:

    - 'integer' or 'signed': smallest signed int dtype (min.: np.int8)
    - 'unsigned': smallest unsigned int dtype (min.: np.uint8)
    - 'float': smallest float dtype (min.: np.float32)

    As this behaviour is separate from the core conversion to
    numeric values, any errors raised during the downcasting
    will be surfaced regardless of the value of the 'errors' input.

    In addition, downcasting will only occur if the size
    of the resulting data's dtype is strictly larger than
    the dtype it is to be cast to, so if none of the dtypes
    checked satisfy that specification, no downcasting will be
    performed on the data.

dtype_backend : {'numpy_nullable', 'pyarrow'}
    Back-end data type applied to the resultant :class:`DataFrame`
    (still experimental). If not specified, the default behavior
    is to not use nullable data types. If specified, the behavior
    is as follows:

    * ``"numpy_nullable"``: returns nullable-dtype-backed object
    * ``"pyarrow"``: returns with pyarrow-backed nullable object

    .. versionadded:: 2.0

Returns
-------
ret
    Numeric if parsing succeeded.
    Return type depends on input.  Series if Series, otherwise ndarray.
```
