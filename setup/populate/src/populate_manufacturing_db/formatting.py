"""Shared formatting helpers for query output display."""

from __future__ import annotations

_W = 70


def header(title: str, description: str) -> None:
    """Print a section header with title and description."""
    print(f"\n{'=' * _W}")
    print(f"  {title}")
    print(f"{'=' * _W}")
    print(f"\n  {description}\n")


def cypher(query: str) -> None:
    """Pretty-print a Cypher query with consistent indentation."""
    lines = query.strip().splitlines()
    indents = [len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()]
    base = min(indents) if indents else 0
    print("  Cypher:")
    for ln in lines:
        print(f"    {ln[base:]}")
    print()


def table(headers: list[str], rows: list[list], widths: list[int] | None = None) -> None:
    """Print a formatted table with auto-calculated column widths."""
    if not rows:
        print("  (no results)\n")
        return
    if widths is None:
        widths = []
        for i, h in enumerate(headers):
            col_max = len(h)
            for row in rows:
                col_max = max(col_max, len(str(row[i] if i < len(row) else "")))
            widths.append(min(col_max + 1, 50))
    print("  " + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("  " + "  ".join("\u2500" * w for w in widths))
    for row in rows:
        cells = []
        for v_item, w in zip(row, widths):
            s = str(v_item) if v_item is not None else "\u2014"
            if len(s) > w:
                s = s[: w - 1] + "\u2026"
            cells.append(s.ljust(w))
        print("  " + "  ".join(cells))
    print()


def val(v, max_len: int = 0) -> str:
    """Format a value for display, optionally truncating to max_len."""
    s = str(v) if v is not None else "\u2014"
    if max_len and len(s) > max_len:
        s = s[: max_len - 1] + "\u2026"
    return s


def banner(text: str) -> None:
    """Print a prominent banner line."""
    print(f"\n{'#' * _W}")
    print(f"  {text}")
    print(f"{'#' * _W}")
