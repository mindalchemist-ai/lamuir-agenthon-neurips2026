# Black-Scholes prices, Greeks and identities

Use this reference to price European vanilla options, compute analytic Greeks, and check decomposition and parity under Black–Scholes.

Explicit task definitions and contract conventions take precedence. If they conflict or are incomplete, identify the ambiguity and state the convention used.

## 1. Shared foundations
Symbols are local to this reference. Map the task's quantities by definition, not by letter. This reference assumes European exercise, positive spot S and strike K, constant rates r and continuous dividend yield q, volatility $\sigma$, remaining maturity T, and payment at expiry. Rates and $\sigma$ are decimals; T is in years. Discrete cash dividends require a different model or an explicitly specified approximation. N and $\phi$ denote the standard normal CDF and density. Formulas below require $T > 0$ and $\sigma  > 0$.

## 2. Prices and decomposition
**Discount and dividend factors**

$$
D = \exp (-r\cdot T), B = \exp (-q\cdot T).
$$

**Black–Scholes standardized moneyness terms**

$$
\mathrm{d1} = (\ln (S/K) + (r-q+\sigma ^{2}/2)\cdot T)/(\sigma \cdot \sqrt{T}); \mathrm{d2} = \mathrm{d1}-\sigma \cdot \sqrt{T}.
$$

**European call price**

$$
C = S\cdot B\cdot N(\mathrm{d1}) - K\cdot D\cdot N(\mathrm{d2}).
$$

**European put price**

$$
\operatorname{P} = K\cdot D\cdot N(-\mathrm{d2}) - S\cdot B\cdot N(-\mathrm{d1}).
$$

A unit-cash call costs D*N(d2); an asset call costs S*B*N(d1). Thus $C = \mathrm{asset}_{\mathrm{call}} - K\cdot \mathrm{unit}_{\mathrm{cash},\mathrm{call}}$. Similarly $\operatorname{P} = K\cdot \mathrm{unit}_{\mathrm{cash},\mathrm{put}} - \mathrm{asset}_{\mathrm{put}}$. If a cash digital pays Q, divide its price by Q before using these decompositions (Q must be nonzero). Check call and put decomposition separately. Put-call parity $C-\operatorname{P}=S\cdot B-K\cdot D$ is a different identity and does not replace these two checks.

## 3. Analytic Greeks
Hold the other model inputs fixed when differentiating.
**Call Delta**

$$
\Delta _{\mathrm{call}} = B\cdot N(\mathrm{d1})
$$

**Put Delta**

$$
\Delta _{\mathrm{put}} = B\cdot (N(\mathrm{d1})-1).
$$

**$\Gamma$ shared by call and put**

$$
\Gamma _{\mathrm{call}} = \Gamma _{\mathrm{put}} = B\cdot \phi (\mathrm{d1})/(S\cdot \sigma \cdot \sqrt{T}).
$$

**Vega shared by call and put**

$$
\mathrm{Vega}_{\mathrm{call}} = \mathrm{Vega}_{\mathrm{put}} = S\cdot B\cdot \phi (\mathrm{d1})\cdot \sqrt{T}.
$$

**Call Rho**

$$
\mathrm{Rho}_{\mathrm{call}} = K\cdot T\cdot D\cdot N(\mathrm{d2})
$$

**Put Rho**

$$
\mathrm{Rho}_{\mathrm{put}} = -K\cdot T\cdot D\cdot N(-\mathrm{d2}).
$$

**Call calendar Theta**

$$
\Theta _{\mathrm{call}} = -S\cdot B\cdot \phi (\mathrm{d1})\cdot \sigma /(2\cdot \sqrt{T}) + q\cdot S\cdot B\cdot N(\mathrm{d1}) - r\cdot K\cdot D\cdot N(\mathrm{d2}).
$$

**Put calendar Theta**

$$
\Theta _{\mathrm{put}} = -S\cdot B\cdot \phi (\mathrm{d1})\cdot \sigma /(2\cdot \sqrt{T}) - q\cdot S\cdot B\cdot N(-\mathrm{d1}) + r\cdot K\cdot D\cdot N(-\mathrm{d2}).
$$

$\Theta$ here is calendar-time sensitivity, $-\mathrm{d}V/\mathrm{d}T$. A requested maturity derivative has the opposite sign. Vega and Rho above are per unit change in decimal $\sigma$ or r. Divide by 100 for a one-percentage-point change; divide Rho by 10000 for one basis point. Convert both an estimate and its standard error. Calendar-day Theta uses the specified day-count divisor, not an assumed trading-day count.

These formulas follow by differentiating Section 2; $SB\phi(d_1)=KD\phi(d_2)$ cancels the derivative-of-d terms. Rho assumes q fixed; a different rule for moving carry or a calibrated curve changes that derivative.

## 4. Verification and limits
Use the Greek conventions in Section 3.
**Black–Scholes PDE residual**

$$
\mathrm{PDE} \mathrm{residual} = \Theta  + (r-q)\cdot S\cdot \Delta  + \sigma ^{2}\cdot S^{2}\cdot \Gamma /2 - r\cdot V.
$$

For a correct analytic implementation it should be close to floating-point error after allowing for the scale of the terms.
**Spot, volatility and rate parity identities**

$$
\Delta _{\mathrm{call}}-\Delta _{\mathrm{put}}=B; \Gamma _{\mathrm{call}}-\Gamma _{\mathrm{put}}=0; \mathrm{Vega}_{\mathrm{call}}-\mathrm{Vega}_{\mathrm{put}}=0; \mathrm{Rho}_{\mathrm{call}}-\mathrm{Rho}_{\mathrm{put}}=K\cdot T\cdot D.
$$

**Calendar-Theta parity identity**

$$
\Theta _{\mathrm{call}}-\Theta _{\mathrm{put}}=q\cdot S\cdot B-r\cdot K\cdot D.
$$

Independently perturb one input at a time and reprice to check signs, units and bindings. Use several bump sizes; very small bumps lose precision. Shared wrong d1/d2 can survive algebraic identity checks, so an independent pricing integral or PDE is stronger evidence.
At $T=0$ return payoff; Greeks at the strike may not exist. At $\sigma =0$ price the deterministic terminal payoff, $D\cdot \max (S\cdot \exp ((r-q)\cdot T)-K,0)$ for a call. Do not divide by zero or assert smooth Greeks at its kink.

## 5. References
Black and Scholes (1973), The Pricing of Options and Corporate Liabilities. Merton (1973), Theory of Rational Option Pricing. These are model references; Sections 2-4 state the conventions used here explicitly.
