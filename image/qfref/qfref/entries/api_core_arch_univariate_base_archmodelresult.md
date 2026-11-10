# Official API description: arch.univariate.base.ARCHModelResult (arch 8.0.0)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
arch.univariate.base.ARCHModelResult(params: numpy.ndarray[tuple[int], numpy.dtype[numpy.float64]], param_cov: numpy.ndarray[tuple[int, ...], numpy.dtype[numpy.float64]] | None, r2: float, resid: numpy.ndarray[tuple[int], numpy.dtype[numpy.float64]], volatility: numpy.ndarray[tuple[int], numpy.dtype[numpy.float64]], cov_type: str, dep_var: pandas.Series, names: list[str], loglikelihood: float, is_pandas: bool, optim_output: scipy.optimize._optimize.OptimizeResult, fit_start: int, fit_stop: int, model: arch.univariate.base.ARCHModel) -> None

Results from estimation of an ARCHModel model

Parameters
----------
params : ndarray
    Estimated parameters
param_cov : {ndarray, None}
    Estimated variance-covariance matrix of params.  If none, calls method
    to compute variance from model when parameter covariance is first used
    from result
r2 : float
    Model R-squared
resid : ndarray
    Residuals from model.  Residuals have same shape as original data and
    contain nan-values in locations not used in estimation
volatility : ndarray
    Conditional volatility from model
cov_type : str
    String describing the covariance estimator used
dep_var : Series
    Dependent variable
names : list (str)
    Model parameter names
loglikelihood : float
    Loglikelihood at estimated parameters
is_pandas : bool
    Whether the original input was pandas
optim_output : OptimizeResult
    Result of log-likelihood optimization
fit_start : int
    Integer index of the first observation used to fit the model
fit_stop : int
    Integer index of the last observation used to fit the model using
    slice notation `fit_start:fit_stop`
model : ARCHModel
    The model object used to estimate the parameters
```
