import json, os, csv, math

SE_KEYS = {'se', 'std_error', 'stderr', 'standard_error'}
FACTORS = {100.0: 'x100', 0.01: 'x0.01', 252.0: 'x252', 1 / 252.0: 'x1/252', 365.0: 'x365', 1 / 365.0: 'x1/365'}


def _num(v):
    if isinstance(v, dict):
        v = v.get('value')
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def walk_sibling_groups(obj, path=()):
    if isinstance(obj, dict):
        nums = {k: v['value'] for k, v in obj.items()
                if isinstance(v, dict) and _num(v) is not None and any(s in v for s in SE_KEYS) and set(v) <= {'value'} | SE_KEYS}
        if len(nums) >= 2:
            yield path, nums
        for k, v in obj.items():
            yield from walk_sibling_groups(v, path + (k,))


def c1_unit_factor(obj, check_sign=False, tol=0.03):
    hits = []
    for path, nums in walk_sibling_groups(obj):
        ks = sorted(nums)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, b = nums[ks[i]], nums[ks[j]]
                if a == 0 or b == 0:
                    continue
                q = a / b
                for f, name in FACTORS.items():
                    if abs(abs(q) / f - 1) < tol:
                        hits.append(('/'.join(path), ks[i], ks[j], a, b, name + ('' if q > 0 else ',sign')))
                if check_sign and abs(q + 1) < 0.05:
                    hits.append(('/'.join(path), ks[i], ks[j], a, b, 'sign'))
    return hits


def leaf_paths(obj, path=()):
    if isinstance(obj, dict):
        if 'value' in obj and _num(obj) is not None:
            yield path, obj['value']
        for k, v in obj.items():
            if k != 'value':
                yield from leaf_paths(v, path + (k,))


def c2_cross_file(csv_path, json_obj, rel_tol=0.02):
    try:
        rows = list(csv.DictReader(open(csv_path)))
    except Exception:
        return []
    if not rows or 'value' not in rows[0]:
        return []
    size_cols = [c for c in rows[0] if c.lower() in ('n', 'n_paths', 'paths', 'num_paths')]
    if not size_cols:
        return []
    sc = size_cols[0]
    try:
        nmax = max(float(r[sc]) for r in rows)
    except Exception:
        return []
    leaves = list(leaf_paths(json_obj))
    hits = []
    for r in rows:
        try:
            if float(r[sc]) != nmax:
                continue
            v = float(r['value'])
        except Exception:
            continue
        labels = {str(x) for k, x in r.items() if k not in (sc, 'value', 'se') and x not in (None, '')}
        labels = {l for l in labels if not _isnum(l)}
        cands = [(p, lv) for p, lv in leaves if labels and labels <= set(p)]
        if not cands:
            continue
        if all(abs(v - lv) > rel_tol * max(abs(lv), 1e-9) for _, lv in cands):
            hits.append((sorted(labels), v, [('/'.join(p), lv) for p, lv in cands]))
    return hits


def _isnum(s):
    try:
        float(s); return True
    except Exception:
        return False


def _tokens(s):
    import re
    return {t for t in re.split(r'[^a-z0-9]+', str(s).lower()) if t}


def c3_error_sign(errors_obj, json_obj, tol=0.05):
    hits = []
    leaves = list(leaf_paths(json_obj))
    def err_leaves(o, path=()):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from err_leaves(v, path + (k,))
        elif isinstance(o, (int, float)) and not isinstance(o, bool) and math.isfinite(o):
            yield path, o
    for path, e in err_leaves(errors_obj):
        if not any(('error' in p.lower() or 'diff' in p.lower()) for p in path[:-1]):
            continue
        toks = _tokens(path[-1])
        for lp, v in leaves:
            if v == 0 or not toks:
                continue
            ptoks = set().union(*(_tokens(x) for x in lp))
            if toks <= ptoks and abs(e - 2 * v) < tol * abs(v) and abs(v) > 1e-9:
                hits.append(('/'.join(path), e, '/'.join(lp), v))
    return hits


def summary_false(summary_obj):
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if 'all' in k.lower() and isinstance(v, bool):
                    yield v
                yield from walk(v)
    vals = list(walk(summary_obj))
    return bool(vals) and not all(vals)


def c2b_same_size_methods(csv_path, k_se=6.0, rel_floor=0.01):
    try:
        rows = list(csv.DictReader(open(csv_path)))
    except Exception:
        return []
    if not rows or 'value' not in rows[0]:
        return []
    size_cols = [c for c in rows[0] if c.lower() in ('n', 'n_paths', 'paths', 'num_paths')]
    if not size_cols:
        return []
    sc = size_cols[0]
    try:
        nmax = max(float(r[sc]) for r in rows)
    except Exception:
        return []
    top = [r for r in rows if _isnum(r.get(sc, '')) and float(r[sc]) == nmax and _isnum(r.get('value', ''))]
    text_cols = [c for c in rows[0] if c not in (sc, 'value', 'se') and not all(_isnum(r.get(c, '')) for r in top)]
    hits = []
    for vary in text_cols:
        groups = {}
        for r in top:
            key = tuple(r[c] for c in text_cols if c != vary)
            groups.setdefault(key, []).append(r)
        for key, grp in groups.items():
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    a, b = float(grp[i]['value']), float(grp[j]['value'])
                    sa = float(grp[i]['se']) if _isnum(grp[i].get('se', '')) else 0.0
                    sb = float(grp[j]['se']) if _isnum(grp[j].get('se', '')) else 0.0
                    band = max(k_se * math.hypot(sa, sb), rel_floor * max(abs(a), abs(b)))
                    if abs(a - b) > band:
                        hits.append((vary, grp[i][vary], a, grp[j][vary], b, band))
    return hits
