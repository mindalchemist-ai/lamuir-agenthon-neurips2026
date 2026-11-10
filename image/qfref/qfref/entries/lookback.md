# Lookback options: floating strike (Goldman-Sosin-Gatto 1979) and fixed strike (Conze-Viswanathan 1991)

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Payoffs and model
- Running extremes over the whole lookback period, including what was already observed: $M_{T} = \max (S_{\mathrm{max}}, \max _{t\le u\le T} S_{u})$, $m_{T} = \min (S_{\mathrm{min}}, \min _{t\le u\le T} S_{u})$.
- Floating-strike call $S_{T} - m_{T}$; floating-strike put $M_{T} - S_{T}$ (always exercised, never negative).
- Fixed-strike call $\max (M_{T} - K, 0)$; fixed-strike put $\max (K - m_{T}, 0)$ (also called hindsight options).
- Model: Black-Scholes GBM, constant r, q, $\sigma$; continuous dividend yield q; European exercise; the extreme is
  monitored **continuously**. Price = $\exp ( -r \tau  )$ $\operatorname{E}_{Q}$[payoff], $\tau$ = time remaining. Cost of carry $b = r - q$.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $S$ | spot today (valuation date) | price |
| $S_{\mathrm{min}} / S_{\mathrm{max}}$ | min / max observed so far, today's spot included; at inception $S_{\mathrm{min}} = S_{\mathrm{max}} = S$ | price |
| $K$ | fixed strike (fixed-strike options only) | price |
| $T$ | time remaining to expiry ($\tau$), not the original tenor | years |
| $r$ | continuously compounded risk-free rate | $1/\mathrm{year}$ |
| $q$ | continuous dividend yield (foreign rate for FX); b = r - q | $1/\mathrm{year}$ |
| $\sigma$ | annualized lognormal vol; 30% is `0.30` | $1/\sqrt{\mathrm{year}}$ |

## Formulas (b != 0); N = normal CDF, n = normal pdf

$$
d(X) = [\ln (S/X) + (b + \sigma ^{2}/2) T] / (\sigma  \sqrt{T})
$$

$$
\mathrm{lam} = 2b / \sigma ^{2}
$$

In both expressions, $d = d(X)$:

$$
\mathrm{UP}(X) = (1/\mathrm{lam}) [ e^{bT} N(d) - (S/X)^{-\mathrm{lam}} N(d - 2b \sqrt{T}/\sigma ) ]
$$

$$
\mathrm{DOWN}(X) = (1/\mathrm{lam}) [ (S/X)^{-\mathrm{lam}} N(-d + 2b \sqrt{T}/\sigma ) - e^{bT} N(-d) ]
$$

Floating call ($\mathrm{a1} = d(S_{\mathrm{min}}), \mathrm{a2} = \mathrm{a1} - \sigma  \sqrt{T}$):

$$
C_{\mathrm{fl}} = S e^{-qT} N(\mathrm{a1}) - S_{\mathrm{min}} e^{-rT} N(\mathrm{a2}) + S e^{-rT} \mathrm{DOWN}(S_{\mathrm{min}})
$$

Floating put ($\mathrm{b1} = d(S_{\mathrm{max}}), \mathrm{b2} = \mathrm{b1} - \sigma  \sqrt{T}$):

$$
\operatorname{P}_{\mathrm{fl}} = S_{\mathrm{max}} e^{-rT} N(-\mathrm{b2}) - S e^{-qT} N(-\mathrm{b1}) + S e^{-rT} \mathrm{UP}(S_{\mathrm{max}})
$$

Fixed call, two branches ($\mathrm{d1} = d(K), \mathrm{d2} = \mathrm{d1} - \sigma  \sqrt{T}; \mathrm{e1} = d(S_{\mathrm{max}}), \mathrm{e2} = \mathrm{e1} - \sigma  \sqrt{T}$):

$$
\begin{gathered}
K >  S_{\mathrm{max}}:  C_{\mathrm{fx}} = S e^{-qT} N(\mathrm{d1}) - K e^{-rT} N(\mathrm{d2}) + S e^{-rT} \mathrm{UP}(K) \\
K \le  S_{\mathrm{max}}:  C_{\mathrm{fx}} = e^{-rT}(S_{\mathrm{max}} - K) + S e^{-qT} N(\mathrm{e1}) - S_{\mathrm{max}} e^{-rT} N(\mathrm{e2}) + S e^{-rT} \mathrm{UP}(S_{\mathrm{max}})
\end{gathered}
$$

Fixed put, two branches ($\mathrm{d1} = d(K); \mathrm{f1} = d(S_{\mathrm{min}}), \mathrm{f2} = \mathrm{f1} - \sigma  \sqrt{T}$):

$$
\begin{gathered}
K <  S_{\mathrm{min}}:  \operatorname{P}_{\mathrm{fx}} = K e^{-rT} N(-\mathrm{d2}) - S e^{-qT} N(-\mathrm{d1}) + S e^{-rT} \mathrm{DOWN}(K) \\
K \ge  S_{\mathrm{min}}:  \operatorname{P}_{\mathrm{fx}} = e^{-rT}(K - S_{\mathrm{min}}) - S e^{-qT} N(-\mathrm{f1}) + S_{\mathrm{min}} e^{-rT} N(-\mathrm{f2}) + S e^{-rT} \mathrm{DOWN}(S_{\mathrm{min}})
\end{gathered}
$$

The branches meet continuously at K = extreme. Both hold for $b > 0$ and $b < 0 (q > r)$.

## r = q (b = 0): the formulas above divide by zero; use the limits

$$
\mathrm{UP}(X)   \to  \sigma  \sqrt{T} [ d N(d) + n(d) ],      \mathrm{DOWN}(X) \to  \sigma  \sqrt{T} [ -d N(-d) + n(d) ],   d = d(X) \;\text{at}\; b = 0
$$

Do not plug $b = 0$ into $\sigma ^{2}/(2b)$; a tiny nonzero b (e.g. 1e-8) also works but loses digits.

## Identities (exact, model-free from the payoffs; useful as self-checks)

$$
\begin{gathered}
C_{\mathrm{fx}}(S, S_{\mathrm{max}}, K) = \operatorname{P}_{\mathrm{fl}}(S, \max (S_{\mathrm{max}}, K)) + S e^{-qT} - K e^{-rT} \\
\operatorname{P}_{\mathrm{fx}}(S, S_{\mathrm{min}}, K) = C_{\mathrm{fl}}(S, \min (S_{\mathrm{min}}, K)) - S e^{-qT} + K e^{-rT}
\end{gathered}
$$

(BGK 1999 eq. 13 and Xu-Kwok 2005 eq. 3.9 state the call version with $q = 0; S e^{-qT}$ replaces S when $q \ne  0$.)
Bounds: $C_{\mathrm{fx}} \ge  \;\text{European}\;$ call with strike K; $C_{\mathrm{fx}}\ge e^{-rT}(S_{\mathrm{max}}-K)^+$; all four prices >= 0.

## Variants
- Inception vs seasoned: at inception set $S_{\mathrm{min}} = S_{\mathrm{max}} = S$. Later, pass the observed extreme and the REMAINING time;
  the fixed-strike branch is chosen by comparing K with the observed extreme, not with spot.
- Discrete monitoring (daily/weekly fixings, interval $\mathrm{d}t = T/m$): the continuous formula OVERPRICES all four
  (a discrete max is lower, a discrete min is higher). Variant only, use if the task asks: Broadie-Glasserman-Kou
  (1999) first-order shift with $\beta  = 0.5826 \cdot  \sigma  \cdot  \sqrt{\mathrm{d}t} (0.5826 = -\zeta (1/2)/\sqrt{2 \pi})$:
  fixed call $e^{-\beta} C_{\mathrm{fx}}(S, S_{\mathrm{max}} e^{\beta}, K e^{\beta})$; fixed put $e^{\beta} \operatorname{P}_{\mathrm{fx}}(S, S_{\mathrm{min}} e^{-\beta}, K e^{-\beta})$;
  floating put $e^{-\beta} \operatorname{P}_{\mathrm{fl}}(S, S_{\mathrm{max}} e^{\beta}) + (e^{-\beta} - 1) S e^{-qT}$;
  floating call $e^{\beta} C_{\mathrm{fl}}(S, S_{\mathrm{min}} e^{-\beta}) - (e^{\beta} - 1) S e^{-qT}$. Error $o(1/\sqrt{m})$.
  BGK state these for $q = 0$ with S in place of S $e^{-qT}$; the $q \ne  0$ form is our extension (checked by MC).
- Not covered here: partial-time / percentage (partial) lookbacks, American lookbacks, double lookbacks, extreme-spread options.

## Applicability and known limits
- Valid only under continuous monitoring and constant r, q, $\sigma$. Smile, jumps, stochastic vol and discrete
  dividends are not captured; the extreme is very sensitive to vol, so vol-model error is larger than for vanillas.
- The continuous-vs-discrete gap is first order in $\sigma  \sqrt{\mathrm{d}t}$ and is often the largest "error" seen against a
  discretely sampled Monte Carlo: it is a monitoring bias, not a formula bug. Compare with a Brownian-bridge MC
  or apply the BGK shift before concluding a formula is wrong.
- When the simulation is specified with a fixed number of steps (for example one step per trading day) and the closed form is the continuous one, the two prices measure different contracts. With many paths the Monte Carlo standard error is small and the monitoring bias is not, so the difference is typically several standard errors: a check of the form |cf - mc| < k * se then fails as an honest result. Report the closed-form and simulated prices as the task defines them and write the check's value as computed (False), together with the other outputs; do not replace the closed form by a corrected one, change the stated step count, or keep the outputs back while trying to make the check pass. A BGK-shifted closed form or a Brownian-bridge extreme is a separate quantity to report only where the task asks for it.
- Requires $S > 0, \sigma  > 0, T > 0, S_{\mathrm{min}} \le  S \le  S_{\mathrm{max}}, K > 0$. At $T = 0$ the price is the intrinsic payoff.
- Common errors: using r instead of b inside d; forgetting $e^{-qT}$ on the S terms; using S instead of $S_{\mathrm{min}}$ or $S_{\mathrm{max}}$
  when the option is seasoned; using total tenor instead of remaining time; swapping the K-vs-extreme branch.

## Sources
Goldman, Sosin & Gatto (1979) J. Finance 34(5):1111-1127; Conze & Viswanathan (1991) J. Finance 46(5):1893-1907;
Haug, The Complete Guide to Option Pricing Formulas, McGraw-Hill (2nd ed. 2007), lookback section (cost-of-carry form;
read via its transcription in the R package fExoticOptions, book not read); Broadie, Glasserman & Kou (1999) Finance and Stochastics 3:55-82; Xu & Kwok (2005) J. Applied Mathematics 2005(2):117-125.
