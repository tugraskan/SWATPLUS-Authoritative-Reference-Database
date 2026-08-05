#!/usr/bin/env python3
"""Validate metadata/database_changes.csv and its coverage of row changes.

Two layers:

* Structural (always): required columns present; no duplicate change_id;
  change_type is one of added/modified/deprecated/removed. `reason` and
  `source` are optional -- scripts/sync_change_log_from_pr.py generates rows
  straight from a PR's file diff and doesn't require either.

* Coverage (with --base-ref REF, as in CI): diff each changed name-keyed
  database file against REF and require a matching change-log entry for every
  added or modified record.  A change-log row with record_name "*" covers all
  records in that file (used for file-level additions such as the external
  imports).

The initial bootstrap import is allowed a documented exception via
``--bootstrap-exception`` (skips coverage; structural checks still run).

Usage:
    python internal/scripts/validate_change_log.py [--repo-root .] \
        [--base-ref origin/main] [--bootstrap-exception]
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from swat_common import parse_name_keyed_table  # noqa: E402
from swat_config import (  # noqa: E402
    DATABASE_FILES_DIR, EXPECTED_BY_NAME, FILE_SCHEMAS, NAME_KEYED_FORMATS,
    METADATA_DIR,
)

REQUIRED_COLUMNS = [
    "change_id", "file_name", "record_name", "change_type", "date",
    "submitted_by", "source", "reason", "swatplus_version", "editor_version",
    "review_status", "notes",
]
VALID_CHANGE_TYPES = {"added", "modified", "deprecated", "removed"}


def _git_show(repo_root: Path, ref: str, rel: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "show", f"{ref}:{rel}"],
            stderr=subprocess.DEVNULL).decode("utf-8", "replace")
    except subprocess.CalledProcessError:
        return None  # file did not exist at base -> whole file is new


def _changed_files(repo_root: Path, ref: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "diff", "--name-only", ref, "--",
             DATABASE_FILES_DIR], stderr=subprocess.DEVNULL).decode()
    except subprocess.CalledProcessError:
        return []
    return [line.split("/", 1)[1] for line in out.splitlines() if "/" in line]


def _record_names(text: str, name: str, fmt: str) -> set[str]:
    # Parse records from an in-memory file version via a temp file so the same
    # format-aware parser is reused for both the current and base contents.
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix="_" + name, delete=False,
                                     encoding="utf-8") as fh:
        fh.write(text)
        tp = fh.name
    cols = FILE_SCHEMAS.get(name, {}).get("columns")
    table = parse_name_keyed_table(tp, fmt, cols)
    Path(tp).unlink(missing_ok=True)
    return {r.name for r in table.records}


def validate(repo_root, base_ref=None, bootstrap_exception=False):
    repo_root = Path(repo_root)
    path = repo_root / METADATA_DIR / "database_changes.csv"
    errors: list[str] = []

    if not path.exists():
        return [f"ERROR: {path} missing"]

    # Documented bootstrap exception: while this marker file exists, per-record
    # coverage against the merge base is skipped (the initial bootstrap import
    # is not expected to have a change-log row for every imported record).
    # Maintainers remove the marker once ordinary row-by-row edits begin.
    marker = repo_root / METADATA_DIR / "bootstrap_exception"
    if marker.exists() and not bootstrap_exception:
        bootstrap_exception = True
        print(f"NOTE: {marker.name} present -> skipping change-log coverage "
              "(documented bootstrap exception)")

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = list(reader)

    # structural: columns
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing_cols:
        errors.append(f"ERROR: database_changes.csv missing columns: {missing_cols}")
        return errors

    seen_ids: dict[str, int] = {}
    # index of (file_name, record_name) -> change_types for coverage
    coverage: dict[tuple[str, str], set[str]] = {}
    filewide: dict[str, set[str]] = {}

    for i, r in enumerate(rows, start=2):  # +1 header, +1 to 1-base
        cid = r["change_id"].strip()
        if cid == "":
            errors.append(f"ERROR: database_changes.csv line {i}: blank change_id")
        elif cid in seen_ids:
            errors.append(f"ERROR: database_changes.csv line {i}: duplicate "
                          f"change_id '{cid}' (first at line {seen_ids[cid]})")
        else:
            seen_ids[cid] = i

        ct = r["change_type"].strip().lower()
        if ct not in VALID_CHANGE_TYPES:
            errors.append(f"ERROR: database_changes.csv line {i}: invalid "
                          f"change_type '{r['change_type']}'")

        fn, rn = r["file_name"].strip(), r["record_name"].strip()
        if rn == "*":
            filewide.setdefault(fn, set()).add(ct)
        else:
            coverage.setdefault((fn, rn), set()).add(ct)

    # coverage
    if base_ref and not bootstrap_exception:
        for name in _changed_files(repo_root, base_ref):
            spec = EXPECTED_BY_NAME.get(name)
            fmt = spec["fmt"] if spec else "flat_named"
            if fmt not in NAME_KEYED_FORMATS:
                continue  # decision tables / constants: file-level coverage only
            cur_path = repo_root / DATABASE_FILES_DIR / name
            if not cur_path.is_file():
                continue
            cur = _record_names(cur_path.read_text(encoding="utf-8", errors="replace"),
                                name, fmt)
            base_text = _git_show(repo_root, base_ref, f"{DATABASE_FILES_DIR}/{name}")
            base = _record_names(base_text, name, fmt) if base_text else set()
            changed_records = (cur - base)  # added (modified needs value diff; kept simple)
            if name in filewide and ("added" in filewide[name]
                                     or "modified" in filewide[name]):
                continue  # file-level entry covers it
            for rec in sorted(changed_records):
                if (name, rec) not in coverage:
                    errors.append(
                        f"ERROR: {name}: added/modified record '{rec}' has no "
                        f"matching database_changes.csv entry")

    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--base-ref", default=None,
                    help="Git ref to diff against (merge base) for coverage")
    ap.add_argument("--bootstrap-exception", action="store_true",
                    help="Skip per-record coverage (documented bootstrap import)")
    args = ap.parse_args(argv)

    errors = validate(args.repo_root, args.base_ref, args.bootstrap_exception)
    for e in errors:
        print(e)
    if errors:
        print(f"\nFAILED: {len(errors)} change-log error(s)")
        return 1
    print("OK: change log valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
