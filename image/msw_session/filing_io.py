"read_filing for the Python session: mechanical reading of an inline-XBRL filing (a .zip bundle or an .htm/.xhtml file)\ninto tagged facts with their contexts and units, the document's tables as cells, and the visible text. It does not know\nany task's fields, choose answers or compute financial measures; every conversion it makes is reported with a status, and\nanything it does not convert is left as text."
import datetime
import decimal
import re
import types
import zipfile

from bs4 import BeautifulSoup
from lxml import etree

DOC_SUFFIXES = (".htm", ".html", ".xhtml")
IX = "http://www.xbrl.org/2013/inlineXBRL"
NEARBY_UNIT = re.compile(r"\(([^()]*\b(?:thousands|millions|billions)\b[^()]*)\)|\bin (?:thousands|millions|billions)\b", re.I)
PLAIN_NUMBER = re.compile(r"\d+(\.\d+)?|\.\d+")
GROUPED = {"numdotdecimal": re.compile(r"\d{1,3}([,  ]\d{3})*(\.\d+)?|\d+(\.\d+)?"),
           "numcommadecimal": re.compile(r"\d{1,3}([.  ]\d{3})*(,\d+)?|\d+(,\d+)?")}
ZERO_FORMATS = {"fixedzero", "zerodash", "numdash"}
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
MONTH_NAME = r"([A-Za-z]{3,9})\.?"
DATE_FORMATS = {"datedaymonthyear": (r"(\d{1,2})\W+(\d{1,2})\W+(\d{4})", "dmy"),
                "datemonthdayyear": (r"(\d{1,2})\W+(\d{1,2})\W+(\d{4})", "mdy"),
                "dateyearmonthday": (r"(\d{4})\W+(\d{1,2})\W+(\d{1,2})", "ymd"),
                "datemonthnamedayyearen": (MONTH_NAME + r"\s*(\d{1,2})\s*,?\s*(\d{4})", "Ndy"),
                "datedaymonthnameyearen": (r"(\d{1,2})\s*" + MONTH_NAME + r"\s*,?\s*(\d{4})", "dNy")}
NO_YEAR_FORMATS = {"datemonthnamedayen", "datedaymonthnameen", "datemonthday", "datedaymonth"}
HIDDEN_STYLE = re.compile(r"display\s*:\s*none", re.I)
BOOLEAN_FORMATS = {"boolballotbox": {"\u2612": True, "\u2610": False}, "fixedtrue": None, "fixedfalse": None}
BLOCKS = ("p", "div", "td", "li")
MULTIPLIERS = {"thousands": 1e3, "millions": 1e6, "billions": 1e9}


def _local(fmt):
    """The transformation's local name without prefix, hyphens or case: ixt:date-day-month-year -> datedaymonthyear."""
    return (fmt or "").split(":")[-1].replace("-", "").lower()


def _ix_elements_present(raw):
    """True when the document parses as XML and has at least one element in the inline-XBRL namespace."""
    try:
        root = etree.fromstring(raw, etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False))
    except etree.XMLSyntaxError:
        return False
    return root is not None and any(isinstance(e.tag, str) and e.tag.startswith("{" + IX + "}") for e in root.iter())


def ixbrl_candidates(path):
    """Names of the documents in a bundle (or the file itself) that contain inline-XBRL elements."""
    if not str(path).lower().endswith(".zip"):
        with open(path, "rb") as f:
            return [str(path)] if _ix_elements_present(f.read()) else []
    with zipfile.ZipFile(path) as z:
        return [n for n in z.namelist() if n.lower().endswith(DOC_SUFFIXES) and _ix_elements_present(z.read(n))]


def _is_ix(tag, name=None):
    return getattr(tag, "namespace", None) == IX and (name is None or tag.name == name)


def _strings_outside_exclude(tag):
    """The text of a fact element, leaving out ix:exclude content."""
    return " ".join(s.strip() for s in tag.find_all(string=True)
                    if s.strip() and not any(_is_ix(p, "exclude") for p in s.parents)).strip()


def _number(text, fmt):
    """(Decimal, status) for the displayed number under no format, a grouped number format or a zero format; else (None, reason)."""
    f, t = _local(fmt), text.strip()
    if f in ZERO_FORMATS:
        return decimal.Decimal(0), "ok"
    if f and f not in GROUPED:
        return None, f"unsupported-format {fmt}"
    if not (GROUPED[f] if f else PLAIN_NUMBER).fullmatch(t):
        return None, "unparsed-number"
    if f == "numdotdecimal":
        t = re.sub(r"[,  ]", "", t)
    elif f == "numcommadecimal":
        t = re.sub(r"[.  ]", "", t).replace(",", ".")
    return decimal.Decimal(t), "ok"


def _boolean(text, fmt):
    """(bool, status) for a ballot-box or fixed true/false transformation; (None, status) for any other mark."""
    f = _local(fmt)
    if f in ("fixedtrue", "fixedfalse"):
        return f == "fixedtrue", "ok"
    value = BOOLEAN_FORMATS[f].get(text.strip())
    return (value, "ok") if value is not None else (None, f"unparsed-boolean {fmt}")


def _date(text, fmt):
    """(ISO date, status) for a supported date transformation; (None, status) otherwise; no parser is asked to guess."""
    f = _local(fmt)
    if not fmt:
        return text, "text"
    if f in BOOLEAN_FORMATS:
        return _boolean(text, fmt)
    if not f.startswith("date"):
        return None, f"unsupported-format {fmt}"
    if f in NO_YEAR_FORMATS:
        return None, f"date-without-year {fmt}"
    if f not in DATE_FORMATS:
        return None, f"unsupported-format {fmt}"
    pattern, order = DATE_FORMATS[f]
    m = re.fullmatch(pattern, re.sub(r"\s+", " ", text.strip()))
    if not m:
        return None, f"unparsed-date {fmt}"
    parts = dict(zip(order, m.groups()))
    month = MONTHS.get(parts["N"][:3].lower()) if "N" in parts else int(parts["m"])
    try:
        return datetime.date(int(parts["y"]), month or 0, int(parts["d"])).isoformat(), "ok"
    except (ValueError, TypeError):
        return None, f"unparsed-date {fmt}"


def _contexts(soup):
    out = {}
    for c in soup.find_all("context"):
        p = c.find("period")
        get = lambda name: (p.find(name).get_text(strip=True) if p and p.find(name) else None)
        members = [(m.get("dimension"), m.get_text(strip=True)) for m in c.find_all(["explicitMember", "typedMember"])]
        out[c.get("id")] = dict(start=get("startDate"), end=get("endDate"), instant=get("instant"), members=members)
    return out


def _units(soup):
    out = {}
    for u in soup.find_all("unit"):
        num, den = u.find("unitNumerator"), u.find("unitDenominator")
        measures = lambda node: " ".join(m.get_text(strip=True) for m in node.find_all("measure"))
        out[u.get("id")] = f"{measures(num)} / {measures(den)}" if num and den else measures(u)
    return out


def _is_nil(t):
    return any(k.split(":")[-1] == "nil" and v.strip().lower() in ("true", "1") for k, v in t.attrs.items())


def _block_text(t):
    """The text of the paragraph, division, cell or list item that holds a fact, or "" for a hidden fact."""
    block = t.find_parent(BLOCKS)
    if block is None or any(_is_ix(p, "header") for p in t.parents):
        return ""
    return " ".join(s.strip() for s in block.find_all(string=True) if s.strip())


def _facts(soup, contexts, units, blocks, tags):
    continuation = {c.get("id"): c for c in soup.find_all("continuation") if _is_ix(c)}
    facts = []
    for order, t in enumerate(x for x in soup.find_all(["nonFraction", "nonNumeric"]) if _is_ix(x)):
        text = _strings_outside_exclude(t)
        nxt, seen, chain = t.get("continuedAt"), set(), "none"
        while nxt:
            if nxt in seen or nxt not in continuation:
                chain = f"{'cycle' if nxt in seen else 'missing'} {nxt}"
                break
            seen.add(nxt)
            text = (text + " " + _strings_outside_exclude(continuation[nxt])).strip()
            nxt, chain = continuation[nxt].get("continuedAt"), "ok"
        ctx = contexts.get(t.get("contextRef"), {})
        nil, fmt, exact = _is_nil(t), t.get("format"), None
        if nil:
            value, status = None, "nil"
        elif chain not in ("none", "ok"):
            value, status = None, "incomplete-continuation"
        elif t.name == "nonFraction":
            exact, status = _number(text, fmt)
            if exact is not None:
                exact = exact.scaleb(int(t.get("scale") or 0))
                exact = -exact if t.get("sign") == "-" else exact
            value = None if exact is None else float(exact)
        else:
            value, status = _date(text, fmt)
        facts.append(dict(concept=t.get("name"), kind=t.name, value_text=text, value=value, value_exact=exact,
                          float_rounded=exact is not None and decimal.Decimal(repr(value)) != exact, conversion=status,
                          format=fmt, continuation=chain, scale=t.get("scale"), sign=t.get("sign"),
                          decimals=t.get("decimals"), nil=nil, context=t.get("contextRef"),
                          context_found=t.get("contextRef") in contexts, period_start=ctx.get("start"),
                          period_end=ctx.get("end"), instant=ctx.get("instant"), members=ctx.get("members", []),
                          unit=t.get("unitRef"), unit_measure=units.get(t.get("unitRef")),
                          hidden=any(_is_ix(p, "hidden") for p in t.parents), order=order))
        blocks.append(_block_text(t))
        tags[id(t)] = facts[-1]
    return facts


def _metadata(s):
    """True for a string inside ix:header, a script or a style element."""
    return any(_is_ix(p, "header") or p.name in ("script", "style") for p in s.parents)


def _own_text(cell, table):
    """The cell's text without the content of any table nested inside it."""
    return " ".join(s.strip() for s in cell.find_all(string=True) if s.strip() and s.find_parent("table") is table)


def _cell_value(cell, table, tags):
    """(converted value, fact orders) of the numeric facts tagged in a cell; the value only when exactly one is there."""
    found = [tags[id(t)] for t in cell.find_all("nonFraction") if id(t) in tags and t.find_parent("table") is table]
    return (found[0]["value"] if len(found) == 1 else None), [f["order"] for f in found]


def _tables(soup, tags):
    """Each table with its own rows only (a nested table is a table of its own), its cells (text, row, col, colspan,
    rowspan, header, nested_table), a grid of cell texts with every source row kept and colspan and rowspan positions left
    empty so rows and columns line up, and the text found just before it and in its own cells that names an amount unit;
    that text is evidence to read, not a unit assigned to every column."""
    tables = []
    for i, tb in enumerate(soup.find_all("table")):
        own = [tr for tr in tb.find_all("tr") if tr.find_parent("table") is tb]
        cells, taken, valued = [], {}, {}
        for r, tr in enumerate(own):
            row_cells, col = [], 0
            for c in tr.find_all(["td", "th"], recursive=False):
                while (r, col) in taken:
                    col += 1
                value, orders = _cell_value(c, tb, tags)
                cell = dict(text=_own_text(c, tb), row=r, col=col, colspan=int(c.get("colspan") or 1),
                            rowspan=int(c.get("rowspan") or 1), header=c.name == "th", nested_table=c.find("table") is not None,
                            facts=orders)
                valued[(r, col)] = value
                for dr in range(cell["rowspan"]):
                    for dc in range(cell["colspan"]):
                        taken[(r + dr, col + dc)] = cell["text"] if dr == dc == 0 else ""
                row_cells.append(cell)
                col += cell["colspan"]
            cells.append(row_cells)
        width = 1 + max((c for _, c in taken), default=-1)
        rows = [[taken.get((r, c), "") for c in range(width)] for r in range(max([len(own)] + [r + 1 for r, _ in taken]))]
        values = [[valued.get((r, c)) for c in range(width)] for r in range(len(rows))]
        if not any(any(row) for row in rows):
            continue
        before = []
        for s in tb.find_all_previous(string=True, limit=80):
            if s.strip() and not _metadata(s):
                before.append(s.strip())
            if sum(len(x) for x in before) > 300:
                break
        nearby = " ".join(reversed(before))[-300:]
        after = []
        for s in tb.find_all_next(string=True, limit=80):
            if s.strip() and s.find_parent("table") is None and not _metadata(s):
                after.append(s.strip())
            if sum(len(x) for x in after) > 400 or (s.find_parent("table") is not None and after):
                break
        notes_after = " ".join(after)[:400]
        note = NEARBY_UNIT.search(nearby)
        inner_note = next((m.group(0) for row in rows for x in row for m in [NEARBY_UNIT.search(x)] if m), None)
        stated = inner_note or (note.group(0) if note else None)
        word = re.search(r"thousands|millions|billions", stated or "", re.I)
        tables.append(dict(index=i, nearby_text=nearby, nearby_unit_note=note.group(0) if note else None,
                           unit_note_in_table=inner_note, notes_after=notes_after, multiplier_from_note=MULTIPLIERS[word.group(0).lower()] if word else None,
                           rows=rows, values=values, cells=cells))
    return tables


def _visible_text(raw):
    """Text of a separate tree with ix:header (hidden facts, contexts, units), scripts, styles and elements whose own style
    attribute says display:none removed; CSS classes and stylesheets are not evaluated."""
    view = BeautifulSoup(raw, "xml")
    for t in [t for t in view.find_all(True) if _is_ix(t, "header") or t.name in ("script", "style")
              or HIDDEN_STYLE.search(t.get("style") or "")]:
        if not t.decomposed:
            t.decompose()
    body = view.find("body") or view
    return "\n".join(s.strip() for s in body.find_all(string=True) if s.strip())


def read_filing(path, member=None):
    """Reads an inline-XBRL filing: a .zip bundle (its inline-XBRL document; pass member= when the bundle has more than one)
    or an .htm/.html/.xhtml file. Returns a namespace with:
      main        the document read
      facts       list of dicts: concept, kind, value_text (ix:exclude left out, continuations joined; continuation is
                  none, ok, "missing <id>" or "cycle <id>"), value (float for numbers, ISO date, bool, the text itself for a fact without format, else None), value_exact (Decimal, numbers only),
                  float_rounded, conversion (ok, text, nil, unparsed-number, unsupported-format <f>, unparsed-date <f>,
                  date-without-year <f>, unparsed-boolean <f>, incomplete-continuation; ballot-box and fixed true/false
                  formats give True/False), format, scale, sign, decimals, nil, context,
                  context_found, period_start, period_end, instant, members, unit, unit_measure, hidden, order
      contexts, units
      tables      list of dicts: index (document order), nearby_text, nearby_unit_note, unit_note_in_table,
                  notes_after (the text right after the table, where footnotes such as unit statements usually are),
                  multiplier_from_note (1e3/1e6/1e9 read from the in-table note, else the note before it; evidence to check
                  against the note's wording, e.g. "except per share"), rows (a grid
                  of cell texts, every source row kept; colspan and rowspan positions empty), values (the same grid
                  holding the converted value of the one numeric fact tagged in a cell, scale and sign applied, else
                  None), cells (text, row, col, colspan, rowspan, header, nested_table, facts: orders of facts in the cell); a cell covers rows row..row+rowspan-1, columns col..col+colspan-1
      text        visible text: ix:header, scripts, styles and inline display:none left out (hidden facts stay in facts)
      check       counts and resolution shares, to inspect before use
      find_facts(substring), find_rows(substring), find_values(substring) (rows with their values grid),
      find_tables(text) (tables whose cells or rows contain the plain text, with all their rows), show_table(index) (one table as compact text), search_text(pattern, width), facts_near(pattern) (facts tagged inside
      the paragraph, division, cell or list item a phrase appears in), facts_in_context(context_id)
    Only the number and date transformations listed in this module are converted; any other stays text with its status.
    """
    if str(path).lower().endswith(".zip"):
        candidates = ixbrl_candidates(path)
        if member is not None and member not in candidates:
            raise ValueError(f"{member!r} is not an inline-XBRL document in the bundle; candidates: {candidates}")
        if member is None:
            if len(candidates) != 1:
                raise ValueError(f"{len(candidates)} inline-XBRL documents in the bundle; pass member= one of {candidates}")
            member = candidates[0]
        with zipfile.ZipFile(path) as z:
            raw = z.read(member)
        main = member
    else:
        main = str(path)
        with open(path, "rb") as f:
            raw = f.read()
        if not _ix_elements_present(raw):
            raise ValueError(f"{main!r} has no inline-XBRL elements")
    soup = BeautifulSoup(raw, "xml")
    contexts, units = _contexts(soup), _units(soup)
    blocks, tags = [], {}
    facts = _facts(soup, contexts, units, blocks, tags)
    tables = _tables(soup, tags)
    text = _visible_text(raw)
    numeric = [f for f in facts if f["kind"] == "nonFraction"]
    check = dict(facts=len(facts), numeric=len(numeric), non_numeric=len(facts) - len(numeric),
                 contexts_resolved=sum(f["context_found"] for f in facts) / max(1, len(facts)),
                 units_resolved=sum(f["unit"] in units for f in numeric) / max(1, len(numeric)),
                 numeric_converted=sum(f["conversion"] == "ok" for f in numeric) / max(1, len(numeric)),
                 not_converted=sorted({f["conversion"] for f in facts if f["conversion"] not in ("ok", "text")}),
                 continuation_problems=sorted({f["continuation"] for f in facts if f["continuation"] not in ("none", "ok")}),
                 float_rounded=sum(f["float_rounded"] for f in facts), hidden_facts=sum(f["hidden"] for f in facts),
                 tables=len(tables), text_chars=len(text))

    def find_facts(substring):
        """Facts whose concept name contains the substring, case-insensitive."""
        s = substring.lower()
        return [f for f in facts if f["concept"] and s in f["concept"].lower()]

    def find_rows(substring):
        """(table index, row texts) for each table row whose joined text contains the substring, case-insensitive."""
        s = substring.lower()
        return [(t["index"], r) for t in tables for r in t["rows"] if s in " ".join(r).lower()]

    def find_values(substring):
        """(table index, row texts, row values) for each row whose text contains the substring."""
        s = substring.lower()
        return [(t["index"], r, v) for t in tables for r, v in zip(t["rows"], t["values"]) if s in " ".join(r).lower()]

    def facts_near(pattern):
        """Facts whose paragraph, division, cell or list item matches the pattern, each with that text as "near"."""
        return [dict(f, near=b[:400]) for f, b in zip(facts, blocks) if b and re.search(pattern, b, re.I)]

    def facts_in_context(context_id):
        """Facts whose context id equals context_id, in document order."""
        return [f for f in facts if f["context"] == context_id]

    def find_tables(text):
        """(table index, all its rows with empty cells dropped) for each table where the plain text (case-insensitive, not a
        regex) is in a cell or in a row written as show_table writes it ("cell | cell")."""
        s, out = text.lower(), []
        for t in tables:
            compact = [[x for x in r if x] for r in t["rows"]]
            if any(s in x.lower() for r in compact for x in r) or any(s in " | ".join(r).lower() for r in compact):
                out.append((t["index"], [r for r in compact if r]))
        return out

    def show_table(index, max_rows=80):
        """One table as text: its stated unit notes and the text right after it, then each non-empty row as 'row number: cell | cell', empty cells dropped."""
        (t,) = [t for t in tables if t["index"] == index]
        lines = [f"table {index}; unit note in table: {t['unit_note_in_table']}; before it: {t['nearby_unit_note']}"]
        if t["notes_after"]:
            lines.append(f"text right after the table (footnotes, units): {t['notes_after'][:300]}")
        lines += [f"{r}: " + " | ".join(x for x in row if x) for r, row in enumerate(t["rows"][:max_rows]) if any(row)]
        return "\n".join(lines)

    def search_text(pattern, width=200):
        """Pieces of the visible text around each match of the regex pattern (case-insensitive), width characters each side."""
        return [text[max(0, m.start() - width):m.end() + width] for m in re.finditer(pattern, text, re.I)]

    return types.SimpleNamespace(main=main, facts=facts, contexts=contexts, units=units, tables=tables, text=text,
                                 check=check, find_facts=find_facts, find_rows=find_rows, search_text=search_text,
                                 facts_near=facts_near, facts_in_context=facts_in_context, find_values=find_values,
                                 find_tables=find_tables, show_table=show_table)
