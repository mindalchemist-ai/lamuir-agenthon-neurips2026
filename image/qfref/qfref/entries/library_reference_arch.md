NumPy 2.5.3; pandas 3.0.5; arch 8.0.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: arch: conditional volatility and units

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
import pandas as pd
from arch import arch_model
rng=np.random.default_rng(27); simple=pd.Series(rng.normal(0,.01,size=350)); scaled=100*simple
```

- `arch_model(y,mean='Constant',vol='GARCH',p=1,o=0,q=1,power=2.,dist='normal',rescale=None)` returns a model; `.fit(disp='off',update_freq=0)` returns ARCHModelResult. Multiplying returns by 100 is a numerical scaling choice, not a required economic definition. Explicit rescale=False prevents opaque automatic unit changes.
```python
model=arch_model(scaled,mean='Constant',vol='GARCH',p=1,o=0,q=1,dist='normal',rescale=False); fit=model.fit(disp='off',update_freq=0); assert fit.convergence_flag==0; assert isinstance(fit.params,pd.Series)
```
Access params by name (mu, omega, alpha[1], beta[1], depending on the model), not assumed positions. If fitting percentage returns, divide means and conditional_volatility by 100 and variances and omega by 10000; alpha/beta stay unchanged. Student-t nu is degrees of freedom, not volatility.
```python
vol=fit.conditional_volatility/100; assert vol.index.equals(simple.index) and (vol>0).all(); assert 'omega' in fit.params and 'alpha[1]' in fit.params
```
- `fit.forecast(horizon=1,method='analytic',align='origin',reindex=False)` returns ARCHModelForecast. variance and residual_variance are DataFrames; origin labels the forecast origin, whereas align='target' labels the target time. variance includes variance induced by mean dynamics; residual_variance is innovation variance.
```python
forecast=fit.forecast(horizon=2,method='analytic',align='origin',reindex=False); future=forecast.residual_variance.iloc[-1].to_numpy()/10000; assert future.shape==(2,) and (future>0).all()
```
Not every model supports analytical multistep forecasts. Use simulation/bootstrap for models such as EGARCH/TARCH when supported, with an explicit random source. Check convergence_flag, optimization_result.message and finite outputs rather than assuming that a returned object means success.

## Version check: forms that fail in this version

### Removed or renamed forms
- fillna(method=...) -> ffill()/bfill().
- to_numeric(errors='ignore') -> errors='raise' or 'coerce'; handle invalid values explicitly.
- np.math -> Python math.
- groupby(axis=1) -> df.T.groupby(...).agg(...).T; check dtypes.
- resample('M') -> resample('ME'); to_period('M') still uses M.
- resample('Q') -> resample('QE').
- resample('Y') -> resample('YE').
- DataFrame.applymap -> DataFrame.map.
- np.trapz -> np.trapezoid.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- pd.random -> the specified NumPy RNG interface.
- s.get_loc(label) -> s.index.get_loc(label).
- Series.to_series() -> omit it, or copy(); Index.to_series is valid.
- expanding().shift(...) -> aggregate before shift; ordering follows the definition.
- string Series.dt -> to_datetime(series).dt.
- ndarray.values -> the array itself.
- DatetimeIndex.dt.year -> index.year.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).
- PeriodIndex.dt.year -> index.year.
- ARCHModelResult.predict -> forecast(...).

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
