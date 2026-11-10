# Conventions: rebuilding state from filings and dated records

**Amendment chains.** Order a period's filings by filing date, then amendment number. A restatement replaces the whole book once per filing; an amendment reporting additional holdings appends its rows and drops nothing. A notice is not a book. Count raw rows on the resolved book, not summed over history.
**Cleaning.** Give each raw row one reason, the first it fails in a fixed order, so `raw == kept + sum(rejected)`. Aggregate the kept rows to one row per security identifier (`groupby(id).sum()`), then weight. A unit-type filter and an option flag are separate tests.

**Join keys.** Take identifiers from the input tables, never from file names. After every join check coverage:
**Session state.** Cells are re-run in one session. Never add columns to an input table in place; derive a new frame (`p = periods.assign(end=pd.to_datetime(periods.end_date))`). Rebuild a joined frame from its sources instead of merging the same table into it again, which adds `_x`/`_y` copies. Renaming onto a name that already exists makes two columns with one label, and `row[name]` then returns a Series. After every merge or rename:
**Insider filings.** Sale = transaction code S; the acquired/disposed flag covers other disposals too. Each ownership entity (direct, each named indirect holder, an entity named only in a footnote) keeps its own balance; post-trade balances are states, not addends.

**Dates.** A report-period date says what is described; a filing date says when it became public. As-of features use records dated on or before t. `(t-L, t]` and `[t-L, t]` differ only at the boundary; if the task does not say, name your choice. "Strictly before t" excludes t.

**Missing history.** If an entity has no record in the window, two readings: (a) missing, then the task's fill rule; (b) a neutral value at the window edge. Unless the task picks one, choose explicitly and say so.

**Per-unit vs position.** A quote, fee or cost per unit is a price; an amount for the position is qty x the per-unit value. A ledger column can be either, and two readings are common: (a) the column is a position amount, so a per-unit input is multiplied by qty when the row is written; (b) the column is itself a per-unit price (a header or note says per unit, per share or per contract, or the column sits beside other per-unit price columns). Decide from the column's description, its unit note and its neighbours; when the task gives none of these, a column named only as a cost, fee or P&L of a trade reads as (a), and say so in a comment. Under (a) convert when writing the row:
Store reserved entry capital (qty x cost per unit) and the receivable (qty x payoff) as separate ledger columns and derive metrics from them; never rebuild a second ledger. A running balance shown on a row (cash before / after) is read right before and right after that row's own action, not once per group.

**Equity and cash checks for a trade ledger.** Cash moves when capital is reserved or a payoff is received; an open position that has been paid for but not yet settled is a receivable (or a reserved amount), not lost money. Equity at any time = cash + reserved entry capital still open + receivables not yet settled, marked as the text states. Two checks catch most unit slips: cash never goes below zero when the text forbids borrowing, and every per-unit price column, multiplied by qty, gives the matching position column.

**Report tables.** Make the requested-key list first and work only on it. Find each report's table by row label, header, period and unit; indices move between filings. Save each value when read.

## Task wording -> API arguments
| Argument | Values | Usual wording |
|---|---|---|
| `merge(how)` | left keeps every base row; inner drops unmatched | "preserve all N rows" means left plus a row-count assert |
| `merge(validate)` | one_to_one, many_to_one | "keyed by", "unique" |
| `merge_asof(direction)` | backward = last at/before; forward = first at/after | "latest available", "next" |
| `merge_asof(allow_exact_matches)` | True: same stamp counts; False: strictly earlier | "on or before" vs "strictly before" |
| `drop_duplicates(keep)` | first/last depend on row order; sort by the tie column first; False drops all copies | "keep the largest sequence" |
| `to_datetime(format, utc)` | explicit format for text months; utc=True before `.dt.date` | "UTC calendar date" |
| `groupby(dropna)` | True (default) silently drops NaN keys | "count every row once" |
| `groupby(sort)` | True sorts keys alphabetically; use the universe file's order for pairs (i before j) | "in the order of the file" |
| `rank(method)` | min = shared rank; first = order of appearance; dense = no gaps | "ties share a rank" vs "complete ordering" |
| `std(ddof)` | 0 population, 1 sample (pandas default) | "population", "ddof=0" |

Check every argument against the wording before running.

Sources: SEC Form 13F FAQ Q58b-58c (sec.gov); SEC Form 4 General Instructions 4 and 8 (sec.gov/files/form4.pdf); EDGAR XBRL Guide 6.6.4; pandas 3.0 API reference: merge, merge_asof, drop_duplicates, to_datetime, groupby, Series.rank. Every code statement checked in verify_filing_conventions.py.

Institutional holdings reports (Form 13F):
- Value units. Values are reported in whole dollars from 3 January 2023 onward; before that they were in thousands of dollars. Decide the unit from the filing date and the period end, not from the size of the numbers. Restatements filed later can convert earlier periods.
- Cover-page totals. A filing's summary page describes that filing's own information table: all of its raw rows, before any cleaning and before an amendment is combined with other filings. Reconcile filing by filing (one accession at a time): the row count against the entry total, and the sum of the value column against the value total. Row counts must match exactly. Values are rounded to whole units row by row, so with $n$ rows the value totals can differ by at most $n/2$ from rounding alone. A reconciliation statistic or pass flag (largest absolute difference, "checks passed") is computed from the same per-filing table you write, never from the cleaned or aggregated book, never hard-coded, and never with a threshold chosen from the observed differences.

Difference between two values of the same quantity:
1. If the task instructions define the difference, follow that definition.
2. Otherwise use $\Delta V = V_{\text{new}} - V_{\text{old}}$, so a positive $\Delta V$ means an increase. $V_{\text{new}}$ is the value you computed, derived or updated; $V_{\text{old}}$ is the value stated in the source, reported earlier, or used as the reference or base. In short: difference = updated / new / derived / recomputed value $-$ original / old / base / raw value.
3. Do not infer the sign from the word order of a column name. Write the direction in a code comment, e.g. `# diff = recomputed - reported`.
4. A column named after the reference source followed by `_diff` (for example `<source>_row_diff`, `<source>_value_diff`) names what is compared against, not the minuend: it is still recomputed minus that source, so a positive value means your recomputed amount is larger than the reported one.

**Reading SEC flat files.** They are tab-delimited: `pd.read_csv(path, sep="\t")` (pandas has no `read_tsv`). An identifier can carry leading zeros in one file and none in another (`0000123456` in one file, `123456` in another): convert each identifier key to one type in every frame before you filter or join, and assert that the filter on the target universe keeps rows. In the first cell load every table and print `df.columns.tolist()`; copy column names from that printout afterwards. Parse SEC dates once with `format="%d-%b-%Y"` and keep each join key in one dtype in every frame. When you merge reported totals, rename them to the output column names in that same statement. Write at most two output files per cell, so one cell stays below the output limit.
- Repeated securities. One security can appear on several rows: different share class, investment discretion, or other managers, plus separate PUT and CALL rows for options. Only long option positions are reported. Count holders of a security by distinct filer (CIK). Before counting, decide whether option rows count as holding the security, and record the decision.
- Ties. When securities are ranked by a holder count, there is no regulatory or standard academic tie rule. Use the tie rule or secondary sort key the inputs specify. If none is given, use a deterministic secondary key and name it in a code comment.
