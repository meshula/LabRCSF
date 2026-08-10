#!/usr/bin/env python3
"""Stitch skels/*.toml back into joints.csv, in two modes.

Reconstruction order is driven entirely by skels/_canonical.toml (the pivot):
the ``skeletons`` list gives column order, the ``joints`` list gives row order.
Each per-skeleton file supplies the cell values.

There are two ways to use this, matching the two directions data can flow:

  check (default) - reconstruct from skels/ and confirm it still reproduces
                    joints.csv, both logically (cell-by-cell) and byte-exact.
                    Exits non-zero on any drift. Use after a split, or in CI.

  --write (apply) - treat skels/ as the source of truth: regenerate joints.csv
                    from it, printing a summary of exactly which cells changed
                    so an edit is self-reviewing. This is the contributor loop:
                    edit a skels/*.toml, run --write, eyeball the diff, commit.

Usage:
    python3 join_csv.py                 # check: does skels/ still match joints.csv?
    python3 join_csv.py --write         # apply: regenerate joints.csv from skels/
    python3 join_csv.py -o out.csv      # write reconstruction to out.csv (joints.csv untouched)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import sys
import tomllib

import rcsf


def load_pivot() -> dict:
    path = os.path.join(rcsf.SKELS_DIR, rcsf.PIVOT_NAME)
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_skeleton(skel: str) -> dict[str, str]:
    path = os.path.join(rcsf.SKELS_DIR, rcsf.skeleton_filename(skel))
    with open(path, "rb") as f:
        doc = tomllib.load(f)
    if doc.get("skeleton") != skel:
        raise ValueError(
            f"{path}: 'skeleton' is {doc.get('skeleton')!r}, expected {skel!r}"
        )
    return doc.get("values", {})


def reconstruct() -> tuple[list[str], list[list[str]]]:
    """Return (header, data_rows) rebuilt from the pivot + skeleton files."""
    pivot = load_pivot()
    canonical_column = pivot["canonical_column"]
    skeletons = pivot["skeletons"]
    joints = pivot["joints"]

    tables = {skel: load_skeleton(skel) for skel in skeletons}

    header = [canonical_column] + list(skeletons)
    data = []
    for joint in joints:
        row = [joint]
        for skel in skeletons:
            values = tables[skel]
            if joint not in values:
                raise KeyError(
                    f"skeleton {skel!r} is missing canonical joint {joint!r}"
                )
            row.append(values[joint])
        data.append(row)
    return header, data


def to_csv_bytes(header: list[str], data: list[list[str]]) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator=rcsf.CSV_NEWLINE)
    writer.writerow(header)
    writer.writerows(data)
    return buf.getvalue().encode("utf-8")


def load_original_cells() -> list[list[str]]:
    with open(rcsf.CSV_PATH, newline="") as f:
        return list(csv.reader(f))


def verify(header: list[str], data: list[list[str]]) -> bool:
    ok = True

    # 1. Logical comparison (the "did we recover the data" check).
    rebuilt_cells = [header] + data
    original_cells = load_original_cells()
    if rebuilt_cells == original_cells:
        print(f"[logical] OK  - {len(data)} rows x {len(header)} cols match cell-for-cell")
    else:
        ok = False
        print("[logical] FAIL - cell contents differ:", file=sys.stderr)
        _report_cell_diffs(original_cells, rebuilt_cells)

    # 2. Byte-exact comparison.
    rebuilt_bytes = to_csv_bytes(header, data)
    with open(rcsf.CSV_PATH, "rb") as f:
        original_bytes = f.read()
    r_md5 = hashlib.md5(rebuilt_bytes).hexdigest()
    o_md5 = hashlib.md5(original_bytes).hexdigest()
    if rebuilt_bytes == original_bytes:
        print(f"[byte]    OK  - byte-exact, md5 {r_md5}")
    else:
        ok = False
        print(f"[byte]    FAIL - md5 rebuilt {r_md5} != original {o_md5}",
              file=sys.stderr)
        print(f"          sizes: rebuilt {len(rebuilt_bytes)} B, "
              f"original {len(original_bytes)} B", file=sys.stderr)

    return ok


def _report_cell_diffs(original: list[list[str]], rebuilt: list[list[str]]) -> None:
    if len(original) != len(rebuilt):
        print(f"          row count: original {len(original)}, "
              f"rebuilt {len(rebuilt)}", file=sys.stderr)
    shown = 0
    for r, (orow, rrow) in enumerate(zip(original, rebuilt)):
        if orow == rrow:
            continue
        for c, (ocell, rcell) in enumerate(zip(orow, rrow)):
            if ocell != rcell:
                print(f"          row {r} col {c}: "
                      f"original {ocell!r} != rebuilt {rcell!r}", file=sys.stderr)
                shown += 1
                if shown >= 20:
                    print("          ... (further differences suppressed)",
                          file=sys.stderr)
                    return


def summarize_changes(header: list[str], data: list[list[str]]) -> None:
    """Print how the reconstruction differs from the current joints.csv.

    Used by --write so an edit is self-reviewing (this is what catches
    off-by-one / wrong-cell mistakes before they land).
    """
    if not os.path.exists(rcsf.CSV_PATH):
        print(f"{rcsf.CSV_PATH} does not exist yet; creating it.")
        return

    old = load_original_cells()
    new = [header] + data
    old_cols, new_cols = old[0], new[0]
    added = [c for c in new_cols if c not in old_cols]
    removed = [c for c in old_cols if c not in new_cols]
    if added:
        print(f"  + columns added: {', '.join(added)}")
    if removed:
        print(f"  - columns removed: {', '.join(removed)}")
    if len(old) != len(new):
        print(f"  rows: {len(old) - 1} -> {len(new) - 1}")

    # Cell-level changes on columns/rows common to both.
    old_hdr_idx = {c: i for i, c in enumerate(old_cols)}
    old_rows = {r[0]: r for r in old[1:]}
    changes = 0
    for nrow in new[1:]:
        joint = nrow[0]
        orow = old_rows.get(joint)
        if orow is None:
            print(f"  + row added: {joint}")
            continue
        for c, col in enumerate(new_cols):
            if col not in old_hdr_idx:
                continue
            ocell = orow[old_hdr_idx[col]]
            if nrow[c] != ocell:
                changes += 1
                if changes <= 40:
                    print(f"  [{col}] {joint}: {ocell!r} -> {nrow[c]!r}")
    if changes > 40:
        print(f"  ... and {changes - 40} more cell change(s)")
    total = changes + len(added) + len(removed)
    print(f"  ({changes} cell change(s)"
          + (f", {len(added)} column(s) added" if added else "")
          + (f", {len(removed)} column(s) removed" if removed else "") + ")")
    if total == 0:
        print("  (no changes: joints.csv already matches skels/)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", metavar="PATH",
                    help="write reconstructed CSV to PATH (leaves joints.csv untouched)")
    ap.add_argument("--write", action="store_true",
                    help=f"apply: regenerate {rcsf.CSV_PATH} from skels/ (the source of truth)")
    args = ap.parse_args()

    # reconstruct() raises on any structural problem (missing joint in a
    # skeleton file, skeleton-name mismatch, unknown pivot entry).
    header, data = reconstruct()

    if args.output:
        with open(args.output, "wb") as f:
            f.write(to_csv_bytes(header, data))
        print(f"Wrote reconstructed CSV to {args.output}")

    if args.write:
        print(f"Regenerating {rcsf.CSV_PATH} from skels/ (source of truth):")
        summarize_changes(header, data)
        with open(rcsf.CSV_PATH, "wb") as f:
            f.write(to_csv_bytes(header, data))
        print(f"Wrote {rcsf.CSV_PATH} ({len(header)} columns, {len(data)} rows).")
        return 0

    # check mode: does skels/ still reproduce joints.csv exactly?
    ok = verify(header, data)
    if ok:
        print("\nRound-trip verified: skels/ fully reproduces joints.csv.")
        return 0
    print("\nMismatch: skels/ and joints.csv differ. "
          "Run with --write to regenerate joints.csv from skels/.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
