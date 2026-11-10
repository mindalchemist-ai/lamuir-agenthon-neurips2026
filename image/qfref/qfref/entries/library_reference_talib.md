NumPy 2.5.3; TA-Lib 0.7.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: TA-Lib: inputs, warm-up and outputs

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
import talib
close=np.linspace(40.,70.,80)+np.sin(np.arange(80)); high=close+1; low=close-1
```

- `SMA(real,timeperiod=30)` and `EMA(real,timeperiod=30)` return same-length ndarrays from one-dimensional float64 inputs ordered in time. Warm-up NaNs are not zero-valued signals. EMA initialization need not match pandas ewm defaults.
```python
sma=talib.SMA(close,timeperiod=5); ema=talib.EMA(close,timeperiod=5); assert np.isnan(sma[:4]).all() and np.isclose(sma[4],close[:5].mean()); assert ema.shape==close.shape
```
- `RSI(real,timeperiod=14)` returns an ndarray, usually in 0..100. `MACD(real,fastperiod=12,slowperiod=26,signalperiod=9)` returns three arrays (macd,signal,hist); parameters determine warm-up length.
```python
rsi=talib.RSI(close,timeperiod=9); macd,signal,hist=talib.MACD(close,fastperiod=5,slowperiod=11,signalperiod=4); assert np.all((rsi[np.isfinite(rsi)]>=0)&(rsi[np.isfinite(rsi)]<=100)); assert np.allclose((macd-signal)[np.isfinite(hist)],hist[np.isfinite(hist)])
```
- `BBANDS(real,timeperiod=5,nbdevup=2,nbdevdn=2,matype=0)` returns (upper,middle,lower), not the middle band first. `ATR(high,low,close,timeperiod=14)` returns an ndarray in absolute price units; divide by price for a relative measure.
```python
upper,middle,lower=talib.BBANDS(close,timeperiod=7,nbdevup=2.,nbdevdn=2.); atr=talib.ATR(high,low,close,timeperiod=7); valid=np.isfinite(upper); assert np.all(upper[valid]>=middle[valid]) and np.all(middle[valid]>=lower[valid]); assert atr.shape==close.shape
```
Missing values can leave subsequent indicator values NaN; do not assume pandas rolling semantics. Check indicator definitions, price adjustments and trade timing first. Indicators do not automatically prevent future information or enforce an execution lag.

## Version check: forms that fail in this version

### Removed or renamed forms
- np.math -> Python math.
- np.trapz -> np.trapezoid.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- ndarray.values -> the array itself.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).
- talib.sma -> talib.SMA.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
