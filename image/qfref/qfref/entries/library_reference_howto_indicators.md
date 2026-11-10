NumPy 2.5.3; TA-Lib 0.7.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Compute rolling technical indicators

TA-Lib requires ordered one-dimensional float64 data; outputs retain input length and warm-up NaNs. Do not fill warm-up with zero. EMA initialization can differ from pandas ewm. MACD returns (macd,signal,hist); BBANDS returns (upper,middle,lower); ATR has price units, RSI usually 0..100. Indicators impose no execution lag. Missing inputs can propagate further than pandas rolling.

```python
import numpy as np, talib
x=np.arange(15,dtype=float)+3
u,m,l=talib.BBANDS(x,timeperiod=4)
assert np.isnan(m[:3]).all() and np.all(u[3:]>=m[3:])
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: talib.sma -> talib.SMA.
