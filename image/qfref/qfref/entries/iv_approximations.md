# Implied Volatility: Named Approximations and Black–Scholes Inversion

Map task quantities to these definitions by meaning and units, not by letter, before the first calculation; recheck when inputs or conventions change.

Use this reference when recovering Black–Scholes or Black-76 volatility from a European option price, comparing named explicit estimators, or checking an implied-volatility solver. It provides price normalization, forward-ATM formulas, the Li quadratic and combined approximations, separate Corrado–Miller and Hallerbach estimators, and numerical inversion checks. It does not price American exercise, identify a local-volatility surface, or supply Minqiang Li's rational approximation. Match the requested formula variant before calculating; a numerical inverse is not a replacement for a named approximation.

## Contents

1. [Inputs and normalization](#1-inputs-and-normalization)
2. [Select the calculation](#2-select-the-calculation)
3. [Forward-ATM calculations](#3-forward-atm-calculations)
4. [Li quadratic and combined approximations](#4-li-quadratic-and-combined-approximations)
5. [Corrado–Miller and Hallerbach](#5-corradomiller-and-hallerbach)
6. [Numerical inversion](#6-numerical-inversion)
7. [Numerical checks](#7-numerical-checks)
8. [References](#8-references)

## 1. Inputs and normalization

Use positive spot S, strike K and expiry T. T is in years; r and q are continuously compounded rates in decimals; $\sigma$ is annualized volatility in decimals. C and P are prices per unit of underlying, not position totals. $\Phi$ and $\phi$ denote the standard normal CDF and density; $\Phi _{\mathrm{inv}}$ denotes the inverse CDF.

For constant rates and a continuous yield:

**Discounted stock and strike inputs**

$$
\begin{gathered}
A = S\cdot \exp (-q\cdot T) \\
B = K\cdot \exp (-r\cdot T)
\end{gathered}
$$

**Normalize volatility, strike and option price**

$$
\begin{gathered}
x = \sigma \cdot \sqrt{T} \\
\eta  = B/A \\
c = C/A
\end{gathered}
$$

**Black–Scholes pricing thresholds**

$$
\begin{gathered}
\mathrm{d1} = \log (A/B)/x + x/2 \\
\mathrm{d2} = \mathrm{d1} - x
\end{gathered}
$$

**Black–Scholes call price**

$$
C_{\mathrm{BS}} = A\cdot \Phi (\mathrm{d1}) - B\cdot \Phi (\mathrm{d2})
$$

**Black–Scholes put price**

$$
\operatorname{P}_{\mathrm{BS}} = B\cdot \Phi (-\mathrm{d2}) - A\cdot \Phi (-\mathrm{d1})
$$

**Vega for numerical inversion**

$$
\mathrm{vega} = A\cdot \phi (\mathrm{d1})\cdot \sqrt{T}
$$

A and B are discounted price quantities; x is total volatility, not annualized volatility and not variance. For Black-76 use A = discount*F and B = discount*K with the appropriate forward F. Deterministic discount/carry curves can likewise be represented by A = discount*F. For FX, q is the foreign rate. Subtracting known cash dividends from spot is an additional model approximation, not an exact treatment of discrete stock-price jumps.

Forward ATM means $A = B$. Spot ATM means $S = K$; these differ when carry is nonzero. If a task explicitly requests evaluation on a spot-ATM subset, preserve that subset but do not call the forward-ATM derivation exact there.

**Convert a put price into its parity-equivalent call price**

$$
C = \operatorname{P} + A - B
$$

For numerical inversion near intrinsic value, directly price the out-of-the-money option when possible; subtraction of large terms can destroy its small time value. Conversion does not change the volatility, but changing a named approximation's normalization or call/put convention can change its approximation error.

## 2. Select the calculation

| Requested calculation | Use | Required distinction |
|---|---|---|
| Accurate inverse at arbitrary moneyness | Section 6 | Numerical root, not an explicit estimator |
| Forward-ATM quick estimate | Brenner–Subrahmanyam in Section 3 | First-order approximation |
| Forward-ATM cubic/trigonometric estimate | Li ATM in Section 3 | Small root of a cubic approximation |
| Li non-ATM estimate (all moneyness) | Section 4, Li non-ATM estimator block | Use that block's formula and radicand rule |
| Li (2003) quadratic, equation (13) | Section 4, quadratic block | Not the Corrado–Miller discriminant |
| Li combined estimate | Section 4, switching block | Select by $\rho$; do not use the quadratic everywhere |
| Corrado–Miller–Hallerbach estimate | Section 5, Corrado–Miller–Hallerbach estimator block | Use that block's formula for this label |
| Corrado–Miller adjusted estimator | Section 5, CM | Not Hallerbach's tweaked estimator |
| Hallerbach estimator | Section 5, raw or tweaked as specified | Name the chosen variant |

An explicit task formula takes precedence over a generic reference. A compound author label without a formula needs its published variant identified; author names alone do not define an estimator. Li's quadratic branch and his combined approximation are distinct requests.

## 3. Forward-ATM calculations

Use this block when $A = B$ and the relevant ATM method is requested. When a task applies an ATM method at spot $\mathrm{ATM} (K = S)$, keep the same normalization $c = C/A$ for Brenner–Subrahmanyam and Li ATM: divide by the dividend-discounted underlying A, never by the undiscounted spot. An exact identity provides a separate check:

**Exact forward-ATM volatility inversion**

$$
\begin{gathered}
c = 2\cdot \Phi (x/2) - 1 \\
x_{\mathrm{exact}} = 2\cdot \Phi _{\mathrm{inv}}((1+c)/2) \\
\sigma _{\mathrm{exact}} = x_{\mathrm{exact}}/\sqrt{T}
\end{gathered}
$$

This holds for $0 \le  c < 1$. At $c = 1$ only the infinite-volatility limit exists. For very small c or c near 1, use numerically stable inverse-distribution routines.

Brenner–Subrahmanyam uses the first-order normal expansion:

**Brenner–Subrahmanyam first-order ATM approximation**

The normalizing underlying is dividend-discounted, not the undiscounted spot $S$:

$$
A = S\cdot \exp (-q\cdot T)
$$

$$
c = C/A
$$

$$
\alpha  = \sqrt{2\cdot \pi}\cdot c
$$

$$
x_{\mathrm{BS},\mathrm{approx}} = \alpha
$$

$$
\sigma _{\mathrm{BS},\mathrm{approx}} = \alpha /\sqrt{T}
$$

Li's ATM cubic keeps the next nonzero term. Select the root continuously approaching zero as $\alpha$ approaches zero:

**Li ATM cubic and its selected small-root solution**

$$
\begin{gathered}
x - x^{3}/24 = \alpha \\
u = 3\cdot \alpha /\sqrt{32} \\
z = \cos (\arccos (u)/3) \\
x_{\mathrm{Li},\mathrm{ATM}} = 2\cdot \sqrt{2}\cdot z - \sqrt{8\cdot z^{2} - 6\cdot \alpha /(\sqrt{2}\cdot z)} \\
\sigma _{\mathrm{Li},\mathrm{ATM}} = x_{\mathrm{Li},\mathrm{ATM}}/\sqrt{T}
\end{gathered}
$$

Its nonnegative small-root branch requires $0 \le  \alpha  \le  4\cdot \sqrt{2}/3$. The upper endpoint is a repeated root and is poorly conditioned. An algebraically equivalent, less cancellation-prone form is:

**Equivalent sine form of the Li ATM root**

$$
x_{\mathrm{Li},\mathrm{ATM}} = 4\cdot \sqrt{2}\cdot \sin (\arcsin (u)/3)
$$

Preserve the trigonometric form if explicitly prescribed. Check the inverse-trigonometric argument before evaluation; outside its real domain report the approximation as unavailable, not as a zero volatility. This is exact for the displayed cubic, not for Black–Scholes. It is distinct from the inverse-normal identity above.

## 4. Li quadratic and combined approximations

The blocks below give the quadratic in Steven Li (2003), equations (13)–(15). It is one branch, not the full combined estimator. Li (2003) uses S for the non-dividend-paying stock and K for the discounted strike; in this entry these correspond to A and B. Thus discounted stock and strike quantities sometimes written $\tilde{S}$ and $\tilde{K}$ mean A and B, respectively; $\eta$ is always B/A. The quadratic expansion is intended for total volatility small relative to $\sqrt{\mathrm{abs}( \eta -1)}$; it is not uniformly accurate across moneyness.

**Li (2003) quadratic coefficients, root and annualization**

$$
\begin{gathered}
\tilde{\alpha} = \sqrt{2\cdot \pi}\cdot (2\cdot c + \eta  - 1)/(1+\eta ) \\
b_{\mathrm{Li}} = (\eta -1)^{2}/(1+\eta ) \\
\mathrm{disc}_{\mathrm{Li}} = \tilde{\alpha}^{2} - 4\cdot b_{\mathrm{Li}} \\
x_{\mathrm{Li},\mathrm{quadratic}} = (\tilde{\alpha} + \sqrt{\mathrm{disc}_{\mathrm{Li}}})/2 \\
\sigma _{\mathrm{Li},\mathrm{quadratic}} = x_{\mathrm{Li},\mathrm{quadratic}}/\sqrt{T}
\end{gathered}
$$

At $\eta  = 1$ it reduces to Brenner–Subrahmanyam, not Li ATM. Require a nonnegative discriminant; a material negative value is outside this approximation's real domain. This failure of the approximation does not imply that the observed price has no Black–Scholes implied volatility. A real result still need not be accurate. Do not replace a failed value with Corrado–Miller or Newton under the Li label.

### Equivalent price-unit form: Li (2003), equation (15)

Use this equivalent form of the same quadratic when working directly with A, B and C instead of $\eta$ and c. A and B retain the discounted-input definitions in Section $1; T > 0$ is in years.

**Call price minus half the discounted stock–strike difference**

$$
a_{\mathrm{Li}} = C - (A-B)/2
$$

**Radicand in the price-unit form of Li (2003), equation (15)**

$$
\mathrm{rad}_{\mathrm{Li}} = a_{\mathrm{Li}}^{2} - (A-B)^{2}\cdot (1+B/A)/(2\cdot \pi )
$$

**Annualized volatility from Li (2003), equation (15), in this entry's notation**

$$
\sigma _{\mathrm{Li},\mathrm{eq15}} = \sqrt{2\cdot \pi}/((A+B)\cdot \sqrt{T}) \cdot  (a_{\mathrm{Li}} + \sqrt{\mathrm{rad}_{\mathrm{Li}}})
$$

The factor $1/\sqrt{T}$ annualizes the result exactly once; the ratio B/A is discounted strike divided by discounted stock. Apply the same nonnegative-radicand condition as above. This is algebraically identical to $\sigma _{\mathrm{Li},\mathrm{quadratic}}$, not a different approximation. Corrado–Miller in Section 5 instead subtracts $(A-B)^2/\pi$ inside its radicand; the two formulas must not be interchanged. The Li quadratic also equals Hallerbach raw ($\gamma  = 2$) in Section 5, but not Hallerbach tweaked.

**Li non-ATM estimator (all moneyness)**

Use this block for an output labelled Li non-ATM, applied across all moneyness. References: Li (2003); Chin, Olafsson and Nel, *Problems and Solutions in Mathematical Finance*, Volume II, section 7.2.1.

$$
a_{\mathrm{Li}} = C - (A-B)/2
$$

$$
\mathrm{rad}_{\mathrm{Li},\mathrm{nonatm}} = a_{\mathrm{Li}}^{2} - (A-B)^{2}\cdot (1+A/B)/(2\cdot \pi )
$$

If $-\mathrm{tol} \le  \mathrm{rad}_{\mathrm{Li},\mathrm{nonatm}} < 0$, set $\mathrm{rad}_{\mathrm{Li},\mathrm{nonatm}} = 0$.
If $\mathrm{rad}_{\mathrm{Li},\mathrm{nonatm}} < -\mathrm{tol}$, $\sigma _{\mathrm{Li},\mathrm{nonatm}} = \mathrm{NaN}$. Otherwise:

$$
\sigma _{\mathrm{Li},\mathrm{nonatm}} = \sqrt{2\cdot \pi}/((A+B)\cdot \sqrt{T}) \cdot  (a_{\mathrm{Li}} + \sqrt{\mathrm{rad}_{\mathrm{Li},\mathrm{nonatm}}})
$$

tol is the task's stated round-off tolerance. Do not clip every negative radicand to zero: the NaN points are excluded from error statistics such as RMSE.

### Li (2003): original branch diagnostic

The working paper's equation (17) gives a rough numerical diagnostic for choosing between its quadratic (13) and near-ATM cubic (16). For $\eta  \ne  1$:

**Li (2003) total-volatility-to-moneyness diagnostic**

$$
\rho _{2003} = x/\sqrt{\mathrm{abs}(\eta -1)}
$$

Use the quadratic when $\rho _{2003} < 2$ and the near-ATM cubic otherwise. Here x is the unknown total volatility: the paper suggests estimating it approximately with either formula before checking the diagnostic. This is not a directly observable statistic or a uniquely specified fixed-point algorithm. State the provisional estimator when implementing this version. At $\eta  = 1$ use the ATM cubic directly. The near-ATM cubic is the Section 3 root with $\alpha$ replaced by $\tilde{\alpha}$, including its real-domain checks.

### Later combined approximation: select the branch first

Use this block for the later combined rule attributed to Li (2005) (Orlando and Taglialatela, 2017), rather than the standalone quadratic or the 2003 diagnostic. Unlike $\rho _{2003}$, its statistic depends only on observed prices and moneyness. Use the same call normalization throughout. For a strictly positive call price, define:

**Li combined-method branch statistic and normalized coefficient**

$$
\begin{gathered}
\rho  = \mathrm{abs}(\eta -1)/(c^{2}) \\
\tilde{\alpha} = \sqrt{2\cdot \pi}\cdot (2\cdot c + \eta  - 1)/(1+\eta )
\end{gathered}
$$

When $\rho  \le  1.4$, use the near-ATM cubic branch:

**Near-ATM cubic branch of the combined method**

$$
\begin{gathered}
u_{\mathrm{combined}} = 3\cdot \tilde{\alpha}/\sqrt{32} \\
x_{\mathrm{combined}} = 4\cdot \sqrt{2}\cdot \sin (\arcsin (u_{\mathrm{combined}})/3)
\end{gathered}
$$

Require $0 \le  u_{\mathrm{combined}} \le  1$. Equivalently use the cosine-and-radical expression in Section 3 with $\alpha$ replaced by $\tilde{\alpha}$. When $\rho  > 1.4$, use $x_{\mathrm{Li},\mathrm{quadratic}}$ from the preceding block, including its discriminant check. In either branch:

**Annualize the selected combined-method total volatility**

$$
\sigma _{\mathrm{combined}} = x_{\mathrm{combined}}/\sqrt{T}
$$

For the quadratic branch, $x_{\mathrm{combined}}$ means $x_{\mathrm{Li},\mathrm{quadratic}}$. The threshold chooses an approximation, not an exact inverse; a discontinuity at the switch is possible. At $\eta  = 1$ and $c > 0$ this combined method reduces to Li ATM. At $c = 0, \rho$ is undefined: handle the price boundary as in Section 6 and do not evaluate the ratio. An unavailable selected branch is not permission to silently switch methods. The divisor in $u_{\mathrm{combined}}$ is $\sqrt{32}$, not 32; the cubic residual below checks this transcription.

## 5. Corrado–Miller and Hallerbach

Use the named variant requested; the coefficients differ. These formulas share the same A, B, C and T normalization.

**Corrado–Miller adjusted quadratic approximation**

$$
\begin{gathered}
a_{\mathrm{CM}} = C - (A-B)/2 \\
\mathrm{rad}_{\mathrm{CM}} = a_{\mathrm{CM}}^{2} - (A-B)^{2}/\pi \\
x_{\mathrm{CM}} = \sqrt{2\cdot \pi}/(A+B)\cdot (a_{\mathrm{CM}} + \sqrt{\mathrm{rad}_{\mathrm{CM}}}) \\
\sigma _{\mathrm{CM}} = x_{\mathrm{CM}}/\sqrt{T}
\end{gathered}
$$

Hallerbach's raw estimator, equation (20), and tweaked estimator, equation (24), can be written in one parameterization:

**Select the raw or tweaked Hallerbach coefficient**

$$
\begin{gathered}
\gamma _{\mathrm{raw}} = 2 \\
\gamma _{\mathrm{tweaked}} = 1.85\cdot \sqrt{A/B}
\end{gathered}
$$

**Hallerbach approximation with the selected coefficient**

$$
\begin{gathered}
L = 2\cdot C + B - A \\
\mathrm{rad}_{H} = L^{2} - \gamma \cdot (A+B)\cdot (B-A)^{2}/(\pi \cdot A) \\
x_{H} = \sqrt{2\cdot \pi}/(2\cdot (A+B))\cdot (L + \sqrt{\mathrm{rad}_{H}}) \\
\sigma _{H} = x_{H}/\sqrt{T}
\end{gathered}
$$

Choose $\gamma$ before evaluation. Corrado–Miller and the two Hallerbach variants reduce to Brenner–Subrahmanyam at $A=B$. Algebraically, Hallerbach raw equals the quadratic in Section 4; Hallerbach tweaked generally does not. This equality does not make Corrado–Miller, Hallerbach tweaked, and Li's combined estimator interchangeable.

**Corrado–Miller–Hallerbach estimator**

Use this block for an output labelled Corrado–Miller–Hallerbach. References: Corrado and Miller (1996); Hallerbach (2004); Chin, Olafsson and Nel, *Problems and Solutions in Mathematical Finance*, Volume II, section 7.2.1. It is a different estimator from the Corrado–Miller formula in this section: implement it as written, even where its errors exceed Corrado–Miller's, and do not replace it with that formula.

```text
m = A / B
alpha = sqrt(2*pi) / (m + 1) * (2*C/B - (m - 1))
beta = 0.5 * ((m - 1) / (m + 1))**2
sigma_cmh = (alpha + sqrt(alpha**2 - 8*beta)) / sqrt(T)      # handle a negative discriminant as the task states
```

$$
\begin{gathered}
m = A/B \\
\alpha _{\mathrm{CMH}} = \sqrt{2\cdot \pi}/(m+1)\cdot (2\cdot C/B - (m-1)) \\
\beta _{\mathrm{CMH}} = 0.5\cdot ((m-1)/(m+1))^{2} \\
\sigma _{\mathrm{CMH}} = (\alpha _{\mathrm{CMH}} + \sqrt{\alpha _{\mathrm{CMH}}^{2} - 8\cdot \beta _{\mathrm{CMH}}})/\sqrt{T}
\end{gathered}
$$

## 6. Numerical inversion

Use when an accurate Black–Scholes inverse is required, or as a separately labelled benchmark. For positive A, B and T:

**Admissible Black–Scholes price range and inverse-volatility cases**

$$
\begin{gathered}
\mathrm{intrinsic}_{\mathrm{call}} = \max (A-B, 0) \\
\mathrm{intrinsic}_{\mathrm{call}} < C < A: \text{unique finite positive} \sigma \\
C = \mathrm{intrinsic}_{\mathrm{call}}: \sigma  = 0 \\
C = A: \text{infinite-volatility limit}, \text{no finite solution} \\
C < \mathrm{intrinsic}_{\mathrm{call}} \;\text{or}\; C > A: \text{no nonnegative Black-Scholes solution}
\end{gathered}
$$

At expiry volatility is not identifiable from the payoff. Do not turn a materially invalid price into a valid one by clipping. Distinguish a price genuinely at intrinsic value from one rounded there.

For plain Newton, honor prescribed starting values, iteration limits and stopping rules:

**Newton residual, update and step size**

$$
\begin{gathered}
\mathrm{residual}_{n} = C_{\mathrm{BS}}(\sigma _{n}) - C_{\mathrm{observed}} \\
\sigma _{\mathrm{next}} = \sigma _{n} - \mathrm{residual}_{n}/\mathrm{vega}(\sigma _{n}) \\
\mathrm{step}_{n} = \sigma _{\mathrm{next}} - \sigma _{n}
\end{gathered}
$$

The generic inflection-point start is $\sqrt{2\cdot \mathrm{abs}(\log (A/B))/T}$; at $A = B$ use a positive ATM estimate. A task-specified start overrides this suggestion. Tiny vega, a nonpositive iterate or a nonfinite step can defeat unsafeguarded Newton. Record failure rather than silently returning a different algorithm's answer.

For a robust inverse when the algorithm is not prescribed, bracket the price monotonically: lo = 0 and increase a finite hi until its price exceeds the target. Use bisection/Brent, or safeguarded Newton accepting only steps inside the updated bracket. Set a bracket-expansion budget and handle numerical saturation. A hybrid is not plain Newton.

Check residual at the final returned iterate. A small step alone may reflect stagnation. Record the actual stopping reason, iterations, last step and price residual. In a vectorized solver keep a per-contract convergence state; an early unconverged step must not permanently mark a later converged contract as failed. Small vega also makes volatility sensitive to rounding even when the price residual is small.

## 7. Numerical checks

Evaluate domains before radicals and inverse trigonometric functions. Follow an explicit task rounding tolerance; otherwise clamp only demonstrable floating-point roundoff, scaled to the radicand's terms. Never take an absolute value to make a negative discriminant positive. Classify before clipping: a radicand below the negative tolerance makes the estimate unavailable, and only one between that tolerance and zero is set to zero; clipping every negative value first removes the unavailable case. An unavailable approximation is distinct from a finite estimate.

Verify annualization exactly once. Scaling A, B and C by the same positive factor must leave every reported volatility unchanged. At forward ATM compare the explicit estimators with the inverse-normal result. For the quadratic in Section 4, check its defining polynomial:

**Polynomial residual for the Li quadratic root**

$$
x_{\mathrm{Li},\mathrm{quadratic}}^{2} - \tilde{\alpha}\cdot x_{\mathrm{Li},\mathrm{quadratic}} + b_{\mathrm{Li}} = 0
$$

For the combined near-ATM branch, the independent algebraic check is:

**Polynomial residual for the combined cubic root**

$$
x_{\mathrm{combined}} - x_{\mathrm{combined}}^{3}/24 - \tilde{\alpha} = 0
$$

Polynomial residual checks transcription and root selection, not approximation accuracy. Reprice each finite estimate through Black–Scholes and compare separately with numerical inversion. Do not force approximation errors to zero or claim one estimator is always best. An all-unavailable set is not zero error. Compare method identity, numerical error and solver convergence separately.

## 8. References

Brenner, M., and Subrahmanyam, M. G. (1988). A simple formula to compute the implied standard deviation. *Financial Analysts Journal*, 44(5), 80–83.

Corrado, C. J., and Miller, T. W. (1996). A note on a simple, accurate formula to compute implied standard deviations. *Journal of Banking & Finance*, 20(3), 595–603.

Hallerbach, W. G. (2004). An improved estimator for Black-Scholes-Merton implied volatility. ERIM Report Series ERS-2004-054-F&A, Erasmus University Rotterdam.

Li, S. (2003). The estimation of implied volatility from the Black-Scholes model: some new formulas and their applications. Discussion Paper No. 141, School of Economics and Finance, Queensland University of Technology.

Li, S. (2005). A new formula for computing implied volatility. *Applied Mathematics and Computation*, 170(1), 611–625.

Orlando, G., and Taglialatela, G. (2017). A review on implied volatility calculation. *Journal of Computational and Applied Mathematics*, 320, 202–220.

Płuciennik, P. (2007). A modified Corrado-Miller implied volatility estimator. *Fasciculi Mathematici*, 38.
