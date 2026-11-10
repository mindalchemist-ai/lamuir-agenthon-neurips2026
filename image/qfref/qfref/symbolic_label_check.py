import csv, glob, os, re

SYMBOLIC_SETS = ({"A", "B"}, {"X", "Y"}, {"A", "B", "C"}, {"X", "Y", "Z"})
MIN_ROWS = 2


def _column_values(path):
    try:
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        return {}
    if not rows:
        return {}
    cols = {}
    for field in rows[0]:
        vals = [(r.get(field) or "").strip() for r in rows]
        cols[field] = [v for v in vals if v != "" and v.lower() not in ("nan", "none", "null")]
    return cols


def issues(out_dir, statement=""):
    found = []
    letters_in_text = set(re.findall(r"\b([A-Z])\b", statement or ""))
    for path in sorted(glob.glob(f"{out_dir}/**/*.csv", recursive=True)):
        for field, vals in _column_values(path).items():
            if len(vals) < MIN_ROWS:
                continue
            uniq = set(vals)
            if any(uniq and uniq <= s for s in SYMBOLIC_SETS):
                if uniq & letters_in_text or not letters_in_text:
                    found.append((os.path.basename(path), field, sorted(uniq)))
    return found


def symbolic_label_notes(out_dir, statement=""):
    notes = []
    for fname, field, labels in issues(out_dir, statement):
        notes.append(
            f"Output note: in {fname}, column '{field}' contains only the symbolic labels {labels}. "
            f"A task that writes a rule such as 'if ... {labels[0]} leads {labels[-1]}' uses those letters to "
            f"name entities, not as the literal cell value. Replace each label with the concrete data value it "
            f"stands for (the ticker, name or id of that entity) in every output file and in any JSON that ranks or lists them."
        )
    return notes
