# SVI smile fitting and Dupire local volatility from the fitted slices

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, an input or a convention, follow the task description.

## Rules that decide most results

1. Fit each expiry in total variance $w = \sigma_{\mathrm{BS}}^2 T$ against forward log-moneyness $k = \ln(K/F_T)$, $F_T = S_0 e^{(r-q)T}$.
2. With `scipy.optimize.minimize` on all five parameters, use a restricted model with strictly positive lower bounds, for example $a \in [10^{-6}, \max w]$, $b \in [10^{-4}, 1]$, $\rho \in [-0.999, 0.999]$, $m \in [\min k, \max k]$, $s \in [10^{-3}, 1]$. These bounds are a modelling choice, not general SVI conditions. $a$ ending on its lower bound or $\rho$ near $\pm 0.999$ is common for equity smiles and acceptable; $b$ or $s$ ending on its lower bound means a collapsed fit (a flat or kinked slice): refit from other starts.
3. Divide the residuals by the slice level $\overline{w}$ (total variance is about $10^{-4}$ for a few days, and an unscaled objective stops early). Start $a$ near $\min w$, $b$ near $(\max w - \min w)/\mathrm{range}(k)$, $m$ at the $k$ of the smallest $w$, $s$ near $\mathrm{range}(k)/4$; try several starts and keep the lowest objective.
4. After fitting EVERY candidate expiry, print its error in volatility units, $\mathrm{RMSE}\left(\sqrt{w_{\mathrm{SVI}}/T} - \sigma_{\mathrm{obs}}\right)$, and its parameters. Then select exactly as many expiries as the task asks for, only among those whose fit meets the task's tolerance and whose $b$ and $s$ are off their lower bounds. Spread them over the term structure: place that many target maturities evenly between the shortest and the longest eligible $T$ and take the eligible expiry nearest to each target, without repeats. If the expiry picked for the shortest target has the largest fit error of the candidates or a nearly flat slice ($b$ close to its lower bound), take the next eligible expiry instead: one badly fitted short slice spoils $\partial_T w$ for every strike. Store the selected list once and use it for every output and every count (fitting every expiry is only for screening). Expiries a few days apart give a noisy $\partial_T w$ and can produce negative forward variances. Fit and print all candidates in one cell, and write several output files per cell once their values are computed: the budget of replies is small.
5. Write ONE function `local_vol(k, T)` that evaluates the formula below at any point, and call it for every local volatility the outputs report: each grid node, the at-the-money value of each expiry ($k = 0$), any summary value and the flat-volatility test, whose local volatility must come out of this function (an error of exactly 0 because the input volatility was copied tests nothing). A local volatility is never set equal to an implied volatility, not even "as an approximation": they differ except on a flat surface.
6. Keep every node of the grid you built. A node where the local variance is negative or not finite is a finding to diagnose (see the bullets below), not a row to delete or fill; if the task says what to write there, write that.
7. Output values: write categorical values (option type, side) with the codes the input data use unless the task names others, also after converting puts to calls by parity (keep each quote's original type code, for example `C` / `P`); build grids with `numpy.linspace` so that endpoints are exact and stay inside a stated range (repeated addition of a step can end at 1.2000000000000004).
8. Before writing the surface, check that total variance increases with $T$ at every grid $k$ between neighbouring selected expiries. Where it does not, the grid reaches beyond the strikes the slices were fitted on: when the grid is discretionary, shrink it to the log-moneyness range quoted in every selected expiry and rebuild.

## SVI slice

$$w(k) = a + b\left[\rho(k-m) + \sqrt{(k-m)^2+s^2}\right]$$
The width $s$ is the parameter usually written $\sigma$; output column names follow the task.
$$w_k = b\left[\rho + \frac{k-m}{\sqrt{(k-m)^2+s^2}}\right], \qquad w_{kk} = \frac{b\,s^2}{\left((k-m)^2+s^2\right)^{3/2}}$$
These are derivatives in $k$; in strike, $w_K = w_k/K$ and $w_{KK} = (w_{kk}-w_k)/K^2$. Lee's bound: $b(1+|\rho|) \le 2$.

## Local volatility from total variance (Gatheral's form)

$$\sigma_{\mathrm{loc}}^2(k,T) = \frac{\partial_T w(k,T)}{g(k,T)}, \qquad g = \left(1 - \frac{k w_k}{2w}\right)^2 - \frac{w_k^2}{4}\left(\frac{1}{w} + \frac14\right) + \frac{w_{kk}}{2}$$

- $\partial_T w$ is taken at FIXED $k$ (not fixed strike) from the fitted slices, with the difference scheme the task names (for a forward difference, $(w(k;T_{i+1}) - w(k;T_i))/(T_{i+1}-T_i)$); for the last expiry use what the task says, otherwise a backward difference. $w_k$ and $w_{kk}$ are analytic, so they exist at the ends of the strike grid too.
- This equals the call-price Dupire formula with dividend yield; if the task gives the price form, either is fine as long as derivatives are consistent.
- $g(k) < 0$ (butterfly arbitrage in the slice) or $\partial_T w < 0$ (calendar arbitrage at that $k$) makes the local variance negative. Diagnose at that point: check the fit of that slice, the calendar order at that $k$, and the grid. When the grid is discretionary, prefer the strike range quoted by the slices used in the time derivative; if extrapolation is required, state and validate it.
- Flat check: a constant implied volatility $\sigma$ gives $w = \sigma^2 T$, $g = 1$, $\partial_T w = \sigma^2$, so the function must return $\sigma$; run the same function on such a surface to test it.
- State which moneyness a strike grid is built in ($K/F_T$ or $K/S_0$) and convert when an output column uses the other one.

## Common mistakes

- Spot moneyness $\ln(K/S_0)$ instead of $\ln(K/F_T)$ shifts the smile by $(r-q)T$.
- Fitting $\sigma_{\mathrm{BS}}^2$ without the factor $T$.
- Using $w_k$, $w_{kk}$ as if they were strike derivatives.
- Interpolating between expiries in implied volatility instead of total variance at fixed $k$.
- Reporting an error in total variance where the task asks for it in volatility.
