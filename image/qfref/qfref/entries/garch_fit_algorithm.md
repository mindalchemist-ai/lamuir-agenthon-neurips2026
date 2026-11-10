# Fitting a GARCH(1,1) with `arch`: units, convergence and conversion back

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

## Algorithm

```text
Input:  daily decimal returns r; the mean model and distribution the task names (Zero / Constant, normal / t)
1   units: if the task text explicitly says to fit raw (unscaled) returns, fit r (case 2);
        otherwise fit 100 * r (case 1). Small decimal returns are NOT a reason for case 2:
        a fit on raw decimal returns often stops at the starting values.
2   res <- arch_model(x, vol="GARCH", p=1, o=0, q=1, mean=..., dist=..., rescale=False).fit(disp="off")
3   start <- res.model.volatility.starting_values(np.asarray(res.resid))
    if the fitted volatility parameters equal start (np.allclose): the fit did not move -> refit with case 1
4   convert back (case 1 only): omega / 100**2, every variance / 100**2, every volatility and mean / 100;
        alpha and beta are unchanged
5   print omega, alpha, beta, alpha + beta and the mean conditional volatility in decimal units
```

## Checks

1. $\alpha + \beta < 1$, and neither parameter equals its starting value.
2. In decimal units, $\omega$ is far below $10^{-3}$ and the daily conditional volatility is far below $0.1$.
3. Annualizing a daily volatility multiplies by $\sqrt{B}$ once; a quantity already in one-day units is not divided by $\sqrt{B}$ again.
