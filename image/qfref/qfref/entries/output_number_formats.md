# Writing deliverable files: planning the outputs, rounding, JSON and CSV values, exact names, row labels, ranks, codes and checks

The task description inside <task_instructions> takes priority over this card: where it states a different format, precision, name, order or code, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Planning and writing the deliverable files

**Purpose:** Leave a complete, correctly named set of files on disk, even if the reply budget runs out.

**When to use:** Every task that writes output files, especially one with several files or a separate results and intermediates file.

**How to implement:**

Step 1: In the first cell, list every output file the task names, and for each table its columns and for each JSON file its keys, copied character by character from the task text. Keep this list for the whole session.

Step 2: Write each file in the same cell that computes its values, or the next one. Write a first version of a results file as soon as some of its keys exist, and update it as more values are computed; do not hold every write until one final assembly cell.

Step 3: Assemble a summary or aggregate file last, from values already in the session.

Step 4: Before finishing, check that every listed file exists and that every listed key or column is present with a finite value.

**Limitations and cautions:**

1. A single large closing cell that builds several files fails on the first missing name and can leave the remaining files unwritten.
2. A task that asks for both a results file and a separate solution or intermediates file is easy to half-answer.

**Double check:**

1. Print the list of required files with an exists flag for each.

## Topic 2: When to round

**Purpose:** Avoid rounding errors that move results by a unit in the last place.

**When to use:** The task states decimals or a precision for written values.

**How to implement:**

Step 1: Compute every derived figure (a mean of ratios, a total, a difference) from the unrounded values held in the session.

Step 2: Round each value once, when writing it, to the stated decimals.

**Limitations and cautions:**

1. Rounding inputs first and then averaging moves the result by up to half a unit in the last place per term.

**Double check:**

1. A derived figure recomputed from the unrounded values and then rounded equals the written value.

## Topic 3: Numbers in JSON files

**Purpose:** Write numeric results as JSON numbers that a reader can compare.

**When to use:** Any JSON output with numeric fields.

**How to implement:**

Step 1: "Rounded to $n$ decimals" for a JSON value means a JSON number, `round(float(x), n)`, not a string such as `"100.420000"`. JSON numbers drop trailing zeros, which is correct for a numeric field.

Step 2: Fields that the schema marks as float, int, or an object or array of numeric results are numbers. Keys, identifiers and timestamps stay strings, even when built from numbers.

Step 3: Convert NumPy scalars with `float()` or `int()` before writing; a NumPy type is not a JSON number.

**Double check:**

1. Reload each JSON file and confirm that every field the schema marks as numeric is an `int` or `float`, recursively inside objects and arrays.

## Topic 4: Fixed-point text in CSV cells and identifiers

**Purpose:** Produce text with an exact number of decimals where the task asks for text.

**When to use:** The task asks for "fixed-point with exactly $n$ decimals", or an identifier string that embeds a number.

**How to implement:**

Step 1: Format with `f"{x:.{n}f}"` when writing that CSV cell or building that identifier; apply it only where the task asks for text.

Step 2: `df.to_csv(float_format=f"%.{n}f")` formats every float column; confirm that integer and string columns are unchanged.

**Double check:**

1. Read the CSV back as text and check the decimals of one row.

## Topic 5: Exact keys, column names and order

**Purpose:** Match the names and order the task writes, since checks read files by name.

**When to use:** The task shows a schema, a list of columns or literal keys.

**How to implement:**

Step 1: Write exactly the keys and column names the task shows, character by character, even when a more descriptive name seems clearer; put a descriptive label in a value, not in place of the key.

Step 2: When the task fixes the order of keys or columns, build them in that order: Python dicts and `json.dump` keep insertion order, while merging dicts or `sort_keys=True` changes it.

Step 3: Before writing each table, compare its columns with the list from Topic 1, Step 1; fix any difference first.

**Limitations and cautions:**

1. A dropped suffix, a different case, a unit added to a name, or a description copied into a header from the task's prose all fail every check that reads that column.

**Double check:**

1. Reload each file and compare its keys or header with the task's list, and its key order when the task fixes one.

## Topic 6: Tables whose first column labels the rows

**Purpose:** Keep row labels (states, ratings, assets) as a named column.

**When to use:** A matrix or table whose rows are labelled and whose first column the task names.

**How to implement:**

Step 1: `df.to_csv(path)` writes the index as an unnamed first column; `df.to_csv(path, index=False)` drops it. Make the labels an ordinary named column first: `df.rename_axis(name).reset_index().to_csv(path, index=False)`, with the name the task states.

Step 2: Write every labelled table the same way, so all of them keep their labels.

**Double check:**

1. Read each file back and compare its header with the stated columns.

## Topic 7: Rank and position fields

**Purpose:** Report ranks that match a 1-based position in a sorted list.

**When to use:** The output has a field named rank, position or order, or compares ranks across periods or samples.

**How to implement:**

Step 1: Sort the full table by the key the task names, in the stated direction.

Step 2: Reset the index after sorting, then set rank $=$ position $+1$. After `sort_values` the index keeps the old row labels, so `iterrows()` and `df.index` return pre-sort labels, not positions.

Step 3: To look up the rank of an item in another table (another period or sample), sort that table by the same key and take positions from it.

**Double check:**

1. The top item of every ranked list has rank $1$; ranks are distinct integers from $1$ to the list length.

## Topic 8: Categorical codes

**Purpose:** Keep category values in the codes the checks expect.

**When to use:** The output has categorical columns (type, side, status, sector).

**How to implement:**

Step 1: Keep the codes the input data use, unless the task names others. After a transformation (for example converting one instrument type into another), keep each record's original code; do not write descriptive labels instead.

**Double check:**

1. Print the distinct values of each categorical output column and compare them with the codes in the input data or the task.

## Topic 9: Which rows a summary field describes

**Purpose:** Compute each summary field from the table its definition names.

**When to use:** A task asks for summary fields (first or last date, counts, ranges, totals) after some rows were filtered for a step.

**How to implement:**

Step 1: A field defined over all events, rows or the whole panel comes from the full table; a field defined for a regression or test sample comes from that subset.

Step 2: When one step filters rows, keep the full table under its own name and take each summary from the table its definition names.

**Double check:**

1. Each summary figure equals the aggregate of the detail table it describes.
