# Age-weighted empirical loss distributions

Use this reference when past scenarios receive unequal probabilities, particularly exponentially decaying age weights. Probability weighting changes the empirical distribution; it is different from scaling each observation's return.

## Shared Foundations

$L_{i}$ is the loss in scenario i, with larger values representing worse outcomes. Map the task's return/loss sign, horizon, weighting clock, quantile interpolation and ES convention explicitly. Observation age and calendar age are not interchangeable.

For nonnegative ages $a_{i}$, newest age zero, and decay $0<\lambda \le 1$, normalized scenario probabilities are:

$$
p_i=\frac{\lambda^{a_i}}{\sum_j\lambda^{a_j}}
$$

At $\lambda =1$ all observations are equally weighted. Weights remain attached to their scenarios when losses are sorted. They are not reassigned according to loss severity.

## Quantile and tail mean

The weighted empirical cumulative distribution is:

$$
F(x) = \sum _{i} p_{i}\cdot \operatorname{indicator}(L_{i}\le x)
$$

The lower generalized-inverse loss quantile at confidence $0<\alpha <1$ is:

$$
q_{\alpha} = \inf \{x: F(x)\ge \alpha \}
$$

Round-off in cumulative normalized weights can move an exact atom boundary. Use a tolerance tied to floating-point summation error when testing that boundary, and check it against the exact count for equal weights; do not change the confidence level or merge genuinely different small probability masses. This step quantile differs from an interpolated sample quantile. An implementation's unweighted default does not define a universal weighted interpolation rule.

For integrated-quantile expected shortfall, include all probability above the threshold and only the needed part of the atom at the threshold:

$$
\begin{gathered}
\operatorname{ES}_{\alpha} = [\sum _{L_{i}>q_{\alpha}} p_{i}\cdot L_{i} \\
+ q_{\alpha}\cdot (1-\alpha -\sum _{L_{i}>q_{\alpha}} p_{i})]/(1-\alpha )
\end{gathered}
$$

The fraction of the atom used is nonnegative and no larger than its probability. This ES is generally not $\operatorname{E}[L\vert L\ge q_{\alpha}]$; the latter includes the entire threshold atom. If a task explicitly requests that conditional mean, it defines a different statistic.

An equivalent characterization, useful for an independent mathematical check, is:

$$
\operatorname{ES}_{\alpha} = \min _{c} [c + \sum _{i} p_{i}\cdot \max (L_{i}-c,0)/(1-\alpha )]
$$

## Horizon and scope

For log returns $x_{t}$, a cumulative H-period log return is the sum of H consecutive values. For simple returns, cumulative return is $\prod (1+r_{t})-1$. These are different scenarios. Overlapping scenarios are statistically dependent; empirical quantiles still exist, but an iid uncertainty calculation need not apply. The age assigned to a multi-period scenario must correspond to a stated observation endpoint or other explicit convention.

If losses become $L_{\mathrm{new}}=a+bL$ with $b>0$, quantile and integrated ES transform affinely: $q_{\mathrm{new}}=a+b\cdot q_{\mathrm{old}}$ and $\operatorname{ES}_{\mathrm{new}}=a+b\cdot \operatorname{ES}_{\mathrm{old}}$. Equal weights recover the discrete empirical distribution, including its atoms. Greater emphasis on recent observations does not imply that risk must increase.

## References

[NumPy quantile documentation, weighted quantiles](https://numpy.org/doc/stable/reference/generated/numpy.quantile.html), for empirical probability and generalized-inverse conventions. Tail-atom and minimization identities follow directly by integrating the discrete loss quantile; no continuity assumption is needed.
