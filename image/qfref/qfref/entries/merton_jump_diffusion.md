# Merton lognormal jump diffusion

Use this reference for European pricing, simulation and parameter interpretation under Merton lognormal jump diffusion.

Explicit task definitions and contract conventions take precedence. If they conflict or are incomplete, identify the ambiguity and state the convention used.

## Black-Scholes comparison: which volatility

A Black-Scholes price or implied volatility set beside Merton prices needs one volatility, and two are in use:

| Volatility | Meaning | Use when |
|---|---|---|
| diffusion σ alone | the Brownian part only; Black-Scholes with it equals Merton with no jumps (λ = 0) | the comparison isolates what the jumps add |
| total σ_total = sqrt(σ² + λ (μ_J² + σ_J²)) (log-jump mean μ_J, sd σ_J; per year) | matches the total variance of log returns per unit time | the comparison is a flat-volatility benchmark against which the Merton smile or skew is read |

Use the one the task names, compute it once, store it under its own name, and pass that variable to every Black-Scholes call and as the reference level of any implied-volatility comparison; print it next to σ before pricing.

## 1. Shared foundations
Symbols are local. Under a specified pricing measure, use
**Compensated jump-diffusion stock dynamics**

$$
\mathrm{d}S/S_{\mathrm{left}}=(r-q-\lambda \cdot \kappa )\cdot \mathrm{d}t+\sigma \cdot \mathrm{d}W+(J-1)\cdot \mathrm{dN}_{\mathrm{jump}},
$$

where $N_{\mathrm{jump}}$ is a Poisson counting process with intensity $\lambda$. At each jump draw a fresh IID multiplier J with $\ln (J)$ normal of mean $\mu _{J}$ and variance $\delta _{J}^{2}$; jump marks, counting process and Brownian motion are independent. Define $\Phi$ as the standard normal CDF and $\kappa =\exp (\mu _{J}+\delta _{J}^{2}/2)-1$. Require $S>0, K>0, T>0, \lambda \ge 0, \sigma \ge 0$ and $\delta _{J}\ge 0; r$ and q are constant continuous rates. At $T=0$ return the payoff directly. Rates and $\lambda$ are annualized, T in years, $\sigma$ annualized decimal diffusion volatility. J is a price multiplier, not a log-return. The compensator ensures $\operatorname{E}[S_{T}]=S\cdot \exp ((r-q)\cdot T)$.

## 2. European pricing by conditioning
Conditional on $N_{\mathrm{jump}}(T)=n$:
$\log (S_{T})$ is normal with mean $m_{n}=\ln (S)+(r-q-\lambda \cdot \kappa -\sigma ^{2}/2)\cdot T+n\cdot \mu _{J}$,

and variance $v_{n}=\sigma ^{2}\cdot T+n\cdot \delta _{J}^{2}$.

For $v_{n}>0$ set $\mathrm{d2}_{n}=(m_{n}-\ln (K))/\sqrt{v_{n}}, \mathrm{d1}_{n}=\mathrm{d2}_{n}+\sqrt{v_{n}}$.

**Call value conditional on jump count**

$$
C_{n}=\exp (-r\cdot T)\cdot (\exp (m_{n}+v_{n}/2)\cdot \Phi (\mathrm{d1}_{n})-K\cdot \Phi (\mathrm{d2}_{n})).
$$

**Put value conditional on jump count**

$$
\operatorname{P}_{n}=\exp (-r\cdot T)\cdot (K\cdot \Phi (-\mathrm{d2}_{n})-\exp (m_{n}+v_{n}/2)\cdot \Phi (-\mathrm{d1}_{n})).
$$

**Poisson mixture of conditional option values**

$$
C=\sum _{n} p_{n}\cdot C_{n}
$$

$$
\operatorname{P}=\sum _{n} p_{n}\cdot \operatorname{P}_{n}
$$

where

$$
p_{n}=\exp (-\lambda \cdot T)\cdot (\lambda \cdot T)^{n}/n!
$$

At $v_{n}=0$ use the discounted deterministic payoff instead. This representation uses the original Poisson intensity; do not mix its weights with a transformed-intensity formula from another convention.

Choose the truncation from BOTH probability and asset-weighted tails. A call tail is at most $\exp (-r\cdot T)\cdot \sum _{\mathrm{tail}} p_{n}\cdot \exp (m_{n}+v_{n}/2)$; a put tail is at most $\exp (-r\cdot T)\cdot K\cdot \sum _{\mathrm{tail}} p_{n}$. For a sum retaining $n=0,\ldots ,n_{\mathrm{max}}$, these upper bounds (not the actual omitted option prices) equal $S\cdot \exp (-q\cdot T)$ times the Poisson survival probability with $\operatorname{mean} \lambda \cdot T\cdot \exp (\mu _{J}+\delta _{J}^{2}/2)$, and $K\cdot \exp (-r\cdot T)$ times that with mean $\lambda T$, respectively; survival probability means $\Pr[\operatorname{Poisson}(\mathrm{mean})>n_{\mathrm{max}}]$. For large intensities use log weights or stable Poisson functions, not underflowing recursion from $p_{0}$.

## Equivalent transformed-intensity series

Let $m_J=\mathrm{E}[J]=e^{\mu_J+\delta_J^2/2}=1+\kappa$. For nonnegative intensity and fixed positive maturity, define an algebraically tilted intensity and component parameters:

$$
\widetilde\lambda=\lambda m_J,\qquad
\sigma_n^2=\sigma^2+n\delta_J^2/T,\qquad
r_n=r-\lambda\kappa+n\log(m_J)/T
$$

Let $C_{\mathrm{BS}}(S,K,r_n,q,\sigma_n,T)$ be the ordinary dividend-yield Black–Scholes call with the indicated rate. The conditional price from the preceding section and this BS term obey:

$$
C_n=e^{(r_n-r)T}C_{\mathrm{BS}}(S,K,r_n,q,\sigma_n,T)
$$

Multiplying the original Poisson probability by that factor gives a new Poisson probability:

$$
p_ne^{(r_n-r)T}
=e^{-\widetilde\lambda T}\frac{(\widetilde\lambda T)^n}{n!}
$$

Consequently the same call value has the transformed series:

$$
C=\sum_{n=0}^\infty e^{-\widetilde\lambda T}\frac{(\widetilde\lambda T)^n}{n!}
 C_{\mathrm{BS}}(S,K,r_n,q,\sigma_n,T)
$$

Using the original probabilities with these transformed BS rates, but omitting $e^{(r_n-r)T}$, is not the same pricing formula. The tilted intensity is an algebraic device for this series, not a new empirical jump-frequency estimate or an assumption identifying historical and pricing measures. Original-probability conditional prices and tilted-probability BS terms must be paired consistently. At $\lambda=0$ both reduce to Black–Scholes.

## 3. Historical estimation and simulation
Historical and pricing parameters need not agree.
If the physical expected price drift is $b_{\operatorname{P}}$ and jump parameters carry subscript P, an interval dt has log-return mixture means $(b_{\mathrm P}-\lambda_{\mathrm P}\kappa_{\mathrm P}-\sigma_{\mathrm P}^2/2)\mathrm{d}t+n\mu_{\mathrm{JP}}$ and variances $\sigma_{\mathrm P}^2\mathrm{d}t+n\delta_{\mathrm{JP}}^2$. Fit the actual mixture likelihood using log-sum-exp, valid bounds and a controlled tail. If drift is instead defined as the log drift, do not subtract $\sigma^2/2$ again. Identify parameters by definitions. Multiple starts and parameter sensitivity matter: sparse jumps can make calibration weakly identified.

Historical estimation alone does not determine a risk-neutral jump premium. Setting physical jump parameters equal to pricing parameters is an additional assumption, usable when explicitly specified. Simulate an increment by drawing the Poisson count, a diffusion normal, and a jump sum with conditional mean $n\mu_J$ and variance $n\delta_J^2$. Include the compensator once. Terminal simulation suffices only for terminal payoffs; path-dependent contracts need their monitoring schedule.

## 4. Checks and limits
$\lambda =0$ reduces to Black-Scholes; zero jump size reduces to pure diffusion even with nonzero intensity. Call-put parity remains $S\cdot \exp (-q\cdot T)-K\cdot \exp (-r\cdot T)$. Verify the forward moment and compare the mixture with direct payoff integration or independent simulation. Check tails after changing parameters. Implied volatility is a separate inversion of the final option price. A Gaussian approximation to aggregate jumps is not the Poisson mixture model.

## 5. References
Merton (1976), Option Pricing When Underlying Stock Returns Are Discontinuous, Journal of Financial Economics 3, 125-144. Formulas above are derived by conditioning on the Poisson count; they state the parameter convention explicitly.
