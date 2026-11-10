# HAC observation time and identification: replacement scope

Use this block to clarify the time-axis and rank assumptions of HAC and factor-regression inference. Explicit task definitions govern the observation clock, lag bandwidth and finite-sample correction. This block supplements mathematical definitions, not a strategy or data-cleaning policy.

## Observation time

A HAC lag refers to a separation in the modeled observation sequence. Consecutive trading sessions need not be consecutive calendar days. Deleting a missing internal month and treating its neighbors as adjacent changes a monthly lag into an observed-row lag. These conventions need not give the same covariance estimate. Neither filling missing returns with zero nor joining arbitrary unequal time intervals is implied by the standard formula.

Overlapping multi-period returns share innovations; this creates serial dependence even when the underlying single-period innovations are independent. Dependence can extend beyond the overlap length because of persistent regressors, estimation windows or underlying serial correlation. A bandwidth based only on overlap is a minimum heuristic in that setting, not a guarantee of valid inference.

## Identification

Let X be the estimation design matrix with T rows and k columns, E the T-by-N residual matrix, and F the T-by-m factor matrix. A prime is transpose. Counting observations is necessary but not sufficient for invertibility; repeated or linearly dependent columns remain unidentified at any sample size.

Full-column-rank condition for the OLS normal matrix:

$$
\operatorname{rank}(X) = k
$$

Nonsingularity of a residual covariance proportional to E'E:

$$
\operatorname{rank}(\operatorname{E}) = N
$$

Nonsingularity of the centered factor covariance, with $F_{\mathrm{centered}}$ denoting column-demeaned factors:

$$
\operatorname{rank}(F_{\mathrm{centered}}) = m
$$

The degrees-of-freedom inequalities in a joint-$\alpha$ test do not replace these conditions. A generalized inverse defines a different statistic unless the test's theory explicitly allows it. HAC changes estimated uncertainty; it cannot identify coefficients in a rank-deficient design.

## Source and derivation

[Statsmodels HAC documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html) states the ordered, equally spaced single-series assumption. Calendar interpretation above specifies that spacing's economic meaning. The rank statements follow from v'X'Xv=||Xv||^2 and the same identity for residual and centered-factor matrices. They do not assert a new asymptotic test.
