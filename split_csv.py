#!/usr/bin/env python3
"""Blast joints.csv apart into one TOML file per skeleton, under skels/.

Each column of joints.csv (other than the canonical/pivot column) is a
skeleton standard. This writes:

  skels/_canonical.toml   the pivot: authoritative column order + row order
  skels/<Skeleton>.toml   per-skeleton map of canonical joint -> cell value

Run join_csv.py afterwards to stitch the CSV back together and verify the
round-trip is lossless.

Usage:
    python3 split_csv.py            # reads joints.csv, writes skels/
"""

from __future__ import annotations

import csv
import os
import sys

import rcsf


def main() -> int:
    with open(rcsf.CSV_PATH, newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        print(f"error: {rcsf.CSV_PATH} is empty", file=sys.stderr)
        return 1

    header = rows[0]
    data = rows[1:]

    canonical_column = header[0]
    skeletons = header[1:]
    joints = [r[0] for r in data]

    if len(set(joints)) != len(joints):
        print("error: canonical joint names are not unique; "
              "cannot key skeleton files by them", file=sys.stderr)
        return 1

    os.makedirs(rcsf.SKELS_DIR, exist_ok=True)

    # --- Pivot file: the canonical spine everything hangs off of. ----------
    pivot_path = os.path.join(rcsf.SKELS_DIR, rcsf.PIVOT_NAME)
    with open(pivot_path, "w", newline="\n") as f:
        f.write("# RCSF pivot. Authoritative CSV column and row order.\n")
        f.write("# Regenerate joints.csv from skels/ with: python3 join_csv.py\n\n")
        f.write(f"canonical_column = {rcsf.toml_basic_string(canonical_column)}\n\n")
        f.write("# Skeleton columns, in CSV order (authoritative names).\n")
        f.write(rcsf.dump_string_array("skeletons", skeletons))
        f.write("\n# Canonical joints, in CSV row order.\n")
        f.write(rcsf.dump_string_array("joints", joints))

    # --- One file per skeleton. --------------------------------------------
    for col, skel in enumerate(skeletons, start=1):
        values = {joints[i]: data[i][col] for i in range(len(data))}
        path = os.path.join(rcsf.SKELS_DIR, rcsf.skeleton_filename(skel))
        with open(path, "w", newline="\n") as f:
            f.write(f"# Skeleton: {skel}\n")
            f.write("# canonical joint = this skeleton's joint name "
                    "('-' = no mapping).\n\n")
            f.write(f"skeleton = {rcsf.toml_basic_string(skel)}\n\n")
            f.write("[values]\n")
            f.write(rcsf.dump_table(values))

    print(f"Wrote pivot + {len(skeletons)} skeleton files to {rcsf.SKELS_DIR}/")
    print(f"  {rcsf.PIVOT_NAME}: {len(joints)} joints x {len(skeletons)} skeletons")
    for skel in skeletons:
        print(f"  {rcsf.skeleton_filename(skel)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
