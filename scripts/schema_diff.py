#!/usr/bin/env python3
"""Diff two SWAT+ schema artifacts to see what a new release changed.

This is the first step of the per-release cadence: when a SWAT+ version is
approved and ``swatplus-doc-builder`` emits a new
``schemas/swatplus-<ver>.json``, run this against the version currently in use
to see exactly which input files changed shape.  The output is meant to be
pasted into the pull request that adopts the new version, so the review is
about a specific list of format changes rather than a version bump.

What it reports, per file:

* fields added / removed (with Fortran type)
* fields whose type changed (e.g. ``integer`` -> ``real``)
* fields that moved position -- these are the dangerous ones, because a
  reordered read assigns existing values to different variables
* files that appeared, disappeared, or became unresolvable

A field is matched between versions by name, not position, so a field that
moved is reported as moved rather than as an unrelated add plus remove.

Usage:
    python scripts/schema_diff.py --from 62.0.0 --to 63.0.0 [--repo-root .]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMAS_DIR = "schemas"


def load(repo_root: Path, version: str) -> dict:
    p = repo_root / SCHEMAS_DIR / f"swatplus-{version}.json"
    if not p.is_file():
        raise SystemExit(f"no artifact for version {version}: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _fields(entry: dict) -> dict[str, dict]:
    return {f["fortran_name"]: f for f in entry.get("fields", [])}


def diff(old: dict, new: dict) -> tuple[list[str], bool]:
    """Return (report lines, any_change)."""
    lines: list[str] = []
    changed = False

    of, nf = old.get("files", {}), new.get("files", {})

    gone = sorted(set(of) - set(nf))
    fresh = sorted(set(nf) - set(of))
    if gone:
        changed = True
        lines.append(f"Files no longer resolvable: {gone}")
    if fresh:
        changed = True
        lines.append(f"Files newly resolvable: {fresh}")
    if gone or fresh:
        lines.append("")

    for name in sorted(set(of) & set(nf)):
        o, n = _fields(of[name]), _fields(nf[name])
        added = [k for k in n if k not in o]
        removed = [k for k in o if k not in n]
        retyped = [(k, o[k]["fortran_type"], n[k]["fortran_type"])
                   for k in o if k in n
                   and o[k]["fortran_type"] != n[k]["fortran_type"]]
        moved = [(k, o[k]["position"], n[k]["position"])
                 for k in o if k in n
                 and o[k]["position"] != n[k]["position"]]

        if not (added or removed or retyped or moved):
            continue
        changed = True
        lines.append(f"{name}  ({len(o)} -> {len(n)} fields)")
        for k in added:
            lines.append(f"    + added   {k} ({n[k]['fortran_type']}) "
                         f"at position {n[k]['position']}")
        for k in removed:
            lines.append(f"    - removed {k} ({o[k]['fortran_type']}) "
                         f"was at position {o[k]['position']}")
        for k, ot, nt in retyped:
            lines.append(f"    ! type    {k}: {ot} -> {nt}")
        for k, op, np_ in moved:
            lines.append(f"    ! moved   {k}: position {op} -> {np_} "
                         f"(existing values will land in a different variable)")
        lines.append("")

    return lines, changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="from_v", required=True)
    ap.add_argument("--to", dest="to_v", required=True)
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args(argv)

    root = Path(args.repo_root)
    old, new = load(root, args.from_v), load(root, args.to_v)

    print(f"SWAT+ schema diff {args.from_v} -> {args.to_v}\n")
    lines, changed = diff(old, new)
    if not changed:
        print("No input-file format changes between these versions.")
        return 0
    print("\n".join(lines))
    print("Adopting the new version means updating FILE_SCHEMAS for each file "
          "above,\nand adding a change-log entry describing the format change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
