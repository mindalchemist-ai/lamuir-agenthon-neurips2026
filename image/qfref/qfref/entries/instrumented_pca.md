# Instrumented PCA: conditional loadings, estimation and identification

Use this note for a factor model in which observed characteristics determine exposures to unobserved common factors. Ordinary PCA estimates unrestricted static exposures; it does not impose the characteristic-loading relation below. Explicit definitions of timing, missing data, weighting, normalization and evaluation take precedence. Do not replace an unidentified convention with a convenient rescaling.

## 1. Model and notation

Characteristics must be available before the return interval they describe. Let the eligible asset set at date $t$ contain only observations admitted by the specified missing-data policy. A missing return is not a zero return. If the task states a replacement rule for missing values, apply it once to the panel before any estimation or summary. Every later statistic and every per-asset regression then uses all assets of the replaced panel, not a masked or complete-case subset.

| Symbol | Meaning | Dimensions |
|---|---|---|
| $r_t$ | Vector of observed excess returns at date $t$ | $N_t$ by 1 |
| $Z_t$ | Predetermined characteristics; one row per eligible asset | $N_t$ by $L$ |
| $\Gamma$ | Common map from characteristics to factor exposures | $L$ by $K$ |
| $f_t$ | Contemporaneous latent factor returns | $K$ by 1 |
| $B_t$ | Asset exposures implied by the characteristics | $N_t$ by $K$ |
| $\varepsilon_t$ | Residual returns | $N_t$ by 1 |
| $F$ | Matrix whose row $t$ is $f_t'$ | $T$ by $K$ |

The exposure matrix changes with the characteristics even though its mapping is fixed:

$$
B_t=Z_t\Gamma
$$

Returns combine these exposures with common shocks and residual risk:

$$
r_t=B_t f_t+\varepsilon_t
$$

Changing a characteristic changes exposure; it is not an additive return forecast unless that extension is explicitly included. A constant column of characteristics permits common baseline exposures. It is not by itself a time-series pricing intercept.

## 2. Least-squares estimation

With equal weight on every eligible asset-date observation, the objective is the sum of squared pricing residuals:

$$
Q(\Gamma,F)=\sum_t\|r_t-Z_t\Gamma f_t\|_2^2
$$

Alternating least squares minimizes over one block with the other fixed. Each block is linear least squares, but the joint problem is bilinear. Decreasing residual loss does not prove a unique global optimum. Initialization, convergence criteria and the permitted number of iterations belong to the specified estimator. A prescribed initialization, for example factors drawn from a stated random seed, is part of that estimator: an SVD or PCA start converges to a different rotation and scale, and every rotation-dependent output (factor Sharpe ratios, loading norms, factor correlations and variance shares) changes with it. Use the stated generator and seed. Compute the convergence criterion on finite numbers only; a loss that contains NaN never meets a tolerance.

### Factor block: exposures given

Conditional on $\Gamma$, let $B_t=Z_t\Gamma$. If $B_t$ has full column rank, the normal equations give the cross-sectional factor estimate:

$$
f_t=(B_t'B_t)^{-1}B_t'r_t
$$

This is a regression of returns on exposures at that date. It needs sufficient independent exposures, not merely more assets than factors. Rank deficiency makes the factor vector nonunique; a least-norm solution is an additional convention, not newly identified economic information.

### Characteristic-map block: factors given

Let $z_{i,t}$ be the characteristic column vector for one observation and let $g$ stack the columns of $\Gamma$. The Kronecker product supplies a linear design vector:

$$
x_{i,t}=f_t\otimes z_{i,t}
$$

The scalar fitted return is unchanged by this vectorization:

$$
z_{i,t}'\Gamma f_t=x_{i,t}'g
$$

The normal equations for the characteristic map are:

$$
\left(\sum_{i,t}x_{i,t}x_{i,t}'\right)g
=\sum_{i,t}x_{i,t}r_{i,t}
$$

The sums use the same admitted observations and weights as the original objective. Reshaping $g$ must use the same column-stacking convention as the design. In numpy, with `Gamma` of shape (L, K), `np.kron(f, z) @ Gamma.ravel(order="F")` equals `z @ Gamma @ f`; with this design, the default row-major `ravel()` and `reshape(K, L)` without a transpose pair it with a different ordering and give a wrong map. Other Kronecker layouts can use other orders; what matters is that design, flattening and rebuilding use one convention. After solving for `g`, rebuild with `g.reshape(L, K, order="F")` and confirm on one observation that `z @ Gamma @ f` equals `np.kron(f, z) @ g`. Solving least squares by QR or SVD avoids explicitly forming an inverse; an ill-conditioned normal matrix does not become well identified by inversion.

A panel array of shape (T, N, L) built from a long table must keep stock and characteristic on their own axes. `DataFrame.pivot(values=[several columns])` orders the resulting columns characteristic first and stock second, so a direct `reshape(T, N, L)` of its values mixes stocks; build one pivot per characteristic, reindex every pivot to the same date order and the same stock order, stack them on the last axis, then compare one (date, stock, characteristic) cell with the long table.

For exact block solutions, an alternating step cannot increase $Q$. Compare fitted returns or the objective when diagnosing convergence: unconstrained factors and loadings can change scale without changing predictions. An arbitrary numerical tolerance is not an economic identification condition.

## 3. Rotation, scale and centered covariance

Use this section before interpreting individual factors or scale-sensitive summaries. For any nonsingular matrix $H$, these transformations leave fitted returns unchanged:

$$
\Gamma^*=\Gamma H,\qquad f_t^*=H^{-1}f_t
$$

Thus least-squares fit alone does not determine factor scale or axes. For a scalar rescaling, factor standard deviations change inversely to loading magnitudes. A factor Sharpe ratio is unchanged by positive scaling but reverses under a sign flip.

For an orthogonal rotation $Q$, rows of $F$ and columns of Gamma rotate by the same matrix:

$$
F^*=FQ,\qquad\Gamma^*=\Gamma Q,\qquad Q'Q=I
$$

The uncentered factor second moment is:

$$
M_F=\frac{F'F}{T}
$$

If $M_F=Q\Lambda Q'$, the rotated second moment is diagonal:

$$
\frac{(FQ)'(FQ)}{T}=\Lambda
$$

In numpy, with eigenvectors `Q` from the factor second moment, rotate as `F_rot = F @ Q` and `Gamma_rot = Gamma @ Q` (not `Q.T`), then check that `Z @ Gamma_rot @ f_rot` reproduces the fitted returns. A norm or singular-value check cannot catch a wrong rotation, since both are unchanged by any orthogonal matrix. This rotation does not select a new scale. Orthogonal rotations preserve Gamma's Frobenius norm and singular values; they only relabel its axes. Repeated eigenvalues leave rotations within the repeated-eigenvalue subspace unresolved.

The centered population-form factor covariance subtracts the outer product of the factor mean:

$$
\Omega_F=\frac{F'F}{T}-\bar f\bar f',
\qquad\bar f=\frac1T\sum_t f_t
$$

Diagonal uncentered second moments therefore do not generally imply zero centered correlations. A rotation based on centered covariance answers a different question. State which object is being diagonalized, and do not remove mean factor premia merely to make the two objects coincide.

If orthonormal loading columns are required and $\Gamma$ has full column rank, a thin QR factorization supplies one possible normalization:

$$
\Gamma=UR,\qquad U'U=I
$$

Compensating factors preserve the same fitted returns:

$$
\Gamma^*=U,\qquad F^*=FR'
$$

This changes scale and is not interchangeable with an orthogonal eigenvector rotation when scale-sensitive quantities are prescribed. Any subsequent sign choice must flip both the factor and its matching loading column. A zero factor mean cannot determine that sign.

### A fully stated normalization versus an axis rotation

When the chosen convention explicitly requires both orthonormal loading columns and a diagonal uncentered factor second moment, the two operations can be combined. For full-rank $\Gamma=UR$, form $F_1=FR'$ and eigendecompose its uncentered moment as $F_1'F_1/T=Q\Lambda Q'$. Then:

$$
\Gamma_*=UQ,\qquad F_*=F_1Q,\qquad
\Gamma_*'\Gamma_*=I,\qquad F_*'F_*/T=\Lambda
$$

The product $F_*\Gamma_*'$ remains $F\Gamma'$. This is one explicit scale-and-axis normalization; a task requesting only an orthogonal rotation has not necessarily requested the preceding QR scale change. Eigenvalue ordering, repeated-eigenvalue subspaces and zero means can leave additional labeling choices. Centered correlations must still be calculated from centered covariance; diagonal uncentered moments alone cannot guarantee zero centered correlation when more than one factor has nonzero mean.

## 4. Fit and factor-return interpretation

Let $\hat r_{i,t}$ denote the fitted return. An uncentered total $R$-squared compares residual squares with squared raw excess returns over the same eligible observations:

$$
R^2_{\mathrm{total}}
=1-\frac{\sum_{i,t}(r_{i,t}-\hat r_{i,t})^2}{\sum_{i,t}r_{i,t}^2}
$$

For a centered cross-sectional $R$-squared, let $I_t$ be the eligible assets at date $t$ and let $\bar r_t$ be their mean return. the denominator removes that date's cross-sectional mean:

$$
R^2_{\mathrm{CS},t}
=1-\frac{\sum_{i\in I_t}(r_{i,t}-\hat r_{i,t})^2}
{\sum_{i\in I_t}(r_{i,t}-\bar r_t)^2}
$$

A time average of these ratios differs from pooling their numerators and denominators. An uncentered cross-sectional convention is also possible; follow the definition rather than infer it from the word $R$-squared. Zero denominator cases require a declared rule, not an arbitrary perfect-fit value.

With full-rank exposures, the least-squares factor estimate is also a linear combination of that date's returns. Its coefficient matrix is:

$$
A_t=(B_t'B_t)^{-1}B_t'
$$

These portfolios reproduce unit exposures to the modeled factors:

$$
A_tB_t=I
$$

They may use shorts and need not have unit net investment. In-sample latent factors are not automatically out-of-sample investable strategies: the characteristic map must also be known at the trading date.

For a stationary factor series under the usual uncorrelated-return annualization assumption, its annualized excess-return Sharpe ratio is:

$$
\mathrm{SR}_{k,\mathrm{annual}}
=\sqrt{A}\frac{\bar f_k}{s_k}
$$

Here $A$ is observations per year and $s_k$ uses the specified standard-deviation divisor. Serial correlation or zero standard deviation invalidates an automatic application of this expression.

## 5. Pricing-alpha diagnostics

A time-series pricing regression with fixed asset coefficients is a separate diagnostic from the conditional-loading estimation model:

$$
r_{i,t}=\alpha_i+\beta_i'f_t+u_{i,t}
$$

Its intercept is not generally the simple average of the IPCA residuals because the characteristic-driven exposures vary through time.

For $N$ assets and $K$ factors on a common sample, let $U$ have regression residuals $u_t'$ as rows and let $\hat\alpha$ collect the $N$ estimated intercepts. Define the residual covariance and centered factor covariance using divisor $T$:

$$
\Sigma_u=\frac{U'U}{T},\qquad
\Omega=\frac{(F-\mathbf1\bar f')'(F-\mathbf1\bar f')}{T}
$$

The corresponding classical GRS statistic is:

$$
\mathrm{GRS}
=\frac{T-N-K}{N}
\frac{\hat\alpha'\Sigma_u^{-1}\hat\alpha}
{1+\bar f'\Omega^{-1}\bar f}
$$

Its conventional $F$ reference has degrees of freedom $N$ and $T-N-K$ under the classical full-rank, iid Gaussian regression-error and factor-exogeneity assumptions. In particular, $T$ must exceed $N+K$ and both covariance inverses must exist. Different divisor conventions require corresponding prefactor changes. With covariances divided by T, the prefactor is $(T-N-K)/N$. With the residual covariance divided by $T-K-1$, it is $(T/N)(T-N-K)/(T-K-1)$. Mixing the two inflates the statistic by $T/(T-K-1)$. The model's own fit statistics (R² of every kind, fitted returns) is measured on its fitted values $z'\Gamma f$. Per-asset time-series regressions on the estimated factors have free intercepts and betas and serve only the alpha diagnostics.

Factors estimated from the same returns need not satisfy the assumptions of the classical exact test. Computing the conventional statistic does not establish its exact finite-sample p-value validity after factor estimation. A common sample and consistent intercept definition remain essential.

## 6. Checks and limits

- Dimensions and missingness define the regression population; do not shift rows by position when dates differ.
- Conditional block updates must not worsen the same least-squares objective, within numerical error.
- General rotation/scale transformations preserve predictions only with a compensating loading/factor transformation.
- Distinguish centered covariance from uncentered moments and positive scale from sign orientation.
- A fitted factor model does not establish a causal interpretation of the characteristics, and a static-alpha test is not a test that all dynamic loadings are zero.

## 7. Sources and derivation scope

Kelly, Pruitt and Su (2019), [Instrumented Principal Component Analysis, author working paper dated December 8, 2019](https://www.cireqmontreal.com/wp-content/uploads/2019/12/pruitt.pdf), Sections 1 and 3.2: the characteristic-loading model, least-squares estimation and alternating block regressions. This working paper is distinct from their 2019 JFE article, *Characteristics Are Covariances: A Unified Model of Risk and Return*, [DOI](https://doi.org/10.1016/j.jfineco.2019.05.001).

The vectorization, transformation, covariance and diagnostic identities here are direct algebra under the stated definitions; they do not claim a uniquely prescribed normalization. The GRS expression is the conventional regression statistic of Gibbons, Ross and Shanken (1989), [A Test of the Efficiency of a Given Portfolio](https://www2.itc.kansai-u.ac.jp/~koji_ota/GRS_test/GibbonsRossShanken_1989_Econometrica.pdf), Sections 2 and 7, with maximum-likelihood-form covariance divisors as explicitly defined above; it is not a new exact-test result for estimated IPCA factors.
