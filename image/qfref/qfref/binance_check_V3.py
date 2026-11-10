import csv, json, os, sys

BAL_KEYS = ("remaining", "leaves", "open_qty", "outstanding")
FILL_KEYS = ("fill_qty", "filled_qty", "exec_qty", "executed_qty", "child_order_qty")


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def balance_lag_problems(path):
    out = []
    try:
        rows = list(csv.DictReader(open(path, newline="")))
    except Exception:
        return out
    if len(rows) < 3:
        return out
    cols = list(rows[0].keys())
    bal = [c for c in cols if any(k in c.lower() for k in BAL_KEYS)]
    fil = sorted((c for c in cols if c.lower() in FILL_KEYS), key=lambda c: FILL_KEYS.index(c.lower()))
    for b in bal:
        for f in fil:
            B = [_num(r[b]) for r in rows]
            F = [_num(r[f]) or 0.0 for r in rows]
            if any(v is None for v in B):
                continue
            moves = [i for i in range(1, len(rows)) if abs(F[i]) > 1e-12]
            if not moves:
                continue
            post = all(abs(B[i - 1] - F[i] - B[i]) <= 1e-6 for i in range(1, len(rows)))
            pre = all(abs(B[i - 1] - F[i - 1] - B[i]) <= 1e-6 for i in range(1, len(rows)))
            if pre and not post:
                i = moves[0]
                out.append(f"{os.path.basename(path)}: `{b}` on each row equals the balance before that row's `{f}` "
                           f"(row {i + 1}: {rows[i][b]} with {f}={rows[i][f]}), so the last row ({rows[-1][b]}) is not the amount left "
                           f"after the final fill. A ledger balance column usually reports the state after the row's own fill; "
                           f"keep the opening balance only if the task defines the column that way.")
                return out
    return out


def reference_time_problems(path):
    out = []
    try:
        d = json.load(open(path))
    except Exception:
        return out

    def walk(o, where):
        if not isinstance(o, dict):
            return
        for k, v in o.items():
            if isinstance(v, dict):
                walk(v, where + k + ".")
            if "reference_time" in k.lower() and isinstance(v, (int, float)) and not isinstance(v, bool):
                stem = k.lower().split("reference_time")[0]
                twins = [k2 for k2, v2 in o.items() if k2 != k and k2.lower().startswith(stem) and
                         ("transaction_time" in k2.lower() or "event_time" in k2.lower()) and v2 == v]
                if twins:
                    out.append(f"{os.path.basename(path)}: `{where}{k}` holds the same value as `{twins[0]}`. If the reference time "
                               f"is defined by a rule (a window end plus a horizon, say), write that computed time; the matched "
                               f"record's own timestamps already have their own fields.")

    walk(d, "")
    return out


def problems(out_dir):
    p = []
    for name in sorted(os.listdir(out_dir)):
        path = os.path.join(out_dir, name)
        if name.endswith(".csv"):
            p += balance_lag_problems(path)
        elif name.endswith(".json"):
            p += reference_time_problems(path)
    return p


if __name__ == "__main__":
    for d in sys.argv[1:]:
        for m in problems(d):
            print(d, "|", m)
