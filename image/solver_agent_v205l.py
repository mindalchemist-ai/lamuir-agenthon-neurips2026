from __future__ import annotations

import ast
import glob
import codecs
import collections
import contextlib
import csv
import datetime as dt
import difflib
import io
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import queue
import re
import secrets
import signal
import stat
import subprocess
import sys
import threading
import time
import unicodedata
import warnings
import zipfile
from collections import defaultdict
from types import SimpleNamespace
from typing import Callable

import litellm
from jinja2 import StrictUndefined, Template
from minisweagent.agents.default import DefaultAgent
from minisweagent.exceptions import FormatError, Submitted
from minisweagent.models.litellm_textbased_model import LitellmTextbasedModel
from minisweagent.models.utils.actions_toolcall import BASH_TOOL

VERSION = "solver-agent-v205l"

REPL_TOOL = True

STEP_LIMIT = 25

MAX_TOKENS_PER_CALL = 4000

WALL_CLOCK_SECONDS = "card"

WALL_CLOCK_MARGIN_SECONDS = 240

RETRY_ATTEMPTS = 1

TEMPLATE_KWARGS = {"low_effort": True}

INDEXED_INSTRUCTION = False

ENTRY_FILE = "solution.py"

ENTRY_LINE = """\
Execution rules for this environment

1. Work stage by stage: compute a part, check it, then continue, reusing what earlier cells left in memory.
2. Write each deliverable file as soon as the values it holds are computed and checked, in that cell or the next; do \
not wait until the whole task is done, even when the task lists saving as its last step. Write it from the session \
straight to the output path the task names, using the task's output-directory variable if it defines one; use task \
paths subject to the path notes above. Build each file's contents from the variables already in the session; print \
values to check them, but do not retype printed numbers. When a later change affects a file's values, write that file \
again.
3. Each reply is cut off at about 4,000 output tokens, counting everything you write in it, reasoning included, and a \
cut-off tool call does not run: none of its code runs or is kept. Do not send a complete program in one tool call, and \
keep your reasoning concise.
4. Preserve the scope of every time limit in the task. A limit on script or computation execution applies to that \
computation across its cells. A limit on the whole task or agent run remains an overall elapsed-time limit. Splitting \
work into cells does not reset either limit.
5. When the task text advises how to package or run code (write a single script that performs all steps, run it with \
python3, avoid python -c), that advice is about running code in a shell, and it does not apply here. Code runs in the \
Python cell session: keep working stage by stage in cells and keep writing each deliverable file as soon as its values \
are checked (rule 2), rather than building one program that produces every file at the end. /app is read-only: write \
files only under the output directory (or /tmp for scratch). Every requirement the task states on results, files and \
formats still applies."""

PREAMBLE = False

VERSIONS_PARAGRAPH = """\
The environment has NumPy 2.5.3, pandas 3.0.5, SciPy 1.18.1, statsmodels 0.15.0, arch 8.0.0, scikit-learn 1.9.0, Polars 1.44.1, TA-Lib 0.7.1, Backtrader 1.9.78.123, openpyxl 3.1.5, PyArrow 25.0.1, Matplotlib 3.11.1, Seaborn 0.13.2, Plotly 7.0.0, and Python 3.13.15 installed.
Use only APIs verified for these installed versions, following any task-specific construction or function restrictions. LibraryReference contains version-specific usage; error hints supply verified replacements when an API fails.
Numba: some task environments may additionally provide it.
Some APIs from older versions have been removed or replaced. Examples (old -> current):
  np.trapz(y, x)                          -> np.trapezoid(y, x)
  from scipy.integrate import trapz       -> from scipy.integrate import trapezoid
  np.math.<function>(...)                 -> math.<function>(...)
  df.resample('M').last()                 -> df.resample('ME').last()   (likewise 'Q' -> 'QE', 'Y' -> 'YE')
  pd.date_range(start, periods=n, freq='H') -> pd.date_range(start, periods=n, freq='h')   ('T' -> 'min', 'S' -> 's')
  df.fillna(method='ffill')               -> df.ffill()
  pd.to_numeric(x, errors='ignore')       -> pd.to_numeric(x, errors='coerce'), then keep the original where the result is NaN
Period operations such as df.to_period('M') still use 'M'.
np.zeros_like, np.ones_like, np.full_like and np.empty_like keep the dtype of their argument: on an integer array
np.full_like(a, 0.01) is all zeros. Pass dtype=float when the values are not integers.
Arithmetic between two DataFrames aligns on column labels: subtracting same-shaped blocks with different column names
gives all-NaN columns. Use .to_numpy() or per-column Series, and keep the input columns the task names.
After resample, sum() and count() give 0 for an empty bin while first/last/min/max give NaN: find empty bins from a
price column or the count, not from a zero-or-NaN sum. In this session sort_values (DataFrame and Series) sorts
stably by default, so rows that tie on the sort key keep their file order.
On trading-day data the first session of each month is dates.groupby(dates.dt.to_period('M')).min(); dt.is_month_start
is true only on calendar day 1 and misses months that begin on a weekend or holiday.
bool is a subclass of int (isinstance(True, int) is True): a converter that tests for int before bool writes 1 for True;
test bool first, or use save_json.
Keep pd and np for pandas and numpy: name a probability of default p_default, never pd.
A boolean mask built from a sorted copy selects from that sorted copy only; apply it to the unsorted array and it picks other rows.
Keep working columns in the working table and write a deliverable table from its own column list: out = work.loc[:, columns].
"""

BASH_INSTANCE_TEMPLATE = """\
{{task}}

---

Each reply, including your reasoning, is cut off at about 4,000 output tokens, and a cut-off command is not run. Write any
program longer than about 120 lines in parts: create the file with the first part, then add each further part with
`cat >> file <<'EOF'`, or split it into modules; run it once all parts are written.

Each of your replies must contain exactly one bash tool call; the system runs it and shows you the
result, and you then write the next one. Each command runs in a new subshell, so a directory or
variable you set does not survive into the next one.

""" + VERSIONS_PARAGRAPH + """
When the task is done, finish by issuing exactly this command on its own: `echo \
COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`. <important>After this command, you cannot continue working \
on this task.</important>
"""

TOOL_SENTENCE = "exactly one tool call (python or bash)"

TEXT_PROTOCOL = ("exactly one code block: either ```mswea_python_command ... ``` with Python code for the Python session, "
                 "or ```mswea_bash_command ... ``` with one shell command")

REPL_INSTANCE_TEMPLATE = """\
{{task}}

---

Each of your replies must contain """ + TOOL_SENTENCE + """; the system runs it and shows you the
result, and you then write the next one.

Work in the Python session one stage per cell, reusing what earlier cells left in memory. For example, for a task that
prices options from a curve file and a quote file and writes two result files (your stages will differ):
  cell 1: curve = pd.read_csv(...); quotes = pd.read_csv(...); params = json.load(...); print shapes and missing values
  cell 2: def build_curve(curve, params): ...      then  zc = build_curve(curve, params); print(zc.head())
  cell 3: def price(quotes, zc, params): ...       then  prices = price(quotes, zc, params); print a few checks
  cell 4: def greeks(quotes, zc, prices): ...      then  risk = greeks(quotes, zc, prices); print a few checks
  cell 5: write both files from prices and risk, then read them back to check
If cell 3 shows a mistake, the next cell is only the corrected def price(...), prices = price(...) and the checks;
then rerun cells 4-5's calls, which use prices. Do not import again, reload the inputs, or resend earlier stages:
their variables are still in the session. Keep each cell under about 120 lines.

""" + VERSIONS_PARAGRAPH + """
When the task is done, finish by issuing exactly this command on its own with the bash tool: `echo \
COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`. <important>After this command, you cannot continue working \
on this task.</important>
"""

INSTANCE_TEMPLATE = REPL_INSTANCE_TEMPLATE if REPL_TOOL else BASH_INSTANCE_TEMPLATE

PREIMPORTS = ["import math", "import json", "import os", "import re", "import datetime as dt",
              "from pathlib import Path", "import numpy as np", "import pandas as pd", "import scipy",
              "from scipy import stats, optimize, integrate, interpolate, linalg", "import statsmodels.api as sm",
              "import qfref", "from session_io import save_json", "from session_io import autosave_json"]

OTHER_LIBRARIES = ("scikit-learn (sklearn), statsmodels.formula.api, arch, polars, pyarrow, matplotlib, openpyxl, "
                   "TA-Lib (talib)")

QFREF_ROOT = "/opt/qfref"
LISTED_ENTRIES = "/cfg/qfref_entries.json"

EXPECTED_KEYS = "/tmp/msw_expected_keys.json"

SESSION_IO_ROOT = "/opt/msw_session"

QFREF_NOTE = """\
The Python session has `qfref`, a small finance reference. `qfref.catalog()` lists its entries and
`qfref.show(name)` prints one: formulas, parameter units, assumptions, limits and variants, with sources.
When the task names a method that the catalog has, read its entry before you write that formula.
It also holds LibraryReference manuals of verified usage for the installed libraries, for example
qfref.show('library_reference_pandas'), 'library_reference_numpy', 'library_reference_statsmodels', 'library_reference_arch',
'library_reference_scipy_optimize', 'library_reference_scipy_stats' or 'library_reference_polars'.
Where the task text defines something differently, follow the task text.
In your first cell, do the preparation together: load each input you need; print its shape, column dtypes, missing
counts and a few raw values of date and identifier columns (check that every date parses, and count values that
became NaT or NaN); and for each library or function the task text names or your plan needs, print its manual from
qfref when the LibraryReference block in the first message does not cover it, e.g.
qfref.show('library_reference_statsmodels') (it prints the manual).
Where the task text prescribes a construction or forbids a function, follow the task text."""

QFREF_INTRO = "Finance reference from qfref for methods this task names (where the task text differs, follow the task text):"

REPL_SYSTEM_TEMPLATE = """\
You are a helpful assistant that can interact with a computer.

Solve this task in the persistent Python REPL, implementing and checking the solution incrementally in short cells.

Task wording recommending a single or standalone script, or prohibiting inline Python, does not change how you should \
work here: implement and check the solution incrementally in short cells in the persistent Python REPL. Preserve all \
required methods, parameters, paths, outputs and runtime requirements.

You have two tools:
- python: runs code in one persistent Python session, like a Jupyter notebook cell. Variables, functions, imports
  and loaded data stay in memory between calls. If the last line of the code is an expression, its value is shown.
  Use it to read the inputs, compute, check results, and write the deliverable files.
- bash: runs one shell command in a new subshell each time. Use it for file-system work and to submit.

Already imported in the Python session:
<PREIMPORTS>
Also installed (import them yourself if needed): """ + OTHER_LIBRARIES + """.

Prefer established functions from the installed libraries for standard operations. Use the task-specific library \
guidance below when its assumptions match the task. Preserve the task's definitions, timing, units, and numerical \
conventions.
Use vectorized array and table operations when each output element, row or group can be computed independently of the \
others from inputs that are already known. Typical cases:
  elementwise arithmetic on columns or arrays       out = a * b,  r = prices.pct_change()
  totals or means by group                          values.groupby(keys.map(group_of)).sum()
  weighted sums and portfolio returns from weights  (weights * returns).sum(axis=1),  w @ x
  differences, lags and rolling statistics          series.diff(),  series.shift(1),  series.rolling(n).mean()
  powers of a fixed matrix for each horizon         np.linalg.matrix_power(P, h)
Keep an explicit loop when a step needs the result of the previous step, for example:
  holdings or cash carried from day to day in a backtest, with trades only on rebalance or event dates
  iterative solvers (PSOR, Newton, fixed-point or bisection) that run until a convergence test
  event-driven or path-dependent simulation where each event changes the state the next one sees
  time stepping in a finite-difference grid, where each time layer is solved from the one before it
Inside such a loop, the work done within one step can still be vectorized (all assets on one date, all grid nodes in \
one layer).

""" + QFREF_NOTE + """

How to work in the Python session:
Follow the execution rules given after the task text. When a result is wrong, change only the necessary code, whether
a function or top-level statements. Reuse unaffected session state, rerun affected dependent computations, and
regenerate any affected deliverables.
If a check fails, determine whether the computation, the check, or their conventions are inconsistent. Repair the cause
and rerun affected checks and outputs. Do not mark an unresolved check as passed.
Follow any computation sequence or workflow specified in the task, whether expressed through Step headings, numbered
sections or lists, algorithm descriptions, work sections, or prose. Distinguish dependent stages from independent
calculations and operations repeated inside a loop. Lists of inputs, rules, conventions, or output fields specify
requirements; their numbering alone does not establish an execution order. If no workflow is specified, organize the
work into short cells based on data dependencies, from input preparation through computation and verification to
writing deliverables. Combine short function definitions, their calls, and targeted checks in the same cell. Split
long stages into smaller cells (roughly 120 lines or fewer per cell) and combine short related calculations when
useful. Preserve intermediate results. After a change, rerun affected dependent computations and regenerate the
deliverables. Keep diagnostic output compact and respect any task-specific restrictions on printing.

Writing deliverables: the task's example objects and column lists are the schema.
- Copy each key's form from the example: a bare value ("x": 1.2) or a wrapped one ("x": {"value": 1.2}); both forms can appear in one file.
- Keys printed in the task's example are used exactly as printed. A glossary or term list is for intermediates the example does not name: look a term up by name (search the keys), do not print the whole list.
- Keep every key and column exactly as printed (case, underscores, prefixes); a parenthetical note after a name is not part of it; replace placeholder keys such as <TICKER> with the actual values.
- Write the type the example shows: integers as integers, booleans as true/false, lists and objects in the shown nesting; convert NumPy values with int(), float(), bool().
- NaN and infinity are not JSON: write null only where the task allows a missing value; otherwise find why the value is missing.
- Build objects and columns in the task's order and do not sort keys unless the task says so.
- In the same cell that writes a file, read it back from disk and compare keys, types, nesting and order with the example.

When calculating values for the output fields, use the data and calculation required by each field's definition.
For example, n_prices usually means the number of price observations, while n_returns usually means the number of
return observations. N consecutive valid prices produce N-1 adjacent one-period returns. Check which observations
each field refers to and count them separately. If a field's name and the task description suggest different
quantities, identify the conflict, briefly state your interpretation, and calculate the value accordingly.

What the session does and does not do:
- A cell with a syntax error is not run at all.
- A cell that raises an error stops at that line; the statements before it have already run, and nothing is rolled
  back (variables and any files written stay as they are).
- Redefining a function does not update results already computed with the old version.
- If the session is restarted, you are told; all variables are then gone and only the imports above are back.
"""


TRUNCATED = ("Your last reply reached the 4,000-token output limit before its command was complete, so nothing was run. "
             "Do not send the whole file again in one command: write it in parts of at most about 120 lines -- create the "
             "file with the first part, then add each further part with `cat >> file <<'EOF'` -- or split it into modules.")

TRUNCATED_REPL = ("Your last reply reached the 4,000-token output limit before its tool call was complete, so nothing was "
                  "run. Send a shorter cell of at most about 120 lines -- for example, define functions in one cell and "
                  "call them in the next. Variables from earlier cells are still in the session.")


REMIND_BEFORE_LIMIT = 4

STATUS_EVERY = 5

STATUS_LINE = "Status: {used} of {limit} replies used, {left} left; {elapsed} of {total} minutes of the time limit used."

STATUS_FILES = ("Required output files, each with its own entry in the task's output section copied as written; the full task "
                "text above is the authority.")

NAMING_NOTE = ("When naming an unspecified field, look at how similar quantities are named elsewhere in the task's JSON examples "
               "and CSV columns. Follow the same abbreviations, underscore placement, prefix order, and letter case. Reuse established "
               "names for the same quantities, and keep explicitly specified field names unchanged. An object keyed by category (one entry "
               "per reason, type or state the task defines) takes the category labels the task defines as its keys, not the names "
               "of other count fields: counts by status written as {\"active\": 3, \"closed\": 1} when the task names the statuses "
               "`active` and `closed`, not {\"n_active_rows\": 3, ...} copied from another file's field names.")

STATUS_NOTES = "The task's Notes section, copied as written:"
STATUS_NOTES_ON = os.environ.get("MINI_STATUS_NOTES") == "1"
NOTES_HEADING = re.compile(r"^(?:(#{1,6})[ \t]+Notes|\*\*Notes\*\*:?)[ \t]*$", re.M)


def task_notes(task: str) -> str:
    m = NOTES_HEADING.search(task)
    if not m:
        return ""
    level = len(m.group(1) or "######")
    rest = task[m.end():]
    end = re.search(r"^(?:#{1,%d}[ \t]+\S|\*\*[^*\n]+\*\*:?[ \t]*$)" % level, rest, re.M)
    return rest[: end.start() if end else len(rest)].strip()


SAVE_JSON_NOTE = ("Consider using save_json(path, data) to write a JSON deliverable: it turns NumPy scalars and arrays into Python "
                  "values, raises on any other type JSON cannot hold, and replaces the file only after the whole content is ready, "
                  "so a failed write leaves the old file.")

REMINDER = ('You have used {used} of the {limit} replies this task allows. In your next reply, save what you have already '
            'computed: in that one cell, write every required file whose values are already in your session, in any order, '
            'with every field or row you have verified so far, without recomputing anything. Make that cell only the writes: '
            'no new lookups in it, so an error cannot stop them. Do not fill unverified fields with guesses or placeholder '
            'values; leave them out for now. If a file holds many fields, write the verified ones now and update the file again '
            'as you verify more. List what is still missing. Then use the remaining replies to fill those gaps one at a time, '
            'rewriting the file after each, and finish with the submit command.')


EARLY_SAVE_AT = 15

EARLY_SAVE = ("Files not written yet: {files}. In your next reply, write a first version of them from the variables already in "
              "your session, with the fields or rows you have verified so far (no guesses or placeholder values), then continue; "
              "rewrite them as you verify more.")


MISPLACED_NOTE = ("Written outside the output directory: {found}. The task reads only {out}: write these files there (or change "
                  "the output directory the script or template uses to {out}) and rerun.")

EXTRACTION_SAVE_AT = 10
EXTRACTION_WORDS = ("filing", "filings", "xml", "10 k report", "10 k reports", "10 k filing", "8 k", "form 4", "13f", "edgar",
                    "prediction market", "prediction markets")
EXTRACTION_SAVE = ("No required file is written yet ({files}). In your next reply, write every required file from the values "
                   "already extracted or computed in your session; give each field not extracted yet the empty value the task "
                   "allows (null, an empty cell, or no row), never a guessed number. Make that cell only the writes, from "
                   "variables that already exist, with no new parsing in it, so an error in new code cannot stop them. Then "
                   "continue extracting and rewrite the files as each part is verified.")


def extraction_task() -> bool:
    try:
        text = " " + re.sub(r"[^a-z0-9]+", " ", pathlib.Path(TASK_STATEMENT).read_text().lower()).strip() + " "
    except OSError:
        return False
    return any(" " + w + " " in text for w in EXTRACTION_WORDS)


VERSION_NOTE = ("Environment note: the installed versions are NumPy 2.5.3, pandas 3.0.5, and SciPy 1.18.1. Check the module, "
                "spelling, and installed API; the missing name may reflect a version change or an incorrect call. "
                "Make a targeted correction and rerun to verify it.")

KNOWN_REPLACEMENTS = {"numpy.trapz": "np.trapz was removed: use np.trapezoid.",
                      "scipy.integrate.trapz": "scipy.integrate.trapz was removed: use scipy.integrate.trapezoid.",
                      "numpy.math": "np.math was removed: use Python's math module."}

VERSION_ERROR = re.compile(r"^AttributeError: module '((?:numpy|scipy|pandas)[\w.]*)' has no attribute '(\w+)'"
                           r"|^ImportError: cannot import name '(\w+)' from '((?:numpy|scipy|pandas)[\w.]*)'", re.M)


READONLY_NOTE = ("Environment note: the task's input files are read-only, and cp or shutil.copy keeps that mode on the copy. To change a "
                 "provided file, read its text, edit the string in Python and write it with open(new_path, 'w') to a new path under /tmp, "
                 "then run or import that new file.")
INPUT_PATH_NOTE = ("Environment note: in this run the task's input files are under {root}, even where the task text or a "
                   "provided script names another directory; point the path there.")
ZERO_ROWS = re.compile(r"(?:remaining|scheduled|selected|matched|eligible)\s+(?:bars|rows|days|trades)[^\n:=]{0,20}[:=]\s*0\b", re.I)
ZERO_ROWS_NOTE = ("Environment note: this output reports zero rows for a set the task builds rows from; check that the set is "
                  "taken from the full data (not from rows kept for another step) before writing an empty table.")
SHADOWED_MODULE_NOTE = ("Environment note: a name that held a module (pd for pandas, np for numpy) now holds a value; rename that "
                        "variable (for example p_default) and run `import pandas as pd` / `import numpy as np` again.")
SHADOWED_MODULE = re.compile(r"'(?:numpy\.)?(?:float64|float|int|int64|ndarray|Series|DataFrame)' object has no attribute "
                             r"'(?:DataFrame|Series|read_csv|concat|to_datetime|array|zeros|ones|nan|linspace|arange|exp|log|sqrt)'")
MISSING_APP_PATH = re.compile(r"(?:FileNotFoundError|No such file or directory)[^\n]*'(/app/(?!output)[^']*)'")


ONE_COLUMN_READ = re.compile(r"\[\\?'(\w[\w %.]*(?:[,;|\t]\w[\w %.]*){2,})\\?'\]|^ {2,}(\w+(?:[,;|]\w+){2,})[ \t]*\n0 +\S", re.M)
SEPARATOR_NOTE = ("Environment note: this looks like a table read as a single column named {name}. Check the column count "
                  "and the file's first line: if it uses another separator, pass that one (sep=',' for commas); files in one "
                  "directory need not share a separator. Check the required columns right after loading.")


def note_path_errors(messages: list[dict]) -> list[dict]:
    for message in messages:
        extra = message.get("extra")
        if not extra or not isinstance(message.get("content"), str):
            continue
        raw = extra.get("raw_output") or message["content"]
        notes = []
        denied = re.findall(r"(?:PermissionError: \[Errno 13\][^\n']*'|Permission denied: ')([^']+)'", raw) or (["?"] if "Permission denied" in raw else [])
        if any(not p.startswith(OUTPUT_DIR.rstrip("/")) and not p.startswith("/output") for p in denied):
            notes.append(READONLY_NOTE)
        roots = [d for d in DATA_DIRS if os.path.isdir(d)]
        if (m := MISSING_APP_PATH.search(raw)):
            hits = [d for d in roots if os.path.exists(os.path.join(d, os.path.basename(m.group(1))))]
            if hits and not m.group(1).startswith(hits[0]):
                notes.append(INPUT_PATH_NOTE.format(root=hits[0]))
        if ZERO_ROWS.search(raw):
            notes.append(ZERO_ROWS_NOTE)
        if (m := ONE_COLUMN_READ.search(raw)):
            notes.append(SEPARATOR_NOTE.format(name=m.group(1) or m.group(2)))
        if SHADOWED_MODULE.search(raw) or re.search(r"NameError: name '(?:DataFrame|Series)' is not defined", raw):
            notes.append(SHADOWED_MODULE_NOTE)
        if "The internally computed table of expected frequencies has a zero element" in raw:
            notes.append(ZERO_EXPECTED_NOTE)
        if notes:
            message["content"] += "\n\n" + " ".join(notes)
    return messages


ZERO_EXPECTED_NOTE = ("Environment note: scipy.stats.chi2_contingency rejects a table with an all-zero row or column; drop "
                      "those (and apply any minimum-count rule the task states) before calling it.")
RESET_INDEX_NOTE = ("Code note: reset_index() names the new column after the index's name (df.index.name), and 'index' only "
                    "when the index is unnamed; rename from df.index.name, or set the name before reset_index().")


class PdRebound:
    SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

    @staticmethod
    def targets(node) -> list:
        if isinstance(node, ast.Assign):
            return node.targets
        if isinstance(node, (ast.AugAssign, ast.AnnAssign, ast.For, ast.AsyncFor, ast.NamedExpr)):
            return [node.target]
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return [i.optional_vars for i in node.items if i.optional_vars is not None]
        return []

    def binds_pd(self, node) -> bool:
        return any(isinstance(n, ast.Name) and n.id == "pd" for t in self.targets(node) for n in ast.walk(t))

    def module_level(self, node) -> bool:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, self.SCOPES):
                continue
            if self.binds_pd(child) or self.module_level(child):
                return True
        return False

    def function_level(self, tree) -> bool:
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nodes = list(ast.walk(fn))
                if any(self.binds_pd(c) for c in nodes) and any(
                        isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "pd" for n in nodes):
                    return True
        return False

    def search(self, code: str) -> bool:
        try:
            tree = ast.parse(code)
        except (SyntaxError, ValueError):
            return False
        return self.module_level(tree) or self.function_level(tree)


ZERO_FFILL = re.compile(r"(?s)\b(\w+)\s*=\s*pd\.(?:DataFrame|Series)\(\s*0(?:\.0*)?\s*,.*\b\1\.ffill\(")


class MonthStartAsDay1:
    DIRECT = re.compile(r"\.dt\.is_month_start|\.is_month_start\b|\.day\s*==\s*1\b"
                        r"|to_period\(\s*['\"]M['\"]\s*\)[^\n]*\.start_time\s*==|==[^\n]*to_period\(\s*['\"]M['\"]\s*\)[^\n]*\.start_time")
    ASSIGNED = re.compile(r"^[ \t]*(\w+)\s*=\s*[^\n]*to_period\(\s*['\"]M['\"]\s*\)[^\n]*\.start_time", re.M)

    def search(self, code: str) -> bool:
        if self.DIRECT.search(code):
            return True
        return any(re.search(r"\b%s\s*==|==\s*%s\b" % (re.escape(v), re.escape(v)), code) for v in self.ASSIGNED.findall(code))


CODE_PATTERN_NOTES = [
    (MonthStartAsDay1(),
     "Code note: is_month_start and .day == 1 are true only on calendar day 1. If the task asks for the first trading "
     "session of each month, use dates.to_series().groupby(dates.to_period('M')).min() instead; if it asks for calendar "
     "dates, or this line only prints, no change is needed."),
    (ZERO_FFILL,
     "Code note: ffill fills only missing values, and this code fills the frame with 0 first. If the frame holds positions "
     "or weights meant to persist between rebalances, start from NaN, write each rebalance row in full (0 for exits), then "
     "ffill and fillna(0); a count or event frame that should stay 0 is fine as it is."),
    (re.compile(r"\A(?=[\s\S]*\.rolling\([^)]*\)\.\w+\([^)]*\)\.shift\(\s*1\s*\))(?=[\s\S]*(?:\.iloc\[\s*\w+\s*-\s*1\s*\]|\b\w+\s*=\s*\w+\s*-\s*1\b|get_loc\([^)]*\)\s*-\s*1\b))"),
     "Code note: this signal is shifted by one row and the rebalance also reads the row before it; that lags the signal "
     "twice. Keep one of the two lags, the one the task's timing states."),
    (PdRebound(),
     "Code note: this cell assigns to pd, the pandas alias; name the value differently (p_default, say)."),
]

SPARSE_TEXT = re.compile(r"(?:Count|Tfidf|Hashing)Vectorizer\b")
SPARSE_TEXT_NOTE = ("Code note: CountVectorizer / TfidfVectorizer .fit_transform returns a scipy.sparse csr_matrix (scikit-learn "
                    "1.9). Arithmetic on it keeps sparse-matrix rules: X / array is still a sparse matrix, and * or np.multiply "
                    "on it is not elementwise: the result collapses or changes shape. Convert with "
                    "X.toarray() (or use X.multiply(w)) before elementwise arithmetic and check the result's shape.")
SPARSE_TEXT_SHOWN: list[bool] = []

DOUBLE_LAG_PATTERN, DOUBLE_LAG_NOTE = next((rx, n) for rx, n in CODE_PATTERN_NOTES if "lags the signal" in n)
LAG_CHAINED = re.compile(r"\.rolling\([^)]*\)\.\w+\([^)]*\)\.shift\(\s*1\s*\)")
LAG_ROLLING_NAME = re.compile(r"^[ \t]*(\w+)\s*=\s*[^\n]*\.rolling\(", re.M)
LAG_EXCLUDING_WINDOW = re.compile(r"\.iloc\[\s*(\w+)\s*-\s*\w+\s*:\s*\1\s*\]")
LAG_PREVIOUS_ROW = re.compile(r"=\s*[^=\n]*(?:\.iloc\[\s*\w+\s*-\s*1\s*\]|get_loc\([^)]*\)\s*-\s*1\b)")
LAG_SIGNAL_NAME = re.compile(r"\b\w*(?:signal|score|rank|zscore|_z|mom|alpha|pred|forecast)\w*\s*\.iloc\[\s*\w+\s*-\s*1\s*\]"
                             r"|\b\w*(?:signal|score|rank|mom|alpha|pred|forecast)\w*\s*(?:\.loc)?\[[^\]]*get_loc", re.I)


def lag_previous_row_read(code: str, signal_only: bool = False) -> bool:
    for line in code.splitlines():
        if LAG_PREVIOUS_ROW.search(line) and (not signal_only or LAG_SIGNAL_NAME.search(line)):
            target = re.match(r"\s*(\w+)\s*(?:\.iloc)?\[", line)
            if not (target and re.search(r"\b%s\.iloc\[\s*\w+\s*-\s*1\s*\]" % re.escape(target.group(1)), line)):
                return True
    return False


def lag_lines(code: str):
    lines = code.splitlines()
    names = LAG_ROLLING_NAME.findall(code)
    shifted = [l for l in lines if LAG_CHAINED.search(l) or any(re.search(r"\b%s\s*\.shift\(\s*1\s*\)" % re.escape(n), l)
                                                              for n in names)]
    reads = [l for l in lines if lag_previous_row_read(l)]
    if shifted and reads:
        return shifted[0].strip(), reads[0].strip()
    windows = [l for l in lines if LAG_EXCLUDING_WINDOW.search(l)]
    signal_reads = [l for l in lines if lag_previous_row_read(l, signal_only=True)]
    if windows and signal_reads:
        return windows[0].strip(), signal_reads[0].strip()
    return None


TIMING_SENTENCE = re.compile(r"[^.\n]*(?:\bt\s*[-−]\s*1\b|previous (?:trading )?day|prior (?:trading )?day|day before|known at|"
                             r"previous close|prior close|information available)[^.\n]*", re.I)
DOUBLE_LAG_ACROSS = ("Code note: `{source}` ({where}) already lags the signal by one row, and `{read}` here reads "
                     "the row before it as well; that lags the signal twice. Keep one of the two lags, the one the task's "
                     "timing states.{task}")


def lag_paired(code: str) -> bool:
    shifted = bool(LAG_CHAINED.search(code)) or any(re.search(r"\b%s\s*\.shift\(\s*1\s*\)" % re.escape(n), code)
                                                    for n in LAG_ROLLING_NAME.findall(code))
    return ((shifted and lag_previous_row_read(code))
            or (bool(LAG_EXCLUDING_WINDOW.search(code)) and lag_previous_row_read(code, signal_only=True)))


LAG_SHIFT = re.compile(r"\.rolling\([^)]*\)\.\w+\([^)]*\)\.shift\(\s*1\s*\)"
                       r"|^[ \t]*\w*(?:signal|score|alpha|mom)\w*\s*=\s*[^\n]*\.shift\(\s*1\s*\)", re.M | re.I)
LAG_PREV = re.compile(r"\.iloc\[\s*\w+\s*-\s*1\s*\]|\b\w+\s*=\s*\w+\s*-\s*1\b|get_loc\([^)]*\)\s*-\s*1\b")
LAG_NOTE = ("Code note: this session contains a one-row shift and a previous-row access or index subtraction. These imply a "
            "double lag only if they delay the same active signal along the same calculation path. Different variables, "
            "superseded definitions, and unrelated counters need no change. Check the task's timing before changing either "
            "operation.")
SESSION_CODE: list[str] = []
LAG_SHOWN: list[bool] = []


NESTED_GRADIENT_NOTE = ("Code note: this cell takes a second derivative by applying np.gradient to the output of np.gradient. "
                        "That nests two first differences, a wider stencil than the three-point central second difference "
                        "(f(x+h) - 2 f(x) + f(x-h)) / h^2 (on an uneven grid, its non-uniform form with the two neighbouring "
                        "spacings), and the two can differ materially where the curvature is small. The task asks for central "
                        "differences and does not name np.gradient; check which stencil it means before keeping this.")
NESTED_GRADIENT_SHOWN: list[bool] = []


def nested_gradient(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return False

    def is_gradient(n) -> bool:
        return isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "gradient"

    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and is_gradient(n.value):
            for t in n.targets:
                for e in ast.walk(t):
                    if isinstance(e, ast.Name):
                        names.add(e.id)
    for n in ast.walk(tree):
        if is_gradient(n) and n.args:
            a = n.args[0]
            if is_gradient(a) or (isinstance(a, ast.Name) and a.id in names):
                return True
    return False


def asks_central_not_gradient(statement: str) -> bool:
    text = match_text(statement)
    return bool(re.search(r" central differences? ", text)) and " gradient " not in text


RESAMPLE_GEN = re.compile(r"product\(\s*[\[(]\s*-?1(?:\.0)?\s*,\s*-?1(?:\.0)?\s*[\])]|\.permutation\(|\bpermutations\(|\.shuffle\("
                          r"|choice\(\s*[\[(]\s*-1(?:\.0)?\s*,\s*1(?:\.0)?\s*[\])]|sign[_ -]?flip", re.I)
EXACT_GE = re.compile(r"abs\([^\n]*>=(?!=)|>=[^\n]*abs\(|\babs_\w+[^\n]*>=(?!=)|>=[^\n]*\babs_\w+|\w+_abs\b[^\n]*>=(?!=)|>=[^\n]*\w+_abs\b"
                      r"|\w*(?:star|perm|boot|null|resampl|flip|draw)\w*[^\n]*>=(?!=)[^\n]*\w*(?:obs|full|observed|actual|orig)\w*"
                      r"|\w*(?:obs|full|observed|actual|orig)\w*[^\n]*<=[^\n]*\w*(?:star|perm|boot|null|resampl|flip|draw)\w*")
MARGIN = re.compile(r"\d[eE]-\d|\beps\b|\btol\b|isclose|allclose|\(\s*1\s*-|\b1\s*-\s*\d|\+\s*\d*\.?\d+[eE]-")


def exact_ge_lines(code: str) -> list[str]:
    out = []
    for line in code.splitlines():
        body = line.split("#", 1)[0]
        if EXACT_GE.search(body) and not MARGIN.search(body) and not body.lstrip().startswith(("assert", "print")):
            out.append(body.strip())
    return out


def resample_matches(code: str, history: str) -> list[str]:
    return exact_ge_lines(code) if RESAMPLE_GEN.search(history) else []



EULER_SLOPE = re.compile(r"^\s*\w*(?:kappa|speed|revers|alpha)\w*\s*=\s*-\s*\(?\s*([A-Za-z_]\w*)\s*\)?\s*/\s*\(?\s*\w+", re.M | re.I)


def exact_lines(code: str, name: str) -> list[str]:
    rx = re.compile(rf"1(?:\.0)?\s*-\s*(?:{re.escape(name)}\s*\*\*\s*2(?:\.0)?\b|{re.escape(name)}\s*\*\s*{re.escape(name)}\b"
                    rf"|np\.square\(\s*{re.escape(name)}\s*\))")
    return [ln.split("#", 1)[0].strip() for ln in code.splitlines() if rx.search(ln.split("#", 1)[0])]


def ou_mix_matches(code: str, history: str) -> list[tuple[str, str]]:
    hist = "\n".join(ln.split("#", 1)[0] for ln in history.splitlines())
    cell = "\n".join(ln.split("#", 1)[0] for ln in code.splitlines())
    out = []
    for name in dict.fromkeys(m.group(1) for m in EULER_SLOPE.finditer(hist)):
        lines = exact_lines(hist, name)
        if lines and (exact_lines(cell, name) or any(m.group(1) == name for m in EULER_SLOPE.finditer(cell))):
            out += [(name, ln) for ln in lines if (name, ln) not in out]
    return out


def ou_mix_note(name: str, line: str) -> str:
    return (f"Code note: `{line}`: `{name}` here is the slope of the change on the level (phi - 1), not the AR(1) coefficient phi; "
            "either use sigma = resid.std(ddof=1)/sqrt(dt) with this regression, or regress the next level on the level and "
            "use phi in both kappa = -log(phi)/dt and the sigma formula.")


GRID_PARAMS = {"N", "NT", "NS", "M", "Nt", "Ns", "nt", "ns", "n_t", "n_s", "N_t", "N_s", "n_steps", "steps", "num_steps",
               "n_time", "n_time_steps", "n_space", "n_space_steps", "time_steps", "space_steps", "n_grid"}


def module_assignments(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return {}
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            used = {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)}
            for t in targets:
                if isinstance(t, ast.Name):
                    out[t.id] = used
    return out


def outer_step_matches(code: str, module_names: dict) -> list[tuple[str, str, str]]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    scope = dict(module_names)
    scope.update(module_assignments(code))
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        a = fn.args
        params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs} | {x.arg for x in (a.vararg, a.kwarg) if x}
        pos = a.posonlyargs + a.args
        defaults = dict(zip([x.arg for x in pos[len(pos) - len(a.defaults):]], a.defaults))
        defaults.update({x.arg: d for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None})
        grid = {p for p in params & GRID_PARAMS if not (isinstance(defaults.get(p), ast.Name) and defaults[p].id == p)}
        if not grid:
            continue
        stored = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
        stored |= {n.name for n in ast.walk(fn) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not fn}
        loaded = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        for name in sorted(loaded - params - stored):
            hit = scope.get(name, set()) & grid
            if hit:
                out.append((fn.name, name, sorted(hit)[0]))
    return out


def outer_step_note(def_line: str, grid: str, name: str) -> str:
    return (f"Code note: `{def_line}` takes `{grid}` but reads the module-level `{name}`, which was computed from a "
            f"module-level `{grid}`; a call with another `{grid}` keeps the old step. Compute the step inside the function "
            f"from its arguments (for example {name} = T / {grid}).")


EXACT_KAPPA = re.compile(r"^\s*\w*(?:kappa|speed|revers|alpha)\w*\s*=\s*-\s*(?:np\.|math\.)?log\(\s*([A-Za-z_]\w*)\s*\)\s*/\s*\(?\s*\w+[^\n]*",
                         re.M | re.I)
EULER_SIGMA = re.compile(r"^\s*\w*sigma\w*\s*=\s*[^\n]*\.std\([^)\n]*\)\s*/\s*(?:np\.|math\.)?sqrt\(\s*\w+\s*\)[^\n]*", re.M | re.I)


def ou_reverse_matches(code: str, history: str) -> list[tuple[str, str]]:
    hist = "\n".join(ln.split("#", 1)[0] for ln in history.splitlines())
    cell = "\n".join(ln.split("#", 1)[0] for ln in code.splitlines())
    sigmas = [m.group(0).strip() for m in EULER_SIGMA.finditer(hist)]
    out = []
    for m in EXACT_KAPPA.finditer(hist):
        kline, name = m.group(0).strip(), m.group(1)
        if exact_lines(hist, name) or not sigmas:
            continue
        sline = sigmas[-1]
        if (kline in cell or sline in cell) and (kline, sline) not in out:
            out.append((kline, sline))
    return out


def ou_reverse_note(kappa_line: str, sigma_line: str) -> str:
    return (f"Code note: `{kappa_line}` uses the exact AR(1) map while `{sigma_line}` uses the Euler scale; pair them: either "
            "kappa = -(phi-1)/dt with sigma = s/sqrt(dt), or kappa = -log(phi)/dt with sigma = s*sqrt(2*kappa/(1-phi**2)). "
            "If the task writes one of the two, use that one.")


OU_MIX_SHOWN: set[str] = set()
OUTER_STEP_SHOWN: set[tuple[str, str]] = set()
OUTER_SCOPE: dict[str, set] = {}

RESAMPLE_SHOWN: set[str] = set()


def resample_note(line: str) -> str:
    return (f"Code note: `{line}` compares resampled statistics with the observed one by an exact >=. In a sign-flip or "
            "permutation test the draw that reproduces the observed sample (all signs +1, or the identity permutation) "
            "counts as a hit, but refitting it returns the observed statistic only up to rounding, so an exact comparison "
            "can drop that draw and lower the p-value by one draw. Compare with a relative margin, for example "
            "`np.abs(stats) >= np.abs(observed) * (1 - 1e-12)`, and check that the identity draw is counted.")


def note_code_patterns(message: dict, observations: list[dict]) -> list[dict]:
    parts = []
    for tc in message.get("tool_calls") or []:
        raw = (tc.get("function") or {}).get("arguments", "")
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
            parts.append(str(args.get("code") or args.get("command") or raw))
        except (ValueError, AttributeError):
            parts.append(str(raw))
    code = "\n".join(parts)
    notes = [n for rx, n in CODE_PATTERN_NOTES if rx.search(code)]
    if not NESTED_GRADIENT_SHOWN and nested_gradient(code):
        with contextlib.suppress(OSError):
            if asks_central_not_gradient(pathlib.Path(TASK_STATEMENT).read_text()):
                NESTED_GRADIENT_SHOWN.append(True)
                notes.append(NESTED_GRADIENT_NOTE)
    if not SPARSE_TEXT_SHOWN and SPARSE_TEXT.search(code) and "fit_transform" in code:
        SPARSE_TEXT_SHOWN.append(True)
        notes.append(SPARSE_TEXT_NOTE)
    SESSION_CODE.append(code)
    history = "\n".join(SESSION_CODE)
    notes += oc7_code_notes(code)
    for line in resample_matches(code, history):
        if line not in RESAMPLE_SHOWN:
            RESAMPLE_SHOWN.add(line)
            notes.append(resample_note(line))
    for name, line in ou_mix_matches(code, history):
        if line not in OU_MIX_SHOWN:
            OU_MIX_SHOWN.add(line)
            notes.append(ou_mix_note(name, line))
    for kline, sline in ou_reverse_matches(code, history):
        if kline not in OU_MIX_SHOWN:
            OU_MIX_SHOWN.add(kline)
            notes.append(ou_reverse_note(kline, sline))
    for fn, name, grid in outer_step_matches(code, OUTER_SCOPE):
        if (fn, name) not in OUTER_STEP_SHOWN:
            OUTER_STEP_SHOWN.add((fn, name))
            d = re.search(rf"^\s*(?:async\s+)?def\s+{re.escape(fn)}\s*\([^\n]*", code, re.M)
            notes.append(outer_step_note(d.group(0).strip() if d else f"def {fn}(...)", grid, name))
    OUTER_SCOPE.update(module_assignments(code))
    if (not LAG_SHOWN and (LAG_SHIFT.search(code) or LAG_PREV.search(code)) and LAG_SHIFT.search(history)
            and LAG_PREV.search(history)):
        LAG_SHOWN.append(True)
        notes.append(LAG_NOTE)
    if re.search(r"reset_index\(\)[\s\S]*rename\(\s*columns\s*=\s*\{\s*['\"]index['\"]", code) and any(
            "KeyError" in str(o.get("content", "")) for o in observations):
        notes.append(RESET_INDEX_NOTE)
    if notes:
        for obs in observations:
            if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                obs["content"] += "\n\n" + " ".join(notes)
    return observations


SCRIPT_EDITS_SHOWN: dict[str, list[str]] = {}


SCRIPT_EDIT_V2: dict = {}
exec(compile('import os, re\n\nCOMPILE_NOTE = "It does not compile ({kind} at line {line}: {msg}); fix this before running it. Edit the file by replacing an exact block copied from it (`text.replace(old_block, new_block)`, keeping the indentation of the copied block) and run `compile` on the new text before writing it back; do not insert lines by index."\nPATH_NOTE = ("It still names {old} for its inputs, which does not exist in this run; the inputs are under {new}. Change the "\n             "path in the file before running it, for example:\\n"\n             "p = {path!r}\\n"\n             "open(p, \'w\').write(open(p).read().replace({old!r}, {new!r}))")\nUNUSED_NOTE = ("Unused-helper note: {src} defines {fn}() but no line in it calls {fn}; {copy} still does not. In a supplied "\n               "script that is known to contain errors, a helper nobody calls usually marks a step that is done some other "\n               "way instead. Find the lines in {copy} that do the job its name describes, compare them with the convention "\n               "the inputs state, call {fn} there, and run the file again.")\nCHECKS = {"compile", "path", "unused"}\nSEARCH_MISS_NOTE = ("Search-miss note: the search text below occurs neither in {src} nor in any earlier cell, so the replacement "\n                    "that depends on it changed nothing:\\n```text\\n{snippet}\\n```\\nPrint the part of {src} you meant to "\n                    "change first, then edit it.")\nINPUT_ROOTS = ("/app/data", "/input/environment/data", "/app/input", "/data")\n\n\ndef _calls(src: str, fn: str) -> bool:\n    import ast\n    try:\n        tree = ast.parse(src)\n    except SyntaxError:\n        return bool(re.search(r"\\b" + re.escape(fn) + r"\\s*\\(", src))\n    return any((isinstance(n, ast.Name) and n.id == fn) or (isinstance(n, ast.Attribute) and n.attr == fn) for n in ast.walk(tree))\n\n\ndef edit_note_extras(path: str, text: str, data_dirs, original: str = None, src_name: str = "the supplied script") -> list:\n    """Notes for one edited copy: a compile error, and the first input root the file names that does not exist here while\n    one of data_dirs does. An unchanged copy of the input script (a backup) gets none."""\n    notes = []\n    if original is not None and text.splitlines() == original.splitlines():\n        return notes\n    try:\n        compile(text, path, "exec")\n    except SyntaxError as e:\n        if "compile" in CHECKS:\n            notes.append(COMPILE_NOTE.format(kind=type(e).__name__, line=e.lineno, msg=e.msg))\n    real = next((d for d in data_dirs if os.path.isdir(d)), None)\n    if real and "path" in CHECKS:\n        for root in INPUT_ROOTS:\n            if os.path.exists(root) or os.path.abspath(root) == os.path.abspath(real):\n                continue\n            if re.search(r"[\'\\"]" + re.escape(root) + r"(?:/[^\'\\"]*)?[\'\\"]", text):\n                notes.append(PATH_NOTE.format(old=root, new=real, path=path))\n                break\n    if original is not None:\n        LAST_COPIES.pop(path, None)\n        LAST_COPIES[path] = (original, text, src_name)\n        for fn in (_unused(original, text) if "unused" in CHECKS else []):\n            if (path, fn) not in WRITE_SEEN:\n                WRITE_SEEN.add((path, fn))\n                notes.append(UNUSED_NOTE.format(src=src_name, fn=fn, copy=path))\n    return notes\n\n\ndef _unused(original: str, text: str) -> list:\n    import ast\n    try:\n        defs = [n.name for n in ast.parse(original).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]\n    except SyntaxError:\n        return []\n    return [fn for fn in defs if fn != "main" and not fn.startswith("test") and not _calls(original, fn) and not _calls(text, fn)]\n\n\nLAST_COPIES: dict = {}\nWRITE_SEEN: set = set()\n\n\ndef unused_helper_problems() -> list:\n    """Submit-check items: functions of a supplied script that the most recently written edited copy still never calls\n    (an earlier copy the model left behind is not checked)."""\n    if "unused" not in CHECKS:\n        return []\n    return [UNUSED_NOTE.format(src=src_name, fn=fn, copy=path)\n            for path, (original, text, src_name) in list(LAST_COPIES.items())[-1:] for fn in _unused(original, text)]\n\n\nSED = re.compile(r"sed\\s+-i[^\']*\'(?:\\d+|/[^/]*/)?(?:,\\S*)?s([/|#])((?:\\\\.|(?!\\1).)*)\\1")\n\n\ndef _bre_to_py(p: str) -> str:\n    out, i = [], 0\n    while i < len(p):\n        c = p[i]\n        if c == "\\\\" and i + 1 < len(p):\n            out.append(p[i + 1] if p[i + 1] in "(){}|+?" else "\\\\" + p[i + 1])\n            i += 2\n            continue\n        out.append("\\\\" + c if c in "(){}|+?" else c)\n        i += 1\n    return "".join(out)\n\n\ndef searches(code: str, kind: str) -> list:\n    """The literal search texts of a cell: ("lit", text) for str.replace(old, new), ("re", (pattern, flags)) for\n    re.sub / re.subn / a re.compile used with .sub, and for the pattern of sed -i s///."""\n    import ast\n    if kind != "python":\n        return [("re", (_bre_to_py(m.group(2)), 0)) for m in SED.finditer(code)]\n    try:\n        tree = ast.parse(code)\n    except SyntaxError:\n        return []\n    out = []\n    for n in ast.walk(tree):\n        if not isinstance(n, ast.Call) or not n.args or not isinstance(n.args[0], ast.Constant) or not isinstance(n.args[0].value, str):\n            continue\n        f = n.func\n        if isinstance(f, ast.Attribute) and f.attr == "replace" and len(n.args) >= 2:\n            out.append(("lit", n.args[0].value))\n        elif (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "re"\n              and (f.attr in ("sub", "subn") or (f.attr == "compile" and ".sub(" in code))):\n            rest = " ".join(ast.unparse(x) for x in list(n.args[1:]) + [k.value for k in n.keywords])\n            flags = (re.M if re.search(r"MULTILINE|re\\.M\\b", rest) else 0) | (re.S if re.search(r"DOTALL|re\\.S\\b", rest) else 0)\n            out.append(("re", (n.args[0].value, flags)))\n    return out\n\n\ndef _found(kind: str, s, text: str) -> bool:\n    if kind == "lit":\n        return s in text\n    import signal, threading\n    pat, flags = s\n    if threading.current_thread() is not threading.main_thread():\n        return True\n    old = signal.signal(signal.SIGALRM, _timeout)\n    signal.setitimer(signal.ITIMER_REAL, 2.0)\n    try:\n        return re.search(pat, text, flags) is not None\n    except (re.error, TimeoutError):\n        return True\n    finally:\n        signal.setitimer(signal.ITIMER_REAL, 0)\n        signal.signal(signal.SIGALRM, old)\n\n\ndef _timeout(signum, frame):\n    raise TimeoutError\n\n\ndef search_miss_notes(code: str, kind: str, scripts: dict, earlier: str) -> list:\n    """One note for the first search text of this cell that edits a supplied script (the cell names it) and occurs neither\n    in any supplied script nor in the earlier cells; scripts: {basename: text}; each search text is noted once per run."""\n    hit = [name for name in scripts if os.path.splitext(name)[0] in code]\n    if not hit:\n        return []\n    seen = "\\n".join(scripts.values()) + "\\n" + (earlier or "")\n    for k, s in searches(code, kind):\n        text = s if k == "lit" else s[0]\n        if (k, text) in MISS_SEEN or _found(k, s, seen):\n            continue\n        MISS_SEEN.add((k, text))\n        snippet = text if len(text) <= 400 else text[:400] + " ..."\n        return [SEARCH_MISS_NOTE.format(src=hit[0], snippet=snippet.replace("`" * 3, "\'" * 3))]\n    return []\n\n\nMISS_SEEN: set = set()\n', "script_edit_v2", "exec"), SCRIPT_EDIT_V2)

SCRIPT_EDIT_CHECKS = {"unused", "compile"}
SEARCH_MISS_ON = True
SCRIPT_EDIT_V2["CHECKS"] = SCRIPT_EDIT_CHECKS
SEARCH_EARLIER: list = []


def note_search_miss(message: dict, observations: list[dict]) -> list[dict]:
    calls = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn["arguments"]) if isinstance(fn.get("arguments"), str) else fn.get("arguments") or {}
        except Exception:
            continue
        if fn.get("name") == "python" and args.get("code"):
            calls.append(("python", str(args["code"])))
        elif fn.get("name") == "bash" and args.get("command"):
            calls.append(("bash", str(args["command"])))
    notes = []
    if SEARCH_MISS_ON and calls:
        try:
            scripts = {}
            for d in DATA_DIRS:
                for root, _, names in os.walk(d):
                    for n in names:
                        if n.endswith(".py"):
                            scripts.setdefault(n, open(os.path.join(root, n), errors="replace").read())
            for kind, code in calls:
                notes += SCRIPT_EDIT_V2["search_miss_notes"](code, kind, scripts, "\n".join(SEARCH_EARLIER)) if scripts else []
        except Exception:
            notes = []
    SEARCH_EARLIER.extend(code for _, code in calls)
    if notes:
        print(f"[solver] search-miss notes: {len(notes)}", flush=True)
        for obs in observations:
            if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                obs["content"] += "\n\n" + "\n\n".join(notes)
                break
    return observations


REREAD_SHOWN: set = set()
REREAD_COUNTS: dict = {}
TEMPLATE_WRITES: dict = {}


def note_reread_template(message: dict, observations: list[dict], since: float, messages: list) -> list[dict]:
    mod = triage_module()
    if mod is None or not hasattr(mod, "reread_notes"):
        return observations
    calls = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn["arguments"]) if isinstance(fn.get("arguments"), str) else fn.get("arguments") or {}
        except Exception:
            continue
        if fn.get("name") == "python" and args.get("code"):
            calls.append(("python", str(args["code"])))
        elif fn.get("name") == "bash" and args.get("command"):
            calls.append(("bash", str(args["command"])))
    notes = []
    with contextlib.suppress(Exception):
        first = next((str(m.get("content") or "") for m in messages if m.get("role") == "user"), "")
        notes = mod.reread_notes(calls, first, REREAD_SHOWN, REREAD_COUNTS)
    with contextlib.suppress(Exception):
        scripts = {n: open(os.path.join(r, n), errors="replace").read() for d in DATA_DIRS for r, _, ns in os.walk(d)
                   for n in ns if n.endswith(".py")}
        mod.template_run_record(calls, scripts, OUTPUT_DIR, since, pathlib.Path(TASK_STATEMENT).read_text(), TEMPLATE_WRITES)
    if notes:
        print(f"[solver] re-read notes: {len(notes)}", flush=True)
        for obs in observations:
            if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                obs["content"] += "\n\n" + "\n\n".join(notes)
                break
    return observations


def note_script_edits(observations: list[dict], since: float) -> list[dict]:
    inputs = [os.path.join(d, n) for root in DATA_DIRS for d, _, names in os.walk(root) for n in names if n.endswith(".py")]
    if not inputs:
        return observations
    notes = []
    for d, _, names in os.walk("/tmp"):
        for n in names:
            path = os.path.join(d, n)
            try:
                if not n.endswith(".py") or os.path.getmtime(path) < since:
                    continue
                new = open(path, errors="replace").read().splitlines()
                best = max(((difflib.SequenceMatcher(None, open(i, errors="replace").read().splitlines(), new).ratio(), i) for i in inputs))
            except OSError:
                continue
            if best[0] < 0.5:
                continue
            old = open(best[1], errors="replace").read().splitlines()
            changed = [l[:160] for l in difflib.unified_diff(old, new, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            if SCRIPT_EDITS_SHOWN.get(path) == changed:
                continue
            SCRIPT_EDITS_SHOWN[path] = changed
            head = f"Script-edit note: {path} differs from the provided {os.path.basename(best[1])} in {len(changed)} line(s)"
            body = "\n".join(changed[:40]) + ("\n..." if len(changed) > 40 else "")
            try:
                extras = SCRIPT_EDIT_V2["edit_note_extras"](path, "\n".join(new), DATA_DIRS, "\n".join(old), os.path.basename(best[1]))
            except Exception:
                extras = []
            notes.append(head + (":\n" + body if changed else "; no edit landed.")
                         + "\nCheck that every change you meant to make is listed; an edit whose search text matched nothing is missing here."
                         + "".join("\n" + x for x in extras))
    if notes:
        for obs in observations:
            if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                obs["content"] += "\n\n" + "\n\n".join(notes)
                break
    return observations


VA_CARDS_ENABLED: set = set()
VA_STEPS = "fix_line"
VA_SEEN: set = set()
try:
    import importlib.util as _va_iu
    _va_spec = _va_iu.spec_from_file_location("va_doc", os.path.join(QFREF_ROOT, "qfref", "va_doc.py"))
    VA_DOC = _va_iu.module_from_spec(_va_spec)
    _va_spec.loader.exec_module(VA_DOC)
    VA_CARDS = VA_DOC.load_cards()
    VA_CARDS_ENABLED = set(['numpy.nanstd', 'numpy.nanvar', 'numpy.ndarray.std', 'numpy.ndarray.var', 'numpy.std', 'numpy.var', 'statsmodels.api.add_constant', 'builtins.dict.get', 'pandas.DataFrame.sort_values', 'pandas.Series.sort_values', 'pandas.DataFrame.rank', 'pandas.Series.rank', 'pandas.GroupBy.rank', 'pandas.Series.std', 'pandas.DataFrame.std']) & set(VA_CARDS)
except Exception:
    VA_DOC, VA_CARDS = None, {}


API_FIXES_PATH = os.path.join(QFREF_ROOT, "qfref", "library_reference_api_error_fixes.json")
API_FIXES_SEEN: set = set()


def api_fix_rules() -> list:
    if not hasattr(api_fix_rules, "rows"):
        try:
            api_fix_rules.rows = [(r["id"], re.compile(r["pattern"], re.S), r["hint"])
                                  for r in json.loads(pathlib.Path(API_FIXES_PATH).read_text())]
        except (OSError, ValueError, KeyError, re.error) as exc:
            print(f"[solver] API repair rows not loaded: {type(exc).__name__}", flush=True)
            api_fix_rules.rows = []
    return api_fix_rules.rows


def note_version_errors(messages: list[dict]) -> list[dict]:
    for message in messages:
        extra = message.get("extra") or {}
        if extra.get("returncode") in (0, None) or not isinstance(message.get("content"), str):
            continue
        raw = re.sub(r"\\u(0027|0022)", lambda m: chr(int(m.group(1), 16)), extra.get("raw_output") or "")
        matched = [(i, h) for i, rx, h in api_fix_rules() if rx.search(raw)]
        if matched:
            fresh = [(i, h) for i, h in matched if i not in API_FIXES_SEEN] if len(matched) == 1 else []
            print(f"[solver] API repair match: {[i for i, _ in matched]} hinted {[i for i, _ in fresh]}", flush=True)
            for i, h in fresh:
                API_FIXES_SEEN.add(i)
                message["content"] += "\n\nAPI note: " + h
            continue
        found = [f"{m1}.{n1}" if m1 else f"{m2}.{n2}" for m1, n1, n2, m2 in VERSION_ERROR.findall(extra.get("raw_output") or "")]
        if found:
            hints = [KNOWN_REPLACEMENTS[k] for k in dict.fromkeys(found) if k in KNOWN_REPLACEMENTS]
            message["content"] += "\n\n" + " ".join([VERSION_NOTE, *hints])
    return messages


CELL_TIMEOUT_SECONDS = None

INTERRUPT_GRACE_SECONDS = 10

KERNEL_START_SECONDS = None

OUTPUT_SETTLE_SECONDS = 5

OUTPUT_HEAD_CHARS = 4000
OUTPUT_TAIL_CHARS = 8000

KERNEL_PATH = "/tmp/work/repl_kernel.py"

PEEK_DATA = "/opt/peek_data_v7.py"
INPUT_DIR = "/input"

PREVIEW_SECONDS = None

DATA_DIRS = (os.path.join(INPUT_DIR, "environment", "data"), "/app/data")

SCRIPT_NOTE = ("Input-script note: {names} among the inputs are read-only. When the task asks you to fix or run a provided "
               "script, read its text into a string in Python, apply each change with text.replace(old, new) after checking "
               "that old occurs exactly once, write the result to a new file under /tmp in the same cell, and run that file. "
               "Check the new file with py_compile before running it. Multi-line sed replacements easily corrupt code; keep the original untouched so you can start again from it. "
               "Path constants in a provided script (a data directory, say) may name a directory that does not exist in this run: the "
               "inputs are under {root}. When you run the script with subprocess, print the end of its stderr, where the error is. "
               "Order of work: first run it with only the path constants changed and confirm it writes every output file; then fix one error at a time, rerunning after each change and confirming the files are still written (an edit that drops the call to main writes nothing and raises nothing). "
               "Once it runs, recompute every output whose formula the task states (signs and directions included) directly from the task text and compare: a provided script can carry errors you were not told about.")
ZIP_NOTE = ("Input-format note: ZIP archives can be inspected and read directly with Python's standard-library zipfile; "
            "no shell unzip command is needed. Combine member inspection, reading and parsing where practical, and retain "
            "loaded data in the session instead of repeatedly reopening the archive.")

FILING_IO = os.path.join("/opt/msw_session", "filing_io.py")
INLINE_XBRL_NAMESPACE = b"http://www.xbrl.org/2013/inlineXBRL"
DOC_SUFFIXES = (".htm", ".html", ".xhtml")

FILING_NOTE = ("Inline-XBRL note: {names} contain inline-XBRL documents. A reader is installed in the Python session: "
               "from filing_io import read_filing; doc = read_filing(path) (pass member= when a bundle holds more than one). "
               "It returns doc.facts (each tagged fact with its concept, displayed text, converted value with a conversion "
               "status, period, dimension members and unit), doc.tables (each table's rows as a grid, cells with their column "
               "positions), doc.text (visible text), doc.check (counts to print first), and doc.find_facts(part_of_name), "
               "doc.find_rows(text), doc.search_text(pattern), doc.facts_near(pattern) (the facts tagged inside the paragraph or "
               "cell where a phrase appears) and doc.facts_in_context(context_id) (facts that share one context, such as a "
               "security's symbol and title). Facts are dicts. Each table also has a values grid beside its rows, holding "
               "the full converted value (scale and sign applied) of the number tagged in a cell, and multiplier_from_note, "
               "the multiplier its stated unit note gives (check the note's wording); doc.find_values(text) returns "
               "(table index, row texts, row values). Untagged amounts need the table's stated unit applied. "
               "doc.find_tables(text) returns (table index, all its rows) for every table containing the plain text, and "
               "print(doc.show_table(index)) shows one table compactly; table indices differ between documents, so look "
               "them up in each. "
               "It only reads and converts: choosing which fact, row or period "
               "answers the task stays with you, and a value whose status is not ok is left as text. help(read_filing) lists "
               "every field.")

FILING_PREVIEW_SCRIPT = """
import sys
from filing_io import read_filing
short = lambda q: q.split(":")[-1]
for path in sys.argv[1:]:
    doc = read_filing(path)
    print(f"== {path} (document {doc.main}): {doc.check['facts']} facts, {doc.check['tables']} tables")
    for f in doc.facts:
        if (f["concept"] or "").startswith("dei:"):
            value = f["value"] if f["conversion"] == "ok" else f["value_text"][:150]
            members = ", ".join(f"{short(a)}={short(m)}" for a, m in f["members"])
            print(f"{f['concept']} = {value!r}  [context {f['context']}{': ' + members if members else ''}]")
"""
FILING_PREVIEW_INTRO = ("Cover facts of each inline-XBRL input, read with read_filing before your first reply: every fact in the "
                        "dei namespace (document and entity information) as concept = value, with its context id and "
                        "dimension members. Values are converted where the format allows, otherwise shown as text. The same "
                        "facts are in doc.facts; facts that share a context id belong together.")

PREVIEW_INTRO = ("Preview of the task's input files, made before your first reply. Each file is listed at the path a program "
                 "here can open. Text tables show their first 3 lines, their number of physical lines (not always the number "
                 "of records) and their last non-empty line. Parquet files show column types, the header, first 2 rows, and "
                 "the last row when available. Excel files show, for each sheet, the rows above the header, the header row (or "
                 "candidate rows and why the header is not certain), the types and first 2 rows of the data, its last data "
                 "row, row counts, and a pandas call that reads the sheet. JSON files up to 50 KB are shown in full; larger "
                 "ones show their size and a structure outline when available. Values appear as stored in the file. Empty "
                 "preview fields may represent missing values; they do not mean zero. Excel header suggestions and data-row "
                 "counts are inferred; check them against the task. Any skipped content or read errors are marked; open those "
                 "files yourself if you need them. A preview is a sample, not the whole file: compute from the files "
                 "themselves.")

VERIFIER_ROOT = "/opt/msw"

VERIFIER_WORK = "/tmp/verifier"

FILE_LIST_REQUESTS = 2

TASK_STATEMENT = "/input/instruction.md"

OUTPUT_DIR = os.environ.get("SOLVER_OUTPUT_DIR", "/app/output")

OUTPUT_ROOT_PREFIX = re.compile(r"^/?(?:app/)?output/")

KERNEL_SOURCE = '\nimport __future__\nimport ast\nimport difflib\nimport json\nimport linecache\nimport os\nimport re\nimport reprlib\nimport signal\nimport sys\nimport traceback\n\nCTL_IN = os.fdopen(os.dup(0), "r", encoding="utf-8")\nos.dup2(os.open(os.devnull, os.O_RDONLY), 0)\nCTL_OUT = os.fdopen(int(sys.argv[1]), "w", encoding="utf-8")\nMARKER = ("\\n" + sys.argv[2] + "\\n").encode()\nPREIMPORTS = json.loads(sys.argv[3])\nDISPLAY_CHARS = int(sys.argv[4])\nNS = {"__name__": "__main__", "__builtins__": __builtins__}\nFLAGS = 0\nRUNNING = False\nSHOW = reprlib.Repr(maxlevel=4, maxdict=30, maxlist=30, maxtuple=30, maxset=30, maxfrozenset=30, maxdeque=30,\n                    maxarray=30, maxlong=200, maxstring=DISPLAY_CHARS, maxother=DISPLAY_CHARS)\n\n\ndef on_interrupt(signum, frame):\n    if RUNNING:\n        raise KeyboardInterrupt\n\n\ndef send(obj):\n    CTL_OUT.write(json.dumps(obj) + "\\n")\n    CTL_OUT.flush()\n\n\ndef end_of_output():\n    sys.stdout.flush()\n    sys.stderr.flush()\n    os.write(1, MARKER)\n\n\ndef show(value):\n    if type(value).__module__.split(".")[0] in ("pandas", "numpy"):\n        text = repr(value)\n    else:\n        text = SHOW.repr(value)\n    return text if len(text) <= DISPLAY_CHARS else text[:DISPLAY_CHARS] + f" ...(+{len(text) - DISPLAY_CHARS} chars)"\n\n\nMAX_EDIT = 2\nMIN_RATIO = 0.85\nMAX_NAMES = 3\nSHORT = 4\nMIN_KEY = 3\n\n\ndef edit_distance(a, b, cap=MAX_EDIT + 1):\n    if abs(len(a) - len(b)) >= cap:\n        return cap\n    prev = list(range(len(b) + 1))\n    for i, ca in enumerate(a, 1):\n        cur = [i]\n        for j, cb in enumerate(b, 1):\n            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))\n        if min(cur) >= cap:\n            return cap\n        prev = cur\n    return prev[-1]\n\n\ndef missing_keys(error_text):\n    m = re.findall(r"^KeyError: (.+)$", error_text, re.M)\n    if not m:\n        return []\n    msg = m[-1].strip()\n    if msg.startswith(("\'", \'"\')) and msg.endswith(("\'", \'"\')) and "[" not in msg:\n        return [msg[1:-1]]\n    return re.findall(r"\'([^\'\\n]+)\'", msg) if "not in index" in msg or "are in the" in msg else []\n\n\ndef similar_keys_note(error_text, namespace_keys):\n    """One line naming keys close to the missing string key(s), or None. Close: edit distance <= 2 (1 for keys of up to\n    4 characters) or difflib ratio >= 0.85, also compared lower-cased; keys shorter than 3 characters, the key itself\n    and names differing from it only in digits are never suggested. At most 3 names per key, closest first."""\n    keys = missing_keys(error_text)\n    names = [k for k in dict.fromkeys(namespace_keys) if isinstance(k, str)]\n    found = []\n    for key in keys:\n        if len(key) < MIN_KEY:\n            continue\n        scored = []\n        for n in names:\n            if n == key or re.sub(r"\\d", "", n) == re.sub(r"\\d", "", key):\n                continue\n            d = min(edit_distance(key, n), edit_distance(key.lower(), n.lower()))\n            r = difflib.SequenceMatcher(None, key.lower(), n.lower()).ratio()\n            if d <= (MAX_EDIT if len(key) > SHORT else 1) or r >= MIN_RATIO:\n                scored.append((d, -r, n))\n        found += [n for _, _, n in sorted(scored)[:MAX_NAMES] if n not in found]\n    if not found:\n        return None\n    return "Similar names in this object: " + ", ".join(repr(n) for n in found)\n\n\ndef kernel_candidate_keys(exc, ns, limit=5000):\n    """Kernel-side collection for a KeyError: column names / index labels / dict keys of the objects in the failing\n    cell\'s frames (innermost first) and in the session namespace. Strings only, capped."""\n    out = []\n\n    def add(obj):\n        try:\n            if hasattr(obj, "columns") and hasattr(obj, "iloc"):\n                out.extend(c for c in obj.columns if isinstance(c, str))\n            elif hasattr(obj, "index") and hasattr(obj, "iloc") and getattr(obj.index, "dtype", None) == object:\n                out.extend(i for i in obj.index[:limit] if isinstance(i, str))\n            elif isinstance(obj, dict):\n                out.extend(k for k in list(obj)[:limit] if isinstance(k, str))\n        except Exception:\n            pass\n\n    frames = []\n    tb = exc.__traceback__\n    while tb is not None:\n        frames.append(tb.tb_frame)\n        tb = tb.tb_next\n    for f in reversed(frames):\n        if f.f_code.co_filename.startswith("<cell"):\n            for v in f.f_locals.values():\n                add(v)\n    for v in list(ns.values()):\n        add(v)\n    return out[:limit]\n\n\ndef error_text(exc):\n    tb = exc.__traceback__\n    while tb is not None and tb.tb_frame.f_code.co_filename == __file__:\n        tb = tb.tb_next\n    text = "".join(traceback.format_exception(type(exc), exc, tb))\n    return re.sub(r\'  File "<oc_hook>", line \\d+, in [^\\n]*\\n(?:    [^\\n]*\\n)*\', "", text) if "<oc_hook>" in text else text\n\n\ndef run(code, cell):\n    global FLAGS, RUNNING\n    name = f"<cell {cell}>"\n    try:\n        tree = compile(code, name, "exec", FLAGS | ast.PyCF_ONLY_AST, dont_inherit=True)\n        last = ast.Expression(tree.body.pop().value) if tree.body and isinstance(tree.body[-1], ast.Expr) else None\n        body = compile(tree, name, "exec", FLAGS, dont_inherit=True)\n        expr = compile(last, name, "eval", FLAGS, dont_inherit=True) if last is not None else None\n    except (SyntaxError, ValueError, OverflowError) as exc:\n        return {"status": "syntax_error", "error": "".join(traceback.format_exception_only(type(exc), exc))}\n    linecache.cache[name] = (len(code), None, code.splitlines(True), name)\n    for feature in __future__.all_feature_names:\n        flag = getattr(__future__, feature).compiler_flag\n        if body.co_flags & flag:\n            FLAGS |= flag\n    RUNNING = True\n    try:\n        exec(body, NS)\n        value = eval(expr, NS) if expr is not None else None\n        RUNNING = False\n        return {"status": "ok", "display": show(value) if value is not None else ""}\n    except KeyboardInterrupt as exc:\n        RUNNING = False\n        return {"status": "interrupted", "error": error_text(exc)}\n    except BaseException as exc:\n        RUNNING = False\n        text = error_text(exc)\n        if isinstance(exc, KeyError):\n            try:\n                note = similar_keys_note(text, kernel_candidate_keys(exc, NS))\n            except Exception:\n                note = None\n            if note:\n                text = text.rstrip("\\n") + "\\n" + note + "\\n"\n        return {"status": "runtime_error", "error": text}\n\n\ndef main():\n    signal.signal(signal.SIGINT, on_interrupt)\n    imported, failed = [], []\n    for stmt in PREIMPORTS:\n        try:\n            exec(stmt, NS)\n            imported.append(stmt)\n        except Exception as exc:\n            failed.append(f"{stmt}: {type(exc).__name__}: {exc}")\n    try:\n        import pandas\n        pandas.set_option("display.max_rows", 20)\n        pandas.set_option("display.max_columns", 30)\n        pandas.set_option("display.width", 200)\n    except Exception:\n        pass\n    try:\n        import numpy\n        numpy.set_printoptions(threshold=200, edgeitems=3)\n    except Exception:\n        pass\n    end_of_output()\n    send({"ready": True, "imported": imported, "failed": failed})\n    while True:\n        try:\n            line = CTL_IN.readline()\n        except KeyboardInterrupt:\n            continue\n        if not line:\n            return\n        request = json.loads(line)\n        result = run(request["code"], request["cell"])\n        end_of_output()\n        send(result)\n\n\nmain()\n'


class Capture:

    def __init__(self):
        self.head, self.tail, self.dropped, self.full = "", "", 0, False

    def feed(self, text: str) -> None:
        if not self.full:
            self.head += text
            if len(self.head) > OUTPUT_HEAD_CHARS:
                self.head, self.tail, self.full = self.head[:OUTPUT_HEAD_CHARS], self.head[OUTPUT_HEAD_CHARS:], True
        else:
            self.tail += text
        if len(self.tail) > 2 * OUTPUT_TAIL_CHARS:
            self.dropped += len(self.tail) - OUTPUT_TAIL_CHARS
            self.tail = self.tail[-OUTPUT_TAIL_CHARS:]

    def text(self) -> str:
        if self.dropped:
            return f"{self.head}\n...[{self.dropped} characters of output omitted]...\n{self.tail}"
        return self.head + self.tail


class Kernel:

    def __init__(self, cwd: str, env: dict, deadline: float | None = None):
        self.cwd, self.env = cwd, {**env, "PYTHONUNBUFFERED": "1", "MPLBACKEND": "Agg"}
        self.generation, self.cell, self.proc, self.state = 0, 0, None, None
        self.imported: list[str] = []
        self.failed: list[str] = []
        self.restart_note = ""
        self.deadline = deadline

    def start(self) -> None:
        pathlib.Path(KERNEL_PATH).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(KERNEL_PATH).write_text(KERNEL_SOURCE)
        self.generation += 1
        marker = secrets.token_hex(12)
        state = SimpleNamespace(marker="\n" + marker + "\n", lock=threading.Lock(), capture=Capture(),
                                finished=queue.Queue(), results=queue.Queue())
        ctl_r, ctl_w = os.pipe()
        self.proc = subprocess.Popen(["python", KERNEL_PATH, str(ctl_w), marker, json.dumps(PREIMPORTS),
                                      str(OUTPUT_HEAD_CHARS)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, cwd=self.cwd, env=self.env, pass_fds=(ctl_w,),
                                     start_new_session=True)
        os.close(ctl_w)
        self.state = state
        threading.Thread(target=self._read_output, args=(state, self.proc.stdout), daemon=True).start()
        threading.Thread(target=self._read_results, args=(state, os.fdopen(ctl_r, "r", encoding="utf-8")),
                         daemon=True).start()
        ready = self._result(KERNEL_START_SECONDS)
        if not isinstance(ready, dict) or not ready.get("ready"):
            self.close()
            raise RuntimeError(f"the Python session did not start: {ready}")
        self.imported, self.failed = ready["imported"], ready["failed"]
        self._take_output()

    @staticmethod
    def _read_output(state, pipe) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        carry = ""
        while chunk := pipe.read1(65536):
            data = carry + decoder.decode(chunk)
            while (i := data.find(state.marker)) >= 0:
                with state.lock:
                    state.capture.feed(data[:i])
                    state.finished.put(state.capture.text())
                    state.capture = Capture()
                data = data[i + len(state.marker):]
            hold = next((n for n in range(min(len(data), len(state.marker) - 1), 0, -1)
                         if state.marker.startswith(data[-n:])), 0)
            with state.lock:
                state.capture.feed(data[:len(data) - hold])
            carry = data[len(data) - hold:]
        with state.lock:
            state.capture.feed(carry + decoder.decode(b"", final=True))

    @staticmethod
    def _read_results(state, pipe) -> None:
        for line in pipe:
            state.results.put(json.loads(line))
        state.results.put(None)

    def _result(self, timeout):
        try:
            return self.state.results.get(timeout=timeout)
        except queue.Empty:
            return "timeout"

    def _take_output(self, wait: float = OUTPUT_SETTLE_SECONDS) -> tuple[str, bool]:
        try:
            return self.state.finished.get(timeout=wait), True
        except queue.Empty:
            return "", False

    def _restart(self, cause: str) -> None:
        self.close()
        self.start()
        for code in getattr(self, "preloads", []):
            cell = self.cell
            with contextlib.suppress(Exception):
                self.run(code)
            self.cell = cell
        self.restart_note = (f"The Python session {cause} and was restarted (generation {self.generation}): all variables, "
                             "functions and loaded data are gone; only the preloaded imports are back.")

    def run(self, code: str) -> dict:
        if self.proc is None or self.proc.poll() is not None:
            self._restart("had ended before this cell")
        self.cell += 1
        self.sources = getattr(self, "sources", {})
        self.sources[self.cell] = code
        with self.state.lock:
            background, self.state.capture = self.state.capture.text(), Capture()
        self.proc.stdin.write((json.dumps({"code": code, "cell": self.cell}) + "\n").encode())
        self.proc.stdin.flush()
        started = time.time()
        limit = None if self.deadline is None else max(1.0, self.deadline - started)
        result = self._result(limit if CELL_TIMEOUT_SECONDS is None else min(CELL_TIMEOUT_SECONDS, limit or CELL_TIMEOUT_SECONDS))
        note = ""
        if result == "timeout":
            os.kill(self.proc.pid, signal.SIGINT)
            result = self._result(INTERRUPT_GRACE_SECONDS)
            note = (f"The cell was still running {round(time.time() - started)} s after it started, close to the task's time "
                    "limit, and was interrupted. Variables from earlier cells are kept if the session survived; write the "
                    "required files now from what you have.")
        if result in ("timeout", None):
            printed, _ = self._take_output(0)
            self._restart("did not stop when interrupted" if result == "timeout" else "ended unexpectedly")
            result = {"status": "kernel_lost"}
        else:
            printed, complete = self._take_output()
            if not complete:
                note += " Output printed after the cell finished may be missing."
        return self._observation(result, background, printed, note.strip(), time.time() - started)

    def _observation(self, result: dict, background: str, printed: str, note: str, seconds: float) -> dict:
        status = result["status"]
        parts = [f"[python cell {self.cell} | session generation {self.generation} | {status} | {seconds:.1f} s]"]
        if self.restart_note:
            parts.append(self.restart_note)
            self.restart_note = ""
        if background.strip():
            parts.append("[output printed by background work since the previous cell]\n" + background)
        if printed:
            parts.append(printed)
        if result.get("display"):
            parts.append(result["display"])
        if result.get("error"):
            parts.append(result["error"][-3000:])
        if status == "syntax_error":
            parts.append("Nothing in this cell was run.")
        elif status in ("runtime_error", "interrupted"):
            parts.append("The statements before the error have already run; their assignments and any files they "
                         "wrote are kept, and nothing was rolled back.")
        if note:
            parts.append(note)
        return {"output": "\n".join(parts), "returncode": 0 if status == "ok" else 1, "exception_info": "",
                "extra": {"python_cell": self.cell, "session_generation": self.generation, "cell_status": status}}

    def close(self) -> None:
        if self.proc is not None:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            self.proc.wait()
            self.proc = None


FIX_LINE_ON = VA_STEPS == "fix_line"
FIX_LINE_BLOCK_OK, FIX_LINE_QUOTE_CHECK, FIX_LINE_KEYWORD_RECHECK = True, True, True
VA_PENDING: list = []
VA_FIX_REFUSALS: dict = {}
try:
    import importlib.util as _fl_iu
    _fl_spec = _fl_iu.spec_from_file_location("va2", os.path.join(QFREF_ROOT, "qfref", "va2.py"))
    VA2 = _fl_iu.module_from_spec(_fl_spec)
    _fl_spec.loader.exec_module(VA2)
    FIX_LINE_TOOL = VA2.FIX_LINE_TOOL
except Exception:
    VA2, FIX_LINE_TOOL, FIX_LINE_ON = None, None, False
_BASH_LINE = "- bash: runs one shell command in a new subshell each time. Use it for file-system work and to submit.\n"


def fix_line_system(template: str) -> str:
    if not FIX_LINE_ON or _BASH_LINE not in template:
        return template
    return (template.replace("You have two tools:", "You have three tools:", 1)
            .replace(_BASH_LINE, _BASH_LINE + VA2.SYSTEM_LINES["fix_line"] + "\n", 1))


def _fl_result(text: str, ok: bool) -> dict:
    return {"output": text, "returncode": 0 if ok else 1, "exception_info": "", "extra": {"fix_line": ok}}


def _fl_site(new_line: str):
    for site in reversed(VA_PENDING):
        name = site["fn"].rsplit(".", 1)[-1]
        if re.search(r"\b(nan)?" + re.escape(name.removeprefix("nan")) + r"\s*\(", new_line) or name in new_line:
            return site
    return VA_PENDING[-1] if VA_PENDING else None


def fix_line_execute(kernel, action: dict) -> dict:
    new, reason = action.get("new_line") or "", action.get("reason") or ""
    site = _fl_site(new)
    if VA2 is None or site is None:
        return _fl_result("Not applied: no API check is open for `fix_line`; change code with `python`.", False)
    n, old = site["cell"], site["line"]
    sources = getattr(kernel, "sources", {})
    if n not in sources:
        return _fl_result(f"Not applied: cell {n} is no longer in this session; change code with `python`.", False)
    key = f"{n}:{old.strip()}"
    consistency = VA2.consistency_fix(sources[n], reason)
    if not consistency and FIX_LINE_QUOTE_CHECK and VA2.task_driven(site["fn"]):
        try:
            statement = pathlib.Path(TASK_STATEMENT).read_text()
        except OSError:
            statement = ""
        line_in = VA2.block_line(sources[n], new)[0] if FIX_LINE_BLOCK_OK else new
        quoted, why = VA2.quotes_task(reason, statement, site["fn"], old, line_in or new)
        claims_none = VA2.NO_REQUIREMENT.search(reason) or VA2.CHECKLIST_REASON.search(reason) or VA2.DOES_NOT_APPLY.search(reason)
        if VA_FIX_REFUSALS.get(key, 0) < VA2.QUOTE_MAX_REFUSALS:
            if not quoted:
                VA_FIX_REFUSALS[key] = VA_FIX_REFUSALS.get(key, 0) + 1
                return _fl_result(VA2.QUOTE_REFUSED, False)
            if claims_none and FIX_LINE_KEYWORD_RECHECK and (found := VA2.keyword_in_task(site["fn"], statement)):
                VA_FIX_REFUSALS[key] = VA_FIX_REFUSALS.get(key, 0) + 1
                return _fl_result(VA2.KEYWORD_REFUSED.format(sentence=found[1]), False)
    if FIX_LINE_BLOCK_OK:
        line, err = VA2.block_line(sources[n], new)
        if err:
            return _fl_result(f"Not applied: {err}. Call `fix_line` again with the corrected line.", False)
        new = line
    ok, why = VA2.check_new_line(old, new)
    edited, err = VA2.replace_line(sources[n], old, new) if ok else (None, why)
    if err:
        return _fl_result(err if err == VA2.MIXED_DDOF_REFUSED else f"Not applied: {err}. Call `fix_line` again with the corrected line.", False)
    if consistency and (left := VA2.still_mixed(edited)):
        return _fl_result(left, False)
    last = max(sources)
    later = VA2.downstream_cells({**sources, n: edited}, n)
    kept = dict(sources)
    kernel._restart("was rebuilt to apply fix_line")
    kernel.restart_note = ""
    for k in sorted(c for c in kept if c < n):
        kernel.cell = k - 1
        kernel.run(kept[k])
    kernel.cell = n - 1
    out = kernel.run(edited)
    parts = [f"Applied: cell {n} line now reads `{new.strip()}`. Cell {n} ran again:", out["output"]]
    for k in later:
        kernel.cell = k - 1
        parts += [f"Cell {k} (uses its results) ran again:", kernel.run(kept[k])["output"]]
    kernel.cell = last
    kernel.sources = {**kept, n: edited}
    VA_PENDING[:] = [s for s in VA_PENDING if s is not site]
    print(f"[solver] fix_line applied at cell {n}; {len(later)} later cell(s) rerun", flush=True)
    return _fl_result("\n".join(parts), out["returncode"] == 0)


class ReplEnvironment:

    def __init__(self, env, kernel: Kernel):
        self._env, self.kernel = env, kernel

    def execute(self, action: dict, cwd: str = "", *, timeout: int | None = None) -> dict:
        if action.get("tool") == "python":
            return self.kernel.run(action["code"])
        if action.get("tool") == "fix_line":
            return fix_line_execute(self.kernel, action)
        return self._env.execute(action, cwd, timeout=timeout)

    def __getattr__(self, name):
        return getattr(self._env, name)


PYTHON_TOOL = {"type": "function", "function": {
    "name": "python",
    "description": ("Run Python code in the persistent Python session, like a Jupyter notebook cell. Variables, functions "
                    "and imports persist between calls; the value of a final expression is shown."),
    "parameters": {"type": "object", "properties": {"code": {"type": "string", "description": "The Python code to run"}},
                   "required": ["code"]}}}

FORMAT_ERROR_TEMPLATE = """\
{% if finish_reason is defined and (finish_reason == "length" or (finish_reason == "tool_calls" and not has_tool_calls)) -%}
Your previous response reached the output token limit (finish_reason={{ finish_reason }}) before you produced a tool call, so it was cut off.
{%- else -%}
Tool call error:
<error>
{{error}}
</error>
Every response needs exactly one tool call: python with {"code": "..."} to run Python in the session, or bash with
{"command": "..."} to run a shell command. To end the task, issue `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` with the
bash tool, without any other command.
{%- endif %}
"""

TOOL_ARGS = {"bash": "command", "python": "code"}


def _format_error(model, finish_reason, error: str, has_tool_calls: bool = True) -> FormatError:
    content = Template(model.config.format_error_template, undefined=StrictUndefined).render(
        actions=[], error=error, has_tool_calls=has_tool_calls, finish_reason=finish_reason)
    return FormatError({"role": "user", "content": content, "extra": {"interrupt_type": "FormatError"}})


def _action(name: str, text: str, call_id: str | None = None) -> dict:
    action = {"command": text} if name == "bash" else {"tool": "python", "code": text, "command": text}
    return {**action, "tool_call_id": call_id} if call_id is not None else action


def parse_tool_actions(model, response) -> list[dict]:
    choice = response.choices[0]
    calls = choice.message.tool_calls or []
    if not calls:
        raise _format_error(model, choice.finish_reason, "No tool calls found in the response.", has_tool_calls=False)
    actions = []
    for call in calls:
        name = call.function.name
        if name == "fix_line" and FIX_LINE_ON:
            try:
                args = json.loads(call.function.arguments)
            except Exception as exc:
                raise _format_error(model, choice.finish_reason, f"Error parsing tool call arguments: {exc}.") from None
            if not isinstance(args, dict) or not isinstance(args.get("new_line"), str):
                raise _format_error(model, choice.finish_reason, "Missing or non-text 'new_line' argument in fix_line call.")
            actions.append({"tool": "fix_line", "new_line": args["new_line"], "reason": str(args.get("reason") or ""),
                            "command": "fix_line " + args["new_line"], "tool_call_id": call.id})
            continue
        if name not in TOOL_ARGS:
            raise _format_error(model, choice.finish_reason, f"Unknown tool '{name}'.")
        try:
            args = json.loads(call.function.arguments)
        except Exception as exc:
            raise _format_error(model, choice.finish_reason, f"Error parsing tool call arguments: {exc}.") from None
        if not isinstance(args, dict) or not isinstance(args.get(TOOL_ARGS[name]), str):
            raise _format_error(model, choice.finish_reason, f"Missing or non-text '{TOOL_ARGS[name]}' argument in {name} call.")
        actions.append(_action(name, args[TOOL_ARGS[name]], call.id))
    return actions


TEXT_ACTION = re.compile(r"```mswea_(bash|python)_command\s*\n(.*?)\n```", re.DOTALL)


def parse_text_actions(model, response) -> list[dict]:
    content = response.choices[0].message.content or ""
    found = TEXT_ACTION.findall(content)
    if len(found) != 1:
        raise FormatError({"role": "user", "content": Template(model.config.format_error_template, undefined=StrictUndefined).render(
            actions=[b for _, b in found], error=f"Expected exactly 1 action, found {len(found)}.",
            finish_reason=response.choices[0].finish_reason),
            "extra": {"interrupt_type": "FormatError", "n_actions": len(found), "model_response": content}})
    kind, body = found[0]
    return [_action(kind, body.strip())]


TASK_TAG = True
TASK_TAG_NOTE = ("The task instructions are the text inside <task_instructions> in the first message; \"the task\" and \"the "
                 "task text\" in these instructions refer to it.")


def tag_task_text(task: str) -> str:
    try:
        statement = pathlib.Path(TASK_STATEMENT).read_text()
    except OSError:
        print("[solver] task tag: instruction file not readable, message left untagged", flush=True)
        return task
    statement = statement.replace("Save scripts and scratch files in /tmp/work", "Save scratch files in /tmp/work").strip()
    i = task.find(statement)
    if not statement or i < 0:
        print("[solver] task tag: task text not found in the first message, message left untagged", flush=True)
        return task
    j = i + len(statement)
    print(f"[solver] task tag: characters {i}-{j} of the first message", flush=True)
    return task[:i] + "<task_instructions>\n" + task[i:j] + "\n</task_instructions>" + task[j:]


def match_text(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


LIBREF_TITLE = "LibraryReference (verified usage of the installed libraries; where the task text differs, follow the task text):"
LIBREF_BUDGET = 3500
LIBREF_LISTED_BUDGET = 12000
LIBREF_PRECEDENCE = "When the task text specifies how to build something or forbids a function, follow the task text."
LIBREF_VERSION_LINE = re.compile(r"^(.*?) (?:is|are) installed\. Use only APIs that exist in this version: not older removed forms, "
                                 r"and not newer or unverified ones\.\n+")
LIBREF_STOP = set("a an and are as at be by for from has have in into is it its of on or that the this to with without was were will "
                  "which when where while not no use using used each per than then their there these those via can may must should do "
                  "does all any both but if only same such other also more most over under between within task output file files value "
                  "values compute computed computes calculate return returns result results data input inputs".split())
LIBREF_LIB_WORDS = {"statsmodels": ["statsmodels"], "arch": ["arch package", "arch_model", "from arch", "import arch"],
                    "polars": ["polars"], "talib": ["ta-lib", "talib"], "backtrader": ["backtrader"], "sklearn": ["scikit-learn", "sklearn"],
                    "pyarrow": ["pyarrow"], "openpyxl": ["openpyxl"], "matplotlib": ["matplotlib"], "seaborn": ["seaborn"],
                    "plotly": ["plotly"], "scipy": ["scipy"]}


LIBREF_NOT_ROUTED = {"library_reference_howto_cash_clock"}
LIBREF_CUES = {"library_reference_howto_dates_align": re.compile(
                   r"\btrading (?:day|date|calendar)|\bcalendar\b|\btimestamp|\bdate column|\bas[- ]of\b|\bbusiness day|"
                   r"\bsettlement date|\bmonth[- ]end", re.I),
               "library_reference_howto_distribution": re.compile(
                   r"\bnormal cdf|\bcumulative normal|\bN\(d[12]\)|\bstudent|\bt[- ]distribution|\bpareto|\blognormal|"
                   r"\bmaximum likelihood|\bMLE\b|\.fit\(|\bppf\b|\bcdf\b", re.I),
               "library_reference_howto_optimize": re.compile(
                   r"\bcalibrat|\bminimi[sz]e|\broot[- ]find|\bbrentq|\bnewton|\bSLSQP|\bleast squares|\bsolve for\b|"
                   r"\bimplied (?:vol|yield|rate)", re.I)}


def libref_norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKC", text).lower()).strip() + " "


def libref_tokens(text: str) -> list[str]:
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", unicodedata.normalize("NFKC", text).lower())
    out = []
    for token in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text):
        parts = token.split("-")
        for p in parts + ([''.join(parts)] if len(parts) > 1 else []):
            if len(p) >= 2 and not p.isdigit() and p not in LIBREF_STOP:
                out.append(p[:-1] if len(p) > 4 and p.endswith("s") and not p.endswith("ss") else p)
    return out


def library_block() -> str:
    root = pathlib.Path(QFREF_ROOT, "qfref", "entries")
    try:
        text = pathlib.Path(TASK_STATEMENT).read_text()
        meta = json.loads((root / "library_reference_operations.json").read_text())
        bodies, versions = {}, {}
        for n in meta:
            body = (root / f"{n}.md").read_text().rstrip()
            m = LIBREF_VERSION_LINE.match(body)
            versions[n] = [v.strip() for v in m.group(1).split(";")] if m else []
            bodies[n] = body[m.end():].replace(LIBREF_PRECEDENCE + "\n\n", "", 1) if m else body
    except (OSError, ValueError, KeyError) as exc:
        print(f"[solver] LibraryReference not added: {type(exc).__name__}", flush=True)
        return ""
    listed = (json.loads(pathlib.Path(LISTED_ENTRIES).read_text()) if os.path.isfile(LISTED_ENTRIES) else [])
    listed = [n for n in dict.fromkeys(listed) if n.startswith("library_reference")]
    for n in listed:
        if n not in bodies:
            body = (root / f"{n}.md").read_text().rstrip()
            m = LIBREF_VERSION_LINE.match(body)
            versions[n] = [v.strip() for v in m.group(1).split(";")] if m else []
            bodies[n] = body[m.end():].replace(LIBREF_PRECEDENCE + "\n\n", "", 1) if m else body
    norm = libref_norm(text)
    hits = {n: [k for k in m["match"] if libref_norm(k) in norm] for n, m in meta.items()}
    hits = {n: k for n, k in hits.items() if k}
    docs = {n: libref_tokens(m["line"] + " " + m["summary"] + " " + " ".join(m["match"])) for n, m in meta.items()}
    tf = {n: collections.Counter(d) for n, d in docs.items()}
    avg = sum(map(len, docs.values())) / len(docs)
    df = collections.Counter(t for d in docs.values() for t in set(d))
    idf = {t: math.log(1 + (len(docs) - c + .5) / (c + .5)) for t, c in df.items()}
    query = set(libref_tokens(re.sub(r"\b[\w.-]+\.(?:csv|json|parquet|pqt|xlsx|txt|md|py|png|html)\b", " ",
                                     re.sub(r"(?:/app|/input|/output)/\S+", " ", text))))
    raw = {n: sum(idf[t] * c[t] * 2.2 / (c[t] + 1.2 * (.25 + .75 * len(docs[n]) / avg)) for t in query if t in c) for n, c in tf.items()}
    score = {n: raw[n] + 2.0 * min(len(hits.get(n, [])), 3) for n in meta}
    names = sorted(hits if hits else [n for n in meta if raw[n] >= 4.0], key=lambda n: (-score[n], n))[:5 if hits else 3]
    low = text.lower()
    named = {}
    for n, m in meta.items():
        found = [a for a in m["apis"] if len(a.rsplit(".", 1)[-1]) >= 5 and re.search(
            r"(?<![\w])" + re.escape(a.rsplit(".", 1)[-1]) + r"\s*\(|[.`]" + re.escape(a.rsplit(".", 1)[-1]) + r"\b", text)]
        found += [lib for lib in m["libraries"] if any(w in low for w in LIBREF_LIB_WORDS.get(lib, []))]
        if found:
            named[n] = found
    names += sorted((n for n in named if n not in names), key=lambda n: (-len(named[n]), -score[n], n))
    names = [n for n in names if n not in LIBREF_NOT_ROUTED and rag_gate_ok(n, text)]
    names += [n for n, rx in LIBREF_CUES.items() if rx.search(text) and n not in names and n in bodies]

    def render(chosen):
        vers = list(dict.fromkeys(v for n in chosen for v in versions[n]))
        head = (LIBREF_TITLE + "\n" + "; ".join(vers) + " are installed. Use only APIs that exist in these versions: not older "
                "removed forms, and not newer or unverified ones.\n" + LIBREF_PRECEDENCE)
        return head + "\n\n" + "\n\n".join(bodies[n] for n in chosen)
    chosen = []
    for n in listed or names:
        if len(render(chosen + [n])) <= (LIBREF_LISTED_BUDGET if listed else LIBREF_BUDGET):
            chosen.append(n)
    block = render(chosen) if chosen else ""
    print(f"[solver] LibraryReference attached: {chosen} ({len(block)} characters; phrase hits {sorted(hits)}; named {sorted(named)})",
          flush=True)
    return block


RAG_INDEX = os.path.join(QFREF_ROOT, "rag_index_v1.json")
RAG_LIBRARY_GATE = {"library_reference_arch": ("garch", "arch_model", "arch "), "library_reference_statsmodels": ("statsmodels", "ols", "regression"),
                    "library_reference_sklearn": ("sklearn", "scikit", "pca", "kmeans", "gaussianmixture", "hmm"),
                    "library_reference_polars": ("polars",), "library_reference_backtrader": ("backtrader",),
                    "library_reference_talib": ("talib", "ta-lib"), "library_reference_howto_polars": ("polars",),
                    "library_reference_howto_pca": ("pca", "principal component", "eigen"),
                    "library_reference_howto_indicators": ("talib", "ta-lib")}


def rag_gate_ok(name: str, text: str) -> bool:
    words = RAG_LIBRARY_GATE.get(name)
    return not words or any(re.search(r"(?<![a-z])" + re.escape(w.strip()) + r"(?![a-z])", text, re.I) for w in words)
RAG_LIBRARY_BUDGET = 3500
RAG_INTRO = ("Further library usage notes chosen for this task from the knowledge base "
             "(where the task text differs, follow the task text):")
RAG_STOP = set("a an and are as at be by for from has have in into is it its of on or that the this to with without was were "
               "will each per not no all any can must should use using used if than then their these those which when where "
               "only also both such may one two file files output outputs column columns json csv value values".split())


def rag_stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("ses", "xes", "ches", "shes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def rag_tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z0-9_]+", text.lower()) if w not in RAG_STOP and len(w) > 2]


def rag_secondary(text: str, index: dict, exclude: set, primary_text: str) -> list[dict]:
    atoms = index["atoms"]
    docs_tok = [rag_tokens(a["title"] + " " + a["text"]) for a in atoms]
    avg = sum(map(len, docs_tok)) / max(len(docs_tok), 1)
    df = collections.Counter(w for d in docs_tok for w in set(d))
    idf = {w: math.log(1 + (len(docs_tok) - c + .5) / (c + .5)) for w, c in df.items()}
    q = set(rag_tokens(text))
    score = []
    for d in docs_tok:
        c = collections.Counter(d)
        score.append(sum(idf[w] * c[w] * 2.2 / (c[w] + 1.2 * (.25 + .75 * len(d) / avg)) for w in q if w in c))
    fns = collections.Counter(f for f in re.findall(r"([A-Za-z_][A-Za-z0-9_]{3,})\s*\(", primary_text + "\n" + text))
    named = (primary_text + "\n" + text).lower()
    allowed = lambda a: a["type"] == "api" or rag_gate_ok(a["base"], named)
    lib_fn = sorted((i for i, a in enumerate(atoms) if a["type"] == "libref" and a["base"] not in exclude
                     and a["base"] not in LIBREF_NOT_ROUTED and set(a["targets"]) & set(fns) and allowed(a)),
                    key=lambda i: (-sum(fns[f] for f in atoms[i]["targets"]), -score[i]))
    lib_bm = sorted((i for i, a in enumerate(atoms) if a["type"] == "libref" and a["base"] not in exclude
                     and a["base"] not in LIBREF_NOT_ROUTED and allowed(a)),
                    key=lambda i: -score[i])
    chosen, used = [], 0
    for i in lib_fn + lib_bm:
        if i not in chosen and used + atoms[i]["chars"] <= RAG_LIBRARY_BUDGET:
            chosen.append(i)
            used += atoms[i]["chars"]
    return [atoms[i] for i in chosen]


def rag_secondary_block(exclude: set, primary_text: str) -> str:
    try:
        index = json.loads(pathlib.Path(RAG_INDEX).read_text())
        text = pathlib.Path(TASK_STATEMENT).read_text()
    except (OSError, ValueError) as exc:
        print(f"[solver] secondary retrieval not added: {type(exc).__name__}", flush=True)
        return ""
    chosen = rag_secondary(text, index, exclude, primary_text)
    print(f"[solver] secondary retrieval attached: {len(chosen)} atoms, {sum(a['chars'] for a in chosen)} characters: "
          f"{[a['id'] for a in chosen]}", flush=True)
    return RAG_INTRO + "\n\n" + "\n\n".join(f"### {a['title']}\n{a['text']}" for a in chosen) if chosen else ""


def reference_block() -> str:
    root = pathlib.Path(QFREF_ROOT, "qfref", "entries")
    try:
        index = json.loads((root / "index.json").read_text())
        text = match_text(pathlib.Path(TASK_STATEMENT).read_text())
        names = [n for n, e in index.items()
                 if not n.startswith("library_reference") and any(match_text(t) in text for t in e["match"])]
        dropped = {m for n in names for m in index[n].get("supersedes", [])}
        names = [n for n in names if n not in dropped]
        names = list(dict.fromkeys(m for n in names for m in [n] + index[n].get("requires", [])))
        if os.path.isfile(LISTED_ENTRIES):
            names = [n for n in dict.fromkeys(json.loads(pathlib.Path(LISTED_ENTRIES).read_text()))
                     if not n.startswith("library_reference")]
            missing = [n for n in names if n not in index or not (root / f"{n}.md").is_file()]
            if missing:
                raise SystemExit(f"[solver] listed qfref entries not in the package: {missing}")
            print("[solver] reference entries listed by the run plan: " + ", ".join(
                f"{n} {hashlib.sha256((root / f'{n}.md').read_bytes()).hexdigest()[:12]}" for n in names), flush=True)
        body = "\n\n".join((root / f"{n}.md").read_text().rstrip() for n in names)
    except (OSError, ValueError, KeyError) as exc:
        print(f"[solver] reference not added: {type(exc).__name__}", flush=True)
        return ""
    print(f"[solver] reference entries attached: {names}", flush=True)
    return QFREF_INTRO + "\n\n" + body if body else ""


def data_preview(env: dict) -> str:
    try:
        p = subprocess.run(["python", PEEK_DATA, INPUT_DIR], capture_output=True, text=True, env=env, timeout=PREVIEW_SECONDS)
    except Exception as exc:
        print(f"[solver] input preview not added: {type(exc).__name__}", flush=True)
        return ""
    if p.returncode not in (0, 3) or not p.stdout.strip():
        print(f"[solver] input preview not added: peek_data exited {p.returncode}", flush=True)
        return ""
    body = re.sub(r"^== ", f"== {INPUT_DIR}/", p.stdout.strip(), flags=re.M)
    if FULL_TEXT_PREVIEW:
        with contextlib.suppress(Exception):
            body = full_text_preview(body)
    if HEADER_DETECT:
        with contextlib.suppress(Exception):
            body = header_detect_preview(body, env)
    return PREVIEW_INTRO + "\n\n" + body


def script_inputs() -> list[str]:
    return sorted({n for root in DATA_DIRS for _, _, names in os.walk(root) for n in names if n.endswith(".py")})


def zip_inputs() -> list[str]:
    found = set()
    for root in DATA_DIRS:
        for dirpath, _, names in os.walk(root):
            for n in names:
                if n.lower().endswith(".zip") and zipfile.is_zipfile(os.path.join(dirpath, n)):
                    found.add(n)
    return sorted(found)


def filing_preview(env: dict, names: list[str]) -> str:
    paths = []
    for name in names:
        for dirpath, _, files in os.walk(DATA_DIRS[0]):
            if name in files:
                paths.append(os.path.join(dirpath, name))
                break
    try:
        p = subprocess.run(["python", "-c", FILING_PREVIEW_SCRIPT, *paths], capture_output=True, text=True, timeout=120,
                           env=env | {"PYTHONPATH": os.pathsep.join(filter(None, [SESSION_IO_ROOT, env.get("PYTHONPATH")]))})
    except Exception as exc:
        print(f"[solver] filing preview not added: {type(exc).__name__}", flush=True)
        return ""
    if p.returncode != 0 or not p.stdout.strip():
        print(f"[solver] filing preview not added: exit {p.returncode} {p.stderr[-300:]}", flush=True)
        return ""
    return FILING_PREVIEW_INTRO + "\n\n" + p.stdout.strip()


def inline_xbrl_inputs() -> list[str]:
    found = set()
    for root in DATA_DIRS:
        for dirpath, _, names in os.walk(root):
            for n in names:
                path = os.path.join(dirpath, n)
                try:
                    if n.lower().endswith(".zip") and zipfile.is_zipfile(path):
                        with zipfile.ZipFile(path) as z:
                            if any(m.lower().endswith(DOC_SUFFIXES) and INLINE_XBRL_NAMESPACE in z.read(m) for m in z.namelist()):
                                found.add(n)
                    elif n.lower().endswith(DOC_SUFFIXES):
                        with open(path, "rb") as f:
                            if INLINE_XBRL_NAMESPACE in f.read():
                                found.add(n)
                except (OSError, zipfile.BadZipFile):
                    continue
    return sorted(found)


def _verifier_modules():
    import shutil
    import sys
    sys.path[:0] = [f"{VERIFIER_ROOT}/verifier-agent", f"{VERIFIER_ROOT}/verifier-agent/v3.1"]
    import verifier_agent_v3_1 as v31
    import verifier_agent_v8_5 as v85

    def run_suite(suite, candidate_dir, image=None, timeout=300):
        stage = pathlib.Path(VERIFIER_WORK) / "stage" / secrets.token_hex(6)
        try:
            (stage / "suite").mkdir(parents=True)
            shutil.copyfile(suite, stage / "suite" / "test_outputs.py")
            p = subprocess.run(["python", "-m", "pytest", "test_outputs.py", "-v", "--no-header", "-p", "no:cacheprovider",
                                "-o", "addopts=", "--tb=line"], cwd=stage / "suite", capture_output=True, text=True,
                               env={**os.environ, "OUTPUT_DIR": str(candidate_dir), "PYTHONDONTWRITEBYTECODE": "1"})
            return v31.read_report(p.stdout + p.stderr, p.returncode)
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    v31.run_suite, v31.ensure_image, v31._git_commit = run_suite, (lambda: "in-container"), (lambda: "unknown")
    v31.STAGE_ROOT = pathlib.Path(VERIFIER_WORK) / "v31-stage"
    return v31, v85


def charge_driver_request() -> None:
    sent = getattr(sys.modules.get("__main__"), "REQUESTS_SENT", None)
    if sent is None:
        return
    budget = int(os.environ.get("MINI_REQUEST_BUDGET", "0") or 0)
    if budget and sent[0] >= budget:
        raise RuntimeError("the task's request allowance is spent")
    sent[0] += 1


REMINDER_PROBLEMS = "A check of the files as written found these problems against the task's output section:\n{problems}"

SUBMIT_CHECK = ("Not submitted yet: a check of the files as written found these problems against the task's output section "
                "(the task text is the authority):\n{problems}\nFix them and submit again; if you have checked that an item "
                "is correct as written, submit again unchanged.")

STATUS_DEFINITE = ("Problems in the files as written (a submit is held until they are fixed or confirmed); fix them in the "
                   "step that produces the values:")

STATUS_DOUBTS = "Worth a second look in the files as written (not blocking):"

SUBMIT_DOUBTS = ("Held once to show these points from a check of the files as written; the next submit goes through even if "
                 "nothing changes. Each may be intended (for example a unit the task does not state):\n{doubts}")

NEW_ITEM = re.compile(r"^\s*(?:\d+[.)]\s|[-*]\s|#{1,6}\s|-{3,}\s*$)")


NOT_FIELDS = {"null", "none", "nan", "true", "false", "float", "int", "bool", "str", "yyyy-mm-dd"}
FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def named_fields(entry: str, files: list[str]) -> list[str]:
    names = re.findall(r'`([^`\n]+)`|"([A-Za-z_][A-Za-z0-9_]*)"', entry)
    out = []
    for a, b in names:
        n = (a or b).strip().strip('"')
        if FIELD.match(n) and n.lower() not in NOT_FIELDS and n not in files and n not in out:
            out.append(n)
    return out


HEADER_LINE = re.compile(r"^\s*`?\s*([A-Za-z_][A-Za-z0-9_]*(?:[-.][A-Za-z0-9_]+)*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*(?:[-.][A-Za-z0-9_]+)*)+)\s*`?\s*$")


LISTED_FIELD = re.compile(r"^(\s*)([-*+]|\d+[.)]|\|)\s*`([A-Za-z_][A-Za-z0-9_]*)`\s*($|[:(|,\u2014\u2013-])", re.M)


NAMED_IN_PROSE = re.compile(r"\b(?:header|column|field|key)\s+(?:is|named|called)\s+`([A-Za-z_][A-Za-z0-9_]*)`", re.I)


def listed_names(entry: str, files: list[str]) -> list[str]:
    out = []
    listed = [name for indent, marker, name, rest in LISTED_FIELD.findall(entry) if rest or (not indent and marker in "-*+")]
    for n in listed + NAMED_IN_PROSE.findall(entry):
        if n.lower() not in NOT_FIELDS and n not in files and n not in out:
            out.append(n)
    return out


SOLE_PLACEHOLDER_KEY = re.compile(r'\{\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*\{\s*(?:"[A-Za-z_][A-Za-z0-9_]*"\s*:\s*)?\.\.\.\s*\}\s*,?\s*\}')


def json_key_names(entry: str, files: list[str]) -> list[str]:
    keyed = re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', entry)
    placeholders = set(SOLE_PLACEHOLDER_KEY.findall(entry))
    keyed = [n for n in keyed if n not in placeholders]
    out = []
    for n in keyed + listed_names(entry, files):
        if n.lower() not in NOT_FIELDS and n not in files and n not in out:
            out.append(n)
    return out


TEMPLATE_KEY = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*\{[A-Za-z]+\}[A-Za-z0-9_{}]*)")


def template_values(statement: str, name: str) -> list[str]:
    m = re.search(rf"\beach\s+{re.escape(name)}\s*\(([^)]+)\)|\b{re.escape(name)}s?\s*\(([^)]+)\)", statement, re.I)
    if not m:
        return []
    vals = [v.strip().strip("`'\"") for v in (m.group(1) or m.group(2)).split(",")]
    return vals if vals and all(re.fullmatch(r"[A-Za-z0-9_]+", v) for v in vals) else []


def expanded_template_keys(entry: str, statement: str) -> list[str]:
    out = []
    for t in dict.fromkeys(TEMPLATE_KEY.findall(entry)):
        names = re.findall(r"\{([A-Za-z]+)\}", t)
        values = {n: template_values(statement, n) for n in names}
        if any(not v for v in values.values()):
            continue
        keys = [t]
        for n in names:
            keys = [k.replace("{" + n + "}", v, 1) for k in keys for v in values[n]]
        out += [k for k in keys if k not in out]
    return out


NUMBERED_COLUMN = re.compile(r"^\s*\d+[.)]\s+`([A-Za-z_][A-Za-z0-9_]*)`\s*$")


def header_columns(entry: str, name: str, files: list[str]) -> list[str]:
    lines, joined, buf = entry.splitlines(), [], ""
    others = [f for f in files if f != name]
    for line in lines:
        if any(f in line for f in others):
            break
        buf = (buf + line.strip()) if buf else line
        if buf.rstrip().endswith(","):
            continue
        joined.append(buf)
        buf = ""
    out = []
    for line in joined:
        listed = re.search(r"\bcolumns?\s*:\s*([^.;(]+)", line, re.I)
        if listed:
            names = [c.strip().strip("`*").strip() for c in listed.group(1).split(",")]
            names = [c for c in names if c]
            if len(names) >= 2 and all(FIELD.match(c) for c in names):
                out += [c for c in names if c not in out]
                continue
        if (m := HEADER_LINE.match(line)):
            out += [c.strip() for c in m.group(1).split(",") if c.strip() not in out]
    for i, line in enumerate(lines):
        if re.search(r"\bcolumns?\s*:\s*$", line, re.I):
            items = []
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    if items:
                        break
                    continue
                m = NUMBERED_COLUMN.match(nxt)
                if not m:
                    break
                items.append(m.group(1))
            if len(items) >= 2:
                out += [c for c in items if c not in out]
    return out


def json_paths(value, prefix=""):
    if isinstance(value, dict):
        if not value:
            yield prefix, value
        for k, v in value.items():
            yield from json_paths(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(value, list):
        if not value:
            yield prefix, value
        for i, v in enumerate(value):
            yield from json_paths(v, f"{prefix}[{i}]")
    else:
        yield prefix, value


def json_keys(value) -> set:
    keys = set()
    if isinstance(value, dict):
        for k, v in value.items():
            keys.add(str(k))
            keys |= json_keys(v)
    elif isinstance(value, list):
        for v in value:
            keys |= json_keys(v)
    return keys



def allowed_null_rules(entry: str) -> list[list[set]]:
    rules = []
    for line in entry.splitlines():
        if not re.search(r"\bnull\b", line, re.I):
            continue
        brackets = re.findall(r'\["([^"]+)"\]', line)
        if brackets:
            rules.append([{b.lower()} for b in brackets])
            continue
        m = re.search(r"\ball\s+(.+?)\s+entries\b", line, re.I)
        if m:
            rules.append([set(w.lower() for w in word.split("/")) for word in re.findall(r"[A-Za-z0-9_/]+", m.group(1))])
    return rules


def null_allowed(path: str, rules: list[list[set]]) -> bool:
    parts = [c.lower() for c in re.split(r"[.\[\]]+", path) if c and not c.isdigit()]
    if parts and parts[-1] in ("value", "se"):
        parts = parts[:-1]
    def hit(group):
        return any(c == w or w in c.split("_") for c in parts for w in group)
    return any(rule and all(hit(g) for g in rule) for rule in rules)


def level_names(entry: str) -> list[tuple[str, set]]:
    chain = re.search(r"((?:\[[A-Za-z_]+\]){2,})", entry)
    if not chain:
        return []
    out = []
    for placeholder in re.findall(r"\[([A-Za-z_]+)\]", chain.group(1)):
        head = placeholder.split("_")[0].lower()
        names = set()
        for line in entry.splitlines():
            label = re.match(r"^\W*([A-Za-z]+)", line)
            if label and label.group(1).lower().startswith(head) and ":" in line:
                names |= {a or b for a, b in re.findall(r'`"([^"`]+)"`|`([A-Za-z_][A-Za-z0-9_]*)`', line.split(":", 1)[1])}
        out.append((placeholder, names))
    return out


def nesting_issues(data, levels: list[tuple[str, set]]) -> list[str]:
    issues, nodes = [], [data]
    for depth, (placeholder, names) in enumerate(levels):
        keys = {str(k) for n in nodes if isinstance(n, dict) for k in n}
        if names and keys and not keys <= names:
            issues.append(f"level {depth + 1} should hold {placeholder} keys ({', '.join(sorted(names))}) but holds "
                          f"{', '.join(sorted(keys - names)[:6])}")
        nodes = [v for n in nodes if isinstance(n, dict) for v in n.values()]
    return issues


TYPED_FIELD = re.compile(r'^\s*"([^"]+)"\s*:\s*<(int|integer|float|number|string|str|bool|boolean)>\s*,?\s*$', re.M)


def type_issues(data, entry: str) -> list[str]:
    if not isinstance(data, dict):
        return []
    want = {"int": int, "integer": int, "float": float, "number": float, "string": str, "str": str, "bool": bool, "boolean": bool}
    bad = []
    for name, kind in TYPED_FIELD.findall(entry):
        if name not in data or data[name] is None:
            continue
        v, t = data[name], want[kind]
        ok = isinstance(v, bool) if t is bool else (isinstance(v, t) and not isinstance(v, bool))
        if not ok:
            bad.append(f"{name}={v!r} ({type(v).__name__}, entry says <{kind}>)")
    typed = placeholder_types(entry)
    for path, v in json_paths(data):
        parts = [c for c in re.split(r"[.\[\]]+", path) if c and not c.isdigit()]
        if parts and parts[-1] in ("value", "se"):
            parts = parts[:-1]
        key = parts[-1] if parts else ""
        parent = parts[-2] if len(parts) > 1 else None
        stated = typed.get(key, [])
        kinds = [k for p, k in stated if p == parent] or [k for _, k in stated]
        if (kinds and all(k in ("bool", "boolean") for k in kinds) and v is not None and not isinstance(v, bool)
                and f"{key}=" not in " ".join(bad)):
            bad.append(f"{path}={v!r} ({type(v).__name__}, entry says <bool>)")
    return bad


PLACEHOLDER = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*("?<[^<>\n]+>"?|null\b)', re.I)


def enclosing_key(text: str, pos: int) -> tuple:
    depth = 0
    for i in range(pos - 1, -1, -1):
        ch = text[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            if depth == 0:
                m = re.search(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*$', text[:i])
                return (m.group(1) if m else None), i
            depth -= 1
    return None, 0


def placeholder_types(entry: str) -> dict:
    out = {}
    for m in PLACEHOLDER.finditer(entry):
        key, kind = m.group(1), m.group(2).strip('"<>').strip().lower()
        parent, brace = enclosing_key(entry, m.start())
        if key in ("value", "se") and parent:
            key, parent = parent, enclosing_key(entry, brace)[0]
        out.setdefault(key, []).append((parent, kind))
    return out


def nullable_keys(entry: str) -> set:
    return {k for k, stated in placeholder_types(entry).items() if any(re.search(r"\b(?:null|none)\b", t) for _, t in stated)}


SORTED_BY = re.compile(r"sorted\s+(?:ascending\s+)?by\s+((?:`[A-Za-z_][A-Za-z0-9_]*`[^.;`\n]*?)+)(?=[.;\n]|$)", re.I)
NON_FINITE_CELLS = {"inf", "-inf", "+inf", "infinity", "-infinity"}
MISSING_CELLS = {"", "nan", "NaN", "None", "null"}
EMPTY_PROHIBITED = re.compile(r"(?:file|table|csv) (?:must|should) (?:not be empty|contain at least one)|at least one (?:data )?row|header[- ]only (?:file |files )?(?:is|are) (?:not allowed|prohibited|invalid)|must not be empty", re.I)
MISSING_PROHIBITED_ANYWHERE = re.compile(r"missing values are (?:not allowed|prohibited)|no missing values (?:are allowed|in any)", re.I)
MISSING_PROHIBITED = re.compile(r"\b(?:no|without) (?:missing|nan|null|empty|blank)|must not (?:contain|have|be) (?:any )?(?:missing|nan|null|empty|blank)|missing values are (?:not allowed|prohibited)|must be (?:populated|non-?empty|finite)", re.I)
EXACT_COLUMNS = re.compile(r"in this (?:exact )?order|exact(?:ly)? (?:order|columns|these)|only (?:these|the following) columns|no (?:other|extra) columns", re.I)


def as_float(cell: str):
    try:
        return float(cell)
    except ValueError:
        return None


def boolean_columns(entry: str) -> set:
    return {n for line in entry.splitlines() if "`true`" in line and "`false`" in line
            for n in re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", line) if n not in ("true", "false")}


def numeric_key(vals: list[str]) -> bool:
    return all(as_float(v) is not None and not re.fullmatch(r"0\d+", v) for v in vals)


def csv_problems(rows: list[list[str]], entry: str, stated: list[str], statement: str = "") -> list[str]:
    if not rows:
        return []
    header, body, out = rows[0], [r for r in rows[1:] if r], []
    short = [n + 1 for n, r in enumerate(body) if len(r) < len(header)]
    if short:
        out.append(f"{len(short)} data row(s) have fewer fields than the header (first at data row {short[0]})")
    if not body and EMPTY_PROHIBITED.search(entry):
        out.append("header only: the task requires data rows in this file")
    if stated and EXACT_COLUMNS.search(entry) and (extra := [c for c in header if c not in stated]):
        out.append("columns not in the task's stated header: " + ", ".join(extra[:8]))
    for name in sorted(boolean_columns(entry) & set(header)):
        k = header.index(name)
        if any(k < len(r) and r[k].strip() in ("True", "False") for r in body):
            out.append(f"column `{name}` holds True/False; the task entry spells its values true/false; "
                       f"df[{name!r}].map({{True: 'true', False: 'false'}}) before to_csv writes them that way")
    inf_cols = sorted({header[i] for r in body for i, c in enumerate(r) if i < len(header) and c.strip().lower() in NON_FINITE_CELLS})
    if inf_cols:
        out.append("infinite values in column(s) " + ", ".join(inf_cols[:8]) + ": check the fit or formula that produced them")
    if MISSING_PROHIBITED.search(entry) or MISSING_PROHIBITED_ANYWHERE.search(statement):
        cols = [c for c in (stated or header) if c in header]
        gaps = []
        for c in cols:
            k = header.index(c)
            empty = sum(1 for r in body if (r[k].strip() if k < len(r) else "") in MISSING_CELLS)
            if empty:
                gaps.append(f"{c} ({empty} of {len(body)})")
        if gaps:
            out.append("empty or NaN cells where the task says values must be filled: " + ", ".join(gaps[:8])
                       + "; find why the calculation left them empty (no zeros, no guesses)")
    for clause in SORTED_BY.findall(entry):
        if re.search(r"\bdescending\b", clause, re.I):
            continue
        keys = [k for k in re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", clause) if k in header]
        if not keys:
            continue
        idx = [header.index(k) for k in keys]
        full = [r for r in body if all(i < len(r) and r[i].strip() not in MISSING_CELLS for i in idx)]
        as_num = [numeric_key([r[i].strip() for r in full]) for i in idx]
        ks = [tuple(as_float(r[i].strip()) if num else r[i].strip() for i, num in zip(idx, as_num)) for r in full]
        bad = next((n for n in range(1, len(ks)) if ks[n] < ks[n - 1]), None)
        if bad is not None:
            out.append(f"rows not sorted by {', '.join(keys)} as the entry states (first out of order at row {bad + 1} of those with keys)")
    return out


NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
JSON_DECIMALS = re.compile(r"json[^\n.]*numeric[^\n]*?rounded to (\w+) decimal", re.I)
CSV_DECIMALS = re.compile(r"([\w.-]+\.csv)`?\s*:\s*(?:fixed|exactly) (\w+) decimal places for every float field", re.I)


def decimals_rule(text: str):
    n = NUMBER_WORDS.get(text.lower(), None)
    return n if n is not None else (int(text) if text.isdigit() else None)


LOSS_FLOOR = re.compile(r"clamp(?:ed)?\s+(?:it\s+)?(?:at|to)\s+zero|no negative losses", re.I)
LOSS_TERM = re.compile(r"\bloss(?:es)?\b|\bc?VaR\b|\bES\b|expected shortfall|value[- ]at[- ]risk", re.I)
NON_LOSS_CLAMP = re.compile(r"radicand|variance|probabilit|sqrt|square root|discriminant|weight", re.I)
LOSS_KEY = re.compile(r"(?:^|_)(?:c?var|es|expected_shortfall)(?:_|$)", re.I)


def loss_floor_problems(path: str, statement: str) -> list[str]:
    clauses = [c for c in re.split(r"(?<=[.;:])\s+|\n", statement) if LOSS_FLOOR.search(c) and LOSS_TERM.search(c)
               and not NON_LOSS_CLAMP.search(c)]
    if not path.endswith(".json") or not clauses:
        return []
    try:
        data = json.loads(open(path).read())
    except (OSError, ValueError):
        return []
    bad = []
    for p, v in json_paths(data):
        parts = [c for c in re.split(r"[.\[\]]+", p) if c and not c.isdigit() and c not in ("value", "se")]
        if parts and LOSS_KEY.search(parts[-1]) and isinstance(v, (int, float)) and not isinstance(v, bool) and v < 0:
            bad.append(p)
    return [f"negative loss measure(s) {', '.join(bad[:6])}; the task clamps losses at zero"] if bad else []


COUNT_TOTALS_SHOWN: set[str] = set()


def count_table_sum(path: str) -> int | None:
    try:
        rows = list(csv.reader(io.StringIO(open(path, errors="replace").read())))
    except OSError:
        return None
    if len(rows) < 2:
        return None
    total, used = 0, 0
    for i, name in enumerate(rows[0]):
        if i == 0 or re.search(r"year|date|index|(?:^|_)id$", name, re.I):
            continue
        cells = [r[i].strip() for r in rows[1:] if i < len(r) and r[i].strip()]
        if not cells or not all(re.fullmatch(r"-?\d+(?:\.0+)?", c) for c in cells):
            return None
        total += sum(int(float(c)) for c in cells); used += 1
    return total if used >= 2 else None


def total_mismatch_items(out_dir: str) -> list[tuple[str, str, int, str, int]]:
    sums = {n: t for n in sorted(os.listdir(out_dir)) if n.endswith(".csv") and (t := count_table_sum(os.path.join(out_dir, n)))}
    out = []
    for n in sorted(os.listdir(out_dir)):
        if not n.endswith(".json"):
            continue
        try:
            data = json.loads(open(os.path.join(out_dir, n)).read())
        except (OSError, ValueError):
            continue
        for k, v in (data.items() if isinstance(data, dict) else []):
            if k.startswith("total_") and isinstance(v, int) and not isinstance(v, bool) and v > 0:
                out += [(n, k, v, table, t) for table, t in sums.items() if t != v and abs(t - v) <= 0.05 * max(t, v)]
    return out


def total_mismatch_problems(out_dir: str) -> list[tuple[str, str]]:
    return [(n, f"`{k}` is {v} while {table} sums to {t} (difference {v - t}). Write down which rows "
                "each figure counts (for example which starting states, periods or categories it "
                "includes); if they count the same set, derive both from the same corrected counts and "
                "the same origin rows; if they count different sets, say which; do not edit either "
                "number by hand") for n, k, v, table, t in total_mismatch_items(out_dir)]


PLAIN_TYPE = {"european", "asian", "vanilla", "eu"}
EXOTIC = {"barrier", "knock", "knockin", "knockout", "digital", "binary", "spread", "short", "up", "down", "in", "out",
          "lookback", "chooser", "straddle", "strangle", "butterfly", "collar", "portfolio", "position", "hedge", "net"}
NOT_GREEK = {"err", "error", "errors", "diff", "difference", "se", "stderr", "std", "stdev", "var", "variance", "ratio",
             "rel", "relative", "abs", "check", "checks", "ok", "flag", "passed", "pass", "pcp", "parity", "tol",
             "tolerance", "within", "ci", "lower", "upper", "lo", "hi", "bias", "rmse", "mae", "change", "pnl", "bump"}
DV01_KEY = {"dv01", "pv01"}
TENOR_KEYS = ("tenor", "tenor_years", "swap_tenor")
TENOR_LABEL = re.compile(r"(\d+(?:\.\d+)?)\s*[YyMm]\s*[xX×]\s*(\d+(?:\.\d+)?)\s*([YyMm])")
UNIT_NOTIONAL = re.compile(r"per unit (?:of )?notional|unit notional|notional (?:of |= ?)?1(?:\.0)?\b", re.I)

def key_tokens(text: str) -> set:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(text))
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and not t.isdigit()}


def is_finite_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)




def json_value_objects(value, prefix=""):
    if isinstance(value, dict):
        yield prefix, value
        for k, v in value.items():
            yield from json_value_objects(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from json_value_objects(v, f"{prefix}[{i}]")


def load_value_output(path: str):
    try:
        text = open(path, errors="replace").read()
    except OSError:
        return None
    if path.endswith(".json"):
        try:
            return json.loads(text)
        except ValueError:
            return None
    if path.endswith(".csv"):
        rows = list(csv.reader(io.StringIO(text)))
        if len(rows) < 2:
            return None
        out = []
        for r in rows[1:]:
            row = {}
            for h, c in zip(rows[0], r):
                try:
                    row[h] = float(c)
                except ValueError:
                    row[h] = c
            out.append(row)
        return out
    return None


def value_leaves(data, is_csv: bool):
    if is_csv:
        for i, row in enumerate(data):
            for k, v in row.items():
                if is_finite_num(v):
                    yield f"{k}[{i}]", key_tokens(k), v
    else:
        for p, v in json_paths(data):
            if is_finite_num(v):
                yield p, key_tokens(p), v


def greek_sign_rule(toks: set, file_toks: set, v: float):
    if abs(v) < 1e-10 or toks & NOT_GREEK or (toks | file_toks) & EXOTIC:
        return None
    if not (toks | file_toks) & PLAIN_TYPE:
        return None
    if "delta" in toks and "put" in toks and "call" not in toks and "gamma" not in toks and v > 0:
        return "A1"
    if "vega" in toks and (toks | file_toks) & {"call", "put"} and v < 0:
        return "A2"
    return None


def tenor_of(obj: dict, key_path: str):
    for k in TENOR_KEYS:
        if is_finite_num(obj.get(k)) and obj[k] > 0:
            return float(obj[k])
    labels = [key_path] + [v for v in obj.values() if isinstance(v, str)]
    for text in labels:
        m = list(TENOR_LABEL.finditer(text))
        if m:
            n, unit = float(m[-1].group(2)), m[-1].group(3).upper()
            return n / 12 if unit == "M" else n
    return None


def dv01_rule(data, is_csv: bool, file_toks: set, statement: str):
    objs = [(f"[{i}]", r) for i, r in enumerate(data)] if is_csv else list(json_value_objects(data))
    swaption = "swaption" in file_toks or re.search(r"swaption", statement, re.I)
    out = []
    for p, obj in objs:
        if not (swaption or "swaption" in key_tokens(p)):
            continue
        tenor = tenor_of(obj, p)
        if tenor is None:
            continue
        for k, v in obj.items():
            if not is_finite_num(v) or not key_tokens(k) & DV01_KEY or key_tokens(k) & NOT_GREEK:
                continue
            kl = k.lower()
            if "bps_per_bp" in kl or "bp_per_bp" in kl:
                bound = tenor
            elif is_finite_num(obj.get("notional")) and obj["notional"] > 0:
                bound = tenor * 1e-4 * obj["notional"]
            elif UNIT_NOTIONAL.search(statement):
                bound = tenor * 1e-4
            else:
                continue
            if abs(v) > bound * (1 + 1e-9):
                out.append((f"{k}{p}" if is_csv else (f"{p}.{k}" if p else k), v, bound))
    return out


TASK_TERMS = {"A1": [("delta", "indicator"), ("pathwise", "delta"), ("put", "delta")],
              "A2": [("vega", "indicator"), ("pathwise", "vega")],
              "A3": [("dv01", "bump"), ("dv01", "bp")]}
FIX = {
    "A1": ("A put's delta is at most zero. Per path, the pathwise derivative of the put payoff max(K - S_T, 0) is "
           "-1{S_T < K} times dS_T/dS0 (for an average-price option use the average A in place of S_T):\n"
           "    delta_put_path = -disc * (S_T < K) * S_T / S0      # GBM: dS_T/dS0 = S_T / S0\n"
           "Check on the same paths: delta_call - delta_put = exp(-q*T), which is 1 without dividends."),
    "A2": ("Vega of a plain long option is at least zero. The pathwise vega multiplies dS_T/dsigma by the indicator "
           "1{S_T > K} (call) or by -1{S_T < K} (put); the indicator selects paths and does not make the vega negative:\n"
           "    dST_dsigma = S_T * (np.log(S_T / S0) - (r - q + 0.5 * sigma**2) * T) / sigma\n"
           "    vega_call_path = disc * (S_T > K) * dST_dsigma\n"
           "    vega_put_path = -disc * (S_T < K) * dST_dsigma\n"
           "Call and put vegas on the same paths agree within sampling error (their difference, a forward, has no vega)."),
    "A3": ("A swaption's |DV01| per unit notional is at most the DV01 of its underlying forward swap, the annuity times "
           "1bp ({bound:g} in this field's unit from the tenor). A larger value means the bumped repricing used another "
           "contract's terms, for example variables left from a previous contract in a loop. Reprice with the same terms "
           "and the fixed strike, changing only the curve:\n"
           "    dv01 = price(curve_up, terms, K_fixed) - price(curve, terms, K_fixed)    # one terms object for both\n"
           "    bound = annuity_on(curve, terms) * 1e-4    # sum of accrual * discount factor over the payment dates\n"
           "and compare abs(dv01) with bound in the same unit."),
}


def task_sentence(statement: str, rule: str) -> str:
    lines = [ln.strip(" -*#\t") for ln in statement.splitlines()]
    for terms in TASK_TERMS[rule]:
        for ln in lines:
            low = ln.lower()
            if all(t in low for t in terms) and 25 < len(ln) <= 300:
                return ln.replace("**", "")
    return ""


def value_message(file: str, path: str, value: float, rule: str, statement: str = "", bound: float = 0.0) -> str:
    quote = task_sentence(statement, rule)
    head = f"Output check: {file} {path} = {value:g}." + (f' The task asks: "{quote}"' if quote else "")
    body = FIX[rule].replace("{bound:g}", f"{bound:g}")
    return (f"{head} {body}\nIf the task defines this quantity with a different sign or unit "
            "convention, keep the value and state the convention.")


def value_problems(path: str, statement: str) -> list[str]:
    data = load_value_output(path)
    if data is None:
        return []
    is_csv = path.endswith(".csv")
    name = os.path.basename(path)
    file_toks = key_tokens(os.path.splitext(name)[0])
    out = []
    for p, toks, v in value_leaves(data, is_csv):
        rule = greek_sign_rule(toks, file_toks, v)
        if rule:
            out.append(value_message(name, p, v, rule, statement))
    for p, v, bound in dv01_rule(data, is_csv, file_toks, statement):
        out.append(value_message(name, p, v, "A3", statement, bound))
    return out

CHANGE = {"change", "changes", "chg", "delta", "pnl", "dv01", "pv01", "vega", "gamma", "sens", "sensitivity",
          "sensitivities", "greek", "greeks", "impact", "dpv", "dprice", "effect", "duration", "convexity"}
CONTEXT_ONLY = {"theta", "rho"}
CONTEXT = {"call", "put", "option", "greek", "greeks", "bs"}
EXCLUDE = {"error", "err", "errors", "diff", "residual", "residuals", "se", "stderr", "pvalue", "count", "n", "num",
           "nobs", "flag", "ok", "passed", "bool", "lag", "index", "idx", "id", "date", "rank", "weight", "weights",
           "contribution", "contrib", "grid", "bump", "tol", "tolerance", "threshold"}
LEVEL_LIKE = {"duration", "convexity"}
LEAF_GENERIC = {"value", "val", "estimate"}
LABEL_KEY = re.compile(r"scenario|shock|stress", re.I)
BASE_LABEL = re.compile(r"base|^(none|no_?shock|unshocked|current|original|zero|0)$", re.I)
GENERIC = {"value", "intermediates", "usd", "pct", "bps", "bp", "test", "outputs", "py", "the", "and", "for", "is",
           "of", "in", "to", "assertionerror", "expected", "not", "with", "phase", "t0", "t1"}


def zero_toks(name):
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", str(name)).lower()
    return [t for t in re.split(r"[^a-z0-9]+", name) if t]


def zero_change_hit(name):
    tk = zero_toks(name)
    s = set(tk)
    if s & EXCLUDE or ("p" in tk and "value" in tk) or ("delta" in s and s & {"t", "time", "days"}):
        return None
    pl = any(a == "p" and b == "l" for a, b in zip(tk, tk[1:]))
    hit = sorted(s & CHANGE) or (["p_l"] if pl else []) or (sorted(s & CONTEXT_ONLY) if s & CONTEXT else [])
    return hit[0] if hit else None


def zero_is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


def zero_json_groups(obj, path, label, out):
    if isinstance(obj, dict):
        lab = next((str(v) for k, v in obj.items() if isinstance(v, str) and LABEL_KEY.search(k)), label)
        if lab is None and path and LABEL_KEY.search(".".join(path[:-1])):
            lab = path[-1]
        out.append((".".join(path), lab, {k: v for k, v in obj.items() if zero_is_num(v)}))
        for k, v in obj.items():
            zero_json_groups(v, path + [str(k)], lab if isinstance(v, (dict, list)) else None, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5000]):
            zero_json_groups(v, path + [f"[{i}]"], label, out)


def zero_num(s):
    try:
        return float(s)
    except Exception:
        return None


def zero_csv_table(fp):
    with open(fp, newline="", errors="replace") as f:
        rd = csv.reader(f)
        hdr = next(rd, None) or []
        lc = next((i for i, h in enumerate(hdr) if LABEL_KEY.search(h)), None)
        rows, labs = [], []
        for i, r in enumerate(rd):
            if i >= 20000:
                break
            rows.append({h: zero_num(c) for h, c in zip(hdr, r)})
            labs.append(r[lc] if lc is not None and lc < len(r) else None)
    return hdr, lc, rows, labs


ZERO_NOTE = ("a nonzero shock or bump was applied but this change is exactly 0; this usually means the shock did not reach "
             "the computation, an array was truncated to integers, or the value is a placeholder; if it is truly 0 under "
             "the task's definition, keep it and state why")


def zero_fires(path: str, rel: str) -> list[dict]:
    fires = []
    if path.endswith(".json"):
        groups = []
        zero_json_groups(json.load(open(path)), [], None, groups)
        for gpath, lab, nums in groups:
            parent = gpath.rsplit(".", 1)[-1]
            nums = {(parent if k.lower() in LEAF_GENERIC and parent else k): v for k, v in nums.items()}
            ch = {k: v for k, v in nums.items() if zero_change_hit(k)}
            where = gpath or "(top level)"
            for k, v in ch.items():
                if v == 0 and zero_change_hit(k) not in LEVEL_LIKE:
                    fires.append(dict(file=rel, where=where, fields=[k], label=lab or ""))
            if lab and not BASE_LABEL.search(lab) and ch and all(v == 0 for v in ch.values()):
                fires.append(dict(file=rel, where=where, fields=list(ch), label=lab))
            if len(ch) >= 2 and all(v == 0 for v in ch.values()):
                fires.append(dict(file=rel, where=where, fields=list(ch), label=lab or ""))
    elif path.endswith(".csv"):
        hdr, lc, rows, labs = zero_csv_table(path)
        chcols = [h for h in hdr if zero_change_hit(h)]
        allzero = [h for h in chcols if rows and all(r.get(h) == 0 for r in rows)]
        for h in chcols:
            zr = [i for i, r in enumerate(rows) if r.get(h) == 0]
            for i in zr[:3]:
                scen = labs[i] and not BASE_LABEL.search(labs[i])
                if (h in allzero or scen) and zero_change_hit(h) not in LEVEL_LIKE:
                    fires.append(dict(file=rel, where="every row", fields=[h], label="") if h in allzero else
                                 dict(file=rel, where=f"row {i}", fields=[h], label=labs[i] or ""))
        for i, r in enumerate(rows):
            lab = labs[i]
            if lab and not BASE_LABEL.search(lab) and chcols and all(r.get(h) == 0 for h in chcols):
                fires.append(dict(file=rel, where=f"row {i}", fields=list(chcols), label=lab))
        if len(allzero) >= 2:
            fires.append(dict(file=rel, where="every row", fields=list(allzero), label=""))
    return fires


ZERO_TAIL = "If it is truly 0 under the task's definition, keep it and state why."


def zero_place_values(path: str, where: str) -> dict:
    try:
        if path.endswith(".csv"):
            rows = list(csv.DictReader(io.StringIO(open(path, errors="replace").read())))
            m = re.match(r"row (\d+)", where)
            row = rows[int(m.group(1))] if m and int(m.group(1)) < len(rows) else {}
            out = {}
            for k, v in row.items():
                try:
                    out[k] = float(v)
                except (TypeError, ValueError):
                    pass
            return out
        obj = json.load(open(path))
        if where not in ("(top level)", ""):
            for part in re.findall(r"[^.\[\]]+|\[\d+\]", where):
                obj = obj[int(part[1:-1])] if part.startswith("[") else obj[part]
        return {k: v for k, v in obj.items() if isinstance(v, (int, float)) and not isinstance(v, bool)} if isinstance(obj, dict) else {}
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return {}


def zero_anchor(session_code: str, label: str, fields: list[str]) -> tuple[str, list[str]]:
    lines = session_code.splitlines()
    keys = [label] if label else []
    if label and (short := re.sub(r"_?\d+(?:\.\d+)?(?:bps?|pct)?$", "", label)) and short != label:
        keys.append(short)
    for key in keys:
        hits = [i for i, ln in enumerate(lines) if key in ln and not ln.strip().startswith("#")]
        defs = [i for i in hits if re.match(rf"\s*(?:def\s+\w*{re.escape(key)}|\w*{re.escape(key)}\w*\s*=[^=])", lines[i])]
        if hits:
            i = (defs or hits)[-1]
            return "builds", [ln.rstrip() for ln in lines[i:i + 3] if ln.strip()][:3]
    for key in fields:
        hits = [i for i, ln in enumerate(lines) if key in ln and not ln.strip().startswith("#")]
        if hits:
            return "writes", [lines[hits[-1]].rstrip()]
    return "", []


def zero_note_v2(file: str, where: str, label: str, fields: list[str], path: str, session_code: str) -> str:
    scen = f" (scenario {label})" if label else ""
    parts = [f"Output check: {file}, {where}{scen}: {', '.join(fields[:8])} = 0, although a nonzero shock or bump was applied."]
    verb, anchor = zero_anchor(session_code, label, fields)
    if anchor:
        indent = min(len(ln) - len(ln.lstrip()) for ln in anchor)
        parts.append(f"The code that {verb} it:\n" + "\n".join("    " + ln[indent:] for ln in anchor))
    vals = zero_place_values(path, where)
    for f in fields:
        base = re.sub(r"_?(?:change|chg|delta|diff|pnl|impact|effect)(?:_pct|_bps|_bp)?$", "", f)
        if base != f and base in vals and vals.get(f) == 0:
            parts.append(f"Your own values: {base} after the shock = {base} before the shock = {vals[base]:.10g}.")
            break
    name = "shock"
    if verb == "builds" and (m := re.match(r"\s*def\s+(\w+)\s*\(\s*\)", anchor[0])):
        name = m.group(1) + "()"
    elif verb == "builds" and (m := re.match(r"\s*(\w+)\s*=[^=]", anchor[0])):
        name = m.group(1)
    parts.append("First check, before changing anything else:\n"
                 f"    print({name}, getattr({name}, 'dtype', None))\n"
                 "    print(np.max(np.abs(shocked_curve - base_curve)))\n"
                 "If the shocked curve equals the base curve, the shock did not reach the computation; a shock array built "
                 "with np.full_like or np.zeros_like from an integer array is all 0. " + ZERO_TAIL)
    return "\n".join(parts)


ZERO_SHOWN: set[tuple[str, str]] = set()


def zero_problems(path: str, rel: str) -> list[str]:
    try:
        fires = zero_fires(path, rel)
    except Exception:
        return []
    places = {}
    for f in fires:
        p = places.setdefault((f["file"], f["where"]), {"fields": [], "label": f["label"]})
        p["fields"] += [x for x in f["fields"] if x not in p["fields"]]
        p["label"] = p["label"] or f["label"]
    out = []
    for (file, where), p in places.items():
        if (file, where) in ZERO_SHOWN or len(out) == 4:
            continue
        ZERO_SHOWN.add((file, where))
        out.append(zero_note_v2(file, where, p["label"], p["fields"], path, "\n".join(SESSION_CODE)))
    return out

VALUE_CHECKS_SHOWN: set[str] = set()


def note_value_checks(observations: list[dict]) -> list[dict]:
    try:
        statement = pathlib.Path(TASK_STATEMENT).read_text()
    except OSError:
        statement = ""
    try:
        names = sorted(n for n in os.listdir(OUTPUT_DIR) if n.endswith((".json", ".csv")))
    except OSError:
        return observations
    found = []
    for n in names:
        try:
            found += value_problems(os.path.join(OUTPUT_DIR, n), statement)
            found += zero_problems(os.path.join(OUTPUT_DIR, n), n)
        except Exception:
            pass
    try:
        found += oc7_output_notes()
    except Exception:
        pass
    try:
        found += dg_output_notes()
    except Exception:
        pass
    new = list(dict.fromkeys(m for m in found if m not in VALUE_CHECKS_SHOWN or m in M3_SEND_NOW))
    M3_SEND_NOW.clear()
    VALUE_CHECKS_SHOWN.update(new)
    if new:
        for obs in observations:
            if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                obs["content"] += "\n\n" + "\n".join(new)
                break
    return observations


LIKE_FULL = re.compile(r"np\.full_like\(\s*([A-Za-z_]\w*)\s*,\s*([^\n]*)")
LIKE_EMPTY = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*np\.(?:zeros|empty|ones)_like\(\s*([A-Za-z_]\w*)\s*\)", re.M)
FLOATISH = re.compile(r"\d\.\d*|\.\d|\d[eE]-?\d|\bnan\b|\binf\b|/")


def split_args(text: str) -> list[str]:
    depth, cur, out = 0, "", []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                out.append(cur); return out
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    return out + [cur]


def like_candidates(code: str) -> list[tuple[str, str, str]]:
    out = []
    for line in code.splitlines():
        body = line.split("#", 1)[0]
        for m in LIKE_FULL.finditer(body):
            args = split_args(m.group(2))
            if "dtype" not in body and args and FLOATISH.search(args[0]):
                out.append(("full", m.group(1), body.strip()))
    for m in LIKE_EMPTY.finditer(code):
        var = m.group(1)
        if re.search(rf"^\s*{re.escape(var)}\s*\[[^\]]*\]\s*[+\-*/]?=(?!=)", code[m.end():], re.M):
            out.append(("assign", var, m.group(0).strip()))
    return out


INT_STATIC = r"^\s*{n}\s*=\s*(?:np\.array\(\s*)?\[\s*-?\d+(?:\s*,\s*-?\d+)*\s*\]|^\s*{n}\s*=\s*np\.arange\(\s*\d+(?:\s*,\s*\d+){{0,2}}\s*\)|^\s*{n}\s*=\s*[^\n]*\.astype\(\s*(?:int|np\.int\w*)\s*\)|^\s*{n}\s*=\s*[^\n]*dtype\s*=\s*(?:int|np\.int\w*)\b"


def static_int(name: str, history: str) -> bool:
    rx = re.compile(INT_STATIC.format(n=re.escape(name)), re.M)
    last_any = [m.start() for m in re.finditer(rf"^\s*{re.escape(name)}\s*=[^=]", history, re.M)]
    last_int = [m.start() for m in rx.finditer(history)]
    return bool(last_int) and bool(last_any) and last_int[-1] == last_any[-1]


LIKE_DTYPE_SHOWN: set[str] = set()


DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y%m%d")


def parse_date(text: str):
    t = text.strip()
    for f in DATE_FORMATS:
        try:
            return dt.datetime.strptime(t, f)
        except ValueError:
            pass
    return None


def descending_date_columns(path: str, max_bytes: int = 20_000_000) -> list[str]:
    if os.path.getsize(path) > max_bytes:
        return []
    try:
        rows = list(csv.reader(io.StringIO(open(path, errors="replace").read())))
    except (OSError, csv.Error):
        return []
    if len(rows) < 4:
        return []
    out = []
    for j, name in enumerate(rows[0]):
        if any(j >= len(r) or parse_date(r[j]) is None for r in rows[1:4]):
            continue
        prev, ok = None, True
        for r in rows[1:]:
            v = parse_date(r[j]) if j < len(r) else None
            if v is None or (prev is not None and not v < prev):
                ok = False
                break
            prev = v
        if ok:
            out.append(name)
    return out


def descending_notes(dirs) -> list[str]:
    notes, seen = [], set()
    for root in dirs:
        for d, _, names in os.walk(root):
            for n in sorted(names):
                p = os.path.join(d, n)
                if not n.lower().endswith(".csv") or n in seen:
                    continue
                cols = descending_date_columns(p)
                if cols:
                    seen.add(n)
                    notes.append(f"{p}: rows are in descending date order (column {cols[0]}); parse that column as "
                                 "dates (pd.to_datetime) and sort ascending on the parsed dates before any time-series "
                                 "step (differences, rolling windows, first/last, argmax ties).")
    return notes


WARN_CELL_HDR = re.compile(r"\[python cell (\d+) \| session generation \d+ \| (\w+)")
WARN_HDR = re.compile(r"^(?P<src><cell[^>]*>):(?P<line>\d+): RuntimeWarning: (?P<msg>(?:invalid value|divide by zero) encountered[^\n]*)$")


def warning_findings(output: str, code: str) -> list[tuple[str, str]]:
    h = WARN_CELL_HDR.search(output)
    if h and h.group(2) != "ok":
        return []
    lines, code_lines, out = output.splitlines(), code.splitlines(), []
    for k, raw in enumerate(lines):
        m = WARN_HDR.match(raw.strip())
        if not m:
            continue
        nxt = lines[k + 1] if k + 1 < len(lines) else ""
        src = nxt.strip() if nxt.startswith((" ", "\t")) and not WARN_HDR.match(nxt.strip()) else ""
        ln = int(m.group("line"))
        if not src and h and m.group("src") == f"<cell {h.group(1)}>" and 0 < ln <= len(code_lines):
            src = code_lines[ln - 1].strip()
        if src:
            out.append((raw.strip(), src))
    return out


def warning_note(warning: str, src: str) -> str:
    return ("Note: this cell emitted a numeric warning:\n"
            f"  {warning}\n      {src}\n"
            "Values computed on that line are invalid (nan or inf) for at least one element, and everything derived from "
            "them (later sums, ratios, t-statistics, files written from them) is invalid too. Find which inputs produce it "
            "and fix the computation before continuing. Do not hide it with clip, abs, nan_to_num, fillna or a max(x, 0) "
            "guard: a negative value under a square root usually means the variance or covariance formula itself is wrong, "
            "so check it against an independent implementation. If the nan/inf is intended (for example a rolling-window "
            "warm-up, an edge case you are deliberately testing, or a branch of np.where that is never selected), say so in "
            "one sentence and keep it, and make sure it does not reach an output field that should hold a number.")

WARN_SHOWN: set[str] = set()


def warn_obs_text(content: str) -> str:
    try:
        j, _ = json.JSONDecoder().raw_decode(content.lstrip())
        if isinstance(j, dict) and isinstance(j.get("output"), str):
            return j["output"]
    except ValueError:
        pass
    return content


def note_num_warnings(message: dict, observations: list[dict]) -> list[dict]:
    codes = []
    for tc in message.get("tool_calls") or []:
        raw = (tc.get("function") or {}).get("arguments", "")
        try:
            a = json.loads(raw) if isinstance(raw, str) else raw
            codes.append(str(a.get("code") or ""))
        except (ValueError, AttributeError):
            codes.append("")
    try:
        for obs, code in zip([o for o in observations if isinstance(o.get("content"), str) and o.get("extra") is not None], codes):
            notes = []
            for warning, src in warning_findings(warn_obs_text(obs["content"]), code):
                if src not in WARN_SHOWN:
                    WARN_SHOWN.add(src)
                    notes.append(warning_note(warning, src))
            if notes:
                obs["content"] += "\n\n" + "\n\n".join(notes)
    except Exception:
        pass
    return observations


HELD_NOTES: list[str] = []


NOTE_START = ("Code note:", "Code check:", "Output check:", "Note: this cell emitted", "Session check:", "Check after",
              "Count note", "Count check", "The document says:", "API note:")
MAP_NOTE = re.compile(r"`[A-Za-z_][\w.]*` maps ")
GENERIC_LAG = "Code note: this session contains a one-row shift"
SEND_AT_MOST = 2


def split_notes(texts: list[str]) -> list[str]:
    out = []
    for text in texts:
        cur = []
        for line in text.splitlines():
            parts = re.split(r"(?<=\S) (?=Code note: )", line)
            for k, part in enumerate(parts):
                if (k > 0 or part.startswith(NOTE_START) or MAP_NOTE.match(part)) and cur:
                    out.append("\n".join(cur).strip())
                    cur = []
                cur.append(part)
        if cur and "\n".join(cur).strip():
            out.append("\n".join(cur).strip())
    return [n for n in out if n]


def note_tier(note: str) -> int:
    if note.startswith("Note: this cell emitted"):
        return 0
    if "your own check `" in note:
        return 1
    if note.startswith(("Code note:", "Code check:", "Count check", "Session check:", "Check after", "The document says:", "API note:")) or MAP_NOTE.match(note):
        return 2
    return 3


def note_key(note: str) -> str:
    if note.startswith("Note: this cell emitted"):
        lines = note.splitlines()
        return "warn:" + (lines[2].strip() if len(lines) > 2 else note)
    return note


def arrange_notes(notes: list[str]) -> list[str]:
    seen, out = set(), []
    for n in notes:
        k = note_key(n)
        if k not in seen:
            seen.add(k)
            out.append(n)
    if any("lags the signal" in n for n in out):
        out = [n for n in out if not n.startswith(GENERIC_LAG)]
    if any(note_tier(n) != 1 and not n.startswith(GENERIC_LAG) for n in out):
        return sorted(out, key=lambda n: (bool(note_tier(n) == 1 and re.search(r"your own check `[^`]*all_checks", n)), note_tier(n)))
    return sorted(out, key=note_tier)
DEFERRED_NOTES: list[str] = []


def hold_notes(observations: list[dict], before: list) -> list[str]:
    failed = any((o.get("extra") or {}).get("returncode") not in (0, None) for o in observations)
    added = []
    for o, b in zip(observations, before):
        c = o.get("content")
        if isinstance(c, str) and isinstance(b, str) and c.startswith(b) and len(c) > len(b):
            text = c[len(b):]
            keep = RESET_INDEX_NOTE in text
            rest = text.replace(" " + RESET_INDEX_NOTE, "").replace(RESET_INDEX_NOTE, "") if keep else text
            if rest.strip():
                added.append(rest.strip())
            o["content"] = b + ("\n\n" + RESET_INDEX_NOTE if keep else "")
    if failed:
        HELD_NOTES.extend(added)
        return []
    carried = list(DEFERRED_NOTES)
    shown = {note_key(n) for n in carried}
    out = carried + [n for n in arrange_notes(split_notes(HELD_NOTES + added)) if note_key(n) not in shown]
    HELD_NOTES.clear()
    DEFERRED_NOTES.clear()
    if len(out) > SEND_AT_MOST:
        DEFERRED_NOTES.extend(out[SEND_AT_MOST:])
        out = out[:SEND_AT_MOST]
    return out


DG_D_SRC = '"""Class D output-layer invariants keyed only on generic field names: D-a resolution consistency, D-b ES/VaR ordering, D-c half-life identity."""\nimport csv, io, json, math, re\nfrom pathlib import Path\n\nLN2 = math.log(2)\n\n\ndef tokens(text):\n    return [t for t in re.split(r"[^a-z0-9]+", str(text).lower()) if t]\n\n\ndef num(x):\n    if isinstance(x, bool):\n        return None\n    try:\n        v = float(x)\n    except (TypeError, ValueError):\n        return None\n    return v if math.isfinite(v) else None\n\n\ndef load(p):\n    try:\n        if p.suffix == ".json":\n            return json.load(open(p))\n        if p.suffix == ".csv":\n            rows = list(csv.DictReader(io.StringIO(open(p, errors="replace").read())))\n            return rows if rows else None\n    except Exception:\n        return None\n    return None\n\n\ndef objects(v, path=""):\n    if isinstance(v, dict):\n        yield "obj", path, v\n        for k, x in v.items():\n            yield from objects(x, f"{path}.{k}" if path else str(k))\n    elif isinstance(v, list):\n        if v and all(isinstance(x, dict) for x in v):\n            yield "rows", path, v\n        for i, x in enumerate(v[:200]):\n            if isinstance(x, (dict, list)):\n                yield from objects(x, f"{path}[{i}]")\n\n\ndef leaves(v, path=""):\n    if isinstance(v, dict):\n        for k, x in v.items():\n            yield from leaves(x, f"{path}.{k}" if path else str(k))\n    elif isinstance(v, list):\n        for i, x in enumerate(v[:500]):\n            yield from leaves(x, f"{path}[{i}]")\n    else:\n        yield path, v\n\n\ndef tables(outdir):\n    for p in sorted(Path(outdir).glob("*")):\n        d = load(p)\n        if d is not None:\n            yield p.name, ("csv" if p.suffix == ".csv" else "json"), d\n\n\nRES_WORD = {"coarse": 0, "coarser": -1, "medium": 1, "mid": 1, "fine": 2, "finer": 3, "finest": 4}\nRES_COL = re.compile(r"^(n_?steps|steps|num_?steps|time_?steps|n_?time_?steps|n_?paths|paths|num_?paths|n_?sims?|"\n                     r"n_?simulations|num_?simulations|grid_?size|n_?grid|grid_?points|n_?grid_?points|n_?nodes|nodes|"\n                     r"n_?s|n_?t|n_?space|n_?spot|resolution|refinement|refine_?level|mesh(_?size)?)$", re.I)\nBARE_RES = re.compile(r"^(n|m|grid)$", re.I)\nCONV_CTX = re.compile(r"conver|refine|richardson|grid_?study|mesh", re.I)\nNOT_VALUE = re.compile(r"(^|_)(se|stderr|std_?err|std|stdev|ci|lo|hi|lower|upper|err|error|errors|abs_?err|rel_?err|"\n                       r"diff|ratio|rate|order|time|runtime|seconds|sec|elapsed|seed|iter|iterations|converged|tol)(_|$)", re.I)\nSE_COL = re.compile(r"(^|_)(se|stderr|std_?err|standard_?error|mc_?se)(_|$)", re.I)\nREL_TOL = 0.05\nJUDGED = []\n\n\ndef res_rank_label(s):\n    ts = tokens(s)\n    hits = [RES_WORD[t] for t in ts if t in RES_WORD]\n    return hits[0] if len(hits) == 1 and len(ts) <= 3 else None\n\n\ndef judge(levels, name):\n    levels = [l for l in levels if l[1] is not None]\n    if len(levels) < 2:\n        return None\n    JUDGED.append(name)\n    (r1, b, sb), (r2, a, sa) = levels[-2][:3], levels[-1][:3]\n    r1, r2 = (levels[-2][3], levels[-1][3]) if len(levels[-1]) > 3 else (r1, r2)\n    if abs(a) < 1e-12 and abs(b) < 1e-12:\n        return None\n    rel = abs(a - b) / max(abs(a), abs(b))\n    if rel <= REL_TOL:\n        return None\n    if sa is not None and sb is not None and abs(a - b) <= 4 * math.hypot(sa, sb):\n        return None\n    if len(levels) >= 3:\n        c = levels[-3][1]\n        if abs(a - b) < abs(b - c):\n            return None\n    return f"{name}: {r1}={b:.6g} vs {r2}={a:.6g} (rel diff {rel:.1%})"\n\n\ndef da_rows(rows, ctx):\n    hits = []\n    cols = list(rows[0])\n    label_cols = [c for c in cols if sum(res_rank_label(r.get(c, "")) is not None for r in rows) >= 2]\n    res_cols = [c for c in cols if RES_COL.match(c.strip()) or (BARE_RES.match(c.strip()) and CONV_CTX.search(ctx))]\n    res_cols = [c for c in res_cols if sum(num(r.get(c)) is not None for r in rows) == len(rows)]\n    for rc in label_cols + res_cols:\n        is_label = rc in label_cols\n        group_cols = [c for c in cols if c != rc and c not in res_cols and c not in label_cols\n                      and any(num(r.get(c)) is None and str(r.get(c, "")).strip() for r in rows)]\n        val_cols = [c for c in cols if c != rc and c not in group_cols and c not in res_cols and c not in label_cols\n                    and not NOT_VALUE.search(c) and all(num(r.get(c)) is not None for r in rows if str(r.get(c, "")).strip())]\n        se_cols = [c for c in cols if SE_COL.search(c)]\n        groups = {}\n        for r in rows:\n            rank = res_rank_label(r.get(rc, "")) if is_label else num(r.get(rc))\n            if rank is None:\n                continue\n            groups.setdefault(tuple(str(r.get(g)) for g in group_cols), []).append((rank, r))\n        for g, members in groups.items():\n            if len({m[0] for m in members}) != len(members) or len(members) < 2:\n                continue\n            members.sort(key=lambda m: m[0])\n            for vc in val_cols:\n                se = se_cols[0] if len(se_cols) == 1 else None\n                lv = [(m[0], num(m[1].get(vc)), num(m[1].get(se)) if se else None, f"{rc}={m[1].get(rc)}") for m in members]\n                h = judge(lv, f"{ctx}:{vc}{\'@\' + \'/\'.join(g) if g else \'\'} by {rc}")\n                if h:\n                    hits.append(h)\n    return hits\n\n\nNUM_RES_KEY = re.compile(r"^(.*?)(?:^|_)(n|nsteps|n_steps|steps|paths|n_paths|grid|nodes|m)_?=?(\\d+)(.*)$", re.I)\n\n\ndef da_obj(obj, ctx):\n    hits = []\n    fam = {}\n    for k, v in obj.items():\n        if num(v) is None:\n            continue\n        ts = tokens(k)\n        rw = [t for t in ts if t in RES_WORD]\n        if len(rw) == 1:\n            fam.setdefault(("w", tuple(t for t in ts if t != rw[0])), []).append((RES_WORD[rw[0]], num(v), k))\n            continue\n        m = NUM_RES_KEY.match(k)\n        if m and m.group(1).strip("_") and not NOT_VALUE.search(k):\n            fam.setdefault(("n", m.group(1).lower(), m.group(2).lower(), m.group(4).lower()), []).append((int(m.group(3)), num(v), k))\n    if all(re.fullmatch(r"\\d+", str(k)) for k in obj) and len(obj) >= 2 and CONV_CTX.search(ctx):\n        fam[("keys",)] = [(int(k), num(v), k) for k, v in obj.items() if num(v) is not None]\n    for key, members in fam.items():\n        if len(members) < 2 or len({m[0] for m in members}) != len(members):\n            continue\n        if any(NOT_VALUE.search(m[2]) for m in members):\n            continue\n        members.sort()\n        h = judge([(m[0], m[1], None, m[2]) for m in members], ctx)\n        if h:\n            hits.append(h)\n    return hits\n\n\ndef check_resolution(outdir):\n    hits = []\n    for name, kind, data in tables(outdir):\n        if kind == "csv":\n            hits += da_rows(data, name)\n        else:\n            for k, path, o in objects(data):\n                ctx = f"{name}:{path}"\n                if k == "obj":\n                    hits += da_obj(o, ctx)\n                elif all(isinstance(x, dict) for x in o) and len(o) >= 2:\n                    rows = [{kk: vv for kk, vv in x.items() if not isinstance(vv, (dict, list))} for x in o]\n                    if rows and rows[0]:\n                        hits += da_rows(rows, ctx)\n    return hits\n\n\nES_TOK = {"es", "cvar", "etl", "tvar", "cte", "shortfall"}\nDROP_WITH_ES = {"expected"}\nEXCL = {"err", "error", "rmse", "mae", "diff", "ratio", "rel", "pct", "increase", "marginal", "component", "contribution",\n        "contrib", "incremental", "check", "sum", "count", "num", "n", "p", "pvalue", "stat", "lr", "breach", "breaches",\n        "violation", "violations", "exceed", "exceedance", "exceedances", "hit", "hits", "test", "se", "std", "bias",\n        "lower", "upper", "ci", "share", "weight", "implementation", "bps", "flag", "ok", "passed", "diffs", "true",\n        "rank", "z", "score", "change", "delta", "decomposition", "of", "total"}\n\n\ndef var_partner(ts):\n    if set(ts) & EXCL or not set(ts) & ES_TOK:\n        return None\n    if "shortfall" in ts and "expected" not in ts:\n        return None\n    out = []\n    for t in ts:\n        if t in ES_TOK:\n            out.append("var")\n        elif t not in DROP_WITH_ES:\n            out.append(t)\n    return tuple(sorted(out))\n\n\ndef es_violation(e, v):\n    if e is None or v is None or (abs(e) < 1e-12 and abs(v) < 1e-12):\n        return False\n    if e * v < 0:\n        return True\n    return abs(e) < abs(v) * (1 - 1e-9) - 1e-12\n\n\ndef check_es_var(outdir):\n    hits = []\n    for name, kind, data in tables(outdir):\n        if kind == "csv":\n            cols = list(data[0])\n            idx = {tuple(sorted(tokens(c))): c for c in cols}\n            for c in cols:\n                p = var_partner(tokens(c))\n                if p and p in idx and idx[p] != c:\n                    bad = [r for r in data if es_violation(num(r.get(c)), num(r.get(idx[p])))]\n                    if bad:\n                        r = bad[0]\n                        hits.append(f"{name}:{c}={r.get(c)} vs {idx[p]}={r.get(idx[p])} ({len(bad)}/{len(data)} rows)")\n        else:\n            lv = [(p, num(v)) for p, v in leaves(data) if num(v) is not None]\n            idx = {}\n            for p, v in lv:\n                idx.setdefault(tuple(sorted(tokens(p))), (p, v))\n            for p, v in lv:\n                q = var_partner(tokens(p))\n                if q and q in idx and idx[q][0] != p and es_violation(v, idx[q][1]):\n                    hits.append(f"{name}:{p}={v:.6g} vs {idx[q][0]}={idx[q][1]:.6g}")\n    return hits\n\n\nSPEED = re.compile(r"^(ou_)?(kappa|mean_reversion_speed|reversion_speed|mr_speed|speed_of_mean_reversion)$", re.I)\nUNIT_TOK = {"years": "y", "year": "y", "yrs": "y", "y": "y", "days": "d", "day": "d", "d": "d", "hours": "h", "hour": "h",\n            "periods": "p", "period": "p", "steps": "p", "step": "p", "obs": "p", "bars": "p", "observations": "p",\n            "weeks": "w", "week": "w", "months": "m", "month": "m"}\nDAYS_PER_YEAR = (252.0, 360.0, 365.0, 365.25)\n\n\ndef input_dts(params):\n    out = set()\n    for k, v in params.items():\n        x = num(v)\n        if not x or x <= 0:\n            continue\n        ts = tokens(k)\n        if "dt" in ts or ("delta" in ts and "t" in ts):\n            out.add(x)\n        if ("periods" in ts or "steps" in ts or "obs" in ts or "annualization" in ts) and ("year" in ts or "annualization" in ts or "per" in ts) and x > 1:\n            out.add(1.0 / x)\n    return out\n\n\ndef unit_lengths(u, dts):\n    if u == "y":\n        return [1.0]\n    if u == "d":\n        return [1 / D for D in DAYS_PER_YEAR]\n    if u == "h":\n        return [1 / (24 * D) for D in DAYS_PER_YEAR]\n    if u == "w":\n        return [1 / 52.0, 7 / 365.0]\n    if u == "m":\n        return [1 / 12.0]\n    if u == "p":\n        return sorted(dts)\n    return []\n\n\ndef half_life_fields(obj):\n    out = []\n    for k, v in obj.items():\n        ts = tokens(k)\n        x = num(v)\n        if x is None or x <= 0:\n            continue\n        if ("half" in ts and "life" in ts) or "halflife" in ts:\n            us = [UNIT_TOK[t] for t in ts if t in UNIT_TOK]\n            out.append((k, x, us[0] if len(us) == 1 else None))\n    return out\n\n\ndef close(a, b, tol=0.02):\n    return abs(a / b - 1) < tol\n\n\ndef check_half_life(outdir, params):\n    hits = []\n    dts = input_dts(params)\n    for name, kind, data in tables(outdir):\n        if kind != "json":\n            continue\n        for k, path, o in objects(data):\n            if k != "obj":\n                continue\n            hl = [h for h in half_life_fields(o) if h[2] is not None and unit_lengths(h[2], dts)]\n            kap = [num(v) for kk, v in o.items() if SPEED.match(kk) and num(v) and num(v) > 0]\n            for i in range(len(hl)):\n                for j in range(i + 1, len(hl)):\n                    (ka, a, ua), (kb, b, ub) = hl[i], hl[j]\n                    if ua == ub:\n                        continue\n                    if not any(close(a * la, b * lb) for la in unit_lengths(ua, dts) for lb in unit_lengths(ub, dts)):\n                        hits.append(f"{name}:{path}: {ka}={a:.6g} and {kb}={b:.6g} do not convert into each other")\n            if kap and hl:\n                kp = kap[0]\n                speed_units = [1.0] + [1 / D for D in DAYS_PER_YEAR] + sorted(dts)\n                ok = any(all(any(close(h[1] * L * kp, LN2 * T) for L in unit_lengths(h[2], dts)) for h in hl) for T in speed_units)\n                if not ok:\n                    hits.append(f"{name}:{path}: kappa={kp:.6g} with " + ", ".join(f"{h[0]}={h[1]:.6g}" for h in hl) +\n                                " fits no single time unit of kappa (hl*kappa != ln2)")\n        phis = sorted((len(tokens(p)), p, num(v)) for p, v in leaves(data) if is_phi(p) and num(v) is not None and 0 < num(v) < 1)\n        if phis:\n            depth, ppath, phi = phis[0]\n            if phi >= 0.5:\n                for k, path, o in objects(data):\n                    if k != "obj":\n                        continue\n                    for key, x, u in half_life_fields(o):\n                        steps = [x] if u == "p" else ([x * L / d for L in unit_lengths(u, dts) for d in dts] if u and dts else [])\n                        if steps and all(s < 1 for s in steps):\n                            hits.append(f"{name}:{path}.{key}={x:.6g} is below one observation step while {ppath}={phi:.3g} >= 0.5 "\n                                        f"(implied half-life {LN2 / -math.log(phi):.3g} steps)")\n    return hits\n\n\ndef is_phi(path):\n    ts = tokens(path)\n    lag1 = "lag1" in ts or ("lag" in ts and "1" in ts) or "ar1" in ts\n    return (lag1 and bool({"autocorr", "autocorrelation", "acf", "ar1", "phi"} & set(ts))) or ts[-1:] == ["phi"]\n\n\ndef params_of(run_dir):\n    out = {}\n    for pj in (Path(run_dir) / "staged" / "environment" / "data").glob("*.json"):\n        try:\n            d = json.load(open(pj))\n        except Exception:\n            continue\n        for p, v in leaves(d):\n            out[p.split(".")[-1]] = v\n    return out'
DG_G_SRC = '"""Class G: the same involutive or cumulative transform applied twice along one object\'s data flow, over a run\'s executed REPL cells."""\nimport ast, copy, json, math, re\n\nUNIT_CONST = {100.0, 0.01, 1e4, 1e-4, 1e3, 1e-3, 1e6, 1e-6, 252.0, 365.0, 365.25, 360.0, 12.0, 52.0, 1095.0, 8760.0}\nORDER_DEP = {"cumsum", "cumprod", "cummax", "cummin", "ewm", "rolling", "expanding", "shift", "diff", "pct_change",\n             "sort_values", "sort_index", "argsort", "sort", "rank", "interpolate", "ffill", "bfill", "fillna", "lfilter",\n             "accumulate", "searchsorted", "reset_index", "set_index", "reindex", "groupby", "resample", "iterrows",\n             "cumulative_sum", "convolve", "correlate", "polyfit", "lstsq"}\nWRAPPERS = {"asarray", "array", "Series", "DataFrame", "list", "copy", "ravel", "squeeze", "atleast_1d", "float",\n            "float64", "ascontiguousarray", "to_numpy", "tolist", "flatten", "reshape", "astype", "values", "item"}\nELEMWISE = {"exp", "log", "log1p", "expm1", "sqrt", "abs", "fabs", "clip", "maximum", "minimum", "round", "power",\n            "square", "tanh", "sign", "where", "nan_to_num"}\nREDUCE = {"sum", "mean", "nansum", "nanmean", "median", "nanmedian", "average"}\nPRODUCTS = {"dot", "matmul", "inner", "vdot", "average", "einsum", "tensordot"}\nREVERSE_FUNCS = {"flip", "flipud", "fliplr", "reversed"}\nOBJ_OUT = {"transform", "predict", "score_samples", "decision_function", "inverse_transform"}\nRESET_METHODS = {"fit", "fit_transform", "partial_fit"}\n\n\ndef key_of(n):\n    if isinstance(n, ast.Name):\n        return n.id\n    if isinstance(n, ast.Attribute):\n        b = key_of(n.value)\n        return f"{b}.{n.attr}" if b else None\n    if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, (str, int)):\n        b = key_of(n.value)\n        return f"{b}[{n.slice.value!r}]" if b else None\n    return None\n\n\ndef const_val(n):\n    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):\n        return float(n.value)\n    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):\n        v = const_val(n.operand)\n        return -v if v is not None else None\n    if isinstance(n, ast.Call) and fname(n) == "sqrt" and n.args:\n        v = const_val(n.args[0])\n        return math.sqrt(v) if v is not None and v > 0 else None\n    return None\n\n\ndef unit_key(c):\n    for u in UNIT_CONST:\n        if abs(c - u) < 1e-12 * max(1, u):\n            return repr(u)\n        if abs(c - math.sqrt(u)) < 1e-9 and u > 1:\n            return f"sqrt({u!r})"\n    return None\n\n\ndef fname(call):\n    f = call.func\n    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)\n\n\ndef is_reverse_slice(s):\n    return isinstance(s, ast.Slice) and s.step is not None and const_val(s.step) == -1\n\n\ndef is_sign_test(t):\n    for n in ast.walk(t):\n        if isinstance(n, ast.Compare) and any(isinstance(o, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)) for o in n.ops) \\\n                and any(const_val(c) == 0 for c in [n.left] + n.comparators):\n            return True\n        if isinstance(n, ast.Call) and fname(n) == "sign":\n            return True\n    return False\n\n\nclass Ev:\n    def __init__(self, kind, detail, line, cell, cond, norm):\n        self.kind, self.detail, self.line, self.cell, self.cond, self.norm = kind, detail, line, cell, cond, norm\n\n\nclass Lin(dict):\n    def plus(self, other, mode):\n        out = Lin({k: list(v) for k, v in self.items()})\n        for k, v in other.items():\n            if mode == "sum":\n                out[k] = out.get(k, []) + v\n            elif len(v) > len(out.get(k, [])):\n                out[k] = list(v)\n        return out\n\n    def keep(self, kinds):\n        return Lin({k: v for k, v in self.items() if k[0] in kinds})\n\n\nclass Scope:\n    def __init__(self, src_lines, cell, fires):\n        self.state = {}\n        self.src = src_lines\n        self.cell = cell\n        self.fires = fires\n        self.cond = []\n        self.loop = 0\n        self.version = {}\n\n    def line(self, n):\n        try:\n            return self.src[n.lineno - 1].strip()\n        except Exception:\n            return ""\n\n    def get(self, k):\n        return self.state.get(k, Lin())\n\n    def obj_lineage(self, base):\n        out = Lin()\n        for k, v in self.state.items():\n            if k == base or k.startswith(base + "."):\n                out = out.plus(v, "max")\n        return out\n\n    def reset(self, base):\n        for k in [k for k in self.state if k == base or k.startswith(base + ".") or k.startswith(base + "[")]:\n            del self.state[k]\n\n    def fire(self, kind, prev, node, msg):\n        self.fires.append({"kind": kind, "cell": self.cell, "line": self.line(node),\n                           "first": f"cell {prev.cell}: {prev.line}" if prev else "", "msg": msg})\n\n    def add_event(self, lin, kind, detail, node, target_key=None, operand_key=None):\n        cond = " & ".join(c for c, _ in self.cond)\n        norm = (target_key is not None and target_key == operand_key) or any(sg for _, sg in self.cond)\n        ev = Ev(kind, detail, self.line(node), self.cell, cond, norm)\n        prev = lin.get((kind, detail), [])\n        if kind == "neg" and prev and len(prev) % 2 == 1 and norm:\n            p = prev[-1]\n            if p.norm and (not p.cond or not cond or p.cond == cond):\n                self.fire("G-sign", p, node, "sign flipped again on a value whose sign was already flipped")\n        if kind == "rev" and prev and len(prev) % 2 == 1:\n            self.fire("G-reverse", prev[-1], node, "order reversed again with no order-dependent step in between")\n        if kind == "scale" and prev:\n            self.fire("G-scale", prev[-1], node, f"same factor {detail} applied again")\n        if kind == "add" and prev and not self.loop:\n            self.fire("G-add", prev[-1], node, "same term added again")\n        out = Lin({k: list(v) for k, v in lin.items()})\n        out[(kind, detail)] = prev + [ev]\n        return out\n\n    def ev(self, n, tk=None, top=False):\n        if n is None:\n            return Lin()\n        k = key_of(n)\n        if k is not None and k in self.state:\n            return self.get(k)\n        if isinstance(n, ast.Name):\n            return self.get(n.id)\n        if isinstance(n, ast.Attribute):\n            return self.ev(n.value)\n        if isinstance(n, ast.Subscript):\n            base = n.value.value if isinstance(n.value, ast.Attribute) and n.value.attr in ("iloc", "loc", "values") else n.value\n            lin = self.ev(base)\n            if is_reverse_slice(n.slice):\n                return self.add_event(lin, "rev", "", n)\n            if isinstance(n.slice, ast.Tuple) and any(is_reverse_slice(e) for e in n.slice.elts):\n                return self.add_event(lin, "rev", "", n)\n            return lin\n        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):\n            lin = self.ev(n.operand)\n            return self.add_event(lin, "neg", "", n, tk, key_of(n.operand)) if top else lin.keep({"rev"})\n        if isinstance(n, ast.BinOp):\n            return self.binop(n, tk, top)\n        if isinstance(n, ast.Call):\n            return self.call(n, tk, top)\n        if isinstance(n, ast.IfExp):\n            return self.ev(n.body, tk).plus(self.ev(n.orelse, tk), "max")\n        return Lin()\n\n    def binop(self, n, tk, top=False):\n        L, R = n.left, n.right\n        cl, cr = const_val(L), const_val(R)\n        if isinstance(n.op, ast.Mult):\n            if cr is not None or cl is not None:\n                c, other = (cr, L) if cr is not None else (cl, R)\n                lin = self.ev(other, tk)\n                if c == -1:\n                    return self.add_event(lin, "neg", "", n, tk, key_of(other)) if top else lin.keep({"rev"})\n                u = unit_key(abs(c))\n                if u and top and tk is not None and key_of(other) == tk:\n                    lin = self.add_event(lin, "scale", f"*{u}", n)\n                return lin.keep({"rev", "scale", "neg", "add"})\n            a, b = self.ev(L, tk), self.ev(R, tk)\n            return a.plus(b, "sum").keep({"scale", "neg"}).plus(a.keep({"rev"}).plus(b.keep({"rev"}), "max"), "max")\n        if isinstance(n.op, ast.Div):\n            if cr is not None:\n                lin = self.ev(L, tk)\n                u = unit_key(abs(cr))\n                if u and top and tk is not None and key_of(L) == tk:\n                    lin = self.add_event(lin, "scale", f"/{u}", n)\n                return lin\n            a, b = self.ev(L, tk), self.ev(R)\n            inv = Lin({(k[0], ("/" + k[1][1:]) if k[1].startswith("*") else ("*" + k[1][1:])): v\n                       for k, v in b.items() if k[0] == "scale"})\n            return a.plus(inv, "sum").plus(b.keep({"neg"}), "sum").plus(b.keep({"rev"}), "max")\n        if isinstance(n.op, ast.MatMult):\n            self.product_check([L, R], n)\n            a, b = self.ev(L), self.ev(R)\n            return a.plus(b, "sum").keep({"scale", "neg"})\n        if isinstance(n.op, (ast.Add, ast.Sub)):\n            a, b = self.ev(L, tk), self.ev(R, tk)\n            out = a.keep({"rev", "scale", "add"}).plus(b.keep({"rev", "scale"}), "max")\n            if isinstance(n.op, ast.Add) and top and not self.loop and tk is not None and key_of(L) == tk:\n                names = sorted({key_of(x) for x in ast.walk(R) if key_of(x)})\n                out = self.add_event(out, "add", ast.dump(R) + repr([(x, self.version.get(x, 0)) for x in names]), n)\n            return out\n        return self.ev(n.left).keep({"rev"}).plus(self.ev(n.right).keep({"rev"}), "max")\n\n    def product_check(self, operands, node):\n        revs = [self.ev(o).get(("rev", ""), []) for o in operands]\n        if len(revs) >= 2 and all(len(r) % 2 == 1 for r in revs[:2]):\n            self.fire("G-reverse-pair", revs[0][-1], node,\n                      f"both operands reversed (first at cell {revs[1][-1].cell}: {revs[1][-1].line}); the two reversals cancel")\n\n    def call(self, n, tk, top=False):\n        f = fname(n)\n        args = list(n.args)\n        if f in REVERSE_FUNCS and args:\n            return self.add_event(self.ev(args[0]), "rev", "", n)\n        if f == "negative" and args and top:\n            return self.add_event(self.ev(args[0]), "neg", "", n, tk, key_of(args[0]))\n        if f in PRODUCTS:\n            ops = args[:2] if f != "average" else args[:1] + [kw.value for kw in n.keywords if kw.arg == "weights"]\n            if f == "einsum":\n                ops = args[1:3]\n            self.product_check(ops, n)\n            out = Lin()\n            for o in ops:\n                out = out.plus(self.ev(o), "sum")\n            return out.keep({"scale", "neg"})\n        if isinstance(n.func, ast.Attribute):\n            obj = n.func.value\n            if f in RESET_METHODS:\n                return Lin()\n            if f in OBJ_OUT and key_of(obj):\n                return self.obj_lineage(key_of(obj)).keep({"neg"})\n            if f in ORDER_DEP:\n                return self.ev(obj).keep({"scale", "neg"})\n            if f in REDUCE:\n                inner = obj\n                if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Mult):\n                    self.product_check([inner.left, inner.right], n)\n                return self.ev(obj).keep({"scale", "neg"})\n            if f in WRAPPERS:\n                return self.ev(obj, tk)\n            if isinstance(obj, ast.Name) and obj.id in ("np", "numpy", "pd", "math", "scipy"):\n                if f in WRAPPERS and args:\n                    return self.ev(args[0], tk)\n                if f in ELEMWISE and args:\n                    return self.ev(args[0]).keep({"rev"})\n                if f in REDUCE and args:\n                    a0 = args[0]\n                    if isinstance(a0, ast.BinOp) and isinstance(a0.op, ast.Mult):\n                        self.product_check([a0.left, a0.right], n)\n                    return self.ev(a0).keep({"scale", "neg"})\n                return Lin()\n            return Lin()\n        if f in WRAPPERS and args:\n            return self.ev(args[0], tk)\n        return Lin()\n\n    def assign(self, target, value_lin, node):\n        k = key_of(target)\n        if k is None:\n            if isinstance(target, (ast.Tuple, ast.List)):\n                for e in target.elts:\n                    if key_of(e):\n                        self.reset(key_of(e))\n            return\n        self.reset(k)\n        self.version[k] = self.version.get(k, 0) + 1\n        if value_lin:\n            self.state[k] = value_lin\n\n    def stmt(self, s):\n        if isinstance(s, ast.Assign):\n            tk = key_of(s.targets[0]) if len(s.targets) == 1 else None\n            lin = self.ev(s.value, tk, top=True)\n            for t in s.targets:\n                self.assign(t, lin, s)\n        elif isinstance(s, ast.AnnAssign) and s.value is not None:\n            self.assign(s.target, self.ev(s.value, key_of(s.target), top=True), s)\n        elif isinstance(s, ast.AugAssign):\n            tk = key_of(s.target)\n            if tk is None:\n                self.ev(s.value)\n                return\n            synth = ast.BinOp(left=s.target, op=s.op, right=s.value)\n            ast.copy_location(synth, s)\n            self.assign(s.target, self.ev(synth, tk, top=True), s)\n        elif isinstance(s, ast.Expr):\n            if isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Attribute) and key_of(s.value.func.value):\n                f, base = s.value.func.attr, key_of(s.value.func.value)\n                if f in RESET_METHODS:\n                    self.reset(base)\n                    return\n                if f == "reverse":\n                    self.state[base] = self.add_event(self.get(base), "rev", "", s)\n                    return\n                if f in ("sort", "sort_index", "sort_values"):\n                    self.state[base] = self.get(base).keep({"scale", "neg"})\n                    return\n            self.ev(s.value)\n        elif isinstance(s, ast.If):\n            cond = ast.unparse(s.test)\n            sg = is_sign_test(s.test)\n            saved = copy.copy(self.state)\n            self.cond.append((cond, sg))\n            self.block(s.body)\n            self.cond.pop()\n            body_state, self.state = self.state, saved\n            self.cond.append(("not " + cond, sg))\n            self.block(s.orelse)\n            self.cond.pop()\n            merged = dict(self.state)\n            for k, v in body_state.items():\n                merged[k] = merged.get(k, Lin()).plus(v, "max") if k in merged else v\n            self.state = merged\n        elif isinstance(s, (ast.For, ast.AsyncFor, ast.While)):\n            if isinstance(s, (ast.For, ast.AsyncFor)) and key_of(s.target):\n                self.reset(key_of(s.target))\n            self.loop += 1\n            self.loop_repeat(s)\n            self.block(s.body)\n            self.loop -= 1\n            self.block(s.orelse)\n        elif isinstance(s, (ast.With, ast.AsyncWith)):\n            self.block(s.body)\n        elif isinstance(s, ast.Try):\n            self.block(s.body)\n            for h in s.handlers:\n                self.block(h.body)\n            self.block(s.orelse)\n            self.block(s.finalbody)\n        elif isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):\n            sub = Scope(self.src, self.cell, self.fires)\n            sub.block(s.body)\n\n    def loop_repeat(self, loop):\n        assigned_before = set()\n        for s in loop.body:\n            tgt, val = None, None\n            if isinstance(s, ast.Assign) and len(s.targets) == 1:\n                tgt, val = s.targets[0], s.value\n            elif isinstance(s, ast.AugAssign):\n                tgt, val = s.target, ast.BinOp(left=s.target, op=s.op, right=s.value)\n            k = key_of(tgt) if tgt is not None else None\n            rebound = k is not None and any(k == a or k.startswith(a + ".") or k.startswith(a + "[") for a in assigned_before)\n            if k and val is not None and not rebound:\n                selfneg = (isinstance(val, ast.UnaryOp) and isinstance(val.op, ast.USub) and key_of(val.operand) == k) or \\\n                          (isinstance(val, ast.BinOp) and isinstance(val.op, ast.Mult) and const_val(val.right) == -1 and key_of(val.left) == k)\n                selfrev = isinstance(val, ast.Subscript) and key_of(val.value) == k and is_reverse_slice(val.slice)\n                selfscale = isinstance(val, ast.BinOp) and isinstance(val.op, (ast.Mult, ast.Div)) and key_of(val.left) == k \\\n                    and const_val(val.right) is not None and unit_key(abs(const_val(val.right)))\n                if selfneg or selfrev or selfscale:\n                    self.fires.append({"kind": "G-loop", "cell": self.cell, "line": self.line(s), "first": "",\n                                       "msg": "self-transform inside a loop on a value the loop does not rebind: applied every iteration"})\n            if k:\n                assigned_before.add(k)\n\n    def block(self, body):\n        for s in body:\n            try:\n                self.stmt(s)\n            except RecursionError:\n                pass\n\n\ndef subs_of(n, name):\n    return [s for s in ast.walk(n) if isinstance(s, ast.Subscript) and key_of(s.value) == name]\n\n\ndef endpoint_slice(s):\n    sl = s.slice\n    if not isinstance(sl, ast.Slice) or sl.step is not None:\n        return False\n    lo, up = const_val(sl.lower) if sl.lower else None, const_val(sl.upper) if sl.upper else None\n    return (sl.lower is None and up is not None and up < 0) or (lo is not None and lo > 0 and sl.upper is None)\n\n\ndef interior_slice(s):\n    sl = s.slice\n    return isinstance(sl, ast.Slice) and sl.lower is not None and sl.upper is not None and const_val(sl.lower) == 1 and const_val(sl.upper) == -1\n\n\ndef endpoint_index(s):\n    return isinstance(s.slice, (ast.Constant, ast.UnaryOp)) and const_val(s.slice) in (0, -1)\n\n\ndef boundary_double(tree, src, cell, fires):\n    for scope in [tree] + [f for f in ast.walk(tree) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]:\n        defs, stencil = {}, {}\n        for s in ast.walk(scope):\n            if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name):\n                t = s.targets[0].id\n                defs[t] = s.value\n                arrays = {key_of(x.value) for x in ast.walk(s.value) if isinstance(x, ast.Subscript) and key_of(x.value)}\n                for v in arrays:\n                    ss = subs_of(s.value, v)\n                    if any(endpoint_slice(x) for x in ss) and any(interior_slice(x) for x in ss):\n                        stencil[t] = (v, s)\n        for s in ast.walk(scope):\n            if isinstance(s, ast.AugAssign) and isinstance(s.op, ast.Add):\n                t = s.target.value if isinstance(s.target, ast.Subscript) else s.target\n                if not isinstance(t, ast.Name) or t.id not in stencil:\n                    continue\n                v, sdef = stencil[t.id]\n                if s.lineno <= sdef.lineno:\n                    continue\n                exprs = [s.value] + [defs[x.id] for x in ast.walk(s.value) if isinstance(x, ast.Name) and x.id in defs]\n                if any(endpoint_index(x) for e in exprs for x in subs_of(e, v)):\n                    fires.append({"kind": "G-boundary", "cell": cell, "line": src[s.lineno - 1].strip(),\n                                  "first": f"cell {cell}: {src[sdef.lineno - 1].strip()}",\n                                  "msg": f"{t.id} already holds {v}[0]/{v}[-1] through shifted slices; this adds a term built from them again"})\n\n\nSTATUS = re.compile(r"\\[python cell \\d+ \\| session generation (\\d+) \\| (\\w+)")\nCELL_ERR = re.compile(r\'File "<cell \\d+>", line (\\d+)\')\n\n\ndef executed_cells(msgs):\n    results = {}\n    for m in msgs:\n        if m.get("role") == "tool":\n            results[m.get("tool_call_id")] = str(m.get("content") or "")\n    out = []\n    for i, m in enumerate(msgs):\n        if m.get("role") != "assistant":\n            continue\n        for tc in m.get("tool_calls") or []:\n            try:\n                a = json.loads(tc["function"]["arguments"])\n                code = a.get("code") or a.get("command") or ""\n            except Exception:\n                continue\n            res = results.get(tc.get("id"), "")\n            try:\n                res = json.loads(res).get("output", res)\n            except Exception:\n                pass\n            st = STATUS.search(res)\n            gen, status = (int(st.group(1)), st.group(2)) if st else (None, "unknown")\n            errs = CELL_ERR.findall(res)\n            out.append((i, code, gen, status, int(errs[0]) if errs else None))\n    return out\n\n\ndef scan(msgs):\n    fires = []\n    state, version = {}, {}\n    gen = None\n    for ci, (mi, code, g, status, errline) in enumerate(executed_cells(msgs)):\n        if status in ("syntax_error",) or not code.strip():\n            continue\n        if g is not None and gen is not None and g != gen:\n            state, version = {}, {}\n        gen = g if g is not None else gen\n        try:\n            tree = ast.parse(code)\n        except SyntaxError:\n            continue\n        body = tree.body\n        if status != "ok" and errline is not None:\n            body = [s for s in body if s.lineno <= errline]\n        src = code.splitlines()\n        sc = Scope(src, mi, fires)\n        sc.state, sc.version = state, version\n        sc.block(body)\n        state, version = sc.state, sc.version\n        boundary_double(ast.Module(body=body, type_ignores=[]), src, mi, fires)\n    return fires'


def dg_module(src: str, name: str) -> dict:
    ns = {"__name__": name}
    exec(compile(src, f"<{name}>", "exec"), ns)
    return ns


VC2 = dg_module('import math\nimport re\n\nFIELD_WRITE = re.compile(r"""["\']([A-Za-z_]\\w*)["\']\\s*:\\s*(\\{\\s*["\']value["\']\\s*:\\s*)?(?:float\\(\\s*)?([A-Za-z_]\\w*)\\s*\\)?""")\nASSIGN = re.compile(r"^\\s*([A-Za-z_]\\w*)\\s*=(?!=)\\s*(.+)$")\nZ_SIGMA = re.compile(r"\\bz\\w*\\s*\\*\\s*\\w*sig\\w*|\\b\\w*sig\\w*\\s*\\*\\s*z\\w*\\b", re.I)\n\n\ndef is_var_field(name: str) -> bool:\n    """A field named for a VaR: a `var` token (var, var95, var_99 ...) and no variance or ratio token."""\n    toks = name.lower().split("_")\n    return any(re.fullmatch(r"var\\d*", t) for t in toks) and not {"variance", "ratio", "pct", "contribution"} & set(toks)\n\n\ndef is_variance_name(name: str) -> bool:\n    """A variable named for a variance: variance in the name, or var_p."""\n    low = name.lower()\n    return "variance" in low or low == "var_p"\n\n\ndef var_writes(code: str) -> list[tuple[str, str, str, bool]]:\n    """(code line, field, variance name, written as {"value": ...}) for each VaR field written from a variance name."""\n    out = []\n    for line in code.splitlines():\n        for m in FIELD_WRITE.finditer(line):\n            if is_var_field(m.group(1)) and is_variance_name(m.group(3)):\n                out.append((line.strip(), m.group(1), m.group(3), bool(m.group(2))))\n    return out\n\n\ndef var_assignments(history: str) -> list[tuple[str, str]]:\n    """(name, code line) of the session\'s VaR variables, last assignment of each name: a name starting var_ that is not\n    variance-named, or a name assigned z * sigma."""\n    found = {}\n    for line in history.splitlines():\n        m = ASSIGN.match(line)\n        if not m:\n            continue\n        name, expr = m.groups()\n        if is_variance_name(name):\n            continue\n        if name.lower().startswith("var_") or Z_SIGMA.search(expr):\n            found.pop(name, None)\n            found[name] = line.strip()\n    return list(found.items())\n\n\ndef var_v2_note(cell: int, write_line: str, field: str, vname: str, vval: float, var_name: str, var_line: str,\n                var_val: float, value_dict: bool) -> str | None:\n    """The VaR v2 message, or None when the two values do not read as a variance and a VaR (both positive, the variance\n    below the VaR)."""\n    if not (all(isinstance(x, float) and math.isfinite(x) for x in (vval, var_val)) and 0 < vval < var_val):\n        return None\n    copy = f\'"{field}": {{"value": float({var_name})}},\' if value_dict else f\'"{field}": float({var_name}),\'\n    return (f"Check after cell {cell}: `{write_line}` writes `{field}` from `{vname}` = {vval!r}, a variance, while the "\n            f"session computes `{var_line}` = {var_val!r}, a VaR. `{field}` names a VaR, for example:\\n    {copy}\\n"\n            f"Keep the variance only if you can quote, word for word, a task sentence that defines `{field}` as a variance.")\n\n\ndef statement_blocks(statement: str) -> list[str]:\n    """Paragraphs and list items of the task, each on one line; headings start a new block and are left out."""\n    blocks, cur = [], []\n    for line in statement.splitlines():\n        if not line.strip() or line.lstrip().startswith("#") or re.match(r"\\s*(?:\\d+[.)]|[-*])\\s", line):\n            if cur:\n                blocks.append(" ".join(cur))\n            cur = [] if not line.strip() or line.lstrip().startswith("#") else [line.strip()]\n        else:\n            cur.append(line.strip())\n    if cur:\n        blocks.append(" ".join(cur))\n    return blocks\n\n\ndef cohort_sentence(statement: str, table: str) -> str | None:\n    """The task\'s sentence that defines the table\'s counts: in the entry naming the table, the sentence holding\n    "number of"; else a sentence holding both "cohort" and "number of"."""\n    def sentences(block):\n        return [x.strip() for x in re.split(r"(?<=[.!?])\\s+(?=[A-Z`*(\\"])", block)]\n    for block in statement_blocks(statement):\n        if table in block:\n            hit = [x for x in sentences(block) if re.search(r"number of", x, re.I)]\n            if hit:\n                return hit[0]\n    for block in statement_blocks(statement):\n        for x in sentences(block):\n            if re.search(r"cohort", x, re.I) and re.search(r"number of", x, re.I):\n                return x\n    return None\n\n\ndef total_line(history: str, key: str) -> str | None:\n    """The session\'s last assignment of the total\'s name, else the last line writing it as a field."""\n    lines = history.splitlines()\n    for rx in (rf"^\\s*{re.escape(key)}\\s*=(?!=)", rf"""["\']{re.escape(key)}["\']\\s*:"""):\n        hit = [x.strip() for x in lines if re.search(rx, x)]\n        if hit:\n            return hit[-1]\n    return None\n\n\ndef summed_matrix(line: str) -> str | None:\n    """The name summed whole in a total line (`int(M.sum())`, `M.sum()`, `np.sum(M)`), else None."""\n    m = re.search(r"=\\s*(?:int\\(\\s*)?(?:([A-Za-z_]\\w*)\\.sum\\(\\s*\\)|np\\.sum\\(\\s*([A-Za-z_]\\w*)\\s*\\))", line)\n    return (m.group(1) or m.group(2)) if m else None\n\n\ndef count_v2_note(file: str, key: str, v: int, table: str, t: int, sentence: str | None, line: str | None,\n                  matrix: str | None, row_sums: list[float] | None) -> str:\n    """The Count note v2 message: the task\'s cohort-size sentence, the rows each figure sums, a conditional request and a\n    line to copy; the rows part and the line use the summed matrix\'s row sums when one row explains the difference."""\n    d = v - t\n    head = f\'Count check ({file}): the task says: "{sentence}" \' if sentence else f"Count check ({file}): "\n    src = f"`{line}` gives `{key}` = {v}" if line else f"`{key}` is {v}"\n    copy, rows = None, ""\n    if matrix and row_sums:\n        hit = [j for j, s in enumerate(row_sums) if round(s) == d]\n        if len(hit) == 1:\n            j, n = hit[0], len(row_sums)\n            rows = (f", summing all {n} origin rows of `{matrix}` including row {j} (row sum {round(row_sums[j])})")\n            copy = (f"{key} = int({matrix}[:{n - 1}].sum())" if j == n - 1\n                    else f"{key} = int(np.delete({matrix}, {j}, axis=0).sum())")\n    if copy is None:\n        copy = f"{key} = <the same rows that build {table}>.sum()"\n    return (f"{head}{src}{rows}, while {table} sums to {t} (difference {d}). If these two figures describe the same "\n            f"population, count the same rows in both, for example:\\n    {copy}\\nOtherwise keep both and quote, word for "\n            f"word, the task sentence that defines which rows `{key}` counts.")\n', "oc10_var_count_v2")
VAR_V2_SHOWN: set[str] = set()
VAR_V2_FIELDS: set[str] = set()


DG_D = dg_module(DG_D_SRC, "dg_d")
DG_G = dg_module(DG_G_SRC, "dg_g")
DG_HINT_TAIL = " If the task defines it differently, keep it and say why."
DG_G_KINDS = {"G-sign": 'Code note: `{line2}` flips a value that already carries the flip from `{line1}`; two flips cancel. Decide the sign once, as a number, and apply that number to every score; do not also change the fitted loadings:\n    pc_train = pca.fit_transform(X_train)[:, 0]\n    s = -1.0 if np.corrcoef(pc_train, ref_train)[0, 1] < 0 else 1.0\n    pc_train = s * pc_train                          # scores used for fitting\n    pc_new = s * pca.transform(X_new)[:, 0]          # every later observation, same s\nRemove any other sign change on pca.components_ or on the transformed scores. Then print np.corrcoef(pc_train, ref_train)[0, 1] and check that it has the sign the task asks for.'}
DG_G_SHOWN: set[tuple] = set()


def dg_input_params() -> dict:
    out = {}
    for root in DATA_DIRS:
        for p in sorted(pathlib.Path(root).glob("*.json")):
            try:
                for path, v in DG_D["leaves"](json.loads(p.read_text())):
                    out[path.split(".")[-1]] = v
            except (OSError, ValueError):
                continue
    return out


def dg_output_notes() -> list[str]:
    out = []
    for hit in DG_D["check_resolution"](OUTPUT_DIR):
        out.append(f"Output check: {hit}. The same quantity at two resolutions should agree closely: refining a convergent "
                   "discretisation, or adding simulation paths, changes the result by an error that shrinks with the "
                   "refinement, so a gap this size usually means the two runs did not solve the same problem (for example "
                   "a step size, horizon or parameter read from outside the function instead of from its own arguments). "
                   "Recompute both from the same inputs and print their difference." + DG_HINT_TAIL)
    for hit in DG_D["check_half_life"](OUTPUT_DIR, dg_input_params()):
        if "do not convert" in hit:
            why = ("Converting a half-life between years, days and observation periods multiplies by the length of one "
                   "unit; check which unit each field is in.")
        elif "fits no single" in hit:
            why = ("half_life x kappa = ln 2 holds in one time unit of kappa (per year, per day or per observation step); "
                   "check which unit kappa is per and convert each half-life into that unit before applying the identity.")
        else:
            why = ("A lag-1 autocorrelation of that size means a deviation keeps more than half of its size after one step, "
                   "which implies a half-life longer than one step (phi ** h = 1/2). Check the time unit of the half-life "
                   "(for example whether the step length dt was applied).")
        out.append(f"Output check: {hit}. {why}" + DG_HINT_TAIL)
    return out


OC7_SRC = {'flags/self_check_flags.py': 'import glob\nimport json\nimport os\nimport re\n\nFLAG_KEY = re.compile(r"(all_checks|checks?_pass|_passed$|^passed$|_ok$|^ok_|is_valid|valid$|consistent|close_to|_positive$|"\n                      r"nonnegative|non_negative|monotone|monotonic|convex|_leq_|_geq_|within_tol|sums?_to_one|reconcil|"\n                      r"matches?$|_match_)", re.I)\n\n\ndef flag_walk(o, p=""):\n    """(dotted path, leaf) for every leaf, lists cut at 50 items as in flagscan.py."""\n    if isinstance(o, dict):\n        for k, v in o.items():\n            yield from flag_walk(v, f"{p}.{k}" if p else k)\n    elif isinstance(o, list):\n        for i, v in enumerate(o[:50]):\n            yield from flag_walk(v, f"{p}[{i}]")\n    else:\n        yield p, o\n\n\ndef flag_notes(output_dir: str) -> list[str]:\n    """One message per false check flag in the JSON outputs."""\n    out = []\n    try:\n        for f in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):\n            try:\n                data = json.load(open(f))\n            except (OSError, ValueError):\n                continue\n            rel = os.path.relpath(f, output_dir)\n            for p, v in flag_walk(data):\n                if v is False and FLAG_KEY.search(p.split(".")[-1]):\n                    out.append(f"Output check: your own check `{p}` in {rel} reports false; find which input or step makes it "\n                               "false and fix it. Do not loosen the check\'s tolerance to make it pass; find the step that makes the "\n                               "values disagree. If the check itself is wrong for this task, correct the check and say why.")\n    except Exception:\n        return out\n    return out\n', 'varES/var_variance.py': '"""Output check: a field read as Value-at-Risk holds a number on the scale of a variance."""\nimport csv\nimport glob\nimport json\nimport math\nimport os\nimport re\nfrom collections import defaultdict\n\nVAR_TOK = re.compile(r"var\\d*$")\nVAR_CUES = [r"value[- ]at[- ]risk", r"\\bVaR\\b", r"\\bquantile", r"\\bpercentile", r"\\bconfidence", r"expected shortfall",\n            r"\\bCVaR\\b", r"\\btail\\b", r"\\blosses?\\b"]\nVARIANCE_CUES = [r"\\bvariances?\\b", r"σ\\s*²|σ\\^2|sigma\\^?2|sigma\\*\\*2|\\\\sigma\\^2", r"\\bsquared\\b", r"\\b[Vv]ar\\s*\\(",\n                 r"second moment"]\nCASE_VAR = (r"\\bVaR\\b", r"\\bCVaR\\b", r"\\b[Vv]ar\\s*\\(")\nCASE_VARIANCE = (r"\\b[Vv]ar\\s*\\(",)\nPARTNER_VAR = {"es", "cvar", "shortfall"}\nPARTNER_VARIANCE = {"mean", "e", "std", "vol", "sd", "stdev"}\nLEVEL_TOK = re.compile(r"(90|95|97|975|99|995|999|\\d+pct)$")\nNON_LEVEL = {"pct", "ratio", "rel", "error", "relerr", "rmse", "err", "factor", "scale", "share", "contribution",\n             "confidence", "alpha", "level", "count", "num", "n", "positive", "sharpe", "wealth", "drawdown", "median",\n             "p50", "floor", "cap", "component", "range"}\nES_TOK = {"es", "cvar", "shortfall"}\nLIMIT_TOK = {"limit", "max", "cap", "budget", "threshold", "target"}\n\n\ndef _tokens(name):\n    s = re.sub(r"VaR", "_var_", name)\n    s = re.sub(r"([a-z0-9])([A-Z])", r"\\1_\\2", s)\n    return [t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t]\n\n\ndef _is_var_name(name):\n    return any(VAR_TOK.match(t) for t in _tokens(name))\n\n\ndef _cue_counts(text):\n    v = sum(len(re.findall(p, text, flags=0 if p in CASE_VAR else re.I)) for p in VAR_CUES)\n    w = sum(len(re.findall(p, text, flags=0 if p in CASE_VARIANCE else re.I)) for p in VARIANCE_CUES)\n    return v, w\n\n\ndef _paragraph_of(lines, i):\n    a = i\n    while a > 0 and lines[a - 1].strip():\n        a -= 1\n    b = i\n    while b + 1 < len(lines) and lines[b + 1].strip():\n        b += 1\n    return "\\n".join(lines[a:b + 1])\n\n\ndef _stem_partner(name, idents):\n    toks = _tokens(name)\n    idx = [i for i, t in enumerate(toks) if VAR_TOK.match(t)]\n    others = {}\n    for x in sorted(idents):\n        if x != name:\n            others.setdefault(tuple(_tokens(x)), x)\n    for i in idx:\n        for lab, group in (("VaR", PARTNER_VAR), ("variance", PARTNER_VARIANCE)):\n            for p in sorted(group):\n                alt = tuple(toks[:i] + [p + toks[i][3:]] + toks[i + 1:])\n                alt2 = tuple(toks[:i] + [p] + toks[i + 1:])\n                hit = others.get(alt) or others.get(alt2)\n                if hit:\n                    return lab, hit\n    return None, None\n\n\ndef _doc_mentions_var(stmt):\n    return bool(re.search(r"value[- ]at[- ]risk", stmt, re.I) or re.search(r"\\b[CS]?VaRs?\\b", stmt))\n\n\ndef _doc_prior(stmt):\n    v = len(re.findall(r"value[- ]at[- ]risk", stmt, re.I)) + len(re.findall(r"\\b[CS]?VaRs?\\b", stmt))\n    w = len(re.findall(r"\\bvariances?\\b", stmt, re.I))\n    return "VaR" if v and not w else ("variance" if w and not v else "none")\n\n\ndef _classify_in_statement(stmt, name):\n    lines = stmt.splitlines()\n    idents = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stmt))\n    pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")\n    hits = [i for i, l in enumerate(lines) if pat.search(l)]\n    if not hits:\n        return "absent", "", ""\n\n    def score(level):\n        v = w = 0\n        ev = ""\n        for i in hits:\n            txt = lines[i] if level == "line" else _paragraph_of(lines, i)\n            a, b = _cue_counts(pat.sub(" ", txt))\n            v += a\n            w += b\n            if (a or b) and not ev:\n                ev = txt.strip().replace("\\n", " ")[:220]\n        return v, w, ev\n\n    v, w, ev = score("line")\n    if v != w:\n        return ("VaR" if v > w else "variance"), "line", ev\n    lab, twin = _stem_partner(name, idents)\n    if lab:\n        return lab, "partner", f"twin field `{twin}`"\n    v, w, ev = score("paragraph")\n    if v != w:\n        return ("VaR" if v > w else "variance"), "paragraph", ev\n    if any(LEVEL_TOK.match(t) for t in _tokens(name)):\n        return "VaR", "level-token", "name carries a confidence level token"\n    spelled = sorted(x for x in idents if "variance" in _tokens(x))\n    if spelled and _doc_mentions_var(stmt):\n        return "VaR", "contrast", f"statement spells variance out elsewhere (`{spelled[0]}`) and talks about VaR"\n    d = _doc_prior(stmt)\n    if d != "none":\n        return d, "document", "statement-wide wording"\n    return "undefined", "", lines[hits[0]].strip()[:220]\n\n\ndef _meaning(name, stmt, sib_names):\n    lab, level, ev = _classify_in_statement(stmt, name)\n    if lab in ("VaR", "variance"):\n        return lab, level, ev\n    t, twin = _stem_partner(name, sib_names)\n    if t:\n        return t, "output-twin", f"output twin `{twin}`"\n    d = _doc_prior(stmt)\n    if d != "none":\n        return d, "document", "statement-wide wording"\n    return "undefined", "", ""\n\n\ndef _is_num(x):\n    try:\n        float(x)\n        return True\n    except ValueError:\n        return False\n\n\ndef _flatten(obj, path=()):\n    if isinstance(obj, dict):\n        if "value" in obj and isinstance(obj["value"], (int, float)) and not isinstance(obj["value"], bool):\n            yield path, float(obj["value"])\n            return\n        for k, v in obj.items():\n            yield from _flatten(v, path + (str(k),))\n    elif isinstance(obj, list):\n        for i, v in enumerate(obj[:200]):\n            yield from _flatten(v, path + (f"[{i}]",))\n    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):\n        yield path, float(obj)\n\n\ndef _leaf_name(path):\n    for p in reversed(path):\n        if not p.startswith("["):\n            return p\n    return ""\n\n\ndef _read_outputs(output_dir):\n    out = []\n    for f in sorted(glob.glob(os.path.join(output_dir, "**", "*"), recursive=True)):\n        rel = os.path.relpath(f, output_dir)\n        if f.endswith(".json"):\n            try:\n                with open(f) as fh:\n                    obj = json.load(fh)\n            except Exception:\n                continue\n            for path, val in _flatten(obj):\n                out.append(dict(file=rel, name=_leaf_name(path), value=val, group=path[:-1]))\n        elif f.endswith(".csv") and os.path.getsize(f) < 5_000_000:\n            try:\n                with open(f, errors="replace") as fh:\n                    rows = list(csv.reader(fh))\n            except Exception:\n                continue\n            if not rows:\n                continue\n            hdr = rows[0]\n            if not any(_is_var_name(x) for r in rows[:50] for x in r if not _is_num(x)):\n                continue\n            for ri, r in enumerate(rows[1:2001]):\n                for ci, c in enumerate(r):\n                    if ci < len(hdr):\n                        try:\n                            val = float(c)\n                        except ValueError:\n                            continue\n                        label = hdr[ci]\n                        rowkey = [x for x in r if x and not _is_num(x)]\n                        if rowkey and not _is_var_name(label) and any(_is_var_name(x) for x in rowkey):\n                            label = next(x for x in rowkey if _is_var_name(x))\n                        out.append(dict(file=rel, name=label, value=val, group=("row", ri)))\n    return out\n\n\ndef _read_inputs(data_dirs):\n    res = {}\n    for d in data_dirs:\n        for f in sorted(glob.glob(os.path.join(d, "**", "*.json"), recursive=True)):\n            try:\n                if os.path.getsize(f) > 2_000_000 or os.path.basename(f) == "glossary.json":\n                    continue\n                with open(f) as fh:\n                    obj = json.load(fh)\n            except Exception:\n                continue\n            for path, val in _flatten(obj):\n                res[".".join(path)] = val\n    return res\n\n\ndef _note(file, name, v, level, ev, b, c):\n    why = ev if level in ("line", "paragraph") else (\n        "the task statement talks about VaR / Value-at-Risk and never uses the word \'variance\'" if level == "document" else ev)\n    parts = [f"{file}: `{name}` = {v:.6g}. The name reads as Value-at-Risk here ({why})."]\n    for k, r in b[:1]:\n        parts.append(f"The VaR-scale reference `{k}` = {r:.6g} is {r / v:.0f}x larger, while sqrt({v:.6g}) = {math.sqrt(v):.6g} "\n                     f"is on that scale: the value has the magnitude of a variance (sigma^2), not of a VaR (z * sigma).")\n    for sn, sv, k, r in c[:1]:\n        parts.append(f"`{sn}` = {sv:.6g} < 1 says the `{k}` limit binds, so the unscaled VaR must be above {r:.6g}; "\n                     f"the reported value is below that limit.")\n    parts.append(f"Re-derive which quantity this field holds. Keep the value only if you can quote, word for word, the sentence "\n                 f"of the task that defines `{name}` itself as a variance; a formula elsewhere that uses a portfolio variance "\n                 f"does not define this field. If you cannot quote such a sentence, change the value.")\n    return " ".join(parts)\n\n\ndef _findings(output_dir, statement, data_dirs):\n    outs = _read_outputs(output_dir)\n    ins = _read_inputs(data_dirs)\n    scopes = defaultdict(list)\n    for o in outs:\n        key = (o["file"], o["group"]) if o["group"][:1] == ("row",) else (o["file"],)\n        scopes[key].append(o)\n    limits = [(k, v) for k, v in ins.items()\n              if _is_var_name(k.split(".")[-1]) and set(_tokens(k.split(".")[-1])) & LIMIT_TOK and v > 0]\n    notes = {}\n    seen = set()\n    for key, sib in scopes.items():\n        names = frozenset(o["name"] for o in sib)\n        for o in sib:\n            n, v = o["name"], o["value"]\n            if not _is_var_name(n) or set(_tokens(n)) & NON_LEVEL or (key, n) in seen:\n                continue\n            seen.add((key, n))\n            if (o["file"], n) in notes or v <= 0:\n                continue\n            lab, level, ev = _meaning(n, statement, names)\n            if lab != "VaR":\n                continue\n            ess = [s for s in sib if set(_tokens(s["name"])) & ES_TOK and not _is_var_name(s["name"]) and s["value"] > 0]\n            scale = [s for s in sib if _is_var_name(s["name"]) and {"scale", "factor"} & set(_tokens(s["name"])) and 0 < s["value"] < 1]\n            refs = list(limits) + [(s["name"], s["value"]) for s in ess]\n            b = [(k, r) for k, r in refs if v < r / 10 and 0.2 * r <= math.sqrt(v) <= 3 * r]\n            c = [(s["name"], s["value"], k, r) for s in scale for k, r in limits if v < (r / s["value"]) / 10]\n            if b or c:\n                notes[(o["file"], n)] = _note(o["file"], n, v, level, ev, b, c)\n    return list(dict.fromkeys(notes.values()))\n\n\ndef var_variance_notes(output_dir: str, statement: str, data_dirs: tuple) -> list[str]:\n    try:\n        return _findings(output_dir, statement or "", tuple(data_dirs or ()))\n    except Exception:\n        return []\n', 'candidate/candidate_checks.py': 'import csv\nimport glob\nimport json\nimport os\nimport re\nfrom collections import Counter\n\nROLL_MINUS = re.compile(r"(\\w+)\\.rolling\\((?:window=)?\\s*(\\d+)[^)]*\\)\\.sum\\(\\)\\s*-\\s*(\\w+)\\b(?!\\s*\\.)")\nDICT_LIT = re.compile(r"\\{[^{}]*\\}", re.S)\nREG_STAT = re.compile(r"""[\'"]\\w*(?:slope|r_squared|rsquared|intercept|beta)\\w*[\'"]\\s*:""", re.I)\nNOBS_LEN = re.compile(r"""[\'"]((?:num_observations|n_obs|nobs|num_obs|n_observations)\\w*)[\'"]\\s*:\\s*((?:int\\()?\\s*len\\(\\s*([A-Za-z_]\\w*)\\s*\\)\\)?)""")\nRAW_TABLE_NAMES = {"df", "series", "data"}\nDATE_KEYS = ("date", "datetime", "timestamp", "time")\nID_COLS = ("ticker", "symbol", "asset", "id", "trade_id", "sector", "fund", "name", "venue", "tenor", "currency", "pair", "contract")\n\n\ndef roll_minus_notes(code: str, history: str, statement: str) -> list[tuple[str, str]]:\n    """L1: a rolling sum minus the same series, which leaves an (N-1)-row window ending one row before t."""\n    out = []\n    for line in code.splitlines():\n        body = line.split("#", 1)[0]\n        for m in ROLL_MINUS.finditer(body):\n            if m.group(1) != m.group(3):\n                continue\n            n, x = int(m.group(2)), m.group(1)\n            out.append((f"L1:{body.strip()}",\n                        f"Code note: `{body.strip()}` covers rows t-{n - 1} .. t-1 (an {n - 1}-row window ending one row before "\n                        "t). If the task\'s window ends earlier or starts later, shift before summing so the covered rows match it, "\n                        f"e.g. `{x}.shift(k).rolling(n).sum()` covers t-k-n+1 .. t-k."))\n    return out\n\n\ndef dup_dates_notes(output_dir: str, history: str) -> list[str]:\n    """O1: a CSV keyed by one date column, other columns numeric, where every date appears the same k >= 2 times."""\n    out = []\n    for f in sorted(glob.glob(os.path.join(output_dir, "*.csv"))):\n        try:\n            with open(f, newline="", errors="replace") as fh:\n                rd = csv.reader(fh)\n                hdr = next(rd)\n                data = [r for r in rd if r]\n        except (OSError, StopIteration, csv.Error):\n            continue\n        if len(hdr) < 2 or len(data) < 4:\n            continue\n        key = [j for j, h in enumerate(hdr) if h.lower() in DATE_KEYS]\n        if len(key) != 1 or any(h.lower() in ID_COLS for h in hdr):\n            continue\n\n        def numeric(x):\n            try:\n                float(x)\n                return True\n            except ValueError:\n                return x == ""\n        cnt = Counter(r[key[0]] for r in data)\n        reps = set(cnt.values())\n        if not (len(reps) == 1 and min(reps) >= 2 and len(cnt) >= 3):\n            continue\n        if not all(numeric(r[j]) for r in data[:50] for j in range(len(hdr)) if j != key[0] and j < len(r)):\n            continue\n        k = min(reps)\n        guard = re.search(r"^[ \\t]*if\\s+[\'\\"]\\w+[\'\\"]\\s+not\\s+in\\s+(?:locals|globals)\\(\\)\\s*:[^\\n]*", history, re.M)\n        cause = (f" Lists created under `{guard.group(0).strip()}` still hold the rows appended by an earlier cell, so a loop "\n                 "appends a second copy." if guard else "")\n        times = "twice" if k == 2 else f"{k} times"\n        out.append(f"Output check: `{os.path.basename(f)}` has {len(data)} rows but only {len(cnt)} distinct dates; every date "\n                   f"appears exactly {times}.{cause} Re-create the lists unconditionally before the loop, then check the row "\n                   "count against the input.")\n    return out\n\n\ndef json_objects_with_key(data, key, path=""):\n    """(dotted path, object) for every JSON object holding the key."""\n    if isinstance(data, dict):\n        if key in data:\n            yield path, data\n        for k, v in data.items():\n            yield from json_objects_with_key(v, key, f"{path}.{k}" if path else str(k))\n    elif isinstance(data, list):\n        for i, v in enumerate(data[:200]):\n            yield from json_objects_with_key(v, key, f"{path}[{i}]")\n\n\ndef json_dicts(data, path=""):\n    """(dotted path, object) for every JSON object."""\n    if isinstance(data, dict):\n        yield path, data\n        for k, v in data.items():\n            yield from json_dicts(v, f"{path}.{k}" if path else str(k))\n    elif isinstance(data, list):\n        for i, v in enumerate(data[:200]):\n            yield from json_dicts(v, f"{path}[{i}]")\n\n\ndef nobs_in_outputs(output_dir: str, field: str):\n    """(file, path, value, count named <field>_..., its value, file holding a top-level field of the same name or "") for the\n    first written object that holds the field next to regression statistics; None when the outputs do not hold them."""\n    files = sorted(glob.glob(os.path.join(output_dir, "*.json"))) if output_dir else []\n    loaded = {}\n    for f in files:\n        try:\n            loaded[f] = json.load(open(f))\n        except (OSError, ValueError):\n            continue\n    for f, data in loaded.items():\n        for path, obj in json_objects_with_key(data, field):\n            v = obj.get(field)\n            if not path or not isinstance(v, int) or isinstance(v, bool) or not any(REG_STAT.search(f"\'{k}\':") for k in obj):\n                continue\n            sibs = [(k, x) for d in loaded.values() for _, o in json_dicts(d) for k, x in o.items()\n                    if k != field and k.startswith(field + "_") and isinstance(x, int) and not isinstance(x, bool) and x != v]\n            if not sibs:\n                continue\n            sib, sv = min(sibs, key=lambda kx: not kx[0].endswith("_fit"))\n            top = next((os.path.basename(g) for g, d in loaded.items() if isinstance(d, dict) and field in d), "")\n            return os.path.basename(f), path, v, sib, sv, top\n    return None\n\n\ndef nobs_len_notes(code: str, history: str, statement: str, output_dir: str = "") -> list[tuple[str, str]]:\n    """N1 (narrowed): a count beside regression statistics written as len() of the whole table; the message names the file,\n    path and a sibling count from the outputs when they hold them, else the general text."""\n    out = []\n    for d in DICT_LIT.finditer(code):\n        block = d.group(0)\n        if not REG_STAT.search(block):\n            continue\n        for m in NOBS_LEN.finditer(block):\n            field, expr, name = m.group(1), m.group(2).strip(), m.group(3)\n            if name not in RAW_TABLE_NAMES and not re.search(rf"^[ \\t]*{re.escape(name)}\\s*=\\s*pd\\.read_\\w+\\(", history, re.M):\n                continue\n            found = nobs_in_outputs(output_dir, field)\n            if found:\n                f, path, v, sib, sv, top = found\n                other = f" The top-level `{field}` in {top} is a different field." if top and top != f else ""\n                msg = (f"Code note: `{f}` -> `{path}.{field}` = {v} (`{expr}`), but the regression whose statistics sit next to it "\n                       f"in `{path}` uses one pair per consecutive row (your `{sib}` = {sv}).{other} Check which count "\n                       f"`{path}.{field}` describes.")\n            else:\n                msg = (f"Code note: `{field}` is written as `{expr}`, next to regression statistics. A regression of a change on "\n                       "a lagged level uses one pair per consecutive row, so its sample has one row fewer than the table. A count "\n                       "reported beside regression statistics is normally the regression\'s sample size (`len(y)` or "\n                       "`model.nobs`); check which one the field describes.")\n            out.append((f"N1:{field}:{expr}", msg))\n    return out\n', 'rootcause/local_vol_identity.py': 'import glob\nimport json\nimport math\nimport os\nimport re\n\nimport numpy as np\nimport pandas as pd\n\nLV_COLS = ("local_vol", "localvol", "sigma_local", "local_volatility", "sigma_loc")\nIV_COLS = ("implied_vol", "iv", "implied_volatility", "sigma_imp", "impl_vol")\nM_COLS = ("moneyness", "k_ratio", "k_over_s", "k_s", "k/s0", "k/s")\nM_LO, M_HI = 0.95, 1.05\nR_LO, R_HI = 0.5, 1.8\nFLAT_IV_TOL = 1e-6\nFLAT_LV_TOL = 0.05\nS0_TEXT = re.compile(r"(?<![/A-Za-z])(?:S_?0|S₀|S_\\{0\\})\\$?\\**\\s*(?:=|:|≈|\\|)\\s*\\$?\\s*([0-9]+(?:\\.[0-9]+)?)")\nS0_KEYS = ("s0", "s_0", "spot", "spot_price", "underlying_price")\nTAIL = "If the task defines it differently, keep it and say why."\n\n\ndef _g(x) -> str:\n    """Short rendering of a run value."""\n    try:\n        return "nan" if x is None or not math.isfinite(float(x)) else f"{float(x):.4g}"\n    except Exception:\n        return str(x)\n\n\ndef _pick(cols: dict, names: tuple):\n    """First column whose lowercased name is in names."""\n    return next((cols[c] for c in cols if c in names), None)\n\n\ndef _row_checks(path: str, df: pd.DataFrame) -> list:\n    """Near-ATM ratio and flat-surface identity on a long-format table."""\n    out = []\n    cols = {str(c).strip().lower(): c for c in df.columns}\n    lv, iv, mc = _pick(cols, LV_COLS), _pick(cols, IV_COLS), _pick(cols, M_COLS)\n    if not (lv and iv):\n        return out\n    name = os.path.basename(path)\n    a = pd.to_numeric(df[lv], errors="coerce")\n    b = pd.to_numeric(df[iv], errors="coerce")\n    if "flat" in name.lower():\n        bb = b.dropna()\n        if len(bb) and bb.gt(0).all():\n            spread = (bb.max() - bb.min()) / bb.abs().max()\n            if spread > FLAT_IV_TOL:\n                out.append(f"{name}: this flat-volatility test file has {iv} ranging {_g(bb.min())}–{_g(bb.max())}, so the "\n                           f"input surface is not flat. The flat test should feed one constant implied volatility. {TAIL}")\n            else:\n                c = float(bb.iloc[0])\n                dev = (a / c - 1).abs()\n                bad = dev.isna() | (dev > FLAT_LV_TOL)\n                if bad.any():\n                    i = int(np.flatnonzero(bad.to_numpy())[0])\n                    out.append(f"{name}: the input implied volatility is constant at {_g(c)}, but {lv} is {_g(a.iloc[i])} on "\n                               f"row {i} ({int(bad.sum())} of {len(a)} rows off by more than {FLAT_LV_TOL:.0%} or NaN; "\n                               f"{lv} range {_g(a.min())}–{_g(a.max())}). Under a flat implied surface the local volatility "\n                               f"equals that same constant. {TAIL}")\n        return out\n    if not mc:\n        return out\n    m = pd.to_numeric(df[mc], errors="coerce")\n    sel = (m > M_LO) & (m < M_HI) & b.gt(0)\n    if not sel.any():\n        return out\n    ratio = a[sel] / b[sel]\n    bad = ratio.isna() | (ratio < R_LO) | (ratio > R_HI)\n    if bad.any():\n        idx = ratio[bad].index[0]\n        out.append(f"{name}: near the money ({mc} {M_LO}–{M_HI}) {lv}/{iv} is outside [{R_LO}, {R_HI}] or NaN in "\n                   f"{int(bad.sum())} of {int(sel.sum())} rows (ratio range {_g(ratio.min())}–{_g(ratio.max())}; e.g. "\n                   f"{mc}={_g(m[idx])}: {lv}={_g(a[idx])}, {iv}={_g(b[idx])}). Near the money local and implied volatility "\n                   f"are of the same size; a ratio this far off usually means a derivative or its denominator is scaled "\n                   f"wrongly. {TAIL}")\n    return out\n\n\ndef _matrix(path: str):\n    """Strike-by-maturity matrix (index = strikes, columns = maturities) or None."""\n    try:\n        df = pd.read_csv(path, index_col=0)\n        df.index = pd.to_numeric(df.index, errors="raise").astype(float)\n        df.columns = [float(c) for c in df.columns]\n        df = df.apply(pd.to_numeric, errors="coerce")\n        return df if df.shape[0] >= 3 and df.shape[1] >= 3 else None\n    except Exception:\n        return None\n\n\ndef _spot(statement: str, data_dirs: tuple, output_dir: str):\n    """Spot from the statement, else a spot key in input JSON, else in output JSON; None if absent or ambiguous."""\n    vals = {float(v) for v in S0_TEXT.findall(statement or "")}\n    if len(vals) == 1:\n        return vals.pop()\n    if len(vals) > 1:\n        return None\n    for root in tuple(data_dirs or ()) + (output_dir,):\n        found = set()\n        for f in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):\n            try:\n                d = json.load(open(f))\n            except Exception:\n                continue\n            if isinstance(d, dict):\n                for k, v in d.items():\n                    if str(k).lower() in S0_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:\n                        found.add(float(v))\n        if len(found) == 1:\n            return found.pop()\n        if len(found) > 1:\n            return None\n    return None\n\n\ndef _surface_checks(output_dir: str, statement: str, data_dirs: tuple) -> list:\n    """Local/implied ratio at the strike nearest spot on matrix-format surfaces, interior maturities."""\n    out = []\n    csvs = glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True)\n    lvs = [f for f in csvs if "local" in os.path.basename(f).lower()]\n    ivs = [f for f in csvs if "local" not in os.path.basename(f).lower()\n           and re.search(r"(^|[^a-z])(iv|implied)", os.path.basename(f).lower())]\n    if not (lvs and ivs):\n        return out\n    s0 = _spot(statement, data_dirs, output_dir)\n    if s0 is None:\n        return out\n    for lf in sorted(lvs):\n        lv = _matrix(lf)\n        if lv is None:\n            continue\n        for vf in sorted(ivs):\n            iv = _matrix(vf)\n            if iv is None:\n                continue\n            cols = [c for c in lv.columns if any(abs(c - d) < 1e-6 for d in iv.columns)]\n            if len(cols) < 3:\n                continue\n            k = min(lv.index, key=lambda x: abs(x - s0))\n            ki = min(iv.index, key=lambda x: abs(x - k))\n            if abs(ki - k) > 1e-6 * max(1.0, abs(k)):\n                continue\n            ivrow = iv.loc[ki]\n            ivv = np.array([ivrow[min(iv.columns, key=lambda d: abs(d - c))] for c in cols], dtype=float)\n            lvv = lv.loc[k, cols].to_numpy(dtype=float)\n            ratio = (lvv / ivv)[1:-1]\n            ts = cols[1:-1]\n            bad = ~np.isfinite(ratio) | (ratio < R_LO) | (ratio > R_HI)\n            if np.isfinite(ratio).any() and not bad.any():\n                continue\n            fin = ratio[np.isfinite(ratio)]\n            rng = f"{_g(fin.min())}–{_g(fin.max())}" if len(fin) else "all NaN"\n            j = int(np.flatnonzero(bad)[0])\n            out.append(f"{os.path.basename(lf)} vs {os.path.basename(vf)}: at the strike nearest spot (K={_g(k)}, spot "\n                       f"{_g(s0)}) local/implied volatility over interior maturities is {rng}, outside [{R_LO}, {R_HI}] "\n                       f"(e.g. T={_g(ts[j])}: local {_g(lvv[1:-1][j])}, implied {_g(ivv[1:-1][j])}). Near the money they "\n                       f"are of the same size; a ratio this far off usually means a finite-difference denominator or "\n                       f"derivative is scaled wrongly. {TAIL}")\n    return out\n\n\ndef local_vol_identity_notes(output_dir: str, statement: str, data_dirs: tuple) -> list:\n    """Messages for local-vol identity violations in the run\'s written files; never raises."""\n    notes = []\n    try:\n        for f in sorted(glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True)):\n            try:\n                notes += _row_checks(f, pd.read_csv(f))\n            except Exception:\n                continue\n        try:\n            notes += _surface_checks(output_dir, statement, data_dirs)\n        except Exception:\n            pass\n    except Exception:\n        return []\n    return list(dict.fromkeys(notes))\n', 'rootcause/swap_npv_sign.py': 'import glob\nimport json\nimport math\nimport os\nimport re\n\nTAIL = "If the task defines it differently, keep it and say why."\nPAY = re.compile(r"^(pay[_ -]?fixed|payer|pay)$", re.I)\nREC = re.compile(r"^(receive[_ -]?fixed|receiver|receive|rec[_ -]?fixed)$", re.I)\nDIR_KEYS = ("pay_receive", "direction", "side", "position", "payer_receiver", "swap_type", "pay_or_receive")\nNPV_KEYS = ("npv", "net_present_value", "swap_npv", "value", "mtm")\nREL_TOL = 1e-6\n\n\ndef _num(v) -> bool:\n    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)\n\n\ndef _objects(value, prefix=""):\n    """(path, dict) for every JSON object."""\n    if isinstance(value, dict):\n        yield prefix, value\n        for k, v in value.items():\n            yield from _objects(v, f"{prefix}.{k}" if prefix else str(k))\n    elif isinstance(value, list):\n        for i, v in enumerate(value):\n            yield from _objects(v, f"{prefix}[{i}]")\n\n\ndef _direction(obj: dict):\n    """\'pay\' or \'receive\' from a direction field of a dict, else None."""\n    for k, v in obj.items():\n        if str(k).lower() in DIR_KEYS and isinstance(v, str):\n            if PAY.match(v.strip()):\n                return "pay"\n            if REC.match(v.strip()):\n                return "receive"\n    return None\n\n\ndef _input_direction(data_dirs: tuple):\n    """Single direction stated in input JSON files, else None."""\n    found = set()\n    for root in data_dirs or ():\n        for f in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):\n            try:\n                d = json.load(open(f))\n            except Exception:\n                continue\n            for _, o in _objects(d):\n                s = _direction(o)\n                if s:\n                    found.add(s)\n    return found.pop() if len(found) == 1 else None\n\n\ndef _legs(obj: dict):\n    """(npv key, fixed-leg key, float-leg key) in one dict, or None."""\n    keys = {str(k).lower(): k for k in obj if _num(obj[k])}\n    npv = next((keys[k] for k in NPV_KEYS if k in keys), None)\n    fix = [keys[k] for k in keys if "fixed" in k and ("pv" in k or "leg" in k) and "rate" not in k]\n    flt = [keys[k] for k in keys if ("float" in k or "floating" in k) and ("pv" in k or "leg" in k) and "rate" not in k]\n    if npv is None or len(fix) != 1 or len(flt) != 1:\n        return None\n    return npv, fix[0], flt[0]\n\n\ndef swap_npv_sign_notes(output_dir: str, statement: str, data_dirs: tuple) -> list:\n    """Messages when a written swap NPV disagrees with its own leg PVs for the stated direction; never raises."""\n    notes = []\n    try:\n        fallback = _input_direction(data_dirs)\n        for f in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):\n            try:\n                d = json.load(open(f))\n            except Exception:\n                continue\n            for path, o in _objects(d):\n                legs = _legs(o)\n                if not legs:\n                    continue\n                side = _direction(o) or fallback\n                if side is None:\n                    continue\n                nk, xk, lk = legs\n                npv, fx, fl = float(o[nk]), float(o[xk]), float(o[lk])\n                if fx < 0 or fl < 0:\n                    continue\n                want = fl - fx if side == "pay" else fx - fl\n                tol = REL_TOL * max(abs(fx), abs(fl), 1.0)\n                if abs(npv - want) <= tol:\n                    continue\n                where = f"{os.path.basename(f)}" + (f" ({path})" if path else "")\n                rule = f"{lk} − {xk}" if side == "pay" else f"{xk} − {lk}"\n                role = "pays fixed" if side == "pay" else "receives fixed"\n                if abs(npv + want) <= tol:\n                    gap = "it equals the opposite difference"\n                else:\n                    gap = f"the difference of the written legs is {want:.6g}"\n                notes.append(f"{where}: {nk}={npv:.6g} with {xk}={fx:.6g} and {lk}={fl:.6g}; {gap}. For a position that "\n                             f"{role}, the value is {rule}. {TAIL}")\n    except Exception:\n        return []\n    return list(dict.fromkeys(notes))\n', 'rootcause/numeric_enum.py': 'import csv\nimport glob\nimport json\nimport math\nimport os\nimport re\n\nTAIL = "If the task defines it differently, keep it and say why."\nNUM = r"-?\\d+(?:\\.\\d+)?"\nNUM_LIST = re.compile(rf"^\\s*{NUM}(?:\\s*(?:,\\s+|,?\\s+or\\s+|,?\\s+and\\s+)\\s*{NUM})+\\s*\\.?\\s*$")\nTABLE_ROW = re.compile(r"^\\s*\\|\\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\\s*\\|(?:[^|\\n]*\\|)*?([^|\\n]*)\\|\\s*$", re.M)\nSET_FORM = re.compile(rf"`([A-Za-z_][A-Za-z0-9_]*)(?:`\\s*)?\\s*(?:∈|is one of|:\\s*one of|one of)\\s*[{{\\[]?\\s*({NUM}(?:\\s*(?:,\\s*|,?\\s+or\\s+)\\s*{NUM})+)\\s*[}}\\]]?")\nDEC_EXC = re.compile(r"decimal[^()]{0,80}?\\((\\d+)\\s+(?:decimals?\\s+)?for\\s+([^)]+)\\)", re.I | re.S)\nDEC_FIELD = re.compile(r"^\\s*[-*]\\s*`([A-Za-z_][A-Za-z0-9_]*)`\\s*:[^\\n]*?\\((\\d+)\\s+decimals?\\)", re.M)\nFILE_REF = re.compile(r"`([\\w\\-./]+\\.(?:csv|json))`")\n\n\ndef _nums(text: str) -> list:\n    return [float(x) for x in re.findall(NUM, text)]\n\n\ndef _scope(statement: str, pos: int):\n    """Nearest output filename named in a heading or line before pos, else None."""\n    head = statement[:pos]\n    m = None\n    for m in re.finditer(r"^#{1,6}[^\\n]*`([\\w\\-./]+\\.(?:csv|json))`[^\\n]*$", head, re.M):\n        pass\n    return os.path.basename(m.group(1)) if m else None\n\n\ndef _enums(statement: str) -> dict:\n    """{(name, scope file or None): set of allowed values}."""\n    out = {}\n    for m in TABLE_ROW.finditer(statement):\n        cell = m.group(2)\n        if NUM_LIST.match(cell):\n            out.setdefault((m.group(1), _scope(statement, m.start())), set()).update(_nums(cell))\n    for m in SET_FORM.finditer(statement):\n        out.setdefault((m.group(1), _scope(statement, m.start())), set()).update(_nums(m.group(2)))\n    return {k: v for k, v in out.items() if len(v) >= 2}\n\n\ndef _decimals(statement: str) -> dict:\n    """{(column, scope file or None): stated decimals} for per-column exceptions."""\n    out = {}\n    for m in DEC_EXC.finditer(statement):\n        n = int(m.group(1))\n        for name in re.split(r"\\s*(?:/|,|\\band\\b)\\s*", m.group(2)):\n            name = name.strip().strip("`").strip()\n            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):\n                out[(name, _scope(statement, m.start()))] = n\n    for m in DEC_FIELD.finditer(statement):\n        out.setdefault((m.group(1), _scope(statement, m.start())), int(m.group(2)))\n    return out\n\n\ndef _csv_columns(path: str) -> dict:\n    """{column: [raw cell strings]} of a CSV file."""\n    with open(path, newline="", errors="ignore") as fh:\n        rows = list(csv.reader(fh))\n    if not rows:\n        return {}\n    head = rows[0]\n    return {h.strip(): [r[i].strip() for r in rows[1:] if i < len(r)] for i, h in enumerate(head)}\n\n\ndef _json_values(value, key: str):\n    """All numeric leaves stored under key anywhere in a JSON value."""\n    if isinstance(value, dict):\n        for k, v in value.items():\n            if k == key and isinstance(v, (int, float)) and not isinstance(v, bool):\n                yield float(v)\n            elif k == key and isinstance(v, list):\n                for x in v:\n                    if isinstance(x, (int, float)) and not isinstance(x, bool):\n                        yield float(x)\n            yield from _json_values(v, key)\n    elif isinstance(value, list):\n        for v in value:\n            yield from _json_values(v, key)\n\n\ndef _to_float(s: str):\n    try:\n        x = float(s)\n        return x if math.isfinite(x) else None\n    except Exception:\n        return None\n\n\ndef _fmt_set(vals) -> str:\n    return ", ".join(f"{v:g}" for v in sorted(vals))\n\n\ndef numeric_enum_notes(output_dir: str, statement: str) -> list:\n    """Messages when written values leave a stated numeric value list or lose stated per-column decimals; never raises."""\n    notes = []\n    try:\n        enums = _enums(statement or "")\n        decs = _decimals(statement or "")\n        if not (enums or decs):\n            return []\n        files = sorted(glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True)\n                       + glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True))\n        for f in files:\n            base = os.path.basename(f)\n            try:\n                if f.endswith(".csv"):\n                    cols = _csv_columns(f)\n                    raw = cols\n                    getv = lambda k: [x for x in (_to_float(s) for s in raw.get(k, [])) if x is not None]\n                else:\n                    d = json.load(open(f))\n                    raw = {}\n                    getv = lambda k, d=d: list(_json_values(d, k))\n            except Exception:\n                continue\n            for (name, scope), allowed in sorted(enums.items(), key=lambda x: (x[0][0], x[0][1] or "")):\n                if scope and scope != base and any(os.path.basename(g) == scope for g in files):\n                    continue\n                vals = getv(name)\n                if not vals:\n                    continue\n                bad = sorted({v for v in vals if not any(abs(v - a) <= 1e-12 * max(1.0, abs(a)) for a in allowed)})\n                if bad:\n                    shown = list(dict.fromkeys(s for s in raw.get(name, []) if _to_float(s) in bad))[:3] or [f"{v:g}" for v in bad[:3]]\n                    notes.append(f"{base}: column `{name}` contains {\', \'.join(shown)}, but the task lists its values as "\n                                 f"{_fmt_set(allowed)}. Write these values exactly as listed; a float format or rounding "\n                                 f"applied to the whole table can alter them. {TAIL}")\n            if not raw:\n                continue\n            for (name, scope), n in sorted(decs.items(), key=lambda x: (x[0][0], x[0][1] or "")):\n                if scope and scope != base:\n                    continue\n                cells = [s for s in raw.get(name, []) if _to_float(s) is not None and "e" not in s.lower()]\n                if len(cells) < 3:\n                    continue\n                places = [len(s.split(".")[1]) if "." in s else 0 for s in cells]\n                if max(places) < n:\n                    notes.append(f"{base}: every value of `{name}` is written with at most {max(places)} decimals (e.g. "\n                                 f"{\', \'.join(list(dict.fromkeys(cells))[:3])}), but the task asks for {n} decimals in this "\n                                 f"column. Rounding or one float format for all columns drops these digits. {TAIL}")\n    except Exception:\n        return []\n    return list(dict.fromkeys(notes))\n', 'stable/grid_scalar.py': '"""Output check: a written (S, t) value grid read at its own (S0, t=0) cell must agree with the scalar value the run reports."""\nimport csv\nimport json\nimport math\nimport os\nimport re\n\n_S_ROWS = re.compile(r"^(s|s_?t|s_?i|spot|stock|stock_?price|underlying|asset_?price|s\\s*[/\\\\]\\s*t)$", re.I)\n_T_ROWS = re.compile(r"^(t|time|t_?n|t\\s*[/\\\\]\\s*s|time\\s*[/\\\\]\\s*s)$", re.I)\n_TAU_ROWS = re.compile(r"^(tau|ttm|time_?to_?maturity)$", re.I)\n_S0_TOKEN = re.compile(r"(?<![A-Za-z0-9])S_?\\{?0\\}?(?![A-Za-z0-9])|initial (?:stock|underlying|asset) price|"\n                       r"(?:current|spot) (?:stock |underlying |asset )?price|spot level", re.I)\n_NUM = re.compile(r"(?<![A-Za-z_\\d.])(\\d+(?:\\.\\d+)?)(?![\\d.]*[A-Za-z_])")\n_CONTAINER = {"grid", "surface", "values", "value", "matrix", "table", "sampled", "sample", "v", "csv"}\n_KEY_EXTRA = {"price", "value", "v", "fine"}\n_REL_TOL = 1e-3\n\n\ndef _floats(xs):\n    try:\n        out = [float(x) for x in xs]\n        return out if all(math.isfinite(v) for v in out) else None\n    except (TypeError, ValueError):\n        return None\n\n\ndef _read_grid(path):\n    with open(path, newline="", errors="ignore") as f:\n        rows = [r for r in csv.reader(f) if r]\n    if len(rows) < 4 or len(rows[0]) < 4:\n        return None\n    hdr = rows[0]\n    cols = _floats(hdr[1:])\n    if cols is None:\n        return None\n    body = [r for r in rows[1:] if len(r) == len(hdr)]\n    if len(body) < 3 or len(body) != len(rows) - 1:\n        return None\n    rlab = _floats([r[0] for r in body])\n    vals = [_floats(r[1:]) for r in body]\n    if rlab is None or any(v is None for v in vals):\n        return None\n    return hdr[0].strip(), rlab, cols, hdr[1:], vals, [r[0] for r in body]\n\n\ndef _json_leaves(obj, path=()):\n    if isinstance(obj, dict):\n        for k, v in obj.items():\n            yield from _json_leaves(v, path + (str(k),))\n    elif isinstance(obj, (int, float)) and not isinstance(obj, bool) and math.isfinite(obj):\n        yield path, float(obj)\n\n\ndef _tokens(s):\n    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]\n\n\ndef _s0_candidates(statement, data_dirs, out_jsons):\n    cands = []\n    for ln in (statement or "").splitlines():\n        for m in _S0_TOKEN.finditer(ln):\n            rest = ln[m.end():]\n            n = _NUM.search(rest)\n            if n and len(rest[:n.start()]) <= 40:\n                cands.append(float(n.group(1)))\n                break\n    for root in list(data_dirs or ()) + [None]:\n        files = out_jsons if root is None else _list_files(root, ".json")\n        for fp in files:\n            try:\n                obj = json.load(open(fp))\n            except Exception:\n                continue\n            for path, v in _json_leaves(obj):\n                if path and re.fullmatch(r"s_?0|spot|spot_?price|initial_?(stock_?)?price|s_?init", path[-1], re.I):\n                    cands.append(v)\n    seen, out = set(), []\n    for c in cands:\n        if c > 0 and c not in seen:\n            seen.add(c)\n            out.append(c)\n    return out\n\n\ndef _list_files(root, ext):\n    out = []\n    try:\n        for dp, dn, fn in os.walk(root):\n            dn.sort()\n            for n in sorted(fn):\n                if n.lower().endswith(ext):\n                    out.append(os.path.join(dp, n))\n            if len(out) > 200:\n                break\n    except Exception:\n        pass\n    return out\n\n\ndef _value_at(labels, column, x):\n    pairs = sorted(zip(labels, column))\n    for i, (lab, v) in enumerate(pairs):\n        if abs(lab - x) <= 1e-9 * max(1.0, abs(x)):\n            return v, None, 0.0\n    for i in range(len(pairs) - 1):\n        (a, va), (b, vb) = pairs[i], pairs[i + 1]\n        if a < x < b:\n            w = (x - a) / (b - a)\n            v = va + w * (vb - va)\n            curv = 0.0\n            if 0 < i and i + 2 < len(pairs):\n                curv = max(abs(pairs[i - 1][1] - 2 * va + vb), abs(va - 2 * vb + pairs[i + 2][1]))\n            return v, (a, b), curv / 8.0\n    return None\n\n\ndef _fmt(v):\n    return f"{v:.6g}"\n\n\ndef _check_grid(path, grid, scalars, s0s):\n    name, rlab, cols, ctexts, vals, rtexts = grid\n    if _S_ROWS.match(name):\n        tcol = [j for j, c in enumerate(cols) if abs(c) < 1e-12]\n        if not tcol:\n            return None\n        j = tcol[0]\n        s_labels, line, s_axis, t_text = rlab, [r[j] for r in vals], "row", ctexts[j].strip()\n    elif _T_ROWS.match(name) or _TAU_ROWS.match(name):\n        target = max(rlab) if _TAU_ROWS.match(name) else 0.0\n        trow = [i for i, t in enumerate(rlab) if abs(t - target) < 1e-12]\n        if not trow:\n            return None\n        i = trow[0]\n        s_labels, line, s_axis, t_text = cols, vals[i], "column", rtexts[i].strip()\n    else:\n        return None\n    readings = []\n    for s0 in s0s:\n        r = _value_at(s_labels, line, s0)\n        if r is not None:\n            readings.append((s0,) + r)\n    if not readings:\n        return None\n    for s0, g, nb, slack in readings:\n        for _, _, p in scalars:\n            if abs(g - p) <= _REL_TOL * abs(p) + slack + 1e-12:\n                return None\n    s0, g, nb, slack = readings[0]\n    jf, key, p = scalars[0]\n    t_axis = "column" if s_axis == "row" else "row"\n    t_name = "tau" if _TAU_ROWS.match(name) else "t"\n    if nb is None:\n        where = f"at {s_axis} S={_fmt(s0)}, {t_axis} {t_name}={t_text} holds {_fmt(g)}"\n    else:\n        where = (f"interpolated to S={_fmt(s0)} between {s_axis}s S={_fmt(nb[0])} and S={_fmt(nb[1])}, "\n                 f"{t_axis} {t_name}={t_text}, gives {_fmt(g)}")\n    return (f"`{os.path.basename(path)}` {where}, but `{os.path.basename(jf)}` reports {key} = {_fmt(p)} "\n            f"for the same contract. Check whether the array written to the grid is shaped (time, stock) "\n            f"rather than (stock, time), i.e. whether its row and column labels are swapped; print the "\n            f"array\'s shape and one known cell (e.g. the value at S0 and t=0) before writing it.")\n\n\ndef grid_scalar_notes(output_dir: str, statement: str, data_dirs: tuple) -> list:\n    """Return messages for value grids whose own (S0, t=0) reading disagrees with the reported scalar."""\n    try:\n        jsons = _list_files(output_dir, ".json")\n        leaves = []\n        for fp in jsons:\n            try:\n                obj = json.load(open(fp))\n            except Exception:\n                continue\n            for path, v in _json_leaves(obj):\n                if path:\n                    leaves.append((fp, ".".join(path), v))\n        if not leaves:\n            return []\n        s0s = None\n        out, seen = [], set()\n        for path in _list_files(output_dir, ".csv"):\n            try:\n                stem = set(_tokens(os.path.splitext(os.path.basename(path))[0])) - _CONTAINER\n                if not stem:\n                    continue\n                scalars = [(fp, k, v) for fp, k, v in leaves\n                           if stem <= set(_tokens(k)) and set(_tokens(k)) - stem <= _KEY_EXTRA]\n                if not scalars:\n                    continue\n                grid = _read_grid(path)\n                if grid is None:\n                    continue\n                if s0s is None:\n                    s0s = _s0_candidates(statement, data_dirs, jsons)\n                if not s0s:\n                    return out\n                msg = _check_grid(path, grid, scalars, s0s)\n                if msg and msg not in seen:\n                    seen.add(msg)\n                    out.append(msg)\n            except Exception:\n                continue\n        return out\n    except Exception:\n        return []\n', 'stable/date_int.py': '"""Output check: a date column written as 8-digit YYYYMMDD integers while the statement asks for ISO dates."""\nimport csv\nimport json\nimport os\nimport re\n\n_ISO_ASK = re.compile(r"YYYY-MM-DD|%Y-%m-%d|\\bISO(?:[ -]?8601)?\\b(?![ -]?(?:4217|3166|639))", re.I)\n_KEY = re.compile(r"date|day$|^dt$", re.I)\n_YMD = re.compile(r"^(19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])(\\.0+)?$")\n_JSON_PAIR = re.compile(r\'"(\\w*date\\w*)"\\s*:\\s*"?(\\d{8}(?:\\.0+)?)"?\', re.I)\n_MAX_ROWS = 50\n\n\ndef _file_wants_ymd(statement, fname):\n    for m in re.finditer(re.escape(fname), statement):\n        seg = statement[m.start(): m.start() + 600]\n        seg = re.split(r"\\n\\s*\\n|\\n#", seg, maxsplit=1)[0]\n        if re.search(r"YYYYMMDD|%Y%m%d", seg) and not _ISO_ASK.search(seg):\n            return True\n    return False\n\n\ndef _csv_hit(path):\n    with open(path, newline="", errors="ignore") as f:\n        rd = csv.DictReader(f)\n        rows = []\n        for r in rd:\n            rows.append(r)\n            if len(rows) >= _MAX_ROWS:\n                break\n    if not rows:\n        return None\n    for k in rows[0].keys():\n        if not k or not _KEY.search(k.strip()):\n            continue\n        vals = [(r.get(k) or "").strip() for r in rows]\n        vals = [v for v in vals if v]\n        if vals and all(_YMD.match(v) for v in vals):\n            return k, vals[0]\n    return None\n\n\ndef _json_hit(path):\n    with open(path, errors="ignore") as f:\n        text = f.read()\n    for k, v in _JSON_PAIR.findall(text):\n        if _YMD.match(v):\n            return k, v\n    return None\n\n\ndef date_int_notes(output_dir: str, statement: str) -> list:\n    """Return messages for output date fields written as YYYYMMDD integers when ISO dates are asked for."""\n    try:\n        statement = statement or ""\n        if not _ISO_ASK.search(statement):\n            return []\n        files = []\n        for dp, dn, fn in os.walk(output_dir):\n            dn.sort()\n            files += [os.path.join(dp, n) for n in sorted(fn)]\n        out, seen = [], set()\n        for fp in files:\n            try:\n                name = os.path.basename(fp)\n                low = name.lower()\n                if low.endswith(".csv"):\n                    hit, kind = _csv_hit(fp), "column"\n                elif low.endswith(".json"):\n                    hit, kind = _json_hit(fp), "field"\n                else:\n                    continue\n                if not hit or _file_wants_ymd(statement, name):\n                    continue\n                k, v = hit\n                msg = (f"`{name}` {kind} `{k}` holds `{v}` (an 8-digit integer, likely copied from the raw "\n                       f"file). The task asks for dates in ISO form (`YYYY-MM-DD`); convert with "\n                       f"`pd.to_datetime(..., format=\'%Y%m%d\').dt.strftime(\'%Y-%m-%d\')` before writing.")\n                if msg not in seen:\n                    seen.add(msg)\n                    out.append(msg)\n            except Exception:\n                continue\n        return out\n    except Exception:\n        return []\n', 'one_item/entity_decor.py': 'import csv\nimport glob\nimport json\nimport os\nimport re\n\nENTITY_KEY = re.compile(r"(_|^)(manager|pair|ticker|cusip|fund|label|security|symbol|asset|issuer)$")\nNUMERIC = re.compile(r"[\\d.\\-eE+]+")\nWORD_CHAR = re.compile(r"[A-Za-z0-9]")\nMAX_TABLE_BYTES = 50_000_000\nTAIL = "If the task defines it differently, keep it and say why."\n\n\ndef table_files(output_dir: str, data_dirs: tuple) -> list:\n    files = []\n    for root in (output_dir,) + tuple(data_dirs or ()):\n        found = []\n        for ext in ("csv", "tsv"):\n            found += glob.glob(os.path.join(root, "**", "*." + ext), recursive=True)\n        files += sorted(found)\n    return files\n\n\ndef table_cells(output_dir: str, data_dirs: tuple) -> dict:\n    cells = {}\n    for f in table_files(output_dir, data_dirs):\n        try:\n            if os.path.getsize(f) > MAX_TABLE_BYTES:\n                continue\n            with open(f, newline="", errors="replace") as fh:\n                for row in csv.reader(fh, delimiter="\\t" if f.endswith(".tsv") else ","):\n                    for c in row:\n                        c = c.strip()\n                        if len(c) >= 3 and not NUMERIC.fullmatch(c):\n                            cells.setdefault(c, os.path.basename(f))\n        except (OSError, csv.Error):\n            continue\n    return cells\n\n\ndef contained_cell(value: str, cells: dict):\n    v = value.strip()\n    if not v or v in cells:\n        return None\n    starts = [i for i in range(len(v)) if i == 0 or not WORD_CHAR.match(v[i - 1])]\n    ends = [j for j in range(1, len(v) + 1) if j == len(v) or not WORD_CHAR.match(v[j])]\n    best = None\n    for i in starts:\n        for j in ends:\n            if j - i < 3 or j - i >= len(v):\n                continue\n            if v[i:j] in cells and (best is None or j - i > len(best)):\n                best = v[i:j]\n    return best\n\n\ndef walk(v, path=""):\n    if isinstance(v, dict):\n        for k, x in v.items():\n            p = path + "/" + str(k)\n            yield p, str(k), x\n            yield from walk(x, p)\n    elif isinstance(v, list):\n        for x in v:\n            yield from walk(x, path)\n\n\ndef entity_decor_notes(output_dir: str, statement: str, data_dirs: tuple) -> list[str]:\n    """One message per entity-named JSON field whose string value wraps a table cell value in extra text."""\n    out = []\n    try:\n        json_files = sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True))\n        if not json_files:\n            return out\n        cells = None\n        for f in json_files:\n            try:\n                with open(f) as fh:\n                    data = json.load(fh)\n            except (OSError, ValueError):\n                continue\n            rel = os.path.relpath(f, output_dir)\n            for path, key, x in walk(data):\n                if not ENTITY_KEY.search(key.lower()):\n                    continue\n                items = x if isinstance(x, list) else [x]\n                if not items or not all(isinstance(i, str) for i in items):\n                    continue\n                if cells is None:\n                    cells = table_cells(output_dir, data_dirs)\n                hits = [(i, contained_cell(i, cells)) for i in items]\n                hits = [(i, c) for i, c in hits if c is not None]\n                if not hits:\n                    continue\n                sources = ", ".join(sorted({cells[c] for _, c in hits}))\n                where = "it contains" if not isinstance(x, list) else "the item(s) " + ", ".join(repr(i) for i, _ in hits) + " contain"\n                out.append(\n                    f"{rel}: field `{path.lstrip(\'/\')}` is {x!r}; {where} a cell value from {sources} with extra characters "\n                    f"added around it. A field that names an entity usually holds the plain value exactly as it appears in "\n                    f"the table. {TAIL}"\n                )\n    except Exception:\n        return out\n    return out\n', 'one_item/plural_count.py': 'import glob\nimport json\nimport os\nimport re\n\nCOUNTISH = re.compile(\n    r"(^|_)(shares|dollars|contracts|units|n|num|number|count|counts|total|size|len|days|years|months|weeks|periods|obs|"\n    r"observations|bps|steps|paths|trials|sims|simulations|iterations|rows|samples|bins|lags|dof|df)($|_)"\n)\nNOT_PLURAL = {"bps", "pass", "status", "basis", "analysis", "yes", "gross", "loss", "is", "was", "has", "this", "its"}\nCOUNT_WORDS = re.compile(r"\\bint\\b|<int>|integer|count|number of")\nTAIL = "If the task defines it differently, keep it and say why."\n\n\ndef plural_bare(key: str) -> bool:\n    k = key.lower()\n    last = k.split("_")[-1]\n    if not re.fullmatch(r"[a-z]+s", last) or last.endswith("ss") or len(last) < 4:\n        return False\n    return not COUNTISH.search(k) and last not in NOT_PLURAL\n\n\ndef walk(v, path=""):\n    if isinstance(v, dict):\n        for k, x in v.items():\n            p = path + "/" + str(k)\n            yield p, str(k), x\n            yield from walk(x, p)\n\n\ndef statement_lines(statement: str, key: str) -> list:\n    rx = re.compile(r"[`\\"]" + re.escape(key) + r"[`\\"]")\n    return [ln for ln in statement.splitlines() if rx.search(ln)]\n\n\ndef plural_count_notes(output_dir: str, statement: str) -> list[str]:\n    """One message per plural-named key quoted in the statement (never typed as a count there) but written as an integer."""\n    out = []\n    try:\n        statement = statement or ""\n        for f in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):\n            try:\n                with open(f) as fh:\n                    data = json.load(fh)\n            except (OSError, ValueError):\n                continue\n            rel = os.path.relpath(f, output_dir)\n            for path, key, x in walk(data):\n                if isinstance(x, bool) or not isinstance(x, int) or not plural_bare(key):\n                    continue\n                lines = statement_lines(statement, key)\n                if not lines or any(COUNT_WORDS.search(ln.lower()) for ln in lines):\n                    continue\n                out.append(\n                    f"{rel}: field `{path.lstrip(\'/\')}` is the integer {x}. The task names `{key}` in plural form, which "\n                    f"usually asks for the items themselves (for example a list), not how many there are. {TAIL}"\n                )\n    except Exception:\n        return out\n    return out\n', 'oc7mid/total_sum.py': 'import glob\nimport json\nimport math\nimport os\nimport re\n\nTOTAL_KEY = re.compile(r"total_(\\w+?)(?:_effect)?$")\n\n\ndef is_num(x) -> bool:\n    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)\n\n\ndef part_values(v):\n    vals = list(v.values()) if isinstance(v, dict) else v if isinstance(v, list) else None\n    if not vals or not all(is_num(x) for x in vals):\n        return None\n    return vals\n\n\ndef fmt(x: float) -> str:\n    return f"{x:.6g}"\n\n\ndef total_sum_notes(output_dir: str, statement: str, data_dirs: tuple) -> list[str]:\n    """One message per top-level total_<stem> whose value differs from the sum of same-file parts keyed with <stem>."""\n    out = []\n    try:\n        for f in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):\n            try:\n                with open(f) as fh:\n                    data = json.load(fh)\n            except (OSError, ValueError):\n                continue\n            if not isinstance(data, dict):\n                continue\n            rel = os.path.relpath(f, output_dir)\n            for k, v in data.items():\n                m = TOTAL_KEY.match(k) if isinstance(k, str) else None\n                if not m or not is_num(v):\n                    continue\n                stem = m.group(1)\n                diffs = []\n                for k2, v2 in data.items():\n                    if k2 == k or not isinstance(k2, str) or stem not in k2:\n                        continue\n                    vals = part_values(v2)\n                    if vals is None:\n                        continue\n                    s = math.fsum(vals)\n                    if abs(s - v) > 1e-6 * max(1.0, abs(v), abs(s)) and abs(s - v) > 1e-9:\n                        diffs.append(f"the {len(vals)} values in `{k2}` sum to {fmt(s)}")\n                if diffs:\n                    out.append(f"Output check: {rel}: `{k}` = {fmt(v)}, but " + "; ".join(diffs) + ". "\n                               "If the task defines this total as the sum of these contributions, both must be the same number. "\n                               "Find which component is left out of one of them (or counted only in one), add it in one place, "\n                               "and derive the per-period, per-group and total figures from that same array; "\n                               "if the total is not meant to equal this sum, say why.")\n    except Exception:\n        return out\n    return out\n', 'oc9/oc9_checks.py': '"""oc9 checks: K1 dates coerced to NaT that another format parses, M1 a mean field equal to its median field, F1 a field\nthe statement names for reporting that no output holds, D1 a derived column that breaks its identity, S1 a membership\nflag true on more rows than the top-N list it names."""\nimport csv\nimport glob\nimport json\nimport math\nimport os\nimport re\n\ncsv.field_size_limit(10**9)\n\n\nNAT_PRELOAD = r\'\'\'\nimport pandas as _k1_pd\n_K1_LOG = []\n_k1_orig = _k1_pd.to_datetime\ndef _k1_to_datetime(arg, *a, **k):\n    res = _k1_orig(arg, *a, **k)\n    if k.get("errors") == "coerce" and k.get("format") != "mixed":\n        try:\n            s = _k1_pd.Series(arg).astype("string")\n            r = _k1_pd.Series(_k1_pd.DatetimeIndex(res) if not isinstance(res, _k1_pd.Series) else res.values)\n            lost = s[r.isna().values & s.notna().values & (s.str.strip().fillna("").str.len() > 0).values]\n            lost = lost[~lost.str.strip().str.lower().isin(["nat", "nan", "none", "null", "na"])]\n            if len(lost):\n                ok = _k1_orig(lost, errors="coerce", format="mixed").notna()\n                if ok.any():\n                    _K1_LOG.append({"lost": int(len(lost)), "mixed_ok": int(ok.sum()),\n                                    "samples": list(dict.fromkeys(lost[ok.values].tolist()))[:3],\n                                    "format": k.get("format")})\n        except Exception:\n            pass\n    return res\n_k1_pd.to_datetime = _k1_to_datetime\n\'\'\'\nNAT_READ = \'import json as _k1j; print("K1LOG", _k1j.dumps(_K1_LOG)); _K1_LOG.clear()\'\n\n\ndef nat_note(entry: dict) -> str:\n    """The message for one logged coerce call."""\n    fmt = f" with format={entry[\'format\']!r}" if entry.get("format") else ""\n    return (f"Code note: pd.to_datetime(..., errors=\'coerce\'){fmt} in this cell turned {entry[\'lost\']} non-empty date "\n            f"strings into NaT, and {entry[\'mixed_ok\']} of them are valid dates in another layout, for example "\n            f"{\', \'.join(repr(x) for x in entry[\'samples\'])}. Rows dropped for NaT later would be valid rows. Parse the "\n            "column with format=\'mixed\' (or the explicit format of each layout) and keep errors=\'coerce\' only for "\n            "strings that are not dates.")\n\n\ndef nat_log_entries(probe_output: str) -> list[dict]:\n    m = re.search(r"K1LOG (\\[.*\\])", probe_output)\n    try:\n        return json.loads(m.group(1)) if m else []\n    except ValueError:\n        return []\n\n\n_K1_CALL = re.compile(r"to_datetime\\(\\s*(\\w+)\\s*\\[\\s*[\'\\"]([^\'\\"]+)[\'\\"]\\s*\\][^)]*errors\\s*=\\s*[\'\\"]coerce[\'\\"]")\n\n\ndef nat_replay_entries(code: str, data_files: list[str]) -> list[dict]:\n    import pandas as pd\n    out = []\n    for m in _K1_CALL.finditer(code):\n        col = m.group(2).strip()\n        tail = code[m.start(): code.find(")", m.end() - 1) + 1]\n        if re.search(r"format\\s*=\\s*[\'\\"]mixed[\'\\"]", tail):\n            continue\n        fm = re.search(r"format\\s*=\\s*[\'\\"]([^\'\\"]+)[\'\\"]", tail)\n        for f in data_files:\n            try:\n                raw = pd.read_csv(f, dtype=str, nrows=200000)\n            except Exception:\n                continue\n            raw.columns = [c.strip() for c in raw.columns]\n            if col not in raw.columns:\n                continue\n            s = raw[col]\n            r = pd.to_datetime(s, errors="coerce", **({"format": fm.group(1)} if fm else {}))\n            lost = s[r.isna() & s.notna() & (s.fillna("").str.strip().str.len() > 0)]\n            lost = lost[~lost.str.strip().str.lower().isin(["nat", "nan", "none", "null", "na"])]\n            if len(lost):\n                ok = pd.to_datetime(lost, errors="coerce", format="mixed").notna()\n                if ok.any():\n                    out.append({"lost": int(len(lost)), "mixed_ok": int(ok.sum()),\n                                "samples": list(dict.fromkeys(lost[ok].tolist()))[:3],\n                                "format": fm.group(1) if fm else None, "column": col, "file": os.path.basename(f)})\n    return out\n\n\n\ndef _json_leaves(obj, path, out):\n    if isinstance(obj, dict):\n        for k, v in obj.items():\n            _json_leaves(v, path + [str(k)], out)\n    elif isinstance(obj, list):\n        for i, v in enumerate(obj[:2000]):\n            _json_leaves(v, path + [f"[{i}]"], out)\n    else:\n        keys = [p for p in path if not p.startswith("[")]\n        name = keys[-1] if keys else ""\n        if name.lower() in {"value", "val", "estimate"} and len(keys) > 1:\n            name = keys[-2]\n        out.append((".".join(path), name, obj))\n\n\ndef _is_num(v):\n    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)\n\n\ndef _out_files(output_dir, ext):\n    return sorted(glob.glob(os.path.join(output_dir, "**", "*" + ext), recursive=True))\n\n\ndef _csv_rows(path, limit=20000):\n    with open(path, newline="", errors="replace") as f:\n        rd = csv.reader(f)\n        hdr = next(rd, None) or []\n        rows = []\n        for i, r in enumerate(rd):\n            if i >= limit:\n                break\n            rows.append(r)\n    return [h.strip() for h in hdr], rows\n\n\n\n_M1_TOK = re.compile(r"(?:^|_)(mean|median)(?=_|$)")\n\n\ndef mean_median_notes(output_dir: str) -> list[str]:\n    """A mean_X (X_mean) and a median_X (X_median) numeric leaf, in any JSON outputs, that hold the same non-integer value."""\n    by = {}\n    for fp in _out_files(output_dir, ".json"):\n        try:\n            leaves = []\n            _json_leaves(json.load(open(fp)), [], leaves)\n        except Exception:\n            continue\n        rel = os.path.relpath(fp, output_dir)\n        for path, name, v in leaves:\n            if not _is_num(v):\n                continue\n            m = list(_M1_TOK.finditer(name.lower()))\n            if len(m) != 1:\n                continue\n            stem = (name.lower()[:m[0].start()] + "_" + name.lower()[m[0].end():]).strip("_")\n            by.setdefault(stem, {}).setdefault(m[0].group(1), []).append((rel, path, v))\n    out = []\n    for stem, d in by.items():\n        if not stem or "mean" not in d or "median" not in d:\n            continue\n        for fm, pm, vm in d["mean"]:\n            hit = next(((fd, pd_, vd) for fd, pd_, vd in d["median"] if float(vm) == float(vd)\n                        and not float(vm).is_integer()), None)\n            if hit:\n                out.append(f"Output check: {fm} `{pm}` = {vm!r} and {hit[0]} `{hit[1]}` = {hit[2]!r} are exactly equal. A "\n                           "mean and a median of the same sample coincide only for a symmetric sample; equal values to the "\n                           "last digit usually mean one statistic was assigned to both fields. Recompute each from its own "\n                           "formula and write it again.")\n                break\n    return out[:2]\n\n\n\n_F1_TICK = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`")\n_F1_NEAR = re.compile(r"\\breported as\\b|\\breport(?:ed)? (?:it )?(?:in|under|as)\\b|\\bintermediates?\\b|\\b(?:key|field|column)s?\\b", re.I)\n_F1_COND = re.compile(r"\\bif\\b.{0,160}?\\b(?:does not|do not|doesn\'t|not include|absent|missing|unavailable)\\b", re.I)\n_F1_VERB = re.compile(r"\\b(report(?:ed|s)?|intermediates?|output(?:s|ted)?|write|written|include[sd]?|key|field|column)\\b", re.I)\n\n\ndef _input_names(data_dirs):\n    names = set()\n    for d in data_dirs:\n        for fp in glob.glob(os.path.join(d, "**", "*"), recursive=True):\n            names.add(os.path.splitext(os.path.basename(fp))[0].lower())\n            try:\n                if fp.endswith((".csv", ".tsv")):\n                    with open(fp, newline="", errors="replace") as f:\n                        names |= {h.strip().lower() for h in next(csv.reader(f, delimiter="\\t" if fp.endswith(".tsv") else ","), [])}\n                elif fp.endswith((".parquet", ".pqt")):\n                    import pyarrow.parquet as pq\n                    names |= {c.lower() for c in pq.read_schema(fp).names}\n                elif fp.endswith(".json") and os.path.getsize(fp) < 5_000_000:\n                    leaves = []\n                    _json_leaves(json.load(open(fp)), [], leaves)\n                    names |= {p.lower() for path, _, _ in leaves for p in path.split(".")}\n            except Exception:\n                continue\n    return names\n\n\ndef _output_names(output_dir):\n    names, strings = set(), set()\n    for fp in _out_files(output_dir, ".json"):\n        try:\n            leaves = []\n            _json_leaves(json.load(open(fp)), [], leaves)\n        except Exception:\n            continue\n        for path, _, v in leaves:\n            names |= {p.lower() for p in path.split(".")}\n            if isinstance(v, str):\n                strings.add(v.strip().lower())\n    for fp in _out_files(output_dir, ".csv"):\n        try:\n            hdr, rows = _csv_rows(fp, 2000)\n        except Exception:\n            continue\n        names |= {h.lower() for h in hdr}\n        for r in rows:\n            strings |= {c.strip().lower() for c in r[:3]}\n    return names, strings\n\n\ndef named_field_notes(output_dir: str, statement: str, data_dirs: list[str]) -> list[str]:\n    """A backticked snake_case name in a statement sentence about reporting, absent from every output key, header and\n    label, and not an input column, input key or input file name."""\n    if not statement:\n        return []\n    inputs = _input_names(data_dirs)\n    names, strings = _output_names(output_dir)\n    missing = []\n    for sent in re.split(r"(?<=[.!?])\\s+|\\n\\s*\\n|\\n\\s*[-*\\d]+[.)]?\\s", statement):\n        if not _F1_VERB.search(sent) or _F1_COND.search(sent):\n            continue\n        for m in _F1_TICK.finditer(sent):\n            tok = m.group(1)\n            if len(tok) < 5:\n                continue\n            after = sent[m.end(): m.end() + 2]\n            near = sent[max(0, m.start() - 40): m.end() + 40]\n            if not _F1_NEAR.search(near) or "=" in sent[m.end(): m.end() + 4]:\n                continue\n            if after.startswith("(") or tok in inputs or tok in names or tok in strings or tok in missing:\n                continue\n            missing.append(tok)\n    if not missing:\n        return []\n    return [f"Output check: the task names `{t}` as a value to report, but no output file has a key, column or label "\n            f"`{t}`. Find the sentence that defines it, compute it, and add it where that sentence puts it (an "\n            "intermediate, a summary key or a column)." for t in missing[:3]]\n\n\n\n_D1_COL = re.compile(r"^(?P<a>.+?)_(?P<op>minus|plus|over|div|times)_(?P<b>.+)$")\n_D1_SYM = {"minus": "-", "plus": "+", "times": "*", "over": "/", "div": "/"}\n_D1_OPS = {"minus": lambda a, b: a - b, "plus": lambda a, b: a + b, "times": lambda a, b: a * b,\n           "over": lambda a, b: a / b if b != 0 else None, "div": lambda a, b: a / b if b != 0 else None}\n\n\ndef _decimals(s):\n    s = s.strip()\n    if "e" in s.lower():\n        return None\n    return len(s.split(".")[1]) if "." in s else 0\n\n\ndef _stated_decimals(statement):\n    m = re.search(r"\\b(\\d)\\s+decimal(?:\\s+places?)?\\b", statement or "")\n    return int(m.group(1)) if m else None\n\n\ndef _operand_pairs(a, b, idx):\n    pairs = [(a, b)] if a in idx and b in idx else []\n    for h in idx:\n        if h.startswith(a + "_") and b + h[len(a):] in idx:\n            pairs.append((h, b + h[len(a):]))\n    return pairs\n\n\ndef _identity_misses(rows, ia, ib, ic, op):\n    from decimal import Decimal, InvalidOperation\n    checked, bad, first = 0, 0, None\n    for n, r in enumerate(rows):\n        try:\n            sa, sb, sc = r[ia].strip(), r[ib].strip(), r[ic].strip()\n            a, b, c = Decimal(sa), Decimal(sb), Decimal(sc)\n        except (IndexError, InvalidOperation):\n            continue\n        if not all(x.is_finite() for x in (a, b, c)) or (op in ("over", "div") and b == 0):\n            continue\n        want = {"minus": lambda: a - b, "plus": lambda: a + b, "times": lambda: a * b}.get(op, lambda: a / b)()\n        half = Decimal(5) * Decimal(10) ** (c.as_tuple().exponent - 1)\n        noise = Decimal("1e-12") * max(abs(a), abs(b), abs(c), Decimal(1))\n        if op in ("over", "div", "times"):\n            ua = Decimal(5) * Decimal(10) ** (a.as_tuple().exponent - 1)\n            ub = Decimal(5) * Decimal(10) ** (b.as_tuple().exponent - 1)\n            half += abs(want) * (ua / max(abs(a), Decimal("1e-300")) + ub / max(abs(b), Decimal("1e-300")))\n        checked += 1\n        if abs(c - want) > half + noise:\n            bad += 1\n            if first is None:\n                first = (n + 1, sa, sb, sc, want)\n    return checked, bad, first\n\n\ndef derived_identity_notes(output_dir: str, statement: str) -> list[str]:\n    """A CSV column a_<op>_b next to its operand columns (a and b, or a_<s> and b_<s>) that holds the identity on some\n    rows and misses it, on the values as written, by more than half a unit in its last written digit on others."""\n    out = []\n    for fp in _out_files(output_dir, ".csv"):\n        try:\n            hdr, rows = _csv_rows(fp)\n        except Exception:\n            continue\n        idx = {h: i for i, h in enumerate(hdr)}\n        for h in hdr:\n            m = _D1_COL.match(h)\n            if not m:\n                continue\n            op = m.group("op")\n            best = None\n            for ca, cb in _operand_pairs(m.group("a"), m.group("b"), idx):\n                if h in (ca, cb):\n                    continue\n                checked, bad, first = _identity_misses(rows, idx[ca], idx[cb], idx[h], op)\n                if checked and (best is None or bad < best[3]):\n                    best = (ca, cb, checked, bad, first)\n            if not best or best[3] == 0 or best[3] == best[2]:\n                continue\n            ca, cb, checked, bad, (n, sa, sb, sc, want) = best\n            rel = os.path.relpath(fp, output_dir)\n            decs = {_decimals(r[idx[h]]) for r in rows if len(r) > idx[h] and r[idx[h]].strip()}\n            fixed = (f" Every row of `{h}` is written with exactly {next(iter(decs))} decimals, so the file uses fixed-decimal "\n                     "formatting.") if len(decs) == 1 and None not in decs else ""\n            out.append(f"Output check: {rel}: `{h}` differs from `{ca}` {op} `{cb}` on {bad} of {checked} rows "\n                       f"(row {n}: {sc} vs {sa} {op} {sb} = {float(want):.12g}).{fixed} A derived column must equal the "\n                       "identity its name states on the values as written. First choice: write the floats themselves, "\n                       "with no fixed-decimal formatting (no f\\"{x:.Nf}\\", round() or float_format), so pandas writes "\n                       f"full precision and `{h}` as written matches `{ca}` {_D1_SYM[op]} `{cb}` as written up to float rounding. Second choice, "\n                       "if a fixed number of decimals is required: round the operands to those decimals first and compute "\n                       "the derived column from the rounded operands.")\n            if len(out) >= 2:\n                return out\n    return out\n\n\n\n_S1_UNION = re.compile(r"\\bunion of\\b", re.I)\n_S1_TOPN = re.compile(r"\\btop[- ]?(\\d{1,4})\\b", re.I)\n_TRUE, _FALSE = {"true", "1", "1.0", "yes", "y", "t"}, {"false", "0", "0.0", "no", "n", "f", ""}\n\n\ndef set_flag_notes(output_dir: str, statement: str) -> list[str]:\n    """When the statement builds a universe as the union of top-N lists, an in_<list> flag column that is true on more\n    rows than N."""\n    if not statement or not _S1_UNION.search(statement):\n        return []\n    ns = {int(x) for x in _S1_TOPN.findall(statement)}\n    if len(ns) != 1:\n        return []\n    n = ns.pop()\n    out = []\n    for fp in _out_files(output_dir, ".csv"):\n        try:\n            hdr, rows = _csv_rows(fp)\n        except Exception:\n            continue\n        flags = [i for i, h in enumerate(hdr) if h.lower().startswith("in_")]\n        if len(flags) < 2 or len(rows) <= n:\n            continue\n        for i in flags:\n            vals = [r[i].strip().lower() if i < len(r) else "" for r in rows]\n            if not all(v in _TRUE | _FALSE for v in vals):\n                continue\n            k = sum(v in _TRUE for v in vals)\n            if k > n:\n                rel = os.path.relpath(fp, output_dir)\n                out.append(f"Output check: {rel}: `{hdr[i]}` is true on {k} of {len(rows)} rows, but the task builds this "\n                           f"table from top-{n} lists, so membership of one list can be true on at most {n} rows. The flag "\n                           "should mark membership of that list\'s top-{n} (the list used to build the union), not every "\n                           "holding of the source.".replace("top-{n}", f"top-{n}"))\n    return out[:2]\n\n\n\nP6_INTRO = ("Ownership footnotes in the Form 4 inputs, as written in the files: each ownership field that points to a "\n            "footnote (with the element path of its footnoteId), the transaction or holding rows that carry it, then the "\n            "text of those footnotes. Form 4 General Instruction 4(b)(iii) has each form of indirect ownership reported "\n            "on its own line, with its nature stated specifically (a named trust, entity or relative); when the nature "\n            "field only points to a footnote, that footnote carries the statement, and rows pointing to different "\n            "footnotes are different indirect holdings.")\n_P6_ROWS = ("nonDerivativeTransaction", "nonDerivativeHolding", "derivativeTransaction", "derivativeHolding")\n\n\ndef _p6_val(el, path):\n    x = el.find(path)\n    if x is None:\n        return None\n    v = x.find("value")\n    return (((v.text if v is not None else x.text) or "").strip()) or None\n\n\ndef form4_footnote_preview(data_dirs: list[str], max_note: int = 300) -> str:\n    """For every input XML whose root is ownershipDocument: each distinct (ownership field, value, referenced footnote)\n    with the footnote text and the rows (counted in document order over transactions and holdings) that carry it. Only\n    fields that reference a footnote are listed. Empty when no input is a Form 4 style ownership document or none of its\n    ownership fields references a footnote."""\n    import xml.etree.ElementTree as ET\n    blocks, seen = [], set()\n    for d in data_dirs:\n        for fp in sorted(glob.glob(os.path.join(d, "**", "*.xml"), recursive=True)):\n            name = os.path.basename(fp)\n            if name in seen:\n                continue\n            try:\n                root = ET.parse(fp).getroot()\n            except Exception:\n                continue\n            if root.tag.split("}")[-1] != "ownershipDocument":\n                continue\n            seen.add(name)\n            notes = {f.get("id"): " ".join((f.text or "").split()) for f in root.iter("footnote")}\n            groups = {}\n            n = 0\n            for kind in _P6_ROWS:\n                for row in root.iter(kind):\n                    n += 1\n                    for fld in ("directOrIndirectOwnership", "natureOfOwnership"):\n                        el = row.find(f"ownershipNature/{fld}")\n                        if el is None:\n                            continue\n                        for ref in [f.get("id") for f in el.iter("footnoteId")]:\n                            groups.setdefault((fld, _p6_val(row, f"ownershipNature/{fld}"), ref), []).append(n)\n            if not groups:\n                continue\n            lines = [f"== {name} ({n} transaction and holding rows)"]\n            for fld in dict.fromkeys(f for f, _, _ in groups):\n                lines.append(f"  {fld}: value at ownershipNature/{fld}/value, footnote reference at "\n                             f"ownershipNature/{fld}/footnoteId/@id")\n            for (fld, val, ref), rows in groups.items():\n                shown = f\'"{val}"\' if val else "(no value)"\n                lines.append(f"  {fld} = {shown} -> {ref} [rows {\', \'.join(map(str, rows))}]")\n            for ref in dict.fromkeys(r for _, _, r in groups):\n                body = notes.get(ref, "")\n                lines.append(f"  {ref}: {body[:max_note]}{\'...\' if len(body) > max_note else \'\'}")\n            blocks.append("\\n".join(lines))\n    return P6_INTRO + "\\n" + "\\n".join(blocks) if blocks else ""\n\n\n\n_P7_FIELD = re.compile(r"(entity|owner|holder|beneficial|nature|name)", re.I)\n_P7_PLACEHOLDER = re.compile(r"^\\s*(see\\s+(the\\s+)?(footnotes?|note)\\b.*|by\\s+trust|\\(?\\d{1,2}\\)?|f\\d{1,2})\\s*$", re.I)\n\n\ndef _p7_xml_refs(data_dirs):\n    import xml.etree.ElementTree as ET\n    refs = {}\n    for d in data_dirs:\n        for fp in sorted(glob.glob(os.path.join(d, "**", "*.xml"), recursive=True)):\n            try:\n                root = ET.parse(fp).getroot()\n            except Exception:\n                continue\n            if root.tag.split("}")[-1] != "ownershipDocument":\n                continue\n            stem = os.path.splitext(os.path.basename(fp))[0]\n            notes = {f.get("id"): " ".join((f.text or "").split()) for f in root.iter("footnote")}\n            n = 0\n            for kind in _P6_ROWS:\n                for row in root.iter(kind):\n                    n += 1\n                    el = row.find("ownershipNature/natureOfOwnership")\n                    val = _p6_val(row, "ownershipNature/natureOfOwnership")\n                    if el is None or not val:\n                        continue\n                    for ref in [f.get("id") for f in el.iter("footnoteId")]:\n                        lst = refs.setdefault((stem, val.lower()), [])\n                        hit = next((x for x in lst if x[0] == ref), None)\n                        if hit is None:\n                            lst.append((ref, notes.get(ref, ""), [n]))\n                        else:\n                            hit[2].append(n)\n    return refs\n\n\ndef _p7_values(output_dir):\n    out = []\n    for fp in _out_files(output_dir, ".csv"):\n        try:\n            hdr, rows = _csv_rows(fp)\n        except Exception:\n            continue\n        fid = next((i for i, h in enumerate(hdr) if h.lower() in ("filing_id", "accession", "filing", "source_file")), None)\n        for i, h in enumerate(hdr):\n            if _P7_FIELD.search(h):\n                for r in rows:\n                    if len(r) > i:\n                        out.append((fp, h, r[i], r[fid] if fid is not None and len(r) > fid else None))\n    for fp in _out_files(output_dir, ".json"):\n        try:\n            leaves = []\n            _json_leaves(json.load(open(fp)), [], leaves)\n        except Exception:\n            continue\n        for _, name, v in leaves:\n            if isinstance(v, str) and _P7_FIELD.search(name):\n                out.append((fp, name, v, None))\n    return out\n\n\ndef _p7_same_filing(stem, xml_stem):\n    a, b = os.path.splitext(str(stem).strip().lower())[0], xml_stem.lower()\n    return a == b or b.endswith("_" + a) or b.endswith("-" + a)\n\n\ndef owner_placeholder_notes(output_dir: str, data_dirs: list[str]) -> list[str]:\n    """An owner-like output field whose value is a placeholder such as "See footnote" while the Form 4 input rows with that\n    nature of ownership point to footnotes: the field, the value, and each referenced footnote with its full text."""\n    refs = _p7_xml_refs(data_dirs)\n    if not refs:\n        return []\n    found = {}\n    for fp, field, val, stem in _p7_values(output_dir):\n        if not _P7_PLACEHOLDER.match(val or ""):\n            continue\n        hits = tuple((k[0], tuple((r, t, tuple(rows)) for r, t, rows in v)) for k, v in refs.items()\n                     if k[1] == val.strip().lower() and (stem is None or _p7_same_filing(stem, k[0])))\n        if hits:\n            where = found.setdefault((val.strip(), hits), [])\n            if (os.path.relpath(fp, output_dir), field) not in where:\n                where.append((os.path.relpath(fp, output_dir), field))\n    out = []\n    for (val, hits), where in list(found.items())[:2]:\n        lines = [f"Output check: \\"{val}\\" is written as an owner value in " +\n                 ", ".join(f"{f} `{c}`" for f, c in where[:6]) + (f" and {len(where) - 6} more" if len(where) > 6 else "") +\n                 ". In the input, the rows whose natureOfOwnership is this text point to footnotes, so the owner of each "\n                 "such row is written in the footnote it points to:"]\n        for xml_stem, lst in hits:\n            for ref, text, rows in lst:\n                lines.append(f"  {xml_stem}.xml rows {\', \'.join(map(str, rows))} -> {ref}: {text}")\n        fields = ", ".join(dict.fromkeys(f"`{c}`" for _, c in where))\n        refs_shown = ", ".join(dict.fromkeys(ref for _, lst in hits for ref, _, _ in lst))\n        one = fields.count("`") == 2\n        lines.append(f"{fields} {\'itself still holds\' if one else \'still hold\'} the placeholder \\"{val}\\"; the owner of these "\n                     f"rows is the one described in the footnote each row points to ({refs_shown}), so "\n                     f"{\'this field\' if one else \'these fields\'} (not a separate column) should identify that owner. Only the rows "\n                     "holding the placeholder change: a row whose nature of ownership already names its holder (for "\n                     "example \\"By X Trust\\") keeps that value, even when it also points to a footnote, because "\n                     "different indirect holdings stay on separate lines.")\n        lines.append("The reference sits at ownershipNature/natureOfOwnership/footnoteId/@id of each transaction or holding "\n                     "element; the same element also has footnoteId children elsewhere (price, transaction coding) that "\n                     "point to other footnotes, so `.//footnoteId` or ownershipNature/footnoteId picks the wrong one or "\n                     "none. For example: `ref = row.find(\'ownershipNature/natureOfOwnership/footnoteId\'); "\n                     "fid = ref.get(\'id\') if ref is not None else None; text = root.find(f\\"footnotes/footnote[@id=\'{fid}\']\\").text`, "\n                     "with `row` the nonDerivativeTransaction or nonDerivativeHolding element and `root` the "\n                     "ownershipDocument element.")\n        out.append("\\n".join(lines))\n    return out\n\n\n\n_D2_SUFFIX = re.compile(r"[\'`\\"](_{1,2}[A-Za-z][A-Za-z0-9]*)[\'`\\"]")\n_D2_ARITH = re.compile(r"\\b(difference|less|minus|subtract\\w*|sum|plus|ratio|divided|change between)\\b|[−-]\\s*[A-Z]\\b", re.I)\n_D2_SCHEMA_KEY = re.compile(r\'"([^"\\n]{2,200})"\\s*:\')\n_D2_MINUS = re.compile(r"^(?P<a>.+?)_(?P<op>minus|plus|over|div|times)_(?P<b>.+)$")\n\n\ndef _d2_derived_suffixes(statement):\n    out = {}\n    for para in re.split(r"\\n\\s*\\n", statement):\n        sufs = list(dict.fromkeys(_D2_SUFFIX.findall(para)))\n        if len(sufs) < 3:\n            continue\n        flat = " ".join(para.split())\n        marks = [(m.start(), m.end(), m.group(1)) for m in _D2_SUFFIX.finditer(flat)]\n        for k, (a, b, s) in enumerate(marks):\n            stop = marks[k + 1][0] if k + 1 < len(marks) else len(flat)\n            seg = flat[b: min(stop, b + 160)]\n            if _D2_ARITH.search(seg):\n                start = max(flat.rfind(". ", 0, a) + 2, 0)\n                out.setdefault(s, ([x for x in sufs if x != s], flat[start: b + 160].strip()))\n    return out\n\n\ndef _d2_num(v):\n    return _is_num(v)\n\n\ndef derived_missing_notes(output_dir: str, statement: str) -> list[str]:\n    """In a top-level JSON object: (a) a key stem+S where the statement defines suffix S by arithmetic on two other\n    suffixes, both stem+operand values are numbers, and stem+S is null or absent while the statement\'s schema lists it;\n    (b) a key a_<op>_b that is null while keys a and b hold numbers."""\n    if not statement:\n        return []\n    derived = _d2_derived_suffixes(statement)\n    schema = set(_D2_SCHEMA_KEY.findall(statement))\n    out = []\n    for fp in _out_files(output_dir, ".json"):\n        try:\n            obj = json.load(open(fp))\n        except Exception:\n            continue\n        if not isinstance(obj, dict):\n            continue\n        rel = os.path.relpath(fp, output_dir)\n        empty = []\n        for s, (ops, sent) in derived.items():\n            stems = {k[: -len(s)] for k in schema if k.endswith(s)}\n            for stem in sorted(stems):\n                vals = [obj.get(stem + o) for o in ops if stem + o in obj or stem + o in schema]\n                nums = [v for v in vals if _d2_num(v)]\n                if len(nums) >= 2 and obj.get(stem + s) is None:\n                    empty.append((stem + s, "absent" if stem + s not in obj else "null", sent))\n        for k, v in obj.items():\n            m = _D2_MINUS.match(k)\n            if m and v is None and _d2_num(obj.get(m.group("a"))) and _d2_num(obj.get(m.group("b"))):\n                empty.append((k, "null", f"`{k}` = `{m.group(\'a\')}` {m.group(\'op\')} `{m.group(\'b\')}`"))\n        if empty:\n            names = ", ".join(f"`{k}` ({how})" for k, how, _ in empty[:6])\n            more = f" and {len(empty) - 6} more" if len(empty) > 6 else ""\n            out.append(f"Output check: {rel}: {names}{more} are empty although both values they are defined from are "\n                       f"written. The task defines them as: \\"{empty[0][2][:240]}\\". Compute each from its two written "\n                       "operands and write it.")\n    return out[:2]\n\n\n\n_C8_REPR = re.compile(r"(?:\\bdtype: \\w+|\\bName: [^,\\n]{0,80}, dtype|\\bLength: \\d+, dtype|\\[\\d+ rows x \\d+ columns\\])")\n\n\ndef csv_shape_notes(output_dir: str) -> list[str]:\n    """A CSV whose header repeats a column name, or whose cells hold the printed form of a pandas Series or DataFrame."""\n    out = []\n    for fp in _out_files(output_dir, ".csv"):\n        try:\n            hdr, rows = _csv_rows(fp, 5000)\n        except Exception:\n            continue\n        rel = os.path.relpath(fp, output_dir)\n        dup = sorted({h for h in hdr if hdr.count(h) > 1})\n        if dup:\n            out.append(f"Output check: {rel}: the header repeats column {\', \'.join(f\'`{h}`\' for h in dup[:3])}. Two columns "\n                       "with one name usually come from concatenating frames that both carry it; keep one column per name "\n                       "with the values the task defines.")\n        hit = next(((hdr[j] if j < len(hdr) else f"column {j + 1}", c) for r in rows for j, c in enumerate(r)\n                    if _C8_REPR.search(c)), None)\n        if hit:\n            sample = " ".join(hit[1].split())[:120]\n            out.append(f"Output check: {rel}: column `{hit[0]}` holds the printed form of a pandas object, for example "\n                       f"\\"{sample}\\". A cell was given a whole Series or DataFrame instead of one value; select the scalar "\n                       "(for example with .iloc[0] or .item()) before writing.")\n    return out[:2]\n\n\n\n_C9_SEL = re.compile(r"(?:^|_)(selected|best|chosen|winning)(?:_|$)", re.I)\n\n\ndef _c9_bad(v):\n    if v is None:\n        return True\n    if isinstance(v, str):\n        return v.strip().lower() in ("", "nan", "inf", "-inf", "infinity", "-infinity", "none", "null")\n    return isinstance(v, float) and not math.isfinite(v)\n\n\ndef selected_param_notes(output_dir: str) -> list[str]:\n    """A row or object that names a selected model X (a selected/best/chosen field) where some X-prefixed parameter is\n    empty, NaN or inf while another X-prefixed field (its score) is a number."""\n    out = []\n    for fp in _out_files(output_dir, ".csv"):\n        try:\n            hdr, rows = _csv_rows(fp)\n        except Exception:\n            continue\n        sel = [j for j, h in enumerate(hdr) if _C9_SEL.search(h)]\n        if not sel:\n            continue\n        bad, total, first = 0, 0, None\n        for n, r in enumerate(rows):\n            for j in sel:\n                x = r[j].strip().lower() if j < len(r) else ""\n                if not x:\n                    continue\n                cols = [k for k, h in enumerate(hdr) if h.lower().startswith(x + "_")]\n                if len(cols) < 2:\n                    continue\n                vals = {hdr[k]: (r[k] if k < len(r) else "") for k in cols}\n                good = [h for h, v in vals.items() if not _c9_bad(v)]\n                missing = [h for h, v in vals.items() if _c9_bad(v)]\n                if x and good:\n                    total += 1\n                if good and missing:\n                    bad += 1\n                    if first is None:\n                        first = (n + 1, x, missing, good)\n        if first:\n            n, x, missing, good = first\n            out.append(f"Output check: {os.path.relpath(fp, output_dir)}: on {bad} of {total} rows the selected model is "\n                       f"`{x}` while its parameter {\', \'.join(f\'`{m}`\' for m in missing[:3])} is empty or not finite "\n                       f"(row {n}; `{good[0]}` is set). A candidate whose parameters could not be estimated should not take "\n                       "part in the selection; exclude it when its estimate is invalid (for example a mean-reversion map "\n                       "that needs a log of a non-positive coefficient) and select among the valid candidates.")\n    for fp in _out_files(output_dir, ".json"):\n        try:\n            leaves = []\n            _json_leaves(json.load(open(fp)), [], leaves)\n        except Exception:\n            continue\n        for path, name, v in leaves:\n            parts = path.split(".")\n            if any(_C9_SEL.search(p) for p in parts[:-1]) and isinstance(v, float) and not math.isfinite(v):\n                out.append(f"Output check: {os.path.relpath(fp, output_dir)} `{path}` = {v} inside the selected model. A "\n                           "selected model must have finite parameters; exclude candidates whose estimates are invalid "\n                           "before selecting.")\n                break\n    return out[:2]\n\n\n_C9_NEGLOG = re.compile(r"-\\s*(?:np|numpy|math)\\.log\\(\\s*([A-Za-z_]\\w*)\\s*\\)")\n\n\ndef neglog_names(code: str) -> list[str]:\n    return list(dict.fromkeys(_C9_NEGLOG.findall(code)))\n\n\ndef neglog_probe(names: list[str]) -> str:\n    return ("import numpy as _c9n\\nfor _c9k in %r:\\n    try:\\n        _c9v = _c9n.asarray(globals()[_c9k], dtype=float)\\n"\n            "        if (_c9v <= 0).any(): print(\'C9NEG\', _c9k, float(_c9v.min()))\\n    except Exception:\\n        pass" % names)\n\n\n\n_C10_NAME = re.compile(r"(?:^|_)(start|initial|init|opening|beginning|at_start|begin)(?:_|$)", re.I)\n_C10_VALUE = re.compile(r"(?:^|_)(cash|value|wealth|capital|price|prices|nav|balance|equity|position|positions|holdings|"\n                        r"notional|pv|level|inventory|exposure)(?:_|$)", re.I)\n_C10_WRITE = re.compile(r"\\.to_csv\\(|\\.to_parquet\\(|json\\.dump\\(|\\.write_text\\(|open\\([^)]*[\'\\"]w")\n\n\ndef unused_start_names(code: str, later: str = "", require_write: bool = False) -> list[tuple[str, str]]:\n    """Names that say they hold an amount at the start of a period (a start word and an amount word, for example\n    cash_at_start), assigned from a computation rather than a parameter or a literal, and never read afterwards in that\n    cell or in later code. require_write limits it to cells that write output files (that version missed the case it\n    was built for, so the default is off)."""\n    import ast\n    if require_write and not _C10_WRITE.search(code):\n        return []\n    try:\n        tree = ast.parse(code)\n    except SyntaxError:\n        return []\n    assigned = {}\n    for node in ast.walk(tree):\n        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):\n            targets = node.targets if isinstance(node, ast.Assign) else [node.target]\n            for t in targets:\n                for x in ast.walk(t):\n                    if isinstance(x, ast.Name) and _C10_NAME.search(x.id) and _C10_VALUE.search(x.id):\n                        src = ast.get_source_segment(code, node) or ""\n                        if re.search(r"=\\s*(?:params|config|cfg|settings)\\b|=\\s*-?[\\d.]+\\s*(?:#|$)", src):\n                            continue\n                        assigned.setdefault(x.id, node.lineno)\n    if not assigned:\n        return []\n    loads = {x.id for x in ast.walk(tree) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)}\n    out = []\n    lines = code.splitlines()\n    for name, ln in assigned.items():\n        if name in loads or re.search(r"\\b%s\\b" % re.escape(name), later):\n            continue\n        out.append((name, lines[ln - 1].strip() if 0 < ln <= len(lines) else name))\n    return out\n\n\ndef unused_start_note(name: str, line: str) -> str:\n    return (f"Code note: `{line}` defines `{name}` in this cell, but nothing in this cell or later reads it. A value "\n            "taken at the start of a period is usually needed by a later formula (a return, a drawdown, a capacity or "\n            "cash measure); check whether the formula that should use it uses something else instead.")\n', 'oc10/oc10_checks.py': 'import csv, glob, json, math, os, re\n\n\n\ndef _out_files(output_dir, ext):\n    return sorted(glob.glob(os.path.join(output_dir, "**", "*" + ext), recursive=True))\n\n\ndef _csv(path, limit=50000):\n    with open(path, newline="", errors="ignore") as f:\n        rows = list(csv.reader(f))\n    return (rows[0], rows[1:limit + 1]) if rows else ([], [])\n\n\ndef _num(s):\n    try:\n        return float(s)\n    except (TypeError, ValueError):\n        return None\n\n\ndef _ints(expr):\n    return sorted(int(x) for x in re.findall(r"\\d+", expr or ""))\n\n\n\n_R1_RANGES = (\n    re.compile(r"`\\s*([A-Za-z])\\s*=\\s*([^`]+?)`\\s*(?:through|to|until)\\s*`([^`]+?)`\\s*,?\\s*\\(?inclusive", re.I),\n    re.compile(r"\\b([A-Za-z])\\s*(?:=|from)\\s*([\\w()+\\-, ]+?)\\s+(?:through|to)\\s+([\\w()+\\-]+)\\s*,?\\s*\\(?inclusive", re.I),\n    re.compile(r"\\b([A-Za-z])\\s*(?:∈|in)\\s*\\[\\s*([^\\],\\[]+?)\\s*,\\s*([^\\]\\[]+?)\\s*\\]"),\n)\n\n\ndef inclusive_lag_ranges(statement: str) -> list[dict]:\n    """Inclusive index ranges of the statement whose paragraph also writes the lag of the same index (x_{j-1}, x[j-1])."""\n    out = []\n    for para in re.split(r"\\n\\s*\\n", statement or ""):\n        flat = " ".join(para.split())\n        for rx in _R1_RANGES:\n            for m in rx.finditer(flat):\n                v, lo, hi = m.group(1), m.group(2).strip(), m.group(3).strip()\n                lag = re.compile(r"[_\\[{]\\s*\\{?\\s*%s\\s*-\\s*1\\s*\\}?" % re.escape(v))\n                if lag.search(flat) and _ints(lo):\n                    out.append({"var": v, "lo": lo, "hi": hi, "text": m.group(0)})\n    return out\n\n\ndef _r1_assign(code, name, pos):\n    found = [m for m in re.finditer(r"^[ \\t]*%s\\s*=(?!=)\\s*([^\\n#]+)" % re.escape(name), code, re.M) if m.start() < pos]\n    return (found[-1].group(1).strip(), found[-1].start()) if found else (None, None)\n\n\ndef _r1_bound(code, low, pos):\n    off = 0\n    for _ in range(3):\n        m = re.fullmatch(r"\\s*(.+?)\\s*([+-])\\s*([1-3])\\s*", low)\n        if m and not re.search(r"[(,]\\s*$", m.group(1)):\n            off += int(m.group(3)) * (1 if m.group(2) == "+" else -1)\n            low = m.group(1)\n        if re.fullmatch(r"[A-Za-z_]\\w*", low.strip()):\n            rhs, p = _r1_assign(code, low.strip(), pos)\n            if rhs is None:\n                break\n            low, pos = rhs, p\n        else:\n            break\n    return low.strip(), off\n\n\n_R1_USE = r"\\b%s(?:\\[[\'\\"]\\w+[\'\\"]\\])?(?:\\.iloc|\\.values|\\.to_numpy\\(\\))?\\s*\\[\\s*%s\\s*\\]"\n\n\ndef _r1_origin(code, name, pos, depth=0):\n    if depth > 4:\n        return None\n    rhs, p = _r1_assign(code, name, pos)\n    if rhs is None:\n        return None\n    m = re.match(r"(?:np\\.)?diff\\(\\s*(?:np\\.\\w+\\(\\s*)?([A-Za-z_]\\w*)", rhs) or re.match(r"([A-Za-z_]\\w*)[^\\n]*?\\.diff\\(\\s*\\)", rhs)\n    if m:\n        o = _r1_origin(code, m.group(1), p, depth + 1) if "[" not in rhs.split("diff")[0] else None\n        sl = re.search(r"\\[\\s*([^\\[\\]:\\n]+?)\\s*:[^\\]\\n]*\\]", rhs)\n        if o is None and sl:\n            o = (sl.group(1), p, 0)\n        return (o[0], o[1], o[2] + 1) if o else None\n    sl = re.search(r"(?:\\.iloc|\\.loc|\\.values|\\b\\w+)\\s*\\[\\s*([^\\[\\]:\'\\"\\n]+?)\\s*:[^\\]\\n]*\\]", rhs)\n    if sl:\n        return (sl.group(1), p, 0)\n    ix = re.search(r"\\.iloc\\[\\s*([A-Za-z_]\\w*)\\s*\\]", rhs)\n    if ix:\n        r2, p2 = _r1_assign(code, ix.group(1), p)\n        rg = re.search(r"range\\(\\s*([^,\\n]+?)\\s*,", r2 or "")\n        if rg:\n            return (rg.group(1), p2, 0)\n    rg = re.search(r"for\\s+\\w+\\s+in\\s+range\\(\\s*([^,\\n]+?)\\s*,", rhs)\n    if rg:\n        return (rg.group(1), p, 0)\n    if re.search(r"^\\[\\s*\\]$|^list\\(\\s*\\)$", rhs) and re.search(r"\\b%s\\s*\\.append\\(" % re.escape(name), code[p:]):\n        loops = [m for m in re.finditer(r"for\\s+\\w+\\s+in\\s+range\\(\\s*([^,\\n]+?)\\s*,", code) if m.start() > p]\n        return (loops[0].group(1), loops[0].start(), 0) if loops else None\n    m = re.match(r"(?:np\\.(?:array|asarray)\\(|list\\()?\\s*([A-Za-z_]\\w*)(?:\\[[\'\\"]\\w+[\'\\"]\\])?\\s*(?:\\.values|\\.to_numpy\\(\\))?\\s*\\)?\\s*$", rhs)\n    if m and m.group(1) != name:\n        return _r1_origin(code, m.group(1), p, depth + 1)\n    return None\n\n\ndef lag_slice_hits(code: str, ranges: list[dict]) -> list[dict]:\n    """Arrays whose first element is the value at a statement range\'s lower endpoint (or later), fitted as W[1:] on\n    W[:-1]: the first index of the inclusive range is lost. The start is traced through slices, iloc index lists, loops\n    that append, np.diff / .diff (one index later) and np.array wrappers; an array that starts one index before the\n    range is the correct construction and is not reported."""\n    hits = []\n    for w in dict.fromkeys(re.findall(r"\\b([A-Za-z_]\\w*)(?:\\[[\'\\"]\\w+[\'\\"]\\])?(?:\\.iloc|\\.values|\\.to_numpy\\(\\))?\\s*\\[\\s*1\\s*:\\s*\\]", code)):\n        use = re.search(_R1_USE % (re.escape(w), r"1\\s*:\\s*"), code)\n        if not re.search(_R1_USE % (re.escape(w), r":\\s*-\\s*1\\s*"), code):\n            continue\n        o = _r1_origin(code, w, use.start())\n        if o is None:\n            continue\n        low, pos, extra = o\n        base, off = _r1_bound(code, low, pos)\n        for r in ranges:\n            rbase, roff = _r1_bound("", r["lo"], 0)\n            if _ints(base) == _ints(rbase) and off + extra >= roff:\n                line = code[pos:].split("\\n", 1)[0].strip()\n                hits.append({"array": w, "low": low, "after": off + extra - roff, "build_line": line,\n                             "build_line_fixed": _r1_fixed(line, low), **r})\n                break\n    return hits\n\n\ndef _r1_fixed(line: str, low: str) -> str | None:\n    k = re.fullmatch(r"(.+?)\\s*-\\s*(\\d+)", low)\n    new = f"{k.group(1)} - {int(k.group(2)) + 1}" if k else low + " - 1"\n    fixed, n = re.subn(r"(range\\(\\s*|\\[\\s*)%s(\\s*[,:])" % re.escape(low), lambda m: m.group(1) + new + m.group(2), line, count=1)\n    return fixed if n else None\n\n\ndef lag_slice_note(hit: dict) -> str:\n    v, w, k = hit["var"], hit["array"], hit["after"]\n    where = f"the first `{v}` of the range" if k == 0 else f"{k} index{\'es\' if k > 1 else \'\'} after the first `{v}`"\n    return (f"Code note: the statement fits a regression on the lag `{v}-1` for `{v}` from `{hit[\'lo\']}` through "\n            f"`{hit[\'hi\']}`, inclusive, so every `{v}` in that range is an observation and the lag of the first one lies "\n            f"just before the range. In this cell the first element of `{w}` (built from `{hit[\'low\']}`) is the value "\n            f"at {where}, and the fit pairs `{w}[1:]` with `{w}[:-1]`, so the first `{v}` of the range is not an "\n            f"observation. " + (\n                f"Build `{w}` from one index earlier and keep the fit as it is:\\n    {hit[\'build_line_fixed\']}        # was: "\n                f"{hit[\'build_line\']}\\nThen `{w}[1:]` covers every `{v}` from `{hit[\'lo\']}` through `{hit[\'hi\']}` and "\n                f"`{w}[:-1]` holds their lags. Print len({w}) - 1 and check it equals the number of `{v}` in the range."\n                if hit.get("build_line_fixed") else\n                f"Build the series from one index before the range so the left-hand side covers every `{v}` "\n                f"from `{hit[\'lo\']}` through `{hit[\'hi\']}`."))\n\n\n\n_R2_SORT = re.compile(r"(?:sorted|ordered|sort(?:ed)?\\s+(?:rows?\\s+)?by)\\s+(?:by\\s+)?`?(abs\\()?`?([A-Za-z_]\\w*)`?\\)?`?"\n                      r"[^.\\n`]{0,30}?\\b(ascending|descending|asc|desc|increasing|decreasing)\\b", re.I)\n_R2_FILE = re.compile(r"`([\\w\\-./]+\\.csv)`")\n\n\ndef sort_rules(statement: str) -> list[dict]:\n    """(file, column, abs, descending) for every "sorted by X ascending/descending" sentence that names CSV files in its own\n    paragraph, or else sits under a heading or bullet that names exactly one CSV file; unbound sentences are dropped."""\n    rules = []\n    lines = (statement or "").splitlines()\n    head_file = None\n    para = []\n\n    def flush():\n        text = " ".join(" ".join(para).split())\n        for m in _R2_SORT.finditer(text):\n            files = list(dict.fromkeys(_R2_FILE.findall(text)))\n            bound = files or ([head_file] if head_file else [])\n            for f in bound:\n                rules.append({"file": os.path.basename(f), "column": m.group(2), "abs": bool(m.group(1)),\n                              "desc": m.group(3).lower().startswith(("desc", "decr")), "text": m.group(0)})\n        para.clear()\n\n    for line in lines:\n        if re.match(r"\\s*#{1,6}\\s", line) or re.match(r"\\s*[-*]\\s+\\*{0,2}`[\\w\\-./]+\\.csv`", line):\n            flush()\n            files = _R2_FILE.findall(line)\n            head_file = files[0] if len(files) == 1 else (None if re.match(r"\\s*#", line) else head_file)\n        if not line.strip():\n            flush()\n            continue\n        para.append(line)\n    flush()\n    return [dict(t) for t in {tuple(sorted(r.items())) for r in rules}]\n\n\ndef sort_order_notes(output_dir: str, statement: str) -> list[str]:\n    out = []\n    for r in sorted(sort_rules(statement), key=lambda r: (r["file"], r["column"])):\n        for fp in _out_files(output_dir, ".csv"):\n            if os.path.basename(fp) != r["file"]:\n                continue\n            try:\n                hdr, rows = _csv(fp)\n            except Exception:\n                continue\n            if r["column"] not in hdr or len(rows) < 3:\n                continue\n            j = hdr.index(r["column"])\n            vals = [_num(x[j]) if j < len(x) else None for x in rows]\n            if any(v is None or math.isnan(v) for v in vals):\n                continue\n            vv = [abs(v) for v in vals] if r["abs"] else vals\n            bad = next((k for k in range(len(vv) - 1) if (vv[k] < vv[k + 1] if r["desc"] else vv[k] > vv[k + 1])), None)\n            if bad is None:\n                continue\n            key = f"abs({r[\'column\']})" if r["abs"] else r["column"]\n            out.append(f"Output check: {os.path.relpath(fp, output_dir)} is not sorted by `{key}` "\n                       f"{\'descending\' if r[\'desc\'] else \'ascending\'}, which the task text asks for this file "\n                       f"(\\"{r[\'text\']}\\"): rows {bad + 1} and {bad + 2} hold {rows[bad][j]} then {rows[bad + 1][j]}. "\n                       "Sort the rows by that key before writing.")\n    return out\n\n\n\n_R3_SIG = r"\\w*(?:signal|sig|cross|buy|sell|position|pos|entry|exit|weight|exec|trade|order|flag|regime)\\w*"\n_R3_PRICE = re.compile(r"(open|close|high|low|price|px|ret|return|yield|volume|vwap|mid|bid|ask|date|time)", re.I)\n_R3_LINE = re.compile(r"^\\s*(?:\\w+\\[[\'\\"](?P<lc>%s)[\'\\"]\\]|(?P<lv>%s))\\s*=\\s*[^\\n#]*?(?:\\[[\'\\"](?P<rc>\\w+)[\'\\"]\\]|\\b(?P<rv>\\w+))"\n                      r"\\s*\\.shift\\(\\s*-\\s*(?P<k>\\d+)\\s*\\)" % (_R3_SIG, _R3_SIG), re.I | re.M)\n\n\ndef future_signal_hits(code: str) -> list[tuple[str, str, str]]:\n    """(target, source, line) for assignments of a signal-like column from a signal-like column shifted by -k."""\n    hits = []\n    for m in _R3_LINE.finditer(code):\n        tgt, src = m.group("lc") or m.group("lv"), m.group("rc") or m.group("rv")\n        if re.fullmatch(_R3_SIG, src, re.I) and not _R3_PRICE.search(src):\n            hits.append((tgt, src, m.group(0).strip()))\n    return hits\n\n\ndef future_signal_note(tgt: str, src: str, line: str) -> str:\n    return (f"Code note: `{line}` puts on each row the value of `{src}` from a later row, so on row t `{tgt}` is the "\n            f"signal of t+k, which is not known at t. If a signal formed on day t is acted on at t+1, either shift the "\n            f"signal forward (shift(+1)) so the execution row sees the earlier signal, or keep the signal on its own row "\n            f"and take the later price (price.shift(-1)) for the fill.")\n\n\n\n_R4_COL = re.compile(r"(?:^|_)(aic|aicc|bic|hqic|loglik|log_likelihood|llf|nll|neg_loglik|likelihood)(?:$|_)", re.I)\n_R4_ALLOW = r"`%s`[^\\n.]{0,120}\\b(null|nan|empty|blank|missing|none)\\b"\n_R4_IC_WORD = re.compile(r"\\b(aic|bic|hqic|log-?likelihood|likelihood)\\b", re.I)\n_R4_GAP_WORD = re.compile(r"\\b(finite|non-finite|infinite|null|nan|empty|blank|missing)\\b", re.I)\n_R4_ROW_SKIP = re.compile(r"insufficient|not_enough|too_few|no_data|skipped|failed", re.I)\n\n\ndef _r4_statement_allows(statement):\n    for sent in re.split(r"(?<=[.;:])\\s+|\\n\\s*[-*]\\s+", " ".join((statement or "").split("\\n"))):\n        if _R4_IC_WORD.search(sent) and _R4_GAP_WORD.search(sent):\n            return True\n    return False\n\n\ndef ic_gap_notes(output_dir: str, statement: str) -> list[str]:\n    out = []\n    if _r4_statement_allows(statement):\n        return out\n    for fp in _out_files(output_dir, ".csv"):\n        try:\n            hdr, rows = _csv(fp)\n        except Exception:\n            continue\n        rows = [x for x in rows if not any(_R4_ROW_SKIP.search(v or "") for v in x)]\n        for j, c in enumerate(hdr):\n            if not _R4_COL.search(c or "") or re.search(_R4_ALLOW % re.escape(c), statement or "", re.I):\n                continue\n            vals = [x[j] if j < len(x) else "" for x in rows]\n            fin = [k for k, v in enumerate(vals) if _num(v) is not None and math.isfinite(_num(v))]\n            bad = [k for k, v in enumerate(vals) if k not in set(fin)]\n            if not fin or not bad:\n                continue\n            k = bad[0]\n            label = ", ".join(f"{h}={rows[k][i]}" for i, h in enumerate(hdr[:3]) if i < len(rows[k]))\n            out.append(f"Output check: {os.path.relpath(fp, output_dir)}: `{c}` is empty or not finite on {len(bad)} of "\n                       f"{len(vals)} rows (first: row {k + 1}, {label}) while the other rows have a value. A comparison by "\n                       f"`{c}` needs a value for every candidate it ranks; find why this fit produced none (for example "\n                       f"a parameter outside the family\'s valid range or a failed optimisation) and compute it, rather "\n                       f"than leaving the row out of the comparison.")\n            break\n    return out\n\n\n', 'varES/es_denominator.py': '"""Code check: expected shortfall divided by the realised tail mass (1 - cdf at the VaR point) instead of (1 - alpha)."""\nimport re\n\nDENOM = re.compile(r"/\\s*\\(?\\s*1(?:\\.0*)?\\s*-\\s*(?:np\\.)?(?:cdf|F|cum\\w*)\\s*(?:\\([^()]*\\))?\\s*(?:\\.(?:iloc|loc|values))?\\s*\\[")\nES_TOK = {"es", "cvar", "shortfall", "tvar", "cte", "etl"}\nES_TEXT = re.compile(r"(?i:expected[ _-]shortfall|\\bcvar\\b|\\bes_\\w*|\\w*_es\\b)|\\bES\\b")\n\n\ndef _tokens(name):\n    s = re.sub(r"([a-z0-9])([A-Z])", r"\\1_\\2", name)\n    return [t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t]\n\n\ndef _is_es_line(line, context):\n    m = re.match(r"\\s*([A-Za-z_][\\w\\[\\]\'\\".]*)\\s*[+\\-*/]?=(?!=)", line)\n    if m and set(_tokens(m.group(1))) & ES_TOK:\n        return True\n    return bool(ES_TEXT.search(context))\n\n\ndef _message(line):\n    return (f"`{line}` divides by the realised tail mass beyond the VaR grid point (one minus the cdf there), not by "\n            f"(1 - alpha). On a discrete or lattice distribution the VaR point carries an atom, so this is the mean of "\n            f"the losses beyond VaR, not expected shortfall at level alpha. The discrete ES at level alpha "\n            f"(Acerbi & Tasche 2002) divides by (1 - alpha) and counts the VaR atom only in the proportion needed to "\n            f"fill the tail: ES = (sum over x > VaR of x * p(x) + VaR * (P(X <= VaR) - alpha)) / (1 - alpha), "\n            f"equivalently VaR + sum(max(x - VaR, 0) * p(x)) / (1 - alpha). Compute both numbers and print them. "\n            f"If the task gives another formula, follow the task.")\n\n\ndef _notes(code, history, statement):\n    res = {}\n    context = "\\n".join((code, history, statement))\n    for raw in code.splitlines():\n        line = raw.strip()\n        if not line or line.startswith("#"):\n            continue\n        body = line.split("#", 1)[0]\n        if not DENOM.search(body) or not _is_es_line(body, context):\n            continue\n        key = "es_denominator:" + re.sub(r"\\s+", "", body)\n        res.setdefault(key, _message(line[:200]))\n    return list(res.items())\n\n\ndef es_denominator_notes(code: str, history: str, statement: str) -> list[tuple[str, str]]:\n    try:\n        return _notes(code or "", history or "", statement or "")\n    except Exception:\n        return []\n', 'stable/reset_index_loc.py': '"""Code check: X.index used to .loc/.iloc into another object after X\'s labels were rebuilt by reset_index."""\nimport ast\nimport re\n\n_ASSIGN = re.compile(r"^\\s*(\\w+)\\s*=(?!=)\\s*(.+)$")\n_USE = re.compile(r"(\\w+)\\.(?:loc|iloc)\\[\\s*(\\w+)\\.index\\b")\n_RESET_CALL = re.compile(r"reset_index\\([^()]*\\)")\n\n\n_RELABEL = {"groupby", "pivot", "pivot_table", "merge", "melt", "stack", "unstack", "agg", "aggregate",\n            "resample", "value_counts", "set_index", "reset_index", "explode", "crosstab", "describe"}\n\n\ndef _index_link(node):\n    for sub in ast.walk(node):\n        if isinstance(sub, ast.Call):\n            for k in sub.keywords:\n                v = k.value\n                if (k.arg == "index" and isinstance(v, ast.Attribute) and v.attr == "index"\n                        and isinstance(v.value, ast.Name)):\n                    return v.value.id\n    return None\n\n\ndef _base_name(node):\n    while True:\n        if isinstance(node, ast.IfExp):\n            node = node.body\n        elif isinstance(node, ast.Call):\n            node = node.func\n        elif isinstance(node, (ast.Attribute, ast.Subscript)):\n            node = node.value\n        elif isinstance(node, ast.Name):\n            return node.id\n        else:\n            return None\n\n\ndef _chain_methods(node):\n    out = []\n    while True:\n        if isinstance(node, ast.IfExp):\n            node = node.body\n        elif isinstance(node, ast.Call):\n            if isinstance(node.func, ast.Attribute):\n                out.append(node.func.attr)\n            node = node.func\n        elif isinstance(node, (ast.Attribute, ast.Subscript)):\n            node = node.value\n        else:\n            return out\n\n\nclass _State:\n    def __init__(self):\n        self.origin = {}\n        self.reset_text = {}\n        self.parent = {}\n\n    def assign(self, var, value, seg):\n        base = _base_name(value)\n        meths = _chain_methods(value)\n        link = _index_link(value)\n        self.parent[var] = link if link else (None if _RELABEL & set(meths) else base)\n        if "reset_index" in meths:\n            self.origin[var] = var\n            m = _RESET_CALL.search(seg or "")\n            self.reset_text[var] = m.group(0) if m else "reset_index()"\n        elif "set_index" in meths:\n            self.origin.pop(var, None)\n        elif base is not None and base in self.origin and base != var:\n            self.origin[var] = self.origin[base]\n        elif base != var:\n            self.origin.pop(var, None)\n\n    def copy(self):\n        c = _State()\n        c.origin, c.reset_text, c.parent = dict(self.origin), dict(self.reset_text), dict(self.parent)\n        return c\n\n    def forget(self, var):\n        self.origin.pop(var, None)\n\n    def shares_labels(self, y, x):\n        org = self.origin.get(x)\n        seen, cur = set(), y\n        while cur is not None and cur not in seen:\n            if cur == x or cur == org or (org is not None and self.origin.get(cur) == org):\n                return True\n            if self.origin.get(cur) == cur:\n                return False\n            seen.add(cur)\n            cur = self.parent.get(cur)\n        return False\n\n\ndef _loc_uses(node):\n    for sub in ast.walk(node):\n        if not (isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Attribute)\n                and sub.value.attr in ("loc", "iloc") and isinstance(sub.value.value, ast.Name)):\n            continue\n        sl = sub.slice\n        first = sl.elts[0] if isinstance(sl, ast.Tuple) and sl.elts else sl\n        if (isinstance(first, ast.Attribute) and first.attr == "index"\n                and isinstance(first.value, ast.Name)):\n            yield sub.value.value.id, first.value.id, sub.lineno\n\n\ndef _walk_statements(body, state, src, lines, hits):\n    for st in body:\n        if hits is not None:\n            for y, x, ln in _loc_uses(st if not hasattr(st, "body") else _header(st)):\n                _maybe_hit(state, y, x, ln, lines, hits)\n        if isinstance(st, ast.Assign):\n            seg = ast.get_source_segment(src, st.value)\n            for t in st.targets:\n                if isinstance(t, ast.Name):\n                    state.assign(t.id, st.value, seg)\n                elif isinstance(t, (ast.Tuple, ast.List)):\n                    for e in t.elts:\n                        if isinstance(e, ast.Name):\n                            state.forget(e.id)\n                elif (isinstance(t, ast.Attribute) and t.attr == "index"\n                      and isinstance(t.value, ast.Name)):\n                    state.forget(t.value.id)\n        elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):\n            f = st.value.func\n            inplace = any(k.arg == "inplace" for k in st.value.keywords)\n            if inplace and isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):\n                if f.attr == "reset_index":\n                    seg = ast.get_source_segment(src, st.value) or ""\n                    m = _RESET_CALL.search(seg)\n                    state.origin[f.value.id] = f.value.id\n                    state.reset_text[f.value.id] = m.group(0) if m else "reset_index()"\n                elif f.attr == "set_index":\n                    state.forget(f.value.id)\n        elif isinstance(st, (ast.For, ast.AsyncFor)):\n            if isinstance(st.target, ast.Name):\n                state.forget(st.target.id)\n            elif isinstance(st.target, (ast.Tuple, ast.List)):\n                for e in st.target.elts:\n                    if isinstance(e, ast.Name):\n                        state.forget(e.id)\n        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):\n            _walk_statements(st.body, state.copy(), src, lines, hits)\n            continue\n        for field in ("body", "orelse", "finalbody"):\n            sub = getattr(st, field, None)\n            if isinstance(sub, list):\n                _walk_statements(sub, state, src, lines, hits)\n        for h in getattr(st, "handlers", []) or []:\n            _walk_statements(h.body, state, src, lines, hits)\n\n\ndef _header(st):\n    for name in ("iter", "test", "items"):\n        v = getattr(st, name, None)\n        if v is not None:\n            return v if not isinstance(v, list) else ast.Tuple(elts=[i.context_expr for i in v], ctx=ast.Load())\n    return ast.Pass()\n\n\ndef _maybe_hit(state, y, x, ln, lines, hits):\n    if x == y or x not in state.origin or state.shares_labels(y, x):\n        return\n    line = lines[ln - 1].strip() if 0 < ln <= len(lines) else ""\n    if line:\n        hits.append((y, x, state.origin[x], state.reset_text.get(state.origin[x], "reset_index()"), line))\n\n\ndef _scan_regex(prefix, code, state=None):\n    state, hits = state or _State(), []\n    for part, collect in ((prefix, False), (code, True)):\n        for ln in part.splitlines():\n            if collect:\n                for y, x in _USE.findall(ln):\n                    if x != y and x in state.origin and not state.shares_labels(y, x):\n                        o = state.origin[x]\n                        hits.append((y, x, o, state.reset_text.get(o, "reset_index()"), ln.strip()))\n            m = _ASSIGN.match(ln)\n            if m:\n                v, rhs = m.groups()\n                try:\n                    node = ast.parse(rhs.strip(), mode="eval").body\n                except SyntaxError:\n                    src = re.match(r"(\\w+)\\b", rhs.strip())\n                    node = ast.Name(id=src.group(1), ctx=ast.Load()) if src else ast.Constant(None)\n                    if "reset_index(" in rhs:\n                        node = ast.Call(func=ast.Attribute(value=node, attr="reset_index", ctx=ast.Load()),\n                                        args=[], keywords=[])\n                state.assign(v, node, rhs)\n    return hits\n\n\ndef _message(y, x, origin, reset_text, line):\n    if origin == x:\n        src = f"`{x}` was rebuilt with `.{reset_text}`"\n    else:\n        src = f"`{x}` comes from `{origin}`, which was rebuilt with `.{reset_text}`"\n    return (f"`{line}` uses `{x}.index`, but {src}; its labels are now 0..n-1 and no longer point at "\n            f"the matching rows of `{y}`. Select by a key column (e.g. the identifier) or keep the "\n            f"original index instead of resetting it, then print the selected identifiers to confirm.")\n\n\ndef reset_index_loc_notes(code: str, history: str, statement: str) -> list:\n    """Return (dedup_key, message) for lines of the current cell that index another object with reset labels."""\n    try:\n        code = code or ""\n        history = history or ""\n        if "reset_index" not in history and "reset_index" not in code:\n            return []\n        prefix = history[: len(history) - len(code)] if code and history.endswith(code) else history\n        try:\n            state = _State()\n            try:\n                ptree = ast.parse(prefix)\n                _walk_statements(ptree.body, state, prefix, prefix.splitlines(), None)\n            except SyntaxError:\n                state = _State()\n                _scan_regex(prefix, "", state)\n            ctree = ast.parse(code)\n            raw = []\n            _walk_statements(ctree.body, state, code, code.splitlines(), raw)\n        except SyntaxError:\n            raw = _scan_regex("", code, state)\n        out, seen = [], set()\n        for y, x, origin, reset_text, line in raw:\n            key = f"reset_index_loc|{y}|{x}|{line}"\n            if key in seen:\n                continue\n            seen.add(key)\n            out.append((key, _message(y, x, origin, reset_text, line)))\n        return out\n    except Exception:\n        return []\n', 'oc7mid/lead_twice.py': 'import re\n\nIDX = r"[^\\[\\],\\n]*?\\+\\s*1(?![\\d.])\\s*"\nACC = r"(?:\\.(?:iloc|loc|at|iat|values|to_numpy\\(\\)|array))?"\nSHIFT = r"\\.shift\\(\\s*(?:periods\\s*=\\s*)?-\\s*1\\s*\\)"\nCOL_DEF = re.compile(r"\\[\\s*([\'\\"])(\\w+)\\1\\s*\\]\\s*=(?!=)[^\\n]*" + SHIFT)\nVAR_DEF = re.compile(r"^\\s*(\\w+)\\s*=(?!=)(?![^\\n]*\\.assign\\()[^\\n]*" + SHIFT)\nIDX_VAR_DEF = re.compile(r"^\\s*(\\w+)\\s*=(?!=)\\s*(?:\\w+|[^\\n]*get_loc\\([^\\n]*\\))\\s*\\+\\s*1\\s*$")\n\n\ndef strip_comment(line: str) -> str:\n    q = None\n    for i, ch in enumerate(line):\n        if q:\n            if ch == q:\n                q = None\n        elif ch in "\'\\"":\n            q = ch\n        elif ch == "#":\n            return line[:i].rstrip()\n    return line.rstrip()\n\n\ndef col_read(col: str, idx: str) -> re.Pattern:\n    c = r"[\'\\"]%s[\'\\"]" % re.escape(col)\n    return re.compile("|".join([\n        r"\\.(?:iloc|loc|at|iat)\\[\\s*(?:%s)\\s*\\]\\s*\\[\\s*%s\\s*\\]" % (idx, c),\n        r"\\.(?:loc|at)\\[\\s*(?:%s)\\s*,\\s*%s\\s*\\]" % (idx, c),\n        r"\\.iloc\\[\\s*(?:%s)\\s*,[^\\]\\n]*%s" % (idx, c),\n        r"\\[\\s*%s\\s*\\]\\s*%s\\s*\\[\\s*(?:%s)\\s*\\]" % (c, ACC, idx),\n        r"\\.(?:iloc|loc)\\[\\s*(?:%s)\\s*\\]\\s*\\.%s\\b" % (idx, re.escape(col)),\n        r"\\.%s%s\\s*\\[\\s*(?:%s)\\s*\\]" % (re.escape(col), ACC, idx),\n    ]))\n\n\ndef var_read(var: str, idx: str) -> re.Pattern:\n    return re.compile(r"(?<![\\w.\'\\"])%s%s\\s*\\[\\s*(?:%s)\\s*\\]" % (re.escape(var), ACC, idx))\n\n\nCOL_ASSIGN = re.compile(r"\\[\\s*([\'\\"])(\\w+)\\1\\s*\\]\\s*=(?!=)")\nNAME_ASSIGN = re.compile(r"^\\s*(\\w+)\\s*=(?!=)")\n\n\ndef update(state: dict, line: str) -> None:\n    for m in COL_ASSIGN.finditer(line):\n        d = COL_DEF.search(line)\n        state["col"][m.group(2)] = line.strip() if d and d.group(2) == m.group(2) else None\n    m = NAME_ASSIGN.match(line)\n    if m:\n        name = m.group(1)\n        state["var"][name] = line.strip() if VAR_DEF.match(line) else None\n        state["idx"][name] = bool(IDX_VAR_DEF.match(line))\n\n\ndef lead_twice_notes(code: str, history: str, statement: str) -> list[tuple[str, str]]:\n    """(dedup_key, message) per line of this cell that reads a shift(-1) column at row +1."""\n    out = []\n    try:\n        code = code or ""\n        history = history or ""\n        pos = history.rfind(code) if code else -1\n        before = history[:pos] if pos >= 0 else history + "\\n"\n        state = {"col": {}, "var": {}, "idx": {}}\n        for x in before.splitlines():\n            update(state, strip_comment(x))\n        seen = set()\n        for raw in code.splitlines():\n            line = strip_comment(raw)\n            cols = sorted(k for k, d in state["col"].items() if d and k in line)\n            vars_ = sorted(k for k, d in state["var"].items() if d and k in line)\n            if "[" in line and (cols or vars_):\n                idx = IDX + "".join("|" + re.escape(v) for v in sorted(k for k, f in state["idx"].items() if f))\n                hits = [(c, state["col"][c]) for c in cols if col_read(c, idx).search(line)]\n                hits += [(v, state["var"][v]) for v in vars_ if var_read(v, idx).search(line)]\n                for name, d in hits:\n                    rd = line.strip()\n                    key = "lead_twice|%s|%s" % (name, re.sub(r"\\s+", "", rd))\n                    if key in seen:\n                        continue\n                    seen.add(key)\n                    out.append((key, f"Code check: `{d}` already moves `{name}` one row forward, and `{rd}` reads it at the next "\n                                     "row again, so this value comes from two rows ahead: the row was moved forward twice. "\n                                     "Keep one of the two leads, the one the task\'s timing states (read the unshifted column at the "\n                                     f"next row, or read `{name}` at the current row), not both; then print one example with the "\n                                     "decision date, the date the value is taken from, and the value."))\n            update(state, line)\n    except Exception:\n        return out\n    return out\n', 'es_boundary/es_strict.py': 'import re\n\nRESAMPLE = re.compile(r"\\.choice\\(|\\.integers\\(|randint\\(|bootstrap|resample|replace\\s*=\\s*True|\\bFHS\\b|filtered historical", re.I)\nTHRESH = r"[A-Za-z_][\\w\\.]*(?:\\[[^\\]\\n]*\\])?"\nLOSS_STRICT = re.compile(rf"(\\w*loss\\w*)(?:\\[[^\\]\\n]*\\])?\\s*>\\s*(?!=)({THRESH})", re.I)\nRET_STRICT = re.compile(rf"(\\w+)(?:\\[[^\\]\\n]*\\])?\\s*<\\s*(?!=)-?\\s*({THRESH})")\nTHRESH_NAME = re.compile(r"var|(?:^|_)q(?:_|\\d|$)|quant|thresh|cut", re.I)\nMEAN = re.compile(r"\\.mean\\(|np\\.mean\\(|nanmean\\(")\nSTRICT_TASK = re.compile(r"strictly\\s+(?:greater\\s+than|exceed\\w*|above|below|less\\s+than)[^.\\n]{0,40}\\bVaR\\b|\\bVaR\\b[^.\\n]{0,40}strictly", re.I)\n\n\ndef tail_mean_follows(body: str, m, following: list[str]) -> bool:\n    """True when the strict comparison selects a tail that is then averaged: used inside a subscript (x[x > v]) whose\n    result is averaged on that line or through the name it is assigned to, or stored as a mask that indexes a series\n    whose selection is averaged; an indicator averaged into a rate does not count."""\n    nxt = [x.split("#", 1)[0] for x in following]\n    target = re.match(r"\\s*([A-Za-z_]\\w*)\\s*=(?!=)", body)\n    inside = body.rfind("[", 0, m.start()) > body.rfind("]", 0, m.start())\n    if inside:\n        if MEAN.search(body):\n            return True\n        if target:\n            t = re.escape(target.group(1))\n            return any(re.search(rf"\\b{t}\\s*\\.\\s*mean\\(|mean\\(\\s*{t}\\b", x) for x in nxt)\n        return False\n    if target:\n        mask = re.escape(target.group(1))\n        for j, x in enumerate(nxt):\n            if re.search(rf"\\[\\s*{mask}\\s*\\]", x):\n                if MEAN.search(x):\n                    return True\n                sel = re.match(r"\\s*([A-Za-z_]\\w*)\\s*=(?!=)", x)\n                if sel and any(re.search(rf"\\b{re.escape(sel.group(1))}\\s*\\.\\s*mean\\(|mean\\(\\s*{re.escape(sel.group(1))}\\b", y)\n                               for y in nxt[j + 1:]):\n                    return True\n    return False\n\n\ndef es_strict_notes(code: str, history: str, statement: str) -> list[tuple[str, str]]:\n    """(key, message) for a strict tail cut at a VaR-like threshold followed within 8 lines by a mean, in a session that\n    resamples, when the task does not ask for a strict inequality at VaR."""\n    out = []\n    try:\n        hint = RESAMPLE.search(history)\n        if not hint or STRICT_TASK.search(statement or ""):\n            return out\n        lines = code.splitlines()\n        for i, raw in enumerate(lines):\n            body = raw.split("#", 1)[0]\n            if not body.strip() or body.lstrip().startswith(("assert", "print")):\n                continue\n            m = LOSS_STRICT.search(body) or RET_STRICT.search(body)\n            if not m or not THRESH_NAME.search(m.group(2).split("[")[0]):\n                continue\n            if not tail_mean_follows(body, m, lines[i + 1:i + 9]):\n                continue\n            src = body.strip()\n            key = "ES-strict:" + re.sub(r"\\s+", "", src)\n            out.append((key,\n                        f"Check after this cell: line {i + 1} `{src}` takes the tail with a strict inequality, and the losses "\n                        f"here come from resampling ({hint.group(0)}), so several of them can equal VaR exactly. The reference "\n                        "note on VaR/ES says: \\"When losses tie at VaR (resampled or bootstrapped rows, ...), the default is the "\n                        "inclusive mean E[L | L >= VaR]\\"; words such as \\"exceeding VaR\\" do not by themselves ask for the strict "\n                        "mean. Print, for one date, the number of losses equal to VaR and both means, then report the inclusive "\n                        "one unless you can quote a sentence of the task that asks for a strict inequality."))\n    except Exception:\n        return []\n    return out\n', 'rootcause/template_lint.py': 'import ast\nimport glob\nimport os\n\nTAIL = "If the task defines it differently, keep it and say why."\nENTRY = {"main"}\n\n\ndef _file_notes(path: str) -> list:\n    """Static facts about one supplied .py file."""\n    src = open(path, errors="ignore").read()\n    tree = ast.parse(src)\n    lines = src.splitlines()\n    name = os.path.basename(path)\n    defs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}\n    used = set()\n    for n in ast.walk(tree):\n        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):\n            used.add(n.id)\n        elif isinstance(n, ast.Attribute):\n            used.add(n.attr)\n    out = []\n    for k, d in defs.items():\n        if k not in used and k not in ENTRY:\n            out.append(f"{name}: function `{k}` (line {d.lineno}) is defined but never called or referenced in this file. "\n                       f"Check whether the computation it implements is done elsewhere with a different rule. {TAIL}")\n    for n in ast.walk(tree):\n        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in defs):\n            continue\n        params = [a.arg for a in defs[n.func.id].args.posonlyargs + defs[n.func.id].args.args]\n        pairs = [(params[i], a.id) for i, a in enumerate(n.args) if isinstance(a, ast.Name) and i < len(params)]\n        pairs += [(kw.arg, kw.value.id) for kw in n.keywords if kw.arg and isinstance(kw.value, ast.Name)]\n        seen = {}\n        for p, var in pairs:\n            if var in seen and seen[var] != p:\n                code = lines[n.lineno - 1].strip() if n.lineno - 1 < len(lines) else ""\n                out.append(f"{name} line {n.lineno}: `{code}` passes the same variable `{var}` to two different "\n                           f"parameters of `{n.func.id}` (`{seen[var]}` and `{p}`). Check whether each parameter should "\n                           f"receive its own input. {TAIL}")\n            seen.setdefault(var, p)\n    return out\n\n\ndef template_lint_notes(data_dirs: tuple) -> list:\n    """Static notes for task-supplied .py files under the data dirs; never raises."""\n    notes = []\n    try:\n        for root in data_dirs or ():\n            for f in sorted(glob.glob(os.path.join(root, "**", "*.py"), recursive=True)):\n                try:\n                    notes += _file_notes(f)\n                except Exception:\n                    continue\n    except Exception:\n        return []\n    return list(dict.fromkeys(notes))\n', 'rootcause/float_format_check.py': 'import ast\nimport io\nimport math\n\nimport numpy as np\nimport pandas as pd\n\nTAIL = "If the task defines it differently, keep it and say why."\nSHORT_DECIMALS = 4\nZERO_SHARE = 0.5\nQUOTE_MAX = 200\nSUM_TOL_BEFORE = 1e-6\nSUM_TOL_AFTER = 1e-3\n\n\ndef _str_consts(tree) -> dict:\n    """Top-level NAME = \'literal\' assignments."""\n    out = {}\n    for n in tree.body:\n        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):\n            for t in n.targets:\n                if isinstance(t, ast.Name):\n                    out[t.id] = n.value.value\n    return out\n\n\ndef _wrappers(tree) -> dict:\n    """{function: (frame param index, format param name, format param index, default format)} for defs forwarding float_format to to_csv."""\n    out = {}\n    for f in ast.walk(tree):\n        if not isinstance(f, ast.FunctionDef):\n            continue\n        params = [a.arg for a in f.args.args]\n        defaults = dict(zip(params[len(params) - len(f.args.defaults):], f.args.defaults))\n        for n in ast.walk(f):\n            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "to_csv"):\n                continue\n            fmt = next((k.value for k in n.keywords if k.arg == "float_format"), None)\n            recv = n.func.value\n            if not (isinstance(fmt, ast.Name) and fmt.id in params and isinstance(recv, ast.Name) and recv.id in params):\n                continue\n            d = defaults.get(fmt.id)\n            dv = d.value if isinstance(d, ast.Constant) and isinstance(d.value, str) else None\n            out[f.name] = (params.index(recv.id), fmt.id, params.index(fmt.id), dv)\n    return out\n\n\ndef float_format_probes(code: str, prior_code: str = "") -> list:\n    """(frame expression, float_format string, quoted line) for each to_csv call in the cell with a resolvable string float_format.\n\n    Direct calls with a literal or a cell-level string constant are covered, and calls to a wrapper function\n    (defined in this cell or in prior_code, earlier cells joined by a "#--cell--" line) that forwards its float_format\n    parameter to to_csv.\n    """\n    out = []\n    try:\n        tree = ast.parse(code)\n        lines = code.splitlines()\n        consts = _str_consts(tree)\n        wraps = {}\n        for prior in prior_code.split("\\n#--cell--\\n") if prior_code else []:\n            try:\n                wraps.update(_wrappers(ast.parse(prior)))\n            except Exception:\n                continue\n        wraps.update(_wrappers(tree))\n        inner = {id(n) for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name in wraps for n in ast.walk(f)}\n        for n in ast.walk(tree):\n            if not isinstance(n, ast.Call) or id(n) in inner:\n                continue\n            seg = ast.get_source_segment(code, n) or (lines[n.lineno - 1] if 0 < n.lineno <= len(lines) else "")\n            line = " ".join(seg.split())[:QUOTE_MAX]\n            if isinstance(n.func, ast.Attribute) and n.func.attr == "to_csv":\n                fmt = next((k.value for k in n.keywords if k.arg == "float_format"), None)\n                val = None\n                if isinstance(fmt, ast.Constant) and isinstance(fmt.value, str):\n                    val = fmt.value\n                elif isinstance(fmt, ast.Name) and fmt.id in consts:\n                    val = consts[fmt.id]\n                if val is not None:\n                    out.append((ast.unparse(n.func.value), val, line))\n            elif isinstance(n.func, ast.Name) and n.func.id in wraps:\n                fi, fname, fpos, default = wraps[n.func.id]\n                if fi >= len(n.args):\n                    continue\n                val = default\n                kw = next((k.value for k in n.keywords if k.arg == fname), None)\n                if kw is None and fpos < len(n.args):\n                    kw = n.args[fpos]\n                if kw is not None:\n                    val = kw.value if isinstance(kw, ast.Constant) and isinstance(kw.value, str) else consts.get(getattr(kw, "id", None))\n                if isinstance(val, str):\n                    out.append((ast.unparse(n.args[fi]), val, line))\n    except Exception:\n        return []\n    return list(dict.fromkeys(out))\n\n\ndef _apply(fmt: str, v: float):\n    """Value after formatting and reading back, or None when the format does not apply."""\n    try:\n        return float(fmt % v)\n    except Exception:\n        return None\n\n\ndef _close(a: float, b: float) -> bool:\n    return abs(a - b) <= 1e-12 * max(abs(a), abs(b))\n\n\ndef _short(v: float) -> bool:\n    """True when the shortest repr of v has at most SHORT_DECIMALS decimals."""\n    r = repr(float(v))\n    if "e" in r or "n" in r:\n        return False\n    return len(r.split(".")[1].rstrip("0")) <= SHORT_DECIMALS if "." in r else True\n\n\ndef float_format_note(frame_values_csv_unformatted: str, fmt: str, line: str):\n    """Message when float_format alters short decimals, zeroes nonzero values, or breaks a unit sum; else None. Never raises."""\n    try:\n        df = pd.read_csv(io.StringIO(frame_values_csv_unformatted))\n        parts = []\n        for col in df.columns:\n            if not pd.api.types.is_float_dtype(df[col]):\n                continue\n            vals = [float(v) for v in df[col].to_numpy() if math.isfinite(v)]\n            if not vals:\n                continue\n            after = [_apply(fmt, v) for v in vals]\n            if any(a is None for a in after):\n                return None\n            changed = [(v, a) for v, a in zip(vals, after) if _short(v) and not _close(v, a)]\n            if changed:\n                ex = ", ".join(f"{v:g} -> {fmt % v}" for v, _ in list(dict.fromkeys(changed))[:3])\n                parts.append(f"`{col}` {ex}")\n            nonzero = [(v, a) for v, a in zip(vals, after) if v != 0]\n            zeroed = [v for v, a in nonzero if a == 0]\n            if len(zeroed) >= 2 and len(zeroed) >= ZERO_SHARE * len(nonzero):\n                parts.append(f"`{col}` {len(zeroed)} of {len(nonzero)} nonzero values become 0 (e.g. {zeroed[0]:.3g})")\n            s0, s1 = float(np.sum(vals)), float(np.sum(after))\n            if len(vals) >= 2 and abs(s0 - 1) <= SUM_TOL_BEFORE and abs(s1 - 1) > SUM_TOL_AFTER:\n                parts.append(f"`{col}` sums to {s0:.6g} before formatting and {s1:.6g} after")\n        if not parts:\n            return None\n        return (f"`{line}`: float_format={fmt!r} applies to every float column and changes the written values: "\n                f"{\'; \'.join(parts)}. Format only the columns that the task asks to round, at the decimals it states, "\n                f"and leave the others at full precision. {TAIL}")\n    except Exception:\n        return None\n', 's2v2/offering_size.py': 'import html\nimport os\nimport re\n\nAMOUNT = re.compile(r"\\$\\s*(\\d{1,3}(?:,\\d{3})+|\\d+(?:\\.\\d+)?)\\s*(million|billion)?", re.I)\nINCLUDES = re.compile(r"\\binclud(?:e|es|ed)\\b", re.I)\nOPTION = re.compile(r"\\boption\\b|over-?allot|greenshoe", re.I)\nPRINTED = re.compile(r"(?<![\\w.])-?\\d+(?:,\\d{3})*(?:\\.\\d+)?(?![\\w.])")\nDOC_CACHE: dict[tuple, list] = {}\n\n\ndef doc_sentences(path: str) -> list[str]:\n    """Sentences of a text or HTML input document, markup removed."""\n    try:\n        t = open(path, errors="ignore").read()\n    except OSError:\n        return []\n    if path.lower().endswith((".htm", ".html", ".xml")):\n        t = html.unescape(re.sub(r"<[^>]+>", " ", t))\n    t = re.sub(r"\\s+", " ", t)\n    return [s.strip() for s in re.split(r"(?<=[.!?])\\s+", t) if s.strip()]\n\n\ndef amounts(sentence: str) -> list[float]:\n    """Dollar amounts of a sentence, in dollars."""\n    out = []\n    for m in AMOUNT.finditer(sentence):\n        v = float(m.group(1).replace(",", ""))\n        unit = (m.group(2) or "").lower()\n        out.append(v * (1e9 if unit == "billion" else 1e6 if unit == "million" else 1.0))\n    return out\n\n\ndef offering_docs(data_dirs: tuple) -> list:\n    """(total sentence, total, include sentence) for each input document stating a total and, elsewhere, that it includes\n    a smaller amount sold under an option; cached per directory set."""\n    key = tuple(data_dirs)\n    if key in DOC_CACHE:\n        return DOC_CACHE[key]\n    found = []\n    for root in data_dirs:\n        for d, _, names in os.walk(root):\n            for n in sorted(names):\n                if not n.lower().endswith((".htm", ".html", ".txt", ".xml")):\n                    continue\n                sents = doc_sentences(os.path.join(d, n))\n                if sum(len(amounts(s)) for s in sents) < 2:\n                    continue\n                incl = [(s, amounts(s)) for s in sents if INCLUDES.search(s) and OPTION.search(s) and amounts(s)]\n                for s in sents:\n                    for a in amounts(s):\n                        for inc, inc_amts in incl:\n                            if inc != s and any(0 < x < a for x in inc_amts):\n                                found.append((s, a, inc))\n    DOC_CACHE[key] = found\n    return found\n\n\ndef offering_notes(output: str, data_dirs: tuple) -> list[tuple[str, str]]:\n    """(key, message) for each number printed in a cell output that equals such a total, in dollars, thousands, millions or\n    billions."""\n    out = []\n    try:\n        docs = offering_docs(data_dirs)\n        if not docs:\n            return out\n        for m in PRINTED.finditer(output):\n            text = m.group(0)\n            p = float(text.replace(",", ""))\n            if p <= 0:\n                continue\n            for total_sentence, total, include_sentence in docs:\n                if any(abs(p * k - total) <= 1e-9 * total for k in (1.0, 1e3, 1e6, 1e9)):\n                    out.append((f"S2:{total_sentence[:80]}",\n                                f"The document says: \\"{total_sentence}\\" and \\"{include_sentence}\\". Our reference note on "\n                                "offering sizes says: when an issued total is stated to include an amount sold under an "\n                                "underwriters\' or purchasers\' option, the base (pre-option) size is the total minus that "\n                                f"amount. Your value {text} equals the total. Re-derive the base size from these two sentences."))\n                    break\n    except Exception:\n        return out\n    return out\n', 'pandas_hook/pandas_hook.py': '"""Runtime pandas checks (R1 zero label overlap, R3 near-key miss, B6 positional product, C2 duplicate-label lookup)."""\nimport json\n\nMARKER = "<<OC_EVENTS>>"\n\nHOOK_CODE = r\'\'\'\ndef _oc_install():\n    import sys, re, linecache, datetime, functools, weakref\n    import numpy as np\n    import pandas as pd\n    from pandas.core import generic, indexing\n    from pandas.core.indexes.base import Index\n    if getattr(pd, "_oc_installed", False):\n        return\n    # Mutable state lives on the pandas module so the probe can reach it without names in the session.\n    st = {"sites": {}, "b6": {}, "cache": {}, "nan": {}}\n    events = []\n    pd._oc_events = events\n    MAX_EVENTS, MAX_SITES, MAX_LABELS = 50, 400, 50000\n    DATE_STR = re.compile(r"^\\s*\\d{4}-\\d{1,2}(-\\d{1,2})?([ T][\\d:.]*)?\\s*$")\n    INT_STR = re.compile(r"^[+-]?\\d+(\\.0+)?$")\n    POSITIONAL = re.compile(r"np\\.(?:dot|matmul|inner|vdot|multiply|einsum|corrcoef|cov)\\(|@|\\*|\\.dot\\(")\n\n    # True when the frame belongs to a model cell.\n    def in_cell(f):\n        return f is not None and f.f_code.co_filename.startswith("<cell")\n\n    # Site key and source text of a cell frame.\n    def where(f):\n        return f.f_code.co_filename, f.f_lineno\n\n    def src_of(fname, line):\n        try:\n            return linecache.getline(fname, line).strip()[:240]\n        except Exception:\n            return ""\n\n    # Short label list for messages.\n    def show(idx, n=6):\n        try:\n            vals = [str(v) for v in list(idx[:n])]\n            return "[" + ", ".join(vals) + (", ..." if len(idx) > n else "") + "]"\n        except Exception:\n            return "?"\n\n    # Results holding NaN from a flagged site, so a later NaN-to-number step can be tied back to it.\n    def track(obj, sk):\n        if len(st["nan"]) < 500:\n            st["nan"][id(obj)] = (weakref.ref(obj), sk)\n\n    def tracked(obj):\n        t = st["nan"].get(id(obj))\n        return t[1] if t is not None and t[0]() is obj else None\n\n    # ---------------- R1: arithmetic on pandas objects whose labels share nothing ----------------\n    def zero_overlap(a, b):\n        if len(a) < 2 or len(b) < 2 or len(a) > MAX_LABELS or len(b) > MAX_LABELS or a.equals(b):\n            return False\n        try:\n            if any(v in a for v in b[:8]):\n                return False\n        except Exception:\n            pass\n        return len(a.intersection(b)) == 0\n\n    def r1_check(left, right, axis, res, f, reflected):\n        if isinstance(left, pd.Series) and isinstance(right, pd.Series):\n            pairs = [(left.index, right.index)]\n        elif isinstance(left, pd.DataFrame) and isinstance(right, pd.Series):\n            pairs = [(left.index if axis == 0 else left.columns, right.index)]\n        elif isinstance(left, pd.DataFrame) and isinstance(right, pd.DataFrame):\n            pairs = [(left.index, right.index), (left.columns, right.columns)]\n        else:\n            return\n        for a, b in pairs:\n            if zero_overlap(a, b):\n                if reflected:\n                    a, b = b, a\n                fname, line = where(f)\n                key = ("R1", fname, line)\n                rec = st["sites"].get(key)\n                if rec is None:\n                    if len(st["sites"]) >= MAX_SITES:\n                        return\n                    k = m = 0\n                    if isinstance(res, pd.DataFrame):\n                        k, m = int(res.isna().all(axis=1).sum()), len(res)\n                    elif isinstance(res, pd.Series):\n                        k, m = int(res.isna().sum()), len(res)\n                    st["sites"][key] = {"c": "R1", "cell": fname, "line": line, "src": src_of(fname, line), "n_ops": 1,\n                                        "n_left": len(a), "n_right": len(b), "ex_l": show(a), "ex_r": show(b),\n                                        "nan_rows": k, "rows": m, "masked": None}\n                else:\n                    rec["n_ops"] += 1\n                track(res, key)\n                return\n\n    def wrap_op(orig, reflected, flex, is_df):\n        @functools.wraps(orig)\n        def w(self, other, *a, **kw):\n            res = orig(self, other, *a, **kw)\n            try:\n                f = sys._getframe(1)\n                if in_cell(f) and res is not NotImplemented and isinstance(res, (pd.Series, pd.DataFrame)):\n                    sk = tracked(self) or (tracked(other) if isinstance(other, (pd.Series, pd.DataFrame)) else None)\n                    if sk is not None:\n                        track(res, sk)\n                if in_cell(f) and isinstance(other, (pd.Series, pd.DataFrame)) and res is not NotImplemented:\n                    if not (isinstance(self, pd.Series) and isinstance(other, pd.DataFrame)):\n                        axis = 1\n                        if flex:\n                            if kw.get("fill_value") is not None or kw.get("level") is not None or len(a) > 1:\n                                return res\n                            ax = kw.get("axis", a[0] if a else ("columns" if is_df else 0))\n                            axis = 0 if ax in (0, "index", "rows") else 1\n                        r1_check(self, other, axis, res, f, reflected)\n            except Exception:\n                pass\n            return res\n        return w\n\n    for cls, is_df in ((pd.Series, False), (pd.DataFrame, True)):\n        for base in ("add", "sub", "mul", "truediv", "floordiv", "mod", "pow"):\n            for nm, refl in ((f"__{base}__", False), (f"__r{base}__", True)):\n                if hasattr(cls, nm):\n                    setattr(cls, nm, wrap_op(getattr(cls, nm), refl, False, is_df))\n            for nm, refl in ((base, False), ("r" + base, True)):\n                if hasattr(cls, nm):\n                    setattr(cls, nm, wrap_op(getattr(cls, nm), refl, True, is_df))\n        for nm, refl in (("multiply", False), ("subtract", False), ("divide", False), ("div", False), ("rdiv", True)):\n            if hasattr(cls, nm):\n                setattr(cls, nm, wrap_op(getattr(cls, nm), refl, True, is_df))\n\n    # Steps that turn NaN into numbers; mark the flagged site they hide.\n    def wrap_mask(orig, name):\n        @functools.wraps(orig)\n        def w(self, *a, **kw):\n            res = orig(self, *a, **kw)\n            try:\n                f = sys._getframe(1)\n                if in_cell(f):\n                    sk = tracked(self)\n                    if sk is not None and sk in st["sites"]:\n                        rec = st["sites"][sk]\n                        rec["masked"] = rec.get("masked") or name\n                        if isinstance(res, (pd.Series, pd.DataFrame)) and name != "sum":\n                            track(res, sk)\n            except Exception:\n                pass\n            return res\n        return w\n\n    for cls in (pd.Series, pd.DataFrame):\n        for nm in ("sum", "fillna", "cumsum", "prod", "cumprod"):\n            setattr(cls, nm, wrap_mask(getattr(cls, nm), nm))\n\n    # ---------------- R3: a lookup misses although a key differing only in format exists ----------------\n    def as_ts(x):\n        try:\n            if isinstance(x, (bool, np.bool_)):\n                return None\n            if isinstance(x, pd.Timestamp):\n                return x\n            if isinstance(x, (datetime.datetime, datetime.date, np.datetime64)):\n                return pd.Timestamp(x)\n            if isinstance(x, pd.Period):\n                return x.to_timestamp()\n            if isinstance(x, str) and DATE_STR.match(x):\n                return pd.Timestamp(x)\n        except Exception:\n            return None\n        return None\n\n    def naive(t):\n        return t.tz_localize(None) if t.tzinfo is not None else t\n\n    def canon(v):\n        if isinstance(v, (bool, np.bool_)):\n            return None\n        if isinstance(v, (int, np.integer)):\n            return str(int(v))\n        if isinstance(v, (float, np.floating)):\n            return str(int(v)) if float(v).is_integer() else repr(float(v))\n        if isinstance(v, str):\n            s = v.strip().lower()\n            return str(int(float(s))) if INT_STR.match(s) else s\n        return None\n\n    # Per-table maps: month -> [count, first key], wall-clock time -> key, canonical text -> key.\n    def table_info(idx):\n        c = st["cache"].get(id(idx))\n        if c is not None and c[0] is idx:\n            return c[1]\n        if len(st["cache"]) > 64:\n            st["cache"].clear()\n        info = None\n        if 0 < len(idx) <= MAX_LABELS and not isinstance(idx, pd.MultiIndex):\n            info = {"month": {}, "exact": {}, "text": {}, "tz": False}\n            if isinstance(idx, pd.DatetimeIndex):\n                info["tz"] = idx.tz is not None\n                nv = idx.tz_localize(None) if idx.tz is not None else idx\n                ym = np.asarray(nv.year) * 12 + np.asarray(nv.month)\n                for k, v in zip(ym.tolist(), list(idx)):\n                    rec = info["month"].setdefault(k, [0, v])\n                    rec[0] += 1\n                for k, v in zip(list(nv), list(idx)):\n                    info["exact"].setdefault(k, v)\n            else:\n                for v in list(idx):\n                    t = as_ts(v)\n                    if t is not None:\n                        t = naive(t)\n                        info["exact"].setdefault(t, v)\n                        rec = info["month"].setdefault(t.year * 12 + t.month, [0, v])\n                        rec[0] += 1\n                    else:\n                        cv = canon(v)\n                        if cv is not None:\n                            info["text"].setdefault(cv, v)\n        st["cache"][id(idx)] = (idx, info)\n        return info\n\n    # The table key equal to `key` up to format, and what differs; None when there is none.\n    def near(key, idx):\n        info = table_info(idx)\n        if info is None:\n            return None\n        t = as_ts(key)\n        if t is not None and (info["exact"] or info["month"]):\n            nt = naive(t)\n            tk = info["exact"].get(nt)\n            if tk is not None:\n                tz_k = getattr(t, "tzinfo", None) is not None\n                tz_t = getattr(tk, "tzinfo", None) is not None\n                if tz_k != tz_t or (tz_k and str(t.tzinfo) != str(tk.tzinfo)):\n                    return tk, "timezone"\n                return tk, f"type ({type(key).__name__} vs {type(tk).__name__})"\n            rec = info["month"].get(nt.year * 12 + nt.month)\n            if rec is not None and rec[0] == 1:\n                return rec[1], "the day within the same month"\n            return None\n        cv = canon(key)\n        if cv is not None:\n            tk = info["text"].get(cv)\n            if tk is not None and not (type(tk) is type(key) and tk == key):\n                if type(tk) is not type(key) and not (isinstance(tk, str) and isinstance(key, str)):\n                    return tk, f"type ({type(key).__name__} vs {type(tk).__name__})"\n                return tk, "case or whitespace"\n        return None\n\n    def hashable_scalar(k):\n        return isinstance(k, (str, int, float, np.integer, np.floating, pd.Timestamp, datetime.date, np.datetime64, pd.Period))\n\n    # One lookup at a cell line: count it, and on a miss find a format twin.\n    def r3_record(f, kind, key, idx, missed, default=None, needs_mask=False):\n        fname, line = where(f)\n        sk = ("R3", fname, line, kind)\n        rec = st["sites"].get(sk)\n        if rec is None:\n            if len(st["sites"]) >= MAX_SITES:\n                return\n            rec = st["sites"][sk] = {"c": "R3", "kind": kind, "cell": fname, "line": line, "src": src_of(fname, line),\n                                     "n_total": 0, "n_miss": 0, "n_near": 0, "n_far": 0, "map": {}, "clash": False,\n                                     "default": None if default is None else repr(default)[:60],\n                                     "needs_mask": needs_mask, "masked": None}\n        rec["n_total"] += 1\n        if not missed:\n            return sk\n        rec["n_miss"] += 1\n        if rec["n_far"] or rec["clash"]:\n            return sk\n        nk = near(key, idx)\n        if nk is None:\n            rec["n_far"] += 1\n            return sk\n        rec["n_near"] += 1\n        tk_r, k_r = repr(nk[0])[:80], repr(key)[:80]\n        prev = rec["map"].get(tk_r)\n        if prev is not None and prev != k_r:\n            rec["clash"] = True\n        elif len(rec["map"]) < 2000:\n            rec["map"][tk_r] = k_r\n        if "key" not in rec:\n            rec["key"], rec["table_key"], rec["diff"] = k_r, tk_r, nk[1]\n        return sk\n\n    def wrap_index_contains(orig):\n        @functools.wraps(orig)\n        def w(self, key):\n            res = orig(self, key)\n            try:\n                if not res:\n                    f = sys._getframe(1)\n                    if in_cell(f) and hashable_scalar(key):\n                        r3_record(f, "contains", key, self, True)\n                elif in_cell(sys._getframe(1)) and hashable_scalar(key):\n                    r3_record(sys._getframe(1), "contains", key, self, False)\n            except Exception:\n                pass\n            return res\n        return w\n\n    def all_index_classes(c):\n        out = [c]\n        for s in c.__subclasses__():\n            out.extend(all_index_classes(s))\n        return out\n\n    for cls in set(all_index_classes(Index)):\n        if "__contains__" in cls.__dict__ and not issubclass(cls, (pd.MultiIndex, pd.IntervalIndex)):\n            cls.__contains__ = wrap_index_contains(cls.__dict__["__contains__"])\n\n    nd_contains = generic.NDFrame.__contains__\n\n    @functools.wraps(nd_contains)\n    def w_nd_contains(self, key):\n        res = nd_contains(self, key)\n        try:\n            f = sys._getframe(1)\n            if in_cell(f) and hashable_scalar(key):\n                r3_record(f, "contains", key, self._info_axis, not res)\n        except Exception:\n            pass\n        return res\n    generic.NDFrame.__contains__ = w_nd_contains\n\n    nd_get = generic.NDFrame.get\n\n    @functools.wraps(nd_get)\n    def w_get(self, key, default=None):\n        res = nd_get(self, key, default)\n        try:\n            f = sys._getframe(1)\n            if in_cell(f) and hashable_scalar(key):\n                r3_record(f, "get", key, self._info_axis, res is default, default)\n        except Exception:\n            pass\n        return res\n    generic.NDFrame.get = w_get\n\n    s_map = pd.Series.map\n\n    @functools.wraps(s_map)\n    def w_map(self, arg, *a, **kw):\n        res = s_map(self, arg, *a, **kw)\n        try:\n            f = sys._getframe(1)\n            if in_cell(f) and isinstance(arg, (dict, pd.Series)) and not hasattr(arg, "__missing__") and isinstance(res, pd.Series):\n                miss = res.isna().to_numpy() & self.notna().to_numpy()\n                table = arg.index if isinstance(arg, pd.Series) else pd.Index(list(arg.keys()))\n                keys = pd.unique(self.to_numpy()[miss])[:500] if miss.any() else []\n                hit_n = int(len(self) - miss.sum())\n                for _ in range(min(hit_n, 1)):\n                    r3_record(f, "map", None, table, False)\n                sk = None\n                for k in keys:\n                    if hashable_scalar(k):\n                        sk = r3_record(f, "map", k, table, True, None, True) or sk\n                if sk is not None:\n                    track(res, sk)\n        except Exception:\n            pass\n        return res\n    pd.Series.map = w_map\n\n    def wrap_reindex(orig, is_df):\n        @functools.wraps(orig)\n        def w(self, *a, **kw):\n            res = orig(self, *a, **kw)\n            try:\n                f = sys._getframe(1)\n                if in_cell(f) and kw.get("method") is None and kw.get("level") is None and kw.get("limit") is None:\n                    targets = []\n                    lab = a[0] if a else kw.get("labels", kw.get("index"))\n                    ax = kw.get("axis", 0)\n                    if lab is not None:\n                        targets.append((lab, self.columns if (is_df and ax in (1, "columns")) else self.index))\n                    if is_df and kw.get("columns") is not None:\n                        targets.append((kw["columns"], self.columns))\n                    for lab, old in targets:\n                        if isinstance(lab, (pd.MultiIndex,)) or isinstance(old, pd.MultiIndex):\n                            continue\n                        new = pd.Index(lab)\n                        missing = ~new.isin(old)\n                        fill = kw.get("fill_value")\n                        sk = None\n                        for k in new[missing][:500]:\n                            if hashable_scalar(k):\n                                sk = r3_record(f, "reindex", k, old, True, fill if fill is not None else np.nan, fill is None) or sk\n                        if sk is not None:\n                            track(res, sk)\n                        if (~missing).any():\n                            r3_record(f, "reindex", None, old, False)\n            except Exception:\n                pass\n            return res\n        return w\n    pd.Series.reindex = wrap_reindex(pd.Series.reindex, False)\n    pd.DataFrame.reindex = wrap_reindex(pd.DataFrame.reindex, True)\n\n    # ---------------- B6: .values of two labelled objects combined by position on one line ----------------\n    def axes_of(obj):\n        return (obj.index,) if isinstance(obj, pd.Series) else (obj.columns, obj.index)\n\n    def b6_note(f, obj):\n        key = where(f)\n        rec = st["b6"].get(key)\n        if rec is None:\n            if len(st["b6"]) >= MAX_SITES:\n                return\n            rec = st["b6"][key] = []\n        if len(rec) < 16:\n            rec.append((f.f_lasti, axes_of(obj)))\n\n    def wrap_values(prop):\n        fget = prop.fget\n\n        @functools.wraps(fget)\n        def g(self):\n            res = fget(self)\n            try:\n                f = sys._getframe(1)\n                if in_cell(f):\n                    b6_note(f, self)\n            except Exception:\n                pass\n            return res\n        return property(g, prop.fset, prop.fdel, prop.__doc__)\n\n    def wrap_to_numpy(orig):\n        @functools.wraps(orig)\n        def w(self, *a, **kw):\n            res = orig(self, *a, **kw)\n            try:\n                f = sys._getframe(1)\n                if in_cell(f):\n                    b6_note(f, self)\n            except Exception:\n                pass\n            return res\n        return w\n\n    for cls in (pd.Series, pd.DataFrame):\n        cls.values = wrap_values(cls.__dict__["values"])\n        cls.to_numpy = wrap_to_numpy(cls.to_numpy)\n\n    # Same label set in a different order, and no axis pair in the same order.\n    def b6_pair(ax1, ax2):\n        found = None\n        for a in ax1:\n            for b in ax2:\n                if len(a) < 2 or len(a) != len(b) or len(a) > MAX_LABELS:\n                    continue\n                if a.equals(b):\n                    return None\n                if found is None and a.is_unique and b.is_unique and len(a.intersection(b)) == len(a):\n                    found = (a, b)\n        return found\n\n    def b6_events():\n        out = []\n        for (fname, line), rec in st["b6"].items():\n            src = src_of(fname, line)\n            if len(rec) < 2 or not POSITIONAL.search(src):\n                continue\n            for (la, xa), (lb, xb) in zip(rec, rec[1:]):\n                if la == lb:\n                    continue\n                hit = b6_pair(xa, xb) if la < lb else b6_pair(xb, xa)\n                if hit:\n                    out.append({"c": "B6", "cell": fname, "line": line, "src": src, "l": show(hit[0], 12), "r": show(hit[1], 12)})\n                    break\n        return out\n\n    # ---------------- C2: .loc with a list of labels on an index with repeated labels ----------------\n    loc_get = indexing._LocationIndexer.__getitem__\n\n    @functools.wraps(loc_get)\n    def w_loc(self, key):\n        res = loc_get(self, key)\n        try:\n            f = sys._getframe(1)\n            if in_cell(f) and len(events) < MAX_EVENTS:\n                k = key[0] if isinstance(key, tuple) and len(key) == 2 else key\n                if isinstance(k, (list, range, np.ndarray, pd.Index, pd.Series)) and not isinstance(k, str):\n                    arr = np.asarray(k)\n                    idx = self.obj.index\n                    if arr.dtype != bool and len(arr) >= 2 and not idx.is_unique and hasattr(res, "__len__"):\n                        n = len(res)\n                        if n != len(arr):\n                            fname, line = where(f)\n                            if not any(e.get("c") == "C2" and e["cell"] == fname and e["line"] == line for e in events):\n                                events.append({"c": "C2", "cell": fname, "line": line, "src": src_of(fname, line),\n                                               "n_keys": int(len(arr)), "n_rows": int(n),\n                                               "n_dup": int(idx.duplicated().sum()), "index_name": str(idx.name)})\n        except Exception:\n            pass\n        return res\n    indexing._LocIndexer.__getitem__ = w_loc\n\n    # ---------------- drain ----------------\n    def drain():\n        out = list(events)\n        try:\n            for rec in st["sites"].values():\n                if rec.get("needs_mask", rec["c"] == "R1") and not rec.get("masked"):\n                    continue\n                if rec["c"] == "R1":\n                    out.append(rec)\n                elif rec["n_near"] >= 1 and rec["n_far"] == 0 and not rec["clash"] and rec["n_near"] == rec["n_miss"]:\n                    r = {k: v for k, v in rec.items() if k not in ("map", "n_far", "clash")}\n                    out.append(r)\n            out.extend(b6_events())\n        except Exception:\n            pass\n        events.clear()\n        st["sites"].clear()\n        st["b6"].clear()\n        st["cache"].clear()\n        st["nan"].clear()\n        try:\n            return json.dumps(out[:MAX_EVENTS], default=str)\n        except Exception:\n            return "[]"\n\n    import json\n    pd._oc_drain = drain\n    pd._oc_installed = True\n\n\ntry:\n    _oc_install()\nexcept Exception:\n    pass\ndel _oc_install\n\'\'\'\n\nDRAIN_CODE = f\'\'\'\ntry:\n    print({MARKER!r} + __import__("pandas")._oc_drain())\nexcept Exception:\n    pass\n\'\'\'\n\nENDING = "If the task defines it differently, keep it and say why."\n\n\ndef _cell_no(name):\n    return name[len("<cell "):-1] if isinstance(name, str) and name.startswith("<cell ") else "?"\n\n\ndef _line_text(ev, code):\n    """The quoted line: the recorded source if the current cell contains it, else the cell\'s line by number."""\n    src = (ev.get("src") or "").strip()\n    lines = code.splitlines() if code else []\n    if src and any(src == ln.strip() for ln in lines):\n        return src\n    ln = ev.get("line")\n    if isinstance(ln, int) and 1 <= ln <= len(lines) and lines[ln - 1].strip():\n        return lines[ln - 1].strip()\n    return src\n\n\ndef _r1(ev, line):\n    masked = ev.get("masked") or "sum"\n    if masked == "sum":\n        tail = f", and the following `.sum()` turned the all-NaN rows into 0 ({ev[\'nan_rows\']} of {ev[\'rows\']} rows)"\n    else:\n        tail = f" ({ev[\'nan_rows\']} of {ev[\'rows\']} rows), and the following `.{masked}()` replaced those NaN values"\n    return (f"Check after cell {_cell_no(ev[\'cell\'])}: line {ev[\'line\']} `{line}` combined two pandas objects whose labels "\n            f"share 0 of {ev[\'n_left\']} / {ev[\'n_right\']} labels (left: {ev[\'ex_l\']}; right: {ev[\'ex_r\']}). pandas aligns "\n            f"by label, so every element of the result is NaN{tail}. Align the labels before the operation. {ENDING}")\n\n\ndef _r3(ev, line):\n    head = f"Check after cell {_cell_no(ev[\'cell\'])}: line {ev[\'line\']} `{line}`"\n    n, t = ev["n_miss"], ev["n_total"]\n    kind = ev.get("kind")\n    if kind == "get":\n        what = f" used its fallback value {ev.get(\'default\')} for {n} of {t} lookups."\n    elif kind == "map":\n        what = (f" left {n} distinct value(s) unmapped (NaN) and the following `.{ev.get(\'masked\')}()` filled them: "\n                f"the mapping has no entry for them.")\n    elif kind == "reindex" and ev.get("masked"):\n        what = (f" found no entry for {n} requested label(s), and the following `.{ev.get(\'masked\')}()` filled the "\n                f"resulting NaN values.")\n    elif kind == "reindex":\n        what = f" found no entry for {n} requested label(s), so those positions got {ev.get(\'default\')}."\n    else:\n        what = f": the membership test was False for {n} of {t} lookups, so the code took its fallback branch."\n    return (f"{head}{what} Every missed key has a counterpart in the table that differs only in {ev[\'diff\']} "\n            f"(looked up {ev[\'key\']}; the table has {ev[\'table_key\']}). The calculation continued without the table "\n            f"entry. Align the keys before the lookup. {ENDING}")\n\n\ndef _b6(ev, line):\n    return (f"`{line}` multiplies by position. The left side is ordered {ev[\'l\']} while the right side is ordered "\n            f"{ev[\'r\']}; `.values` drops the labels, so each value is paired with another label\'s value. Align by label "\n            f"first and print both index lists. {ENDING}")\n\n\ndef _c2(ev, line):\n    return (f"`{line}` returned {ev[\'n_rows\']} rows for {ev[\'n_keys\']} keys: the index ({ev[\'index_name\']}) has "\n            f"{ev[\'n_dup\']} repeated labels, so each label returns every matching row and the result no longer lines up "\n            f"one-to-one with the keys. Build the lookup from one row per key, check its length equals the number of "\n            f"keys, then use it. {ENDING}")\n\n\n_BUILDERS = {"R1": _r1, "R3": _r3, "B6": _b6, "C2": _c2}\n\n\ndef parse_drain(text):\n    """Events from a probe\'s printed output (the last marker line)."""\n    for ln in reversed((text or "").splitlines()):\n        if ln.startswith(MARKER):\n            try:\n                return json.loads(ln[len(MARKER):])\n            except ValueError:\n                return []\n    return []\n\n\ndef event_notes(events, code):\n    """(dedup_key, message) per event, quoting the cell\'s own line and the event\'s labels/values."""\n    out, seen = [], set()\n    for ev in events or []:\n        try:\n            build = _BUILDERS.get(ev.get("c"))\n            if build is None:\n                continue\n            line = _line_text(ev, code)\n            key = f"{ev[\'c\']}|{line}"\n            if key in seen:\n                continue\n            seen.add(key)\n            out.append((key, build(ev, line)))\n        except Exception:\n            continue\n    return out\n'}
OC7: dict[str, dict] = {}
for _name, _src in OC7_SRC.items():
    try:
        OC7[_name] = dg_module(_src, "oc7_" + _name.replace("/", "_").replace(".py", ""))
    except Exception as _exc:
        print(f"[solver] oc7 check not loaded: {_name}: {type(_exc).__name__}", flush=True)
FF_SHOWN: set[str] = set()
FF_FRAME = re.compile(r"[A-Za-z_][\w.]*(?:\[[^\[\]()]+\])*")
OC7_SHOWN: set[str] = set()
STRUCT_SHOWN: set[tuple[str, str]] = set()
WRITES_FILE = re.compile(r"\.to_csv\(|\.to_json\(|json\.dump|\.to_parquet\(|\.write\(|save_json|open\([^)]*['\"][wa]")


WC_COUNT_KEY = re.compile(r"(?:^|_)(?:num|n|count|number)(?:_|$).*(?:obs|observation|valid|rows|sample|days)|(?:obs|observations|valid_rows)(?:_count)?$", re.I)
WC_WINDOW_KEY = re.compile(r"window|lookback", re.I)


def window_params(data_dirs):
    out = {}
    for d in data_dirs:
        for f in glob.glob(os.path.join(d, "**", "*.json"), recursive=True):
            try:
                j = json.load(open(f))
            except (OSError, ValueError):
                continue
            stack = [j]
            while stack:
                o = stack.pop()
                if isinstance(o, dict):
                    for k, v in o.items():
                        if isinstance(v, (dict, list)):
                            stack.append(v)
                        elif WC_WINDOW_KEY.search(k) and isinstance(v, int) and not isinstance(v, bool) and v > 1:
                            out[k] = v
                elif isinstance(o, list):
                    stack.extend(o)
    return out


def window_count_notes(output_dir, data_dirs):
    wins = window_params(data_dirs)
    if not wins:
        return []
    notes = []
    for f in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
        try:
            j = json.load(open(f))
        except (OSError, ValueError):
            continue
        stack = [("", j)]
        while stack:
            p, o = stack.pop()
            if isinstance(o, dict):
                if set(o) == {"value"}:
                    stack.append((p, o["value"]))
                    continue
                for k, v in o.items():
                    stack.append((f"{p}.{k}" if p else k, v))
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                key = p.split(".")[-1]
                if WC_COUNT_KEY.search(key) and not WC_WINDOW_KEY.search(key):
                    for wk, wv in wins.items():
                        if o == wv:
                            notes.append(f"Output check: `{p}` in {os.path.relpath(f, output_dir)} equals the input "
                                         f"`{wk}` ({wv}). A count of valid observations is every row that survives "
                                         "cleaning; a window only selects the rows used for the statistics. Check which "
                                         "count the task asks for, and keep the two as separate variables.")
    return notes


FX_K15: list = []


def fx_k15_notes(statement: str) -> list[str]:
    if not FX_K15:
        try:
            spec = importlib.util.spec_from_file_location("fx_k15", os.path.join(QFREF_ROOT, "qfref", "fx_k15.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            FX_K15.append(mod)
        except Exception as exc:
            FX_K15.append(None)
            print(f"[solver] fx_k15 not loaded: {type(exc).__name__}", flush=True)
    return FX_K15[0].k15_notes(OUTPUT_DIR, list(DATA_DIRS), statement) if FX_K15[0] is not None else []


def oc7_output_notes() -> list[str]:
    try:
        statement = pathlib.Path(TASK_STATEMENT).read_text()
    except OSError:
        statement = ""
    out = []
    try:
        out += m3_notes()
    except Exception:
        pass
    try:
        out += [x for x in var_variance_notes_now(statement)
                if not any(f"`{f}`" in x for f in VAR_V2_FIELDS)]
    except Exception:
        pass
    try:
        out += OC7['candidate/candidate_checks.py']['dup_dates_notes'](OUTPUT_DIR, "\n".join(SESSION_CODE))
    except Exception:
        pass
    try:
        out += OC7['rootcause/local_vol_identity.py']['local_vol_identity_notes'](OUTPUT_DIR, statement, DATA_DIRS)
    except Exception:
        pass
    try:
        out += OC7['rootcause/swap_npv_sign.py']['swap_npv_sign_notes'](OUTPUT_DIR, statement, DATA_DIRS)
    except Exception:
        pass
    try:
        out += OC7['rootcause/numeric_enum.py']['numeric_enum_notes'](OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += OC7['stable/grid_scalar.py']['grid_scalar_notes'](OUTPUT_DIR, statement, DATA_DIRS)
    except Exception:
        pass
    try:
        out += OC7['stable/date_int.py']['date_int_notes'](OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += OC7['one_item/entity_decor.py']['entity_decor_notes'](OUTPUT_DIR, statement, DATA_DIRS)
    except Exception:
        pass
    try:
        out += OC7['one_item/plural_count.py']['plural_count_notes'](OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += OC7['oc7mid/total_sum.py']['total_sum_notes'](OUTPUT_DIR, statement, DATA_DIRS)
    except Exception:
        pass
    try:
        out += OC7['oc9/oc9_checks.py']['mean_median_notes'](OUTPUT_DIR)
    except Exception:
        pass
    try:
        out += OC7['oc9/oc9_checks.py']['derived_identity_notes'](OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += (OC11M["s1_v2"].set_flag_notes if "s1_v2" in OC11M else OC7['oc9/oc9_checks.py']['set_flag_notes'])(OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += OC7['oc9/oc9_checks.py']['derived_missing_notes'](OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += OC7['oc9/oc9_checks.py']['csv_shape_notes'](OUTPUT_DIR)
    except Exception:
        pass
    try:
        out += OC7['oc9/oc9_checks.py']['selected_param_notes'](OUTPUT_DIR)
    except Exception:
        pass
    try:
        out += [x for x in OC7['oc9/oc9_checks.py']['owner_placeholder_notes'](OUTPUT_DIR, list(DATA_DIRS))
                if p7_first_seen(x)]
    except Exception:
        pass
    try:
        out += OC7['oc10/oc10_checks.py']['sort_order_notes'](OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += OC7['oc10/oc10_checks.py']['ic_gap_notes'](OUTPUT_DIR, statement)
    except Exception:
        pass
    for _fn in (lambda: OC11M["oc11a_checks"].null_key_notes(OUTPUT_DIR),
                lambda: OC11M["key_case_check"].key_case_notes(OUTPUT_DIR, statement, list(DATA_DIRS)),
                lambda: API_LINT.output_notes(OUTPUT_DIR, statement) if API_LINT is not None else [],
                key_name_notes):
        try:
            out += _fn()
        except Exception:
            pass
    try:
        out += triage_notes('pair_order_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        import importlib.util as _ilu, pathlib as _pl
        _p = _pl.Path('/opt/qfref/qfref/symbolic_label_check.py')
        if _p.is_file():
            _spec = _ilu.spec_from_file_location('symbolic_label_check', _p)
            _m = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_m)
            out += _m.symbolic_label_notes(OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('forward_sign_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += window_count_notes(OUTPUT_DIR, list(DATA_DIRS))
    except Exception:
        pass
    try:
        out += fx_k15_notes(statement)
    except Exception:
        pass
    try:
        out += triage_notes('calendar_offset_notes', OUTPUT_DIR, statement, list(DATA_DIRS))
    except Exception:
        pass
    try:
        out += triage_notes('momentum_sharpe_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('cdf_jump_notes', OUTPUT_DIR)
    except Exception:
        pass
    try:
        out += triage_notes('nan_text_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('key_shift_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('parity_notes', OUTPUT_DIR, statement, list(DATA_DIRS))
    except Exception:
        pass
    try:
        out += triage_notes('balance_reference_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('subfit_count_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('id_subset_notes', OUTPUT_DIR, list(DATA_DIRS))
    except Exception:
        pass
    try:
        out += triage_notes('rank_equal_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('scale_ratio_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('sign_double_notes', OUTPUT_DIR, statement, shown=TRIAGE_SHOWN)
    except Exception:
        pass
    try:
        out += triage_notes('method_gap_notes', OUTPUT_DIR, statement)
    except Exception:
        pass
    try:
        out += triage_notes('fx_identity_notes', OUTPUT_DIR, statement, data_dirs=list(DATA_DIRS))
    except Exception:
        pass
    try:
        out += triage_notes('xccy_identity_notes', OUTPUT_DIR, statement, data_dirs=list(DATA_DIRS))
    except Exception:
        pass
    return [x if x.startswith("Output check") else "Output check: " + x for x in out]


def oc7_code_notes(code: str) -> list[str]:
    try:
        statement = pathlib.Path(TASK_STATEMENT).read_text()
    except OSError:
        statement = ""
    history = "\n".join(SESSION_CODE)
    out = []
    try:
        for key, msg in OC7['varES/es_denominator.py']['es_denominator_notes'](code, history, statement):
            if key not in OC7_SHOWN:
                OC7_SHOWN.add(key)
                out.append(msg)
    except Exception:
        pass
    try:
        for key, msg in OC7['candidate/candidate_checks.py']['roll_minus_notes'](code, history, statement):
            if key not in OC7_SHOWN:
                OC7_SHOWN.add(key)
                out.append(msg)
    except Exception:
        pass
    try:
        for key, msg in OC7['candidate/candidate_checks.py']['nobs_len_notes'](code, history, statement, OUTPUT_DIR):
            if key not in OC7_SHOWN:
                OC7_SHOWN.add(key)
                out.append(msg)
    except Exception:
        pass
    try:
        for key, msg in OC7['stable/reset_index_loc.py']['reset_index_loc_notes'](code, history, statement):
            if key not in OC7_SHOWN:
                OC7_SHOWN.add(key)
                out.append(msg)
    except Exception:
        pass
    try:
        for key, msg in OC7['oc7mid/lead_twice.py']['lead_twice_notes'](code, history, statement):
            if key not in OC7_SHOWN:
                OC7_SHOWN.add(key)
                out.append(msg)
    except Exception:
        pass
    try:
        for key, msg in OC7['es_boundary/es_strict.py']['es_strict_notes'](code, history, statement):
            if key not in OC7_SHOWN:
                OC7_SHOWN.add(key)
                out.append(msg)
    except Exception:
        pass
    try:
        oc10 = OC7['oc10/oc10_checks.py']
        for hit in oc10["lag_slice_hits"](code, oc10["inclusive_lag_ranges"](statement)):
            if ("R1:" + hit["array"]) not in OC7_SHOWN:
                OC7_SHOWN.add("R1:" + hit["array"])
                out.append(oc10["lag_slice_note"](hit))
        for tgt, src, line in oc10["future_signal_hits"](code):
            if ("R3:" + line) not in OC7_SHOWN:
                OC7_SHOWN.add("R3:" + line)
                out.append(oc10["future_signal_note"](tgt, src, line))
    except Exception:
        pass
    return out


S2_SHOWN: set[str] = set()


def note_offering(observations: list[dict]) -> list[dict]:
    s2 = OC7.get("s2v2/offering_size.py")
    if s2 is None:
        return observations
    for obs in observations:
        if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
            notes = []
            for key, msg in s2["offering_notes"](warn_obs_text(obs["content"]), DATA_DIRS):
                if key not in S2_SHOWN:
                    S2_SHOWN.add(key)
                    notes.append(msg)
            if notes:
                obs["content"] += "\n\n" + "\n".join(notes)
    return observations


PROBE_SHOWN: set[str] = set()
NAT_READ_PROBE = 'print("K1LOG", __import__("json").dumps(_K1_LOG)); _K1_LOG.clear()'


TRUNCATED_AFTER_REMINDER = 'Your last reply reached the 4,000-token output limit before its tool call was complete, so nothing was run, and few replies remain. In your next reply write exactly one required file -- the one whose values are already computed and checked in the session -- in a cell of at most about 40 lines that only refers to variables already in the session and computes nothing new. Write each remaining file the same way, one per reply, then submit.'


OUTPUT_TREE_TOOL = os.path.join(QFREF_ROOT, "qfref", "check_output_tree.py")
OUTPUT_TREE: list = []
TREE_SHOWN: set[str] = set()
P7_SHOWN: set = set()
TREE_NOTE = ("Output check: the output folder {out} breaks the platform's output folder rules, and a single such problem "
             "makes the whole folder unscorable: {problems}. Delete intermediate files from {out}, or move small ones to /tmp "
             "(which holds at most 64 MiB; keep large intermediate data in memory), so that {out} holds only the required "
             "files.")


def output_tree_problems() -> list[str] | None:
    if not OUTPUT_TREE:
        try:
            spec = importlib.util.spec_from_file_location("check_output_tree", OUTPUT_TREE_TOOL)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            OUTPUT_TREE.append(mod)
        except Exception as exc:
            OUTPUT_TREE.append(None)
            print(f"[solver] output folder rules not loaded: {type(exc).__name__}", flush=True)
    if OUTPUT_TREE[0] is None or not os.path.isdir(OUTPUT_DIR):
        return None
    return OUTPUT_TREE[0].problems(OUTPUT_DIR)


def note_output_tree(observations: list[dict]) -> list[dict]:
    try:
        found = [p for p in (output_tree_problems() or []) if p != "no files" and p not in TREE_SHOWN]
    except Exception:
        return observations
    if found:
        TREE_SHOWN.update(found)
        for obs in observations:
            if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                obs["content"] += "\n\n" + TREE_NOTE.format(out=OUTPUT_DIR, problems="; ".join(found[:8]))
                break
    return observations


def clean_output_tree(required: set[str]) -> None:
    try:
        found = output_tree_problems()
        if not found:
            return
        if not required:
            print(f"[solver] output folder: {len(found)} rule problem(s), required files unknown, nothing removed: "
                  f"{found[:5]}", flush=True)
            return
        for here, dirs, files in os.walk(OUTPUT_DIR, followlinks=False):
            for name in dirs + files:
                path = os.path.join(here, name)
                rel = os.path.relpath(path, OUTPUT_DIR)
                st = os.lstat(path)
                if rel in required:
                    continue
                if stat.S_ISLNK(st.st_mode) or not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
                    os.remove(path)
                    print(f"[solver] output folder: removed link or special file {rel}", flush=True)
                elif stat.S_ISREG(st.st_mode) and (st.st_size > 64 * 2 ** 20 or st.st_nlink > 1):
                    os.remove(path)
                    print(f"[solver] output folder: removed {rel} ({st.st_size} bytes, {st.st_nlink} link(s))", flush=True)
                elif st.st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                    os.chmod(path, stat.S_IMODE(st.st_mode) & ~(stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX))
                    print(f"[solver] output folder: cleared special permission bits on {rel}", flush=True)
            dirs[:] = [d for d in dirs if os.path.isdir(os.path.join(here, d)) and not os.path.islink(os.path.join(here, d))]
        if left := output_tree_problems():
            print(f"[solver] output folder: {len(left)} rule problem(s) left: {left[:5]}", flush=True)
    except Exception as exc:
        print(f"[solver] output folder guard failed: {type(exc).__name__}", flush=True)


def p7_first_seen(note: str) -> bool:
    m = re.match(r'Output check: "(.*?)" is written as an owner value in (.*?)\. In the input', note)
    key = (m.group(1), tuple(sorted(set(re.findall(r"`([^`]+)`", m.group(2)))))) if m else note
    if key in P7_SHOWN:
        return False
    P7_SHOWN.add(key)
    return True


try:
    CURVE = dg_module('import csv, datetime as dt, glob, json, math, os, re, sys\n\nDET = "CURVE-REPRICE"\nSRC = ("Hull, Options Futures and Other Derivatives, ch. \'Interest Rates\' (zero curve bootstrap reprices every input "\n       "instrument); Hagan & West (2006) \'Interpolation methods for curve construction\', Applied Mathematical Finance "\n       "13(2): exact-fit (bootstrap) curves reprice their calibration instruments, best-fit (parametric) curves do not")\nFLOOR_UNIT = 1e-5\nFLOOR_BP = 1e-3\nEPS = sys.float_info.epsilon\nNONBASE_TOK = {"stress", "stressed", "shift", "shifted", "shock", "shocked", "bump", "bumped", "scenario", "scenarios",\n               "up", "down", "parallel", "twist", "steepener", "flattener", "fit", "fitted", "ns", "nelson", "siegel",\n               "svensson", "nss", "smooth", "smoothed", "spline", "comparison", "compare", "alt", "alternative", "pca",\n               "perturbed", "sensitivity", "krd", "stress_test"}\nRX_EXACT = (r"priced at par|par pricing equation|par[- ]bond pricing identity|prices? at exactly|reprice every input|"\n            r"reprices? (each|every|all) (input |calibration )?instruments?|exact(ly)? (fit|reprice)|"\n            r"correct bootstrap (makes|produces)")\nRX_BESTFIT = r"least[- ]squares|minimi[sz]e|best[- ]fit|\\brmse\\b|nelson|svensson|smoothing|regression|fitted curve"\n\n\ndef ev(kind, file, detail, evidence=None):\n    return dict(det=DET, kind=kind, file=file, detail=detail, evidence=evidence or {})\n\n\ndef toks(name):\n    return [t for t in re.split(r"[^a-z0-9]+", os.path.splitext(os.path.basename(str(name)))[0].lower()) if t]\n\n\nRX_NUM = re.compile(r"^[+-]?(\\d+\\.?\\d*|\\.\\d+)([eE][+-]?\\d+)?$")\n\n\ndef half_unit(raw):\n    s = str(raw).strip()\n    if not RX_NUM.match(s):\n        return None\n    mant, _, ex = s.lower().lstrip("+-").partition("e")\n    dec = len(mant.split(".")[1]) if "." in mant else 0\n    return 0.5 * 10.0 ** (int(ex or 0) - dec) + EPS * abs(float(s))\n\n\ndef stated_half_unit(stmt):\n    m = re.search(r"(round(ed)?|precision|accurate)[^.\\n]{0,40}?(\\d+)\\s*(decimal|dp\\b|d\\.p\\.)", stmt, re.I)\n    return 0.5 * 10.0 ** (-int(m.group(3))) if m else None\n\n\ndef unit_err(raw, stated):\n    h = half_unit(raw)\n    if h is None:\n        return None\n    return max(h, stated or 0.0)\n\n\nclass RawF(float):\n    def __new__(cls, raw):\n        x = float.__new__(cls, raw)\n        x.raw = raw\n        return x\n\n\ndef load_json_raw(p):\n    with open(p) as f:\n        return json.load(f, parse_float=RawF, parse_int=RawF)\n\n\ndef read_csv(p):\n    with open(p, newline="") as f:\n        return list(csv.DictReader(f))\n\n\ndef find(data_dir, pattern):\n    hits = sorted(glob.glob(os.path.join(data_dir, "**", pattern), recursive=True))\n    return hits[0] if hits else None\n\n\ndef int_tenor(x):\n    try:\n        v = float(x)\n    except (TypeError, ValueError):\n        return None\n    return int(round(v)) if v >= 1 and abs(v - round(v)) < 1e-12 else None\n\n\ndef blocks(stmt):\n    return re.split(r"\\n\\s*\\n", stmt)\n\n\ndef base_curve_file(stmt, fname):\n    base = os.path.basename(fname)\n    nb = set(toks(base)) & NONBASE_TOK\n    if nb:\n        return False, f"{base} is a stressed/shifted/fitted/comparison curve ({sorted(nb)}), not the base bootstrap curve"\n    if base not in stmt:\n        return False, f"statement does not name {base}; cannot link it to the input quotes"\n    fit = [m.group(0) for b in blocks(stmt) if base in b for m in re.finditer(RX_BESTFIT, b, re.I)]\n    if fit:\n        return False, f"statement block naming {base} describes a best-fit curve ({sorted(set(fit))})"\n    return True, ""\n\n\ndef exact_gate(stmt):\n    return sorted({m.group(0) for m in re.finditer(RX_EXACT, stmt, re.I)})\n\n\ndef df_positive(file, nodes):\n    bad = [(k, v) for k, v in nodes if not (v > 0 and math.isfinite(v))]\n    if bad:\n        return [ev("fired", file, "discount factor <= 0 or non-finite at a curve node",\n                   dict(identity="DF(T) = exp(-z(T) T) > 0 by definition", nodes=bad[:5], source=SRC))]\n    return [ev("ok", file, f"DF > 0 at all {len(nodes)} nodes")]\n\n\ndef verdict(resid, tol, readings_tried):\n    best = min(resid, key=lambda m: abs(resid[m]))\n    if abs(resid[best]) > tol:\n        return "fired", best, "misses under every permitted reading"\n    if best == readings_tried[0]:\n        return "ok", best, "verified under the statement\'s reading"\n    return "ok", best, f"not excluded (passes only under alternative reading \'{best}\')"\n\n\ndef spec_par_json(stmt, out_dir, data_dir):\n    need = {"par pricing equation": r"par pricing equation|priced at par",\n            "schedule t_k = k/freq": r"t_k\\s*=\\s*k\\s*/\\s*freq",\n            "linear zero-rate interpolation": r"interpolate the zero rate|interpolate zero rates linearly",\n            "continuous zero from DF": r"z\\(T\\)\\s*=\\s*-\\s*ln\\(df\\(T\\)\\)\\s*/\\s*T"}\n    miss = [k for k, p in need.items() if not re.search(p, stmt, re.I)]\n    if miss:\n        return None, "spec A not matched: " + ", ".join(miss)\n    inp = None\n    for p in sorted(glob.glob(os.path.join(data_dir, "**", "*.json"), recursive=True)):\n        try:\n            d = json.load(open(p))\n        except (ValueError, OSError):\n            continue\n        if isinstance(d, dict) and {"maturities", "par_rates", "coupon_freq"} <= set(d):\n            inp = d\n    if inp is None:\n        return [ev("skip", "-", "spec A: input JSON with maturities/par_rates/coupon_freq not found")], None\n    stated = stated_half_unit(stmt)\n    res, bases = [], []\n    for p in sorted(glob.glob(os.path.join(out_dir, "*.json"))):\n        try:\n            o = load_json_raw(p)\n        except (ValueError, OSError):\n            continue\n        if not isinstance(o, dict) or not isinstance(o.get("discount_factors"), dict):\n            continue\n        ok, why = base_curve_file(stmt, p)\n        if not ok:\n            res.append(ev("skip", os.path.basename(p), "spec A: " + why))\n            continue\n        bases.append((p, o))\n    if len(bases) != 1:\n        return res + [ev("skip", "-", f"spec A: {len(bases)} base-curve outputs (need exactly one)")], None\n    p, o = bases[0]\n    fn = os.path.basename(p)\n    try:\n        freq = int_tenor(inp["coupon_freq"])\n        T = [float(x) for x in inp["maturities"]]\n        c = [float(x) for x in inp["par_rates"]]\n    except (TypeError, ValueError):\n        return res + [ev("skip", fn, "spec A: non-numeric input")], None\n    if freq is None or len(T) != len(c):\n        return res + [ev("skip", fn, "spec A: coupon_freq not a positive integer or ragged input")], None\n    if any(t <= 0 or abs(round(t * freq) - t * freq) > 1e-9 for t in T):\n        return res + [ev("skip", fn, "spec A: a maturity is not on the regular coupon grid (short first/last period unsupported)")], None\n    dfmap, herr = {}, {}\n    for k, v in o["discount_factors"].items():\n        try:\n            t = float(k)\n        except (TypeError, ValueError):\n            return res + [ev("skip", fn, "spec A: non-numeric discount_factors key")], None\n        if not isinstance(v, RawF):\n            return res + [ev("skip", fn, "spec A: non-numeric discount_factors value")], None\n        dfmap[t], herr[t] = float(v), unit_err(v.raw, stated)\n    if sorted(dfmap) != sorted(T):\n        return res + [ev("skip", fn, "spec A: output DF nodes differ from input maturities")], None\n    res += df_positive(fn, sorted(dfmap.items()))\n    if any(v <= 0 for v in dfmap.values()):\n        return res, None\n    Ts = sorted(T)\n    z = {t: -math.log(dfmap[t]) / t for t in T}\n    dz = {t: herr[t] / (dfmap[t] * t) for t in T}\n\n    def interp(t, mode, n):\n        if t in z:\n            return dfmap[t], herr[t]\n        if t < Ts[0]:\n            return None, None\n        i = max(j for j in range(len(Ts)) if Ts[j] < t)\n        a, b = Ts[i], Ts[i + 1]\n        w = (t - a) / (b - a)\n        if mode == "solved_segment_flat" and b == T[n]:\n            d = math.exp(-z[a] * t)\n            return d, d * t * dz[a]\n        d = math.exp(-((1 - w) * z[a] + w * z[b]) * t)\n        return d, d * t * ((1 - w) * dz[a] + w * dz[b])\n    readings = ["linear_zero", "solved_segment_flat"]\n    for n, (Tn, cn) in enumerate(zip(T, c)):\n        times = [k / freq for k in range(1, int(round(Tn * freq)) + 1)]\n        cfs = [cn / freq] * len(times)\n        cfs[-1] += 1.0\n        on_nodes = all(t in z for t in times)\n        resid, prop = {}, {}\n        for m in (readings[:1] if on_nodes else readings):\n            vals = [interp(t, m, n) for t in times]\n            if any(d is None for d, _ in vals):\n                continue\n            resid[m] = sum(cf * d for cf, (d, _) in zip(cfs, vals)) - 1.0\n            prop[m] = sum(abs(cf) * e for cf, (_, e) in zip(cfs, vals))\n        if not resid:\n            res.append(ev("skip", fn, f"spec A: T={Tn:g} needs extrapolation before first node (undefined)"))\n            continue\n        tol = max(FLOOR_UNIT, max(prop.values()))\n        kind, best, note = verdict(resid, tol, readings)\n        evd = dict(file=fn, instrument=f"par bond T={Tn:g} coupon={cn} freq={freq}", quote=1.0,\n                   residual={m: r for m, r in resid.items()}, propagated_rounding=max(prop.values()), floor=FLOOR_UNIT,\n                   tol=tol, reading_sensitivity=(max(resid.values()) - min(resid.values())) if len(resid) > 1 else 0.0,\n                   identity="1 = (c/freq) * sum_k DF(t_k) + DF(T)", source=SRC, nodes_only=on_nodes, note=note,\n                   abs_resid=abs(resid[best]))\n        res.append(ev(kind, fn, f"par bond T={Tn:g}: {note}", evd))\n    return res, None\n\n\ndef spec_par_annual_csv(stmt, out_dir, data_dir):\n    need = {"bootstrap": r"bootstrap", "par-bond identity": r"par[- ]bond pricing identity|par bond prices at exactly 1",\n            "annual coupons": r"pay \\*\\*annual\\*\\* coupons|annual coupons",\n            "settlement on valuation date": r"settlement on valuation date"}\n    miss = [k for k, p in need.items() if not re.search(p, stmt, re.I)]\n    if miss:\n        return None, "spec B not matched: " + ", ".join(miss)\n    py = find(data_dir, "par_yields.csv")\n    dfp = os.path.join(out_dir, "discount_factors.csv")\n    if not py or not os.path.exists(dfp):\n        return [ev("skip", "discount_factors.csv", "spec B: par_yields.csv or discount_factors.csv missing")], None\n    ok, why = base_curve_file(stmt, dfp)\n    if not ok:\n        return [ev("skip", "discount_factors.csv", "spec B: " + why)], None\n    stated = stated_half_unit(stmt)\n    try:\n        qrows, rows = read_csv(py), read_csv(dfp)\n        qt = [(int_tenor(r["maturity_years"]), float(r["par_yield"])) for r in qrows]\n        dt_ = [(int_tenor(r["maturity_years"]), float(r["discount_factor"]), unit_err(r["discount_factor"], stated)) for r in rows]\n    except (KeyError, ValueError, TypeError):\n        return [ev("skip", "discount_factors.csv", "spec B: unexpected columns")], None\n    if any(t is None for t, _ in qt) or any(t is None or h is None for t, _, h in dt_):\n        return [ev("skip", "discount_factors.csv", "spec B: non-integer tenor (e.g. 1.5Y) or non-numeric DF; "\n                                                   "short/odd coupon periods unsupported")], None\n    if len({t for t, _ in qt}) != len(qt) or len({t for t, _, _ in dt_}) != len(dt_):\n        return [ev("skip", "discount_factors.csv", "spec B: duplicate tenor")], None\n    q = dict(qt)\n    d = {t: v for t, v, _ in dt_}\n    h = {t: e for t, _, e in dt_}\n    res = df_positive("discount_factors.csv", sorted(d.items()))\n    if any(v <= 0 for v in d.values()):\n        return res, None\n    for T, y in sorted(q.items()):\n        if any(k not in d for k in range(1, T + 1)):\n            res.append(ev("skip", "discount_factors.csv", f"spec B: node missing for T={T}"))\n            continue\n        cf = [y] * T\n        cf[-1] += 1.0\n        rep = sum(cc * d[k] for k, cc in zip(range(1, T + 1), cf))\n        prop = sum(abs(cc) * h[k] for k, cc in zip(range(1, T + 1), cf))\n        tol = max(FLOOR_UNIT, prop)\n        evd = dict(file="discount_factors.csv", instrument=f"par bond T={T} annual coupon={y}", quote=1.0,\n                   residual=rep - 1.0, propagated_rounding=prop, floor=FLOOR_UNIT, tol=tol,\n                   identity="1 = y_T * sum_{k<=T} DF(k) + DF(T)", source=SRC, nodes_only=True, abs_resid=abs(rep - 1))\n        res.append(ev("fired" if abs(rep - 1) > tol else "ok", "discount_factors.csv", f"par bond T={T}", evd))\n    bp, ba = find(data_dir, "bonds.csv"), os.path.join(out_dir, "bond_analytics.csv")\n    if bp and os.path.exists(ba) and "bond_analytics.csv" in stmt and re.search(\n            r"price\\*\\* using the bootstrapped discount factors|price using the bootstrapped", stmt, re.I):\n        try:\n            bonds = {r["bond_id"]: r for r in read_csv(bp)}\n            for r in read_csv(ba):\n                b = bonds.get(str(r["bond_id"]).strip())\n                if b is None:\n                    res.append(ev("skip", "bond_analytics.csv", f"spec B: bond {r[\'bond_id\']} not in input"))\n                    continue\n                F, cpn, M = float(b["face_value"]), float(b["coupon_rate"]), int_tenor(b["maturity_years"])\n                hp = half_unit(r["price"])\n                if M is None or hp is None or any(k not in d for k in range(1, M + 1)):\n                    res.append(ev("skip", "bond_analytics.csv", f"spec B: bond {r[\'bond_id\']} non-integer maturity or cash flows off nodes"))\n                    continue\n                unit = sum(cpn * d[k] for k in range(1, M + 1)) + d[M]\n                uerr = sum(cpn * h[k] for k in range(1, M + 1)) + h[M]\n                rep = float(r["price"])\n                diffs = {s: rep - s * unit for s in (F, 100.0, 1.0)}\n                s = min(diffs, key=lambda k: abs(diffs[k]))\n                prop = hp + s * uerr\n                tol = max(FLOOR_UNIT * s, prop)\n                evd = dict(file="bond_analytics.csv", instrument=f"bond {r[\'bond_id\']} F={F:g} c={cpn} M={M}",\n                           quote=f"reported price {rep}", residual=diffs[s], scale=s, propagated_rounding=prop,\n                           floor=FLOOR_UNIT * s, tol=tol, abs_resid=abs(diffs[s]) / s,\n                           identity="price = sum_k CF_k * DF(t_k) on the bootstrapped curve (statement Step 2)",\n                           source=SRC, nodes_only=True)\n                res.append(ev("fired" if abs(diffs[s]) > tol else "ok", "bond_analytics.csv",\n                              f"bond {r[\'bond_id\']} price vs repricing", evd))\n        except (KeyError, ValueError, TypeError):\n            res.append(ev("skip", "bond_analytics.csv", "spec B: unexpected bond columns"))\n    lp, la = find(data_dir, "liability.json"), os.path.join(out_dir, "liability_analytics.json")\n    if lp and os.path.exists(la) and "liability_analytics.json" in stmt and re.search(r"same bootstrapped curve", stmt, re.I) \\\n            and re.search(r"PV of the liability", stmt, re.I):\n        try:\n            cfs = [(int_tenor(x["years"]), float(x["amount"])) for x in json.load(open(lp))["cash_flows"]]\n            pv = load_json_raw(la)["pv_liability"]\n            hp = half_unit(pv.raw)\n            if all(t is not None and t in d for t, _ in cfs) and hp is not None:\n                rep = sum(a * d[t] for t, a in cfs)\n                prop = hp + sum(abs(a) * h[t] for t, a in cfs)\n                tol = max(FLOOR_UNIT * abs(rep), prop)\n                evd = dict(file="liability_analytics.json", instrument="liability cash-flow schedule",\n                           quote=f"reported pv_liability {float(pv)}", residual=float(pv) - rep, propagated_rounding=prop,\n                           floor=FLOOR_UNIT * abs(rep), tol=tol, abs_resid=abs(float(pv) - rep) / max(abs(rep), 1e-300),\n                           identity="PV = sum_k CF_k * DF(t_k) on the same bootstrapped curve (statement Step 3)",\n                           source=SRC, nodes_only=True)\n                res.append(ev("fired" if abs(float(pv) - rep) > tol else "ok", "liability_analytics.json", "liability PV", evd))\n            else:\n                res.append(ev("skip", "liability_analytics.json", "spec B: liability cash flows off integer nodes"))\n        except (KeyError, ValueError, TypeError, AttributeError):\n            res.append(ev("skip", "liability_analytics.json", "spec B: unexpected liability format"))\n    return res, None\n\n\ndef last_feb(d):\n    return d.month == 2 and (d + dt.timedelta(days=1)).month == 3\n\n\ndef dc_30360_us(a, b):\n    d1, d2 = a.day, b.day\n    if last_feb(a) and last_feb(b):\n        d2 = 30\n    if last_feb(a):\n        d1 = 30\n    if d2 == 31 and d1 >= 30:\n        d2 = 30\n    if d1 == 31:\n        d1 = 30\n    return ((b.year - a.year) * 360 + (b.month - a.month) * 30 + (d2 - d1)) / 360.0\n\n\ndef dc_30e360(a, b):\n    d1, d2 = min(a.day, 30), min(b.day, 30)\n    return ((b.year - a.year) * 360 + (b.month - a.month) * 30 + (d2 - d1)) / 360.0\n\n\nDC30 = {"30/360 US": dc_30360_us, "30E/360": dc_30e360}\n\n\ndef variant_30360(text):\n    us = re.search(r"30/360\\s*\\(?\\s*(US|U\\.S\\.|SIA|NASD)\\b|30U/360", text, re.I)\n    eu = re.search(r"30E/360(?!\\s*\\(?\\s*ISDA)|30/360\\s*\\(?\\s*(European|Eurobond|ICMA|ISMA)\\b|eurobond basis", text, re.I)\n    if bool(us) == bool(eu):\n        return None\n    return "30/360 US" if us else "30E/360"\n\n\ndef ymd(s):\n    return dt.date.fromisoformat(str(s).strip()[:10])\n\n\ndef add_months(d, m):\n    y, mo = divmod(d.month - 1 + m, 12)\n    y += d.year\n    mo += 1\n    last = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]\n    return dt.date(y, mo, min(d.day, last))\n\n\ndef spot_date(v, lag):\n    d, n = v, 0\n    while n < lag:\n        d += dt.timedelta(days=1)\n        if d.weekday() < 5:\n            n += 1\n    return d\n\n\nclass LogLinCurve:\n    def __init__(self, val, pts):\n        self.v = val\n        self.p = sorted(((d - val).days / 365.25, df) for d, df in pts)\n\n    def __call__(self, d):\n        t = (d - self.v).days / 365.25\n        if t <= 0:\n            return 1.0\n        p = self.p\n        if t <= p[0][0]:\n            return math.exp(math.log(p[0][1]) / p[0][0] * t)\n        if t >= p[-1][0]:\n            return math.exp(math.log(p[-1][1]) / p[-1][0] * t)\n        for (t0, d0), (t1, d1) in zip(p, p[1:]):\n            if t0 <= t <= t1:\n                w = (t - t0) / (t1 - t0)\n                return math.exp((1 - w) * math.log(d0) + w * math.log(d1))\n\n\ndef schedule(eff, mat, months):\n    ds, k = [mat], 1\n    while True:\n        d = add_months(mat, -months * k)\n        if d <= eff:\n            break\n        ds.append(d)\n        k += 1\n    return [eff] + ds[::-1], d == eff\n\n\ndef spec_single_payment(stmt, out_dir, data_dir):\n    need = {"single-payment DF formula": r"D\\(T\\)\\s*=\\s*1\\s*/\\s*\\(1\\s*\\+\\s*rate\\s*\\*\\s*tau_ACT_360\\)",\n            "log-linear DF interpolation": r"log-linear in `?time_years_ACT_365_25",\n            "conventions file is source of truth": r"conventions\\.json"}\n    miss = [k for k, p in need.items() if not re.search(p, stmt, re.I)]\n    if miss:\n        return None, "spec C not matched: " + ", ".join(miss)\n    cp = find(data_dir, "conventions.json")\n    oq, dq, iq = find(data_dir, "ois_quotes.csv"), find(data_dir, "deposits.csv"), find(data_dir, "irs_3m_quotes.csv")\n    oc, lc = os.path.join(out_dir, "ois_discount_curve.csv"), os.path.join(out_dir, "libor_forward_curve.csv")\n    if not (cp and oq and dq and iq) or not (os.path.exists(oc) and os.path.exists(lc)):\n        return [ev("skip", "ois_discount_curve.csv", "spec C: conventions/quotes or curve outputs missing")], None\n    for f in (oc, lc):\n        ok, why = base_curve_file(stmt, f)\n        if not ok:\n            return [ev("skip", os.path.basename(f), "spec C: " + why)], None\n    conv = json.load(open(cp))\n    stated = stated_half_unit(stmt)\n    try:\n        ok_conv = (conv["ois"]["day_count"] == "ACT/360" and conv["deposits"]["day_count"] == "ACT/360"\n                   and conv["irs_3m"]["float_leg"]["day_count"] == "ACT/360"\n                   and conv["payment_date_convention"] == "unadjusted"\n                   and "log_linear" in conv["interpolation"]["ois_discount_factor"]\n                   and "log_linear" in conv["interpolation"]["libor_discount_factor"])\n        fixed_dc = str(conv["irs_3m"]["fixed_leg"]["day_count"])\n        val = ymd(conv["valuation_date"])\n        spot = spot_date(val, int(conv.get("spot_lag_business_days", 0)))\n        fm, flm = int(conv["irs_3m"]["fixed_leg"]["frequency_months"]), int(conv["irs_3m"]["float_leg"]["frequency_months"])\n    except (KeyError, ValueError, TypeError):\n        return [ev("skip", "-", "spec C: conventions.json lacks a required field")], None\n    if not ok_conv:\n        return [ev("skip", "-", "spec C: conventions differ from the implemented ones")], None\n    try:\n        orow, lrow = read_csv(oc), read_csv(lc)\n        ois = [(ymd(r["pillar_date"]), float(r["discount_factor"]), unit_err(r["discount_factor"], stated)) for r in orow]\n        lib = [(ymd(r["pillar_date"]), float(r["libor_discount_factor"]), unit_err(r["libor_discount_factor"], stated)) for r in lrow]\n    except (KeyError, ValueError, TypeError):\n        return [ev("skip", "ois_discount_curve.csv", "spec C: unexpected curve columns")], None\n    if any(h is None for _, _, h in ois + lib):\n        return [ev("skip", "ois_discount_curve.csv", "spec C: non-numeric discount factor text")], None\n    res = df_positive("ois_discount_curve.csv", [(str(d), v) for d, v, _ in ois])\n    res += df_positive("libor_forward_curve.csv", [(str(d), v) for d, v, _ in lib])\n    if any(v <= 0 for _, v, _ in ois + lib):\n        return res, None\n    om, lm = {d: (v, h) for d, v, h in ois}, {d: (v, h) for d, v, h in lib}\n    for fname, qp, col, nodes, kind in (("ois_discount_curve.csv", oq, "par_rate", om, "OIS"),\n                                        ("libor_forward_curve.csv", dq, "rate", lm, "deposit")):\n        for r in read_csv(qp):\n            m, rate = ymd(r["maturity_date"]), float(r[col])\n            if m not in nodes:\n                res.append(ev("skip", fname, f"spec C: {kind} {r[\'tenor_label\']} maturity is not a curve node"))\n                continue\n            dfv, h = nodes[m]\n            resid = {s: dfv * (1 + rate * (m - st).days / 360.0) - 1 for s, st in (("from_valuation", val), ("from_spot", spot))}\n            prop = h * (1 + abs(rate) * (m - val).days / 360.0)\n            tol = max(FLOOR_UNIT, prop)\n            kind_, best, note = verdict(resid, tol, ["from_valuation", "from_spot"])\n            note = note if best != "from_valuation" else "not excluded (accrual start not fixed by the statement)"\n            evd = dict(file=fname, instrument=f"{kind} {r[\'tenor_label\']} {m} rate={rate}", quote=1.0,\n                       residual=resid, propagated_rounding=prop, floor=FLOOR_UNIT, tol=tol, note=note,\n                       identity="DF(T) * (1 + r * tau_ACT/360) = 1", source=SRC, nodes_only=True,\n                       abs_resid=abs(resid[best]))\n            res.append(ev(kind_, fname, f"{kind} {r[\'tenor_label\']}: {note}", evd))\n    variant = variant_30360(fixed_dc + "\\n" + stmt)\n    oc_f, lc_f = LogLinCurve(val, [(d, v) for d, v, _ in ois]), LogLinCurve(val, [(d, v) for d, v, _ in lib])\n    for r in read_csv(iq):\n        m, rate = ymd(r["maturity_date"]), float(r["par_rate"])\n        pars, regular, coincide = {}, True, True\n        for s, eff in (("from_spot", spot), ("from_valuation", val)):\n            fx, rx = schedule(eff, m, fm)\n            fl, rl = schedule(eff, m, flm)\n            regular &= rx and rl\n            coincide &= all(dc_30360_us(a, b) == dc_30e360(a, b) for a, b in zip(fx, fx[1:]))\n            flt = sum((lc_f(a) / lc_f(b) - 1) * oc_f(b) for a, b in zip(fl, fl[1:]))\n            for vn, fdc in DC30.items():\n                pars[f"{vn}|{s}"] = flt / sum(fdc(a, b) * oc_f(b) for a, b in zip(fx, fx[1:]))\n        resid_bp = {k: (v - rate) * 1e4 for k, v in pars.items()}\n        evd = dict(file="libor_forward_curve.csv", instrument=f"IRS 3M {r[\'tenor_label\']} {m} par={rate}", quote=rate,\n                   residual_bp=resid_bp, identity="par = sum tau_j F_j DF_OIS(s_j) / sum tau_i DF_OIS(t_i)", source=SRC,\n                   variants_coincide_on_all_periods=coincide, fixed_day_count_text=fixed_dc)\n        reasons = []\n        if variant is None:\n            reasons.append(f"fixed-leg day count \'{fixed_dc}\' does not name a 30/360 variant (US with Feb EOM, or 30E/360)")\n        if not regular:\n            reasons.append("schedule has a short first period (stub) under the backward rule; stubs unsupported")\n        if reasons:\n            res.append(ev("skip", "libor_forward_curve.csv", f"spec C: IRS {r[\'tenor_label\']}: " + "; ".join(reasons)))\n            if min(abs(x) for x in resid_bp.values()) > FLOOR_BP:\n                res.append(ev("candidate", "libor_forward_curve.csv", f"IRS {r[\'tenor_label\']}",\n                              dict(evd, uncertain="; ".join(reasons))))\n            continue\n        sub = {k: v for k, v in resid_bp.items() if k.startswith(variant + "|")}\n        tol_bp = FLOOR_BP\n        kind_, best, note = verdict(sub, tol_bp, [f"{variant}|from_spot", f"{variant}|from_valuation"])\n        res.append(ev(kind_, "libor_forward_curve.csv", f"IRS {r[\'tenor_label\']}: {note}",\n                      dict(evd, tol_bp=tol_bp, note=note, abs_resid=abs(sub[best]) * 1e-4)))\n    return res, None\n\n\nSPECS = [spec_par_json, spec_par_annual_csv, spec_single_payment]\n\n\ndef run_check(out_dir, stmt, data_dir):\n    if not stmt:\n        return [ev("skip", "-", "no statement")]\n    if not (re.search(r"bootstrap", stmt, re.I) and re.search(r"discount factor|discount curve|zero curve|zero-coupon", stmt, re.I)):\n        return [ev("n/a", "-", "gate closed: statement does not bootstrap a discount curve")]\n    exact = exact_gate(stmt)\n    if not exact:\n        return [ev("skip", "-", "statement does not require the curve to reprice its calibration instruments exactly")]\n    reasons = []\n    for f in SPECS:\n        r, why = f(stmt, out_dir, data_dir)\n        if r is not None:\n            for e in r:\n                e["evidence"].setdefault("exact_fit_phrases", exact)\n            return r\n        reasons.append(why)\n    return [ev("skip", "-", "bootstrap statement but no fully specified instrument family: " + " | ".join(reasons))]\n\n\nREADING_TEXT = {"linear_zero": "zero rates linearly interpolated between nodes",\n                "solved_segment_flat": "the zero rate held flat on the segment being solved",\n                "log_linear_df": "log-linear interpolation of discount factors"}\n\n\ndef _join(xs):\n    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]\n\n\ndef _label(e):\n    inst = e["evidence"].get("instrument", e["file"])\n    m = re.search(r"T=([0-9.]+)", inst)\n    if m and not isinstance(e["evidence"].get("quote"), str):\n        return f"T={m.group(1)}"\n    return re.split(r" (?:F|T|M|rate|par|annual|coupon)=", inst)[0]\n\n\ndef _primary_residual(e):\n    r = e["evidence"].get("residual")\n    return next(iter(r.values())) if isinstance(r, dict) else r\n\n\ndef _unit_text(e):\n    q = e["evidence"].get("quote")\n    if q == 1.0:\n        return "per unit of face value"\n    if isinstance(q, str):\n        return "in the units of the reported value"\n    return "in the units of the quoted rate"\n\n\nMAX_LISTED = 4\n\n\ndef _miss_text(e):\n    r = _primary_residual(e)\n    if isinstance(e["evidence"].get("quote"), str):\n        return f"the reported {_label(e)} value is {abs(r):.3g} {\'above\' if r > 0 else \'below\'} the value recomputed from your own discount factors"\n    return f"{_label(e)} reprices {abs(r):.3g} {_unit_text(e)} {\'above\' if r > 0 else \'below\'} its quote"\n\n\ndef _order_key(e):\n    m = re.search(r"T=([0-9.]+)", e["evidence"].get("instrument", ""))\n    return float(m.group(1)) if m else float("inf")\n\n\ndef repricing_note(events, reading=None):\n    fired = [e for e in events if e["kind"] == "fired" and _primary_residual(e) is not None]\n    if not fired:\n        return None\n    ok = [e for e in events if e["kind"] == "ok" and "instrument" in e["evidence"]]\n    phrases = next((e["evidence"].get("exact_fit_phrases") for e in fired if e["evidence"].get("exact_fit_phrases")), [])\n    files = sorted({e["evidence"].get("file", e["file"]) for e in fired})\n    how = READING_TEXT.get(reading or next((k for e in fired if isinstance(e["evidence"].get("residual"), dict)\n                                            for k in e["evidence"]["residual"]), ""), "")\n    misses = [_miss_text(e) for e in fired[:MAX_LISTED]]\n    if len(fired) > MAX_LISTED:\n        misses.append(f"{len(fired) - MAX_LISTED} more")\n    text = f"Curve check on {_join(files)}"\n    text += f" (the task says \\"{phrases[0]}\\"): " if phrases else ": "\n    text += "repricing the input instruments on the curve as written" + (f" (with {how}, as the task states)" if how else "")\n    text += " gives " + (f"their quotes for {_join([_label(e) for e in ok][:MAX_LISTED] + ([f\'{len(ok) - MAX_LISTED} more\'] if len(ok) > MAX_LISTED else []))} but not for " if ok else "a miss for ")\n    text += _join([_label(e) for e in fired][:MAX_LISTED] + ([f"{len(fired) - MAX_LISTED} more"] if len(fired) > MAX_LISTED else [])) + ": " + _join(misses) + ", far beyond the rounding of the written values."\n    ordered = sorted(ok + fired, key=_order_key)\n    grows = False\n    if all(_order_key(e) < float("inf") for e in ordered) and len(fired) > 1:\n        first_bad = next(i for i, e in enumerate(ordered) if e in fired)\n        sizes = [abs(_primary_residual(e)) for e in sorted(fired, key=_order_key)]\n        if first_bad > 0 and all(e in fired for e in ordered[first_bad:]) and sizes == sorted(sizes):\n            grows = True\n            text += f" The misses start at {_label(ordered[first_bad])}, after the nodes that reprice, and grow with maturity."\n    if all(isinstance(e["evidence"].get("quote"), str) for e in fired):\n        text += (" The curve itself reprices its inputs, so these values were not computed from it. Common causes: a value "\n                 "computed from an earlier or different curve and not recomputed, a cash flow or coupon date left out, a "\n                 "clean versus dirty price or a face-value scaling difference, or a discount factor taken at the wrong date. "\n                 f"Check which applies in your code, recompute the values from the curve you wrote, and rewrite {_join(files)}. "\n                 "If the task defines these values differently, quote that sentence and keep it.")\n        return text\n    if grows:\n        text += (" That pattern usually means the cash-flow dates between nodes were not valued from the curve, for "\n                 "example a discount factor that was not yet known being taken as 0 or as a stale value. Under the stated "\n                 "interpolation those discount factors depend on the node being solved, so solve each node together with "\n                 "its segment: one node at a time, use a scalar root finder such as scipy.optimize.brentq on that node\'s "\n                 "pricing equation, rebuilding the curve with the trial node inside the function it solves. Other possible causes: an accrual or day count that differs from the stated "\n                 "convention, or interpolating a different quantity than the task states.")\n    else:\n        text += (" Common causes of a bootstrap that does not reprice its inputs: cash-flow dates between nodes valued "\n                 "without the curve (a missing discount factor defaulting to a constant such as 0 or 1, or a stale node); "\n                 "a node solved as if those in-between discount factors were known, when under the stated interpolation "\n                 "they depend on the node being solved (solve the node and its segment together, for example with a root "\n                 "finder on the pricing equation); an accrual or day count that differs from the stated convention; or "\n                 "interpolating a different quantity than the task states.")\n    text += (f" Check which applies in your code, re-solve the nodes, and rewrite {_join(files)}. If the task defines "\n             "the pricing differently, quote that sentence and keep it.")\n    return text\n', "oc11_curve_check_v2")
except Exception as _exc:
    CURVE = None
    print(f"[solver] curve check not loaded: {type(_exc).__name__}", flush=True)
CURVE_SHOWN: set = set()


def note_curve_reprice(message: dict, observations: list[dict]) -> list[dict]:
    code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                            else tc["function"].get("arguments") or {}).get("code") or "")
                      for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
    if CURVE is None or not WRITES_FILE.search(code) or K2C_THIS_COMMAND:
        return observations
    try:
        statement = pathlib.Path(TASK_STATEMENT).read_text()
        data_dir = next((d for d in DATA_DIRS if os.path.isdir(d)), DATA_DIRS[0] if DATA_DIRS else "")
        events = CURVE["run_check"](OUTPUT_DIR, statement, data_dir)
        key = tuple(sorted((e["file"], e["detail"]) for e in events if e["kind"] == "fired"))
        note = CURVE["repricing_note"](events) if key and key not in CURVE_SHOWN else None
    except Exception:
        return observations
    if note:
        CURVE_SHOWN.add(key)
        for obs in observations:
            if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                obs["content"] += "\n\n" + note
                break
    return observations


T1_NOTE = ("Your last {n} replies were all cut off at the 4,000-token output limit, so nothing ran; sending the same cell again "
           "will be cut off again. These functions and data already exist in the session from cells that ran: {names}. Do not "
           "redefine them or reload the data. In your next reply send only the next step, at most 60 lines, that calls them "
           "\u2014 for example, write {first_missing_file} from variables already in the session.")
TRUNC_VERSION = None
TRUNC: dict = {}
exec(compile('import ast, json, re\n\nPLACEHOLDER = ("[This reply was cut off at the 4,000-token output limit before its tool call was complete. Nothing in it was "\n               "run. It began: {first}; length: {length}.]")\nPLACEHOLDER_V3 = ("[This reply was cut off at the 4,000-token output limit before its tool call was complete. Its complete "\n                  "function definitions {defs} were run and now exist in the session; everything after `{last}` was not run. "\n                  "It began: {first}; length: {length}.]")\nSPLIT = ("Your previous reply was cut off (see the note above). Do not send it again: the same cell will be cut off again. "\n         "Split it. In this reply send only the first part, at most 60 lines, and keep your reasoning short. These functions "\n         "and data already exist in the session; call them instead of writing them again: {names}. Send the next part in the "\n         "next reply.")\nVERSIONS = ("V1", "V2", "V3")\n\n\ndef partial_code(arguments: str) -> str:\n    """The code argument of a tool call cut mid-JSON (\'{"code": "import x\\\\nde\'), decoded as far as it goes; \'\' if none."""\n    m = re.search(r\'"(?:code|command)"\\s*:\\s*"\', arguments or "")\n    if not m:\n        return ""\n    body = arguments[m.end():]\n    end = re.search(r\'(?<!\\\\)(?:\\\\\\\\)*"\', body)\n    if end:\n        body = body[:end.end() - 1]\n    for cut in range(len(body), max(len(body) - 8, -1), -1):\n        try:\n            return json.loads(\'"\' + body[:cut] + \'"\')\n        except ValueError:\n            continue\n    return ""\n\n\ndef cut_info(response) -> dict:\n    """Log record of one cut reply from the raw response (dict or litellm object): length, whether a tool call had begun,\n    where it was cut, and the code recovered from the tool call arguments (usually none: the endpoint returns \'{}\')."""\n    r = response if isinstance(response, dict) else response.model_dump(mode="json")\n    choice = (r.get("choices") or [{}])[0]\n    msg = choice.get("message") or {}\n    calls = msg.get("tool_calls") or []\n    args = "".join(((c.get("function") or {}).get("arguments") or "") for c in calls)\n    reasoning = msg.get("reasoning_content") or (msg.get("provider_specific_fields") or {}).get("reasoning") or ""\n    content = msg.get("content") or ""\n    code = partial_code(args)\n    where = ("tool call arguments (code recovered)" if code else\n             "tool call arguments (endpoint returned no arguments)" if calls else\n             "content" if content.strip() else "reasoning")\n    return {"finish_reason": choice.get("finish_reason"), "completion_tokens": (r.get("usage") or {}).get("completion_tokens"),\n            "reasoning_chars": len(reasoning), "content_chars": len(content), "tool_call_started": bool(calls),\n            "tool": ((calls[0].get("function") or {}).get("name") if calls else None), "argument_chars": len(args),\n            "code_chars": len(code), "cut_in": where, "reasoning_first": next((l.strip() for l in reasoning.splitlines() if l.strip()), ""),\n            "code_tail": code[-80:], "code": code}\n\n\ndef complete_defs(code: str) -> list:\n    """(name, source) of the top-level def / class blocks of cut code that are complete: the longest parsable prefix\'s top-level\n    nodes, each followed by another top-level node."""\n    lines = code.splitlines()\n    for cut in range(len(lines), 0, -1):\n        try:\n            tree = ast.parse("\\n".join(lines[:cut]))\n            break\n        except SyntaxError:\n            continue\n    else:\n        return []\n    src = "\\n".join(lines[:cut])\n    return [(n.name, ast.get_source_segment(src, n)) for n in tree.body[:-1]\n            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]\n\n\ndef first_and_length(info: dict) -> tuple:\n    """The placeholder\'s first line (the code\'s, else the reasoning\'s) and its length text."""\n    line = next((l.strip() for l in info.get("code", "").splitlines() if l.strip()), "") or info.get("reasoning_first", "")\n    first = f"`{line[:120]}`" if line else "(no text)"\n    tokens = info.get("completion_tokens")\n    length = (f"{tokens} tokens" if tokens else "the output limit") + f", {info.get(\'reasoning_chars\', 0)} characters of reasoning"\n    if info.get("code_chars"):\n        length += f" and {info[\'code_chars\']} characters of code"\n    return first, length\n\n\ndef placeholder(info: dict, ran: list | None = None) -> str:\n    """The assistant message kept in the history for a cut reply; with V3\'s executed defs when there are any."""\n    first, length = first_and_length(info)\n    if ran:\n        return PLACEHOLDER_V3.format(defs=", ".join(f"`{n}`" for n in ran), last=ran[-1], first=first, length=length)\n    return PLACEHOLDER.format(first=first, length=length)\n\n\ndef log_line(info: dict, streak: int) -> str:\n    """One run-log line per cut reply, without the code itself."""\n    keep = {k: v for k, v in info.items() if k != "code"}\n    return f"[solver] cut reply {streak} in a row: " + json.dumps(keep, ensure_ascii=True)\n', "trunc_chain", "exec"), TRUNC)

EMPTY_LABEL = re.compile(r"date|time|(?:^|_)(?:id|ids|name|label|ticker|symbol|type|category|status|reason|note|notes|comment|description|flag|method|model|source)(?:_|$)", re.I)
EMPTY_COLUMN_NOTE = ("Output check: `{file}` was just written, and these columns the task asks for have no value in any of "
                     "its {rows} rows: {cols}. A common cause is assigning the result of `groupby(...).apply(f)` to a column: when `f` "
                     "returns a list or an array, the result is indexed by the group keys, not by the rows, so the assignment "
                     "matches nothing and fills the column with NaN. Compute one value per row instead (for example "
                     "`groupby(...)[...].transform(...)`, or a per-group table merged back on the group keys), write the file "
                     "again, and print how many values in each such column are not missing.")
EMPTY_SHOWN: set[tuple[str, str]] = set()


def empty_columns(path: str, statement: str) -> list[tuple[str, str, int]]:
    name = os.path.basename(path)
    if not name.endswith(".csv") or name not in statement:
        return []
    with open(path, newline="", errors="replace") as fh:
        rows = list(csv.reader(fh))
    head, body = (rows[0], rows[1:]) if rows else ([], [])
    out = []
    for i, c in enumerate(head):
        vals = [r[i].strip().lower() if i < len(r) else "" for r in body]
        if (body and all(v in ("", "nan", "none", "null") for v in vals) and not EMPTY_LABEL.search(c)
                and re.search(r"(?<![\w])%s(?![\w])" % re.escape(c), statement)):
            out.append((name, c, len(body)))
    return out


def python_code(message: dict) -> str:
    parts = []
    for tc in message.get("tool_calls") or []:
        try:
            if (tc.get("function") or {}).get("name") == "python":
                raw = tc["function"].get("arguments")
                parts.append(str((json.loads(raw) if isinstance(raw, str) else raw or {}).get("code") or ""))
        except (ValueError, AttributeError, KeyError, TypeError):
            continue
    return "\n".join(parts)


def missing_value_notes(code: str, ok: bool) -> list[str]:
    notes = []
    if not (ok and WRITES_FILE.search(code)):
        return notes
    try:
        statement = pathlib.Path(TASK_STATEMENT).read_text()
        names = sorted(n for n in os.listdir(OUTPUT_DIR) if n.endswith(".csv"))
    except OSError:
        return notes
    for n in names:
        try:
            found = empty_columns(os.path.join(OUTPUT_DIR, n), statement)
        except Exception:
            continue
        new = [(col, rows) for _, col, rows in found if (n, col) not in EMPTY_SHOWN]
        if new:
            EMPTY_SHOWN.update((n, col) for col, _ in new)
            notes.append(EMPTY_COLUMN_NOTE.format(file=n, rows=new[0][1], cols=", ".join(f"`{c}`" for c, _ in new)))
    return notes


SPLIT_FILES_VERSION = os.environ.get("SPLIT_FILES_VERSION", "off")
SPLIT_FILES_NOTES = {
    "V1": ("Code note: the reply that was cut off was going to write {files} in one cell. Write at most two files per cell: "
           "send the cell for {first} now and the remaining files in the next replies."),
    "V2": ("A single cell that computes the results and writes several output files is longer than one reply allows, and a "
           "cut-off reply runs nothing. The reply that was cut off was going to write {files}. Split it into several cells "
           "that each write at most two files: in this reply send only the cell for {first}, using the variables already in "
           "the session, and send the next files in the next replies."),
    "V3": ("A single cell that computes the results and writes several output files is longer than one reply allows, and a "
           "cut-off reply runs nothing; the same cell sent again will be cut off again. Still to write: {files}. Split the "
           "work into several cells that each write at most two files. In this reply send only the cell for {first}, at most "
           "60 lines, and keep your reasoning short. These functions and data already exist in the session; call them "
           "instead of writing them again: {names}. Send the next files in the next replies."),
}
WRITE_VERB = re.compile(r"\b(?:writ|wrote|sav|output|produc|dump|export|emit|generat|creat|to_csv|to_json)\w*", re.I)


def cut_text(response) -> str:
    r = response if isinstance(response, dict) else response.model_dump(mode="json")
    msg = ((r.get("choices") or [{}])[0]).get("message") or {}
    reasoning = msg.get("reasoning_content") or (msg.get("provider_specific_fields") or {}).get("reasoning") or ""
    args = "".join(((c.get("function") or {}).get("arguments") or "") for c in msg.get("tool_calls") or [])
    return "\n".join((reasoning, msg.get("content") or "", args))


def names_file(text: str, file: str, write_context: bool) -> bool:
    low = text.lower()
    stem = file.rsplit(".", 1)[0].lower()
    for form in {file.lower(), stem, stem.replace("_", " ")}:
        for m in re.finditer(re.escape(form), low):
            if not write_context or WRITE_VERB.search(low[max(0, m.start() - 120):m.start()]):
                return True
    return False


def split_files_due(version: str, text: str, missing: list[str], streak: int) -> list[str]:
    if version not in SPLIT_FILES_NOTES or len(missing) < 2:
        return []
    named = [f for f in missing if names_file(text, f, version != "V3")]
    if version == "V3":
        return named if len(named) >= 2 else missing if streak >= 2 else []
    return named if len(named) >= 2 and (version == "V2" or streak == 1) else []


def split_files_note(version: str, files: list[str], names: str) -> str:
    return SPLIT_FILES_NOTES[version].format(files=", ".join(f"`{f}`" for f in files),
                                             first=" and ".join(f"`{f}`" for f in files[:2]), names=names)


OK_CODE: list[str] = []


def session_names(keep: int = 15) -> str:
    funcs, assigned = [], []
    for code in OK_CODE:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                funcs.append(node.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                    for n in (x.id for x in ast.walk(t) if isinstance(x, ast.Name)):
                        if n in assigned:
                            assigned.remove(n)
                        assigned.append(n)
    funcs = list(dict.fromkeys(funcs))
    assigned = [n for n in assigned if n not in funcs]
    shown = assigned[-keep:]
    text = ", ".join(f"`{n}`" for n in funcs + shown)
    return text + (f" and {len(assigned) - len(shown)} more variables" if len(assigned) > len(shown) else "")


JOINT_SHOWN: set[str] = set()
JOINT_NOTE = ("Self-test note: before using `{fn}({params})` (defined at message {cell_msg}), check it against limits that any "
              "joint probability must satisfy. P(A and B) is never larger than P(A) or P(B); when one condition is relaxed until "
              "it always holds (for example a barrier or level moved far away), the result must equal the marginal probability "
              "of the other condition; and it must change when each of its arguments changes. For a Brownian motion with drift "
              "mu and volatility sigma, the marginal of the terminal value is P(X_T <= x) = Phi((x - mu*T)/(sigma*sqrt(T))). "
              "Evaluate `{fn}` at a few values of each argument, with the other condition relaxed, and print it next to the "
              "marginal. If a limit fails, the formula is missing a term or a dependence; fix it and recompute everything that "
              "uses it. If your setup satisfies a condition this check cannot see, say which and keep it.")


def joint_functions(code: str) -> list[tuple[str, list[str]]]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or "joint" not in node.name.lower():
            continue
        params = [a.arg for a in node.args.posonlyargs + node.args.args]
        calls = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "cdf"
                    and isinstance(c.func.value, (ast.Name, ast.Attribute))
                    and (c.func.value.id if isinstance(c.func.value, ast.Name) else c.func.value.attr) == "norm"
                    for c in ast.walk(node))
        if calls and len(params) >= 2:
            out.append((node.name, params))
    return out


OC11_CHECKS_DIR = os.environ.get("OC11_CHECKS_DIR", os.path.join(QFREF_ROOT, "qfref"))
OC11M: dict = {}
try:
    os.environ.setdefault("API_LINT_RULES_DIR", OC11_CHECKS_DIR)
    os.environ.setdefault("KEY_NAMES_V2_DIR", OC11_CHECKS_DIR)
    if OC11_CHECKS_DIR not in sys.path:
        sys.path.insert(0, OC11_CHECKS_DIR)
    for _name in ("oc11a_checks", "api_lint", "bermudan_check", "a102_mapping", "mapping_note", "key_case_check", "s1_v2",
                  "key_name_consistency", "theta_convention"):
        OC11M[_name] = importlib.import_module(_name)
except Exception as _exc:
    print(f"[solver] oc11 checks not loaded: {type(_exc).__name__}: {_exc}", flush=True)
API_LINT = OC11M["api_lint"].ApiLint({"K6": True, "K4x": True, "K2c": True}) if "api_lint" in OC11M else None
OC11_SHOWN: set = set()


def key_name_notes() -> list[str]:
    out = []
    for site in OC11M["key_name_consistency"].key_name_sites(OUTPUT_DIR, pathlib.Path(TASK_STATEMENT).read_text(), DATA_DIRS[0]):
        if ("keyname", site["file"], site["key"]) not in OC11_SHOWN:
            OC11_SHOWN.add(("keyname", site["file"], site["key"]))
            out.append(OC11M["key_name_consistency"].key_name_note(site, OUTPUT_DIR))
    return out
K2C_THIS_COMMAND: list[bool] = []
K2C_V2 = 'Code check: line {lineno} of your cell at message {N}, `{line}`, reads `{recv}.get({key}, {default})` while discounting a bond. Here {missing_keys} are coupon dates that are not solved nodes yet, so each enters as {default}. A discount factor at such a date is not known before the new node: it depends on the node you are solving. Do not fill it with {default}, and do not interpolate it from the nodes solved so far. Solve the new node and those dates together, so that this bond reprices to its input price:\n    def gap(z, T, c, curve):\n        trial = {**curve, T: z}; ks = sorted(trial)\n        df = lambda t: np.exp(-np.interp(t, ks, [trial[k] for k in ks]) * t)\n        times = np.arange(1, int(round(T * freq)) + 1) / freq\n        return (c / freq) * sum(df(t) for t in times) + df(T) - 1.0\n    zero[T] = scipy.optimize.brentq(gap, -0.5, 0.5, args=(T, c, zero))\nUse the interpolation the task states in place of np.interp on zero rates if it says otherwise. Solve the nodes in maturity order, check that every input bond reprices to its price, then rewrite the output file.'
K2C_PROBE = ("try:\n"
             "    __import__('builtins').exec(%r, dict(globals()))\n"
             "except Exception:\n"
             "    print('K2CMISS null')")


def k2c_probe(code: str, lineno: int, recv: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    path = []

    def find(node, trail):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call) and getattr(child, "lineno", 0) == lineno and isinstance(child.func, ast.Attribute) \
                    and child.func.attr == "get" and ast.unparse(child.func.value) == recv and len(child.args) == 2:
                path[:] = trail + [child]
                return True
            if find(child, trail + [child]):
                return True
        return False
    if not find(tree, []):
        return None
    call, loops = path[-1], [n for n in path if isinstance(n, ast.For)]
    if not loops:
        return None

    def simple(stmt):
        return (isinstance(stmt, ast.Assign) and all(isinstance(t, (ast.Name, ast.Tuple)) for t in stmt.targets)
                and not any(isinstance(c, ast.Call) and not (isinstance(c.func, ast.Name) and c.func.id in
                            ("range", "int", "float", "len", "round", "min", "max", "abs", "enumerate", "zip", "sorted", "list"))
                            for c in ast.walk(stmt.value)))

    def build(i, indent):
        loop, nxt = loops[i], (loops[i + 1] if i + 1 < len(loops) else None)
        lines = [" " * indent + f"for {ast.unparse(loop.target)} in {ast.unparse(loop.iter)}:"]
        for stmt in loop.body:
            if nxt is not None and stmt is nxt:
                lines += build(i + 1, indent + 4)
                break
            if nxt is None and any(n is call for n in ast.walk(stmt)):
                lines.append(" " * (indent + 4) + f"_k2c_keys.add({ast.unparse(call.args[0])})")
                break
            if simple(stmt):
                lines.append(" " * (indent + 4) + ast.unparse(stmt))
        return lines
    body = ["def _k2c():", "    _k2c_keys = set()"] + build(0, 4) + ["    return _k2c_keys",
            f"_k2c_have = set({recv})",
            "print('K2CMISS', __import__('json').dumps(sorted(float(k) for k in _k2c() if k not in _k2c_have)))"]
    return K2C_PROBE % "\n".join(body)


REQUIRED_NAMES: list[str] = []
M3_SEEN: dict[tuple[str, str], str] = {}
M3_SEND_NOW: set[str] = set()
M3_NOTE = re.compile(r"Output check: your own check `(.+?)` in (.+?) reports false;")


def placeholder_file(path: str) -> bool:
    try:
        if os.path.getsize(path) == 0:
            return True
        if path.lower().endswith(".csv"):
            return sum(1 for line in open(path, errors="replace") if line.strip()) <= 1
        if path.lower().endswith(".json"):
            leaves = []
            def walk(o):
                if isinstance(o, dict):
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
                else:
                    leaves.append(o)
            walk(json.loads(open(path).read()))
            return all(v in (None, "", 0, False) for v in leaves)
    except (OSError, ValueError):
        return True
    return False


def m3_notes() -> list[str]:
    if REQUIRED_NAMES and all(placeholder_file(os.path.join(OUTPUT_DIR, n)) for n in REQUIRED_NAMES):
        return []
    out = []
    for note in OC7["flags/self_check_flags.py"]["flag_notes"](OUTPUT_DIR):
        m = M3_NOTE.match(note)
        if not m:
            out.append(note)
            continue
        key = (m.group(2), m.group(1))
        try:
            sig = hashlib.sha1(open(os.path.join(OUTPUT_DIR, m.group(2)), "rb").read()).hexdigest()
        except OSError:
            continue
        if M3_SEEN.get(key) == sig:
            continue
        if key in M3_SEEN:
            note = note.replace("reports false;", "still reports false after the file was rewritten;", 1)
        M3_SEEN[key] = sig
        M3_SEND_NOW.add(note)
        out.append(note)
    return out


FULL_TEXT_PREVIEW = True
FULL_TEXT_SUFFIXES = {".py", ".md", ".txt", ".r", ".sql", ".yaml", ".yml", ".toml", ".cfg", ".ini"}
FULL_TEXT_LINES = 500
FULL_TEXT_CAP = 40000
FULL_TEXT_HEAD = ("Full text of {rel} ({n} lines; the task names this file and it is too long for one cell's output, so it is "
                  "shown here once with line numbers -- read it from here instead of printing it again):")
FULL_TEXT_INDEX_HEAD = ("Full text of {rel} (index only; {n} lines; the task names this file and it is too long for one cell's "
                        "output; its definitions are listed with line numbers -- print the lines you need):")


def norm_tokens(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def text_index(path: str, text: str, start: int) -> list[str]:
    lines = text.splitlines()
    if path.lower().endswith(".py"):
        try:
            nums = sorted({n.lineno for n in ast.walk(ast.parse(text))
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.lineno >= start})
        except SyntaxError:
            return []
        return [(k, re.sub(r"\s+#.*$", "", lines[k - 1].strip())) for k in nums]
    if path.lower().endswith(".md"):
        return [(k, l) for k, l in enumerate(lines, 1) if k >= start and re.match(r"#{1,6}\s", l)]
    return []


def full_text_block(rel: str, path: str, text: str, index_only: bool) -> str:
    lines = [l.replace("\t", "    ") for l in text.splitlines()]
    n, w = len(lines), len(str(len(lines)))
    if index_only:
        return "\n".join([FULL_TEXT_INDEX_HEAD.format(rel=rel, n=n)] + [f"{k:>{w}}| {l}" for k, l in text_index(path, text, 1)])
    out = [FULL_TEXT_HEAD.format(rel=rel, n=n)] + [f"{k:>{w}}| {l}" for k, l in enumerate(lines[:FULL_TEXT_LINES], 1)]
    if n > FULL_TEXT_LINES:
        out.append(f"Lines {FULL_TEXT_LINES + 1}-{n} are not shown; definitions there:")
        out += [f"{k:>{w}}| {l}" for k, l in text_index(path, text, FULL_TEXT_LINES + 1)]
    return "\n".join(out)


def full_text_preview(body: str) -> str:
    try:
        statement = norm_tokens(pathlib.Path(TASK_STATEMENT).read_text())
        raw = pathlib.Path(TASK_STATEMENT).read_text().lower()
    except OSError:
        return body
    found = []
    for m in re.finditer(r"^== (\S+)(?:  \(skipped: [^)]*\))?$", body, re.M):
        path = m.group(1)
        name = os.path.basename(path)
        if os.path.splitext(name)[1].lower() not in FULL_TEXT_SUFFIXES or not os.path.isfile(path):
            continue
        if norm_tokens(name) not in statement:
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        if len(json.dumps(text)) > OUTPUT_HEAD_CHARS + OUTPUT_TAIL_CHARS:
            found.append((raw.find(name.lower()), path, text))
    added = 0
    for _, path, text in sorted(found, key=lambda f: f[0] if f[0] >= 0 else len(raw)):
        block = full_text_block(path, path, text, index_only=False)
        if added + len(block) > FULL_TEXT_CAP:
            block = full_text_block(path, path, text, index_only=True)
        added += len(block)
        sec = re.search(r"^== %s(?:  \(skipped: [^)]*\))?(?:\n(?!== ).*)*" % re.escape(path), body, re.M)
        if sec:
            rest = body[sec.end():].lstrip("\n")
            body = body[:sec.start()] + f"== {path}\n{block}" + ("\n\n" + rest if rest else "")
        print(f"[solver] full text preview: {path} ({len(block)} characters)", flush=True)
    return body


HEADER_DETECT = True
HEADER_DETECT_SCRIPT = ("import json, os, sys\nsys.path.insert(0, sys.argv[1])\nos.environ.setdefault('PEEK_HELPERS_DIR', '/opt')\nimport header_detect as hd\ntry:\n    import header_detect_v2 as hd2\nexcept Exception:\n    hd2 = None\nout = {}\nfor p in sys.argv[2:]:\n    lines = []\n    try:\n        lines = hd2.preview_lines(p) if hd2 is not None else [l for l in hd.preview_lines(p) if 'header note:' not in l]\n    except Exception:\n        pass\n    try:\n        lines += [l for l in hd.preview_lines(p) if 'header note:' in l]\n    except Exception:\n        pass\n    out[p] = lines\nprint(json.dumps(out))")


def header_detect_preview(body: str, env: dict) -> str:
    paths = [m.group(1) for m in re.finditer(r"^== (\S+)", body, re.M)
             if os.path.splitext(m.group(1))[1].lower() in (".csv", ".tsv", ".txt", ".dat", ".psv", ".xlsx", ".xlsm", ".xls")]
    if not paths:
        return body
    p = subprocess.run(["python", "-c", HEADER_DETECT_SCRIPT, os.environ.get("OC11_CHECKS_DIR", os.path.join(QFREF_ROOT, "qfref"))]
                       + paths, capture_output=True, text=True, env=env, timeout=120)
    lines = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else {}
    for path, add in lines.items():
        if not add:
            continue
        sec = re.search(r"^== %s(?:  \(skipped: [^)]*\))?(?:\n(?!== ).*)*" % re.escape(path), body, re.M)
        if sec:
            end = sec.end() - (len(sec.group(0)) - len(sec.group(0).rstrip("\n")))
            body = body[:end] + "\n" + "\n".join(add) + body[end:]
            print(f"[solver] header lines added for {path}: {len(add)}", flush=True)
    return body


TRIAGE: list = []
TRIAGE_SHOWN: set = set()
TRIAGE_RULES: set = set()
TRIAGE_RULES.add('method_gap')
TRIAGE_RULES.add('calendar_offset')
TRIAGE_RULES.add('sign_double')
TRIAGE_RULES.add('scale_ratio')
TRIAGE_RULES.add('empty_bars')
TRIAGE_OBJECTS: dict = {}
TRIAGE_RULES.add('ewma_parity')
TRIAGE_RULES.add('exercise_boundary')
TRIAGE_RULES.add('rank_equal')
TRIAGE_RULES.add('id_subset')
TRIAGE_RULES.add('direction_sign')
TRIAGE_RULES.add('array_cell')
TRIAGE_RULES.add('degree_day_sign')
TRIAGE_RULES.add('kappa_log')
TRIAGE_RULES.add('placeholder_zeros')
TRIAGE_RULES.add('subfit_count')
TRIAGE_RULES.add('reference_time')
TRIAGE_RULES.add('balance_lag')
TRIAGE_RULES.add('weight_cap')
TRIAGE_RULES.add('forward_sign')
TRIAGE_RULES.add('pair_order')
TRIAGE_RULES.add('reread')
TRIAGE_RULES.add('template_run')
TRIAGE_RULES.add('cdf_jump')
TRIAGE_RULES.add('argmax_hit')
TRIAGE_RULES.add('partial_row_ffill')
TRIAGE_RULES.add('nan_text')
TRIAGE_RULES.add('baw_coef')
TRIAGE_RULES.add('global_param')
TRIAGE_RULES.add('loc_window')
TRIAGE_RULES.add('parity')
TRIAGE_RULES.add('key_shift')
TRIAGE_RULES.add('utc_z_suffix')
TRIAGE_RULES.add('kde_bandwidth')
TRIAGE_RULES.add('scale_mismatch')
TRIAGE_RULES.add('fx_identities')
TRIAGE_RULES.add('xccy_identities')
TRIAGE_RULES.add('neg_index')
TRIAGE_RULES.add('lattice_prob')
TRIAGE_RULES.add('momentum_sharpe')


def triage_module():
    if not TRIAGE:
        try:
            os.environ.setdefault("OC11_TRIAGE_DIR", OC11_CHECKS_DIR)
            TRIAGE.append(importlib.import_module("triage_checks"))
            for rule in TRIAGE_RULES:
                TRIAGE[0].ENABLED[rule] = True
        except Exception as exc:
            TRIAGE.append(None)
            print(f"[solver] triage checks not loaded: {type(exc).__name__}: {exc}", flush=True)
    return TRIAGE[0]


def triage_items(items) -> list[str]:
    out = []
    for r in items:
        if tuple(r["key"]) not in TRIAGE_SHOWN:
            TRIAGE_SHOWN.add(tuple(r["key"]))
            out.append(r["note"])
    return out


def triage_notes(fn: str, *args, probe=None, **kwargs) -> list[str]:
    mod = triage_module()
    out = []
    for r in getattr(mod, fn, lambda *a, **k: [])(*args, **kwargs) if mod is not None else []:
        key = tuple(r["key"])
        if key in TRIAGE_SHOWN:
            continue
        if r.get("probe"):
            if probe is None or not getattr(mod, r["rule"] + "_confirmed")(probe(r["probe"])):
                continue
        TRIAGE_SHOWN.add(key)
        out.append(r["note"])
    return out


D2_PRELOAD = '\nimport json as _d2j\n_d2_dumps, _d2_dump = _d2j.dumps, _d2j.dump\ndef _d2_np(v):\n    if isinstance(v, dict):\n        return {_d2_np(k): _d2_np(x) for k, x in v.items()}\n    if isinstance(v, (list, tuple)):\n        return [_d2_np(x) for x in v]\n    if type(v).__module__.split(".")[0] == "numpy":\n        if hasattr(v, "tolist"):\n            return _d2_np(v.tolist())\n        if hasattr(v, "item"):\n            return _d2_np(v.item())\n    return v\ndef _d2_dumps_wrap(obj, *a, **k):\n    try:\n        return _d2_dumps(obj, *a, **k)\n    except TypeError as e:\n        try:\n            return _d2_dumps(_d2_np(obj), *a, **k)\n        except TypeError:\n            raise e\ndef _d2_dump_wrap(obj, fp, *a, **k):\n    fp.write(_d2_dumps_wrap(obj, *a, **k))\n_d2j.dumps, _d2j.dump = _d2_dumps_wrap, _d2_dump_wrap\nimport re as _rsr\n_rsr_sub = _rsr.sub\ndef _rsr_sub_wrap(pattern, repl, string, *a, **k):\n    out = _rsr_sub(pattern, repl, string, *a, **k)\n    if isinstance(string, str) and out == string and "\\n" in string and len(str(getattr(pattern, "pattern", pattern))) >= 30:\n        print("Code note: re.sub matched nothing, so the text is unchanged. Copy the exact block from the file and use text.replace(old_block, new_block), checking old_block in text first.")\n    return out\n_rsr.sub = _rsr_sub_wrap\n'


SESSION_PROBE: list = []
VAR_V2: list = []


def var_variance_notes_now(statement: str) -> list[str]:
    vv = OC7["varES/var_variance.py"]
    if not VAR_V2:
        try:
            VAR_V2.append(importlib.import_module("var_v2"))
        except Exception as exc:
            VAR_V2.append(None)
            print(f"[solver] var_v2 not loaded: {type(exc).__name__}", flush=True)
    if VAR_V2[0] is None:
        return vv["var_variance_notes"](OUTPUT_DIR, statement, DATA_DIRS)
    return VAR_V2[0].var_variance_notes_v2(vv, OUTPUT_DIR, statement, DATA_DIRS, SESSION_PROBE[0] if SESSION_PROBE else None)


COLON_LIST: list = []


def colon_list_missing(path: str, entry: str, files: list[str], expected: list[str]) -> list[str]:
    if not COLON_LIST:
        try:
            COLON_LIST.append(importlib.import_module("colon_list_keys"))
        except Exception as exc:
            COLON_LIST.append(None)
            print(f"[solver] colon_list_keys not loaded: {type(exc).__name__}", flush=True)
    if COLON_LIST[0] is None:
        return []
    return COLON_LIST[0].colon_list_missing(path, entry, files, expected, named_fields(entry, files))


INTEGER_HEAD = {"n", "num", "number", "rank", "idx"}
INTEGER_TAIL = {"id", "ids", "count", "counts", "index", "idx", "rank", "ms", "us", "ns", "ts", "timestamp", "epoch", "year",
                "month", "day", "days", "shares", "contracts", "lots", "trades"}


def integer_name(col: str) -> bool:
    words = [w for w in col.lower().split("_") if w]
    return bool(words) and (words[0] in INTEGER_HEAD or words[-1] in INTEGER_TAIL)


def decimal_problems(path: str, statement: str) -> list[str]:
    name, out = os.path.basename(path), []
    if name.endswith(".json") and (m := JSON_DECIMALS.search(statement)) and (n := decimals_rule(m.group(1))) is not None:
        try:
            data = json.loads(open(path).read())
        except (OSError, ValueError):
            return []
        top = data.items() if isinstance(data, dict) else []
        bad = [k for k, v in top if isinstance(v, float) and math.isfinite(v) and abs(v - round(v, n)) > 1e-12]
        if bad:
            out.append(f"{len(bad)} JSON number(s) not rounded to {n} decimals as the task states: " + ", ".join(bad[:6]))
    for fname, word in CSV_DECIMALS.findall(statement):
        n = decimals_rule(word)
        if fname == name and n is not None:
            rows = list(csv.reader(io.StringIO(open(path, errors="replace").read())))
            head, cols = (rows[0] if rows else []), {}
            for r in rows[1:]:
                for i, c in enumerate(r):
                    if re.fullmatch(r"-?\d+\.\d*", c.strip()) and len(c.strip().split(".")[1]) != n:
                        col = head[i] if i < len(head) else f"column {i + 1}"
                        cols.setdefault(col, [0, c.strip()])[0] += 1
            all_whole = {k for k in cols if (i := head.index(k) if k in head else -1) >= 0
                         and all(re.fullmatch(r"-?\d+(?:\.0*)?", r[i].strip()) for r in rows[1:] if i < len(r) and r[i].strip())}
            whole = {k for k in all_whole if integer_name(k)}
            def cells_of(k):
                i = head.index(k)
                return [r[i].strip() for r in rows[1:] if i < len(r) and r[i].strip()]
            reported = {k for k in whole if is_id_time_column(k, cells_of(k), len(rows))}
            gated = {k for k in whole if last_word(k) in ID_TIME_TAIL} - reported
            whole -= reported | gated
            unsure = (all_whole - whole - reported - gated) | gated
            floats = {k: v for k, v in cols.items() if k not in all_whole}
            if floats:
                listed = ", ".join(f"`{k}` ({v[0]}, e.g. {v[1]})" for k, v in list(floats.items())[:8])
                out.append(f"{sum(v[0] for v in floats.values())} float cell(s) without exactly {n} decimal places, which the task requires for every float field: {listed}; "
                           f"df.to_csv(path, index=False, float_format='%.{n}f') writes every float column that way")
            if unsure:
                listed = ", ".join(f"`{k}` (e.g. {cols[k][1]})" for k in list(unsure)[:8])
                out.append(f"whole numbers written with a decimal point in {listed}: if the task describes the field as a count, id or "
                           f"integer, write integers; otherwise it is a float field and takes exactly {n} decimal places")
            if whole:
                listed = ", ".join(f"`{k}` (e.g. {cols[k][1]})" for k in list(whole)[:8])
                out.append(f"whole numbers written with a decimal point in {listed}: an id, count or timestamp field is written as an integer without a decimal point; a float field takes exactly {n} decimal places; "
                           f"df.astype({{col: 'Int64'}}) before to_csv keeps such a column integer (missing cells stay empty)")
    return out


ID_TIME_TAIL = {"id", "ids", "index", "idx", "ms", "us", "ns", "ts", "timestamp", "epoch"}
TIME_UNIT_TAIL, INDEX_TAIL = {"ms", "us", "ns", "ts"}, {"index", "idx"}


def last_word(col: str) -> str:
    words = [w for w in col.lower().split("_") if w]
    return words[-1] if words else ""


def is_id_time_column(col: str, cells: list[str], n_rows: int) -> bool:
    tail = last_word(col)
    if not (tail in ID_TIME_TAIL and cells and all(re.fullmatch(r"-?\d+(?:\.0*)?", c) for c in cells)):
        return False
    values = [float(c) for c in cells]
    if tail in TIME_UNIT_TAIL and not all(abs(v) >= 1e9 for v in values):
        return False
    return not (tail in INDEX_TAIL and not all(0 <= v < n_rows for v in values))


def integer_column_problems(path: str) -> list[str]:
    if not path.lower().endswith(".csv"):
        return []
    rows = list(csv.reader(io.StringIO(open(path, errors="replace").read())))
    if len(rows) < 2:
        return []
    head, bad = rows[0], []
    for i, col in enumerate(head):
        cells = [r[i].strip() for r in rows[1:] if i < len(r) and r[i].strip()]
        if is_id_time_column(col, cells, len(rows)) and (dotted := [c for c in cells if "." in c]):
            bad.append(f"`{col}` (e.g. {dotted[0]})")
    if not bad:
        return []
    return [f"whole numbers written with a decimal point in {', '.join(bad[:8])}: an id or timestamp field is written as an "
            f"integer without a decimal point, whatever decimals rule applies to float fields; a column with missing cells "
            f"is held as float by pandas, so df.astype({{col: 'Int64'}}) before to_csv keeps it integer (missing cells stay empty)"]


OBJECT_FIELD = re.compile(r'"([^"]+)"\s*:\s*(?:\{\s*"value"\s*:\s*)?"?<object>"?')


def copied_key_problems(entries: list[tuple[str, str]], out_dir: str) -> list[tuple[str, str]]:
    data = {}
    for n, _ in entries:
        if n.endswith(".json"):
            try:
                data[n] = json.loads(open(os.path.join(out_dir, n)).read())
            except (OSError, ValueError):
                pass
    out = []
    for n, entry in entries:
        if n not in data:
            continue
        for field in OBJECT_FIELD.findall(entry):
            node = next((v for p, v in json_obj_paths(data[n]) if p.split(".")[-1] == field), None)
            node = node.get("value", node) if isinstance(node, dict) and set(node) == {"value"} else node
            if not isinstance(node, dict) or len(node) < 2:
                continue
            for other, d in data.items():
                if other != n and isinstance(d, dict) and set(node) <= set(d):
                    out.append((n, f"`{field}` uses the field names of {other} as its keys ({', '.join(list(node)[:4])}); "
                                   "if it is keyed by category, use the category labels the task defines"))
                    break
    return out


def json_obj_paths(value, prefix=""):
    if isinstance(value, dict):
        yield prefix, value
        for k, v in value.items():
            yield from json_obj_paths(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from json_obj_paths(v, f"{prefix}[{i}]")


def file_problems(path: str, entry: str, files: list[str], statement: str = "") -> list[str]:
    if not (os.path.isfile(path) and os.path.getsize(path) > 0):
        return ["not written"]
    suffix = os.path.splitext(path)[1].lower()
    problems, present = [], None
    try:
        if suffix == ".json":
            data = json.loads(open(path).read())
            present = json_keys(data) | {v for _, v in json_paths(data) if isinstance(v, str)}
            problems += nesting_issues(data, level_names(entry))
            if typed := type_issues(data, entry):
                problems.append(f"{len(typed)} value(s) of a different JSON type than the task entry writes: "
                                + ", ".join(typed[:8]) + (" ..." if len(typed) > 8 else ""))
            if infinite := [p for p, v in json_paths(data) if isinstance(v, float) and math.isinf(v)]:
                problems.append("infinite value(s): " + ", ".join(infinite[:8]))
            rules = allowed_null_rules(entry)
            if rules:
                nullable = nullable_keys(entry)
                nulls = [p for p, v in json_paths(data)
                         if (v is None or (isinstance(v, float) and not math.isfinite(v))) and not null_allowed(p, rules)
                         and not {c for c in re.split(r"[.\[\]]+", p) if c} & nullable]
                if nulls:
                    problems.append(f"{len(nulls)} null or non-finite value(s) the task entry does not allow: "
                                    + ", ".join(nulls[:8]) + (" ..." if len(nulls) > 8 else ""))
        elif suffix in (".csv", ".tsv"):
            rows = list(csv.reader(io.StringIO(open(path, errors="replace").read()), delimiter="\t" if suffix == ".tsv" else ","))
            present = set(rows[0]) if rows else set()
            problems += csv_problems(rows, entry, header_columns(entry, os.path.basename(path), files), statement)
            stated = re.search(r"(\d+)\s+rows\b", entry)
            if stated and int(stated.group(1)) != max(len(rows) - 1, 0):
                problems.append(f"{max(len(rows) - 1, 0)} data rows; the task entry states {stated.group(1)}")
    except Exception as exc:
        return [f"cannot be read as {suffix.lstrip('.')}: {type(exc).__name__}: {str(exc)[:120]}"]
    problems += decimal_problems(path, statement)
    problems += integer_column_problems(path)
    problems += loss_floor_problems(path, statement)
    if present is not None:
        expected = ((header_columns(entry, os.path.basename(path), files) or listed_names(entry, files)) if suffix in (".csv", ".tsv")
                    else json_key_names(entry, files) + expanded_template_keys(entry, statement))
        missing = [n for n in expected if n not in present]
        with contextlib.suppress(Exception):
            missing += [n for n in colon_list_missing(path, entry, files, expected) if n not in missing]
        if missing:
            spare = sorted(n for n in (json_keys(data) if suffix == ".json" else present) if isinstance(n, str) and n not in expected)
            close = [(w[0], m) for m in missing if (w := difflib.get_close_matches(m, spare, n=1, cutoff=0.85))]
            spelled = {m for _, m in close}
            longer = [(w[0], m) for m in missing if m not in spelled
                      and len(w := [n for n in spare if n.endswith("_" + m) or n.startswith(m + "_")]) == 1]
            problems.insert(0, "named in the task entry but not found as a key or column: " + ", ".join(missing)
                            + "".join(f"; `{w}` looks like a misspelling of the required `{m}`" for w, m in close)
                            + "".join(f"; `{w}` may be the required `{m}` written with an extra prefix or suffix" for w, m in longer))
    return problems


NEGATION = re.compile(r"\b(?:do not|don't|never|not to|instead of|rather than|avoid)\b", re.I)
NON_MANDATORY = re.compile(r"\b(?:preferred|prefer|equivalent|e\.g\.|for example|such as|ideally|recommended|where possible|if possible|may)\b", re.I)
DECIMAL_CONV = re.compile(r"(?:ratios?|percentages?|fractions?|shares?)[^.\n]{0,60}?\b(?:as|in|are)\s+(?:raw\s+)?decimal", re.I)
PERCENT_CONV = re.compile(r"(?:percentages?|percents?)[^.\n]{0,40}?(?:0\s*[-\u2013to]+\s*100\b|in percent(?:age)? points\b|as percent(?:age)?s?\b(?! of))", re.I)
FIELD_PERCENT = r"(?:\u00d7|x|\*)\s*100\b|in percent(?:age)?(?: points)?\b|as a percent(?:age)?\b|\b0\s*[-\u2013]\s*100\b|\(%\)|\bpercent(?:age)? of\b|\bin %"
FIELD_BPS = r"in basis points|\bin bps\b|(?:\u00d7|x|\*)\s*10,?000\b"
FIELD_DECIMAL = r"as a decimal|decimal (?:fraction|ratio)|not (?:a )?percent|\bin \[0,\s*1\]"
UNITNAME = re.compile(r"(?:^|_)(pct|percent|bps|bp|ratio|share|weight|frac|fraction)(?:_|$)", re.I)
PCT_NAME = re.compile(r"(?:^|_)(?:pct|percent)$", re.I)
BPS_NAME = re.compile(r"(?:^|_)(?:bps|bp)$", re.I)
WEIGHT_NAME = re.compile(r"^(?!rank_|n_|num_)(?!.*(?:gross|leverage|total)).*(?:^|_)weights?(?:_|$)", re.I)
DECIMAL_SCALE_NAME = re.compile(r"^(?!rank_|n_|num_).*(?:_(?:pct|percent)$|(?:^|_)(?:share|frac|fraction)(?:_|$))", re.I)


def contract_finding(rule: str, tier: str, file: str, field: str, msg: str) -> dict:
    return {"rule": rule, "tier": tier, "file": file, "field": field, "msg": msg}


def sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.;:])\s+|\n", text)


def field_unit(statement: str, name: str) -> tuple[str | None, str]:
    for sent in sentences(statement):
        if re.search(r"(?<![A-Za-z0-9_])`?%s`?(?![A-Za-z0-9_])" % re.escape(name), sent) and not NEGATION.search(sent):
            if re.search(FIELD_BPS, sent, re.I):
                return "bps", sent.strip()[:160]
            if re.search(FIELD_DECIMAL, sent, re.I):
                return "decimal", sent.strip()[:160]
            if re.search(FIELD_PERCENT, sent, re.I):
                return "percent", sent.strip()[:160]
    return None, ""


def file_unit(statement: str) -> tuple[str | None, str]:
    for sent in sentences(statement):
        if NEGATION.search(sent):
            continue
        if DECIMAL_CONV.search(sent):
            return "decimal", sent.strip()[:160]
        if PERCENT_CONV.search(sent):
            return "percent", sent.strip()[:160]
    return None, ""


def numeric_fields(path) -> tuple[dict, list[dict]]:
    vals, siblings = {}, []
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text())
        except ValueError:
            return vals, siblings

        def walk(x):
            if isinstance(x, dict):
                nums = {k: float(v) for k, v in x.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)}
                if nums:
                    siblings.append(nums)
                for k, v in nums.items():
                    vals.setdefault(k, []).append(v)
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(data)
    elif path.suffix == ".csv":
        rows = list(csv.reader(io.StringIO(path.read_text(errors="replace"))))
        if rows:
            h = rows[0]
            for r in rows[1:]:
                row = {}
                for i, c in enumerate(r[:len(h)]):
                    try:
                        v = float(c)
                        if math.isfinite(v):
                            vals.setdefault(h[i], []).append(v)
                            row[h[i]] = v
                    except ValueError:
                        pass
                if row:
                    siblings.append(row)
    return vals, siblings


def unit_problems(path, statement: str) -> list[dict]:
    out = []
    vals, sibs = numeric_fields(path)
    fconv, fev = file_unit(statement)
    for name, vs in vals.items():
        nz = [abs(v) for v in vs if v != 0]
        if not nz or not UNITNAME.search(name):
            continue
        unit, ev = field_unit(statement, name)
        if unit is None and fconv and not BPS_NAME.search(name):
            unit, ev = fconv, fev
        note = None
        if unit == "percent" and max(nz) <= 1.0:
            note = f"every value is at most 1 in size (max {max(nz):.6g}) while the task states percent ({ev!r})"
        elif unit == "decimal" and ((DECIMAL_SCALE_NAME.search(name) and max(nz) > 1.5)
                                    or (WEIGHT_NAME.search(name) and re.search(r"\bweights?\b", ev, re.I) and max(nz) > 2.5)):
            note = f"values reach {max(nz):.6g} while the task states decimal ratios ({ev!r})"
        elif unit == "bps" and max(nz) < 0.01:
            note = f"every value is below 0.01 in size while the task states basis points ({ev!r})"
        if note:
            out.append(contract_finding("U1", "doubt", path.name, name, f"`{name}`: {note}; check that the scale matches the task text"))
        elif unit is None and PCT_NAME.search(name):
            for s in sibs:
                if name not in s or not (0 < abs(s[name]) < 1):
                    continue
                v = s[name]
                hit = next(((a, b) for a in s for b in s if a != b and name not in (a, b) and s[b] != 0
                            and abs(s[a] / s[b] - v) <= 1e-9 * max(1, abs(v)) + 1e-12
                            and not re.search(r"pct|percent|ratio|share|weight", a + b, re.I)), None)
                if hit:
                    out.append(contract_finding("U3", "doubt", path.name, name,
                                                f"`{name}` = {v:.6g} equals `{hit[0]}` / `{hit[1]}`; the task does not state its unit"))
                    break
    return out


def rank_problems(path, statement: str) -> list[dict]:
    if path.suffix != ".csv":
        return []
    rows = list(csv.reader(io.StringIO(path.read_text(errors="replace"))))
    if len(rows) < 3:
        return []
    h, body = rows[0], [r for r in rows[1:] if len(r) >= len(rows[0])]
    out = []

    def f(x):
        try:
            return float(x)
        except ValueError:
            return None
    for i, c in enumerate(h):
        m = re.fullmatch(r"rank_(.+)", c, re.I)
        if not m or m.group(1) not in h:
            continue
        j = h.index(m.group(1))

        def consistent(groups):
            for g in groups.values():
                ys = [y for _, y in sorted((f(r[i]), f(r[j])) for r in g if f(r[i]) is not None and f(r[j]) is not None)]
                if len(ys) >= 2 and not (all(a >= b - 1e-12 for a, b in zip(ys, ys[1:])) or all(a <= b + 1e-12 for a, b in zip(ys, ys[1:]))):
                    return False
            return True
        candidates = [None] + [k for k in range(len(h)) if k not in (i, j) and len({r[k] for r in body}) < len(body)]
        if not any(consistent({None: body} if k is None else {v: [r for r in body if r[k] == v] for v in {r[k] for r in body}}) for k in candidates):
            out.append(contract_finding("R", "doubt", path.name, c, f"`{c}` does not order `{m.group(1)}` consistently (neither "
                                        "ascending nor descending, also within each group)"))
    return out


ENUM_LIST = re.compile(r"(?:one of|allowed values:?)\s*((?:`[^`]+`(?:\s*(?:,\s*or|,\s*and|,|or|and|/)\s*)?){2,})", re.I)


def stated_labels(statement: str) -> dict:
    allowed, lines = {}, statement.splitlines()
    for n, s in enumerate(lines):
        m = ENUM_LIST.search(s)
        block = re.search(r"(?:one of|allowed values)\s*:\s*$", s, re.I)
        if not m and not block:
            continue
        if m:
            labels = {x.strip('"\'') for x in re.findall(r"`([^`]+)`", m.group(1))}
            head = s[:m.start()]
        else:
            labels, head = set(), s[:block.start()]
            base = len(s) - len(s.lstrip()) if re.match(r"\s*(?:[-*+]|\d+[.)])\s", s) else -1
            for line in lines[n + 1:]:
                if not line.strip():
                    if labels:
                        break
                    continue
                if not re.match(r"\s*(?:[-*+]|\d+[.)])\s", line) or len(line) - len(line.lstrip()) <= base:
                    break
                if (t := re.match(r"\s*(?:[-*+]|\d+[.)])\s*`([^`]+)`", line)):
                    labels.add(t.group(1).strip('"\''))
        before = re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", head)
        if before and len(labels) >= 2 and not NON_MANDATORY.search(s):
            allowed.setdefault(before[-1], set()).update(labels)
    return allowed


def enum_problems(path, statement: str) -> list[dict]:
    allowed = stated_labels(statement)
    if not allowed:
        return []
    vals = {}
    if path.suffix == ".csv":
        rows = list(csv.reader(io.StringIO(path.read_text(errors="replace"))))
        if rows:
            for i, c in enumerate(rows[0]):
                if c in allowed:
                    vals[c] = {r[i] for r in rows[1:] if i < len(r) and r[i] != ""}
    elif path.suffix == ".json":
        try:
            data = json.loads(path.read_text())
        except ValueError:
            return []

        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in allowed and isinstance(v, str):
                        vals.setdefault(k, set()).add(v)
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(data)
    out = []
    for k, vs in vals.items():
        bad = sorted(v for v in vs if v not in allowed[k] and v.lower() not in {a.lower() for a in allowed[k]})
        if bad:
            out.append(contract_finding("E", "definite", path.name, k, f"`{k}` has value(s) {bad[:4]} outside the labels the "
                                        f"task lists: {sorted(allowed[k])[:8]}"))
    return out


DATE_FMT = {"YYYY-MM-DD": r"\d{4}-\d{2}-\d{2}", "YYYY-MM-DDTHH:MM:SSZ": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "YYYYMMDD": r"\d{8}"}
OUT_HEAD = re.compile(r"^#+\s.*(output|deliverable|result|schema|format|convention|rule|note|file)", re.I)
IN_HEAD = re.compile(r"^#+\s.*\b(input|data|source|background|method|step)", re.I)


def output_text(statement: str) -> str:
    keep, on = [], False
    for line in statement.splitlines():
        if line.lstrip().startswith("#"):
            on = bool(OUT_HEAD.match(line.strip())) and not IN_HEAD.match(line.strip())
        elif on:
            keep.append(line)
    return "\n".join(keep)


def stated_dates(statement: str) -> dict:
    rules = {}
    for line in output_text(statement).splitlines():
        if NON_MANDATORY.search(line):
            continue
        for fmt in sorted(DATE_FMT, key=len, reverse=True):
            for m in re.finditer(r"`([A-Za-z_][A-Za-z0-9_]*)`[^`\n]{0,25}?`?%s`?" % re.escape(fmt), line):
                rules.setdefault(m.group(1), fmt)
    return rules


def date_problems(path, statement: str) -> list[dict]:
    rules = stated_dates(statement)
    if not rules or path.suffix != ".csv":
        return []
    rows = list(csv.reader(io.StringIO(path.read_text(errors="replace"))))
    out = []
    for i, c in enumerate(rows[0] if rows else []):
        if c in rules:
            bad = [r[i] for r in rows[1:] if i < len(r) and r[i] and not re.fullmatch(DATE_FMT[rules[c]], r[i])]
            if bad:
                out.append(contract_finding("D", "definite", path.name, c, f"`{c}`: {len(bad)} value(s) not in the stated "
                                            f"format {rules[c]} (e.g. {bad[0]!r})"))
    return out


def dedupe_findings(findings: list[dict]) -> list[dict]:
    seen, out = set(), []
    for f in findings:
        k = (f["rule"], f["file"], f["field"])
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


DATE_COL = re.compile(r"(?:^|_)(?:date|asof|as_of|period|month|rebalance|timestamp|ts)(?:_|$)", re.I)
ITEM_COL = re.compile(r"(?:^|_)(?:id|identifier|ticker|asset|security|symbol|cusip|permno|name)(?:_|$)", re.I)
PRE = re.compile(r"(?:^|_)(?:prev|previous|old|start|before|pre|w_prev|lag)(?:_|$)", re.I)
POST = re.compile(r"(?:^|_)(?:final|executed|new|after|post|end|held|actual|capped|clipped)(?:_|$)", re.I)
TARGET = re.compile(r"(?:^|_)(?:target|raw|desired|ideal|uncapped|unclipped|pre_cap)(?:_|$)", re.I)
WEIGHTISH = re.compile(r"weight|(?:^|_)w(?:_|$)|position|holding|alloc", re.I)
CAP_STMT = re.compile(r"(?P<q>turnover|leverage|weight|position|exposure)[^.\n]{0,80}?(?:<=|\u2264|capped at|cap of|a cap|at most|no more than|(?:must|should|may|does|do) not exceed|maximum of)\s*`?(?P<v>\d*\.\d+|\d+(?:\.\d+)?)(?![\d.]*\s*[*/\u00d7])", re.I)
WHOLE = re.compile(r"whole (?:shares|units|contracts|lots)|floor\(\s*\w*cash|integer (?:shares|contracts|units|lots)|round(?:ed)? down to (?:whole|an integer)", re.I)


def read_table(p) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(io.StringIO(p.read_text(errors="replace"))))
    return (rows[0], [r for r in rows[1:] if r]) if rows else ([], [])


def finite_number(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def near(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-6 + 1e-6 * abs(b)


def first_column(h: list[str], rx, pred=lambda c: True):
    return next((i for i, c in enumerate(h) if rx.search(c) and pred(c)), None)


def state_tables(tables: dict) -> list[tuple]:
    out = []
    for name, (h, body) in tables.items():
        di, ii = first_column(h, DATE_COL), first_column(h, ITEM_COL)
        w = lambda c: bool(WEIGHTISH.search(c))
        pi, fi, ti = first_column(h, PRE, w), first_column(h, POST, w), first_column(h, TARGET, w)
        if di is not None and ii is not None and pi is not None and fi is not None:
            out.append((name, di, pi, fi, ti))
    return out


def per_date_moves(body: list[list[str]], di: int, a: int, b: int) -> dict:
    s = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in body:
        x, y = (finite_number(r[a]) if a < len(r) else None), (finite_number(r[b]) if b < len(r) else None)
        if x is None or y is None:
            continue
        t = s[r[di]]
        t[0] += abs(y - x)
        t[1] += abs(y)
        t[2] += y
    return s


def reported_vs_executed(d: str, statement: str) -> list[dict]:
    out, tables = [], {p.name: read_table(p) for p in sorted(pathlib.Path(d).glob("*.csv"))}
    for sname, di, pi, fi, ti in state_tables(tables):
        h0, b0 = tables[sname]
        post, pre_t = per_date_moves(b0, di, pi, fi), (per_date_moves(b0, di, pi, ti) if ti is not None else {})
        for name, (h, body) in tables.items():
            dj = first_column(h, DATE_COL)
            if dj is None:
                continue
            for qrx, k in ((re.compile(r"turnover", re.I), 0), (re.compile(r"gross.*(?:leverage|exposure)|leverage", re.I), 1),
                           (re.compile(r"(?:net|dollar).*exposure", re.I), 2)):
                qi = first_column(h, qrx)
                if qi is None or (name == sname and qi in (pi, fi)):
                    continue
                for r in body:
                    if r[dj] not in post or (v := finite_number(r[qi])) is None:
                        continue
                    want = post[r[dj]][k]
                    ok = near(v, want) or (k == 0 and near(v, 0.5 * want))
                    if not ok:
                        tgt = pre_t.get(r[dj], [None] * 3)[k]
                        hint = (f"; it matches the pre-constraint `{h0[ti]}` ({tgt:.6g}" + (" or half of it" if k == 0 else "") + ")"
                                if tgt is not None and (near(v, tgt) or (k == 0 and near(v, 0.5 * tgt))) else "")
                        out.append(contract_finding("S", "doubt", name, h[qi], f"{name} {r[dj]}: `{h[qi]}` = {v:.6g}, but the "
                                                    f"written `{h0[pi]}` \u2192 `{h0[fi]}` in {sname} give {want:.6g}"
                                                    + (" (or half for one-way)" if k == 0 else "") + hint))
    for m in CAP_STMT.finditer(statement):
        q, cap = m.group("q").lower(), float(m.group("v"))
        for name, (h, body) in tables.items():
            for i, c in enumerate(h):
                if q in c.lower() and not re.search(r"cap|limit|max_|threshold|target|raw|pre", c, re.I):
                    over = [r[i] for r in body if i < len(r) and (v := finite_number(r[i])) is not None and abs(v) > cap + 1e-6]
                    if over and cap < 10:
                        out.append(contract_finding("C", "definite", name, c, f"{name}: `{c}` exceeds the stated limit {cap} "
                                                    f"on {len(over)} row(s) (first {over[0]}); apply the limit in the step that "
                                                    "produces these values and recompute everything derived from them, rather "
                                                    "than editing the reported numbers"))
    if WHOLE.search(statement):
        for name, (h, body) in tables.items():
            for k, c in enumerate(h):
                if (re.fullmatch(r"(?:\w+_)?(?:shares|qty|quantity|contracts|lots|units)(?:_\w+)?", c, re.I)
                        and not re.search(r"pct|ratio|frac|share_of|_per_|price|value|dollar|weight", c, re.I)):
                    frac = [r[k] for r in body if k < len(r) and (v := finite_number(r[k])) is not None and abs(v - round(v)) > 1e-9]
                    if frac:
                        out.append(contract_finding("W", "definite", name, c, f"{name}: `{c}` has {len(frac)} non-integer "
                                                    f"value(s) (e.g. {frac[0]}) where the task trades whole units; use whole "
                                                    "units in the step that sizes the positions and recompute what depends on them"))
    return dedupe_findings(out)


UNAMBIGUOUS = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`[^`\n]{0,200}?\bunambiguous\s+(?:\w+\s+)?encoding", re.I)
LIST_DELIMITERS = (",", ";", "|")


def encoding_problems(path, statement):
    fields = {m.group(1) for m in UNAMBIGUOUS.finditer(statement)}
    if not fields:
        return []
    values = []
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text())
        except ValueError:
            return []
        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in fields and isinstance(v, str): values.append((k, v))
                    walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        walk(data)
    elif path.suffix == ".csv":
        rows = list(csv.reader(io.StringIO(path.read_text(errors="replace"))))
        if rows:
            for i, c in enumerate(rows[0]):
                if c in fields:
                    values += [(c, r[i]) for r in rows[1:] if i < len(r) and r[i].strip()]
    out, seen = [], set()
    for k, v in values:
        s = v.strip()
        if k in seen or s.startswith(("[", "(")) or any(d in s for d in LIST_DELIMITERS):
            continue
        if re.search(r"\s*-\s*|\s+/\s+|\s+and\s+|:", s):
            seen.add(k)
            out.append(contract_finding("L", "definite", path.name, k, f"`{k}` is written as one joined string ({s[:60]!r}); the task asks for an "
                                                             "unambiguous encoding, so write the items as a list, e.g. [\"A\", \"B\"]"))
    return out


def listed_columns(statement, fname):
    lines = statement.splitlines()
    for i, l in enumerate(lines):
        if l.lstrip().startswith("#") and fname in l:
            cols, on = [], False
            for m in lines[i + 1:]:
                if m.lstrip().startswith("#"):
                    break
                if re.match(r"\s*Columns\s*:\s*$", m, re.I):
                    on = True
                    continue
                if not on:
                    continue
                t = re.match(r"\s*(?:[-*]|\d+[.)])\s*`([^`]+)`\s*$", m)
                inline = re.fullmatch(r"\s*`([^`]*,[^`]*)`\s*", m)
                if t:
                    cols.append(t.group(1))
                elif inline and not cols:
                    cols = [c.strip() for c in inline.group(1).split(",") if c.strip()]
                    break
                elif m.strip() and cols:
                    break
            names = [c for c in cols if c not in ("...", "\u2026")]
            patterns = []
            for k, c in enumerate(cols):
                if c in ("...", "\u2026") and 0 < k < len(cols) - 1:
                    a, b = re.fullmatch(r"(.*?)(-?\d+)", cols[k - 1]), re.fullmatch(r"(.*?)(-?\d+)", cols[k + 1])
                    if a and b and a.group(1) == b.group(1):
                        patterns.append(re.compile(re.escape(a.group(1)) + r"-?\d+"))
            return names, patterns
    return [], []


def extra_column_problems(path, statement):
    if path.suffix != ".csv":
        return []
    cols, patterns = listed_columns(statement, path.name)
    if not cols:
        return []
    header = next(csv.reader(io.StringIO(path.read_text(errors="replace"))), [])
    extra = [c for c in header if c not in cols and not any(p.fullmatch(c) for p in patterns)]
    if not extra:
        return []
    return [contract_finding("X", "definite", path.name, extra[0], f"columns not in the task's column list for {path.name}: {', '.join(extra[:6])}; "
                                                           "drop working columns from the deliverable")]


CONTRACT_CHECKS = (unit_problems, rank_problems, enum_problems, date_problems, encoding_problems, extra_column_problems)


def output_findings(d: str, statement: str) -> list[dict]:
    try:
        out = [q for p in sorted(pathlib.Path(d).glob("*")) if p.suffix in (".json", ".csv")
               for check in CONTRACT_CHECKS for q in check(p, statement)]
        return dedupe_findings(out + reported_vs_executed(d, statement))
    except Exception as exc:
        print(f"[solver] output_findings error: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
        return []


HEADING = re.compile(r"^\s*(#{1,6})\s")


def starts_with_other_file(line: str, name: str, files: list[str], cites) -> bool:
    m = re.match(r"\s*`([^`]+)`", line)
    return bool(m) and any(cites(f, m.group(1)) for f in files if f != name)


def file_entries(statement: str, sections: list[dict], files: list[str], cites) -> list[tuple[str, str]]:
    lines = statement.splitlines()
    out = []
    for name in files:
        entry = "(no entry found in the task's output section; read the task text)"
        own = [i for i, l in enumerate(lines) if HEADING.match(l) and (re.findall(r"`([^`]+)`", l) or [""])[0].endswith(name)]
        if own:
            s = own[0]
            level = len(HEADING.match(lines[s]).group(1))
            e = s + 1
            while e < len(lines) and not (HEADING.match(lines[e]) and len(HEADING.match(lines[e]).group(1)) <= level):
                e += 1
            out.append((name, f"(task lines {s + 1}-{e}, as written)\n" + "\n".join(lines[s:e]).strip()))
            continue
        for sec in sections:
            a, b = sec["line_start"] - 1, sec["line_end"]
            hits = [i for i in range(a, b) if cites(name, lines[i])]
            if not hits:
                continue
            heads = [i for i in hits if NEW_ITEM.match(lines[i]) and name in (re.findall(r"`([^`]+)`", lines[i]) or [lines[i]])[0]]
            s = (heads or hits)[0]
            e = s + 1
            while e < b and not ((NEW_ITEM.match(lines[e]) and (lines[e].lstrip().startswith("#") or lines[e].strip().startswith("---")
                                                               or any(cites(m, lines[e]) for m in files if m != name)))
                                 or starts_with_other_file(lines[e], name, files, cites)):
                e += 1
            while e > s + 1 and not lines[e - 1].strip():
                e -= 1
            entry = f"(task lines {s + 1}-{e}, as written)\n" + "\n".join(lines[s:e])
            break
        out.append((name, entry))
    return out


def output_requirements(model) -> tuple[list[tuple[str, str]], int]:
    spent = [0]

    def ask(system: str, user: str) -> tuple[str, dict]:
        spent[0] += 1
        charge_driver_request()
        reply = litellm.completion(model=model.config.model_name, messages=[{"role": "system", "content": system},
                                                                             {"role": "user", "content": user}],
                                   **model.config.model_kwargs)
        choice = reply.choices[0]
        return choice.message.content or "", {"finish_reason": choice.finish_reason}

    try:
        v31, v85 = _verifier_modules()
        run_dir = v31.build(pathlib.Path(INPUT_DIR), pathlib.Path(VERIFIER_WORK) / "builds", ask, v31.PROMPTS,
                            FILE_LIST_REQUESTS, record=True)
        made = json.loads((run_dir / "construction.json").read_text())
        if made["status"] != "OK" or not made["files"]:
            print(f"[solver] output requirements not found: file list {made['status']}", flush=True)
            return [], spent[0]
        statement = pathlib.Path(TASK_STATEMENT).read_text()
        files = list(dict.fromkeys(OUTPUT_ROOT_PREFIX.sub("", name) for name in made["files"]))
        sections = v85.oc.extract(statement, v85.v81.v8.ins.index(statement)["sections"], files,
                                  matches_name=v85.v81.cites_name)["sections"]
        entries = file_entries(statement, sections, files, v85.v81.cites_name)
    except Exception as exc:
        print(f"[solver] output requirements not found: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
        return [], spent[0]
    print(f"[solver] output requirements: {len(files)} file(s), {spent[0]} request(s) in the driver count", flush=True)
    return entries, spent[0]


def install_repl_tools(model) -> None:
    if isinstance(model, LitellmTextbasedModel):
        model._parse_actions = lambda response: parse_text_actions(model, response)
    else:
        def query(messages, **kwargs):
            return litellm.completion(model=model.config.model_name, messages=messages, tools=[BASH_TOOL, PYTHON_TOOL] + ([FIX_LINE_TOOL] if FIX_LINE_ON else []),
                                      **(model.config.model_kwargs | kwargs))
        model._query = query
        model._parse_actions = lambda response: parse_tool_actions(model, response)
        model.config.format_error_template = FORMAT_ERROR_TEMPLATE
    model.repl_tools_installed = True


class GatedAgent(DefaultAgent):

    def __init__(self, *args, gate: Callable[["GatedAgent"], str | None] | None = None,
                 max_gate_rounds: int = 1, final_verdict_call: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        if REPL_TOOL and not getattr(self.model, "repl_tools_installed", False):
            raise RuntimeError("REPL_TOOL is on but install_repl_tools(model) was not called before the agent was built")
        self.gate = gate
        self.max_gate_rounds = max_gate_rounds
        self.final_verdict_call = final_verdict_call
        self.gate_rounds = 0
        self.gate_history: list[str] = []
        self.final_verdict: str | None = None
        self.reminded = False
        self.status_sent: set[int] = set()
        self.entries: list[tuple[str, str]] = []
        self.submit_problems: list[str] | None = None
        self.doubts_listed: dict[tuple, str] = {}
        self.doubts_shown = False
        self.kernel: Kernel | None = None
        self.prepared = False
        self.notes = ""
        self.held_watch: str | None = None

    def run(self, task: str = "", **kwargs) -> dict:
        env = os.environ | dict(self.env.config.env)
        task = task.replace("Save scripts and scratch files in /tmp/work", "Save scratch files in /tmp/work")
        if TASK_TAG:
            task = tag_task_text(task)
        self.notes = task_notes(task) if STATUS_NOTES_ON else ""
        if preview := data_preview(env):
            task = task + "\n\n" + preview
        with contextlib.suppress(Exception):
            if linted := OC7["rootcause/template_lint.py"]["template_lint_notes"](DATA_DIRS):
                task = task + "\n\nNotes on the supplied scripts (static facts, nothing was run):\n" + "\n".join(linted)
                print(f"[solver] supplied-script lint: {len(linted)} note(s)", flush=True)
        if dated := descending_notes(DATA_DIRS):
            task = task + "\n\n" + "\n".join(dated)
            print(f"[solver] descending-date note: {len(dated)} file(s)", flush=True)
        if zips := zip_inputs():
            task = task + "\n\n" + ZIP_NOTE
            print(f"[solver] zip note: {zips}", flush=True)
        if scripts := script_inputs():
            root = next((d for d in DATA_DIRS if os.path.isdir(d)), DATA_DIRS[0])
            task = task + "\n\n" + SCRIPT_NOTE.format(names=", ".join(scripts), root=root)
            print(f"[solver] script note: {scripts}", flush=True)
        if os.path.exists(FILING_IO) and (filings := inline_xbrl_inputs()):
            task = task + "\n\n" + FILING_NOTE.format(names=", ".join(filings))
            print(f"[solver] filing note: {filings}", flush=True)
            if preview := filing_preview(env, filings):
                task = task + "\n\n" + preview
                print(f"[solver] filing preview: {len(preview)} characters", flush=True)
        self.entries, spent = output_requirements(self.model)
        REQUIRED_NAMES[:] = [n for n, _ in self.entries]
        reference = reference_block()
        if reference:
            task = task + "\n\n" + reference
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            library = library_block()
        print(capture.getvalue(), end="", flush=True)
        chosen_libs = re.search(r"LibraryReference attached: \[(.*?)\]", capture.getvalue())
        if library:
            task = task + "\n\n" + library
        if secondary := rag_secondary_block(set(re.findall(r"'([^']+)'", chosen_libs.group(1))) if chosen_libs else set(),
                                            reference):
            task = task + "\n\n" + secondary
        self.output_preview_requests = spent
        if self.config.step_limit:
            self.config.step_limit = max(1, self.config.step_limit - spent)
        try:
            if REPL_TOOL:
                files = [n for n, _ in self.entries]
                keys = {os.path.basename(n): json_key_names(e, files) for n, e in self.entries if n.lower().endswith(".json")}
                with open(EXPECTED_KEYS, "w") as f:
                    json.dump({n: k for n, k in keys.items() if k}, f)
                self.kernel = Kernel(cwd=self.env.config.cwd or os.getcwd(),
                                     env=env | {"PYTHONPATH": os.pathsep.join(filter(None, [QFREF_ROOT, SESSION_IO_ROOT, env.get("PYTHONPATH")])),
                                                "MSW_EXPECTED_KEYS": EXPECTED_KEYS})
                if self.config.wall_time_limit_seconds:
                    self.kernel.deadline = self._start_time + self.config.wall_time_limit_seconds - WALL_CLOCK_MARGIN_SECONDS
                self.kernel.start()
                self.kernel.preloads = [D2_PRELOAD]
                with contextlib.suppress(Exception):
                    self.session_probe(D2_PRELOAD)
                with contextlib.suppress(Exception):
                    if oc9 := OC7.get("oc9/oc9_checks.py"):
                        self.session_probe(oc9["NAT_PRELOAD"])
                    if ph := OC7.get("pandas_hook/pandas_hook.py"):
                        self.session_probe("exec(compile(%r, '<oc_hook>', 'exec'), globals())" % ph["HOOK_CODE"])
                SESSION_PROBE[:] = [self.session_probe]
                self.env = ReplEnvironment(self.env, self.kernel)
                imports = "\n".join("  " + s for s in self.kernel.imported) or "  (none)"
                self.config.system_template = ("{% raw %}" + fix_line_system(REPL_SYSTEM_TEMPLATE).replace("<PREIMPORTS>", imports)
                                               + ("\n\n" + TASK_TAG_NOTE if TASK_TAG else "") + "{% endraw %}")
            self.prepared = True
            return super().run(task, **kwargs)
        finally:
            clean_output_tree({n for n, _ in self.entries})
            if self.kernel is not None:
                self.kernel.close()

    def query(self) -> dict:
        if not self.prepared:
            raise RuntimeError("the agent was queried before run() prepared it")
        limit = self.config.step_limit
        if limit and not self.reminded and self.n_calls >= limit - REMIND_BEFORE_LIMIT:
            self.reminded = True
            text = REMINDER.format(used=self.n_calls, limit=limit)
            if self.entries:
                text += "\n\n" + self.files_block()
                if problems := self.file_problem_list():
                    text += "\n\n" + REMINDER_PROBLEMS.format(problems="\n".join(problems))
            self.add_messages({"role": "user", "content": text})
            print(f"[solver] wrap-up reminder with file status after reply {self.n_calls}", flush=True)
        elif (limit and self.n_calls and self.n_calls % STATUS_EVERY == 0 and self.n_calls not in self.status_sent
              and isinstance(self.messages[-1].get("content"), str)):
            self.status_sent.add(self.n_calls)
            total = (self.config.wall_time_limit_seconds or 0) / 60
            line = STATUS_LINE.format(used=self.n_calls, limit=limit, left=limit - self.n_calls,
                                      elapsed=round((time.time() - self._start_time) / 60), total=round(total))
            if self.entries:
                missing = [n for n, _ in self.entries
                           if not (os.path.isfile(p := os.path.join(OUTPUT_DIR, n)) and os.path.getsize(p) > 0)]
                if self.n_calls == EXTRACTION_SAVE_AT and len(missing) == len(self.entries) and extraction_task():
                    line += "\n\n" + EXTRACTION_SAVE.format(files=", ".join(missing))
                    print(f"[solver] extraction save request after reply {self.n_calls}: {missing}", flush=True)
                if self.n_calls == EARLY_SAVE_AT and missing:
                    line += "\n\n" + EARLY_SAVE.format(files=", ".join(missing))
                    print(f"[solver] early-save request after reply {self.n_calls}: {missing}", flush=True)
                line += "\n\n" + self.files_block()
                found = self.contract_findings()
                new = [q for q in found if self.doubts_listed.get((q["rule"], q["file"], q["field"])) != q["msg"]]
                self.doubts_listed.update(((q["rule"], q["file"], q["field"]), q["msg"]) for q in new)
                if definite := [q for q in new if q["tier"] == "definite"]:
                    line += "\n\n" + STATUS_DEFINITE + "\n" + "\n".join(f"- {q['file']}: {q['msg']}" for q in definite)
                if doubts := [q for q in new if q["tier"] == "doubt"]:
                    line += "\n\n" + STATUS_DOUBTS + "\n" + "\n".join(f"- {q['file']}: {q['msg']}" for q in doubts)
            if self.notes:
                line += "\n\n" + STATUS_NOTES + "\n" + self.notes
            self.messages[-1]["content"] += "\n\n" + line
            print(f"[solver] status line after reply {self.n_calls}", flush=True)
        try:
            reply = super().query()
            self.trunc_streak = 0
            return reply
        except FormatError as exc:
            if exc.messages and "finish_reason=length" in str(exc.messages[0].get("content", "")):
                self.trunc_streak = getattr(self, "trunc_streak", 0) + 1
                if not REPL_TOOL:
                    exc.messages[0]["content"] = TRUNCATED
                elif self.reminded:
                    exc.messages[0]["content"] = TRUNCATED_AFTER_REMINDER
                elif self.trunc_streak >= 2:
                    missing = [n for n, _ in self.entries
                               if not (os.path.isfile(p := os.path.join(OUTPUT_DIR, n)) and os.path.getsize(p) > 0)]
                    exc.messages[0]["content"] = T1_NOTE.format(
                        n=self.trunc_streak, names=session_names() or "(none yet)",
                        first_missing_file=f"`{os.path.basename(missing[0])}`" if missing else "the next required file")
                    print(f"[solver] truncation chain note after {self.trunc_streak} cut replies", flush=True)
                else:
                    exc.messages[0]["content"] = TRUNCATED_REPL
                self.trunc_chain(exc)
                self.split_files(exc)
            else:
                self.trunc_streak = 0
            raise

    def trunc_chain(self, exc) -> None:
        try:
            note = exc.messages[0]
            extra = note.setdefault("extra", {})
            info = TRUNC["cut_info"](extra.get("response") or {})
            extra["cut_reply"] = {k: v for k, v in info.items() if k != "code"}
            print(TRUNC["log_line"](info, self.trunc_streak), flush=True)
            if TRUNC_VERSION not in TRUNC["VERSIONS"] or not REPL_TOOL:
                return
            ran = self.trunc_run_defs(info["code"]) if TRUNC_VERSION == "V3" and info["code"] else []
            if TRUNC_VERSION in ("V2", "V3") and not self.reminded:
                note["content"] = TRUNC["SPLIT"].format(names=session_names() or "(none yet)")
            held = {"role": "assistant", "content": TRUNC["placeholder"](info, ran),
                    "extra": {"cut_placeholder": True, "cost": extra.pop("cost", 0.0)}}
            exc.messages = (held, note)
            print(f"[solver] cut reply kept as a {TRUNC_VERSION} placeholder; defs run: {ran}", flush=True)
        except Exception as e:
            print(f"[solver] cut reply handling skipped: {type(e).__name__}: {str(e)[:120]}", flush=True)

    def split_files(self, exc) -> None:
        try:
            if self.reminded or not REPL_TOOL or not self.entries:
                return
            response = next((m["extra"]["response"] for m in exc.messages if (m.get("extra") or {}).get("response")), None)
            missing = [n for n, _ in self.entries
                       if not (os.path.isfile(p := os.path.join(OUTPUT_DIR, n)) and os.path.getsize(p) > 0)]
            files = split_files_due(SPLIT_FILES_VERSION, cut_text(response or {}), missing, self.trunc_streak)
            if files:
                note = split_files_note(SPLIT_FILES_VERSION, files, session_names() or "(none yet)")
                exc.messages = (*exc.messages, {"role": "user", "content": note})
                print(f"[solver] split-files note {SPLIT_FILES_VERSION}: {files}", flush=True)
        except Exception as e:
            print(f"[solver] split-files note skipped: {type(e).__name__}: {str(e)[:120]}", flush=True)

    def trunc_run_defs(self, code: str) -> list:
        if self.kernel is None or self.kernel.proc is None:
            return []
        out = self.session_probe("print('TRUNC_HAVE', sorted(k for k in globals() if not k.startswith('_')))")
        m = re.search(r"TRUNC_HAVE (\[.*\])", out or "")
        try:
            have = set(ast.literal_eval(m.group(1))) if m else set()
        except (ValueError, SyntaxError):
            have = set()
        ran = []
        for name, src in TRUNC["complete_defs"](code):
            if name in have or not src:
                continue
            cell, gen = self.kernel.cell, self.kernel.generation
            try:
                res = self.kernel.run(src)
            except Exception:
                continue
            if self.kernel.generation == gen:
                self.kernel.cell = cell
            if res.get("returncode") == 0:
                ran.append(name)
                OK_CODE.append(src)
        return ran

    def misplaced_outputs(self) -> dict:
        dirs = [os.getcwd(), os.path.join(os.getcwd(), "output")] + glob.glob("/tmp/*/") + glob.glob("/tmp/*/output/")
        for root in DATA_DIRS:
            for d, _, names in os.walk(root):
                for n in names:
                    if n.endswith(".py"):
                        try:
                            text = open(os.path.join(d, n), errors="replace").read()
                        except OSError:
                            continue
                        dirs += [m for m in re.findall(r"['\"](/[\w./-]*output[\w./-]*)['\"]", text) if os.path.isdir(m)]
        found = {}
        for n, _ in self.entries:
            if os.path.isfile(os.path.join(OUTPUT_DIR, n)):
                continue
            for d in dict.fromkeys(os.path.abspath(x) for x in dirs):
                if os.path.abspath(d) != os.path.abspath(OUTPUT_DIR) and os.path.isfile(os.path.join(d, n)):
                    found[n] = os.path.join(d, n)
                    break
        return found

    def files_block(self) -> str:
        rows, unnamed = [], False
        for i, (n, block) in enumerate(self.entries, 1):
            written = os.path.isfile(p := os.path.join(OUTPUT_DIR, n)) and os.path.getsize(p) > 0
            body = block.split("\n")
            if body and body[0].startswith("(task lines"):
                body = body[1:]
            if body and re.sub(r"^\s*(?:\d+[.)]|[-*])?\s*|[*`\s]", "", body[0]) in (n, os.path.join(OUTPUT_DIR, n).lstrip("/")):
                body = body[1:]
            block = "\n".join(body)
            unnamed |= (os.path.splitext(n)[1].lower() in (".json", ".csv")
                        and not named_fields(block, [f for f, _ in self.entries]))
            rows.append(f"{i}. {OUTPUT_DIR.rstrip('/')}/{n}  [status: {'written' if written else 'not written yet'}]\n{block}")
        text = STATUS_FILES + ("\n\n" + NAMING_NOTE if unnamed else "") + "\n\n" + "\n\n".join(rows)
        if any(n.lower().endswith(".json") for n, _ in self.entries):
            text += "\n\n" + SAVE_JSON_NOTE
        try:
            misplaced = self.misplaced_outputs()
        except OSError:
            misplaced = {}
        if misplaced:
            text += "\n\n" + MISPLACED_NOTE.format(found="; ".join(f"{n} at {p}" for n, p in misplaced.items()),
                                                     out=OUTPUT_DIR.rstrip("/"))
            print(f"[solver] misplaced outputs: {misplaced}", flush=True)
        return text

    def note_held_rows(self, message: dict, observations: list[dict]) -> list[dict]:
        if self.kernel is None or self.kernel.proc is None:
            return observations
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        m = ZERO_FFILL.search(code)
        if not m:
            return observations
        res = (re.search(r"\b(\w+)\s*=\s*%s\.ffill\(" % re.escape(m.group(1)), code) or m).group(1)
        h = self.held_rows(res)
        if h:
            held, rows = h
            if held * 2 < rows:
                self.held_watch = res
            note = (f"Session check: after this cell, `{res}` has a nonzero row on {held} of its {rows} rows. "
                    "If it holds positions meant to persist between rebalances, every row from the first rebalance on should carry "
                    "the latest target (rows before it may stay flat); then recompute returns, costs and the regression and "
                    "rewrite the output files.")
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + note
                    break
            print(f"[solver] held-rows check on {res}: {held}/{rows}", flush=True)
        return observations

    def note_like_dtype(self, message: dict, observations: list[dict]) -> list[dict]:
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        notes = []
        try:
            for kind, name, line in like_candidates(code):
                if name in LIKE_DTYPE_SHOWN:
                    continue
                kd = self.session_dtype_kind(name)
                if kd is None and kind == "full" and static_int(name, "\n".join(SESSION_CODE)):
                    kd = "i"
                if kd is None or kd not in "iub":
                    continue
                LIKE_DTYPE_SHOWN.add(name)
                if kind == "full":
                    notes.append(f"Session check: `{line}`: `{name}` has an integer dtype, so np.full_like returns an integer "
                                 "array and the decimal fill value is truncated. Pass dtype=float.")
                else:
                    notes.append(f"Session check: `{line}`: `{name}` has an integer dtype inherited from its template; fractional "
                                 "values assigned to it are truncated; pass dtype=float if it should hold real numbers.")
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def session_dtype_kind(self, name: str) -> str | None:
        if self.kernel is None or self.kernel.proc is None or not re.fullmatch(r"[A-Za-z_]\w*", name):
            return None
        cell, gen = self.kernel.cell, self.kernel.generation
        try:
            out = self.kernel.run(f"try:\n    print('LIKEDT', __import__('numpy').asarray({name}).dtype.kind)\n"
                                  "except Exception:\n    print('LIKEDT none')")["output"]
        except Exception:
            return None
        if self.kernel.generation == gen:
            self.kernel.cell = cell
        h = re.search(r"LIKEDT ([a-zA-Z])\b", out)
        return h.group(1) if h and h.group(1) != "n" else None

    def note_dg_code(self, message: dict, observations: list[dict]) -> list[dict]:
        notes = []
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                fires = DG_G["scan"](self.messages)
            for f in fires:
                key = (f["kind"], f["line"], f.get("first", ""))
                if f["kind"] in DG_G_KINDS and key not in DG_G_SHOWN:
                    DG_G_SHOWN.add(key)
                    notes.append(DG_G_KINDS[f["kind"]].replace("{line1}", f.get("first", "")).replace("{line2}", f["line"]))
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def note_float_format(self, message: dict, observations: list[dict]) -> list[dict]:
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        ff = OC7.get("rootcause/float_format_check.py")
        if "float_format" not in code or ff is None or self.kernel is None or self.kernel.proc is None:
            return observations
        notes = []
        try:
            prior = "\n#--cell--\n".join(SESSION_CODE[:-1])
            for frame, fmt, line in ff["float_format_probes"](code, prior):
                if line in FF_SHOWN or not FF_FRAME.fullmatch(frame.strip()):
                    continue
                text = self.session_csv(frame.strip())
                if text and (note := ff["float_format_note"](text, fmt, line)):
                    FF_SHOWN.add(line)
                    notes.append("Output check: " + note)
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def session_csv(self, frame: str) -> str | None:
        cell, gen = self.kernel.cell, self.kernel.generation
        try:
            out = self.kernel.run(f"try:\n    print('FFCSV>>' + ({frame}).to_csv(index=False) + '<<FFCSV')\n"
                                  "except Exception:\n    print('FFCSV none')")["output"]
        except Exception:
            return None
        if self.kernel.generation == gen:
            self.kernel.cell = cell
        m = re.search(r"FFCSV>>(.*)<<FFCSV", out, re.S)
        return m.group(1) if m else None

    def note_structure_early(self, message: dict, observations: list[dict]) -> list[dict]:
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        if not self.entries or not WRITES_FILE.search(code):
            return observations
        notes = []
        try:
            statement = pathlib.Path(TASK_STATEMENT).read_text()
            for n, entry in self.entries:
                p = os.path.join(OUTPUT_DIR, n)
                if not os.path.isfile(p):
                    continue
                found = []
                if n.lower().endswith(".json"):
                    with contextlib.suppress(OSError, ValueError):
                        found += nesting_issues(json.loads(open(p).read()), level_names(entry))
                found += decimal_problems(p, statement)
                found += [q["msg"] for q in enum_problems(pathlib.Path(p), statement) + date_problems(pathlib.Path(p), statement)
                          if q["tier"] == "definite"]
                for f in found:
                    if (n, f) not in STRUCT_SHOWN:
                        STRUCT_SHOWN.add((n, f))
                        notes.append(f"Output check: {n}: {f}")
            if all(os.path.isfile(os.path.join(OUTPUT_DIR, n)) for n, _ in self.entries) and (oc9 := OC7.get("oc9/oc9_checks.py")):
                for msg in oc9["named_field_notes"](OUTPUT_DIR, statement, list(DATA_DIRS)):
                    if ("F1", msg) not in STRUCT_SHOWN:
                        STRUCT_SHOWN.add(("F1", msg))
                        notes.append(msg)
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def note_session_probes(self, message: dict, observations: list[dict]) -> list[dict]:
        oc9 = OC7.get("oc9/oc9_checks.py")
        if oc9 is None or self.kernel is None or self.kernel.proc is None:
            return observations
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        notes = []
        try:
            for entry in (oc9["nat_log_entries"](self.session_probe(NAT_READ_PROBE)) if "to_datetime" in code else []):
                key = "K1:" + "|".join(map(str, entry.get("samples", [])))
                if key not in PROBE_SHOWN:
                    PROBE_SHOWN.add(key)
                    notes.append(oc9["nat_note"](entry))
            if ph := OC7.get("pandas_hook/pandas_hook.py"):
                for key, msg in ph["event_notes"](ph["parse_drain"](self.session_probe(ph["DRAIN_CODE"])), code):
                    if ("PH:" + key) not in PROBE_SHOWN:
                        PROBE_SHOWN.add("PH:" + key)
                        notes.append(msg)
            names = oc9["neglog_names"](code)
            if names:
                for name, low in re.findall(r"C9NEG (\w+) (\S+)", self.session_probe(oc9["neglog_probe"](names))):
                    line = next((x.strip() for x in code.splitlines() if f"log({name})" in x.replace(" ", "")), name)
                    if ("C9:" + line) not in PROBE_SHOWN:
                        PROBE_SHOWN.add("C9:" + line)
                        notes.append(f"Code note: `-np.log({name})` in this cell takes the log of a value <= 0 (minimum {low}), so "
                                     "the result is inf or NaN and any likelihood, score or selection built on it is invalid. "
                                     f"Check the parameter bounds or the transform that produced `{name}`.")
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def note_va_cards(self, message: dict, observations: list[dict]) -> list[dict]:
        if not VA_CARDS_ENABLED or self.kernel is None or self.kernel.proc is None or VA_DOC is None:
            return observations
        if self.reminded:
            return observations
        if any((o.get("extra") or {}).get("returncode") not in (0, None) for o in observations):
            return observations
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        try:
            sites = VA_DOC.va_sites(code)
            if not sites:
                return observations
            try:
                task = pathlib.Path(TASK_STATEMENT).read_text()
            except OSError:
                task = ""
            output = "\n".join(str(o.get("content") or "") for o in observations)
            notes = VA_DOC.va_notes(code, self.kernel.cell, sites, self.session_probe(VA_DOC.va_probe_code(sites)), VA_CARDS,
                                    VA_SEEN, "D2", VA_CARDS_ENABLED, VA_STEPS, VA_PENDING, task=task, output=output)
        except Exception as exc:
            print(f"[solver] va cards skipped: {type(exc).__name__}", flush=True)
            return observations
        if notes:
            print(f"[solver] va card notes: {len(notes)}", flush=True)
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n\n".join(notes)
                    break
        return observations

    def session_probe(self, code: str) -> str:
        cell, gen = self.kernel.cell, self.kernel.generation
        try:
            out = self.kernel.run(code)["output"]
        except Exception:
            return ""
        getattr(self.kernel, "sources", {}).pop(self.kernel.cell, None)
        if self.kernel.generation == gen:
            self.kernel.cell = cell
        return out

    def note_var_v2(self, message: dict, observations: list[dict]) -> list[dict]:
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        if self.kernel is None or self.kernel.proc is None or "var" not in code.lower():
            return observations
        notes = []
        try:
            cell = self.kernel.cell
            var_names = VC2["var_assignments"]("\n".join(SESSION_CODE))
            for line, field, vname, value_dict in VC2["var_writes"](code):
                if line in VAR_V2_SHOWN or not var_names:
                    continue
                var_name, var_line = var_names[-1]
                got = re.search(r"VC2 (\S+) (\S+)", self.session_probe(
                    f"try:\n    print('VC2', repr(float({vname})), repr(float({var_name})))\nexcept Exception:\n    pass"))
                if got and (msg := VC2["var_v2_note"](cell, line, field, vname, float(got.group(1)), var_name, var_line,
                                                      float(got.group(2)), value_dict)):
                    VAR_V2_SHOWN.add(line)
                    VAR_V2_FIELDS.add(field)
                    notes.append(msg)
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def note_count_totals(self, observations: list[dict]) -> list[dict]:
        try:
            items = [x for x in total_mismatch_items(OUTPUT_DIR) if repr(x) not in COUNT_TOTALS_SHOWN]
        except OSError:
            return observations
        notes = []
        try:
            statement = pathlib.Path(TASK_STATEMENT).read_text()
        except OSError:
            statement = ""
        for n, k, v, table, t in items:
            COUNT_TOTALS_SHOWN.add(repr((n, k, v, table, t)))
            try:
                line = VC2["total_line"]("\n".join(SESSION_CODE), k)
                matrix = VC2["summed_matrix"](line) if line else None
                rows = None
                if matrix and self.kernel is not None and self.kernel.proc is not None:
                    got = re.search(r"VC2ROWS (\[.*\])", self.session_probe(
                        f"try:\n    print('VC2ROWS', [float(x) for x in __import__('numpy').asarray({matrix}).sum(axis=1)] "
                        f"if __import__('numpy').asarray({matrix}).ndim == 2 else None)\nexcept Exception:\n    pass"))
                    rows = json.loads(got.group(1)) if got else None
                notes.append(VC2["count_v2_note"](n, k, v, table, t, VC2["cohort_sentence"](statement, table), line, matrix, rows))
            except Exception:
                continue
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def note_joint_selftest(self, message: dict, observations: list[dict]) -> list[dict]:
        if not all((o.get("extra") or {}).get("returncode") in (0, None) for o in observations):
            return observations
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        notes = []
        try:
            at = next((i for i in range(len(self.messages) - 1, -1, -1) if self.messages[i] is message), len(self.messages) - 1)
            for fn, params in joint_functions(code) if "joint" in code.lower() else []:
                if fn not in JOINT_SHOWN:
                    JOINT_SHOWN.add(fn)
                    notes.append(JOINT_NOTE.format(fn=fn, params=", ".join(params), cell_msg=at))
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def note_oc11_cells(self, message: dict, observations: list[dict]) -> list[dict]:
        K2C_THIS_COMMAND.clear()
        code = "\n".join(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                else tc["function"].get("arguments") or {}).get("code") or "")
                          for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
        if not OC11M or not code.strip():
            return observations
        if not all((o.get("extra") or {}).get("returncode") in (0, None) for o in observations):
            with contextlib.suppress(Exception):
                if API_LINT is not None:
                    API_LINT.cell(code, None)
            with contextlib.suppress(Exception):
                if self.kernel is not None and self.kernel.proc is not None and (notes := self.theta_notes(code, self.kernel.cell)):
                    for obs in observations:
                        if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                            obs["content"] += "\n\n" + "\n".join(notes)
                            break
            return observations
        live = self.kernel is not None and self.kernel.proc is not None
        cell = self.kernel.cell if live else len(OK_CODE)
        at = next((i for i in range(len(self.messages) - 1, -1, -1) if self.messages[i] is message), len(self.messages) - 1)
        notes = []
        try:
            for site in API_LINT.cell(code, cell) if API_LINT is not None else []:
                if site["rule"] == "K2c":
                    probe = k2c_probe(code, site["lineno"], site["recv"]) if live else None
                    got = re.search(r"K2CMISS (\[.*\])", self.session_probe(probe)) if probe else None
                    miss = json.loads(got.group(1)) if got else []
                    if miss:
                        keys = ", ".join(f"{k:g}" for k in miss[:-1]) + (" and " if len(miss) > 1 else "") + f"{miss[-1]:g}"
                        API_LINT.shown.add(site["key"])
                        K2C_THIS_COMMAND.append(True)
                        notes.append(K2C_V2.replace("{lineno}", str(site["lineno"])).replace("{N}", str(at))
                                     .replace("{line}", site["line"]).replace("{recv}", site["recv"]).replace("{key}", site["k"])
                                     .replace("{default}", site["default"]).replace("{missing_keys}", keys))
                    continue
                out = self.session_probe(site["probe"]) if site.get("probe") and live else ""
                if site.get("probe") and not live:
                    continue
                if msg := API_LINT.note(site, out):
                    notes.append(msg)
            bc, am, mn = OC11M.get("bermudan_check"), OC11M.get("a102_mapping"), OC11M.get("mapping_note")
            for site in (bc.bermudan_sites(code, SESSION_CODE) if bc and live else []):
                key = ("bermudan", site.get("call") or site.get("line") or json.dumps(site, default=str)[:200])
                if key in OC11_SHOWN:
                    continue
                r = bc.bermudan_result(self.session_probe(bc.bermudan_probe(site)))
                if r:
                    OC11_SHOWN.add(key)
                    notes.append(bc.bermudan_note(site, cell, r, SESSION_CODE))
            for site in (mn.topup_sites(code) if mn and live else []):
                key = ("mapping", site["line_diff"])
                if key in OC11_SHOWN:
                    continue
                got = re.search(r"MAPSKIP (\[.*\])", self.session_probe(mn.topup_probe(site)))
                skipped = json.loads(got.group(1)) if got else []
                if skipped:
                    OC11_SHOWN.add(key)
                    notes.append((am.a102_note(site, cell, skipped, SESSION_CODE) if am else None)
                                 or mn.mapping_note(site, cell, skipped))
            notes += self.theta_notes(code, cell) if live else []
            if (_tm := triage_module()) is not None and hasattr(_tm, 'KdeBandwidth'):
                _to = TRIAGE_OBJECTS.setdefault('KdeBandwidth', getattr(_tm, 'KdeBandwidth')())
                notes += triage_items(_to.cell(code, cell))
            notes += triage_notes('scale_mismatch_notes', OUTPUT_DIR) if WRITES_FILE.search(code) else []
            notes += triage_notes('loc_window_notes', code, cell)
            notes += triage_notes('baw_coef_notes', code, cell)
            notes += triage_notes('global_param_notes', code, cell)
            notes += triage_notes('argmax_hit_notes', code, cell)
            notes += triage_notes('partial_row_ffill_notes', code, cell)
            notes += triage_notes('empty_bars_notes', code, cell, probe=self.session_probe if live else None)
            notes += triage_notes('neg_index_notes', code, cell)
            notes += triage_notes('lattice_prob_notes', code, cell)
            if (_tm := triage_module()) is not None and hasattr(_tm, 'EwmaParity'):
                _to = TRIAGE_OBJECTS.setdefault('EwmaParity', getattr(_tm, 'EwmaParity')())
                notes += triage_items(_to.cell(code, cell))
            notes += triage_notes('exercise_boundary_notes', code, cell, probe=self.session_probe if live else None)
            notes += triage_notes('direction_sign_notes', code, probe=self.session_probe if live else None)
            notes += triage_notes('array_cell_notes', OUTPUT_DIR) if WRITES_FILE.search(code) else []
            if live and (_tm := triage_module()) is not None and (_tp := getattr(_tm, 'degree_day_probe')(pathlib.Path(TASK_STATEMENT).read_text())):
                notes += triage_notes('degree_day_notes', self.session_probe(_tp), pathlib.Path(TASK_STATEMENT).read_text())
            notes += triage_notes('kappa_log_notes', code, pathlib.Path(TASK_STATEMENT).read_text(), probe=self.session_probe if live else None)
            notes += triage_notes('weight_cap_notes', code, probe=self.session_probe if live else None)
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def theta_notes(self, code: str, cell) -> list[str]:
        th, out = OC11M.get("theta_convention"), []
        for site in th.theta_sites(code) if th else []:
            if ("theta", cell) in OC11_SHOWN:
                break
            r = th.theta_result(self.session_probe(th.theta_probe(site)))
            if r:
                OC11_SHOWN.add(("theta", cell))
                TRIAGE_SHOWN.add(tuple(getattr(th, "SIGN_FAMILY_KEY", ("sign-convention", "theta"))))
                out.append(th.theta_note(site, r, code, SESSION_CODE, OUTPUT_DIR))
        return out

    def note_dupcols(self, message: dict, observations: list[dict]) -> list[dict]:
        t4 = OC11M.get("oc11a_checks")
        if t4 is None or self.kernel is None or self.kernel.proc is None or not any(
                (tc.get("function") or {}).get("name") == "python" for tc in message.get("tool_calls") or []):
            return observations
        notes = []
        try:
            for entry in t4.dupcol_entries(self.session_probe(t4.DUPCOL_PROBE)):
                key = "T4:" + entry["name"] + ":" + entry["dups"][0]
                if key not in PROBE_SHOWN:
                    PROBE_SHOWN.add(key)
                    notes.append(t4.dupcol_note(entry))
        except Exception:
            return observations
        if notes:
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + "\n".join(notes)
                    break
        return observations

    def held_rows(self, name: str) -> tuple[int, int] | None:
        if self.kernel is None or self.kernel.proc is None or not re.fullmatch(r"\w+", name):
            return None
        cell, gen = self.kernel.cell, self.kernel.generation
        try:
            out = self.kernel.run(f"try:\n    print('HELD', int(({name}.fillna(0) != 0).any(axis=1).sum()), len({name}))\n"
                                  "except Exception:\n    print('HELD none')")["output"]
        except Exception:
            return None
        if self.kernel.generation == gen:
            self.kernel.cell = cell
        h = re.search(r"HELD (\d+) (\d+)", out)
        return (int(h.group(1)), int(h.group(2))) if h else None

    def file_problem_list(self) -> list[str]:
        return self._file_problem_list() + ["- " + p for p in SCRIPT_EDIT_V2["unused_helper_problems"]()]

    def _file_problem_list(self) -> list[str]:
        files = [n for n, _ in self.entries]
        try:
            statement = pathlib.Path(TASK_STATEMENT).read_text()
        except OSError:
            statement = ""
        out = [f"- {n}: {p}" for n, entry in self.entries for p in file_problems(os.path.join(OUTPUT_DIR, n), entry, files, statement)]
        out += [f"- {n}: {p}" for n, p in copied_key_problems([(n, e) for n, e in self.entries], OUTPUT_DIR)]
        out += [f"- {n}: {p}" for n, p in total_mismatch_problems(OUTPUT_DIR)]
        out += [f"- {q['file']}: {q['msg']}" for q in output_findings(OUTPUT_DIR, statement) if q["tier"] == "definite"]
        if self.held_watch and (h := self.held_rows(self.held_watch)) and h[0] * 2 < h[1]:
            out.append(f"- session: `{self.held_watch}` (filled with 0, then forward-filled) has a nonzero row on only {h[0]} of "
                       f"{h[1]} rows; if it holds positions meant to persist between rebalances, rebuild it from NaN, recompute "
                       "the returns and every output, and rewrite the files")
        with contextlib.suppress(Exception):
            if (mod := triage_module()) is not None and hasattr(mod, 'placeholder_zero_notes'):
                out += ["- " + r["note"] for r in mod.placeholder_zero_notes(OUTPUT_DIR, list(SESSION_CODE))]
        with contextlib.suppress(Exception):
            if (mod := triage_module()) is not None and hasattr(mod, 'utc_z_notes'):
                out += ["- " + r["note"] for r in mod.utc_z_notes(OUTPUT_DIR, pathlib.Path(TASK_STATEMENT).read_text())]
        with contextlib.suppress(Exception):
            if (mod := triage_module()) is not None and hasattr(mod, 'template_run_problems'):
                out += ["- " + p for p in mod.template_run_problems(TEMPLATE_WRITES, OUTPUT_DIR)]
        return out

    def contract_findings(self) -> list[dict]:
        try:
            statement = pathlib.Path(TASK_STATEMENT).read_text()
        except OSError:
            statement = ""
        return output_findings(OUTPUT_DIR, statement)

    def doubt_findings(self) -> list[dict]:
        return [q for q in self.contract_findings() if q["tier"] == "doubt"]

    def note_double_lag(self, message: dict, observations: list[dict]) -> list[dict]:
        parts = []
        for tc in message.get("tool_calls") or []:
            try:
                raw = tc["function"].get("arguments")
                parts.append(str((json.loads(raw) if isinstance(raw, str) else raw or {}).get("code") or ""))
            except (ValueError, AttributeError, KeyError, TypeError):
                continue
        code = re.sub(r"#[^\n]*", "", "\n".join(parts))
        seen = getattr(self, "lag_code", "")
        self.lag_code = seen + "\n" + code
        if getattr(self, "lag_note_shown", False):
            return observations
        if DOUBLE_LAG_PATTERN.search(code):
            self.lag_note_shown = True
        elif lag_paired(self.lag_code) and not lag_paired(seen):
            self.lag_note_shown = True
            source, read = lag_lines(self.lag_code)
            try:
                timing = TIMING_SENTENCE.search(pathlib.Path(TASK_STATEMENT).read_text())
            except OSError:
                timing = None
            task = f' The task says: "{timing.group(0).strip()[:200]}"' if timing else ""
            where = "this cell" if source in code else "an earlier cell"
            note = DOUBLE_LAG_ACROSS.format(source=source[:160], where=where, read=read[:160], task=task)
            print("[solver] double-lag note across cells", flush=True)
            for obs in observations:
                if isinstance(obs.get("content"), str) and obs.get("extra") is not None:
                    obs["content"] += "\n\n" + note
                    break
        return observations

    def execute_actions(self, message: dict) -> list[dict]:
        try:
            since = time.time() - 1
            observations = note_path_errors(note_version_errors(super().execute_actions(message)))
            observations = note_script_edits(self.note_held_rows(message, observations), since)
            observations = note_search_miss(message, observations)
            observations = note_reread_template(message, observations, since, self.messages)
            if all((o.get("extra") or {}).get("returncode") in (0, None) for o in observations):
                OK_CODE.extend(str((json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str)
                                    else tc["function"].get("arguments") or {}).get("code") or "")
                               for tc in message.get("tool_calls") or [] if (tc.get("function") or {}).get("name") == "python")
            before = [o.get("content") for o in observations]
            observations = self.note_joint_selftest(message, note_output_tree(note_curve_reprice(message, self.note_count_totals(note_offering(note_num_warnings(message, self.note_like_dtype(message, note_value_checks(self.note_oc11_cells(message, self.note_dupcols(message, self.note_var_v2(message, self.note_va_cards(message, self.note_session_probes(message, self.note_float_format(message, self.note_structure_early(message, self.note_dg_code(message, self.note_double_lag(message, note_code_patterns(message, observations))))))))))))))))))
            if notes := hold_notes(observations, before):
                self.add_messages({"role": "user", "content": "\n\n".join(notes)})
            for note in missing_value_notes(python_code(message),
                                            all((o.get("extra") or {}).get("returncode") in (0, None) for o in observations)):
                print(f"[solver] missing-value note: {note[:60]}", flush=True)
                self.add_messages({"role": "user", "content": note})
            return observations
        except Submitted:
            if self.entries and self.config.step_limit and self.n_calls < self.config.step_limit:
                problems = self.file_problem_list()
                print(f"[solver] submit check: {len(problems)} problem(s)", flush=True)
                if problems and problems != self.submit_problems:
                    self.submit_problems = problems
                    return self.add_messages({"role": "user", "content": SUBMIT_CHECK.format(problems="\n".join(problems))})
                if not problems and not self.doubts_shown and (doubts := self.doubt_findings()):
                    self.doubts_shown = True
                    print(f"[solver] submit doubts: {len(doubts)}", flush=True)
                    listed = "\n".join(f"- {q['file']}: {q['msg']}" for q in doubts)
                    return self.add_messages({"role": "user", "content": SUBMIT_DOUBTS.format(doubts=listed)})
            if self.gate is None:
                raise
            if self.gate_rounds >= self.max_gate_rounds:
                if not self.final_verdict_call:
                    raise
                try:
                    self.final_verdict = self.gate(self)
                except Exception as exc:
                    self.final_verdict = f"gate raised {type(exc).__name__}: {exc}"
                raise
            try:
                feedback = self.gate(self)
            except Exception as exc:
                self.gate_history.append(f"gate raised {type(exc).__name__}: {exc}")
                raise Submitted({"role": "exit", "content": "",
                                 "extra": {"exit_status": "Submitted", "submission": ""}}) from None
            if not feedback:
                raise
            self.gate_rounds += 1
            self.gate_history.append(feedback)
            return self.add_messages({"role": "user", "content": feedback})


def build(model, env, *, gate=None, max_gate_rounds: int = 1, final_verdict_call: bool = True,
          **agent_config):
    if REPL_TOOL:
        install_repl_tools(model)
    env.config.timeout = None
    return GatedAgent(model, env, gate=gate, max_gate_rounds=max_gate_rounds,
                      final_verdict_call=final_verdict_call, **agent_config)
