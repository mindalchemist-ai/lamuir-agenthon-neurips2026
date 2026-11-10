# Turnover, trading costs and turnover limits in portfolio rebalancing

The task description inside <task_instructions> takes priority over this card: where it defines turnover, cost, a cap rule, an order of operations or the first rebalance differently, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Measuring turnover

**Purpose:** Quantify the fraction of the book traded at a rebalance.

**When to use:** Whenever a task reports turnover, charges costs on trades, or limits trading.

**How to implement:**

Step 1: Identify the weights held before the rebalance, $w^{\mathrm{old}}$, and after it, $w^{\mathrm{new}}$, as fractions of capital (not percentages, not share counts).

Step 2: Put both on one index containing every name held in either period; a name absent from one side has weight $0$ there.

Step 3: Two-way turnover is $\sum_i|w^{\mathrm{new}}_i-w^{\mathrm{old}}_i|$; one-way turnover is half of it, the usual "fraction of the portfolio replaced". Use the definition the task states, and note that a cap and a report may use different ones.

**Implementation tips:**

1. Keep the aligned vectors for the whole session; every later cost, cap and report uses them.

**Limitations and cautions:**

1. Comparing only the names selected this period misses the names that were sold out; those are trades too.

**Double check:**

1. Building a fully invested book from cash has one-way turnover equal to half its gross leverage.

## Topic 2: Transaction costs

**Purpose:** Charge trading costs consistently with the stated convention.

**When to use:** The task states a cost rate on trades.

**How to implement:**

Step 1: Read the convention: a rate per unit of two-way change, a rate per side, or a rate per unit of one-way turnover, in basis points or decimals ($1\,\mathrm{bp}=10^{-4}$).

Step 2: Cost $=c\sum_i|\Delta w_i|$ for a rate $c$ per unit traded on each side; a rate $c_1$ per unit of one-way turnover gives the same cost when $c_1=2c$.

Step 3: Net return $=$ gross return $-$ cost, both from the weights actually held.

**Limitations and cautions:**

1. Mixing a per-side rate with one-way turnover halves or doubles the cost.

**Double check:**

1. Recompute the cost from the final and previous weights and compare with the reported value.

## Topic 3: Turnover cap by proportional shrink toward the old weights

**Purpose:** Trade toward a target portfolio but stop at a stated portfolio-level turnover limit.

**When to use:** The task states a portfolio-level cap ("one-way turnover at most x") and a target portfolio, or states a cap without saying how to enforce it; this is the standard default. Use per-name limits or an optimizer instead when the task states those.

**How to implement:**

Step 1: Compute the turnover of the target against the old weights, measured the way the cap is stated.

Step 2: If it is within the cap, trade to the target. Otherwise set $w=w^{\mathrm{old}}+\lambda(w^{\mathrm{tgt}}-w^{\mathrm{old}})$ with $\lambda=\mathrm{cap}/\mathrm{turnover}(w^{\mathrm{tgt}})$; turnover is linear in $\lambda$ along this line, so the result sits exactly on the cap.

**Implementation tips:**

1. Every name trades in the target's direction, scaled by the same $\lambda$.

**Limitations and cautions:**

1. The shrink does not preserve neutrality or leverage conditions that the target met; see Topic 6.

**Double check:**

1. The turnover of the result equals the cap (within a tiny tolerance) whenever the cap binds.

## Topic 4: Turnover limit by per-name clipping

**Purpose:** Limit the trade in each position separately.

**When to use:** The task states a limit per position (for example "no weight changes by more than x", or a liquidity-based limit per name) rather than a portfolio-level cap.

**How to implement:**

Step 1: For each name, clip the trade: $\Delta w_i=\mathrm{clip}\big(w^{\mathrm{tgt}}_i-w^{\mathrm{old}}_i,\,-c_i,\,c_i\big)$ with $c_i$ the stated limit.

Step 2: $w=w^{\mathrm{old}}+\Delta w$.

Step 3: If the task also states a portfolio-level cap, clip first, then shrink the clipped trade proportionally to the portfolio cap.

**Limitations and cautions:**

1. Clipping does not hit a portfolio-level cap exactly and changes the shape of the trade, so leverage and neutrality usually need attention afterwards.

**Double check:**

1. Every $|\Delta w_i|\le c_i$.

## Topic 5: Turnover constraint inside an optimization

**Purpose:** Choose the best portfolio subject to turnover and other constraints at the same time.

**When to use:** The task asks for an optimal portfolio under an objective (expected return, risk, costs) with several constraints that must all hold exactly, or names an optimizer. Do not introduce an optimizer when the task describes a simpler rule.

**How to implement:**

Step 1: Write the objective and every constraint (turnover, neutrality, leverage, bounds) from the task.

Step 2: Solve with the stated optimizer, or otherwise a constrained solver (for example SLSQP from `scipy.optimize`), starting from the old weights.

**Limitations and cautions:**

1. The absolute value in turnover is not smooth; split each trade into buy and sell parts, or use a solver that handles it, and check convergence.

**Double check:**

1. Every constraint holds at the solution; the solver reports success.

## Topic 6: Combining a turnover cap with other portfolio constraints

**Purpose:** Decide what holds exactly at the end when a cap meets neutrality projections or leverage normalizations.

**When to use:** The task requires, besides the cap, a projection (for example zero beta or zero net exposure) or a normalization (for example gross leverage 1).

**How to implement:**

Step 1: When the task gives an order of operations (shrink, project, normalize, recheck), follow it exactly, including any instruction not to renormalize after a final shrink.

Step 2: Apply any projection to the whole aligned vector, every name of either period, not only to this period's selection.

Step 3: Report the leverage and exposures the final weights actually have, which may differ from the targets (for example gross leverage below 1 after a final shrink).

**Limitations and cautions:**

1. A shrink toward old weights breaks the projection; re-projecting moves turnover off the cap. Only one of the two can be exact unless the task's order resolves it or an optimizer handles both.

**Double check:**

1. Print the turnover, gross leverage and each constrained exposure of the final weights.

## Topic 7: First rebalance, carrying weights forward, and reporting

**Purpose:** Keep reported figures consistent with the weights actually held over time.

**When to use:** Any multi-period rebalanced backtest.

**How to implement:**

Step 1: First rebalance: starting from cash, $w^{\mathrm{old}}=0$, so building the book counts as turnover and may itself hit the cap; some tasks exempt it. Follow the task; when it is silent, start from zero and state it.

Step 2: The next period's $w^{\mathrm{old}}$ is this period's final traded weights, not the uncapped target.

Step 3: Compute every reported turnover, cost, leverage, return and exposure from the final weights against the previous final weights.

**Limitations and cautions:**

1. Reporting the target's turnover, dropping last period's holdings from the alignment, and carrying the target forward are the common mistakes.

**Double check:**

1. Reported turnover equals the recomputed turnover of the final weights and is within the cap; reported gross leverage equals $\sum_i|w_i|$ of the final weights.
