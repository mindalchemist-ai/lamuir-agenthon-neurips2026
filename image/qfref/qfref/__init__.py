"""A small finance reference: catalog() lists the entries, show(name) prints one."""
import json
import pathlib

_DIR = pathlib.Path(__file__).parent / "entries"

ENTRIES = {name: entry["line"] for name, entry in json.loads((_DIR / "index.json").read_text()).items()}


def catalog() -> None:
    """Print every entry name with its one-line description."""
    for name, line in ENTRIES.items():
        print(f"{name}: {line}")


def show(name: str) -> None:
    """Print the entry whose name, or whose description, contains `name` (case-insensitive)."""
    q = name.strip().lower()
    hits = [n for n, line in ENTRIES.items() if q == n or q in line.lower()]
    if not hits:
        print(f"No entry matches {name!r}. Entries: {', '.join(ENTRIES)}")
        return
    for n in hits:
        print((_DIR / f"{n}.md").read_text())
