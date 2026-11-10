# Official API description: arch.univariate.base.ARCHModelResult.forecast (arch 8.0.0)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
arch.univariate.base.ARCHModelResult.forecast(self, params: Union[numpy.ndarray[tuple[int], numpy.dtype[numpy.float64]], pandas.Series, NoneType] = None, horizon: int = 1, start: Union[int, str, datetime.datetime, numpy.datetime64, pandas.Timestamp, NoneType] = None, align: Literal['origin', 'target'] = 'origin', method: Literal['analytic', 'simulation', 'bootstrap'] = 'analytic', simulations: int = 1000, rng: collections.abc.Callable[[int | tuple[int, ...]], numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]]] | None = None, random_state: numpy.random.mtrand.RandomState | None = None, *, reindex: bool = False, x: Union[dict[Optional[collections.abc.Hashable], Union[numpy.ndarray, pandas.DataFrame, pandas.Series]], numpy.ndarray, pandas.DataFrame, pandas.Series, NoneType] = None) -> 'ARCHModelForecast'

Construct forecasts from estimated model

Parameters
----------
params : ndarray, optional
    Alternative parameters to use.  If not provided, the parameters
    estimated when fitting the model are used.  Must be identical in
    shape to the parameters computed by fitting the model.
horizon : int, optional
   Number of steps to forecast
start : {int, datetime, Timestamp, str}, optional
    An integer, datetime or str indicating the first observation to
    produce the forecast for.  Datetimes can only be used with pandas
    inputs that have a datetime index. Strings must be convertible
    to a date time, such as in '1945-01-01'.
align : str, optional
    Either 'origin' or 'target'.  When set of 'origin', the t-th row
    of forecasts contains the forecasts for t+1, t+2, ..., t+h. When
    set to 'target', the t-th row contains the 1-step ahead forecast
    from time t-1, the 2 step from time t-2, ..., and the h-step from
    time t-h.  'target' simplified computing forecast errors since the
    realization and h-step forecast are aligned.
method : {'analytic', 'simulation', 'bootstrap'}, optional
    Method to use when producing the forecast. The default is analytic.
    The method only affects the variance forecast generation.  Not all
    volatility models support all methods. In particular, volatility
    models that do not evolve in squares such as EGARCH or TARCH do not
    support the 'analytic' method for horizons > 1.
simulations : int, optional
    Number of simulations to run when computing the forecast using
    either simulation or bootstrap.
rng : callable, optional
    Custom random number generator to use in simulation-based forecasts.
    Must produce random samples using the syntax `rng(size)` where size
    the 2-element tuple (simulations, horizon).
random_state : RandomState, optional
    NumPy RandomState instance to use when method is 'bootstrap'
reindex : bool, optional
    Whether to reindex the forecasts to have the same dimension as the series
    being forecast.

    .. versionchanged:: 6.2

       The default has been changed to False.

x : {dict[label, array_like], array_like}
    Values to use for exogenous regressors if any are included in the
    model. Three formats are accepted:

    * 2-d array-like: This format can be used when there is a single
      exogenous variable. The input must have shape (nforecast, horizon)
      or (nobs, horizon) where nforecast is the number of forecasting
      periods and nobs is the original shape of y. For example, if a
      single series of forecasts are made from the end of the sample
      with a horizon of 10, then the input can be (1, 10). Alternatively,
      if the original data had 1000 observations, then the input can be
      (1000, 10), and only the final row is used to produce forecasts.
    * A dictionary of 2-d array-like: This format is identical to the
      previous except that the dictionary keys must match the names of
      the exog variables.  Requires that the exog variables were passed
      as a pandas DataFrame.
    * A 3-d NumPy array (or equivalent). In this format, each panel
      (0th axis) is a 2-d array that must have shape (nforecast, horizon)
      or (nobs,horizon). The array x[j] corresponds to the j-th column of
      the exogenous variables.

    Due to the complexity required to accommodate all scenarios, please
    see the example notebook that demonstrates the valid formats for
    x.

    .. versionadded:: 4.19

Returns
-------
arch.univariate.base.ARCHModelForecast
    Container for forecasts. Key properties are ``mean``,
    ``variance`` and ``residual_variance``.
```
