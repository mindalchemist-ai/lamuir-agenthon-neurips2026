# Official API description: pandas.DataFrame.rolling (pandas 3.0.5)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
pandas.DataFrame.rolling(self, window: 'int | dt.timedelta | str | BaseOffset | BaseIndexer', min_periods: 'int | None' = None, center: 'bool' = False, win_type: 'str | None' = None, on: 'str | None' = None, closed: 'IntervalClosedType | None' = None, step: 'int | None' = None, method: 'str' = 'single') -> 'Window | Rolling'

Provide rolling window calculations.

Parameters
----------
window : int, timedelta, str, offset, or BaseIndexer subclass
    Interval of the moving window.

    If an integer, the delta between the start and end of each window.
    The number of points in the window depends on the ``closed`` argument.

    If a timedelta, str, or offset, the time period of each window. Each
    window will be a variable sized based on the observations included in
    the time-period. This is only valid for datetimelike indexes.
    To learn more about the offsets & frequency strings, please see
    :ref:`this link<timeseries.offset_aliases>`.

    If a BaseIndexer subclass, the window boundaries
    based on the defined ``get_window_bounds`` method. Additional rolling
    keyword arguments, namely ``min_periods``, ``center``, ``closed`` and
    ``step`` will be passed to ``get_window_bounds``.

min_periods : int, default None
    Minimum number of observations in window required to have a value;
    otherwise, result is ``np.nan``.

    For a window that is specified by an offset, ``min_periods`` will default
    to 1.

    For a window that is specified by an integer, ``min_periods`` will default
    to the size of the window.

center : bool, default False
    If False, set the window labels as the right edge of the window index.

    If True, set the window labels as the center of the window index.

win_type : str, default None
    If ``None``, all points are evenly weighted.

    If a string, it must be a valid `scipy.signal window function
    <https://docs.scipy.org/doc/scipy/reference/signal.windows.html#module-scipy.signal.windows>`__.

    Certain Scipy window types require additional parameters to be passed
    in the aggregation function. The additional parameters must match
    the keywords specified in the Scipy window type method signature.

on : str, optional
    For a DataFrame, a column label or Index level on which
    to calculate the rolling window, rather than the DataFrame's index.

    Provided integer column is ignored and excluded from result since
    an integer index is not used to calculate the rolling window.

closed : str, default None
    Determines the inclusivity of points in the window

    If ``'right'``, uses the window (first, last] meaning the last point
    is included in the calculations.

    If ``'left'``, uses the window [first, last) meaning the first point
    is included in the calculations.

    If ``'both'``, uses the window [first, last] meaning all points in
    the window are included in the calculations.

    If ``'neither'``, uses the window (first, last) meaning the first
    and last points in the window are excluded from calculations.

    () and [] are referencing open and closed set
    notation respetively.

    Default ``None`` (``'right'``).

step : int, default None
    Evaluate the window at every ``step`` result, equivalent to slicing as
    ``[::step]``. ``window`` must be an integer. Using a step argument other
    than None or 1 will produce a result with a different shape than the input.

method : str {'single', 'table'}, default 'single'

    Execute the rolling operation per single column or row (``'single'``)
    or over the entire object (``'table'``).

    This argument is only implemented when specifying ``engine='numba'``
    in the method call.

Returns
-------
pandas.api.typing.Window or pandas.api.typing.Rolling
    An instance of Window is returned if ``win_type`` is passed. Otherwise,
    an instance of Rolling is returned.

Notes
-----
See :ref:`Windowing Operations <window.generic>` for further usage details
and examples.
```
