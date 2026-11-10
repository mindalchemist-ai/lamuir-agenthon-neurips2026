# Rate caplets and floorlets: fixing, payment and Black pricing

Use this reference for European options on a single rate fixing and sums of such options into caps or floors. It distinguishes the option's uncertainty horizon from its payment date and accrual fraction. It does not value an option on a compounded realized rate by simply treating that payoff as a single term-rate fixing.

## 1. Shared Foundations

Map notation by meaning and units, following explicit contract conventions. Let v be today, $T_{f}$ the fixing date, $T_{p}$ the payment date, $\tau$ the year fraction from v to $T_{f}$, and $\delta >0$ the underlying coupon accrual fraction. The payment discount factor is $D=\operatorname{P}_{d}(v,T_{p})>0$, not a discount factor to $T_{f}$. $N\ge 0$ is notional, K the strike rate and F the projected fixing under the payment-date pricing measure. Rates are decimals. Values below are for a long option; a short position reverses their sign.

For an unfixed positive rate, Black's model assumes a lognormal fixing with total log variance w. Constant annual volatility $\sigma$ gives:

$$
w = \sigma ^{2}\cdot \tau
$$

The rate at fixing, expressed using a standard normal Z under that pricing measure, is:

$$
L_{\mathrm{fix}} = F\cdot \exp (-w/2+\sqrt{w}\cdot Z)
$$

This construction has mean F. A projection-curve quantity requires appropriate calibration/measure interpretation before being treated as F; do not add a second spot-to-forward drift to it.

## 2. Payoffs and pricing

The caplet pays the excess of the fixed rate over strike at $T_{p}$.

$$
\;\text{payoff}\;_{\mathrm{caplet}} = N\cdot \delta \cdot \max (L_{\mathrm{fix}}-K,0)
$$

The floorlet pays the shortfall below strike at the same date.

$$
\;\text{payoff}\;_{\mathrm{floorlet}} = N\cdot \delta \cdot \max (K-L_{\mathrm{fix}},0)
$$

For $F>0, K>0$ and $w>0$, the normal-CDF arguments are:

$$
\begin{gathered}
\mathrm{d1} = (\ln (F/K)+w/2)/\sqrt{w} \\
\mathrm{d2} = \mathrm{d1}-\sqrt{w}
\end{gathered}
$$

Writing $\Phi$ for the standard normal CDF, integration of the positive payoff gives the caplet value [1].

$$
V_{\mathrm{caplet}} = N\cdot \delta \cdot D\cdot (F\cdot \Phi (\mathrm{d1})-K\cdot \Phi (\mathrm{d2}))
$$

The floorlet value follows from the complementary payoff region [1].

$$
V_{\mathrm{floorlet}} = N\cdot \delta \cdot D\cdot (K\cdot \Phi (-\mathrm{d2})-F\cdot \Phi (-\mathrm{d1}))
$$

Total variance w already includes the time horizon. It must not receive a second multiplication by $\tau$. Annual volatility is dimensionless per square root year, whereas $\delta$ scales the coupon amount and may use a different day-count basis.

## 3. Known fixings and degenerate cases

If the fixing is known, use the observed contractual rate $L_{\mathrm{known}}$ even if the forward curve has moved. Payment can still be in the future.

$$
V_{\mathrm{caplet},\mathrm{known}} = N\cdot \delta \cdot D\cdot \max (L_{\mathrm{known}}-K,0)
$$

The known floorlet is:

$$
V_{\mathrm{floorlet},\mathrm{known}} = N\cdot \delta \cdot D\cdot \max (K-L_{\mathrm{known}},0)
$$

For an unfixed rate with zero total variance, the same deterministic expressions apply with F in place of $L_{\mathrm{known}}$. At $K=0$ and nonnegative lognormal $L_{\mathrm{fix}}$, the caplet value is $N\delta DF$ and the floorlet is zero; negative strike extends this linear caplet branch. A deterministic zero forward can be handled by its deterministic payoff, but an unshifted lognormal model cannot represent a genuinely negative rate distribution.

A specified shifted-lognormal model applies Black to F+s and K+s, with positive shifted inputs and shift s; the payoff difference is unchanged. A normal-volatility model instead uses a different distribution and volatility units. Substituting an absolute value into $\ln (F/K)$ does not repair an invalid lognormal model.

## 4. Portfolios and checks

A cap is the sum of its component caplets, with each component's own accrual, fixing, payment, notional and volatility. A floor is the corresponding sum of floorlets. A quoted cap volatility reprices a cap as a whole and is not generally a term structure of individual caplet volatilities; stripping is a separate calibration problem [1].

Pointwise payoff subtraction gives exact caplet-floorlet parity with consistent inputs:

$$
V_{\mathrm{caplet}}-V_{\mathrm{floorlet}} = N\cdot \delta \cdot D\cdot (F-K)
$$

For known fixings replace F by the known rate. Summing this identity gives the corresponding floating-minus-fixed coupon stream, without inventing principal exchanges. A mixed portfolio of known and future fixings uses the correct rate for each component.

When $F=K>0$, the Black caplet simplifies to:

$$
V_{\mathrm{caplet},\mathrm{ATM}} = N\cdot \delta \cdot D\cdot F\cdot (2\cdot \Phi (\sqrt{w}/2)-1)
$$

Parity, the zero-variance limit and positive homogeneity in N are independent checks on signs and scaling. Under the positive-rate model, the caplet lies between zero and $N\delta DF$; the floorlet lies between zero and $N\delta DK$ for $K\ge 0$. These bounds are not the bounds of a normal model with negative rates.

## References

[1] OpenGamma quantitative research, Eight ways to strip your caplets: An introduction to caplet stripping, rate-option definitions and Black caplet valuation. [Author technical paper](https://quant.opengamma.io/Caplet-Stripping-OpenGamma.pdf). Black's forward-option framework originates in Fischer Black (1976), The Pricing of Commodity Contracts, Journal of Financial Economics 3, 167–179; [bibliographic record](https://doi.org/10.1016/0304-405X(76)90024-6).
