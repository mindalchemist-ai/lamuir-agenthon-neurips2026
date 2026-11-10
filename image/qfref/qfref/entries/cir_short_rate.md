# CIR short-rate transitions and discount bonds

Use this reference for a nonnegative square-root rate process, exact discrete transition likelihood and affine zero-coupon valuation. Historical estimation and pricing use different probability measures unless a modeling assumption explicitly equates them. A fitted historical rate process is not automatically a calibrated market discount curve.

Map notation, calendar-time increments, rate scale and probability measure to the stated model. If definitions conflict, distinguish the supplied convention from the mathematical model rather than silently mixing them. All formulas below use consistent time units and decimal rates; they do not support negative observations without an explicit model extension.

## 1. Process and moments

Here r is the short rate; $\kappa  > 0$ is reversion speed, $\theta  > 0$ the long-run rate, $\sigma  > 0$ the square-root diffusion coefficient, and W standard Brownian motion under the chosen measure.

CIR dynamics:

$$
\mathrm{d}r = \kappa \cdot (\theta -r)\cdot \mathrm{d}t + \sigma \cdot \sqrt{r}\cdot \mathrm{d}W
$$

For annual time, $\kappa$ has inverse-year units. Rescaling a rate $r_{\mathrm{new}} = a\cdot r$ changes $\theta$ to $a\theta$ and $\sigma$ to $\sqrt{a}\cdot \sigma$, while $\kappa$ is unchanged. Rescaling percentages is not the same as changing the clock.

Conditional mean over a positive interval h, given current rate r:

$$
\operatorname{mean}_{h} = \theta  + (r-\theta )\cdot \exp (-\kappa \cdot h)
$$

Conditional variance over the same interval:

$$
\mathrm{var}_{h} = r\cdot \sigma ^{2}\cdot \exp (-\kappa \cdot h)\cdot (1-\exp (-\kappa \cdot h))/\kappa  + \theta \cdot \sigma ^{2}\cdot (1-\exp (-\kappa \cdot h))^{2}/(2\cdot \kappa )
$$

These follow from the first two moment equations. They provide a scale and time-decay check independent of a density parameterization.

Feller ratio for the zero boundary:

$$
\mathrm{Feller}_{\mathrm{ratio}} = 2\cdot \kappa \cdot \theta /\sigma ^{2}
$$

For r initially positive, ratio >= 1 makes zero inaccessible. A smaller positive ratio permits hitting zero but does not make the exact process negative; the ordinary Euler approximation may nevertheless go negative. Failure of this condition does not invalidate the positive-parameter transition law.

## 2. Exact transition and likelihood

For current rate $r \ge  0$ and interval $h > 0$, define a positive scale $s_{h}$, degrees of freedom $\nu$, and noncentrality $\lambda _{h}$ [1,2]. The noncentrality is a dimensionless parameter, not a standard deviation.

Transition scale:

$$
s_{h} = \sigma ^{2}\cdot (1-\exp (-\kappa \cdot h))/(4\cdot \kappa )
$$

Degrees of freedom:

$$
\nu  = 4\cdot \kappa \cdot \theta /\sigma ^{2}
$$

Noncentrality, including mean-reversion decay of the initial state:

$$
\lambda _{h} = \exp (-\kappa \cdot h)\cdot r/s_{h}
$$

Conditional next rate as a scaled noncentral $\chi$-square random variable:

$$
\begin{gathered}
r_{\mathrm{next}} = s_{h} \cdot  Y \\
Y \sim \text{noncentral }\chi^2(\nu,\lambda_h)
\end{gathered}
$$

If $f_{\mathrm{ncx2}}$ is the density of Y, changing variables gives the rate density. The Jacobian is parameter-dependent and belongs in estimation.

Conditional log density for a positive observed rate x:

$$
\ln p(x \vert  r,h) = \ln f_{\mathrm{ncx2}}(x/s_{h}; \nu ,\lambda _{h}) - \log (s_{h})
$$

Conditional log likelihood of successive observed rates $r_{i}$ at times $t_{i}$:

$$
\mathrm{LL} = \sum _{i=1}^{n} \ln p(r_{i} \vert  r_{i-1}, t_{i}-t_{i-1})
$$

Time increments refer to consecutive retained observations. Equal business-day steps and elapsed calendar fractions are different models of the observation clock. A missing observation does not itself create an additional observed transition. Direct evaluation of a small density can underflow; its log-density is the appropriate numerical quantity. Exact or rounded zeros need an explicit observation/boundary treatment: assigning a tiny positive replacement changes the likelihood.

The noncentral $\chi$-square mean and variance imply the moment checks:

$$
\operatorname{E}[r_{\mathrm{next}}] = s_{h}\cdot (\nu +\lambda _{h})
$$

$$
\operatorname{Var}[r_{\mathrm{next}}] = 2\cdot s_{h}^{2}\cdot (\nu +2\cdot \lambda _{h})
$$

As h tends to zero, the conditional mean tends to r and variance tends to zero. At $r=0$ the noncentrality vanishes, leaving a scaled central $\chi$-square law.

## Transition-parameterization consistency

Some density expressions use $c_h=1/(2s_h)$ rather than the scale $s_h$. With the transition definitions above, the equivalent density is:

$$
p(x\mid r,h)=2c_h\,f_{\mathrm{ncx2}}\left(2c_hx;\nu,2c_he^{-\kappa h}r\right)
$$

The initial state in noncentrality decays by $e^{-\kappa h}$, and the density includes its transformation Jacobian. A scale taken from one convention and a noncentrality from another need not describe CIR. An independent short-interval check is:

$$
\mathrm{E}[r_{t+h}\mid r_t=r]=r+\kappa(\theta-r)h+O(h^2),\qquad
\operatorname{Var}(r_{t+h}\mid r_t=r)=\sigma^2rh+O(h^2)
$$

At $r=0$ the leading variance term is zero and the next order matters. These checks distinguish a formula's stochastic meaning without selecting an unspecified calibration convention. If two supplied transition formulas disagree, keep their parameterizations separate and identify the conflict; the standard process does not make contradictory formulas equal.

## 3. Pricing measure and affine bond

For bond pricing, $\kappa$ and $\theta$ in this section are risk-neutral parameters. Historical likelihood usually estimates physical-measure parameters. Equating the two sets is an additional assumption, not a consequence of maximum likelihood. The original CIR paper includes a risk-premium adjustment; it is absorbed into the risk-neutral coefficients here [1].

A claim paying one unit after remaining maturity $\tau$ has risk-neutral value:

$$
\operatorname{P}(r,\tau ) = \operatorname{E}_{Q}[\exp (-\int _{0}^{\tau} r_{s} \mathrm{d}s) \vert  r_{0}=r]
$$

Affine representation:

$$
\operatorname{P}(r,\tau ) = \exp (a(\tau ) - B(\tau )\cdot r)
$$

For $\sigma  > 0$, the following scaled-exponential form avoids exponentials growing with maturity.

Auxiliary decay speed:

$$
\gamma  = \sqrt{\kappa ^{2}+2\cdot \sigma ^{2}}
$$

Decaying exponential and denominator:

$$
\operatorname{E}_{\tau} = \exp (-\gamma \cdot \tau )
$$

$$
H_{\tau} = (\gamma +\kappa )\cdot (1-\operatorname{E}_{\tau}) + 2\cdot \gamma \cdot \operatorname{E}_{\tau}
$$

Rate loading in the affine price:

$$
B(\tau ) = 2\cdot (1-\operatorname{E}_{\tau})/H_{\tau}
$$

Logarithm of the affine prefactor, $a(\tau)=\ln A(\tau)$:

$$
a(\tau ) = (2\cdot \kappa \cdot \theta /\sigma ^{2})\cdot (\ln (2\cdot \gamma /H_{\tau}) + (\kappa -\gamma )\cdot \tau /2)
$$

For very small $\tau$, accurate evaluation of $1-\exp (-\gamma \cdot \tau )$ matters. At $\tau =0, B=0, a=0$ and $\operatorname{P}=1$.

The Riccati equations provide an independent characterization; primes mean derivatives in remaining maturity:

$$
B' = 1-\kappa \cdot B-0.5\cdot \sigma ^{2}\cdot B^{2}
$$

$$
(a)' = -\kappa \cdot \theta \cdot B
$$

Their initial conditions are $B(0)=0$ and $a(0)=0$. The negative quadratic term belongs in B', not its positive version.

For $\sigma =0$ the path is deterministic and division by $\sigma^{2}$ is unnecessary. The integrated short rate is:

$$
I(\tau ) = \theta \cdot \tau  + (r-\theta )\cdot (1-\exp (-\kappa \cdot \tau ))/\kappa
$$

Deterministic-limit bond price:

$$
\operatorname{P}(r,\tau ) = \exp (-I(\tau ))
$$

## 4. Yield, forward and scope checks

Continuous zero yield for $\tau  > 0$:

$$
y(\tau ) = -\ln (\operatorname{P}(r,\tau ))/\tau
$$

The exponent $-\ln (\operatorname{P})$ equals $\tau y$, not the annualized yield. An observed par or coupon-equivalent yield is not inherently a zero yield.

Continuous average forward over $a < b$:

$$
f_{\mathrm{avg}}(a,b) = (\ln (\operatorname{P}(r,a))-\ln (\operatorname{P}(r,b)))/(b-a)
$$

Instantaneous forward at remaining maturity $\tau$:

$$
f_{\mathrm{inst}}(\tau ) = -(a)'(\tau ) + B'(\tau )\cdot r
$$

A finite interval average is not the derivative at either endpoint. With nonnegative paths, $0<\operatorname{P}\le 1$ and P is nonincreasing in maturity; nonnegative B makes price nonincreasing in the current short rate. At vanishing maturity y and $f_{\mathrm{inst}}$ approach r. These bounds are model properties, not statements about all real-world yield curves.

## References

[1] Cox, Ingersoll and Ross (1985), A Theory of the Term Structure of Interest Rates, Econometrica 53, 385–407, equations (18)–(19) and (23). [Original article scan](https://roycheng.cn/files/papers/interestRate/paper_Cox%26Ingersoll%26Ross_1985.pdf). Notation here uses risk-neutral coefficients directly for valuation.

[2] Malham and Wiese, Chi-square simulation of the CIR process and the Heston model, section on CIR simulation: scaled noncentral $\chi$-square transition. [Author manuscript](https://arxiv.org/pdf/0802.4411).
