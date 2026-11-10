# FX quote direction, funded forwards and forward value

Use this note for currency quote inversion, covered forwards and carry cashflows. Specify base currency, reporting currency, settlement dates and executable bid/ask sides. Follow explicit day-count, collateral and contractual conventions; do not infer them from a currency name.

## Executable quote direction

For positive dealer quotes in domestic units per foreign unit, reversing the pair reverses bid and ask as well as taking reciprocals:

$$
S_{\mathrm{bid}}^{\mathrm{inverse}}=1/S_{\mathrm{ask}},\qquad
S_{\mathrm{ask}}^{\mathrm{inverse}}=1/S_{\mathrm{bid}}
$$

For compatible pairs quoted as units of $B$ per $A$ and units of $C$ per $B$, synthetic $A/C$ bid and ask multiply corresponding executable sides. If a leg is divided rather than multiplied, its side reverses through reciprocal quotation. A cross of midpoints need not equal the midpoint of crossed bid/ask quotes.


Each tenor's forward uses the deposit rates quoted for that tenor in each currency (the mid of a bid/offer snapshot when one is given); interpolate between quoted tenors only for a broken date. A single-tenor rate series, such as a monthly 3M history used for carry signals, is not the rate for every forward tenor.
## Covered forward

Parity formulas name currencies by their place in the quote, not by the investor's home: the terms currency (the one the price is counted in) plays the domestic role and the base currency the foreign role, so for a USD-base pair the USD rate sits in the denominator even for a USD investor. Write the outright as $F=S(1+r_{\mathrm{terms}}\tau_{\mathrm{terms}})/(1+r_{\mathrm{base}}\tau_{\mathrm{base}})$, each year fraction on that currency's own day-count basis from the spot date. An unknown rate comes from the same identity: $r_{\mathrm{terms}}=((F/S)(1+r_{\mathrm{base}}\tau_{\mathrm{base}})-1)/\tau_{\mathrm{terms}}$. Check before writing: the outright lies above spot exactly when the terms rate exceeds the base rate, and an implied rate far outside the quoted deposit range means the identity was inverted.

Let $S$ be domestic-per-foreign FX for spot value date $v$, with forward delivery $T$. With deterministic collateral-compatible discount curves, the outright forward is:

$$
F(v,T)=S\frac{D_f(v,T)}{D_d(v,T)}
$$

For simple deposit rates with currency-specific year fractions, the no-basis funded expression is:

$$
F=S\frac{1+r_d\tau_d}{1+r_f\tau_f}
$$

Discount factors over $[v,T]$ are ratios $D_c(t,T)/D_c(t,v)$. Forward points are increments to spot, divided by the quoted point multiplier when converting to an outright. Interpolation of outright FX, forward points, log forwards and implied yields defines different broken-date curves. A traded non-deliverable forward can carry basis relative to deliverable covered parity.

For the same mid-market convention, implied simple foreign funding solves the forward identity:

$$
r_f=\frac{S(1+r_d\tau_d)/F-1}{\tau_f}
$$

Which rate is implied: the one the task asks for, and the task's word "foreign" (or "local") decides which side that is. Two readings are in use: (a) by quote position, foreign = the base currency, so in a EURUSD quote the implied foreign rate is the EUR rate and in a USDJPY quote it is the USD rate; (b) by the investor's home currency, foreign = the non-home currency, so for a USD-based investor it is the EUR rate in EURUSD and the JPY rate in USDJPY. Under (b), for a USD-base pair (USDXXX, including a USD-base NDF whose local currency is XXX) the implied rate is the terms rate, from $r_{\mathrm{terms}}=((F/S)(1+r_{\mathrm{base}}\tau_{\mathrm{base}})-1)/\tau_{\mathrm{terms}}$; for an XXXUSD pair it is the base rate below. A task that calls one currency foreign for the whole trade (a carry or hedge from one home currency) means (b); a task that speaks only of base and terms means (a). In code:

```python
def implied_base_rate(spot, forward, r_terms, tau_terms, tau_base):
    return (spot * (1 + r_terms * tau_terms) / forward - 1) / tau_base
def implied_terms_rate(spot, forward, r_base, tau_base, tau_terms):
    return ((forward / spot) * (1 + r_base * tau_base) - 1) / tau_terms
```

A higher forward implies a lower base rate: the offer forward gives the lower implied base rate, which is the rate bid, and the bid forward gives the rate offer. For the terms rate it is the other way: a higher forward implies a higher terms rate, so the bid forward gives the terms rate bid. Use the pairing of forward side and known-rate side the task states. Check before writing: the implied bid rate is below the offer rate, and the implied rate lies near the deposit rates quoted for that currency; a negative implied rate for a currency whose quoted rates are positive (often seen for a high-yield NDF local currency) means the base and terms sides, or the bid and offer sides, were swapped.

Executable bid/ask implied rates require the stated borrowing/lending and FX sides; a mid identity alone does not determine them. When the inputs give spot bid and ask but a single deposit rate per currency, apply the same accrual factor to each side: $F_{\mathrm{bid}}=S_{\mathrm{bid}}\,D_{\mathrm{base}}/D_{\mathrm{terms}}$ and $F_{\mathrm{ask}}=S_{\mathrm{ask}}\,D_{\mathrm{base}}/D_{\mathrm{terms}}$, with points on each side $F_{\mathrm{side}}-S_{\mathrm{side}}$ in pips; the mid is computed from the mid inputs or the average of the sides, as the task states. A two-sided quote with bid equal to ask is not an executable quote; it means the sides were dropped. Check bid < ask for every outright and cross before writing. In a P&L decomposition of a forward position (spot move, carry, residual), apply the position sign (+1 long the base currency, −1 short) to every component, not only to the total. When the residual is defined as total minus the other components, the components sum to the total whatever error they contain; check instead that the residual is small next to the spot and carry terms and that the spot term has the sign the spot move implies for that position.

## Covered-parity diagnostics and pair names

- When the task asks for a CIP (covered interest parity) forward or a CIP diagnostic, compute it from spot and the two deposit rates even when a market forward is also given; the market forward is the other side of the comparison, and the gap between them is the basis to report, not a reason to replace one with the other.
- Use one spelling for a pair throughout a task (with or without a slash, base first as the inputs write it) when building keys, joining tables and looking up conventions. A pair that is missing from a lookup is an error to raise, not a value to fill with 0 or to skip.

```python
conv = {p.replace("/", ""): c for p, c in pair_conventions.items()}     # one spelling for every lookup
def lookup(pair):
    key = pair.replace("/", "")
    if key not in conv:
        raise KeyError(f"no conventions for {pair}")
    return conv[key]
```

## Existing forward value

For a positive foreign notional $N_f$ bought at contractual delivery rate $K$, and current forward $F(t,T)$, domestic value is:

$$
V_d=N_fD_d(t,T)\{F(t,T)-K\}
$$

The short position has the opposite sign. Current contract value, settlement P&L and quote return are distinct. With spot defined at the valuation instant and matched curves, the same value is $N_f\{S D_f(t,T)-K D_d(t,T)\}$. Initial zero value does not mean zero future exposure.

## Carry and perspective

A foreign asset with simple local return $r_f^{\mathrm{asset}}$, converted through domestic-per-foreign FX, earns the domestic gross return:

$$
1+R_d=(1+r_f^{\mathrm{asset}})\frac{S_1}{S_0}
$$

Funding cost and transaction costs are additional cashflows. Reversing the quote changes the FX ratio, not the investor's economic position. A forward hedge's payoff depends on its locked notional and maturity; a current asset basket does not retroactively change an existing hedge book.

## Quote consistency checks

Write the quote as terms currency per base unit before calculating. Under compatible deterministic curves, $F=S D_{\mathrm{base}}/D_{\mathrm{terms}}$; the growth-factor ratio is the reciprocal of this discount-factor ratio. Inverting a bid/ask quote gives bid $1/\mathrm{ask}$ and ask $1/\mathrm{bid}$. Check each forward's direction against the relative accrual factors, its spot-date origin, and each currency's own day count. Convert outright differences to pips only with the pair's point multiplier. A cashflow's payment currency and present-value conversion must remain explicit; a pair name alone does not set a position's sign.

## References

[Reiswich and Wystup, FX Volatility Smile Construction](https://www.econstor.eu/bitstream/10419/40186/1/613825101.pdf), quotation and forward notation. The forward, implied-rate, mark-to-market and return expressions above follow by equating the two stated funded currency legs and converting terminal cashflows.

## Forward points, exposures and signs

- Forward points are quoted in pips: points $= (F - S)\times m$ with the pair's point multiplier m (for example $10^{4}$ for most pairs, $10^{2}$ when the terms currency is JPY, or the multiplier the inputs give). The outright is $F = S + \mathrm{points}/m$. A reported "forward points" figure of about $10^{-3}$ for a major pair is the unmultiplied difference.
- A forward or spot position in base/terms creates two currency exposures: $+N$ units of the base currency and $-N\cdot K$ units of the terms currency for a long base position (signs reversed for a short one). Net exposure per currency sums these legs over all trades, including currencies that appear only as the terms side of a cross, and then converts each currency's net amount to the reporting currency.
- Profit attribution signs follow the position direction: a long base position gains when the base/terms rate rises, a short one loses. Keep the trade's direction as a signed notional and apply it once.
