# Annualization and return conventions

Use this when a task turns prices into returns, aggregates returns over time, or reports annualized returns or volatilities. A number or formula the task states always wins; the rows below say what to use when it does not.

## Decisions

| Decision | Options | How the task text selects | When the text is silent |
|---|---|---|---|
| Periods per year A | a stated annualization factor; 252; 365 or 365.25; 52; 12 | A given factor or "periods per year" is used as is. "Trading days" or daily exchange data usually means 252; calendar-day accrual, assets that trade every day, or "calendar days" mean 365 (or 365.25 if written); weekly 52; monthly 12. | Count the observations per year in the data's date column and use the conventional value that matches its frequency, then state it. |
| Volatility scaling | sqrt(A) * sd of period returns; a method the task gives for dependent returns | sqrt(A) assumes uncorrelated period returns; the same rule gives sqrt(h) for an h-period horizon. | sqrt(A), stated as an i.i.d. approximation. |
| Annual return | arithmetic: A * mean(r); geometric: (1 + R_total) ** (A / n) - 1 | "Arithmetic", a formula of mean times A, or a Sharpe-ratio numerator usually means arithmetic; "compound", "CAGR", "geometric" or a formula with a power means geometric. The years elapsed can be n / A or the calendar span in days / 365 (or 365.25). | Report what the field name says (a "CAGR" field is geometric); otherwise arithmetic for ratios built from means, geometric for growth of wealth, and say which. |
| Return definition | log: ln(P[t] / P[t-1]); simple: P[t] / P[t-1] - 1 | "log", "ln", "continuously compounded" mean log; "percentage change", "pct_change", "simple", "arithmetic return" mean simple. | Simple returns for portfolios and wealth, log returns for models written in logs; state the choice. |
| Aggregating over time and across assets | log returns add over time; simple returns compound over time; portfolio returns weight simple returns | A portfolio's return is the weighted sum of simple returns; weighting log returns is only an approximation. | — |

Use one definition for every quantity derived from the same series: a Sharpe ratio, a volatility and a drawdown reported together come from the same returns and the same A.

## Check

```python
import numpy as np, pandas as pd

rng = np.random.default_rng(0)
dates = pd.bdate_range("2021-01-01", periods=504)
P = pd.Series(100 * np.exp(np.cumsum(0.0003 + 0.01 * rng.standard_normal(504))), index=dates)
simple, logr = P.pct_change().dropna(), np.log(P).diff().dropna()
assert np.allclose(np.log1p(simple), logr)                          # the two definitions are linked exactly
assert np.isclose((1 + simple).prod() - 1, np.exp(logr.sum()) - 1)  # compound simple returns, add log returns

per_year = simple.groupby(simple.index.year).size().mean()          # about 252 rows per year for weekday data
A = 252 if 240 <= per_year <= 262 else (12 if per_year <= 13 else 52 if per_year <= 53 else 365)
n = len(simple)
arith = A * simple.mean()
geom = (1 + simple).prod() ** (A / n) - 1
vol = np.sqrt(A) * simple.std(ddof=1)
assert A == 252 and geom < arith                                    # geometric is below arithmetic when vol > 0
assert np.isclose(geom, np.exp(A * logr.mean()) - 1)
```
