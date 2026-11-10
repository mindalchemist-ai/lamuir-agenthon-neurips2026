import csv, io, json, os, re

PROSE_LIST = re.compile(r":\s*((?:`[A-Za-z_][A-Za-z0-9_]*`\s*,\s*(?:and\s+)?){2,}`[A-Za-z_][A-Za-z0-9_]*`)")


def colon_list_names(entry: str, files: list[str], named: list[str]) -> list[str]:
    out = []
    for m in PROSE_LIST.finditer(entry):
        for n in re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", m.group(1)):
            if n in named and n not in files and n not in out:
                out.append(n)
    return out


def written_tokens(path: str):
    suffix = os.path.splitext(path)[1].lower()
    seen = set()
    try:
        if suffix == ".json":
            stack = [json.loads(open(path).read())]
            while stack:
                v = stack.pop()
                if isinstance(v, dict):
                    seen.update(str(k).strip() for k in v)
                    stack += list(v.values())
                elif isinstance(v, list):
                    stack += v
                elif isinstance(v, str):
                    seen.add(v.strip())
        elif suffix in (".csv", ".tsv"):
            for row in csv.reader(io.StringIO(open(path, errors="replace").read()), delimiter="\t" if suffix == ".tsv" else ","):
                seen.update(c.strip() for c in row)
        else:
            return None
    except Exception:
        return None
    return seen


def colon_list_missing(path: str, entry: str, files: list[str], expected: list[str], named: list[str]) -> list[str]:
    extra = [n for n in colon_list_names(entry, files, named) if n not in expected]
    if not extra:
        return []
    seen = written_tokens(path)
    return [] if seen is None else [n for n in extra if n not in seen]
