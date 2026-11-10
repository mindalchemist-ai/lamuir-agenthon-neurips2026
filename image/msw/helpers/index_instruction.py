from __future__ import annotations

import hashlib
import pathlib
import re

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
MARKER = re.compile(r"^(S\d{2,3})(?::(\d+)(?:-(\d+))?)?$")
LINES_ONLY = re.compile(r"^(?:S|L|lines?\s*)?(\d+)\s*-\s*(\d+)$", re.I)


def fenced_out(lines: list[str]) -> list:
    out, open_fence = [], None
    for line in lines:
        m = FENCE.match(line)
        if open_fence is None and m:
            open_fence = m.group(1)
            out.append(None)
        elif open_fence is not None:
            closing = m and m.group(1)[0] == open_fence[0] and len(m.group(1)) >= len(open_fence)
            out.append(None)
            open_fence = None if closing else open_fence
        else:
            out.append(line)
    return out


def sections(statement: str) -> list[dict]:
    lines = statement.splitlines()
    heads = [(i, len(m.group(1)), m.group(2).strip())
             for i, line in enumerate(fenced_out(lines))
             if line is not None and (m := HEADING.match(line))]
    spans = [(0, heads[0][0] if heads else len(lines), 0, "")] if not heads or heads[0][0] else []
    for n, (i, level, heading) in enumerate(heads):
        spans.append((i, heads[n + 1][0] if n + 1 < len(heads) else len(lines), level, heading))
    sections, stack = [], []
    for n, (start, end, level, heading) in enumerate(spans):
        while stack and stack[-1][1] >= level:
            stack.pop()
        marker = f"S{n:02d}"
        path = " > ".join([h for _, _, h in stack] + [heading]) if heading else "(before the first heading)"
        sections.append({"id": marker, "heading": heading, "level": level,
                         "parent": stack[-1][0] if stack else None, "path": path,
                         "line_start": start + 1, "line_end": end})
        stack.append((marker, level, heading))
    return sections


def render(sections: list[dict], statement: str) -> str:
    lines = statement.splitlines()
    out = []
    for s in sections:
        out.append(f"[{s['id']} | lines {s['line_start']}-{s['line_end']}] {s['path']}")
        out += [f"{n:>5} | {lines[n - 1]}" for n in range(s["line_start"], s["line_end"] + 1)]
    return "\n".join(out)


def resolve(marker, sections: list[dict], statement: str) -> tuple[dict | None, str | None]:
    text = marker.strip() if isinstance(marker, str) else ""
    ids = {s["id"]: s for s in sections}
    m = MARKER.match(text)
    lines = LINES_ONLY.match(text)
    named = None
    if m and m.group(1) in ids:
        sid = m.group(1)
        span = [int(m.group(2)), int(m.group(3) or m.group(2))] if m.group(2) else None
    elif lines:
        span = [int(lines.group(1)), int(lines.group(2))]
        holds = [x for x in sections if x["line_start"] <= span[0] <= span[1] <= x["line_end"]]
        if len(holds) != 1:
            return None, f"lines {span} are not inside one section"
        sid = holds[0]["id"]
    elif m and m.group(2):
        span = [int(m.group(2)), int(m.group(3) or m.group(2))]
        holds = [x for x in sections if x["line_start"] <= span[0] <= span[1] <= x["line_end"]]
        if len(holds) != 1:
            return None, (f"section {m.group(1)} does not exist, and lines {span} are not "
                          f"inside one section")
        sid, named = holds[0]["id"], m.group(1)
    elif m:
        return None, f"section {m.group(1)} does not exist"
    else:
        return None, f'{marker!r} is not a marker; write "S07" or "S07:120-126"'
    section = ids[sid]
    corrected = named
    if span:
        if span[0] > span[1]:
            return None, f"lines {span} are the wrong way round"
        if not (section["line_start"] <= span[0] <= span[1] <= section["line_end"]):
            holds = [x for x in sections if x["line_start"] <= span[0] <= span[1] <= x["line_end"]]
            if len(holds) != 1:
                return None, (f"lines {span} are not inside {sid} "
                              f"(lines {section['line_start']}-{section['line_end']})")
            corrected, section, sid = sid, holds[0], holds[0]["id"]
    first, last = span or (section["line_start"], section["line_end"])
    where = {"section": sid, "path": section["path"], "line_start": first, "line_end": last,
             "level": "lines" if span else "section",
             "text": "\n".join(statement.splitlines()[first - 1:last])}
    if corrected:
        where["corrected_from"] = corrected
    return where, None


def index(statement: str) -> dict:
    secs = sections(statement)
    return {"statement": statement, "sha256": hashlib.sha256(statement.encode()).hexdigest(),
            "sections": secs, "numbered": render(secs, statement)}


def read(unit_dir) -> dict:
    unit_dir = pathlib.Path(unit_dir)
    return {**index((unit_dir / "instruction.md").read_text()), "unit": unit_dir.name}
