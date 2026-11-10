# PCA risk factors, exposures and neutralization

Use this reference for linear principal components of returns or curve changes, and for hedging exposures to a selected component subspace. Ordinary PCA does not estimate characteristic-dependent loadings in an instrumented latent-factor model.

## Meaning of the input

Let Y have T time observations and n assets or maturities. Decide whether entries represent levels, changes or returns. Covariance PCA centers columns; correlation PCA also divides each by its standard deviation. Those are different risk questions. Match the task's units, covariance divisor and sign convention; none is determined by the word PCA alone.

For an inference or investment exercise, the estimation sample determines the mean and axes; full-sample axes applied to earlier dates do not constitute a causal out-of-sample strategy.

## Covariance principal components

Here mean(Y) denotes the row vector of column means, Z is centered data, d is the selected positive covariance divisor, and $v_{j}$ is a unit column vector. I denotes an identity matrix.

**Centered observations and covariance**

$$
\begin{gathered}
Z = Y - 1\cdot \operatorname{mean}(Y) \\
C = Z'\cdot Z/d
\end{gathered}
$$

**Ordered component axes**

$$
\begin{gathered}
C\cdot v_{j} = \lambda _{j}\cdot v_{j} \\
\lambda _{1} \ge  \lambda _{2} \ge  \ldots  \ge  0 \\
v_{i}'\cdot v_{j} = \operatorname{indicator}(i=j)
\end{gathered}
$$

For singular values $s_{j}$ of Z, the covariance eigenvalues equal $s_{j}$ squared divided by d. PCA of the original centered observations and this covariance eigendecomposition describe the same axes. Feeding C as if it were an observation matrix to a routine that centers its input describes a different problem.

**Scores and explained variance fractions**

$$
\begin{gathered}
f_{j} = Z\cdot v_{j} \\
\mathrm{variance}_{\mathrm{fraction},j} = \lambda _{j}/\sum _{l} \lambda _{l}
\end{gathered}
$$

The denominator includes every covariance eigenvalue, not only the retained ones. If total variance is zero, these fractions are undefined. “Loadings” may mean unit axes or axes multiplied by square roots of eigenvalues; identify the convention before calculating exposure.

## Sign, scaling and identification

An eigenvector may change sign if its score changes sign with it. Repeated eigenvalues identify a subspace rather than unique individual axes. A sign convention is applied per component: flip component k (and its scores) exactly when its own reference quantity, for example the sum of its loadings or its exposure at a stated maturity, is negative. Never flip all components together. Explained-variance shares are unchanged by any flip. A sign convention cannot make a mixed-sign vector have only positive entries; level, slope and curvature interpretations are empirical descriptions.

If all input values are multiplied by a constant a, covariance eigenvalues scale by a squared. Fractions and the eigenspaces are unchanged. Standardizing columns separately generally changes those spaces. Whitening rescales scores to unit variance and therefore changes what a coefficient on a score means.

## Portfolio exposure

Let V contain k retained unit axes as columns and w be n portfolio weights. Assume returns are measured consistently across assets.

**Retained-factor reconstruction**

$$
Z_{\mathrm{retained}} = (Z\cdot V)\cdot V'
$$

**Portfolio coefficients on the retained scores**

$$
\begin{gathered}
b_{\mathrm{portfolio}} = V'\cdot w \\
Z_{\mathrm{retained}}\cdot w = (Z\cdot V)\cdot b_{\mathrm{portfolio}}
\end{gathered}
$$

The portfolio's mean return comes from mean(Y)*w, not from the centered scores alone. Zero exposure to retained axes leaves unmodeled covariance risk and does not guarantee a lower realized variance or a higher Sharpe ratio after additional constraints.

## Minimum-size hedge with linear constraints

Use this block when a hedge h must neutralize specified exposures while preserving selected linear quantities. Write $A\cdot h=b$ for those constraints. For example, a row of ones with right-hand side zero preserves the sum of portfolio weights. A superscript + denotes the Moore–Penrose pseudoinverse.

**Minimum Euclidean-norm feasible hedge**

$$
h = A^{+}\cdot b
$$

This gives an exact constrained hedge only if b lies in the column space of A. Otherwise it is a minimum-norm least-squares residual solution, not a neutral portfolio. For independent rows the same feasible solution is A'*(A*A')^(-1)*b. Position limits, trading costs and a covariance-weighted objective define different optimization problems.

**Exposure and budget residual check**

$$
\mathrm{constraint}_{\mathrm{residual}} = A\cdot h-b
$$

Check the actual residual and numerical rank. Dependent constraints may be consistent or inconsistent; counting equations alone does not decide feasibility. Replacing V by V*Q for orthogonal Q, and transforming exposures consistently, preserves the hedge against that subspace.

## Neutrality after scaling, clipping and turnover control

Let $B$ be the current asset-by-exposure matrix, possibly including a column of ones. For common asset ordering, the orthogonal projection onto its neutral subspace is:

$$
P=I-B(B'B)^+B',\qquad B'Pw=0.
$$

The pseudoinverse handles dependent exposure columns; numerical rank still matters. Any common scalar multiple of a neutral vector stays neutral. Thus dividing a nonzero neutral vector by its gross exposure preserves linear neutrality, but can violate position limits or a turnover cap. If gross exposure is zero, that normalization is undefined.

For old holdings $w_{\mathrm{old}}$ and a neutral target $w_{\mathrm{target}}$, consider a turnover-controlled blend with $0\le a\le1$:

$$
w(a)=(1-a)w_{\mathrm{old}}+a w_{\mathrm{target}},\qquad
B'w(a)=(1-a)B'w_{\mathrm{old}}.
$$

The blend stays neutral only if the right side is zero. In particular, a portfolio neutral to an earlier exposure matrix need not be neutral to today's $B$. Align old and new positions on one declared universe; an omitted exiting position is not zero turnover.

For the one-way convention, the blend's turnover from the old allocation is:

$$
\frac12\lVert w(a)-w_{\mathrm{old}}\rVert_1
=a\,\frac12\lVert w_{\mathrm{target}}-w_{\mathrm{old}}\rVert_1.
$$

This identity precedes any further projection, clipping or gross normalization. Those subsequent transformations can change turnover again. Componentwise clipping generally destroys linear neutrality; repeated projection and clipping is not automatically the solution of a constrained allocation problem. A prescribed sequence of transformations defines its own portfolio and should not be replaced by an extra normalization intended to improve one diagnostic. These are algebraic properties, not a guarantee of lower realized risk.

## Yield interpretation

PCA of yield changes measures co-movement, not a term-premium decomposition. Par rates generally are not zero rates. If a stated approximation treats them as zero yields z(t) with continuous compounding, the finite-interval forward is an average over the interval, not an instantaneous forward.

**Continuously compounded forward over an interval**

$$
f_{a,b} = (b\cdot z(b)-a\cdot z(a))/(b-a)
$$

Both endpoints use a common time unit, and rates retain their input scale. The instantaneous rate is the derivative of t*z(t), obtained only as the interval shrinks under differentiability.

## Sources

[Scikit-learn PCA documentation](https://scikit-learn.org/stable/modules/decomposition.html#pca), for centering, scaling and SVD semantics. Jolliffe and Cadima (2016), [Principal component analysis: a review and recent developments](https://doi.org/10.1098/rsta.2015.0202), for PCA terminology and covariance/SVD equivalence. Portfolio exposure, unit transformation and constrained-hedge formulas above are direct linear-algebra derivations; they do not assert an empirical performance improvement.
