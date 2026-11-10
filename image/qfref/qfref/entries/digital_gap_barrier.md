# Black–Scholes Reference by Contract Type

This reference explains how to identify a payoff, select its Black–Scholes pricing formula, and check the result. It covers European terminal payoffs and continuously monitored single barriers with constant model parameters. Read Shared Foundations first, then the sections needed for the contract. Follow the contract specification when it differs from this reference; do not force a contract outside these assumptions into these formulas. American exercise and stochastic volatility require other methods.

Follow the task’s prescribed steps. Use the referenced sections for definitions and formulas; the section order is not an execution plan.

## Shared Foundations

Map the task’s symbols and units to the definitions here before the first calculation. Recheck the mapping when the contract, model, or input definitions change; there is no need to repeat an unchanged mapping in every response.

Before choosing a formula, identify what is paid, when it is paid, and which event causes payment. Also identify exercise style, any barrier monitoring schedule, rebate rules, and input/output units. If a necessary convention is unspecified, state the assumption used.

European describes exercise timing; digital describes the payoff; barrier describes a path condition. These features can occur in the same contract.

| Symbol | Meaning |
|---|---|
| $S$ | Current underlying price |
| $K$ | Strike |
| $H$ | Barrier level |
| $Q$ | Fixed cash payment, distinct from the risk-neutral measure $\mathbb Q$ |
| $R$ | Rebate amount |
| $r$ | Continuously compounded risk-free rate |
| $q$ | Continuous dividend yield |
| $\sigma$ | Annualized volatility in decimal units |
| $T$ | Remaining maturity in years |
| N, $\phi$ | Standard normal CDF and density |
| $S_{T}$ | Underlying price at maturity |
| $\Pi$ | Payoff function, written $\Pi$ in formulas |
| $V$ | Present value of a payoff |
| $C, \operatorname{P}$ | Ordinary European call and put prices, unless a subscript specifies another contract |

Notation: $\mathbf1_A$ equals 1 when event A occurs and 0 otherwise; $z^+=\max(z,0)$; ln is the natural logarithm. All probabilities and expectations in this reference use the risk-neutral measure $\mathbb Q$, including expressions where the superscript is omitted.

For FX, the foreign interest rate plays the role of q. Rates and volatility use annual units here, so T must be in years. The discount factor $\exp (-rT)$ applies to a payment at maturity. The formulas below assume positive spot, strike, volatility, and maturity. At zero maturity evaluate the payoff; at zero volatility use the deterministic terminal price and path.

The model describes proportional price changes. Under the risk-neutral measure,
**Risk-neutral stock dynamics**

$$
dS_t=(r-q)S_tdt+\sigma S_tdW_t^{\mathbb Q}.
$$

Applying Itô's lemma converts the price process into the log-price process:
**Risk-neutral log-price dynamics**

$$
d\ln S_t=(r-q-\sigma^2/2)dt+\sigma dW_t^{\mathbb Q}.
$$

Define log drift $\nu=r-q-\sigma^2/2$. Then
**Terminal stock distribution**

$$
S_T=S\exp(\nu T+\sigma\sqrt T Z),\quad Z\sim N(0,1).
$$

If an input already describes log drift, do not subtract the Itô correction again.

For a payoff $\Pi(S_T)$ paid at maturity, calculate its risk-neutral expectation and discount it:
**Discounted expected payoff**

$$
V=e^{-rT}\mathbb E^{\mathbb Q}[\Pi(S_T)].
$$

**Black–Scholes exercise thresholds**

$$
d_2=\frac{\ln(S/K)+(r-q-\sigma^2/2)T}{\sigma\sqrt T},\qquad d_1=d_2+\sigma\sqrt T.
$$

The event $S_{T} > K$ is equivalent to $Z > -\mathrm{d2}$. Normal symmetry therefore gives probability N(d2). For an asset payment, the expectation also contains $S_{T}$. The following identity, valid for real a and z, evaluates that weighted normal integral:
**Normal-density exponential tilting identity**

$$
e^{az}\phi(z)=e^{a^2/2}\phi(z-a)
$$

**Truncated terminal asset expectation**

$$
\mathbb E[S_T\mathbf1_{S_T>K}]=Se^{(r-q)T}N(d_1).
$$

### Transfer across notation and parameter values

For example, a dividend yield named D can replace q here only if it denotes the same continuous annual yield; a cash dividend amount cannot.

Renaming symbols consistently does not change the mathematics or numerical result. The definitions, relationships, and derivations transfer to another task when the payoff, model assumptions, payment timing, and monitoring convention match. Changing parameter values usually changes the result. Re-evaluate branch conditions such as the ordering of strike and barrier for each new input; do not carry over a previously selected branch or Boolean conclusion.

Notation invariance is different from parameter invariance. A relationship can remain valid across admissible parameter values without the price being constant. Some transformations imply a predictable change rather than equality: multiplying a fixed cash payoff Q by a positive factor multiplies its price by that factor, with the other inputs unchanged. For a vanilla cash digital, jointly scaling positive S and K by the same factor leaves its price unchanged when Q, r, q, $\sigma$, and T are fixed, because S/K is unchanged. That test is not a test of sensitivity to spot alone.

Use these as transformation checks only after deriving what must remain equal and what must scale. If a new task changes the payoff, stochastic process, exercise rights, or observation schedule, re-establish applicability before reusing a formula.

## European Vanilla Options

**Ordinary European payoff.** A call pays $(S_T-K)^+$; a put pays $(K-S_T)^+$, both at maturity. These are payoffs, not profits after deducting the premium.

**Ordinary European pricing.** Decompose the call payoff as
**Call payoff decomposition**

$$
(S_T-K)^+=S_T\mathbf1_{S_T>K}-K\mathbf1_{S_T>K}.
$$

Using the shared probability and asset moment gives
**European call price**

$$
C=Se^{-qT}N(d_1)-Ke^{-rT}N(d_2)
$$

**European put price**

$$
P=Ke^{-rT}N(-d_2)-Se^{-qT}N(-d_1).
$$

Apply contract quantity separately if the requested value is for a position.

**Ordinary European checks.** Compare contracts with the same spot, strike, maturity, rates, and volatility:
**European put-call parity**

$$
C-P=Se^{-qT}-Ke^{-rT}.
$$

**European call price bounds**

$$
\max(Se^{-qT}-Ke^{-rT},0)\le C\le Se^{-qT}
$$

**European put price bounds**

$$
\max(Ke^{-rT}-Se^{-qT},0)\le P\le Ke^{-rT}.
$$

Do not apply these European formulas as an American early-exercise solution.

## Cash or Nothing Digital Options

**Cash-or-nothing payoff.** A call pays $Q\mathbf1_{S_T>K}$; a put pays $Q\mathbf1_{S_T<K}$. Identify the cash amount rather than assuming $Q = 1$. Under the nondegenerate continuous terminal distribution, equality at the strike has zero probability.

**Cash digital pricing.** Multiply the fixed cash payment by its payment probability, then discount:
**Cash digital call price**

$$
C_{cash}=Qe^{-rT}N(d_2)
$$

**Cash digital put price**

$$
P_{cash}=Qe^{-rT}N(-d_2).
$$

Use d2 for the terminal probability. An ordinary option formula would price a different payoff.

**Cash digital checks.** Use the same parameters and cash amount for the call and put. For positive Q,
**Cash digital complement and bounds**

$$
C_{cash}+P_{cash}=Qe^{-rT},\qquad 0\le C_{cash},P_{cash}\le Qe^{-rT}.
$$

Holding all other inputs fixed,
**Cash-call sensitivity to spot**

$$
\frac{\partial C_{cash}}{\partial S}=\frac{Qe^{-rT}\phi(d_2)}{S\sigma\sqrt T}>0,\quad
$$

**Cash-call sensitivity to strike**

$$
\frac{\partial C_{cash}}{\partial K}=-\frac{Qe^{-rT}\phi(d_2)}{K\sigma\sqrt T}<0.
$$

To check spot sensitivity, change spot alone and retain the original strike. Holding moneyness fixed changes another input. Allow floating-point tolerance in saturated tails. These signs cannot be assumed for barrier digitals.

## Asset or Nothing Digital Options

**Asset-or-nothing payoff.** A call pays $S_T\mathbf1_{S_T>K}$; a put pays $S_T\mathbf1_{S_T<K}$. There is no strike payment in these contracts. The delivered asset value is the terminal value, not the initial spot.

**Asset digital pricing.** Discount the asset-weighted expectation to obtain
**Asset digital call price**

$$
C_{asset}=Se^{-qT}N(d_1)
$$

**Asset digital put price**

$$
P_{asset}=Se^{-qT}N(-d_1).
$$

The use of d1 follows from weighting the terminal distribution by $S_{T}$; it is not the same calculation as a fixed-cash payment probability.

**Asset digital checks.** With matching parameters, call and put events cover all terminal outcomes, so
**Asset digital complement**

$$
C_{asset}+P_{asset}=Se^{-qT}.
$$

**Payoff decomposition and price checks.** Decomposition means expressing one payoff as a linear combination of other payoffs. For European contracts with the same underlying, strike K and maturity T,
**Call payoff decomposition**

$$
(S_T-K)^+=S_T\mathbf1_{S_T>K}-K\mathbf1_{S_T>K}
$$

**Put payoff decomposition**

$$
(K-S_T)^+=K\mathbf1_{S_T<K}-S_T\mathbf1_{S_T<K}.
$$

The asset digital supplies the asset leg; K units of a unit-payment cash digital supply the strike leg. Discounted expectation is linear, so their prices satisfy
**Call price from digital legs**

$$
C=C_{asset}-K C_{cash}^{(1)}
$$

**Put price from digital legs**

$$
P=K P_{cash}^{(1)}-P_{asset}.
$$

Use matching spot, strike, maturity, rates, volatility, payment time and currency for all legs. Here C and P are ordinary European option prices; the superscript (1) means a cash payment of one currency unit. If the cash digital instead pays $Q > 0$, divide its price by Q. For $Q = 0$, obtain a unit-payment digital separately rather than dividing by zero.

Check the prices already computed by the implementation, separately for calls and puts at every parameter set:

**Compute both decomposition residuals using the priced legs**

```python
# Per-contract prices, with matching inputs and Q_cash > 0.
unit_cash_call = cash_call_price / Q_cash
unit_cash_put = cash_put_price / Q_cash
call_replica = asset_call_price - strike * unit_cash_call
put_replica = strike * unit_cash_put - asset_put_price
call_residual = vanilla_call_price - call_replica
put_residual = vanilla_put_price - put_replica
```

Compare each residual with a suitable absolute-plus-relative numerical tolerance; for simulation, account for the sampling error of the difference, including covariance when estimates share paths. Do not replace the computed vanilla prices with the replicas merely to make this check pass. If vanilla prices were constructed from these same digital legs, zero residuals hold by construction and provide no independent pricing validation.

Put-call parity checks a different relation: $C - \operatorname{P} = S \exp (-qT) - K \exp (-rT)$. It does not check the asset/cash decomposition of either option. A passing parity residual cannot substitute for the two decomposition residuals. These identities concern matched European terminal payoffs; do not combine plain and barrier legs or different exercise styles.

## Gap Options

**Gap payoff.** A call pays $(S_T-K_{pay})\mathbf1_{S_T>K_{trigger}}$; a gap put pays $(K_{pay}-S_T)\mathbf1_{S_T<K_{trigger}}$. The trigger strike selects the event; the payment strike determines the cash leg. Identify these roles from definitions, since K1/K2 conventions vary.

**Gap pricing.** Substitute $K_{\mathrm{trigger}}$ for K in both d1 and d2; use $K_{\mathrm{pay}}$ only in the cash-payment terms below. Linearity of expectation gives
**Gap call price**

$$
C_{gap}=Se^{-qT}N(d_1^{trigger})-K_{pay}e^{-rT}N(d_2^{trigger})
$$

**Gap put price**

$$
P_{gap}=K_{pay}e^{-rT}N(-d_2^{trigger})-Se^{-qT}N(-d_1^{trigger}).
$$

**Gap checks.** When the trigger and payment strikes coincide, the gap formulas reduce to ordinary European formulas. For a matched gap call and put,
**Gap put-call parity**

$$
C_{gap}-P_{gap}=Se^{-qT}-K_{pay}e^{-rT}.
$$

The specified gap payoff can be negative on some outcomes. Adding a positive-part operator or clipping changes the contract.

## Vanilla Barrier Options

**Barrier condition.** Let $\tau_H$ be the first time the continuously monitored price reaches or crosses H during the contract. Use $\tau_H=\infty$ if no touch occurs. For a lower barrier, a touch means $S_{t} \le  H$; for an upper barrier, it means $S_{t} \ge  H$. A knock-out pays $\Pi(S_T)\mathbf1_{\tau_H>T}$; a knock-in pays $\Pi(S_T)\mathbf1_{\tau_H\le T}$. Identify upper or lower barrier, monitoring schedule, and rebate terms. A terminal condition alone does not determine whether the path previously touched the barrier.

For an ordinary barrier call or put, first apply the assumptions and knock-in/out rules in [Shared Barrier Mathematics](#shared-barrier-mathematics), then use its interval and surviving moments:
**Knock-out call from surviving moments**

$$
C_{KO}=e^{-rT}(J_1-KJ_0)
$$

**Knock-out put from surviving moments**

$$
P_{KO}=e^{-rT}(KJ_0-J_1).
$$

These combine surviving asset and cash legs. They price an ordinary payoff, not a fixed-cash digital payoff.

## Digital Barrier Options

**Digital barrier payoff.** A cash digital knock-out call pays $Q\mathbf1_{S_T>K}\mathbf1_{\tau_H>T}$. An asset digital knock-out call replaces Q by $S_{T}$. For a put, replace the terminal event $S_{T} > K$ with $S_{T} < K$. For a knock-in, replace the survival event $\tau _{H} > T$ with $\tau _{H} \le  T$. Keep the terminal trigger as well as the path condition; activation alone does not guarantee payment.

For a digital barrier payoff, first apply the assumptions and knock-in/out rules in [Shared Barrier Mathematics](#shared-barrier-mathematics), then use its interval and surviving moments:
**Cash digital knock-out value**

$$
V_{cash,KO}=Qe^{-rT}J_0
$$

**Asset digital knock-out value**

$$
V_{asset,KO}=e^{-rT}J_1.
$$

As an explicit branch, consider a down-and-out cash call with $S > H$ and $K \ge  H$. Define $z_{\mathrm{ref}}$ as the standardized reflected log-price threshold below. Then the price is
**Down-and-out cash-call branch and reflected threshold**

$$
Qe^{-rT}\left[N(d_2)-(H/S)^{2\nu/\sigma^2}N(z_{ref})\right],\quad
z_{ref}=\frac{\ln(H^2/(SK))+\nu T}{\sigma\sqrt T}.
$$

If $K < H$, surviving above H already guarantees finishing above K; use the interval beginning at $\ln  H$ instead. Choose branches from events, not labels alone.

## Shared Barrier Mathematics

This section calculates two building blocks: J0 is the joint probability of surviving and ending in a selected interval; J1 is the expected terminal asset value multiplied by the indicator of that same joint event. Neither quantity is divided by survival probability. Use them in the ordinary or digital barrier pricing section. Here, survival means the barrier has not been touched during monitoring. The formulas assume continuous monitoring, constant parameters, no rebate, and an initially unbreached barrier. For discretely monitored barriers, see [Discrete Monitoring and the BGK Approximation](#discrete-monitoring-and-the-bgk-approximation); the continuous formulas here are not exact discrete-monitoring formulas. The barrier H must be positive. An initially unbreached lower barrier requires $S > H$; an initially unbreached upper barrier requires $S < H$.

In the following identity, $V_{\mathrm{vanilla}}$ means the price of the same terminal payoff with the barrier condition removed. For a digital barrier, this is a vanilla digital, not an ordinary call or put. Knock-in and knock-out events partition paths, so with matching payoff, payment time, and monitoring, and no rebates,
**Knock-in value from in-out parity**

$$
V_{KI}=V_{vanilla}-V_{KO}.
$$

For nonnegative payoffs, both prices lie between zero and the matching vanilla price. A knock-out approaches vanilla as its barrier becomes sufficiently remote. Determine barrier status before using these formulas. If monitoring has already begun, check the monitored history as well as the current spot: a past touch remains effective even if spot has returned to the safe side. During active continuous monitoring, $S \le  H$ touches a lower barrier and $S \ge  H$ touches an upper barrier. Once touched, a no-rebate knock-out has value zero and a knock-in becomes the matching contract without a barrier. If a knock-out rebate remains payable, value only that outstanding payment according to its specified payment time; do not include a rebate that has already been paid. Rebate terms modify simple parity. Do not hide a material negative value or branch error by clipping.

Define $x = \ln  S, h = \ln  H, k = \ln  K, s = \sigma  \sqrt{T}, s^{2} = \sigma ^{2} T$, and $\nu  = r - q - \sigma ^{2}/2$. The variable y below denotes a possible terminal log-price. With no barrier restriction, its density conditional on initial log-price x is
**Unrestricted terminal log-price density**

$$
p_{free}(y\mid x)=\phi((y-x-\nu T)/s)/s.
$$

Reflect the initial log-price to 2h-x and define
**Reflection weight**

$$
w=\exp(2\nu(h-x)/\sigma^2).
$$

The safe side is $y > h$ for a lower barrier and $y < h$ for an upper barrier. On that side, the density for paths that survive is
**Surviving terminal log-price density**

$$
p_{survive}(y)=p_{free}(y\mid x)-wp_{free}(y\mid 2h-x).
$$

The subtraction removes paths that touch the barrier. Both density terms solve the drift–diffusion equation, and the weighted difference equals zero at the barrier. The reflected initial point lies outside the safe domain. Integrating $p_{\mathrm{survive}}$ over the safe domain gives survival probability; it is not a density conditional on survival and need not integrate to one.

Set $\mathrm{a0} = x + \nu  T$ and $\mathrm{a1} = 2h - x + \nu  T$: these are the terminal means of the original and reflected log-price processes. In F0 and F1, a is a generic log-price mean, while l and u are lower and upper terminal log-price limits. **Probability mass of a lognormal interval**

$$
F_0(a;l,u)=N((u-a)/s)-N((l-a)/s)
$$

**Asset moment of a lognormal interval**

$$
F_1(a;l,u)=e^{a+s^2/2}[N((u-a-s^2)/s)-N((l-a-s^2)/s)].
$$

F0 integrates the normal density over (l,u). F1 integrates $\exp (y)$ times that density, so it measures terminal asset value over the same interval. Completing the square gives the expression for F1. Subtract the reflected contributions to obtain
**Surviving probability moment**

$$
J_0=F_0(a_0;l,u)-wF_0(a_1;l,u),\quad
$$

**Surviving asset moment**

$$
J_1=F_1(a_0;l,u)-wF_1(a_1;l,u).
$$

| Knock-out | Allowed terminal log-price interval (l,u) |
|---|---|
| Down call | $(\max(h,k),\infty)$ |
| Down put | $(h,k)$ if $k > h$; otherwise empty |
| Up call | $(k,h)$ if $k < h$; otherwise empty |
| Up put | (-infinity,$\min ( h,k )$) |

Select the row using barrier direction and call/put type. The interval is the intersection of the safe side and the terminal payoff event; its endpoints are log-prices, not prices. Evaluate F0 and F1 at a0 and a1, form J0 and J1, and then apply the payoff-specific pricing formula. J0 and J1 are not discounted; apply $\exp (-rT)$ once in that pricing formula.

An empty interval contributes zero. Use $N(-\infty )=0$ and $N(\infty )=1$. For gap barriers, select the interval with the trigger strike and combine moments with the payment strike. Evaluate extreme normal tails and differences carefully to avoid cancellation or overflow.

## Rebates and Independent Verification

**Rebate payment timing.** R is the rebate amount. The expressions below give the rebate component only; add it to the contract's no-rebate payoff value as appropriate. A knock-out rebate paid at touching time has value
**Touch-time rebate value**

$$
R\mathbb E[e^{-r\tau_H}\mathbf1_{\tau_H\le T}].
$$

If paid at maturity instead, its value is
**Rebate paid at expiry after a hit**

$$
Re^{-rT}\mathbb Q(\tau_H\le T).
$$

A maturity-paid knock-in rebate for nonactivation has value
**Rebate paid at expiry if never hit**

$$
Re^{-rT}\mathbb Q(\tau_H>T).
$$

Payment timing determines the discounting; do not substitute one rebate convention for another. The following subsection supplies the continuous-monitoring computation.

### Computing continuous-monitoring rebates

Use the definitions and assumptions in [Shared Foundations](#shared-foundations), together with the initial barrier-status rules in [Shared Barrier Mathematics](#shared-barrier-mathematics). The formulas here apply to a positive, initially unbreached barrier, constant parameters, continuous monitoring, and positive volatility and maturity. Define the positive log-distance and drift toward the barrier by
**Barrier distance and drift toward the barrier**

$$
a=|\ln(H/S)|,\qquad
\theta=\begin{cases}\nu,&H>S\quad\text{(upper barrier)},\\-\nu,&H<S\quad\text{(lower barrier)}.\end{cases}
$$

Here a is the first-passage distance, local to this section; it is not a log-price mean used in F0 or F1. Reflecting the process for a lower barrier converts both cases to hitting the positive level a. Its first-passage density is
**First-passage-time density**

$$
f_\tau(t)=\frac{a}{\sigma\sqrt{2\pi t^3}}
\exp\left[-\frac{(a-\theta t)^2}{2\sigma^2t}\right],\quad t>0.
$$

Thus the at-touch rebate value can be evaluated by quadrature:
**Touch-time rebate as a discounted density integral**

$$
V_{rebate,hit}=R\int_0^T e^{-rt}f_\tau(t)\,dt.
$$

For a closed form, define $\kappa=\sqrt{\theta^2+2r\sigma^2}$, provided its radicand is nonnegative. Expanding the density exponent gives
**Exponent rearrangement for the rebate integral**

$$
-rt-\frac{(a-\theta t)^2}{2\sigma^2t}
=\frac{a\theta}{\sigma^2}-\frac{a^2}{2\sigma^2t}
-\frac{\kappa^2t}{2\sigma^2}.
$$

Integrating, or differentiating the expression below with respect to T, yields
**Closed-form touch-time rebate**

$$
V_{rebate,hit}=R\left[
 e^{a(\theta-\kappa)/\sigma^2}N\left(\frac{\kappa T-a}{\sigma\sqrt T}\right)
+e^{a(\theta+\kappa)/\sigma^2}N\left(\frac{-\kappa T-a}{\sigma\sqrt T}\right)
\right].
$$

This already includes discounting to the random hit time: do not multiply it by $\exp (-rT)$. If negative rates make the radicand negative, use the real-valued integral instead of this square-root form. For extreme parameters, evaluate exponential-times-normal-tail products in log space.

The undiscounted probability of a touch by T is
**Barrier-hit probability by expiry**

$$
p_T=N\left(\frac{\theta T-a}{\sigma\sqrt T}\right)
+e^{2a\theta/\sigma^2}N\left(\frac{-\theta T-a}{\sigma\sqrt T}\right).
$$

Therefore a knock-out rebate paid at maturity is $Re^{-rT}p_T$, and a knock-in nonactivation rebate paid at maturity is $Re^{-rT}(1-p_T)$. These formulas concern the rebate component only. At $r = 0$, the at-touch value reduces to R $p_{T}$. For $R \ge  0$ and $r \ge  0$, it lies between $Re^{-rT}p_T$ and $Rp_T$.

The at-touch expression is equivalent to the Rubinstein–Reiner F component implemented in [QuantLib's analytic barrier engine](https://github.com/lballabio/QuantLib/blob/master/ql/pricingengines/barrier/analyticbarrierengine.cpp); the positive-distance notation above makes the lower/upper drift mapping explicit.

This check uses a different calculation path from the closed-form moments, but shares their Black–Scholes assumptions. First read [Shared Barrier Mathematics](#shared-barrier-mathematics) for x, h, w, and $p_{\mathrm{free}}$. Simulate terminal prices from Shared Foundations. For each terminal sample, calculate the probability of a barrier touch conditional on that endpoint. When both endpoints are on the safe side, this probability is
**Conditional bridge hit probability**

$$
p_{hit}=\frac{wp_{free}(\ln S_T\mid 2h-x)}{p_{free}(\ln S_T\mid x)}
=\exp\left[-\frac{2\ln(S/H)\ln(S_T/H)}{\sigma^2T}\right].
$$

If either endpoint touches or crosses the barrier, set $p_{\mathrm{hit}} = 1$ instead of using the exponential formula. For every sample, evaluate the terminal payoff $\Pi(S_T)$, multiply it by $1-p_{\mathrm{hit}}$ for a knock-out or $p_{\mathrm{hit}}$ for a knock-in, and discount. Averaging these values estimates, with no rebates,
**Bridge-weighted knock-out value**

$$
V_{KO}=e^{-rT}\mathbb E[\Pi(S_T)(1-p_{hit})],\quad
$$

**Bridge-weighted knock-in value**

$$
V_{KI}=e^{-rT}\mathbb E[\Pi(S_T)p_{hit}].
$$

Estimate sampling error from the discounted weighted payoffs. For independent samples, standard error is their sample standard deviation divided by $\sqrt{\text{sample count}}$. Checking the barrier only at the specified monitoring dates, without bridge probabilities, prices a discretely monitored contract. By contrast, sampling only a terminal price and weighting its payoff by the bridge survival probability above accounts for continuous monitoring under this model. When simulation already checks the actual discrete monitoring dates, do not add Brownian-bridge crossings between them. The BGK approximation below instead maps a continuous closed form to a discretely monitored contract.

## Consistency checks

Contract terms determine parameter meanings. Price, variance, probability and position value are different quantities. For a sensitivity check, perturb only the intended input and keep the others fixed.

When a check fails, inspect its design, contract interpretation, parameter mapping, branch selection, and numerical stability. An identity satisfied by construction can detect inconsistency but cannot independently certify its components.

## Discrete Monitoring and the BGK Approximation

Use the definitions and assumptions in [Shared Foundations](#shared-foundations). For equally spaced observations with interval $\Delta t$ measured in years, consistent with annualized volatility, the Broadie–Glasserman–Kou approximation uses the continuous-barrier formula with
**Discrete-monitoring correction for an upper barrier**

$$
H_{adj}=H\exp(+\beta\sigma\sqrt{\Delta t})\quad\text{for an upper barrier}
$$

**Discrete-monitoring correction for a lower barrier and its constant**

$$
H_{adj}=H\exp(-\beta\sigma\sqrt{\Delta t})\quad\text{for a lower barrier},
\qquad \beta=-\frac{\zeta(1/2)}{\sqrt{2\pi}}\approx0.5826.
$$

Here $\zeta$ is the Riemann $\zeta$ function. The shift moves the barrier away from spot. Apply it only when using a continuous formula to approximate discrete monitoring; do not shift the barrier in a simulation that already checks the actual observation dates. This is an asymptotic approximation, not an exact identity. Accuracy can deteriorate near the barrier or with coarse monitoring. Irregular observation schedules require separate treatment. Follow a specified algorithm rather than silently substituting this approximation.

Source: [Broadie, Glasserman and Kou (1997), A Continuity Correction for Discrete Barrier Options](https://business.columbia.edu/sites/default/files-efs/pubfiles/1845/bgk_mf.pdf).

## Sources

Foundational references: Black and Scholes (1973), *The Pricing of Options and Corporate Liabilities*; Merton (1973), *Theory of Rational Option Pricing*. Implementation cross-reference: [QuantLib analytic binary barrier engine](https://github.com/lballabio/QuantLib/blob/master/ql/pricingengines/barrier/analyticbinarybarrierengine.cpp). Use model and contract assumptions to determine applicability; availability of a library does not establish that its defaults match a contract.
