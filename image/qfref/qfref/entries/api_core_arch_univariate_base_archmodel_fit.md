# Official API description: arch.univariate.base.ARCHModel.fit (arch 8.0.0)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
arch.univariate.base.ARCHModel.fit(self, update_freq: int = 1, disp: Union[Literal['off', 'final'], bool] = 'final', starting_values: Union[numpy.ndarray[tuple[int], numpy.dtype[numpy.float64]], pandas.Series, NoneType] = None, cov_type: Literal['robust', 'classic'] = 'robust', show_warning: bool = True, first_obs: Union[int, str, datetime.datetime, numpy.datetime64, pandas.Timestamp, NoneType] = None, last_obs: Union[int, str, datetime.datetime, numpy.datetime64, pandas.Timestamp, NoneType] = None, tol: float | None = None, options: dict[str, typing.Any] | None = None, backcast: float | numpy.ndarray[tuple[int], numpy.dtype[numpy.float64]] | None = None) -> 'ARCHModelResult'

Estimate model parameters

Parameters
----------
update_freq : int, optional
    Frequency of iteration updates.  Output is generated every
    `update_freq` iterations. Set to 0 to disable iterative output.
disp : {bool, "off", "final"}
    Either 'final' to print optimization result or 'off' to display
    nothing. If using a boolean, False is "off" and True is "final"
starting_values : ndarray, optional
    Array of starting values to use.  If not provided, starting values
    are constructed by the model components.
cov_type : str, optional
    Estimation method of parameter covariance.  Supported options are
    'robust', which does not assume the Information Matrix Equality
    holds and 'classic' which does.  In the ARCH literature, 'robust'
    corresponds to Bollerslev-Wooldridge covariance estimator.
show_warning : bool, optional
    Flag indicating whether convergence warnings should be shown.
first_obs : {int, str, datetime, Timestamp}
    First observation to use when estimating model
last_obs : {int, str, datetime, Timestamp}
    Last observation to use when estimating model
tol : float, optional
    Tolerance for termination.
options : dict, optional
    Options to pass to `scipy.optimize.minimize`.  Valid entries
    include 'ftol', 'eps', 'disp', and 'maxiter'.
backcast : {float, ndarray}, optional
    Value to use as backcast. Should be measure :math:`\sigma^2_0`
    since model-specific non-linear transformations are applied to
    value before computing the variance recursions.

Returns
-------
results : ARCHModelResult
    Object containing model results
```
