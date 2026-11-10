# FX options: discounting, delta conventions and smile wings

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description. Explicit input conventions override market shorthand; a currency-pair name alone does not establish a delta convention.

## Topic: Option value and dates

**Purpose:** Price a European currency option from forward, volatility and discount factors.

**When to use:** European currency options. Map the quote direction, premium currency, notional, expiry and delivery separately.

**How to implement:** $S$ is instantaneous domestic currency per foreign unit, $K$ the same quote, $T_e>0$ time to expiry, $T_d$ delivery time. $D_d,D_f$ discount to delivery under the specified deterministic currency curves, with compatible collateral treatment. $\sigma>0$ is annualized volatility, $\phi=1$ for a call on foreign currency, $\phi=-1$ for a put. $N$ is the standard normal CDF, $n$ its density.

$$F=S\frac{D_f}{D_d},\qquad a=\sigma\sqrt{T_e}$$

$$d_1=\frac{\log(F/K)}a+\frac a2,\qquad d_2=d_1-a$$

$$V_\phi=\phi D_d\{F N(\phi d_1)-K N(\phi d_2)\}$$

$V_\phi$ is the domestic value per foreign notional.

**Limitations and cautions:**

1. A quoted spot with a future spot value date is not instantaneous $S$. Forward construction uses discount-factor ratios from that value date, while present value discounts from valuation. Adjust dates consistently before applying derivatives.
2. Stochastic rates, FX/reset convexity and collateral optionality require additional modelling.
3. In a Garman–Kohlhagen setting the drift is $r_{\mathrm{terms}}-r_{\mathrm{base}}$.

**Double check:**

1. Total volatility is $\sigma\sqrt{T_e}$ everywhere $a$ appears.

## Topic: Delta conventions

**Purpose:** Compute the right one of four delta conventions.

**When to use:** A delta is requested, or a delta quote must be interpreted.

**How to implement:** Holding curves and volatility fixed, spot delta differentiates domestic value with respect to $S$:

$$\Delta_s=\phi D_fN(\phi d_1)$$

The usual unadjusted forward delta quotation divides spot delta by $D_f$:

$$\Delta_f=\phi N(\phi d_1)$$

It is an undiscounted forward-delta convention; the literal derivative $\partial V/\partial F$ is $D_d\Delta_f$. Unadjusted forward delta carries no discount factor; spot delta carries $e^{-r_{\mathrm{base}}T}$.

For the standard present-valued foreign-premium hedge convention, subtract premium measured in foreign units:

$$\Delta_{s,\mathrm{pa}}=\Delta_s-\frac VS=\phi D_f\frac KF N(\phi d_2)$$

Its forward-delta counterpart removes the foreign discount factor:

$$\Delta_{f,\mathrm{pa}}=\phi\frac KF N(\phi d_2)$$

Pips delta is the ordinary unadjusted delta per unit of base notional, a fraction, not scaled by the point multiplier.

**Limitations and cautions:**

1. A later premium date requires its present value before conversion.
2. A premium-adjusted hedge is not an extra adjustment to option value.

**Double check:**

1. For otherwise identical call/put contracts, ordinary spot-delta difference is $D_f$; premium-adjusted spot-delta difference is $D_fK/F$.

## Topic: Strike from delta

**Purpose:** Invert a delta quote to a strike.

**When to use:** A strike is needed from a delta target, unadjusted or premium-adjusted.

**How to implement:** For a signed unadjusted forward target $\delta_f$ with $0<\phi\delta_f<1$:

$$K=F\exp\{-\phi a N^{-1}(\phi\delta_f)+a^2/2\}$$

For an unadjusted spot target use $\delta_f=\delta_s/D_f$. The inverse-normal term is multiplied by the total volatility $\sigma\sqrt{T}$, not by $\sigma$.

Premium-adjusted delta has no closed-form inverse. At a fixed quoted volatility, premium-adjusted call delta can have two roots. The usual wing convention takes the larger-strike root, to the right of its delta maximum. Find the peak strike from $aN(d_2)=n(d_2)$, then bracket the target root between that strike and the unadjusted-delta strike for the same target and spot/forward convention. Solve with a bracketing root finder.

**Limitations and cautions:**

1. Check that the target lies below the maximum. Puts are monotone at fixed volatility.
2. If volatility itself varies with strike, solve under the specified smile construction rather than assuming the fixed-volatility derivative still locates the peak.
3. Put targets are normally negative. Absolute-delta quotes first require the call/put sign.
4. A strike on a bracket end, or a premium near zero, means the root was not found.

**Double check:**

1. Bracket ends give opposite signs before solving.
2. Recompute the delta at the root and require it to match the target (with the put formula for puts).

## Topic: Smile wings from risk reversal and butterfly

**Purpose:** Build call-wing and put-wing volatilities and ATM strikes.

**When to use:** A smile is quoted by ATM, risk reversal and butterfly.

**How to implement:** If risk reversal means call-wing volatility minus put-wing volatility, and butterfly is the arithmetic wing average minus ATM volatility:

$$\sigma_c=\sigma_{\mathrm{ATM}}+\sigma_{\mathrm{BF}}+\frac12\sigma_{\mathrm{RR}},\qquad
\sigma_p=\sigma_{\mathrm{ATM}}+\sigma_{\mathrm{BF}}-\frac12\sigma_{\mathrm{RR}}$$

Forward ATM means $K=F$. An unadjusted delta-neutral straddle gives $K=F\exp(a^2/2)$; its premium-adjusted counterpart gives $K=F\exp(-a^2/2)$ under these assumptions.

**Limitations and cautions:**

1. A market-strangle premium quote is a different definition of butterfly and need not satisfy this direct split.

**Double check:**

1. $\sigma_c-\sigma_p=\sigma_{\mathrm{RR}}$ and $(\sigma_c+\sigma_p)/2-\sigma_{\mathrm{ATM}}=\sigma_{\mathrm{BF}}$.

## Topic: Premium and Greek units

**Purpose:** Report premium, Gamma and Vega in the right units.

**When to use:** Premium amounts or Greeks are requested per notional.

**How to implement:** For foreign notional $Q_f$, domestic premium is $Q_fV$ and its present foreign equivalent is $Q_fV/S$. A price per domestic notional uses its explicitly specified denominator. At fixed strike and curves, ordinary spot Gamma and Vega per foreign notional:

$$\Gamma_s=\frac{D_fn(d_1)}{S\sigma\sqrt{T_e}},\qquad
\mathrm{Vega}=D_dF n(d_1)\sqrt{T_e}$$

Vega is per unit decimal volatility; per percentage-point Vega is $0.01$ times this value.

**Limitations and cautions:**

1. Pips and percentage premium are not interchangeable.
2. Sticky-strike and sticky-delta smile sensitivities are different: smile movement can add chain-rule terms.

**Double check:**

1. The unit (decimal versus percentage-point, foreign versus domestic) matches the field name.
