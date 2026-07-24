#!/usr/bin/env python3
"""Import externally supplied reference files (Option C).

Four expected files have no approved Ames/OSU bootstrap source but were supplied
by the maintainer from outside those sources:

    pathogens.pth, metals.mtl, salt.slt, flo_con.dtl

To keep bootstrap provenance pure, these are imported here (not by
bootstrap_database_files.py) and their provenance is recorded in a *separate*
file, metadata/external_sources.json.  A change-log row is seeded for each.

Files whose configured status is ``needs_review`` (example/seed grade) are
imported but flagged for curation in the manifest.

Usage:
    python scripts/import_external_files.py --source-dir <dir> [--repo-root .]

``--source-dir`` may contain the files under their exact name or under an
upload-prefixed name (e.g. ``34dd83b8-metals.mtl``); both are matched.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from manifest_builder import write_manifest  # noqa: E402
from swat_common import sha256_file  # noqa: E402
from swat_config import (  # noqa: E402
    DATABASE_FILES_DIR,
    EXTERNAL_FILES,
    METADATA_DIR,
)

CHANGES_HEADER = [
    "change_id", "file_name", "record_name", "change_type", "date",
    "submitted_by", "source", "reason", "swatplus_version", "editor_version",
    "review_status", "notes",
]


def locate(source_dir: Path, name: str) -> Path | None:
    exact = source_dir / name
    if exact.is_file():
        return exact
    matches = [p for p in source_dir.iterdir()
               if p.is_file() and (p.name == name or p.name.endswith("-" + name)
                                   or p.name.endswith(name))]
    return matches[0] if matches else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", required=True,
                    help="Directory containing the supplied external files")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--overwrite", action="store_true",
                    help="Allow overwriting existing authoritative files")
    ap.add_argument("--submitted-by", default="maintainer")
    args = ap.parse_args(argv)

    source_dir = Path(args.source_dir).resolve()
    repo_root = Path(args.repo_root).resolve()
    db_dir = repo_root / DATABASE_FILES_DIR
    db_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / METADATA_DIR).mkdir(parents=True, exist_ok=True)

    today = _dt.date.today().isoformat()
    records = []
    missing = []

    for cfg in EXTERNAL_FILES:
        name = cfg["name"]
        src = locate(source_dir, name)
        if src is None:
            missing.append(name)
            continue
        dest = db_dir / name
        if dest.exists() and not args.overwrite:
            print(f"REFUSING to overwrite existing {dest} (use --overwrite)",
                  file=sys.stderr)
        else:
            shutil.copyfile(src, dest)  # exact byte copy
        records.append({
            "file_name": name,
            "selected_source": "external",
            "origin_type": cfg["origin_type"],
            "source_repository": cfg["source_repository"],
            "source_location": cfg["source_location"],
            "source_ref": cfg["source_ref"],
            "reproducible": cfg["reproducible"],
            "status": cfg["status"],
            "import_date": today,
            "content_sha256": sha256_file(dest),
            "notes": cfg["notes"],
        })
        print(f"  {name:16} <- external:{cfg['origin_type']} "
              f"({'reproducible' if cfg['reproducible'] else 'non-reproducible'})")

    if missing:
        print(f"ERROR: external file(s) not found in {source_dir}: "
              f"{', '.join(missing)}", file=sys.stderr)
        return 1

    ext_doc = {
        "description": "Files supplied from outside the approved Ames/OSU "
                       "bootstrap sources. Kept separate from bootstrap "
                       "provenance. See CONTRIBUTING.md / README.md.",
        "files": records,
    }
    (repo_root / METADATA_DIR / "external_sources.json").write_text(
        json.dumps(ext_doc, indent=2) + "\n", encoding="utf-8")

    _seed_change_log(repo_root, records, today, args.submitted_by)
    write_manifest(repo_root)

    print(f"Imported {len(records)} external files; wrote external_sources.json")
    return 0


def _seed_change_log(repo_root: Path, records, today: str, who: str) -> None:
    """Add one file-level 'added' change-log row per external file (idempotent)."""
    path = repo_root / METADATA_DIR / "database_changes.csv"
    existing_ids = set()
    rows = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for r in reader:
                rows.append(r)
                existing_ids.add(r["change_id"])

    for rec in records:
        cid = f"ext-{rec['file_name']}"
        if cid in existing_ids:
            continue
        rows.append({
            "change_id": cid,
            "file_name": rec["file_name"],
            "record_name": "*",  # file-level addition
            "change_type": "added",
            "date": today,
            "submitted_by": who,
            "source": rec["source_repository"] or rec["source_location"],
            "reason": "Added expected file from external source "
                      "(no approved Ames/OSU bootstrap source available)",
            "swatplus_version": "not_applicable",
            "editor_version": "not_applicable",
            "review_status": "needs_review" if rec["status"] == "needs_review"
                             else "imported",
            "notes": rec["notes"],
        })

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CHANGES_HEADER)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


if __name__ == "__main__":
    raise SystemExit(main())
