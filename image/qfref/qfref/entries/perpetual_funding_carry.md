# Perpetual funding carry: cash flows, rate units and mean reversion

Use this note for periodic funding payments and carry from a spot/perpetual hedge. Distinguish a funding-rate-only return model from the complete trade P&L. Settlement timing, notional definition, return denominator and estimation conventions follow the contract.

## Funding cash flows

Let $f_{j}$ be a decimal funding rate at settlement j and $N_{j}$ the positive position notional in settlement currency. Under the positive-long-pays convention, the short receives the following cash flow.

$$
\mathrm{cash}_{\mathrm{short},j} = N_{j}\cdot f_{j}
$$

The long has the opposite cash flow. The signed funding rate and the signed fee shown in an account ledger need not use the same sign convention. One basis point is an absolute $0.0001$ in decimal rate units, or $0.01\%$, not a relative fraction of the current rate.

For constant notional N and capital denominator N, simple accumulated funding return is additive.

$$
R_{\mathrm{funding}} = \sum _{j} f_{j}
$$

For varying notionals or a different capital denominator C, the cash-flow return changes.

$$
R_{\mathrm{cash}} = \sum _{j} N_{j}\cdot f_{j} / C
$$

Thus funding return on notional differs from return on posted margin. Spot/perpetual basis movement, financing, trading fees, slippage and liquidation exposure remain in the complete trade even if the price $\delta$ is approximately hedged. Positive expected funding alone does not imply a riskless arbitrage.

With A settlements per year and H included settlements, a simple annualized rate is a rescaling, not compounded wealth growth.

$$
R_{\mathrm{annual}} = (A/H)\cdot R_{\mathrm{funding}}
$$

Settlement indices decide whether the known initial rate is included; phrases such as starting rate and first realized payment must refer to the same convention.

## OU estimation conventions

Let f be modeled as $\mathrm{d}f=\kappa(\mu-f)\mathrm{d}t+\sigma\mathrm{d}W$, with constant parameters. In a regression of changes on the previous level, write the intercept $\alpha$ and slope $\beta$. The Euler parameter mapping is:

$$
\begin{gathered}
\kappa _{\operatorname{E}} = -\beta /h \\
\mu _{\operatorname{E}} = -\alpha /\beta \\
\sigma _{\operatorname{E}} = s_{\mathrm{residual}}/\sqrt{h}
\end{gathered}
$$

For an exact AR(1) level regression $f_{\mathrm{next}}=a+bf+\mathrm{error}$ with $0<b<1$, the continuous-time mapping is different.

$$
\begin{gathered}
\kappa _{\mathrm{exact}} = -\ln (b)/h \\
\mu _{\mathrm{exact}} = a/(1-b) \\
\sigma _{\mathrm{exact}} = s_{\mathrm{residual}}\cdot \sqrt{2\cdot \kappa _{\mathrm{exact}}/(1-b^{2})}
\end{gathered}
$$

Residual standard-deviation degrees of freedom are an estimation convention. Neither mapping licenses silently replacing a specified estimator with the other. Calibration and simulation are separate choices: Euler plug-in estimates can be used in an exact OU transition.

## Risk of accumulated funding

For a covariance-stationary sequence with autocovariance $\gamma _{l}$ at lag l, the variance of the H-settlement sum includes cross-period dependence.

$$
\operatorname{Var}(\sum _{j=1}^{H} f_{j}) = H\cdot \gamma _{0} + 2\cdot \sum _{l=1}^{H-1} (H-l)\cdot \gamma _{l}
$$

The iid simplification retains only $H\gamma_0$. Positive weighted autocovariances increase the true sum variance; negative ones can decrease it. The variance of the mean divides this sum variance by H^2. These stationary formulas do not describe the initial transient conditional on a fixed $f_{0}$.

Loss is minus return. Quantile loss, a loss quantile floored at zero, and the mean strictly above that threshold are distinct risk definitions. A strict tail can be empty; it must not silently become a zero empirical estimate.

## Sources and scope

[Bybit, Funding Fee Calculation](https://www.bybit.com/en/help-center/article/Funding-fee-calculation?category=cd60af6303161fd598) documents the payer direction, notional-based fee and contract-dependent settlement intervals. It is an example of an exchange convention, not a substitute for another venue's rules. OU mappings and the variance-of-sums identity are algebraic consequences of the SDE transition and covariance expansion. No specific funding cadence or fixed risk threshold is assumed here.
