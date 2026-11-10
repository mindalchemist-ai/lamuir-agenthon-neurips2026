# Official API description: pandas.core.window.rolling.Rolling.std (pandas 3.0.5)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
pandas.core.window.rolling.Rolling.std(self, ddof: 'int' = 1, numeric_only: 'bool' = False, engine: "Literal['cython', 'numba'] | None" = None, engine_kwargs: 'dict[str, bool] | None' = None)

Calculate the rolling standard deviation.

Parameters
----------
ddof : int, default 1
    Delta Degrees of Freedom.  The divisor used in calculations
    is ``N - ddof``, where ``N`` represents the number of elements.

numeric_only : bool, default False
    Include only float, int, boolean columns.

engine : str, default None
    * ``'cython'`` : Runs the operation through C-extensions from cython.
    * ``'numba'`` : Runs the operation through JIT compiled code from numba.
    * ``None`` : Defaults to ``'cython'`` or
      globally setting ``compute.use_numba``

engine_kwargs : dict, default None
    * For ``'cython'`` engine, there are no accepted ``engine_kwargs``
    * For ``'numba'`` engine, the engine can accept ``nopython``, ``nogil``
      and ``parallel`` dictionary keys. The values must either be ``True`` or
      ``False``.

    The default ``engine_kwargs`` for the ``'numba'`` engine is
    ``{'nopython': True, 'nogil': False, 'parallel': False}``.

Returns
-------
Series or DataFrame
    Return type is the same as the original object with ``np.float64`` dtype.

Notes
-----
The default ``ddof`` of 1 used in :meth:`Series.std` is different
than the default ``ddof`` of 0 in :func:`numpy.std`.

A minimum of one period is required for the rolling calculation.
```
