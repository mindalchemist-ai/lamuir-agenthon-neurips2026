# Holdings selection and fund membership

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

## Topic: Selecting each fund's holdings

**Purpose:** Keep a requested number of holdings per fund and build the union table with a membership flag per fund.

**When to use:** The task keeps the top $k$ holdings of each fund, builds the union of the selections and flags which fund holds each name.

**How to implement:** Sort each fund's list by decimal weight descending with the declared tie-break, keep the first $k$ rows. This selected table is the only source for that fund from here on. Build one flag per fund from its selected table; overlap means held in both selections.

**Limitations and cautions:**

1. A name in a fund's full list but outside its selection has zero quantity, zero weight, zero value and a missing (NaN) implied price for that fund.
2. Do not look up membership, quantities or weights in the full source list, and do not derive flags from nonzero full-list values.

**Double check:**

1. Each fund's flag count equals the selected count $k$.

## Topic: Weights, values and prices

**Purpose:** Turn displayed weights into decimal weights, dollar values and implied prices.

**When to use:** Weights are displayed as percent numbers (a full list sums to about 100).

**How to implement:** Divide by 100 once into a working column and reuse it. Value of a holding is fund net assets times the decimal weight. The price of a name in one fund is value divided by share quantity (positive quantity only). The price of a name held by several funds is total value divided by total share quantity.

**Limitations and cautions:**

1. Do not convert twice, and do not keep percent units in a decimal output.
2. Do not use market capitalization or a renormalized weight as the value.
3. Do not fill a missing price with zero, and do not average per-fund prices.

**Double check:**

1. A decimal full-fund weight list sums to about 1.

## Topic: Concentration on a selection

**Purpose:** Measure how concentrated a fund is on its selected holdings.

**When to use:** The task asks for a concentration index of the selected portfolio.

**How to implement:** $\sum_i w_i^2$ with full-fund decimal weights of the selected names.

**Limitations and cautions:**

1. Do not renormalize the selection to one unless the task defines a conditional concentration.

**Double check:**

1. The value lies between $1/k$ and 1 for $k$ equally weighted names at the lower end.

## Topic: Writing the deliverable

**Purpose:** Write the table the task asks for from the working table.

**When to use:** Every output file.

**How to implement:** Select exactly the requested columns from the working table. A field named in plural for several funds (list, counts) returns the items, as a list or a mapping fund to integer.

**Limitations and cautions:**

1. Do not add flags or helper columns to the file.
2. Do not return one scalar for a field that is plural.

**Double check:**

1. Compare the header with the task's column list character by character.
