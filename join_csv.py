#!/usr/bin/env python3
"""Stitch skels/*.toml back into a CSV and verify it matches joints.csv.

Reconstruction order is driven entirely by skels/_canonical.toml (the pivot):
the ``skeletons`` list gives column order, the ``joints`` list gives row order.
Each per-skeleton file supplies the cell values.

Verification happens at two levels:
  1. logical  - parse both CSVs and compare cell-by-cell (did we recover data?)
  2. byte      - compare raw bytes / md5 (is the round-trip byte-exact?)

Usage:
    python3 join_csv.py                 # verify against joints.csv (no write)
    python3 join_csv.py -o out.csv      # also write reconstructed CSV to out.csv
    python3 join_csv.py --write         # overwrite joints.csv (only if verified)
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", metavar="PATH",
                    help="write reconstructed CSV to PATH")
    ap.add_argument("--write", action="store_true",
                    help=f"overwrite {rcsf.CSV_PATH} (only if verification passes)")
    args = ap.parse_args()

    header, data = reconstruct()
    ok = verify(header, data)

    if args.output:
        with open(args.output, "wb") as f:
            f.write(to_csv_bytes(header, data))
        print(f"Wrote reconstructed CSV to {args.output}")

    if args.write:
        if not ok:
            print("Refusing to overwrite: verification failed.", file=sys.stderr)
            return 1
        with open(rcsf.CSV_PATH, "wb") as f:
            f.write(to_csv_bytes(header, data))
        print(f"Overwrote {rcsf.CSV_PATH} (verified identical).")

    if ok:
        print("\nRound-trip verified: skels/ fully reproduces joints.csv.")
        return 0
    print("\nRound-trip FAILED. See differences above.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
