# Proportional fund flows on selected holdings

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

## Topic: Ranks and ties

**Purpose:** Produce a rank column that matches the metric it ranks.

**When to use:** A table has a rank column for a named metric, with or without ties.

**How to implement:** Rank the column's own metric at full precision and return complete positions $1,\dots,n$: `rank(method='first', ascending=False).astype(int)` within each group. `first` gives tied rows the order they already have, so first put the rows in a stated order: the ranked table's own stated sort, or, when it states none, the stated sort of the detail table that holds the same rows (for example a table keyed by case and name). If the task requests tied ranks, use the stated tie method instead.

**Limitations and cautions:**

1. Do not rank on a frame whose row order came from a merge or cross join with another table.
2. Do not add an alphabetical or other tie-break key of your own, and do not use the row position of a table sorted by another key.
3. An extreme picked across scenario rows: values equal within `np.isclose` are ties; take the first in declared scenario order. Floating-point noise must not choose.

**Double check:**

1. After writing, recompute each rank from the written detail rows in their stated order and compare. Read the CSV back with `float_precision='round_trip'`; default parsing can move ties.

## Topic: Sold amounts and ratios

**Purpose:** Turn each fund's proportional outflow fraction $\rho$ into sold quantities and values per name.

**When to use:** Each fund receives a proportional outflow fraction $\rho$ per scenario after the selections and the union table exist.

**How to implement:** Per fund: $\rho\times$ quantity and $\rho\times$ value on that fund's selected exposure; then add across funds. Value ratio is sold value divided by held value; the quantity ratio is sold share quantity divided by held share quantity.

**Limitations and cautions:**

1. Do not spread a fund's flow over names outside its selection.
2. The value ratio and the quantity ratio differ for names held by several funds when the shocks differ; do not set them equal.

**Double check:**

1. With different shocks per fund, the two ratios are not identical for a name held by several funds.

## Topic: Concentration and buckets per scenario

**Purpose:** Report concentration and bucket splits of the sold amounts per scenario.

**When to use:** A concentration or a split of the flow is reported per scenario.

**How to implement:** $\text{share}_i=\text{flow}_i/\sum\text{flow}$ in that scenario; $\mathrm{HHI}=\sum_i \text{share}_i^2$. Partition buckets (shared names versus names of only one fund) by the selection flags; the fund-specific part next to the shared part is the covered amount minus the shared amount.

**Limitations and cautions:**

1. Do not reuse weights that do not change with the scenario; an HHI identical across different shocks is wrong.
2. Do not use full-list membership for buckets, and do not recompute a fund-specific part from another base.

**Double check:**

1. The bucket parts add back to the scenario total, and HHI differs across scenarios with different shocks.

## Topic: Redemption amounts and transfer

**Purpose:** Value a fund redemption and compare selected flow with it.

**When to use:** The task gives units redeemed, NAV, market price or trading volume.

**How to implement:** Redeemed units are $\rho\times$ units outstanding. NAV amount is units times NAV; market amount is units times market price. Selected flow relative to the fund's redemption is selected sold value divided by the redeemed NAV amount. Redeemed units against trading is redeemed units divided by traded units. Transfer in basis points is $(\text{market amount}/\text{NAV amount}-1)\times 10^4$ from unrounded prices.

**Limitations and cautions:**

1. Do not mix NAV and market amounts, and do not divide by the market amount or by traded volume.
2. Do not divide dollars by shares.
3. Do not multiply a rounded displayed premium by $10^4$.

**Double check:**

1. Under a pro-rata shock, the selected-flow ratio is close to the selected weight sum and does not change with $\rho$.

## Topic: Counts and order of work

**Purpose:** Return counts correctly and finish the files within the request budget.

**When to use:** A count above a threshold is asked for, and always when writing outputs.

**How to implement:** A count above a threshold is the integer number of names meeting or exceeding it. Parse all inputs in one cell, build all tables in two or three cells, write each deliverable as soon as it is computed, read back once.

**Limitations and cautions:**

1. Do not return a list of names for a count.
2. Do not use one input per cell, and do not hold every write until the end.
3. `groupby(key).apply(f)` in this pandas version drops the grouping column from each group and from the result, so a later lookup of that column raises `KeyError`, and merging again does not help. Use `groupby(key)[col].rank(...)`, `transform` or `agg` and assign the result back to the original frame; print `df.columns` once after the first error instead of re-running the merge.

**Double check:**

1. Every output file listed by the task exists before finishing.
2. After any groupby, the grouping column is still a column of the frame you keep using.
