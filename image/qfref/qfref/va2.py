import ast, copy, os, re

FIX_LINE_TOOL = {"type": "function", "function": {
    "name": "fix_line",
    "description": ("Replace one line that an API check pointed at. Only after an API check message, and only when the line does "
                    "not match the task instructions."),
    "parameters": {"type": "object", "properties": {
        "new_line": {"type": "string", "description": "the full corrected line, written exactly as it should appear in the cell"},
        "reason": {"type": "string", "description": "one sentence quoting the task instructions that require the change"}},
        "required": ["new_line", "reason"]}}}
SYSTEM_LINES = {
    "fix_line": ("- `fix_line`: use it only after an \"API check\" message, when your line does not match what the task "
                 "instructions require. Give the corrected\n  line; the host replaces only that line, reruns that cell and the later cells that use "
                 "its results, and returns their output."),
    "edit_cell": ("- `edit_cell`: use it when a note gives you an exact edit for an earlier cell: it replaces that text in the "
                  "cell and runs the cell again.")}


def tool_list_prompt(system: str, names) -> str:
    words = {3: "three", 4: "four"}
    n = 2 + len(names)
    text = system.replace("You have two tools:", f"You have {words[n]} tools:", 1)
    anchor = "- bash: runs one shell command in a new subshell each time. Use it for file-system work and to submit.\n"
    assert anchor in text, "tool list anchor not found"
    return text.replace(anchor, anchor + "".join(SYSTEM_LINES[x] + "\n" for x in names), 1)


def _strip_comment(s: str) -> str:
    import io, tokenize
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(s).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return s
    for t in toks:
        if t.type == tokenize.COMMENT:
            return s[:t.start[1]].rstrip()
    return s


def _parse(line: str):
    s = _strip_comment(line.strip())
    for wrap in ("{}", "{{{}}}", "({},)"):
        body = s.rstrip(",") if wrap != "{}" else s
        try:
            return ast.parse(wrap.format(body)), wrap
        except SyntaxError:
            continue
    return None, None


def _outer_calls(tree):
    inner = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            for a in list(n.args) + [k.value for k in n.keywords]:
                inner.update(id(x) for x in ast.walk(a) if isinstance(x, ast.Call))
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and id(n) not in inner]


NAN_TWINS = {"nanstd": "std", "nanvar": "var", "nanmean": "mean"}


def _blank_args(tree):
    t = copy.deepcopy(tree)
    for n in ast.walk(t):
        if isinstance(n, ast.Call):
            n.args, n.keywords = [], []
            if isinstance(n.func, ast.Attribute):
                n.func.attr = NAN_TWINS.get(n.func.attr, n.func.attr)
            elif isinstance(n.func, ast.Name):
                n.func.id = NAN_TWINS.get(n.func.id, n.func.id)
    return ast.dump(t)


def check_new_line(old: str, new: str):
    if not isinstance(new, str) or not new.strip():
        return False, "`new_line` is empty; give the whole corrected line."
    t_old, wrap = _parse(old)
    if t_old is None:
        return False, "the current line could not be parsed by the host; edit the cell directly instead of using `fix_line`."
    new_s = _strip_comment(new.strip())
    try:
        t_new = ast.parse(wrap.format(new_s.rstrip(",") if wrap != "{}" else new_s))
    except SyntaxError as e:
        return False, f"`new_line` does not parse ({e.msg}); give the whole corrected line as it should stand in the cell."
    if ast.dump(t_old) == ast.dump(t_new):
        return False, "`new_line` is the same as the current line."
    if _blank_args(t_old) != _blank_args(t_new):
        return False, ("`new_line` changes more than the arguments of the call (the called function or the code around the "
                       "call is different); change only the arguments of that call.")
    a, b = _outer_calls(t_old), _outer_calls(t_new)
    changed = sum(ast.dump(x) != ast.dump(y) for x, y in zip(a, b))
    if changed != 1:
        return False, f"`new_line` changes the arguments of {changed} calls; change only the call the note is about."
    return True, ""


FIX_LINE_BLOCK_OK = False
FIX_LINE_QUOTE_CHECK = False
QUOTE_MIN_WORDS = 8
QUOTE_REFUSED = ("Not applied: quote a sentence from <task_instructions>, not from this API check. If the task instructions do "
                 "not specify which case, the checklist default applies: give reason \"not specified in the task instructions; "
                 "checklist default\".")
CHECKLIST_REASON = re.compile(r"checklist|default applies|say(?:s)?\s+nothing|not\s+specified|unspecified", re.I)
QUOTE_MAX_REFUSALS = 1
FIX_LINE_KEYWORD_RECHECK = False
KEYWORD_REFUSED = ("Not applied yet: <task_instructions> contain \"{sentence}\". Does that sentence describe the quantity this "
                   "line computes? If yes, quote it in reason. If it describes a different quantity, give reason \"does not "
                   "apply: <what that sentence is about>; not specified for this line; checklist default\".")
NO_REQUIREMENT = re.compile(r"not\s+(?:explicitly\s+)?stated|(?:do|does|did)\s+not\s+(?:explicitly\s+)?(?:state|specify|say|mention)|"
                            r"no\s+explicit|not\s+explicitly|not\s+specified|unspecified", re.I)
DOES_NOT_APPLY = re.compile(r"^\s*[\"']?does not apply\s*:\s*\S", re.I)


def keyword_in_task(fn: str, statement: str):
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", statement or "") if x.strip()]
    if not hasattr(keyword_in_task, "cards"):
        keyword_in_task.cards = _va_doc().load_cards()
    card = keyword_in_task.cards.get(fn or "", {})
    for p in dict.fromkeys(p for it in card.get("checklist", []) for p in it.get("params", [])):
        for w in _va_doc().LOOK_FOR.get(p, []):
            rx = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(w) + r"(?![A-Za-z0-9-])", re.I)
            hit = next((x for x in sentences if rx.search(x)), None)
            if hit:
                return w, hit
    return None


def _va_doc():
    import importlib.util
    if not hasattr(_va_doc, "mod"):
        here = os.path.dirname(os.path.abspath(__file__))
        path = next(p for p in (os.path.join(here, "va_doc.py"), os.path.join(os.path.dirname(here), "va_doc.py"))
                    if os.path.isfile(p))
        spec = importlib.util.spec_from_file_location("va_doc", path)
        _va_doc.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_va_doc.mod)
    return _va_doc.mod


def _checklist():
    return _va_doc().CHECKLIST_DEFAULTS


def task_driven(fn: str) -> bool:
    if not hasattr(task_driven, "cards"):
        task_driven.cards = _va_doc().load_cards()
    return bool(task_driven.cards.get(fn or "", {}).get("task_driven"))


ALIASES = (("np.", "numpy."), ("pd.", "pandas."), ("sm.", "statsmodels.api."), ("stats.", "scipy.stats."))


def call_name(line: str):
    t, _ = _parse(line)
    calls = _outer_calls(t) if t is not None else []
    if not calls:
        return None
    callee = ast.unparse(calls[0].func)
    for short, full in ALIASES:
        if callee.startswith(short):
            return full + callee[len(short):]
    return callee if callee.startswith(("numpy.", "pandas.", "scipy.")) else None


def sets_checklist_default(fn: str, old: str, new: str) -> bool:
    want = _checklist().get(fn or "")
    if not want:
        return False
    def kws(line):
        t, _ = _parse(line)
        calls = _outer_calls(t) if t is not None else []
        out = {}
        for c in calls[:1]:
            for k in c.keywords:
                try:
                    out[k.arg] = ast.literal_eval(k.value)
                except ValueError:
                    out[k.arg] = None
        return out
    before, after = kws(old), kws(new)
    return any(after.get(p) == v and before.get(p) != v for p, v in want.items())


def block_line(src: str, new: str):
    lines = [l for l in new.split("\n") if l.strip()]
    if len(lines) <= 1:
        return new, None
    have = {l.strip() for l in src.split("\n")}
    differ = [l for l in lines if l.strip() not in have]
    if len(differ) == 1:
        return differ[0], None
    if not differ:
        return None, "`new_line` repeats lines the cell already holds and changes none of them"
    return None, (f"`new_line` is a block in which {len(differ)} lines differ from the cell; give only the one corrected line")


def _words(text: str) -> list:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


def task_text(first_message: str) -> str:
    m = re.search(r"<task_instructions>\n?(.*?)\n?</task_instructions>", first_message or "", re.S)
    return m.group(1) if m else ""


def quotes_task(reason: str, statement: str, fn: str = None, old: str = None, new: str = None):
    if not isinstance(reason, str) or not reason.strip():
        return False, "empty reason"
    if NO_REQUIREMENT.search(reason) or CHECKLIST_REASON.search(reason) or DOES_NOT_APPLY.search(reason):
        if fn and old is not None and new is not None and sets_checklist_default(fn, old, new):
            return True, ""
        if NO_REQUIREMENT.search(reason):
            return False, "the reason says the task instructions state no requirement"
    task = " " + " ".join(_words(statement)) + " "
    quoted = re.findall(r"[\"\u201c\u201d']([^\"\u201c\u201d]{20,}?)[\"\u201c\u201d]", reason)
    for cand in quoted + [reason]:
        w = _words(cand)
        for i in range(len(w) - QUOTE_MIN_WORDS + 1):
            if " " + " ".join(w[i:i + QUOTE_MIN_WORDS]) + " " in task:
                return True, ""
    return False, f"no {QUOTE_MIN_WORDS} consecutive words of the reason occur in the task instructions"


CONSISTENCY_REASON = re.compile(r"consisten|same\s+`?ddof`?|every variance and covariance", re.I)
MIXED_STILL_REFUSED = ("Not applied: after this change the cell still divides its variances and covariances by different "
                       "`ddof` ({calls}). Change the `ddof` of this line's call so it matches the other calls of this cell.")


def consistency_fix(src: str, reason: str) -> bool:
    return _va_doc().mixed_ddof(src) and bool(CONSISTENCY_REASON.search(reason or ""))


def still_mixed(edited: str):
    v = _va_doc()
    if not v.mixed_ddof(edited):
        return None
    return MIXED_STILL_REFUSED.format(calls="; ".join(f"`{c}` uses `ddof={d}`" for c, _, d in v.ddof_calls(edited)))


MIXED_DDOF_REFUSED = ("Not applied: with this change the cell's variances and covariances use different `ddof` (for example "
                      "`np.var` with `ddof=1` and `np.cov` with `ddof=0`). Inside one ratio or decomposition every variance "
                      "and covariance must use the same `ddof`; change them together with `python`, or keep the line.")


def replace_line(src: str, old: str, new: str):
    lines = src.split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == old.strip()]
    if len(hits) != 1:
        return None, f"the flagged line occurs {len(hits)} times in the cell"
    i = hits[0]
    indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    body = new.strip()
    if old.rstrip().endswith(",") and not body.endswith(","):
        body += ","
    lines[i] = indent + body
    edited = "\n".join(lines)
    try:
        compile(edited, "<cell>", "exec")
    except SyntaxError as e:
        return None, f"the edited cell does not compile ({e.msg} at line {e.lineno})"
    if _va_doc().mixed_ddof(edited) and not _va_doc().mixed_ddof(src):
        return None, MIXED_DDOF_REFUSED
    return edited, None


def _names(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set(), set()
    stored = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    stored |= {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return stored, loaded


def downstream_cells(cells: dict, n: int) -> list:
    bound, out = _names(cells[n])[0], []
    for k in sorted(c for c in cells if c > n):
        stored, loaded = _names(cells[k])
        if loaded & bound:
            out.append(k)
            bound |= stored
    return out


