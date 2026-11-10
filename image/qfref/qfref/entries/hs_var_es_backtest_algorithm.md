# Historical-simulation VaR / ES and the expanding-window VaR backtest
The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

Historical-simulation (HS) VaR at confidence $c$ is an order statistic of the empirical loss distribution, and ES is the mean of the losses at or beyond that order statistic. Write one function with one order-statistic rule and reuse it for the full sample, ES and every backtest window.

```text
1. Inputs: return series $r_1..r_n$ (portfolio level), confidence $c$, tail $\alpha = 1 - c$.
2. Losses: $L_i = -r_i$ (positive = loss).
3. Choose ONE order-statistic rule. The task's definition wins; common choices:
   (a) sort losses descending (`np.sort(L)[::-1]`), $k = \lceil n\alpha \rceil$ ($k \ge 1$),
       VaR = k-th largest loss (element `k-1`), ES = mean of the k largest losses;
   (b) `np.quantile(L, c, method=...)` with interpolation, ES = mean of $L \ge$ VaR;
   (c) as (a) with $k = \lfloor n\alpha \rfloor$.
   If the task does not say, pick one and state it in the output notes.
   Ascending vs descending sort changes which element `k-1` is: check that VaR is a large loss.
4. ES uses the same k (or the same threshold) as VaR from the same sorted array.
5. Wrap steps 2-4 in `hs_var_es(returns, c) -> (var, es)`.
6. Use this one function for the full sample and for every backtest window.
7. Expanding-window backtest: for each test day t from the first allowed index to the end,
   window = returns strictly before t (index < t); (var_t, _) = hs_var_es(window, c);
   exceedance_t = ($L_t$ > var_t), or $\ge$ if the task says so. Count exceedances x over T days.
8. Kupiec POF with $p = \alpha$, $\hat p = x/T$:
   $LR = -2[(T-x)\ln(1-p) + x\ln p - (T-x)\ln(1-\hat p) - x\ln \hat p]$,
   p-value = `scipy.stats.chi2.sf(LR, 1)`; when x = 0 drop the $x\ln\hat p$ term.
9. Apply unit scaling (returns vs currency) once at output time; every summary statistic derived from a per-method table uses the same units as that table.
```

Checks:
- $\mathrm{ES}_c \ge \mathrm{VaR}_c > 0$ for each confidence, and the full-sample HS VaR equals `hs_var_es` applied to all data.
- Backtest exceedance rate is near $\alpha$ (same order of magnitude); a rate near $1-\alpha$ or near 0.5 means the sort direction or k is inverted.
- Summary ranges / min / max match the per-method table they summarise (same units).
