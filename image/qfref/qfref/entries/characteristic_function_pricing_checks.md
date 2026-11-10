# Characteristic-function option prices: choosing and checking a numerical integration

The task description inside <task_instructions> takes priority over this card: where it gives a different formula or a rule, follow the task description.

## Concepts

Semi-analytic prices such as $C = S e^{-qT} P_1 - K e^{-rT} P_2$ with $P_j = \tfrac12 + \tfrac1\pi \int_0^\infty \mathrm{Re}\left[\frac{e^{-i\eta \ln K} g_j(\eta)}{i\eta}\right] d\eta$ have an oscillating integrand. Integration error appears first where the price is small: short maturities and deep out-of-the-money strikes.

## Algorithm: judge integration methods against a high-accuracy reference

```text
1   price the comparison grid with every candidate method exactly as the task specifies it
2   reference <- the same prices from a much more accurate integration: scipy.integrate.quad with
        epsabs = 1e-12, epsrel = 1e-12, a larger limit (for example 1000) and an upper bound well beyond
        where the integrand has decayed (check that doubling the bound does not change the price)
3   error of each method <- max over the grid of |method price - reference price|; print all of them
4   also test every price against no-arbitrage bounds:
        max(S e^{-qT} - K e^{-rT}, 0) <= C <= S e^{-qT};  C decreasing and convex in K
        a method that gives a price below its lower bound (for example a negative call) is inaccurate there
5   two methods agreeing with each other, or disagreeing, does not show which one is accurate; when the
        task's selection rule compares the methods, decide with the errors from step 3 and the checks
        from step 4, apply the rule, and state the numbers that decided it
6   use the chosen method, with the task's settings, for all later prices
```

## Implied volatility from these prices

- Before root-finding, check the price against the same bounds. A price at or below the lower bound has no implied volatility above zero; a solver bracket such as $[10^{-4}, 5]$ then returns its lower end.
- An implied volatility equal to the lower end of the search interval is a diagnosis of the price, not a result: check the integration at that strike and maturity.
- Deep out-of-the-money short-dated prices can be smaller than the absolute tolerance of the integrator; tighten `epsabs`/`epsrel`, raise the upper integration limit, or use the method with the smaller error in steps 3 and 4.
