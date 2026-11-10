# Compound options (Geske 1979) and the simple chooser option (Rubinstein 1991), Black-Scholes-Merton with yield q

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting and assumptions
- Underlying S follows GBM under the risk-neutral measure with constant vol $\sigma$, rate r, continuous dividend yield q
  (cost of carry b = r - q); European exercise; no smile, no jumps.
- Compound option = outer option (strike K1, expiry T1) written on an inner European option (strike K2, expiry $\mathrm{T2} > \mathrm{T1}$).
  At T1 the holder pays K1 (outer call) or receives K1 (outer put) for the inner option. Payoffs at T1:
  outer call $\max (V(S_{\mathrm{T1}}) - \mathrm{K1}, 0)$, outer put $\max (\mathrm{K1} - V(S_{\mathrm{T1}}), 0)$, where V is the BSM value of the inner option
  with remaining life $\tau  = \mathrm{T2} - \mathrm{T1}$.
- Times are measured from today (valuation date): T1 and T2 are times to expiry in years, not dates.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $S$ | spot today | price |
| K1 | strike of the outer option (premium paid/received at T1 for the inner option) | price (option premium units) |
| K2 | strike of the inner option | price |
| T1, T2 | times from today to the outer and inner expiries, $\mathrm{T1} < \mathrm{T2}$ | years |
| $r, q$ | continuously compounded rate and dividend yield; 5% is 0.05 | $1/\mathrm{year}$ |
| $\sigma$ | annualized lognormal vol; 30% is 0.30 | $1/\sqrt{\mathrm{year}}$ |

## Step 1: critical price S* (uses tau = T2 - T1, NOT T2)
$S^{*}$ solves $\mathrm{BSM}_{\mathrm{inner}}(S^{*}, \mathrm{K2}, \tau , r, q, \sigma ) = \mathrm{K1}$, where $\mathrm{BSM}_{\mathrm{inner}}$ is the call or put price with time $\tau$.
- Inner call: value increases in S from 0 to infinity, so $S^{*}$ always exists for $\mathrm{K1} > 0$. Root-find (Brent/bisection) on
  $f(x) = \;\text{Call}\;(x, \mathrm{K2}, \tau ) - \mathrm{K1}$, bracket [tiny, K2] and double the upper end until $f > 0$.
- Inner put: value decreases in S from $\mathrm{K2} e^{-r \tau}$ (at $S \to  0$) to 0. Root-find $\;\text{Put}\;(x, \mathrm{K2}, \tau ) - \mathrm{K1}$, bracket
  [tiny, K2], double the upper end until $f < 0$. $S^{*}$ exists only if $\mathrm{K1} < \mathrm{K2} e^{-r \tau}$.
  If $\mathrm{K1} \ge  \mathrm{K2} e^{-r \tau}$: call on put = 0 (never exercised) and put on put = $\mathrm{K1} e^{-r \mathrm{T1}} - \;\text{Put}\;(S, \mathrm{K2}, \mathrm{T2})$ (always exercised).
- $\mathrm{K1} \to  0$: for an inner call $S^{*} \to  0$(its value rises in S); for an inner put $S^{*} \to  \infty$(its value falls in S).
  In both cases the outer call tends to the inner option: call on call -> Call(S, K2, T2), call on put -> Put(S, K2, T2).

## Step 2: d-terms (y pairs S with S* and T1; z pairs S with K2 and T2)

$$
\begin{gathered}
\mathrm{y1} = [ \ln (S / S^{*}) + (b + \sigma ^{2}/2) \mathrm{T1} ] / (\sigma  \sqrt{\mathrm{T1}}),     \mathrm{y2} = \mathrm{y1} - \sigma  \sqrt{\mathrm{T1}} \\
\mathrm{z1} = [ \ln (S / \mathrm{K2}) + (b + \sigma ^{2}/2) \mathrm{T2} ] / (\sigma  \sqrt{\mathrm{T2}}),     \mathrm{z2} = \mathrm{z1} - \sigma  \sqrt{\mathrm{T2}} \\
\rho  = \sqrt{\mathrm{T1} / \mathrm{T2}}
\end{gathered}
$$

$M(a, c; \rho ) = \operatorname{P}(X \le  a, Y \le  c)$ for standard bivariate normal X, Y with correlation $\rho$; N = univariate normal CDF.
Use an accurate bivariate CDF (e.g. scipy.stats.$\mathrm{multivariate}_{\mathrm{normal}}$.cdf with mean 0, cov [[1, $\rho$], [$\rho$, 1]],
or Drezner-Wesolowsky / Genz). Discounting: $S e^{-q \mathrm{T2}}$, $\mathrm{K2} e^{-r \mathrm{T2}}$, $\mathrm{K1} e^{-r \mathrm{T1}}$.

## Step 3: the four compound options (Geske 1979; Haug 2007 sign convention)

$$
\begin{gathered}
\text{Call on call} = S e^{-\mathrm{qT2}} M( \mathrm{z1},  \mathrm{y1};  \rho ) - \mathrm{K2} e^{-\mathrm{rT2}} M( \mathrm{z2},  \mathrm{y2};  \rho ) - \mathrm{K1} e^{-\mathrm{rT1}} N( \mathrm{y2}) \\
\text{Put on call}  = \mathrm{K2} e^{-\mathrm{rT2}} M( \mathrm{z2}, -\mathrm{y2}; -\rho ) - S e^{-\mathrm{qT2}} M( \mathrm{z1}, -\mathrm{y1}; -\rho ) + \mathrm{K1} e^{-\mathrm{rT1}} N(-\mathrm{y2}) \\
\text{Call on put}  = \mathrm{K2} e^{-\mathrm{rT2}} M(-\mathrm{z2}, -\mathrm{y2};  \rho ) - S e^{-\mathrm{qT2}} M(-\mathrm{z1}, -\mathrm{y1};  \rho ) - \mathrm{K1} e^{-\mathrm{rT1}} N(-\mathrm{y2}) \\
\text{Put on put}   = S e^{-\mathrm{qT2}} M(-\mathrm{z1},  \mathrm{y1}; -\rho ) - \mathrm{K2} e^{-\mathrm{rT2}} M(-\mathrm{z2},  \mathrm{y2}; -\rho ) + \mathrm{K1} e^{-\mathrm{rT1}} N( \mathrm{y2})
\end{gathered}
$$

$S^{*}$ above is the call-inner root for the first two lines and the put-inner root for the last two.
Outer option exercised at T1 when: call on call $S_{\mathrm{T1}}$ > $S^{*}$; put on call $S_{\mathrm{T1}}$ < $S^{*}$; call on put $S_{\mathrm{T1}}$ < $S^{*}$; put on put $S_{\mathrm{T1}}$ > $S^{*}$.
Correlation argument: +$\rho$ when the outer option is a call, -$\rho$ when the outer option is a put (exactly as written above).

## Checks (compound put-call parity, exact)

$$
\begin{gathered}
\text{Call on call} - \text{Put on call} = \;\text{Call}\;(S, \mathrm{K2}, \mathrm{T2}) - \mathrm{K1} e^{-r \mathrm{T1}} \\
\text{Call on put}  - \text{Put on put}  = \;\text{Put}\;(S, \mathrm{K2}, \mathrm{T2})  - \mathrm{K1} e^{-r \mathrm{T1}}
\end{gathered}
$$

Call(S, K2, T2) / Put(S, K2, T2) are plain BSM prices with time T2. Also: every price >= 0, and as $\mathrm{T1} \to  \mathrm{T2}$ call on call
-> Call(S, K1 + K2, T2) and call on put -> Put(S, K2 - K1, T2) (when $\mathrm{K2} > \mathrm{K1}$).

## Simple chooser option (Rubinstein 1991), with yield q
At choice time $t (0 < t < T)$ the holder picks a European call or put, both with strike K and expiry T (times from today).
Value at t is $\max (c_{t}, p_{t}) = c_{t} + e^{-q(T-t)} \max (K e^{-(r-q)(T-t)} - S_{t}, 0)$ by put-call parity, so

$$
\mathrm{Chooser} = \;\text{Call}\;(S, K, T) + e^{-q(T-t)} \cdot  \;\text{Put}\;(S, K e^{-(r-q)(T-t)}, t)
$$

where Call(., ., T) and Put(., ., t) are BSM prices with the same r, q, $\sigma$ and the stated time to expiry. Explicitly:

$$
\begin{gathered}
d  = [ \ln (S/K) + (b + \sigma ^{2}/2) T ] / (\sigma  \sqrt{T}) \\
y  = [ \ln (S/K) + b T + \sigma ^{2} t / 2 ] / (\sigma  \sqrt{t}) \\
\mathrm{Chooser} = S e^{-qT} N(d) - K e^{-rT} N(d - \sigma  \sqrt{T}) - S e^{-qT} N(-y) + K e^{-rT} N(-y + \sigma  \sqrt{t})
\end{gathered}
$$

Checks: Chooser >= $\max ( \;\text{Call}\;(S,K,T), \;\text{Put}\;(S,K,T) )$; t -> 0 gives $\max ( \;\text{call}\;, \;\text{put}\; )$; t -> T gives the straddle Call + Put.
Equivalent form: $\;\text{Put}\;(S, K, T) + e^{-q(T-t)} \;\text{Call}\;(S, K e^{-(r-q)(T-t)}, t)$.
Complex choosers (different strikes or expiries for the call and the put) need a critical price and bivariate normals;
the formula above does NOT apply to them.

## Common mistakes
- Using T2 instead of $\tau  = \mathrm{T2} - \mathrm{T1}$ inside the critical-price equation ($S^{*}$ is a price AT T1 for an option with life $\tau$).
- Pairing $S^{*}$ with T2 or K2 with T1: y-terms use ($S^{*}$, T1), z-terms use (K2, T2).
- Wrong sign of $\rho$ or of an argument for the put variants; check with the two parity relations above.
- Forgetting $e^{-\mathrm{qT2}}$ on S (not $e^{-\mathrm{qT1}}$) and discounting K1 with T2 instead of T1.
- Using the call-inner $S^{*}$ for an option on a put ($S^{*}$ differs per inner type).
- Not handling the no-root case for an inner put; a root-finder with a fixed bracket then fails or returns garbage.
- Chooser: forgetting the $e^{-q(T-t)}$ factor or using strike K $e^{-r(T-t)}$ when $q \ne  0$; putting T instead of t into the put.
- Low-precision bivariate normal approximations can give parity errors far above rounding; prefer a library CDF.

## Applicability and limits
- Exact only under constant-parameter BSM with European outer and inner options; American features, stochastic or
  term-structure vol and smiles are not covered. Geske's original application is equity as a call on firm value.
- With discrete dividends between T1 and T2, or time-varying r, the formula needs modification.
- Numerical independent check: Monte Carlo of $S_{\mathrm{T1}}$ (exact GBM step), inner option in closed form at T1, outer payoff
  discounted with $e^{-r \mathrm{T1}}$; or 1-D quadrature over $S_{\mathrm{T1}}$ split at $S^{*}$.

## Sources
Geske, R. (1979) "The valuation of compound options", J. Financial Economics 7(1):63-81;
Rubinstein, M. (1991) "Options for the undecided", Risk 4(4) (simple chooser);
Haug, E. G. (2007) The Complete Guide to Option Pricing Formulas, 2nd ed., McGraw-Hill (compound and chooser sections);
Hull, J. C. Options, Futures, and Other Derivatives, exotic options chapter (compound and chooser options).
