import glob, json, os, re, sys

MIN_LEAVES = 4
WRITE = re.compile(r"(save_json|json\.dump\(|to_csv|write_text|open\([^)]*['\"]w['\"])")
MARK = re.compile(r"#[^\n]*\b(placeholder|fill (it |them )?(in )?later|to be (filled|updated)|update later|will (fill|update))", re.I)


def leaves(v):
    if isinstance(v, dict):
        for x in v.values():
            yield from leaves(x)
    elif isinstance(v, list):
        for x in v:
            yield from leaves(x)
    elif isinstance(v, float):
        yield v


def zero_blocks(v, path=""):
    if isinstance(v, dict):
        nums = list(leaves(v))
        if len(nums) >= MIN_LEAVES and all(x == 0.0 for x in nums):
            return [path or "<root>"]
        return [p for k, x in v.items() for p in zero_blocks(x, f"{path}.{k}")]
    if isinstance(v, list):
        return [p for i, x in enumerate(v) for p in zero_blocks(x, f"{path}[{i}]")]
    return []


def cells(traj):
    for m in traj.get("messages", []):
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            a = tc["function"]["arguments"]
            try:
                a = json.loads(a)
            except Exception:
                pass
            c = a.get("code") if isinstance(a, dict) else a
            if isinstance(c, str):
                yield c


def issues(out_dir, code_cells):
    found = []
    for f in sorted(glob.glob(f"{out_dir}/**/*.json", recursive=True)):
        name = os.path.basename(f)
        try:
            blocks = zero_blocks(json.load(open(f)))
        except Exception:
            continue
        if not blocks:
            continue
        stem = re.escape(name)
        last = [c for c in code_cells if re.search(stem, c) and WRITE.search(c)]
        if last and MARK.search(last[-1]):
            found.append(f"{name}: {', '.join(blocks)} still all zeros; the cell that last wrote it marked values as placeholders")
    return found


if __name__ == "__main__":
    run = sys.argv[1]
    traj = json.load(open(f"{run}/trace/mini.traj.json"))
    print("\n".join(issues(f"{run}/output", list(cells(traj)))) or "no issue")
