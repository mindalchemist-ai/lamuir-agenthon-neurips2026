Python 3.13.15; pandas 3.0.5 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Track portfolio execution, costs and cash timing

For monthly_long_short, earning row i reads signal[i-1]; do not shift unlagged signal again. rebalanced_returns keys t set weights at close t, earning at t+1. Align rows/columns and start>=1; legs must be disjoint. Replacement zeroes omitted names; cost uses absolute weight changes times bps/10000. This helper maintains weights and maps NaN returns to zero. Keep interest/dividend/trade/liquidation events ordered; reconcile cash+marked positions. arithmetic_metrics omits initial wealth from drawdown.

```python
import pandas as pd
from backtest_tools import rebalanced_returns
r=pd.DataFrame({'a':[.01,.02,.03]})
x=rebalanced_returns(r,{0:pd.Series({'a':1.})},initial=pd.Series({'a':0.}))
assert x.tolist()==[0.,.02,.03]
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
