# Sampling bivariate copulas (Gaussian, Student-t, Clayton, Gumbel, Frank) and their Kendall's tau / Spearman's rho

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting
- Output: pairs (U, V) with uniform(0, 1) margins and copula C. Data with margins F, G: $X = F^{-1}(U)$, $Y = G^{-1}(V)$.
- Notation: Z1, Z2 i.i.d. N(0, 1); E1, E2 i.i.d. Exp(1) (mean 1); W uniform(0, 1); all independent; one fresh set per pair.
  $\Phi$ = standard normal CDF; $t_{\nu}$ = Student-t CDF with $\nu$ df.
- Parameter domains as in the fitting entry: $\rho$ in (-1, 1), $\nu$ > 0, Clayton $\theta  > 0$, Gumbel $\theta  \ge  1$, Frank $\theta  \ne  0$.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $\rho$ | Gaussian / t copula correlation parameter | none |
| $\nu$ | t copula degrees of freedom | none |
| $\theta$ | Clayton / Gumbel / Frank parameter | none |
| $n$ | number of simulated pairs | count |

## Samplers
- Gaussian: $Y = \rho  \mathrm{Z1} + \sqrt{1 - \rho ^{2}} \mathrm{Z2}$; $U = \Phi (\mathrm{Z1})$, $V = \Phi (Y)$ (Cholesky of [[1, $\rho$], [$\rho$, 1]]).
- Student-t: Z1, Y as above and ONE $Q \sim \chi^2(\nu)$ per pair: $U = t_{\nu}(\mathrm{Z1} / \sqrt{Q/\nu})$, $V = t_{\nu}(Y / \sqrt{Q/\nu})$.
  A separate $\chi$-square per margin is a different copula (at $\rho  = 0$ it is independence, no tail dependence).
- Archimedean via Marshall-Olkin (frailty): $C(u, v) = \psi (\psi ^{-1}(u) + \psi ^{-1}(v))$ with $\psi$ the Laplace transform of a positive frailty M.
  Draw M, then $U = \psi (\mathrm{E1} / M)$, $V = \psi (\mathrm{E2} / M)$ (same M for both coordinates).
  - Clayton ($\theta  > 0$): $\psi (s) = (1 + s)^{-1/\theta}$, $M \sim \Gamma (\mathrm{shape} = 1/\theta , \mathrm{scale} = 1)$ (mean $1/\theta$, NOT shape $\theta$):

$$
`U = (1 + \mathrm{E1}/M)^{-1/\theta}`.
$$

  - Gumbel ($\theta  \ge  1$): $\psi (s) = \exp (-s^{1/\theta})$, M positive stable with $\alpha  = 1/\theta$, $\operatorname{E}[\exp (-s M)] = \exp (-s^{\alpha})$.
Kanter / Chambers–Mallows–Stuck:

$$
\Theta  \sim \mathrm{uniform}(0, \pi )
$$

$$
E \sim \mathrm{Exp}(1)
$$

$$
M = [\sin (\alpha  \Theta ) / \sin (\Theta )^{1/\alpha}] \cdot  [\sin ((1 - \alpha ) \Theta ) / E]^{(1 - \alpha )/\alpha}
$$

In code, with the exponent $1/\alpha$ on $\sin(\Theta)$ (not $\alpha$):

```python
M = (np.sin(alpha * Th) / np.sin(Th) ** (1 / alpha)) * (np.sin((1 - alpha) * Th) / E) ** ((1 - alpha) / alpha)
```

Check the frailty before using it: $\operatorname{E}[\exp(-M)]$ should be close to $\exp(-1) \approx 0.3679$ (the Laplace transform at $s = 1$), and each sampled margin U should have mean about 0.5 and an empirical CDF close to uniform. A wrong exponent fails both (for $\theta = 2$: about 0.48 and a margin mean about 0.40), so a failed check means the sampler is wrong, not that a tail statistic needs a different threshold.

$\theta  = 1$ gives $M = 1$ (independence). In Nolan's $S(\alpha , \beta , \gamma , \delta ; 1)$ notation this is

$$
S(\alpha , 1, (\cos (\pi  \alpha  / 2))^{1/\alpha}, 0; 1)
$$

A generic stable generator must use exactly this scale, not $\gamma  = 1$. Then

$$
U = \exp (-(\mathrm{E1}/M)^{1/\theta})
$$

  - Frank ($\theta  > 0$): $\psi (s) = -(1/\theta ) \ln (1 - (1 - e^{-\theta}) e^{-s})$, M logarithmic-series on {1, 2, ...} with

$$
`p = 1 - e^{-\theta}`, `\operatorname{P}(M = k) = p^{k} / (k \theta )`; `U = \psi (\mathrm{E1} / M)`.
$$

- Conditional inversion (draw $U = \mathrm{W1}$, solve $\mathrm{dC}/\mathrm{d}u (u, v) = \mathrm{W2}$ for v; works for any $\theta$ in the domain):
  - Frank: $V = -(1/\theta ) \ln (1 + \mathrm{W2} (e^{-\theta} - 1) / (\mathrm{W2} + (1 - \mathrm{W2}) e^{-\theta  U}))$. Also the simplest route for $\theta  < 0$
    (or sample Frank(|$\theta$|) and return (U, 1 - V)).
  - Clayton: $V = [U^{-\theta} (\mathrm{W2}^{-\theta /(1+\theta )} - 1) + 1]^{-1/\theta}$.
- Rotations / survival: transform the sample: 90 deg $(1 - U, V)$, 270 deg $(U, 1 - V)$, 180 deg $(1 - U, 1 - V)$ (match the task's convention).

## Theoretical Kendall's tau and Spearman's rho
| family | $\tau$ | $\rho _{S}$ |
|---|---|---|
| Gaussian | $(2/\pi ) \arcsin (\rho )$ | $(6/\pi ) \arcsin (\rho /2)$ |
| Student-t | $(2/\pi ) \arcsin (\rho )$ (does not depend on $\nu$) | no closed form; NOT the Gaussian formula for finite $\nu$ |
| Clayton | $\theta  / (\theta  + 2)$ | no closed form (numerical) |
| Gumbel | $1 - 1/\theta$ | no closed form (numerical) |
| Frank | $1 - (4/\theta )(1 - D_{1}(\theta ))$ | $1 - (12/\theta )(D_{1}(\theta ) - D_{2}(\theta ))$ |

- Debye function $D_{k}(x) = (k / x^{k}) \int _{0}^{x} t^{k} / (e^{t} - 1) \mathrm{d}t$ (integrand -> 1 at $t = 0$ for $k = 1, \to  0$ for $k \ge  2$);
  use the same integral for $x < 0$(or $D_{k}(-x) = D_{k}(x) + k x / (k + 1)$); Frank $\tau$ and $\rho _{S}$ are odd in $\theta$.
- Numerical $\rho _{S}$: $\rho _{S} = 12 \int _{0}^{1} \int _{0}^{1} [C(u, v) - u v] \mathrm{d}u \mathrm{d}v$. For t (or Gaussian) integrate in score space:
  $\rho _{S} = 12 \operatorname{E}[(t_{\nu}(X) - 1/2)(t_{\nu}(Y) - 1/2)]$ under the bivariate t density with correlation $\rho$ and $\nu$ df.
- Numerical $\tau$: $\tau  = 4 \operatorname{E}[C(U, V)] - 1 = 4 \int  \int  C(u, v) c(u, v) \mathrm{d}u \mathrm{d}v - 1$; Archimedean $\tau  = 1 + 4 \int _{0}^{1} \phi (t)/\phi '(t) \mathrm{d}t$, $\phi  = \psi ^{-1}$.
- Sample statistics: Kendall $\tau$ ($\tau_a=\tau_b$ with continuous data), Spearman = Pearson correlation of the ranks.

## Self-checks (do them before using a sampler or density)
- Sampling: margins uniform (KS test); empirical $\tau$ and $\rho _{S}$ within a few standard errors of the table for several parameters
  (std. error about $1/\sqrt{n}$ scale; replicate to estimate it); empirical C(a, b) = share of pairs with $U \le  a, V \le  b$ vs the closed-form C.
- Density: integrates to 1 over the unit square (integrate in normal-score space to tame corner singularities) and equals the
  mixed finite difference $[C(u+h, v+h) - C(u+h, v-h) - C(u-h, v+h) + C(u-h, v-h)] / (4 h^{2})$ of the CDF.
- Frailty: $\operatorname{mean}(\exp(-sM))$ matches $\psi(s)$ for a few s.

## Common mistakes
- Clayton frailty with shape $\theta$ (or scale $\theta$) instead of shape $1/\theta$, scale 1: wrong $\tau$.
- Gumbel frailty from a stable generator with unit scale or $\beta  \ne  1$, or $\alpha  = \theta$ instead of $1/\theta$.
- Drawing a new frailty (or $\chi$-square) per coordinate: destroys the dependence.
- Using $\exp (-\operatorname{E}/M)$ instead of $\psi (\operatorname{E}/M)$, or uniforms instead of Exp(1) without the `-ln W` transform.
- Reporting Pearson correlation of (U, V) as Kendall's $\tau$; using $(6/\pi ) \arcsin (\rho /2)$ for the t copula.
- Frank frailty with $\theta  < 0$(p would exceed 1): use conditional inversion instead.

## Applicability and known limits
- Marshall-Olkin needs a completely monotone generator: valid for Clayton $\theta  > 0$, Gumbel $\theta  \ge  1$, Frank $\theta  > 0$ only.
- Very large $\theta$: Frank frailty M becomes heavy-tailed (mean $p / ((1 - p) \theta )$, about $e^\theta/\theta$) and Gumbel M extreme;
  conditional inversion and log-space evaluation stay stable.
- Pseudo-random results depend on the generator and seed; tasks with a fixed seed usually also fix the sampling order and method.

## Sources
Marshall & Olkin (1988) JASA 83(403):834-841; Hofert (2008) Comput. Statist. Data Anal. 52(12):5163-5174 (frailty table);
Kanter (1975) Ann. Probab. 3(4):697-707; Chambers, Mallows & Stuck (1976) JASA 71(354):340-344; Devroye (2009) ACM TOMACS 19(4) art. 18
(states Kanter's formula); Genest (1987) Biometrika 74:549-555 (Frank $\tau$/$\rho$ via Debye); Nelsen (2006) An Introduction to Copulas, 2nd ed.;
Demarta & McNeil (2005) Int. Statist. Rev. 73(1):111-129; McNeil, Frey & Embrechts (2015) Quantitative Risk Management, rev. ed.
