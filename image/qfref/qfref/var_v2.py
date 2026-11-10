import ast, math, re

V2_TEXT = ("Output check: {file}: `{field}` = {v:.6g} has the size of a variance (sqrt = {sq:.6g}); `{scale}` = {s:.6g} sits in the "
           "same outputs and `{limit}` = {L:.6g}, so `{field}` is read as value-at-risk and must equal {L:.6g} / {s:.6g} = {imp:.6g}. "
           "{held}Change the value; then add `assert abs({scale} * {field} - {limit}) <= 1e-9 * {limit}` to the cell that writes the file.")
V2_HELD = "Your session already holds `{name}` = {u:.6g}; write it to `{field}`. "


def v2_triples(VV, output_dir, statement, data_dirs):
    ins = VV["_read_inputs"](data_dirs)
    limits = [(k.split(".")[-1], v) for k, v in ins.items() if VV["_is_var_name"](k.split(".")[-1])
              and set(VV["_tokens"](k.split(".")[-1])) & VV["LIMIT_TOK"] and v > 0]
    outs = VV["_read_outputs"](output_dir)
    names = frozenset(o["name"] for o in outs)
    scales = [o for o in outs if VV["_is_var_name"](o["name"]) and {"scale", "factor"} & set(VV["_tokens"](o["name"])) and 0 < o["value"] < 1]
    fields = [o for o in outs if VV["_is_var_name"](o["name"]) and not set(VV["_tokens"](o["name"])) & VV["NON_LEVEL"]
              and o["value"] > 0 and VV["_meaning"](o["name"], statement, names)[0] == "VaR"]
    out = []
    for s in scales:
        for k, L in limits:
            for x in fields:
                imp = L / s["value"]
                if abs(x["value"] - imp) > 1e-3 * imp:
                    out.append((x["file"], x["name"], x["value"], s["name"], s["value"], k, L))
    return out


def v2_probe_code(target: float) -> str:
    return ("import numbers as _n\n"
            f"_t = {target!r}\n"
            "print('V2HELD', [k for k, v in list(globals().items()) if not k.startswith('_') and isinstance(v, _n.Real)"
            " and not isinstance(v, bool) and v and abs(float(v) - _t) <= 1e-6 * abs(_t)])")


def var_variance_notes_v2(VV, output_dir, statement, data_dirs, probe=None) -> list[str]:
    old = VV["var_variance_notes"](output_dir, statement, data_dirs)
    triples = v2_triples(VV, output_dir, statement, data_dirs)
    if not triples:
        return old
    notes, done = [], set()
    for f, n, v, sn, s, k, L in triples:
        if n in done:
            continue
        done.add(n)
        imp = L / s
        held = ""
        if probe:
            m = re.search(r"V2HELD (\[.*\])", probe(v2_probe_code(imp)) or "")
            cands = [x for x in (ast.literal_eval(m.group(1)) if m else []) if x != n]
            if cands:
                held = V2_HELD.format(name=cands[0], u=imp, field=n)
        notes.append(V2_TEXT.format(file=f, field=n, v=v, sq=math.sqrt(v), scale=sn, s=s, limit=k, L=L, imp=imp, held=held))
    notes += [o for o in old if not any(f"`{n}`" in o for n in done)]
    return notes
