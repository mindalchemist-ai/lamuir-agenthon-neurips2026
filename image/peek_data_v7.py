'Preview every data file of one unit: first 3 lines of text tables, header + 2 rows of parquet and\nExcel sheets, whole content of small JSON files in compact form.\n\n    python peek_data.py <unit_dir> [--all | --data-dir REL] [--max-line-chars N]\n\nScans `<unit_dir>/environment/data/` by default (what the agent sees); `--data-dir` names another\ndirectory relative to the unit, `--all` scans the whole unit. Nothing is truncated unless\n`--max-line-chars` is given. Rows are numbered from 0.\n\nText files: first 3 physical lines, the number of physical lines (newlines, plus one when the file does\nnot end with a newline) and the last non-empty physical line with its line number. A quoted CSV field\nspanning lines makes physical lines differ from records.\n\nParquet: a table when it has at least one column; column types from the schema, the first 2 rows and\nthe last row, written as CSV with proper quoting, nested values as JSON, nulls as empty fields. The\nlast row is not read when the last row group is over 256 MB uncompressed (a read-cost guard, not a\nmemory limit).\n\nJSON: up to 50 KB (by file size) printed whole in compact form; larger files get their size and a\nstructure outline (keys, value types, counts, 2 samples per list).\n\nExcel: every sheet; the rows above the header, the header (rule-detected; when not certain, the\nreasons and the candidate rows), rows between header and data classified as header-continuation\ncandidates or notes, combined column names inferred from continuation candidates, the cell types of\nthe first data row, 2 data rows, the last data row, row counts with their source, and conditional\npandas calls; columns whose sample text cells look like numbers are read with converters=str so text\nsuch as IDs with leading zeros stays text. A .xls file needs xlrd; without it the file is marked as such.\n\nExit status: 0 all previewed or skipped, 1 no data, 2 no unit directory, 3 some file could not be\nread.\n'
from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import sys

TEXT_EXT = {".csv", ".tsv", ".psv", ".txt", ".dat", ".jsonl", ".ndjson"}
PARQUET_EXT = {".parquet", ".pqt", ".pq"}
JSON_EXT = {".json"}
EXCEL_EXT = {".xlsx", ".xlsm", ".xls"}
TEXT_LINES = 3
SMALL_TEXT_LINES = 20
PARQUET_ROWS = 2
JSON_FULL_BYTES = 50 * 1024
JSON_PARSE_BYTES = 50 * 1024 * 1024
OUTLINE_KEYS = 40
OUTLINE_DEPTH = 4
OUTLINE_SAMPLE_CHARS = 300
OUTLINE_SCALAR_CHARS = 200
JSON_TYPES = {"dict": "object", "list": "array", "str": "string", "int": "number", "float": "number",
              "bool": "boolean", "NoneType": "null"}
DEFAULT_DATA_DIR = "environment/data"
EXCEL_HEADER_SCAN = 30
EXCEL_MAX_ROWS = 200_000
HEADER_FILL = 0.8
TAIL_BLOCK = 64 * 1024
COUNT_BLOCK = 1024 * 1024
LAST_ROW_GROUP_BYTES = 256 * 1024 * 1024


def data_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def clip(line: str, limit: int) -> str:
    return line if not limit or len(line) <= limit else line[:limit] + f" ...(+{len(line) - limit} chars not shown)"


def physical_lines(path: pathlib.Path) -> int:
    size = path.stat().st_size
    if not size:
        return 0
    count = 0
    with path.open("rb") as f:
        for block in iter(lambda: f.read(COUNT_BLOCK), b""):
            count += block.count(b"\n")
        f.seek(size - 1)
        return count + (f.read(1) != b"\n")


def last_non_empty_line(path: pathlib.Path, total: int) -> tuple[int, str] | None:
    size = path.stat().st_size
    buf, pos = b"", size
    with path.open("rb") as f:
        while pos > 0:
            step = min(TAIL_BLOCK, pos)
            pos -= step
            f.seek(pos)
            buf = f.read(step) + buf
            parts = buf.split(b"\n")
            if parts and parts[-1] == b"":
                parts.pop()
            complete = parts if pos == 0 else parts[1:]
            for j in range(len(complete) - 1, -1, -1):
                if complete[j].strip():
                    index = total - (len(complete) - j)
                    return index, complete[j].decode("utf-8", errors="replace").rstrip("\r")
    return None


def peek_text(path: pathlib.Path) -> list[str]:
    total = physical_lines(path)
    if total <= SMALL_TEXT_LINES:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = [line.rstrip("\r\n") for line in f]
        return lines + [f"lines: {total} physical lines (header included; shown whole)"]
    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines = [line.rstrip("\r\n") for _, line in zip(range(TEXT_LINES), f)]
    lines.append(f"lines: {total} physical lines (header included)")
    last = last_non_empty_line(path, total) if total > TEXT_LINES else None
    if last and last[0] >= TEXT_LINES:
        lines.append(f"last non-empty line r{last[0]}: {last[1]}")
    return lines


def compact(value) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def outline(value, indent: str = "", depth: int = 0) -> list[str]:
    if isinstance(value, dict):
        lines = []
        for key in list(value)[:OUTLINE_KEYS]:
            v = value[key]
            lines.append(f"{indent}{compact(key)}: {kind(v)}")
            if isinstance(v, (dict, list)) and v and depth + 1 < OUTLINE_DEPTH:
                lines += outline(v, indent + "  ", depth + 1)
        if len(value) > OUTLINE_KEYS:
            lines.append(f"{indent}... {len(value) - OUTLINE_KEYS} more keys")
        return lines
    if isinstance(value, list):
        return [f"{indent}[{i}]: {clip(compact(v), OUTLINE_SAMPLE_CHARS)}" for i, v in enumerate(value[:2])]
    return []


def kind(value) -> str:
    if isinstance(value, dict):
        return f"object, {len(value)} keys"
    if isinstance(value, list):
        types = sorted({JSON_TYPES[type(v).__name__] for v in value})
        return f"array, {len(value)} items" + (f" of {'/'.join(types)}" if types else "")
    return f"{JSON_TYPES[type(value).__name__]} {clip(compact(value), OUTLINE_SCALAR_CHARS)}"


def peek_json(path: pathlib.Path) -> list[str]:
    size = path.stat().st_size
    if size <= JSON_FULL_BYTES:
        return [compact(json.loads(path.read_text(encoding="utf-8", errors="replace")))]
    head = f"<json not shown in full: {size} bytes, over {JSON_FULL_BYTES}; read the file yourself when you need more>"
    if size > JSON_PARSE_BYTES:
        return [head, f"<structure not computed: file over {JSON_PARSE_BYTES} bytes>"]
    value = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    return [head, f"top level: {kind(value)}", *outline(value, "  ")]


def cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def csv_line(values: list[str]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow(values)
    return buf.getvalue()


def columns_to_rows(table, start: int, stop: int) -> list[list]:
    part = table.slice(start, stop - start)
    cols = [part.column(i).to_pylist() for i in range(part.num_columns)]
    return [list(r) for r in zip(*cols)]


def parquet_last_row(pf) -> tuple[list | None, str | None]:
    meta = pf.metadata
    groups = [g for g in range(meta.num_row_groups) if meta.row_group(g).num_rows]
    if not groups:
        return None, None
    size = meta.row_group(groups[-1]).total_byte_size
    if size > LAST_ROW_GROUP_BYTES:
        return None, f"last row not read: last row group is {size / 2**20:.0f} MB uncompressed"
    table = pf.read_row_group(groups[-1])
    return columns_to_rows(table, table.num_rows - 1, table.num_rows)[0], None


def peek_parquet(path: pathlib.Path) -> list[str]:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return ["<error: pyarrow not installed, cannot read parquet>"]
    pf = pq.ParquetFile(path)
    schema = pf.schema_arrow
    names, rows_total = schema.names, pf.metadata.num_rows
    shape = f"rows={rows_total} cols={len(names)}"
    if not names:
        return [f"<not a table: no columns; {shape}>"]
    batch = next(pf.iter_batches(batch_size=PARQUET_ROWS), None)
    rows = columns_to_rows(batch, 0, PARQUET_ROWS) if batch is not None else []
    out = [f"<table; {shape}>", "types: " + ", ".join(f"{n}:{t}" for n, t in zip(names, schema.types)),
           csv_line(names), *(csv_line([cell(v) for v in r]) for r in rows)]
    if rows_total > PARQUET_ROWS:
        last, note = parquet_last_row(pf)
        out.append(note if note else f"last row r{rows_total - 1}: {csv_line([cell(v) for v in last])}")
    return out


def trimmed(row) -> list:
    row = list(row)
    while row and row[-1] in (None, ""):
        row.pop()
    return row


def filled(row) -> int:
    return sum(v not in (None, "") for v in row)


class MissingReader(Exception):
    pass


def excel_sheets(path: pathlib.Path):
    if path.suffix.lower() == ".xls":
        try:
            import xlrd
        except ImportError:
            raise MissingReader(".xls needs the xlrd package, which is not installed; file not previewed") from None
        import pandas as pd
        frames = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
        for name, df in frames.items():
            rows = (tuple(None if pd.isna(v) else v for v in r) for r in df.itertuples(index=False))
            yield name, rows, "no size metadata (.xls read whole through pandas)"
        return
    try:
        import openpyxl
    except ImportError:
        raise MissingReader(f"{path.suffix} needs the openpyxl package, which is not installed; file not previewed") from None
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            try:
                dim = ws.calculate_dimension()
            except Exception:
                dim = None
            note = (f"file metadata says {dim} ({ws.max_row} rows, counting every stored row: notes, header, blank rows, footer)"
                    if dim else "file metadata has no sheet size")
            yield ws.title, ws.iter_rows(values_only=True), note
    finally:
        wb.close()


def find_header(rows: dict) -> tuple[int | None, int]:
    common = [filled(r) for r in rows.values() if filled(r) >= 2]
    width = max(set(common), key=common.count) if common else 0
    for i, row in rows.items():
        cells = [v for v in row if v not in (None, "")]
        if width and len(cells) >= HEADER_FILL * width and all(isinstance(v, str) for v in cells):
            if any(filled(rows.get(j, [])) * 2 >= width for j in (i + 1, i + 2)):
                return i, width
    return None, width


def header_doubts(header: list, width: int, extra: list, samples: list) -> list[str]:
    doubts = []
    if filled(header) < width:
        doubts.append(f"it names {filled(header)} of the {width} columns the data rows fill")
    if extra:
        doubts.append(f"row(s) {', '.join(f'r{j}' for j, _ in extra)} between it and the data also hold text")
    if samples and all(isinstance(v, str) for _, r in samples for v in r if v not in (None, "")):
        doubts.append("the data rows are text only, so a header looks like data")
    return doubts


def padded(row: list, n: int) -> list:
    return list(row) + [None] * (n - len(row))


def classify_between(header: list, extra: list, ncols: int) -> dict:
    kinds, upper = {}, padded(header, ncols)
    for j, row in extra:
        cells = [(k, v) for k, v in enumerate(row) if v not in (None, "")]
        if len(cells) < 2 or any(not isinstance(v, str) for _, v in cells):
            kinds[j] = "note"
        elif all(k < ncols for k, _ in cells) and any(upper[k] in (None, "") for k, _ in cells):
            kinds[j] = "continuation"
            upper = [u if u not in (None, "") else (padded(row, ncols)[k]) for k, u in enumerate(upper)]
        else:
            kinds[j] = "other"
    return kinds


def combine_names(header: list, continuations: list, ncols: int) -> list[str]:
    upper = [str(v) if v not in (None, "") else "" for v in padded(header, ncols)]
    for row in continuations:
        low = [str(v) if v not in (None, "") else "" for v in padded(row, ncols)]
        base = list(upper)
        for k in range(ncols):
            if not upper[k] and low[k] and k > 0:
                j = k - 1
                while j >= 0 and not upper[j] and low[j]:
                    j -= 1
                if j >= 0 and upper[j]:
                    base[k] = upper[j]
        upper = [" | ".join(x for x in (b, l) if x) for b, l in zip(base, low)]
    return [u or f"Unnamed: {k}" for k, u in enumerate(upper)]


def dedupe(names: list[str]) -> tuple[list[str], list[str]]:
    used, seen, out, notes = set(names), set(), [], []
    for name in names:
        if name in seen:
            i = 1
            while f"{name}.{i}" in used:
                i += 1
            new = f"{name}.{i}"
            used.add(new)
            notes.append(f"{name!r} -> {new!r}")
            name = new
        seen.add(name)
        out.append(name)
    return out, notes


def cell_type(value) -> str:
    import datetime
    if value in (None, ""):
        return "empty"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, (datetime.datetime, datetime.date)):
        return "date"
    if isinstance(value, datetime.time):
        return "time"
    return "text"


def looks_numeric(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        float(value.strip())
    except ValueError:
        return False
    return True


def read_window(rows_iter) -> tuple[dict, int, bool, bool]:
    window, read, extra_after = {}, 0, None
    for i, row in enumerate(rows_iter):
        if i >= EXCEL_MAX_ROWS:
            return window, read, False, True
        read = i + 1
        row = trimmed(row)
        if filled(row):
            window[i] = row
        if extra_after is None and len(window) >= EXCEL_HEADER_SCAN:
            extra_after = i + 2
        if extra_after is not None and i >= extra_after:
            return window, read, False, False
    return window, read, True, False


def peek_sheet(path: pathlib.Path, name: str, rows_iter, meta: str) -> list[str]:
    row_line = lambda i, r: f"r{i}: {csv_line([cell(v) for v in r])}"
    out = [f"[sheet {name!r}]"]
    window, read, ended, limited = read_window(rows_iter)
    if not window:
        if limited:
            return out + [f"  <no non-empty row in the first {EXCEL_MAX_ROWS} rows; scan stopped, rest of the sheet not checked>"]
        return out + ["  <empty sheet>", f"  rows: {meta}"]
    h, width = find_header(window)
    if h is None:
        out.append(f"  <no header row found in the first {len(window)} non-empty rows; first non-empty rows as stored>")
        return out + [f"  {row_line(i, r)}" for i, r in list(window.items())[:5]] + [f"  rows: {meta}"]
    header = window[h]
    first = next((j for j, r in window.items() if j > h and filled(r) * 2 >= width), None)
    extra = [(j, r) for j, r in window.items() if h < j < (first if first is not None else read)]
    above = [(i, r) for i, r in window.items() if i < h]
    if above:
        out.append("  above the header:")
        out += [f"    {row_line(i, r)}" for i, r in above]
    if first is None:
        out.append(f"  header {row_line(h, header)}")
        return out + ["  <no data row found below the header>", f"  rows: {meta}"]

    data = last = blank = 0
    samples, other, footer = [], [], []
    last_row = None
    def visit(i, row):
        nonlocal data, last, blank, footer, last_row
        if i < first:
            return
        if not filled(row):
            blank += 1
        elif filled(row) * 2 >= width:
            data, last, last_row = data + 1, i, row
            if len(samples) < PARQUET_ROWS:
                samples.append((i, row))
            other.extend(footer)
            footer = []
        else:
            footer.append((i, row))
    for i in range(first, read):
        visit(i, window.get(i, []))
    total, stopped = read, limited
    if not ended and not limited:
        for i, row in enumerate(rows_iter, start=read):
            if i >= EXCEL_MAX_ROWS:
                stopped = True
                break
            visit(i, trimmed(row))
            total = i + 1

    ncols = max([len(header), *(len(r) for _, r in extra), *(len(r) for _, r in samples)])
    data_cols = max(len(r) for _, r in samples)
    doubts = header_doubts(header, width, extra, samples)
    kinds = classify_between(header, extra, data_cols)
    if doubts:
        out.append(f"  header not certain ({'; '.join(doubts)}); candidate rows as stored:")
        out += [f"    {row_line(j, r)}" for j, r in [(h, header), *extra]]
    else:
        out.append(f"  header r{h} (rule-detected): {csv_line([cell(v) for v in header])}")
    labels = {"continuation": "header continuation candidate (may be units or notes instead; check the rows above)",
              "note": "note row (not used for column names)",
              "other": "row not used for column names (it does not fill any unnamed column)"}
    for j, _ in extra:
        out.append(f"  r{j}: {labels[kinds[j]]}")
    col_names = [str(v) if v not in (None, "") else f"c{k}" for k, v in enumerate(padded(header, ncols))] \
        if not doubts else [f"c{k}" for k in range(ncols)]
    first_row = padded(samples[0][1], ncols)
    out.append("  types (cells of the first data row): " + ", ".join(f"{n}:{cell_type(v)}" for n, v in zip(col_names, first_row)))
    out.append("  first data rows:")
    out += [f"    {row_line(j, r)}" for j, r in samples]
    out.append(f"  last data row (by the data-row rule: at least half the usual width filled) {row_line(last, last_row)}")
    out.append(f"  rows: {meta}")
    out.append(f"  rows streamed: {total}{' (stopped at the scan limit; counts below are partial)' if stopped else ''} = "
               f"{first} before the data (notes, header) + {data} data rows r{first}-r{last} + "
               f"{blank} blank + {len(other) + len(footer)} other non-empty rows")
    nrows = f", nrows={data}" if last - first + 1 == data and not stopped else ""
    keep_text = sorted({k for _, r in [*samples, (last, last_row)] for k, v in enumerate(r) if looks_numeric(v)})
    conv = f", converters={{{', '.join(f'{k}: str' for k in keep_text)}}}" if keep_text else ""
    conts = [r for j, r in extra if kinds[j] == "continuation"]
    if conts:
        names, renamed = dedupe(combine_names(header, conts, ncols))
        rows_used = ", ".join([f"r{h}"] + [f"r{j}" for j, _ in extra if kinds[j] == "continuation"])
        out.append(f"  combined names (inferred from {rows_used}; not guaranteed unique or correct):")
        out.append(f"  names = {json.dumps(names, ensure_ascii=False)}")
        if renamed:
            out.append(f"  repeated names were given suffixes: {', '.join(renamed)}")
        out.append(f"  if {rows_used} are the header rows, read with: pd.read_excel({str(path)!r}, sheet_name={name!r}, "
                   f"header=None, skiprows={first}{nrows}, names=names{conv})")
    skip = f", skiprows={[j for j, _ in extra]}" if extra else ""
    lead = f"  if r{h} alone is the header, read with: " if doubts else "  read with: "
    out.append(f"{lead}pd.read_excel({str(path)!r}, sheet_name={name!r}, header={h}{skip}{nrows}{conv})")
    if keep_text:
        out.append(f"  (converters keep columns {', '.join(map(str, keep_text))} (0-based) as text: their sample cells are "
                   "text that looks like numbers, which pandas may otherwise convert to numbers, dropping leading zeros for example)")
    if extra:
        out.append(f"  (with that call the names in {', '.join(f'r{j}' for j, _ in extra)} are not column names)")
    if other:
        out.append(f"  non-empty rows inside the data that are not data rows: {', '.join(f'r{i}' for i, _ in other[:10])}")
    if footer:
        out.append(f"  after the last data row ({len(footer)} non-empty rows; without nrows pandas reads them as data):")
        out += [f"    {clip(row_line(i, r), 200)}" for i, r in footer[:3]]
    return out


def peek_excel(path: pathlib.Path) -> list[str]:
    try:
        blocks = [peek_sheet(path, name, rows_iter, meta) for name, rows_iter, meta in excel_sheets(path)]
    except MissingReader as e:
        return [f"<error: missing reader: {e}>"]
    return [f"<excel; sheets: {', '.join(b[0][7:-1] for b in blocks)}>", *(x for b in blocks for x in b)]


def peek(path: pathlib.Path) -> tuple[str, list[str]]:
    ext = path.suffix.lower()
    readers = {**dict.fromkeys(PARQUET_EXT, peek_parquet), **dict.fromkeys(JSON_EXT, peek_json),
               **dict.fromkeys(TEXT_EXT, peek_text), **dict.fromkeys(EXCEL_EXT, peek_excel)}
    if ext not in readers:
        return "skipped", []
    try:
        lines = readers[ext](path)
    except Exception as e:
        return "error", [f"<error: {type(e).__name__}: {e}>"]
    return ("error" if lines and lines[0].startswith("<error") else "ok"), lines


def preview(root: pathlib.Path, max_line_chars: int = 0) -> list[dict]:
    out = []
    for path in data_files(root):
        status, lines = peek(path)
        out.append({"path": path, "status": status, "lines": [clip(x, max_line_chars) for x in lines]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("unit", type=pathlib.Path, help="unit/task directory")
    where = ap.add_mutually_exclusive_group()
    where.add_argument("--all", action="store_true", help="scan the whole unit")
    where.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help=f"directory to scan, relative to the unit (default {DEFAULT_DATA_DIR})")
    ap.add_argument("--max-line-chars", type=int, default=0, help="cut longer lines and say so (default 0 = never cut)")
    args = ap.parse_args()
    if not args.unit.is_dir():
        print(f"unit directory not found: {args.unit}", file=sys.stderr)
        return 2
    root = args.unit if args.all else args.unit / args.data_dir
    if not root.is_dir():
        print(f"no data directory: {root}", file=sys.stderr)
        return 1
    records = preview(root, args.max_line_chars)
    shown = {}
    for r in records:
        rel = r["path"].relative_to(args.unit)
        if r["status"] == "skipped":
            print(f"== {rel}  (skipped: {r['path'].suffix or 'no extension'})\n")
            continue
        key = (r["path"].suffix.lower(), r["lines"][0]) if r["path"].suffix.lower() in TEXT_EXT and r["lines"] else None
        if key in shown:
            count = next((l for l in r["lines"] if l.startswith("lines: ")), "").split(" (")[0]
            print(f"== {rel}\n(same header as {shown[key]}; {count})\n")
            continue
        if key:
            shown[key] = rel.name
        print(f"== {rel}\n" + "\n".join(r["lines"]) + "\n")
    counts = {s: sum(r["status"] == s for r in records) for s in ("ok", "skipped", "error")}
    print(f"files={len(records)} previewed={counts['ok']} skipped={counts['skipped']} errors={counts['error']}", file=sys.stderr)
    return 1 if not records else 3 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
