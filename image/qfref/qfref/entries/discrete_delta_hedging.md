# Discrete delta hedging and cash-account accounting

Use this reference to track a discrete $\delta$ hedge through trades, financing, dividends and settlement, and reconcile its cash flows and P&L.

Map task quantities to these definitions by meaning and units, not by letter, before the first calculation; recheck when inputs or conventions change.

Explicit task definitions and contract conventions take precedence. If they conflict or are incomplete, identify the ambiguity and state the convention used.

## 1. Shared foundations
**Portfolio positions and marked wealth**

Symbols are local. Let $n_{\mathrm{opt}}$ be the signed number of option units (negative for a short position), $V_{t}$ the value per unit, $\Delta _{t}$ its spot derivative, $h_{t}$ the stock units held, and $B_{t}$ cash (negative means borrowing). Include any contract multiplier in $n_{\mathrm{opt}}$ exactly once. Portfolio wealth is $W_{t}=n_{\mathrm{opt}}\cdot V_{t}+h_{t}\cdot S_{t}+B_{t}$. Time is in years. Explicitly distinguish a realized stock path from pricing-model assumptions.

## 2. Initialization and rebalancing
A Delta-neutral stock target is $h_{\mathrm{target}}=-n_{\mathrm{opt}}\cdot \Delta _{t}$.

**Opening cash balance**

For an initially zero-wealth book with stock position $h_{0}$, set $B_{0}=-n_{\mathrm{opt}}\cdot V_{0}-h_{0}\cdot S_{0}-\mathrm{TC}_{0}$, so wealth after opening costs is -$\mathrm{TC}_{0}$. If an initial cash endowment exists, add it separately. Selling an option receives cash; buying the hedge consumes cash.

**Cash change and self-financing at rebalancing**

At a rebalance trade $\mathrm{d}h=h_{\mathrm{new}}-h_{\mathrm{old}}$, cash changes by $-\mathrm{d}h\,S_{\mathrm{trade}}-\mathrm{TC}(\mathrm{d}h,S_{\mathrm{trade}})$. Use the actual specified fill price; proportional costs are nonnegative and typically depend on $|\mathrm{d}h|$, not signed $\mathrm{d}h$. At a common mark and fill price, without costs or market movement, $hS+B$ must be unchanged by the trade. If fill differs from the mark, the wealth change also includes $\mathrm{d}h(S_{\mathrm{mark}}-S_{\mathrm{trade}})$. This is the self-financing check.

## 3. Cash accrual and dividends
Choose the event order from the contract and data timestamps.
**Financing between events**

Between events, with a single financing rate, $B_{\mathrm{before}}=B_{\mathrm{previous}}\cdot \exp (r_{\mathrm{cash}}\cdot \mathrm{d}t)$. If borrowing and lending rates differ, choose the rate from the cash sign over that interval; split at intervening cash events. Do not earn financing twice by also adding an overlapping daily interest term.

Dividend entitlement is determined by the shares held across the ex-dividend event. If the model treats ex-date and payment date as the same, a cash dividend $D_{\mathrm{cash}}$ adds $h_{\mathrm{entitled}}D_{\mathrm{cash}}$ to cash on that date; a short stock position owes it. If payment is later, record a receivable or payable at ex-date and move it into cash on payment date, using the entitled shares even if the hedge has since changed. Include the value of this receivable/payable in interim wealth; do not count it again after payment. Accrue cash interest only after cash is received or paid.

Under the same-date deterministic dividend convention, the theoretical ex-dividend spot falls by $D_{\mathrm{cash}}$, offset by dividend cash. With delayed payment the idealized drop corresponds to the value of the dividend entitlement; real price moves need not equal this theoretical drop. Observed ex-dividend prices already contain the event: do not subtract it a second time. Continuous dividend yield belongs to a continuous-income model and must not duplicate separately booked cash dividends.

## 4. Closing and interpreting P&L
Settle the option and stock under the stated contract.
For cash settlement at expiry and stock liquidation at $S_{T}$:
**Terminal wealth after settlement and stock liquidation**

$$
W_{\mathrm{final}}=B_{\mathrm{before}}+n_{\mathrm{opt}}\cdot g(S_{T})+h_{\mathrm{before}}\cdot S_{T}-\mathrm{TC}_{\mathrm{close}}.
$$

Subtract the appropriate initial capital or financed benchmark if the requested P&L definition requires it. Physical settlement, exercise fees and residual positions need their own cash flows. Mark-to-market wealth includes the option liability before settlement; do not subtract it again afterward.

Changing implied volatility changes V and $\Delta$, not cash directly. A revaluation of the option is not a cash receipt. Discrete hedging, transaction costs, model mismatch and volatility changes can all generate nonzero hedge P&L. Do not require a zero terminal error as a universal test.

## 5. Checks and related knowledge
Retain an event ledger: previous positions, financing, dividends, trades, costs, settlement and closing wealth. Reconcile each cash update with the trade ledger. Selling h shares adds h·S to cash and buying subtracts it; after the closing sale the stock position is zero. Use one update for every trade, the closing sale included: with $\mathrm{d}h=h_{\mathrm{new}}-h_{\mathrm{old}}$ (so $\mathrm{d}h=-h$ at the close), cash changes by $-\mathrm{d}h\,S-\mathrm{TC}$. Writing the close as `cash += dh * S` with a negative dh subtracts the sale proceeds. A hedged P&L of several times the option premium is a hint to recheck signs, not proof; the decisive checks are cash conservation through the ledger, a zero stock position after the close, and every fee recomputed from its trade's direction. Check the zero-trade case, a dividend event with fixed shares, long/short sign reversal only with zero transaction costs, symmetric financing and sign-symmetric trading/settlement rules, and zero-cost rebalancing conservation. For a Black-Scholes hedge use the analytic Greeks entry; discrete-dividend pricing is not generally obtained exactly by replacing S with S-PV(dividends). Follow an explicitly requested approximation and label it.

## 6. References
Black and Scholes (1973), dynamic replication framework. The cash equations here are direct bookkeeping identities; financing, event order and cost conventions are contract inputs, not universal market conventions.
