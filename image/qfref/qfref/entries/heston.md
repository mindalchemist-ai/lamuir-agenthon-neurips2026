# Heston and multi-factor Heston: characteristic function, Gil-Pelaez and FFT pricing, surfaces, implied volatilities and checks

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Model and parameter units

**Purpose:** Read the model's parameters with the right meaning and units before any pricing.

**When to use:** Any Heston or multi-factor Heston task.

**Constraints:**

1. $\theta$ and $v_0$ are variances, not volatilities: a 20% long-run volatility is $\theta=0.04$; square a volatility the task gives as $v_0$.
2. Do not change parameters to satisfy the Feller condition unless the task says so.

**How to implement:**

Step 1: Risk-neutral dynamics, constant $r$ and $q$, European exercise, no jumps:

$$dS_t=(r-q)S_t\,dt+\sqrt{v_t}\,S_t\,dW_1$$

$$dv_t=\kappa(\theta-v_t)\,dt+\sigma_v\sqrt{v_t}\,dW_2,\qquad dW_1\,dW_2=\rho\,dt$$

Step 2: Parameters (print them with their units): $\kappa$ speed of mean reversion (per year); $\theta$ long-run variance; $\sigma_v$ volatility of variance (some papers write $\xi$, $\nu$, or $\lambda$); $\rho\in(-1,1)$, usually negative for equities; $v_0$ initial variance; $S_0$, $K$, $T$ in years, continuous $r$ and $q$. Papers reuse letters for different roles (one writes $\eta$ for $\theta$): map each by its position in the dynamics, not by its letter.

Step 3: If the task gives a price of volatility risk $\lambda$ (premium $\lambda v$), the risk-neutral parameters are $\kappa^*=\kappa+\lambda$ and $\theta^*=\kappa\theta/(\kappa+\lambda)$; most tasks give risk-neutral parameters directly.

**Limitations and cautions:**

1. When $2\kappa\theta<\sigma_v^2$ zero variance is reachable and reflecting; the model and the characteristic-function price stay valid, only simulation becomes harder.

**Double check:**

1. Print $\sqrt\theta$ and $\sqrt{v_0}$: they should look like volatilities (for example 0.1 to 0.6); values like 0.02 to 0.04 mean a variance was used as a volatility or the reverse.

## Topic 2: Characteristic function of $\ln S_T$ in the little-trap form

**Purpose:** Evaluate $\phi(u)$ stably for all maturities.

**When to use:** Every Fourier price (Topics 4 to 6).

**Constraints:**

1. Use the little-trap form below. The original Heston form ($b+d$, $1/g$, $e^{+dT}$) is algebraically equal but, with principal branches of the complex square root and logarithm, its logarithm jumps across the branch cut at longer maturities and misprices without any error.
2. Do not evaluate it at $\sigma_v=0$ (division by $\sigma_v^2$); use the Black-Scholes limit in Topic 8 instead.

**How to implement:**

Step 1: On whole arrays of $u$ (complex numpy arrays; `np.sqrt` and `np.log` give the principal branch):

$$b=\kappa-\rho\sigma_v iu,\qquad d=\sqrt{b^2+\sigma_v^2(iu+u^2)},\qquad g=\frac{b-d}{b+d},\qquad e=e^{-dT}$$

In numpy the term $iu+u^2$ is `1j*u + u**2`: the square is of $u$ itself, not of $iu$; `(1j*u)**2` equals $-u^2$ and breaks the martingale check below.

Step 2: Affine terms ($B$ is not yet multiplied by $v_0$):

$$C=\frac{\kappa\theta}{\sigma_v^2}\left[(b-d)T-2\ln\frac{1-ge}{1-g}\right],\qquad B=\frac{b-d}{\sigma_v^2}\cdot\frac{1-e}{1-ge}$$

Step 3: Characteristic function:

$$\phi(u)=\exp\left(iu(\ln S_0+(r-q)T)+C+v_0B\right)$$

**Limitations and cautions:**

1. At $u=-i$, $iu+u^2=0$; if $\kappa-\rho\sigma_v\le0$ the generic $g$ can have a zero denominator: use the known first moment there rather than declaring the model invalid.
2. The two moment checks below do not prove integration accuracy (Topic 4).

**Double check:**

1. $\phi(0)=1$ and $\phi(-i)=S_0e^{(r-q)T}$. At $u=-i$ the term $iu+u^2$ is exactly 0, so $d=b$, $g=0$ and $C=B=0$: print $iu+u^2$, $C$ and $B$ at $u=-i$. If $iu+u^2\neq0$ the discriminant was coded as $iu+(iu)^2$; if it is 0 but the check still fails, the spot and carry term or the sign of $r-q$ is wrong. Fix this before any pricing; it takes one cell.

## Topic 3: Several variance factors

**Purpose:** Combine independent Heston variance factors into one characteristic function.

**When to use:** The model has two or more variance factors, each with its own spot shock correlated only with its own variance.

**Constraints:**

1. The spot and carry term $iu(\ln S_0+(r-q)T)$ enters once, not once per factor; multiplying complete single-factor characteristic functions counts it twice.
2. Each factor's initial variance enters once: $B_m$ is multiplied by $v_{0,m}$ once; under the convention where the factor term already includes $v_{0,m}$, do not multiply again.

**How to implement:**

Step 1: For each factor $m$, compute $C_m$ and $B_m$ by Topic 2, Steps 1 and 2, with that factor's parameters.

Step 2: Combine:

$$\ln\phi(u)=iu(\ln S_0+(r-q)T)+\sum_m\left(C_m+B_mv_{0,m}\right)$$

Step 3: Short-maturity variance check at a fixed real $u\neq0$ over decreasing maturities: $-2\ln|\phi(u,T)|/(u^2T)\to\sum_m v_{0,m}$ as $T\to0$.

**Limitations and cautions:**

1. Adding the exponents assumes the factors are independent of each other; specified cross-factor dependence needs its own characteristic function.
2. References use the same letter (often $D$) for either convention; match definitions, not letters.

**Double check:**

1. $\phi(0)=1$, $\phi(-i)=S_0e^{(r-q)T}$ (fails when the spot term is counted per factor), and linearity in one factor's $v_0$: with $v_0$ set to $0,1,2$, $\phi_{2}\,\phi_{0}/\phi_{1}^2=1$ (fails when $v_0$ is multiplied in twice).

## Topic 4: Prices from the Gil-Pelaez probabilities

**Purpose:** Price European calls and puts from $\phi$ by two Fourier integrals.

**When to use:** Characteristic-function pricing with quadrature (the default; Topic 6 is the FFT alternative). For a whole grid, compute these in matrix form (Topic 5).

**Constraints:**

1. Each integral feeds its own probability: $P_1$ uses $\phi(u-i)/\phi(-i)$ (stock measure), $P_2$ uses $\phi(u)$ (risk-neutral).
2. When the task states the integration range, node count or subinterval limit for a method, use exactly those for that method; a comparison of two rules runs each on its own stated setting.
3. A price outside the no-arbitrage bounds is an error upstream: do not clip it to zero or leave the cell empty.

**How to implement:**

Step 1: Probabilities:

$$P_1=\frac12+\frac1\pi\int_0^{U}\mathrm{Re}\left[\frac{e^{-iu\ln K}\phi(u-i)}{iu\,\phi(-i)}\right]du$$

$$P_2=\frac12+\frac1\pi\int_0^{U}\mathrm{Re}\left[\frac{e^{-iu\ln K}\phi(u)}{iu}\right]du$$

The integrands have finite limits at $u\to0$: start just above 0, or use Gauss-Legendre nodes (`np.polynomial.legendre.leggauss` mapped to $[0,U]$), which skip 0.

Step 2: Prices:

$$C=S_0e^{-qT}P_1-Ke^{-rT}P_2,\qquad P=C-S_0e^{-qT}+Ke^{-rT}$$

Step 3: Truncation where the task leaves it open: choose $U$ where the integrand is negligible and confirm by doubling $U$. Decay is slower at short maturities and low variance; for one typical parameter set, an error below $10^{-6}$ needed $U\approx200$ at about a week, $100$ at a quarter and $50$ at two years.

Step 4: Choosing between two settings the task names: their difference is the same number for both and cannot rank them. Build a reference with `scipy.integrate.quad` on $[10^{-10},4U_{max}]$ (`limit=2000`, `epsabs=1e-12`, $U_{max}$ the larger of both limits), so it reaches beyond both rules; each rule's error is $\max|C_{rule}-C_{ref}|$ over the grid (`np.max(np.abs(...))`); keep the smaller, unless the task's own selection rule decides. If no reference is possible, prefer the longer range with more nodes, which has the smaller truncation error, and state why.

**Limitations and cautions:**

1. A slightly negative deep out-of-the-money price is truncation error of a short range; keep it visible for the comparison.
2. More nodes on the same interval do not test the omitted tail: vary the endpoint and the resolution separately.

**Double check:**

1. $0\le P_1,P_2\le1$ and $\max(S_0e^{-qT}-Ke^{-rT},0)\le C\le S_0e^{-qT}$ for every price; if not, check Topics 2 and 3 and the integration range before going on.

## Topic 5: Pricing a whole strike-by-maturity surface in matrix form

**Purpose:** Price every strike and maturity of a surface in seconds, without a pricing call per cell.

**When to use:** Prices, implied volatilities or Greeks on a grid of strikes and maturities, with any characteristic-function model. For a single option, Topic 4 directly.

**Constraints:**

1. Never loop over strike-maturity cells calling a one-option pricer: each call repeats the characteristic function and the quadrature, so a grid of a few hundred cells takes many minutes and exhausts the run's time.
2. Loop only over maturities (or over none); all strikes of a maturity are priced together.

**How to implement:**

Step 1: Quadrature nodes and weights once: $\mathbf u$ and $\mathbf w$ of length $N$.

Step 2: For each maturity $T_j$, evaluate the characteristic function once on the node vector: $\boldsymbol\phi_j=\phi(\mathbf u;T_j)$ and $\boldsymbol\phi^{(1)}_j=\phi(\mathbf u-i;T_j)/\phi(-i;T_j)$.

Step 3: For the strike vector $\mathbf k=\ln\mathbf K$ of length $M$, the $N\times M$ kernel matrix by an outer product, $\mathbf E=\exp(-i\,\mathbf u\,\mathbf k^{\top})$ (`np.outer`), and the integrand matrices, with the node vectors broadcast down the rows:

$$\mathbf A_1=\mathrm{Re}\left[\frac{\mathbf E\odot\boldsymbol\phi^{(1)}_j}{i\mathbf u}\right],\qquad\mathbf A_2=\mathrm{Re}\left[\frac{\mathbf E\odot\boldsymbol\phi_j}{i\mathbf u}\right]$$

Step 4: All probabilities of maturity $T_j$ by one matrix product with the weights (`w @ A` or `np.einsum`):

$$\mathbf P_1=\frac12+\frac1\pi\mathbf w^{\top}\mathbf A_1,\qquad\mathbf P_2=\frac12+\frac1\pi\mathbf w^{\top}\mathbf A_2$$

Step 5: Calls $\mathbf C=S_0e^{-qT_j}\mathbf P_1-\mathbf Ke^{-rT_j}\mathbf P_2$; puts from put-call parity, not by a second quadrature.

Step 6: Before the full surface, time Steps 2 to 5 for one maturity and print the estimate for all maturities.

**Limitations and cautions:**

1. An adaptive routine such as `scipy.integrate.quad` chooses its own nodes per integrand, so its work cannot be shared across strikes; where the task requires it, run it as specified, but only for the cells that need it.
2. Recompute the cached values whenever parameters, maturity or the rule change.

**Double check:**

1. Price one cell with Topic 4 directly and compare with the matrix result (agreement to about $10^{-10}$); then compare the surface at $N$ and $2N$ nodes. If either fails, the broadcast axes are swapped or the node mapping is wrong.

## Topic 6: Carr-Madan FFT

**Purpose:** Price calls on a whole log-strike grid with one fast Fourier transform.

**When to use:** The task names the FFT method, or many strikes per maturity are needed and quadrature is too slow.

**Constraints:**

1. The damping $\alpha>0$ must keep $E[S_T^{\alpha+1}]$ finite. Under Heston this moment can explode at a finite maturity (most easily with positive $\rho$, large $\sigma_v$, large $\alpha$, long $T$); past it $\phi(-(\alpha+1)i)$ is a wrong finite, possibly complex, number and the prices are wrong without any error.

**How to implement:**

Step 1: Damped transform, with $k=\ln K$:

$$\psi(v)=\frac{e^{-rT}\phi(v-(\alpha+1)i)}{\alpha^2+\alpha-v^2+i(2\alpha+1)v}$$

Step 2: Grids: $v_j=j\Delta v$ and $k_m=k_0+m\Delta k$, $j,m=0,\dots,N-1$, with $\Delta k\,\Delta v=2\pi/N$; center the log strikes, $k_0=\ln S_0-N\Delta k/2$.

Step 3: Simpson weights $w_0=\Delta v/3$ and $w_j=(\Delta v/3)(3+(-1)^{j+1})$.

Step 4: One FFT gives every log strike:

$$C(k_m)=\frac{e^{-\alpha k_m}}{\pi}\mathrm{Re}\left[\sum_j e^{-2\pi ijm/N}e^{-iv_jk_0}\psi(v_j)w_j\right]$$

with `np.fft.fft`; interpolate in $k$ to the task's strikes.

Step 5: A common choice is a quarter of the largest admissible $\alpha$ (for example $\alpha=1.5$, $\Delta v=0.25$, $N=4096$); a smaller $\alpha$ makes $\psi$ peak near $v=0$, so refine $\Delta v$ by raising $N$.

**Limitations and cautions:**

1. With an admissible $\alpha$, FFT and Gil-Pelaez agree to about $10^{-6}$; with an inadmissible one the error can be of the order of the spot.

**Double check:**

1. $\phi(-(\alpha+1)i)$ is real and positive, and a few strikes agree with Topic 4; if not, lower $\alpha$.

## Topic 7: Model prices to implied volatilities

**Purpose:** Invert model prices to Black-Scholes implied volatilities consistently.

**When to use:** An implied-volatility surface is reported from model prices.

**Constraints:**

1. Use the same spot, strike, expiry, rate and dividend yield in the model price and in the Black-Scholes price that inverts it; a zero-rate inversion is not the inversion at the task's rate.
2. Check every price against the bounds before inverting; a price outside them is a pricing error, never an implied volatility of zero (a price exactly at the lower bound may invert to zero volatility).

**How to implement:**

Step 1: On the price matrix $\mathbf C$ over the grid (matrices $\mathbf K,\mathbf T$ from `np.meshgrid`): lower bound $\mathbf L=\max(S_0e^{-q\mathbf T}-\mathbf Ke^{-r\mathbf T},0)$ (`np.maximum`), upper bound $\mathbf U=S_0e^{-q\mathbf T}$; flag cells where $\mathbf C$ is not finite (`np.isfinite`), $\mathbf C<\mathbf L-\mathrm{tol}$ or $\mathbf C>\mathbf U+\mathrm{tol}$.

Step 2: If any cell is flagged, fix the pricer (combined characteristic function, maturity, integration range) before inverting.

Step 3: Invert the whole grid in matrix form (see the option-numerics card, implied volatility over a grid).

**Limitations and cautions:**

1. At short maturities the characteristic function decays slowly, so a short truncation range leaves visible errors, largest far from the money.
2. A failed root search does not mean zero implied volatility.

**Double check:**

1. Reprice each implied volatility with Black-Scholes and compare with the model price; every cell must be finite. This checks the inversion, not the model price.

## Topic 8: Independent checks: constant-variance limit and Monte Carlo

**Purpose:** Test a Heston implementation against cases with known answers.

**When to use:** After writing the pricer, and whenever a price looks suspicious.

**How to implement:**

Step 1: Constant-variance limit ($\sigma_v\to0$): Heston reduces to Black-Scholes with

$$\sigma_{eff}^2=\theta+(v_0-\theta)\frac{1-e^{-\kappa T}}{\kappa T}$$

(with several factors, the sum of the factors' effective variances). Compare with a small $\sigma_v$, not $\sigma_v=0$.

Step 2: Monte Carlo with full-truncation Euler, $v^+=\max(v,0)$, on whole arrays of paths:

$$\ln S\mathrel{+}=(r-q-v^+/2)\,dt+\sqrt{v^+dt}\,Z_1$$

$$v\mathrel{+}=\kappa(\theta-v^+)\,dt+\sigma_v\sqrt{v^+dt}\left(\rho Z_1+\sqrt{1-\rho^2}Z_2\right)$$

**Limitations and cautions:**

1. Full truncation has a bias that shrinks with $dt$ but is large when the Feller condition is badly violated; the QE scheme has lower bias.

**Double check:**

1. The Fourier price lies within about two standard errors of the Monte Carlo price; if not, and the time step is fine, check Topics 2 to 4.

## Topic 9: Calibration

**Purpose:** Fit Heston parameters to market prices or implied volatilities.

**When to use:** The task asks for fitted parameters.

**How to implement:**

Step 1: Minimize weighted squared price errors (weights about $1/\text{vega}$) or implied-volatility errors over $(\kappa,\theta,\sigma_v,\rho,v_0)$ with bounds $\kappa,\theta,\sigma_v,v_0>0$ and $-1<\rho<1$ (`scipy.optimize.minimize` or `least_squares` with bounds); the Feller condition only if the task asks.

Step 2: Roles for starting values: $v_0$ sets the short-dated at-the-money level, $\theta$ the long-dated level, $\kappa$ the speed between them, $\rho$ the skew, $\sigma_v$ the smile curvature.

**Limitations and cautions:**

1. $\kappa$, $\theta$ and $\sigma_v$ trade off (a flat objective): use several starting points.

**Double check:**

1. Report the fit error and the parameters from the best start; parameters on a bound mean the fit collapsed: restart from other values.
