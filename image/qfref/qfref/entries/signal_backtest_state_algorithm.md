# Daily signal backtest: position state, next-day execution and one row per trading day

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

## Algorithm

```text
Input:  daily bars in date order (signal price, execution price), indicator series, entry / exit rules, costs
Output: trades table, daily portfolio table with one row for EVERY trading day, summary

1   state <- {cash: initial, shares: 0, in_position: False, pending: None, peak: None}
2   for each trading day i in order (warm-up days included; an undefined indicator gives no signal):
3       if pending is set: execute it at day i's execution price, then
            BUY:  shares += n; cash -= cost; in_position <- True
            SELL: cash += revenue; shares <- 0; in_position <- False; peak <- None
            pending <- None
4       value_i <- cash + shares * mark price of day i; append a daily row for day i
5       if in_position: update peak / trailing levels with day i's signal price
6       signal on day i's close (only when the indicator exists):
            not in_position and entry rule holds  -> pending <- BUY (size from the rules), peak <- signal price
            in_position and an exit rule holds    -> pending <- SELL
7   on the last day, a position still held is closed as the task says (forced close)
```

The state flag changes only when a fill executes (step 3); a signal only sets `pending`. Forgetting to set `in_position` after a BUY fill keeps the strategy from ever exiting.

## Checks

1. The daily table has exactly as many rows as there are trading days in the data window, warm-up days included, and its first cumulative return is 1.0.
2. Trades alternate BUY, SELL, BUY, ...; every SELL follows a BUY; the number of trades is even unless a forced close is written separately.
3. Final capital equals cash after the last fill; recompute it from the trades table and compare.
