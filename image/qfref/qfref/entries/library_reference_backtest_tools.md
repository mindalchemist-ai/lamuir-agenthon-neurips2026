Python 3.13.15; NumPy 2.5.3; pandas 3.0.5 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: backtest_tools: information clock and return types

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
import pandas as pd
from backtest_tools import month_start_rows, rebalanced_returns, monthly_long_short, factor_regression, arithmetic_metrics
idx=pd.date_range('2021-01-27',periods=9)
returns=pd.DataFrame({'left':np.full(9,.01),'right':np.full(9,-.01)},index=idx)
signal=pd.DataFrame({'left':np.arange(9,dtype=float)+1,'right':-np.arange(9,dtype=float)-1},index=idx)
```

This describes the current session implementation, not universal financial conventions. Check the task requirements before using it.

- `month_start_rows(index,start=0)` returns list[int]: start itself plus the first available row of each subsequent calendar month, not an exchange calendar. start must be a valid position.
```python
rows=month_start_rows(idx,start=2); assert rows==[2,5]
```
- `rebalanced_returns(returns,rebalance_weights,initial=None,cost_bps=0.)` returns a Series on the input index. Dictionary key t sets weights at row t's close, earning from row t+1. Series/dict weights align by column label; arrays align by position. Every rebalance replaces the whole book, setting omitted names to zero. initial=None starts equally weighted; pass zeros to start flat.
```python
r=rebalanced_returns(returns,{1:pd.Series({'left':1.})},initial=pd.Series(0.,index=returns.columns),cost_bps=10.); assert r.iloc[0]==0 and r.iloc[1]==0 and np.isclose(r.iloc[2],.009)
```
The implementation maintains the supplied weights each row rather than simulating fixed shares and weight drift. NaN returns become zero, which does not establish a valid missing-data policy. Cost is cost_bps/10000*sum(abs(new-old)), deducted when the new weights first earn returns. Weights set at the final close have no subsequent earning row or charged cost.

- `monthly_long_short(returns,signal,first_trade_row,n_long,n_short,weight_long,weight_short,cost_bps=0.,max_position=None)` returns a dict: returns (a sliced Series), rebalance_rows (positions), n_rebalances (int), and weights (effective-date to Series mapping). signal[t] contains information through row t; **do not shift it again**. Rebalance row i ranks signal.iloc[i-1], stores book key i-1, and earns from i. First ensure identical signal/return row indices, column sets and order; the current implementation does not check these for you.
```python
assert signal.index.equals(returns.index) and signal.columns.equals(returns.columns); result=monthly_long_short(returns,signal,2,1,1,.5,.5,cost_bps=0.); assert result['rebalance_rows']==[2,5]; assert result['returns'].index.equals(idx[2:]); assert np.allclose(result['returns'],.01); assert result['weights'][idx[2]]['left']==.5
```
first_trade_row must be >=1; otherwise iloc[-1] reads the final row. There must be enough eligible names and disjoint legs. With overlapping legs, short assignments currently overwrite long assignments. nlargest/nsmallest resolve ties by input column order; implement any different required tie rule. max_position clips individual absolute weights without restoring gross exposure afterward.

- `factor_regression(r,factors,periods=252)` returns a dict: alpha (intercept times periods), betas (list), tracking_error (residual std(ddof=1)*sqrt(periods)), information_ratio, and residuals (ndarray). Inputs are converted to arrays without date alignment; align and jointly drop missing rows first. This is not a HAC inference interface.
```python
rng=np.random.default_rng(13); F=rng.normal(size=(30,2)); y=.002+F@np.array([.3,-.2])+rng.normal(size=30)*.01; regression=factor_regression(y,F,periods=12); assert len(regression['betas'])==2 and regression['residuals'].shape==(30,)
```
- `arithmetic_metrics(x,annualization=252.,ddof=1)` returns a dict with annualized arithmetic mean, annualized volatility, their ratio, maximum drawdown as a positive magnitude, and positive-return share; it is not CAGR. Drawdown uses cummax only within (1+x).cumprod(), without prepending initial wealth 1, so an initial loss can be missed. Compute separately when the initial wealth must participate.
```python
metrics=arithmetic_metrics(pd.Series([.01,-.02,.03]),annualization=12.,ddof=1); assert np.isclose(metrics['annualized_return'],.08) and np.isclose(metrics['max_drawdown'],.02)
```

## Version check: forms that fail in this version

### Removed or renamed forms
None among the verified calls shown.

### Unavailable or wrong-object forms
- ndarray.values -> the array itself.
- s.get_loc(label) -> s.index.get_loc(label).
- string Series.dt -> to_datetime(series).dt.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
