# Official API description: arch.univariate.base.ARCHModelForecast (arch 8.0.0)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
arch.univariate.base.ARCHModelForecast(index: list[typing.Optional[collections.abc.Hashable]] | pandas.Index, start_index: int, mean: numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]], variance: numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]], residual_variance: numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]], simulated_paths: numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]] | None = None, simulated_variances: numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]] | None = None, simulated_residual_variances: numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]] | None = None, simulated_residuals: numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]] | None = None, align: Literal['origin', 'target'] = 'origin', *, reindex: bool = False) -> None

Container for forecasts from an ARCH Model

Parameters
----------
index : {list, ndarray}
mean : ndarray
variance : ndarray
residual_variance : ndarray
simulated_paths : ndarray, optional
simulated_variances : ndarray, optional
simulated_residual_variances : ndarray, optional
simulated_residuals : ndarray, optional
align : {'origin', 'target'}
```
