# FX conventions: quote direction, crosses, covered forwards, signed positions

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

## Topic: Quote direction and USD conversion

**Purpose:** Convert any currency to USD with one function so no pair is inverted by accident.

**When to use:** Any FX code: P&L, exposure, cross, forward. Always apply before other FX topics.

**How to implement:** In a quote BASE/TERMS the number is the amount of terms currency paid for one unit of base. Write one `usd_per(ccy, side)` returning the USD value of 1 unit of any currency, and reuse it everywhere. An X/USD quote already is USD per X. A USD/Y quote must be inverted, and inverting swaps bid and ask.
```python
def usd_per(ccy, s="mid"):
    if ccy == "USD": return 1.0
    if f"{ccy}/USD" in q: return q[f"{ccy}/USD"][s]
    inv = {"bid": "ask", "ask": "bid", "mid": "mid"}[s]
    return 1.0 / q[f"USD/{ccy}"][inv]
assert abs(usd_per("JPY") * q["USD/JPY"]["mid"] - 1) < 1e-12   # JPY is worth far less than 1 USD
```

**Limitations and cautions:**

1. Build every cross rate, spot or forward for every tenor, from `usd_per` of its two currencies: cross(BASE/TERMS) = usd_per(BASE) / usd_per(TERMS). This works whatever the direction of the USD legs. Code that assumes one leg layout fails with a missing-pair KeyError on the other.
2. A pair quoted directly in the inputs is used as quoted unless the task asks to derive it from the legs.
3. `usd_per` already inverts a USD-base quote once and swaps its sides. Inverting or swapping again turns the cross upside down.

**Double check:**

1. A pair and its inverse multiply to one: `assert abs(cross(a, b) * cross(b, a) - 1) < 1e-12` for mids.
2. The USD value of a weak currency (JPY) is far below 1.

## Topic: Crosses with bid and ask

**Purpose:** Build cross bid, ask and mid for spot and for each forward tenor.

**When to use:** A cross pair is requested or needed and both legs are quoted against USD.

**How to implement:** Express both legs as USD per unit, then divide. Selling the base and buying the terms happens at the worst side of each leg: the cross bid is the base's USD bid over the terms' USD ask; the ask is the other way round.
```text
bid = usd_per(X, "bid") / usd_per(Y, "ask")
ask = usd_per(X, "ask") / usd_per(Y, "bid")
mid = usd_per(X, "mid") / usd_per(Y, "mid")
```
For two USD-base legs (USD/X, USD/Y) this gives bid = (USD/Y bid)/(USD/X ask). Multiplying legs takes the same side of both; dividing takes opposite sides. Dealer rule by leg layout (every row equals the `usd_per` construction):

| USD legs | cross X/Y | bid | ask |
|---|---|---|---|
| X/USD and USD/Y | multiply | (X/USD bid) * (USD/Y bid) | (X/USD ask) * (USD/Y ask) |
| X/USD and Y/USD | divide | (X/USD bid) / (Y/USD ask) | (X/USD ask) / (Y/USD bid) |
| USD/X and USD/Y | divide, terms leg on top | (USD/Y bid) / (USD/X ask) | (USD/Y ask) / (USD/X bid) |
| USD/X and Y/USD | invert the product | 1 / ((USD/X ask) * (Y/USD ask)) | 1 / ((USD/X bid) * (Y/USD bid)) |

One function for spot and for each tenor's outright forwards keeps the side mapping in one place:
```python
def cross_quote(q, base, terms):                  # q: USD legs for spot, or one tenor's outright forward bid/ask/mid
    def usd_per(ccy, s):
        if ccy == "USD": return 1.0
        if f"{ccy}/USD" in q: return q[f"{ccy}/USD"][s]
        return 1.0 / q[f"USD/{ccy}"][{"bid": "ask", "ask": "bid", "mid": "mid"}[s]]
    out = {"bid": usd_per(base, "bid") / usd_per(terms, "ask"),
           "ask": usd_per(base, "ask") / usd_per(terms, "bid"),
           "mid": usd_per(base, "mid") / usd_per(terms, "mid")}
    assert out["bid"] < out["ask"] and out["bid"] <= out["mid"] <= out["ask"], (base, terms, out)
    return out
```

**Limitations and cautions:**

1. Writing the side mapping by hand is where crosses go wrong. A division that takes the same side of both legs puts bid above ask in about half of all quote sets.
2. Round only when writing output. Rounding legs first can make bid equal ask.
3. A forward cross takes each leg's outright forward bid and ask for that tenor and passes them through the same function. Crossing mids and adding a spread afterwards is a different quote.

**Double check:**

1. For every computed pair, spot and each tenor: `bid < ask` and `bid <= mid <= ask`. Bid above ask means a side was flipped twice or taken from the same side of both legs.

## Topic: Covered forward and implied rates

**Purpose:** Compute the covered forward, forward points and implied deposit rates.

**When to use:** Spot and two interest rates (or discount factors) are given and a forward, forward points or an implied rate is asked.

**How to implement:** The terms currency plays the domestic role. Each currency uses its own day count. The accrual factor follows how the rates are quoted:

- money-market (simple) deposit rates: $(1+rt)$, the usual reading for deposit or LIBOR-style quotes up to a year;
- continuously compounded: $e^{rt}$;
- annually compounded: $(1+r)^t$;
- discount factors from curves: $F = S\,P_{base}(T)/P_{terms}(T)$.

The task's description of the rates ("deposit rate", "continuously compounded", "zero rate", a curve of discount factors) decides. The skeleton below is the simple-rate case; the implied-rate inversions change with the accrual form.
```text
def fwd(S, r_base, t_base, r_terms, t_terms):   # simple-rate form; exp(r * t) or (1 + r) ** t for the other quotes
    return S * (1 + r_terms * t_terms) / (1 + r_base * t_base)
F = fwd(S, r_base, t_base, r_terms, t_terms)
points = (F - S) * pip_multiplier
r_base_implied = (S * (1 + r_terms * t_terms) / F - 1) / t_base      # unknown is the base currency
r_terms_implied = ((F / S) * (1 + r_base * t_base) - 1) / t_terms    # unknown is the terms currency
```

**Limitations and cautions:**

1. Which implied-rate formula applies depends on where the unknown currency sits in the quote, not on which currency is "foreign" to the investor.
2. With one deposit rate per currency, apply the same accrual factor to spot bid and spot ask.
3. When a task maps bid/offer sides explicitly, write the mapping as a small table in code.

**Double check:**

1. Round trip: `abs(fwd(S, r_base_implied, t_base, r_terms, t_terms) - F) < 1e-10` and the same for `r_terms_implied`.
2. Implied bid < implied offer when sides are mapped.

## Topic: CIP deviation

**Purpose:** Measure a forward's deviation from covered interest parity in the right unit.

**When to use:** A CIP deviation or cross-currency basis is requested, on a pair that has both deposit rates.

**How to implement:** Compare a forward with the parity forward from the two deposit rates. Which forward depends on the inputs:

- market forwards or forward points are supplied: the deviation is usually not 0 (the cross-currency basis). Its unit follows the field. In bp of spot: `(F_market - F_cip) / S * 1e4`. In pips or forward points: `(F_market - F_cip) * point_multiplier`, with no division by S. For a deviation field, a key ending in `_pips` or `_points` is the second kind. A forward-points field itself is `(F - S) * point_multiplier`, not a deviation.
- the forward is built from parity in the code: the deviation is about 0, and the line is an identity check of the build.

The unit and which pairs to report follow the task's key names and unit notes.

**Limitations and cautions:**

1. The gap between an exact parity formula and its linear approximation is not a CIP deviation.
2. The forward premium $(F-S)/S\times 10^4$ is not a CIP deviation. It is the interest-rate differential parity predicts (about 35 bp over three months for a 140 bp rate gap), while the parity deviation of the same forward is 0.
3. A deviation subtracts the parity forward, never spot.

**Double check:**

1. A forward built from parity gives a deviation of about 0.
2. The unit matches the field name (bp of spot versus pips or points).

## Topic: Signed forward positions

**Purpose:** Compute forward P&L, spot and carry parts, and currency exposure with consistent signs.

**When to use:** Trades buy or sell a base currency forward and P&L or exposures are requested.

**How to implement:** Let $s=+1$ when buying the base currency forward, $-1$ when selling. Apply $s$ to every component, then convert terms-currency amounts with `usd_per(terms)`. The terms leg of a position is $-N\times$ leg_rate in the terms currency; for exposures of an existing contract, leg_rate is its contract rate $K$.
```text
def forward_trade(direction, N, K, F_now, S_now, S_then, base, terms, leg_rate):
    s = {"buy_base": 1.0, "sell_base": -1.0}[direction]
    pnl, spot = s * N * (F_now - K), s * N * (S_now - S_then)
    carry = s * N * (F_now - S_now)
    usd = [x * usd_per(terms) for x in (pnl, spot, carry, pnl - spot - carry)]
    legs = {base: s * N * usd_per(base), terms: -s * N * leg_rate * usd_per(terms)}
    return usd, legs
```
The terms leg can be read two ways: the contract amount (rate = K, the cash actually exchanged) or a mark-to-market delta (rate = current forward F). Both are standard; the task's wording decides.

**Limitations and cautions:**

1. In a per-trade loop, read every trade field (notional, side, contract rate K, tenor) from the current row. A name left over from an earlier loop silently prices every trade at the last trade's value.
2. The residual sums to the total by construction, so checking the sum is useless.

**Double check:**

1. Buy and sell of the same trade are exact negatives: `all(abs(b + c) < 1e-6 for b, c in zip(buy, sell))`.
2. `(buy[1] > 0) == (S_now > S_then)`.
3. Check the size of the residual, not the sum.

## Topic: Swap points and roll quotes

**Purpose:** Express a swap (roll) quote in the right unit.

**When to use:** Near and far forward points or outrights are given and a swap or roll is requested.

**How to implement:** A swap (roll) quote is far points minus near points. In dealer quoting it is stated in pips, the unit of the points columns. As a price difference it is far outright minus near outright $=(\text{far points}-\text{near points})/\text{multiplier}$.

**Limitations and cautions:**

1. The two forms differ only by the multiplier. Pick the unit the output field's name and the task's unit notes describe.

**Double check:**

1. The output unit matches the field name (pips versus price difference).

## Topic: Daily series from monthly data

**Purpose:** Align monthly values to a daily trading-date index without look-ahead.

**When to use:** A daily output is built from monthly signals or data.

**How to implement:** Index the daily output on the trading dates present in the daily price file, then carry the latest monthly value forward (`merge_asof` with `direction="backward"`). A "month-end" signal is the last trading date of that month in the data.

**Limitations and cautions:**

1. A calendar-day range adds weekends and holidays.

**Double check:**

1. Every output date exists in the daily price file.

## Topic: Pandas arguments, rounding and day count

**Purpose:** Map task wording to correct pandas, rounding and day-count choices.

**When to use:** The task says "daily", "month end", "lag", "round to n decimals", "ACT/360" or similar.

**How to implement:**

- `pd.date_range` freq: "D" calendar days, "B" weekdays. Neither equals the data's trading dates. Wording "daily" in a backtest usually means the price file's rows.
- `pd.merge_asof` direction: "backward" uses the last known value (information available on that date). "forward" or "nearest" can look ahead.
- `DataFrame.shift(k)` with positive k moves values later. "Active the next business day after the signal" is a shift by the lag on the trading-date index, not a calendar offset.
- Rounding "to n decimals" in the output is applied once at serialization.
- Day count "ACT/360" and "ACT/365": $t$ = actual days / 360 or / 365, counted from the spot date to delivery unless the task names other dates.

**Limitations and cautions:**

1. In pandas 3 the alias "M" raises. Month end is "ME", month start "MS".
2. Python `round()` rounds the stored binary value half-to-even (`round(2.675, 2)` gives 2.67).

**Double check:**

1. No look-ahead: each output date uses only information available on that date.
