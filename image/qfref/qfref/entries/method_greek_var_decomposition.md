# Method: VaR of an option position split into delta, gamma and vega parts

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Component VaRs of an option position

**Purpose:** Compute a one-day VaR of an option position for each Greek component (delta, gamma, vega) and the share of each in the total.

**When to use:** The task asks for a one-day VaR of an option position by Greek component, or for each component's share of the risk.

**Constraints:**

1. Keep every component on the same one-day horizon: the spot move and the volatility move are both one-day changes.
2. Use a separate, descriptive variable for each quantity: periods per year, barrier level, strike and notional each get their own name, and no name is reused for another quantity later in the session. Reason: in a barrier task the barrier is often called B; a periods-per-year constant stored under the same name is silently overwritten, and the one-day move then divides by the square root of the barrier.
3. Do not rescale the volatility-of-volatility by $\sqrt{P}$ again once it is a one-day change: the standard deviation of daily differences of an annualized volatility path is already a one-day change in annualized-volatility units, so annualizing and then scaling to one day multiplies and divides by $\sqrt{P}$, and the two cancel.

**How to implement:**

Step 1: Inputs. Print the number of contracts $n$; the Greeks $\Delta$, $\Gamma$, $\mathcal V$ at the pricing volatility $\sigma$ (annual); the confidence level and $z=N^{-1}(\text{level})$ (`scipy.stats.norm.ppf`); the periods per year $P$ from the task (252 is common); and the volatility path the task names (for example a daily GARCH conditional volatility, see the arch card for its units).

Step 2: One-day spot move scale (print $P$, $\sigma$ and $\Delta S$ in this step):

$$\Delta S=\frac{S_0\,\sigma}{\sqrt P}$$

Step 3: Delta component:

$$\mathrm{VaR}_\Delta=\left|n\,\Delta\,z\,\Delta S\right|$$

Step 4: Gamma component, in the form the task defines (Topic 2); the usual scenario form is the second-order P&L at the VaR move:

$$\mathrm{VaR}_\Gamma=\tfrac12\left|n\,\Gamma\right|(z\,\Delta S)^2$$

Step 5: Volatility-of-volatility: the annualized volatility path (for a daily fit in percent, divide by 100 and multiply by $\sqrt P$), its daily changes (absolute differences, or log changes times the volatility level, as the task names), and their standard deviation with the `ddof` the task names.

Step 6: Vega component:

$$\mathrm{VaR}_{\mathcal V}=\left|n\,\mathcal V\,z\,\sigma_{\sigma}\right|$$

with $\sigma_\sigma$ the one-day volatility-of-volatility from Step 5.

Step 7: Aggregate and take shares by the rule of Topic 2; print which aggregation the shares use.

**Double check:**

1. $\Delta S/S_0$ is a plausible one-day move (about $\sigma/16$ for $P=252$); a much larger value means the periods-per-year variable was overwritten: recompute with the value from the task.
2. The mean of the annualized volatility path lies in a plausible range (about 0.02 to 2); outside it, the units of the fit were not converted.
3. The shares sum to 100.

## Topic 2: Choices in the decomposition

**Purpose:** Pick the gamma form, the aggregation and the volatility-of-volatility definition from the task's wording.

**When to use:** Together with Topic 1, whenever the task does not fix one of these choices explicitly.

**How to implement:**

Step 1: Read each choice from the task text:

| Choice | Options | How to pick |
|---|---|---|
| Gamma component | (a) scenario form $\tfrac12\lvert n\Gamma\rvert(z\Delta S)^2$, the second-order P&L at the VaR move; (b) variance form from the delta-gamma-normal expansion, gamma-term variance $\tfrac12(n\Gamma)^2(\Delta S)^4$, independent of $z$; (c) Cornish-Fisher or full revaluation | the definition the task writes; (a) is the usual one when components are reported as VaRs side by side |
| Aggregation | square root of the sum of squared component VaRs (independent factors); with covariance terms (delta and vega moves correlated); a plain sum (perfect correlation, an upper bound) | the task's stated aggregation; shares follow the same choice (variance shares for the first two, VaR shares for the plain sum) |
| Volatility-of-volatility | daily changes of the annualized volatility path (absolute) or log changes (relative, then multiplied by the volatility level); `ddof` 1 or 0; the path from a GARCH fit or from implied volatilities | the series, difference type and `ddof` the task names; keep it on the one-day horizon |

Step 2: Independent factors: total $=\sqrt{\mathrm{VaR}_\Delta^2+\mathrm{VaR}_\Gamma^2+\mathrm{VaR}_{\mathcal V}^2}$ and each share $=100\,\mathrm{VaR}_i^2/\sum_j\mathrm{VaR}_j^2$. Plain sum: total $=\sum_i\mathrm{VaR}_i$ and each share $=100\,\mathrm{VaR}_i/\sum_j\mathrm{VaR}_j$.

**Limitations and cautions:**

1. Variance shares and plain-sum shares both sum to 100 but give different numbers; they are not interchangeable.

**Double check:**

1. Recompute the total from the printed components with the chosen rule and compare it with the reported total.
