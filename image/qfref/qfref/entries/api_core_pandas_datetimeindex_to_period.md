# Official API description: pandas.DatetimeIndex.to_period (pandas 3.0.5)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
pandas.DatetimeIndex.to_period(self, freq=None) -> 'PeriodArray'

Cast to PeriodArray/PeriodIndex at a particular frequency.

Converts DatetimeArray/Index to PeriodArray/PeriodIndex.

Parameters
----------
freq : str or Period, optional
    One of pandas' :ref:`period aliases <timeseries.period_aliases>`
    or a Period object. Will be inferred by default.

Returns
-------
PeriodArray/PeriodIndex
    Immutable ndarray holding ordinal values at a particular frequency.
```
