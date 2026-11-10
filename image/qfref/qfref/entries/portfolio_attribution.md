# Holdings-based return attribution

Use this entry to explain a portfolio's return relative to a benchmark through category allocation and within-category selection. This is a holdings-based accounting decomposition, not a regression estimate of factor exposures or a variance decomposition. Categories may be sectors, countries or asset classes.

Map the notation to the contract's definitions. Explicit conventions for rebalancing, cash, return measurement and multiperiod aggregation take precedence. Returns and weights below are decimal quantities; one unit of return equals 10,000 basis points.

## 1. What the weights and returns measure

For one period, let $\mathrm{wP}_{i}$ and $\mathrm{wB}_{i}$ be the category's portfolio and benchmark weights at the period's beginning. Include cash and financing where applicable so both complete weight sets sum to one. Let $\mathrm{rP}_{i}$ and $\mathrm{rB}_{i}$ be the returns of the respective holdings within category i; these need not be the same even when the category labels agree. Let RP and RB be total portfolio and benchmark returns.

**Within-category return, for nonzero category weight $W_{i}$.** Security j has whole-portfolio weight $a_{j}$ and simple return $r_{j}$. Dividing by the category weight distinguishes a category return from its contribution to the whole portfolio.

$$
\begin{gathered}
W_{i} = \sum _{j \in  \mathrm{category} i} a_{j} \\
r_{i} = \sum _{j \in  \mathrm{category} i} a_{j}\cdot r_{j} / W_{i}
\end{gathered}
$$

When $W_{i}$ is zero, this quotient is undefined. A reference return convention is needed for any attribution term still involving that category. A zero contribution alone does not identify its hypothetical return.

**Portfolio return from category contributions.**

$$
\mathrm{RP} = \sum _{i} \mathrm{wP}_{i}\cdot \mathrm{rP}_{i}
$$

**Benchmark return from its own holdings.** A convenient market index is not interchangeable with a specified weighted benchmark.

$$
\mathrm{RB} = \sum _{i} \mathrm{wB}_{i}\cdot \mathrm{rB}_{i}
$$

## 2. Single-period Brinson–Fachler attribution

Use the following three-effect form when separating allocation, selection and their interaction. Other variants may combine selection and interaction; the labels alone do not establish which definition is intended. These identities assume comparable simple returns over the same period, with any costs treated consistently.

**Allocation effect $A_{i}$: overweighting a category relative to the benchmark's total return.**

$$
A_{i} = (\mathrm{wP}_{i}-\mathrm{wB}_{i})\cdot (\mathrm{rB}_{i}-\mathrm{RB})
$$

**Selection effect $S_{i}$: different holdings' performance at benchmark category weight.**

$$
S_{i} = \mathrm{wB}_{i}\cdot (\mathrm{rP}_{i}-\mathrm{rB}_{i})
$$

**Interaction effect $I_{i}$: allocation and selection differences together.**

$$
I_{i} = (\mathrm{wP}_{i}-\mathrm{wB}_{i})\cdot (\mathrm{rP}_{i}-\mathrm{rB}_{i})
$$

**Reconciliation to arithmetic active return for this period.** This follows by expansion and $\sum _{i}(\mathrm{wP}_{i}-\mathrm{wB}_{i})=0$, not by a fitted residual.

$$
\sum _{i} (A_{i}+S_{i}+I_{i}) = \mathrm{RP}-\mathrm{RB}
$$

The uncentered Brinson allocation expression uses $\mathrm{rB}_{i}$ instead of $\mathrm{rB}_i-\mathrm{RB}$. Its total allocation equals the centered total when both weight sets sum to one, but its category allocation contributions differ. Do not mix the two category definitions within a report.

**Off-benchmark cash under an explicit common cash-return convention.** If $\mathrm{wB}_{c}=0$ and $\mathrm{rB}_{c}=\mathrm{rP}_{c}=r_{\mathrm{cash}}$, the cash selection and interaction vanish. This conclusion requires the return convention; zero benchmark weight alone only forces selection to zero.

$$
\begin{gathered}
A_{c} = \mathrm{wP}_{c}\cdot (r_{\mathrm{cash}}-\mathrm{RB}) \\
S_{c} = 0 \\
I_{c} = 0
\end{gathered}
$$

## 3. Return timing and drifting weights

Use start-of-period weights to attribute the returns earned during that period. Under buy-and-hold within a period, with no external flows, trades or unmodelled fees, each position's wealth changes by its own gross return. Let $w_{i}$ be its initial weight and $r_{i}$ its holding return, with positive total ending wealth.

**Ending weight before any new rebalance.** This is also the next period's initial weight if no intervening trade occurs.

$$
w_{i,\mathrm{end}} = w_{i}\cdot (1+r_{i}) / (1+\sum _{j} w_{j}\cdot r_{j})
$$

A rebalance sets the subsequent weights to the new allocation; it does not retroactively change the weights that earned earlier returns. External flows require a flow-adjusted return convention.

**Simple total return from a total-return index J.** Both endpoints must refer to the same holding and consecutive period boundaries.

$$
r_{t} = J_{t}/J_{t-1}-1
$$

Ordinary price changes exclude distributions unless adjusted appropriately. Annualized cash quotes also need the stated accrual convention: simple rate times year fraction and effective-rate compounding are different definitions.

When beginning-of-period weights are stored in a table or dict keyed by period-end dates, the entry labelled with the end of period $m$ holds the weights at the start of period $m$; the weights at the beginning of $m$ are that entry, not the one labelled with the end of $m-1$. Check that a reported weight snapshot for period $m$ equals the weights used for period $m$'s effects, for example `assert all(np.isclose(snapshot[k], weights_used[m][k]) for k in snapshot)`.

## 4. Multiperiod meaning

Let $\mathrm{RP}_{t}$ and $\mathrm{RB}_{t}$ be successive period returns; $A_{it}$, $S_{it}$ and $I_{it}$ are period attribution effects.

**Compounded portfolio return.**

$$
\mathrm{RP}_{\mathrm{total}} = \prod _{t} (1+\mathrm{RP}_{t})-1
$$

**Compounded benchmark return.**

$$
\mathrm{RB}_{\mathrm{total}} = \prod _{t} (1+\mathrm{RB}_{t})-1
$$

**Unlinked sums of effects explain the sum of period active returns.**

$$
\sum _{t} \sum _{i} (A_{it}+S_{it}+I_{it}) = \sum _{t} (\mathrm{RP}_{t}-\mathrm{RB}_{t})
$$

The right side generally differs from $\mathrm{RP}_{\mathrm{total}}$-$\mathrm{RB}_{\mathrm{total}}$. If unlinked period sums are requested, they remain unlinked sums. To explain compounded active return with linked effects requires a stated linking method; it is not achieved by relabelling the simple sums. Different linking conventions can allocate compounding differently, even when each reconciles overall.

## 5. Checks and scope

Identical portfolio and benchmark holdings and weights give zero active return and zero effects. Equal category weights eliminate allocation and interaction. Equal within-category returns eliminate selection and interaction. Wealth-based drift preserves total weight one under the assumptions above.

A return attribution identity does not imply causality or investment skill. This entry does not cover currency overlays, derivatives with exposure weights different from capital weights, or a complete fee attribution model.

## Sources

[MathWorks, Brinson model documentation, “More About”](https://www.mathworks.com/help/finance/brinsonattribution.html): the centered three-effect identity and distinction between period attribution and linked multiperiod results. Labels here are A/S/I rather than the documentation's S/I/U.

[Lu and Kane (2013), Performance Attribution for Equity Portfolios, §3](https://journal.r-project.org/articles/RJ-2013-025/): holdings-based Brinson interpretation and uncentered allocation convention. Within-category returns above are explicitly normalized by category weight; they are not whole-portfolio contributions. The weight-drift and reconciliation formulas follow directly from wealth accounting and algebra.
