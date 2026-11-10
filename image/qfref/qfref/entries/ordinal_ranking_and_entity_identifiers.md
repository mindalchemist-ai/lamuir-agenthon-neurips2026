# Ordered outputs: ordinal positions, tie-breaking, statistical ranks, entity identifiers and copied input fields

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Ordinal positions in a sorted table

**Purpose:** Number the rows of a ranked table $1,\dots,n$ so that the numbers match the written row order.

**When to use:** The output has a column named rank, position or order that lists every row once (a leaderboard of securities, funds or pairs). For ranks that may repeat on ties, use Topic 3 instead.

**Constraints:**

1. Positions are assigned after the table is sorted by every key (the primary key and all tie-break keys of Topic 2), never before.

**How to implement:**

Step 1: Inputs. From the task text: the primary sort key, its direction, and any tie-break keys or tie rule it states. Print them.

Step 2: Sort the full table by all keys at once with `sort_values(keys, ascending=directions, kind="stable")`, then `reset_index(drop=True)`.

Step 3: Set the position column to `np.arange(1, n + 1)` on the sorted table, and write the table in that order.

Step 4: Do not compute positions with `Series.rank(method="first")` on the primary key alone. Reason: `"first"` orders tied rows by their current row order, which comes from how the table was built (a merge, a groupby), so the tie-break keys never take effect; a later sort by the tie-break keys cannot repair positions that were already fixed.

**Limitations and cautions:**

1. After `sort_values` the index keeps the old row labels, so `df.index`, `iterrows()` and `idxmax()` give pre-sort labels, not positions.

**Double check:**

1. Positions are the consecutive integers $1,\dots,n$, and the row with position $1$ is the first row of the written file; if not, sort again by all keys and renumber.

## Topic 2: Breaking ties when the task states no tie rule

**Purpose:** Order rows with equal primary keys in an economically meaningful and reproducible way.

**When to use:** The primary key can tie and the task names no tie-break keys and no tie method. When the task names them, use exactly those (Topic 1 or Topic 3).

**Constraints:**

1. When the primary key is a count (holders, funds, filers, names, events), the next key is the size measure of the same rows, such as the aggregate dollar value behind that count, larger first; an identifier ascending comes only as the final key.

**How to implement:**

Step 1: Classify the primary key. A count takes few distinct values, so ties are common and decide many positions. A continuous amount (a value, a weight, a return) rarely ties exactly.

Step 2: Count key: sort by the count, then by the size measure that the same table reports for those rows, both descending, then by the identifier ascending. Reason: among rows held by the same number of holders, the one with more money behind it is the more crowded or more important one; ordering ties by identifier or by input order gives positions with no economic meaning.

Step 3: Continuous key: sort by it, then by the identifier ascending as a final deterministic key. Do not round the amount before sorting: rounding manufactures ties.

Step 4: Any summary field defined by the ordering (the top item, the first $k$ items) is read from the table after this sort.

**Limitations and cautions:**

1. Floating-point results that represent the same economic ratio can differ in the last digits; do not round to force or break a tie.

**Double check:**

1. After sorting, within each group of equal primary keys the size measure (count key) or the identifier (continuous key) is in the stated direction: assert it. If it fails, the tie-break keys were not part of the sort; sort again by all keys and renumber (Topic 1).

## Topic 3: Statistical ranks with ties

**Purpose:** Compute ranks that may repeat for tied values, as used in rank correlations and percentile ranks.

**When to use:** The task asks for a rank statistic (a cross-sectional rank, a rank correlation, a percentile rank) or names a tie method; not for a list position (Topic 1).

**How to implement:**

Step 1: Use the tie method the task names: `Series.rank(method=...)` with `"average"` (mean rank of the tied group), `"min"` (best rank of the group, then a gap), `"dense"` (no gap) or `"first"` (order of appearance).

Step 2: Without a named method, use `"average"`, the convention of rank statistics such as Spearman's correlation, and state it.

**Limitations and cautions:**

1. `"min"` repeats ranks and skips the following positions, so it never gives a complete $1,\dots,n$ list; `"first"` hides ties.

**Double check:**

1. The sum of average ranks over $n$ items is $n(n+1)/2$; if not, the ranks were computed on a filtered or duplicated set.

## Topic 4: Naming entities in every output field

**Purpose:** Write the identifier that a reader of the other output files can match, wherever an output names an entity.

**When to use:** Any output field names one or more entities: a list column in a CSV (holders of a security, members of a group), a pair of entities, and also summary fields in JSON such as the pair with the largest value, the top item, or an object keyed by entity. The rule applies to all of them, not only to the table where the list first appears.

**Constraints:**

1. Never an internal order or sequence number, in any file.

**How to implement:**

Step 1: Inputs. List every column that identifies the same entity in the task's output schemas (for example an order number, a label or name, a registry code).

Step 2: When there is one identifier, use it. When there are several, use the one the task itself uses to name entities in the tables that list several of them with a single identifier column each (for example a pair table that carries only label columns). Reason: that is the identifier the task treats as the entity's name; a registry code or order number is a key for joining tables, not the name a list is read by.

Step 3: Build summary fields from the named columns, not from the order columns: when the top pair is found in a table that holds both, take the label columns of that row.

Step 4: Encoding, unless the task states one: in JSON, a flat array of identifiers, and a pair as a two-element array; in a CSV cell, the identifiers joined by a separator that occurs in none of them (not `_`, `-` or a space, which labels can contain).

**Limitations and cautions:**

1. Records with extra attributes (names plus weights) in place of the identifier are not an identifier list.

**Double check:**

1. After all files are written, reload each one and list every field or cell that names entities (CSV list columns, JSON pairs, top items, keys of per-entity objects); every identifier in them must appear in the chosen identifier column of another output file. A bare integer where a name is expected is an order number: replace it with the identifier chosen in Step 2 and write the file again.

## Topic 5: One row per entity when grouping

**Purpose:** Aggregate rows so that each entity appears once.

**When to use:** The output has "one row per" security, manager or pair, and the input rows for one entity can carry different descriptive text (names, class labels, spellings).

**Constraints:**

1. The grouping keys are the entity's identifier alone (plus the period when the table is per period); descriptive columns are never grouping keys.

**How to implement:**

Step 1: Group by the entity's identifier alone (for a security, its identifier code), not by the identifier together with descriptive labels. Reason: one identifier with two spellings of its name would otherwise become two rows, and every count or total for it would be split between them.

Step 2: Take descriptive columns afterwards, from the canonical label the task defines, or the most frequent value within the group, and state which.

**Double check:**

1. Assert that the number of output rows equals the number of unique identifiers (per period when the table is per period); if not, a descriptive column was among the grouping keys: regroup by the identifier alone and rebuild every output and summary field that used the table.

## Topic 6: Fields copied from the inputs

**Purpose:** Report input fields that an output repeats exactly as the input states them.

**When to use:** An output column has the same name as an input field (a flag, a code, a type, a date as filed), so that a reader can match the output row to its source record.

**Constraints:**

1. Keep the input's values and codes as given (for example `Y`, `N` or blank, a type code, a date string); do not re-encode them as booleans, numbers or other labels.

**How to implement:**

Step 1: For each output column with an input counterpart, take the value from the input row it describes.

Step 2: Read the input columns as text when they hold codes, so that blanks, leading zeros and letter codes are not converted on reading.

Step 3: Derived fields are separate columns with their own names (for example a boolean computed from a flag); do not overwrite the copied column with them.

**Double check:**

1. For each copied column, the set of distinct output values is a subset of the distinct input values; if a value such as `True` or `False` appears that the input does not contain, the column was re-encoded: copy the input value instead.
