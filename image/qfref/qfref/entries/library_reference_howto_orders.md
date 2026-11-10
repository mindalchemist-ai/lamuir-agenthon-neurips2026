Backtrader 1.9.78.123 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Schedule event-driven orders and fills

Backtrader PandasData maps the time index and OHLCV. next() sees current close; ordinary Market orders generally fill next bar's open. Track pending orders; inspect Completed/Canceled/Margin/Rejected notifications. Stock commission is a proportion, not bps; futures margin/multipliers need separate settings. cheat-on-close/open change the clock. Cerebro.run returns strategy instances.

```python
import backtrader as bt
engine=bt.Cerebro(); engine.broker.setcash(1234.); engine.broker.setcommission(commission=.002)
assert engine.broker.getvalue()==1234.
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
