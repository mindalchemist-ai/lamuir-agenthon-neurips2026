# Down-and-out barrier calls, finite-difference Greeks, principal-protected notes and their delta-based risk

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, monitoring rule, bump, contract term, horizon or risk method, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Pricing a down-and-out call (barrier below the strike)

**Purpose:** Price a European call that is cancelled if the underlying touches a barrier $B$ below the spot before expiry.

**When to use:** Continuous monitoring, $B\le K$, no rebate. A barrier above the strike, a rebate or an up barrier needs other formulas; discrete monitoring needs the barrier shift in Implementation tips.

**How to implement:**

Step 1: Inputs, printed with units: spot $S_0>B$, strike $K$, barrier $B$, continuous rate $r$, dividend yield $q$ (zero if none), maturity $T$ in years, annual volatility $\sigma$.

Step 2: If $S_0\le B$ the option is already knocked out and worth $0$.

Step 3: Reiner-Rubinstein: the vanilla Black-Scholes call minus the down-and-in call,

$$C_{do}=C_{BS}-C_{di},\qquad C_{di}=S_0e^{-qT}\Big(\frac{B}{S_0}\Big)^{2\lambda}N(y)-Ke^{-rT}\Big(\frac{B}{S_0}\Big)^{2\lambda-2}N\big(y-\sigma\sqrt T\big),$$

with $\lambda=\frac{r-q+\sigma^2/2}{\sigma^2}$ and $y=\frac{\ln\!\big(B^2/(S_0K)\big)}{\sigma\sqrt T}+\lambda\sigma\sqrt T$.

**Implementation tips:**

1. Discrete monitoring with step $\Delta t$: shift a down barrier to $Be^{-0.5826\sigma\sqrt{\Delta t}}$ (Broadie-Glasserman-Kou) and use the continuous formula.
2. Write one pricing function and reuse it for every Greek and every scenario.

**Limitations and cautions:**

1. A daily volatility used as annual is about 16 times too small.

**Double check:**

1. $0\le C_{do}\le C_{BS}$ at the same inputs; $C_{do}\to0$ as $S_0\downarrow B$; $C_{do}\to C_{BS}$ as $B\to0$.

## Topic 2: Greeks by finite differences

**Purpose:** Delta, gamma and vega of any option from its pricing function.

**When to use:** The task asks for Greeks by bumping, or the product has no simple closed-form Greeks.

**How to implement:**

Step 1: Read the bump convention: spot bumps relative ($\Delta S=hS_0$) or absolute; volatility bumps absolute (volatility points) or relative; central or one-sided. When the task gives none, choose one and state it.

Step 2: Central differences with the same pricing function $V$:

1. Delta: $\frac{V(S+\Delta S)-V(S-\Delta S)}{2\Delta S}$.
2. Gamma: $\frac{V(S+\Delta S)-2V(S)+V(S-\Delta S)}{\Delta S^2}$.
3. Vega: $\frac{V(\sigma+\Delta\sigma)-V(\sigma-\Delta\sigma)}{2\Delta\sigma}$.

**Limitations and cautions:**

1. Near a barrier the price has a kink; a spot bump that crosses $B$ mixes knocked-out and live values. Keep $S_0-\Delta S>B$ or use a one-sided difference, and state it.

**Double check:**

1. Halving the bump changes the Greeks only slightly; a large change points to a kink or a bump that is too small for the price precision.

## Topic 3: A principal-protected note as a bond plus options

**Purpose:** Value a note that repays a principal $N$ at maturity and adds participation in an option payoff, and find its breakeven volatility.

**When to use:** The task describes a note, certificate or structured product with capital protection and an option-linked coupon.

**How to implement:**

Step 1: Inputs: principal, participation rate $p$, issue price, maturity, rate, and the option's terms.

Step 2: Bond part $=Ne^{-rT}$ (or the task's compounding). Option part $=$ number of options $\times$ option price. Fair value $=$ bond part $+$ option part.

Step 3: Number of options, from the payoff the task writes: $Np/S_0$ when the payoff is $pN\max(S_T/S_0-1,0)$ (participation in the percentage return), $Np/K$ when options are counted on the strike, or a stated count.

Step 4: Breakeven volatility: the volatility at which fair value equals the issue price; solve with a bracketing root finder (`scipy.optimize.brentq`) after checking the difference changes sign on the bracket.

Step 5: Note delta $=$ number of options $\times$ option delta; the bond part has no spot delta.

**Implementation tips:**

1. Issue price: a stated offer price, or par ($N$) when none is given.
2. Premium or markup: over fair value $(\text{issue}-\text{fair})/\text{fair}$, as a margin on the issue price $(\text{issue}-\text{fair})/\text{issue}$, or the investor's view $\text{fair}-\text{issue}$; the wording sets the denominator and sign.
3. Pricing volatility: the one the task names. For a GARCH volatility, two readings exist, the conditional volatility fitted for the final in-sample day or the one-step-ahead forecast; use the one the wording supports and state it.

**Limitations and cautions:**

1. A bracket on which the difference does not change sign means no breakeven volatility exists in that range; report it rather than widening blindly.

**Double check:**

1. Fair value lies between the bond part and the bond part plus the vanilla-option equivalent; at the breakeven volatility the fair value reprices to the issue price.

## Topic 4: Delta-based VaR and ES of a position

**Purpose:** One-period risk of an option or note position from its delta.

**When to use:** The task asks for a delta-normal VaR or ES; use delta-gamma or full revaluation when the task names it or convexity matters.

**How to implement:**

Step 1: Read the horizon, method, volatility source (annual divided by $\sqrt{\text{periods per year}}$, or a stated daily estimate) and confidence level $\alpha$.

Step 2: P&L standard deviation $\mathrm{sd}=|\Delta|\,S_0\,\sigma_{\mathrm{period}}$.

Step 3: Normal VaR $=z_\alpha\,\mathrm{sd}$ and normal ES $=\mathrm{sd}\,\phi(z_\alpha)/(1-\alpha)$, with $z_\alpha=\Phi^{-1}(\alpha)$.

**Limitations and cautions:**

1. Delta-normal ignores the bond's rate risk and the option's convexity; a longer horizon needs square-root-of-time scaling or simulation, as the task says.

**Double check:**

1. ES exceeds VaR and both are positive; at 99% the normal ES is about 1.15 times VaR. When the task writes its own ES formula, use it and print the ratio next to the normal one.
