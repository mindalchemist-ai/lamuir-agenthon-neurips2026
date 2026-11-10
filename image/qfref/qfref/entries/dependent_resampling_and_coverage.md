# Dependent resampling and conditional risk coverage

Use block resampling when preserving serial dependence matters. Explicit task definitions determine residual normalization, block length, refitting, risk horizon and quantile convention. Resampling is not a substitute for a correctly specified conditional variance model.

## Stationary bootstrap

Let the historical series have $n$ ordered rows. A stationary-bootstrap path starts with a uniformly sampled row. For subsequent rows, continue to the next circular index with probability $1-p$, otherwise choose another uniform starting row. The mean block length is $b=1/p$, with $b\ge1$.

The resulting block length has geometric probability:

$$
\Pr(K=k)=p(1-p)^{k-1},\qquad k=1,2,\ldots
$$

For a multivariate series, a common row index preserves within-row dependence. Sampling each column independently destroys that dependence. Taking circular successors preserves time ordering inside blocks; sorting sampled rows does not preserve the bootstrap law.

## Standardized-residual simulation

For conditional covariance $H_t=A_tA_t'$ with nonsingular $A_t$, whitened shocks have identity conditional covariance under the model:

$$
z_t=A_t^{-1}(r_t-m_t)
$$

Drawing historical vectors standardized only by marginal volatilities retains cross-sectional correlation. Applying a fresh correlation factor to those already correlated vectors generally counts correlation again. Whitening/recoloring and complete-row filtered historical simulation are distinct choices. Centering and scaling historical residuals are finite-sample conventions, not automatic model identities.

## Sampling uncertainty

For scalar bootstrap estimates $\widehat\theta^{*(1)},\ldots,\widehat\theta^{*(M)}$, the bootstrap standard error is their sample standard deviation, not that standard deviation divided by $\sqrt M$:

$$
\widehat{\mathrm{SE}}_{\mathrm{boot}}=
\sqrt{\frac1{M-1}\sum_{j=1}^M(\widehat\theta^{*(j)}-\overline\theta^*)^2}
$$

The latter division describes Monte Carlo error in a bootstrap mean. Refit parameters in each replicate when the target includes parameter-estimation uncertainty; holding them fixed addresses a conditional target. A percentile interval uses empirical quantiles of the bootstrap estimates, not quantiles of their individual standard errors.

## Risk coverage

For loss $L_t$ and a forecast made with information through the preceding observation, define the violation indicator by the chosen strict/non-strict convention. Under a continuous correctly calibrated conditional quantile, its conditional probability is:

$$
I_t=\mathbf{1}\{L_t>\operatorname{VaR}_{q,t}\},\qquad
\operatorname{E}[I_t\mid\mathcal F_{t-1}]=1-q
$$

Correct average coverage alone does not imply independent violations. Overlapping multi-period losses can create dependence even with reasonable forecasts. With atoms, an unrandomized quantile can have violation probability below $1-q$, so exact equality is not automatic. Clipping zero transition counts changes likelihood-ratio backtests; evaluate limiting terms such as $0\log0=0$ instead.

## References

[arch: StationaryBootstrap](https://bashtage.github.io/arch/bootstrap/generated/arch.bootstrap.StationaryBootstrap.html), geometric block construction following Politis and Romano (1994). The whitening, variance and conditional-expectation distinctions are direct consequences of the definitions above.
