import collections, json, re
from common import UNITS, OUT, instruction, input_names

STOP = {"of", "and", "the", "to", "in", "for", "on", "at", "by", "a", "an", "per", "vs", "with", "or"}
FUNC = {"then", "must", "only", "see", "from", "task", "slug", "debug", "combine", "should", "each", "use", "this",
        "that", "these", "also", "into", "will", "are", "be", "not", "pairs", "net", "locked", "estimates"}
COMMON = {"price", "prices", "return", "returns", "date", "dates", "weight", "weights", "value", "values", "volume",
          "number", "count", "time", "rate", "rates", "total", "mean", "average", "maximum", "minimum", "percent",
          "percentage", "difference", "position", "quantity", "frequency", "parameter", "parameters", "period",
          "cumulative", "annualized", "daily", "monthly", "error", "errors", "estimate", "reference", "threshold",
          "number", "observation", "observations", "index", "column", "name", "level", "change", "ratio", "spread", "volumes",
          "market", "markets", "ticker", "method", "methods", "type", "side", "size"}
GENERIC = {"python", "python3", "directory", "deliverables", "snapshot", "timestamp", "timestamps", "month", "seconds",
           "millisecond", "check", "default", "temperature", "perspective", "depend", "dropped", "dedup", "recompute",
           "vocabulary", "vocabularies", "violation", "assignment", "iterations", "frequencies", "datetime", "market",
           "stressed", "lagger", "simulations", "nameofissuer", "otherincludedmanagerscount", "charactersitics"}
ENGLISH = {"name", "order", "seed", "asset", "time", "date", "spot", "beta", "lag", "run", "per", "star", "cost",
           "clean", "high", "win", "pay", "par", "alpha", "stats", "stat", "dir", "exec", "sim", "temp", "rich"}
NOT_ABBR = {"is", "as", "at", "be", "by", "do", "go", "if", "in", "it", "me", "my", "no", "of", "on", "or", "so", "to",
            "up", "us", "we", "id", "ok", "all", "and", "any", "are", "can", "day", "end", "for", "get", "has", "key",
            "low", "new", "not", "one", "out", "set", "the", "two", "use", "via", "was", "yes", "csv", "json", "png",
            "app", "data", "file", "path", "true", "false", "none", "nan", "row", "rows", "col", "max", "min", "sum",
            "avg", "std", "abs", "log", "exp", "num", "pct", "est", "ref"}
PUBLIC = [
    ("nobs", "number_of_observations", "statsmodels RegressionResults.nobs ('Number of observations')"),
    ("resid", "residual", "statsmodels RegressionResults.resid ('The residuals of the model')"),
    ("ssr", "sum_of_squared_residuals", "statsmodels RegressionResults.ssr ('Sum of squared (whitened) residuals')"),
    ("mse", "mean_squared_error", "statsmodels RegressionResults.mse_resid ('Mean squared error of the residuals')"),
    ("var", "value_at_risk", "BCBS d457 Minimum capital requirements for market risk (2019), VaR"),
    ("es", "expected_shortfall", "BCBS d457 Minimum capital requirements for market risk (2019), ES"),
    ("bps", "basis_points", "general market convention (1 bp = 0.01%)"),
]


def toks(name):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name))
    return [t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t]


def initials(words):
    return "".join(w[0] for w in words)


def line_units(text):
    out = []
    for line in text.splitlines():
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]*", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", line))]
        ids = set()
        for sp in re.findall(r"`([^`\n]+)`", line) + re.findall(r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+", line):
            ids.update(toks(sp))
        out.append((words, ids))
    return out


def materials(task):
    out = []
    text = instruction(task)
    out.append(("instruction", line_units(text), text))
    names, _, template = input_names(task)
    if names:
        units = [(toks(n), set(toks(n))) for n in names]
        out.append(("input_data", units, ""))
    if template:
        src = "".join(f.read_text(errors="ignore") for f in (UNITS / task / "environment" / "data").glob("*template*.py"))
        out.append(("template", line_units(src), src))
    return out


def subseq(a, w):
    it = iter(w)
    return all(c in it for c in a)


def collect(task):
    found = set()
    for label, units, raw in materials(task):
        for m in re.finditer(r"((?:[A-Za-z][A-Za-z\-]+\s+){1,5}[A-Za-z][A-Za-z\-]+)\s*\(\s*([A-Za-z][A-Za-z0-9]{1,6})\s*\)", raw):
            ab = m.group(2).lower()
            ws = [w.lower() for w in re.split(r"[\s\-]+", m.group(1)) if w]
            for L in range(len(ws), 1, -1):
                ph = ws[-L:]
                while ph and ph[0] in STOP:
                    ph = ph[1:]
                core = [w for w in ph if w not in STOP]
                if len(core) >= 2 and initials(core) == re.sub(r"\d", "", ab) and len(core) == len(re.sub(r"\d", "", ab)):
                    found.add((ab, "_".join(ph), "parenthetical", label))
                    break
        for m in re.finditer(r"[`\"']([A-Za-z][A-Za-z0-9]{1,6})[`\"']+\s*\(\s*((?:[A-Za-z][A-Za-z\-]+\s+){0,4}[A-Za-z][A-Za-z\-]+)\s*[/)]", raw):
            ab = m.group(1).lower()
            ws = [w.lower() for w in re.split(r"[\s\-]+", m.group(2)) if w and w.lower() not in STOP]
            if len(ws) >= 2 and initials(ws) == ab:
                found.add((ab, "_".join(ws), "parenthetical", label))
            elif len(ws) == 1 and ws[0] != ab and ws[0][0] == ab[0] and subseq(ab, ws[0]):
                found.add((ab, ws[0], "parenthetical", label))
        for i, (_, ids) in enumerate(units):
            words = [w for u in units[max(0, i - 2):i + 3] for w in u[0]]
            cand = {t for t in ids if 2 <= len(t) <= 5 and t.isalpha() and t not in NOT_ABBR}
            for ab in cand:
                for j in range(len(words) - len(ab) + 1):
                    run = words[j:j + len(ab)]
                    if initials(run) == ab and all(w not in STOP and w not in NOT_ABBR and w not in FUNC and len(w) >= 3 for w in run) and len(set(run)) == len(run):
                        found.add((ab, "_".join(run), "initials", label))
                for w in set(words):
                    if w != ab and w[0] == ab[0] and len(w) >= len(ab) + 3 and subseq(ab, w) and w not in NOT_ABBR:
                        if w.startswith(ab) or ab[-1] not in "aeiou":
                            found.add((ab, w, "single_word", label))
    return found


def build():
    votes = collections.defaultdict(lambda: collections.defaultdict(set))
    kinds = {}
    tasks = sorted(p.name for p in UNITS.glob("t1-*"))
    for t in tasks:
        for ab, full, kind, label in collect(t):
            votes[ab][full].add(f"{t}:{label}")
            rank = {"parenthetical": 0, "initials": 1, "single_word": 2}
            if rank[kind] < rank.get(kinds.get((ab, full)), 9):
                kinds[(ab, full)] = kind
    pairs = []
    for ab, fulls in votes.items():
        for full, srcs in fulls.items():
            kind = kinds[(ab, full)]
            words = full.split("_")
            if kind == "parenthetical":
                is_term = True
            elif kind == "initials":
                is_term = not all(w in COMMON for w in words) and not any(w in GENERIC or w in FUNC for w in words)
            else:
                is_term = (full not in COMMON and full not in GENERIC and ab not in ENGLISH and ab not in COMMON
                           and len(ab) >= 3 and full.startswith(ab))
            pairs.append({"abbr": ab, "full": full, "kind": kinds[(ab, full)], "n_sources": len(srcs),
                          "sources": sorted(srcs), "term": is_term, "origin": "materials"})
    for ab, full, src in PUBLIC:
        pairs.append({"abbr": ab, "full": full, "kind": "public", "n_sources": 1, "sources": [src], "term": True, "origin": "public"})
    return pairs


if __name__ == "__main__":
    pairs = build()
    json.dump(pairs, open(OUT / "abbrev_pairs.json", "w"), indent=1)
    c = collections.Counter((p["kind"], p["term"]) for p in pairs)
    print(len(pairs), c)
