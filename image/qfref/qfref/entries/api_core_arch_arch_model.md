# Official API description: arch.arch_model (arch 8.0.0)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
arch.arch_model(y: Union[numpy.ndarray, pandas.DataFrame, pandas.Series, NoneType], x: Union[numpy.ndarray, pandas.DataFrame, pandas.Series, numpy.ndarray[tuple[int, int], numpy.dtype[numpy.float64]], NoneType] = None, mean: Literal['Constant', 'Zero', 'LS', 'AR', 'ARX', 'HAR', 'HARX', 'constant', 'zero'] = 'Constant', lags: int | list[int] | numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.int32]] | numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.int64]] | None = 0, vol: Literal['GARCH', 'ARCH', 'EGARCH', 'FIGARCH', 'APARCH', 'HARCH'] = 'GARCH', p: int | list[int] = 1, o: int = 0, q: int = 1, power: float = 2.0, dist: Literal['normal', 'gaussian', 't', 'studentst', 'skewstudent', 'skewt', 'ged', 'generalized error'] = 'normal', hold_back: int | None = None, rescale: bool | None = None) -> arch.univariate.mean.HARX

Initialization of common ARCH model specifications

Parameters
----------
y : ndarray, Series, None
    The dependent variable
x : ndarray, DataFrame, optional
    Exogenous regressors.  Ignored if model does not permit exogenous
    regressors.
mean : str, optional
    Name of the mean model.  Currently supported options are: 'Constant',
    'Zero', 'LS', 'AR', 'ARX', 'HAR' and  'HARX'
lags : int or list[int], optional
    Either a scalar integer value indicating lag length or a list of
    integers specifying lag locations.
vol : str, optional
    Name of the volatility model.  Currently supported options are:
    'GARCH' (default), 'ARCH', 'EGARCH', 'FIGARCH', 'APARCH' and 'HARCH'
p : int, optional
    Lag order of the symmetric innovation
o : int, optional
    Lag order of the asymmetric innovation
q : int, optional
    Lag order of lagged volatility or equivalent
power : float, optional
    Power to use with GARCH and related models
dist : int, optional
    Name of the error distribution.  Currently supported options are:

        * Normal: 'normal', 'gaussian' (default)
        * Students's t: 't', 'studentst'
        * Skewed Student's t: 'skewstudent', 'skewt'
        * Generalized Error Distribution: 'ged', 'generalized error"

hold_back : int
    Number of observations at the start of the sample to exclude when
    estimating model parameters.  Used when comparing models with different
    lag lengths to estimate on the common sample.
rescale : bool
    Flag indicating whether to automatically rescale data if the scale
    of the data is likely to produce convergence issues when estimating
    model parameters. If False, the model is estimated on the data without
    transformation.  If True, then y is rescaled and the new scale is
    reported in the estimation results.

Returns
-------
model : ARCHModel
    Configured ARCH model
```
