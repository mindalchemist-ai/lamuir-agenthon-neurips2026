# Variance swaps and option-strip replication

Use this reference to calculate a variance strike from an option strip and interpret realized-variance settlement and notional units.

Map task quantities to these definitions by meaning and units, not by letter, before the first calculation; recheck when inputs or conventions change.

Explicit task definitions and contract conventions take precedence. If they conflict or are incomplete, identify the ambiguity and state the convention used.

## 1. Shared foundations
Symbols are local. $T>0$ is years, $D>0$ is the deterministic discount factor to expiry, $F>0$ the forward at that expiry, C(K)/P(K) discounted European call/put prices, and $K_{\mathrm{var}}$ the annualized variance strike in decimal-squared units. $K_{\mathrm{var}}$ is not volatility. A standard ideal replication assumes a positive continuous price process, deterministic carry and a sufficiently rich strike continuum. Discrete monitoring, jumps and finite strike coverage require qualifications.

## 2. Continuous-strike replication
For the ideal continuous-monitoring variance claim:
**Continuous-strike replication of the fair variance strike**

$$
K_{\mathrm{var}} = 2/(T\cdot D) \cdot  (\int _{0}^{F} \operatorname{P}(K)/K^{2} \mathrm{d}K + \int _{F}^{\infty} C(K)/K^{2} \mathrm{d}K).
$$

For the normalized log payoff $f(x)=-2\cdot \ln (x/F), f''(x)=2/x^{2}$. Its static option-strip representation, combined with dynamic trading and Ito's formula, gives this identity when the relevant expectations are finite and the trading stochastic integral has zero expectation. Under constant-volatility Black-Scholes it returns $\sigma^{2}$. With jumps, the log-contract jump term is not the squared-log-return jump term: do not call the strip an exact replication of an arbitrary realized-variance definition.

**Extract the forward from matched options**

Use puts below F and calls above F at the SAME maturity and consistent discount/carry. From matched call/put quotes, $F=K+(C-\operatorname{P})/D$. Cleaning rules, duplicate handling and quote selection come from the data contract. The model does not impose one universal cleaning policy.

## 3. Discrete strike conventions
One approach numerically integrates the OTM price divided by K^2, inserting a split at F and stating the quadrature and tail treatment. Finite coverage omits nonnegative tails and need not reproduce the continuum integral.
A different, Cboe-style convention uses K0, the largest available strike not exceeding F:
**Discrete option-strip variance convention**

$$
K_{\mathrm{var}} \approx  2/(T\cdot D)\cdot \sum _{i} (\mathrm{DeltaK}_{i}/K_{i}^{2})\cdot Q_{i} - (F/\mathrm{K0}-1)^{2}/T.
$$

**Strike widths and option selection**

This discrete rule needs positive, distinct sorted strikes spanning the forward and enough strikes to define widths. Interior $\mathrm{DeltaK}_{i}=(K_{i+1}-K_{i-1})/2$; endpoint widths are the full adjacent gaps, $K_2-K_1$ and $K_n-K_{n-1}$. $Q_{i}$ is a put below K0, call above K0, and the average call/put at K0. Apply the required quote-selection rules. Do not add this correction to an unrelated quadrature formula without deriving the convention. Nonuniform strike spacing requires actual widths.

## 4. Settlement and units
Use the contract's realized-variance definition.
**Realized-variance convention**

For equally spaced adjacent log returns $x_{j}$, one common convention is $\mathrm{RV}=(A/N)\cdot \sum _{j} x_{j}^{2}$, where N is the number of included returns and A is observations per year. Demeaned sample variance with denominator N-1 is a different statistic. Missing observations, irregular intervals and annualization must follow the contract.

**Variance-swap settlement**

For a long variance notional $N_{\mathrm{var}}$ defined per unit decimal variance, payoff $=N_{\mathrm{var}}(\mathrm{RV}-K_{\mathrm{var}})$. Its present value at inception is zero at the fair strike under the stated model; a deterministic terminal scenario payoff is not automatically a present value. Multiply by the appropriate discount factor only if present value is requested.

**Variance and vega notional conversion**

If variance is quoted in percentage-squared units, decimal variance is multiplied by 10000 and the notional must change consistently. If vega notional $N_{\mathrm{vega}}$ is defined as derivative of payoff with respect to decimal realized volatility at strike $\sigma _{K}=\sqrt{K_{\mathrm{var}}}$, then $N_{\mathrm{vega}}=2\cdot \sigma _{K}\cdot N_{\mathrm{var}}$. Other unit conventions change the numerical conversion. A volatility swap has a square-root payoff and is not a variance swap.

## 5. Checks and references
Reproduce $\sigma^{2}$ from a synthetic flat Black-Scholes surface with converged integration; then vary strike density and endpoints separately. Check forward extraction with independent parity, nonnegative option weights, and notional units.

If the task also asks for implied volatilities from the same quotes, check the Black-Scholes pricer against parity
before inverting; a price -> IV -> price round trip cannot catch a wrong discount factor, because it is self-consistent:

```python
c = bs(S, K, T, r, q, 0.2, "call"); p = bs(S, K, T, r, q, 0.2, "put")   # bs: the pricer used for the inversion
assert abs((c - p) - (S * np.exp(-q * T) - K * np.exp(-r * T))) < 1e-10      # a stray discount factor on the S term fails here
```

Where both a call and a put are quoted near the forward, their implied vols should be close; a gap of several vol
points that flips sign at the forward points to the pricer, not the market. Equality to ATM implied variance is not a general identity under a smile.
Cboe Volatility Index Mathematics Methodology, Section 3(a), documents the discrete convention in Section 3; it is not a universal variance-swap contract specification. The continuous representation and ledger conventions above are stated separately.
https://cdn.cboe.com/resources/indices/Cboe_Volatility_Index_Mathematics_Methodology.pdf
