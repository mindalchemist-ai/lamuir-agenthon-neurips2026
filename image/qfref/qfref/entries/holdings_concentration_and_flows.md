# Holdings concentration, overlap and proportional flow exposure

For an ETF flow bridge, reconstruct relative transfer from its stated cash-flow base rather than a rounded displayed premium. When both amounts use the same positive redeemed share quantity:

```python
market_dollars = redeemed_shares * market_price
nav_dollars = redeemed_shares * nav_per_share
transfer_bps = (market_dollars - nav_dollars) / nav_dollars * 1e4
```

A premium or discount column in a product file is a rounded display: multiplying it by 1e4 is not this quantity; compute `(market_price / nav_per_share - 1) * 1e4` from the unrounded prices. This defines transfer relative to redeemed NAV dollars; it equals the price/NAV premium in basis points and does not acquire another redemption-fraction multiplier. A zero quantity makes this cash-flow ratio undefined; a price-based ratio is available only if that is the specified metric. Other denominators describe other quantities.

Components reported side by side over one base partition that base: a part described as specific to one fund next to the overlap part is the fund's covered amount minus the overlap amount, so the parts add back to the covered total. Each rank column orders the rows by its own named metric; the position of a row in a table sorted by another key is not that rank.

Use this note for long-only portfolio concentration, cross-fund common exposure and proportional flow scenarios. Identify whether weights refer to the whole fund or a selected subset. Explicit metric definitions override these conventional choices.

Aggregate positions by the security identifier alone (`CUSIP` or the task's equivalent key). Issuer names and class labels are display attributes: keep one representative label per identifier. Grouping by identifier plus a label splits one security into several rows and breaks every count, weight and rank built on it.

```python
agg = rows.groupby(id_col, as_index=False)[value_cols].sum()       # one row per identifier
labels = rows.groupby(id_col, as_index=False)[label_cols].first()  # one representative label each
agg = agg.merge(labels, on=id_col, how="left")
assert agg[id_col].is_unique                                        # a repeated identifier means a label was in the key
```

Labels and pairs that several outputs share:
1. A label shown for an identifier in a summary or ranking output (issuer name, class) is taken from the cleaned holdings table you wrote for the same period, so one identifier carries the same label in every output file; do not re-read it from the raw rows.
2. "One row per unordered pair" means each pair once, with the lower order key first, so $n$ entities give $n(n-1)/2$ rows.

3. "Latest period" is the latest period of the stated target periods, selected by its key in the cleaned table, not the latest date found in the raw filings.
4. Every column of a latest-period output, including a displayed date and labels, is taken from the frame already filtered to the latest period key. A value read with `.iloc[0]` from a frame that still holds several periods belongs to whichever period happens to come first.

```python
latest_key = periods[order_col].max()                      # from the universe file
latest = book[book[order_col] == latest_key]
latest_end = periods.loc[periods[order_col] == latest_key, end_col].item()
out[end_col] = latest_end
assert latest[end_col].nunique() == 1 and (latest[end_col] == latest_end).all()
```

5. Entities in outputs. A field or cell that lists or names entities (funds, managers, securities, pairs) holds the identifier that names them in the other outputs, such as a ticker or a label, never an internal order or sequence number. Unless the task states another format: in JSON, write a list of entities as a flat array of those identifiers and a pair as a two-element array `[id_i, id_j]`; in a CSV cell, join the identifiers with a separator that occurs in none of them. Do not write records with extra attributes (names, weights) in place of the identifier, and do not join labels with `_`, `-` or spaces, which labels themselves can contain. A field that holds one quantity per entity (counts, totals or weights named in the plural) is an object keyed by the entity identifiers, `{id: value}`, unless the task says it is a single number.

For nonnegative holding values $v_{i}$ with positive total V, portfolio weights are normalized values.

$$
\begin{gathered}
w_{i} = v_{i}/V \\
V = \sum _{i} v_{i}
\end{gathered}
$$

Herfindahl concentration and its effective equally weighted number of positions are:

$$
\begin{gathered}
\mathrm{HHI} = \sum _{j} w_{j}^{2} \\
N_{\mathrm{effective}} = 1/\mathrm{HHI}
\end{gathered}
$$

For n positive positions, $1/n\le \mathrm{HHI}\le 1$. A subset with weights summing to $c<1$ has raw concentration $\sum w_i^{2}$ and conditional concentration $\sum  (w_{i}/c)²$; these are different. In the full portfolio a name outside the subset still has its own weight; but when a task defines a fund's exposures on a selected holdings subset, a name outside that fund's subset has zero shares and zero dollars for that fund, even if it appears in the fund's complete list. A cash buffer in basis points is net cash divided by net assets times $10^4$. When a metric's inputs are in the data, compute it from them rather than writing a placeholder such as zero.

For two fully normalized books a and b on the union of securities, one common weighted-overlap measure is the shared minimum weight.

$$
O = \sum _{i} \min (a_{i},b_{i})
$$

Its relationship to total variation distance provides a check.

$$
O = 1 - (1/2)\cdot \sum _{i} \mathrm{abs}(a_{i}-b_{i})
$$

This identity requires equal unit totals. Snapshot weight distance is sometimes called turnover, but it includes price movement and differs from trading turnover against drifted pre-trade weights. Common-name counts ignore position sizes.

Portfolio turnover between two weight vectors $w^{prev}$ and $w^{curr}$ on the union of names (missing weight $=0$) has two common definitions. One-sided turnover is $\frac{1}{2}\sum_i |w^{curr}_i - w^{prev}_i|$, which lies in $[0, 1]$ for fully invested long-only books. Two-sided turnover is $\sum_i |w^{curr}_i - w^{prev}_i|$, which lies in $[0, 2]$. If the task gives the formula or a bound, use that; if it only says "turnover", state in a code comment which definition you use and why, and check that every value lies inside its range.

When the task names turnover without a formula, the common portfolio-turnover convention is the one-sided measure (half the sum of absolute weight changes, so a full replacement of the book is $1$):

```python
w = prev_w.reindex(union).fillna(0.0), curr_w.reindex(union).fillna(0.0)
turnover = 0.5 * (w[1] - w[0]).abs().sum()   # one-sided; state the choice in a comment
assert 0.0 <= turnover <= 1.0 + 1e-12
```

## Proportional fund flows

Let $A_{f}$ be fund net assets, $w_{\mathrm{fi}}$ its full-fund security weight, $q_{\mathrm{fi}}$ shares held, and $\rho _{f}$ the assumed proportional outflow fraction. Holding dollars and the implied constituent price satisfy:

$$
\begin{gathered}
V_{\mathrm{fi}} = A_{f}\cdot w_{\mathrm{fi}} \\
\operatorname{P}_{\mathrm{fi}} = V_{\mathrm{fi}}/q_{\mathrm{fi}}
\end{gathered}
$$

The price is defined only for positive share quantity and comparable unit/date conventions. Across funds, an aggregate implied price is total dollars divided by total shares, not the unweighted mean of individual prices.

Under the proportional-exposure scenario, the security's dollar outflow allocation is:

$$
\mathrm{flow}_{i} = \sum _{f} \rho _{f}\cdot V_{\mathrm{fi}}
$$

A fund redemption is valued at NAV: the basket of holdings delivered or sold for redeemed shares is worth redeemed shares x NAV per share. A ratio of the dollars attributed to a subset of holdings (the largest names, an overlap set) to the fund's redemption therefore uses the redeemed NAV dollars as its denominator unless the task names another base; redeemed market dollars (shares x market price) differ by the premium or discount and measure what the redeeming holders receive, not the basket. Check: under a pro-rata sale the ratio equals the subset's summed portfolio weight.

```python
nav_dollars = redeemed_shares * nav_per_share
subset_ratio = subset_sell_dollars / nav_dollars
assert abs(subset_ratio - subset_weight_sum) < 1e-3     # pro-rata basket: capture equals the subset's weight in the fund
```

Summing over all holdings gives total modeled outflow. Summing only a selected universe captures only that universe's share. Normalizing selected holdings back to one changes the scenario by reallocating omitted exposure.

Actual ETF redemptions can transfer securities in kind rather than cause immediate exchange sales. A modeled sale-pressure amount is therefore an assumed exposure measure, not proof of executed selling or price impact. NAV dollars and secondary-market traded dollars are also different quantities.

For market price P and NAV per share $N>0$, relative premium is:

$$
\mathrm{premium} = \operatorname{P}/N - 1
$$

Liquidity ratios compare compatible quantities: shares against share volume, or dollars against dollar volume. Their denominators define the economic interpretation; no universal blend of these ratios exists.

## Ties and ordinal positions

A tied statistical rank and an ordinal list position are different outputs. Pick the tie handling from two things: what the task states, and what kind of key drives the order.

| Situation | Order and positions | Avoid |
|---|---|---|
| The task names tie-break keys | sort by the metric, then exactly those keys; number the rows 1..n | extra keys placed before the named ones |
| The task names a tie method for ranks (min, average, dense) | `rank(method=<that method>)`; keep the repeated ranks | converting them into a permutation |
| The ranked table states no order, but another output holds the same rows in a stated order | keep that order (copy those rows) and rank within it with `rank(method="first", ascending=False)` | an order left over from a merge or cross join |
| The primary key is a count (holders, funds, filers, names) and no tie rule is given | after the count, sort by the size measure of the same rows, such as the aggregate dollar value behind that count, larger first; an identifier ascending comes only as the last key | ordering equal counts by identifier or by input row order: a count ties often, and those positions would then carry no economic meaning |
| The primary key is a continuous amount and no tie rule is given | sort by it, then an identifier ascending as a final deterministic key; exact ties are rare | rounding the amount first, which manufactures ties |
| A statistical rank with no tie rule | `rank(method="average")` | `first`, which hides the tie |

```python
ordered = table.sort_values(sort_keys, ascending=sort_directions, kind="stable").reset_index(drop=True)
ordered[position_column] = np.arange(1, len(ordered) + 1)   # positions follow the written row order
```

`method="min"` repeats a tied rank and skips the next positions, so it never yields a complete list. Write the table in the same order used to assign the positions. Do not invent a tie-break rule from an observed output. Floating-point expressions representing the same economic ratio can differ slightly; use justified precision consistent with the data or an exact construction, not rounding to force a desired order.

## Derivation and scope

Concentration and overlap identities follow from normalized weights and $\min(a,b)=(a+b-|a-b|)/2$. Flow identities are accounting under the explicitly stated proportional scenario, not a liquidation model. ETF primary-market mechanics are described by the [SEC Investor Bulletin on ETFs](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-24). These formulas do not define a composite metric from its column name alone.
