"""Shared helpers for the RCSF joints.csv <-> skels/*.toml round-trip tools.

Python 3.11+ ships ``tomllib`` for *reading* TOML but has no writer, so this
module provides a small, dependency-free TOML emitter that is sufficient for
our data: flat tables of string keys mapped to string values. Strings are
emitted as TOML basic strings with correct escaping, so the round-trip stays
lossless even if odd characters appear later.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Layout constants (single source of truth shared by split + join)
# ---------------------------------------------------------------------------

CSV_PATH = "joints.csv"
SKELS_DIR = "skels"
PIVOT_NAME = "_canonical.toml"

# CSV on disk uses CRLF line endings (verified); reproduce exactly.
CSV_NEWLINE = "\r\n"


# ---------------------------------------------------------------------------
# Filenames
# ---------------------------------------------------------------------------

def skeleton_filename(name: str) -> str:
    """Map an authoritative skeleton name to a filesystem-safe TOML filename.

    Only the path-separating characters need replacing (e.g. ``ASF/AMC`` ->
    ``ASF_AMC.toml``). The authoritative name is always stored *inside* the
    file and in the pivot, so this mapping never needs to be reversed.
    """
    safe = name.replace("/", "_").replace("\\", "_")
    return f"{safe}.toml"


# ---------------------------------------------------------------------------
# TOML emitter (writer)
# ---------------------------------------------------------------------------

_BASIC_ESCAPES = {
    "\\": "\\\\",
    "\"": "\\\"",
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def toml_basic_string(s: str) -> str:
    """Encode *s* as a TOML basic string, including surrounding quotes."""
    out = ["\""]
    for ch in s:
        if ch in _BASIC_ESCAPES:
            out.append(_BASIC_ESCAPES[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    out.append("\"")
    return "".join(out)


def toml_key(key: str) -> str:
    """Encode a table key. We always quote to stay safe regardless of content."""
    return toml_basic_string(key)


def dump_string_array(key: str, values: list[str]) -> str:
    """Emit ``key = [ ... ]`` with one string entry per line (stable, diff-able)."""
    if not values:
        return f"{key} = []\n"
    lines = [f"{key} = ["]
    for v in values:
        lines.append(f"    {toml_basic_string(v)},")
    lines.append("]\n")
    return "\n".join(lines)


def dump_table(values: dict[str, str]) -> str:
    """Emit a flat table body (``"k" = "v"`` lines), preserving insertion order."""
    return "".join(
        f"{toml_key(k)} = {toml_basic_string(v)}\n" for k, v in values.items()
    )
