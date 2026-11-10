NumPy 2.5.3; pandas 3.0.5; Backtrader 1.9.78.123 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: Backtrader: feeds, orders and execution timing

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
import pandas as pd
import backtrader as bt
prices=np.linspace(30.,34.,8)
feed=pd.DataFrame({'open':prices,'high':prices+1,'low':prices-1,'close':prices,'volume':np.ones(8)*100},index=pd.date_range('2021-05-01',periods=8))
```

- `bt.feeds.PandasData(dataname=df)` returns a feed; explicitly map the DatetimeIndex and OHLCV fields. `Cerebro().adddata(data)` registers it. `addstrategy(StrategyClass)` registers a strategy; `run()` returns a list of strategy instances.
- `Strategy.buy(size=...)` returns Order. Ordinary Market orders generally execute at the next bar's open; close[0] in next is the current bar's close. Submission and execution times differ. Avoid duplicate orders while an order is pending. The synthetic example verifies only the default engine clock.
```python
class Probe(bt.Strategy):
    def __init__(self):
        self.sent=False
        self.completed=[]
    def next(self):
        if not self.sent:
            self.buy(size=1)
            self.sent=True
    def notify_order(self,order):
        if order.status==order.Completed:
            self.completed.append((len(self),order.executed.price))
engine=bt.Cerebro(); engine.adddata(bt.feeds.PandasData(dataname=feed)); engine.addstrategy(Probe); engine.broker.setcash(1000.); engine.broker.setcommission(commission=.001); runs=engine.run(); assert len(runs)==1 and runs[0].completed[0][0]==2; assert np.isclose(runs[0].completed[0][1],feed['open'].iloc[1])
```
- `broker.setcash(cash)` returns None. `setcommission(commission=...,...)` configures commission; the default stock percentage rate is not bps. Futures margin, mult and leverage need separate settings. `broker.getvalue()` returns a float including marked holdings.
```python
assert np.isfinite(engine.broker.getvalue()) and engine.broker.getcash()<1000.
```
cheat-on-close/cheat-on-open change the clock and are not enabled by default. In order notifications, check Completed/Canceled/Margin/Rejected. Do not transfer timestamps, calendars, costs or position units unchanged to a different engine.

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

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
