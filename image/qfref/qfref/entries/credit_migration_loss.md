# Rating transitions, credit losses and portfolio aggregation

Use this reference for Gaussian-factor rating migration, default-only portfolio losses, and loss aggregation across scenarios and obligors. It distinguishes these models from full migration-based bond revaluation; it does not estimate a transition matrix from censored rating histories.

## 1. Shared Foundations

Map notation by economic meaning, units and horizon. Explicit task definitions take precedence; if definitions conflict, identify the ambiguity and state the interpretation. A label such as mean loss alone does not identify the averaging population.

Let i index obligors, s index independent scenarios, and k index terminal rating states. $\operatorname{E}_{i}$ is exposure in currency, $R_{i}$ is a recovery fraction, and $p_{ik}$ is the probability of state k conditional on obligor i's initial rating. All probabilities are decimals. Expectations below are under the specified risk distribution, which need not be a risk-neutral pricing measure.

## 2. State mapping and dependence

Each transition row is a categorical probability distribution, including every terminal state in the model.

$$
\begin{gathered}
p_{ik} \ge  0 \\
\sum _{k} p_{ik} = 1
\end{gathered}
$$

For a chosen state ordering, $b_{ik}$ is the cumulative-normal threshold. $\Phi$ denotes the standard normal distribution function; $b_{\mathrm{i0}}$ is minus infinity and $b_{\mathrm{iK}}$ is plus infinity, where K is the number of states.

$$
\begin{gathered}
b_{ik} = \Phi _{\mathrm{inverse}}(\sum _{j=1}^{k} p_{ij}) \\
\mathrm{state}_{i} = k \;\text{when}\; b_{i,k-1} < Z_{i} \le  b_{ik}
\end{gathered}
$$

This construction gives each interval probability $p_{ik}$ by subtraction of two cumulative probabilities. If states run best to worst, high Z is bad; if they run worst to best, low Z is bad. Both conventions are valid when thresholds and the state mapping agree. They give the same distribution but not the same simulated scenarios: with a fixed seed, the bonds that default in a given draw differ between the two orientations. In the CreditMetrics formulation the latent variable is a standardized asset return, so a low value is bad: default is the lowest interval and the best rating the highest, with thresholds cumulated from the default end of the transition row. Use that orientation when the latent variable is described as an asset return or ability-to-pay index, and keep it in every place that reads the thresholds. Equality at a threshold has zero probability under a continuous normal model. Zero-probability states have empty intervals.

For a common nonnegative loading $\beta _{i}$, a unit-normal systematic factor M and mutually independent unit-normal idiosyncratic factors $\epsilon _{i}$ give unit marginal variance.

$$
\begin{gathered}
Z_{i} = \beta _{i}\cdot M + \sqrt{1-\beta _{i}^{2}}\cdot \epsilon _{i} \\
0 \le  \beta _{i} \le  1 \\
\operatorname{Corr}(Z_{i},Z_{j}) = \beta _{i}\cdot \beta _{j}, \text{for distinct} i,j
\end{gathered}
$$

In a homogeneous model $\beta _{i} = \sqrt{\rho}, \rho$ is the pairwise latent correlation. With unequal loadings, $\beta _{i}$ squared is the systematic variance share, not every pair's correlation. Default-indicator correlation is a different quantity.

For upper-tail default probability $p_{iD}$ and $\beta _{i} < 1$, the conditional default probability is:

$$
\begin{gathered}
c_{i} = \Phi _{\mathrm{inverse}}(1-p_{iD}) \\
\operatorname{P}(\mathrm{default}_{i} \vert  M=m) = 1-\Phi ((c_{i}-\beta _{i}\cdot m)/\sqrt{1-\beta _{i}^{2}})
\end{gathered}
$$

For lower-tail default, the corresponding probability is:

$$
\begin{gathered}
c_{i} = \Phi _{\mathrm{inverse}}(p_{iD}) \\
\operatorname{P}(\mathrm{default}_{i} \vert  M=m) = \Phi ((c_{i}-\beta _{i}\cdot m)/\sqrt{1-\beta _{i}^{2}})
\end{gathered}
$$

At $\beta _{i} = 1$ the latent value equals M and the event is deterministic conditional on M; the formulas with a zero denominator are not applicable. Probabilities zero and one represent impossible and certain default without a finite threshold.

## 3. Which loss model applies?

When only default causes loss, $D_{is}$ is the default indicator and $\mathrm{LGD}_{i}$ is the lost fraction of exposure. For deterministic exposure and recovery:

$$
\begin{gathered}
\mathrm{LGD}_{i} = 1-R_{i} \\
L_{is} = \operatorname{E}_{i}\cdot \mathrm{LGD}_{i}\cdot D_{is} \\
L_{s} = \sum _{i} L_{is} \\
\operatorname{E}[L] = \sum _{i} \operatorname{E}_{i}\cdot \mathrm{LGD}_{i}\cdot p_{iD}
\end{gathered}
$$

Correlation changes the distribution but not this expected-loss identity. Random recovery or exposure correlated with default requires the expectation of their product instead.

When nondefault migration changes market value, a default-only loss is insufficient. Let H be the risk horizon, $C_{ij}$ future contractual cash flows paid at dates $t_{ij} > H$, and $\operatorname{P}_{k}$(H,$t_{ij}$) the rating-conditioned valuation discount factors at H. Nondefault horizon value is:

$$
V_{i}(H,k) = \sum _{j:t_{ij}>H} C_{ij}\cdot \operatorname{P}_{k}(H,t_{ij})
$$

Cash flows received on or before H belong to horizon wealth separately, with any specified reinvestment. Default recovery must follow the contract's recovery base and payment timing. Horizon loss is specified reference wealth minus actual wealth, both measured at $H$. Reference wealth may, for example, be the horizon value conditional on the initial rating remaining unchanged; state the requested reference explicitly; a present-value loss discounts consistently. Do not subtract today's price directly from an undiscounted future value. Transition probabilities and rating-dependent valuation inputs have distinct roles. These are the default/nondefault valuation branches of CreditMetrics [1].

## 4. Scenarios, groups and averaging

For a disjoint group G with $n_{G}$ obligors and N scenarios, its scenario loss is a sum across names. Its expected total loss is a mean across scenarios.

$$
\begin{gathered}
L_{Gs} = \sum _{i \in  G} L_{is} \\
\operatorname{mean}_{\mathrm{total},G} = (1/N)\cdot \sum _{s} L_{Gs}
\end{gathered}
$$

The per-obligor mean is a different quantity, defined for $n_{G} > 0$.

$$
\operatorname{mean}_{\mathrm{per},\mathrm{obligor},G} = \operatorname{mean}_{\mathrm{total},G}/n_{G}
$$

For a partition of the portfolio, only group totals add directly to the portfolio total.

$$
\begin{gathered}
\operatorname{mean}_{\mathrm{portfolio}} = \sum _{G} \operatorname{mean}_{\mathrm{total},G} \\
\operatorname{mean}_{\mathrm{portfolio}} = \sum _{G} n_{G}\cdot \operatorname{mean}_{\mathrm{per},\mathrm{obligor},G}
\end{gathered}
$$

An equal-name default rate averages indicators, whereas an exposure-weighted default share averages using exposure. With positive total group exposure:

$$
\begin{gathered}
\mathrm{default}_{\mathrm{rate},G} = \sum _{s} \sum _{i \in  G} D_{is}/(N\cdot n_{G}) \\
\mathrm{default}_{\mathrm{exposure},\mathrm{share},G} = \sum _{s} \sum _{i \in  G} \operatorname{E}_{i}\cdot D_{is}/(N\cdot \sum _{i \in  G} \operatorname{E}_{i})
\end{gathered}
$$

These coincide only in special cases, such as equal exposures. Empty groups have no per-name probability estimate. With states ordered by credit quality, upgrade, unchanged, nondefault downgrade and default are mutually exclusive categories whose probabilities sum to one; default must not also be counted as a nondefault downgrade.

## 5. Quantiles and tails with default-loss atoms

For loss L and confidence $\alpha$ in (0,1), the lower quantile convention is:

$$
q_{\alpha} = \inf  \{x : \operatorname{P}(L \le  x) \ge  \alpha \}
$$

Interpolated empirical quantiles are a different finite-sample convention. A task may define a strict or inclusive conditional tail mean. These definitions are generally different at a loss atom:

$$
\begin{gathered}
\mathrm{tail}_{\mathrm{strict}} = \operatorname{E}[L \vert  L > q_{\alpha}] \\
\mathrm{tail}_{\mathrm{inclusive}} = \operatorname{E}[L \vert  L \ge  q_{\alpha}]
\end{gathered}
$$

An empty strict tail has no conditional mean. Integrated-quantile expected shortfall fills exactly probability $1-\alpha$, taking only the required mass at the quantile [2].

$$
\begin{gathered}
\operatorname{ES}_{\alpha} = (\operatorname{E}[L\cdot \operatorname{indicator}(L>q_{\alpha})] \\
+ q_{\alpha}\cdot (\operatorname{P}(L\le q_{\alpha})-\alpha ))/(1-\alpha )
\end{gathered}
$$

An equivalent expression, for a finite first moment, is [2]:

$$
\operatorname{ES}_{\alpha} = \min _{z} \{z + \operatorname{E}[\max (L-z,0)]/(1-\alpha )\}
$$

For equally weighted scenarios, retain the largest losses until the tail mass is filled, allowing a fractional boundary scenario. Averaging a rounded number of scenarios is an approximation unless the tail size is an integer. Whichever tail definition is required, additive group attribution uses the same portfolio-tail scenarios and boundary weights for every group; separate group tails do not in general add to portfolio ES.

## 6. Checks and Scope

Marginal transition frequencies should recover the input probabilities within sampling error, regardless of dependence. Group loss totals sum exactly scenario by scenario. Expected default-only loss has the analytic check in Section 3. Sampling precision for a probability is governed by independent scenarios; dependent names within a scenario are not independent replications.

Nonnegative exposures and LGD in [0,1] imply loss lies between zero and total exposure. With known deterministic LGDs the upper bound tightens to the sum of exposure times LGD. VaR need not exceed expected loss: a rare severe loss can produce a zero quantile and positive mean. ES, strict tail means and inclusive tail means must not be silently interchanged.

This entry does not cover transition-history estimation, recovery calibration, regulatory capital rules, valuation of callable credit instruments, or arbitrarily dependent stochastic recoveries. Full rating migration revaluation needs contractual cash flows and horizon valuation curves, not merely a default probability.

For cumulative-probability thresholds, set the first and last endpoints explicitly to $-\infty$ and $+\infty$. Do not compute the final endpoint by applying the inverse CDF to a rounded row total.

## References

[1] Gupton, Finger and Bhatia (1997), CreditMetrics Technical Document, Sections 2.3 and 3.1–3.2: rating-dependent revaluation and latent-threshold dependence. [Original document](https://www.phy.pmf.unizg.hr/~bp/CMTD1.pdf).

[2] Rockafellar and Uryasev (2002), Conditional Value-at-Risk for General Loss Distributions: discrete distributions and mass at the quantile. [Author manuscript](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf).
