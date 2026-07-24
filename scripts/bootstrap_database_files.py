#!/usr/bin/env python3
"""Bootstrap authoritative files from a pinned SWAT+ checkout.

Ames first, OSU only when Ames lacks the file.  Contents are copied byte-for-
byte; headers are parsed for provenance (never guessed); SHA-256 checksums are
recorded.  This script writes:

    database_files/<file>            (exact copies)
    metadata/bootstrap_sources.json  (per-file provenance)
    metadata/database_manifest.json  (derived; via manifest_builder)
    docs/bootstrap_report.md

It refuses to overwrite an existing authoritative file unless
``--overwrite-bootstrap`` is given, and it never runs during validation or
release builds.

Externally supplied files (pathogens.pth, metals.mtl, salt.slt, flo_con.dtl)
are NOT handled here -- they are imported by import_external_files.py so that
bootstrap provenance stays pure Ames/OSU.

Usage:
    python scripts/bootstrap_database_files.py \
        --swatplus-checkout /path/to/swat-model/swatplus \
        [--commit <sha>] [--repo-root .] [--overwrite-bootstrap]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from manifest_builder import write_manifest  # noqa: E402
from swat_common import parse_header, sha256_file  # noqa: E402
from swat_config import (  # noqa: E402
    BOOTSTRAP_SOURCE_PRIORITY,
    BOOTSTRAP_SWATPLUS_BRANCH,
    BOOTSTRAP_SWATPLUS_COMMIT,
    BOOTSTRAP_SWATPLUS_REPOSITORY,
    DATABASE_FILES_DIR,
    EXPECTED_FILES,
    METADATA_DIR,
)

REFDATA = "refdata"


def resolve_commit(checkout: Path, override: str | None) -> str:
    if override:
        return override
    try:
        out = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return BOOTSTRAP_SWATPLUS_COMMIT


def find_source(checkout: Path, name: str) -> tuple[str, Path] | tuple[None, None]:
    """Return (selected_source, path) using Ames-first priority."""
    for src in BOOTSTRAP_SOURCE_PRIORITY:
        candidate = checkout / REFDATA / src / name
        if candidate.is_file():
            return src, candidate
    return None, None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--swatplus-checkout", required=True,
                    help="Local checkout of swat-model/swatplus")
    ap.add_argument("--commit", default=None,
                    help="Exact SWAT+ commit (resolved from checkout if omitted)")
    ap.add_argument("--repo-root", default=".",
                    help="Authoritative repository root (default: cwd)")
    ap.add_argument("--overwrite-bootstrap", action="store_true",
                    help="Allow overwriting existing authoritative files")
    args = ap.parse_args(argv)

    checkout = Path(args.swatplus_checkout).resolve()
    repo_root = Path(args.repo_root).resolve()
    if not (checkout / REFDATA).is_dir():
        print(f"ERROR: {checkout}/{REFDATA} not found; is this a SWAT+ checkout?",
              file=sys.stderr)
        return 2

    commit = resolve_commit(checkout, args.commit)
    if commit != BOOTSTRAP_SWATPLUS_COMMIT and args.commit is None:
        print(f"WARNING: checkout HEAD {commit} != pinned "
              f"{BOOTSTRAP_SWATPLUS_COMMIT}", file=sys.stderr)

    db_dir = repo_root / DATABASE_FILES_DIR
    db_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / METADATA_DIR).mkdir(parents=True, exist_ok=True)
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)

    today = _dt.date.today().isoformat()
    provenance = []
    report_rows = []
    failures = []

    for spec in EXPECTED_FILES:
        name = spec["name"]
        if spec["origin"] != "bootstrap":
            # external / unavailable_expected -> not bootstrapped here
            report_rows.append((name, "skipped (not a bootstrap source)"))
            continue

        selected, src_path = find_source(checkout, name)
        if selected is None:
            report_rows.append((name, "unavailable"))
            if spec["required"]:
                failures.append(name)
            continue

        dest = db_dir / name
        if dest.exists() and not args.overwrite_bootstrap:
            print(f"REFUSING to overwrite existing {dest} "
                  f"(use --overwrite-bootstrap)", file=sys.stderr)
            report_rows.append((name, f"exists; not overwritten (from {selected})"))
            # still record provenance from existing file below
            src_for_provenance = dest
            source_path_rel = f"{REFDATA}/{selected}/{name}"
        else:
            shutil.copyfile(src_path, dest)  # exact byte copy
            src_for_provenance = dest
            source_path_rel = f"{REFDATA}/{selected}/{name}"
            report_rows.append((name, f"<- {source_path_rel}"))

        header_line = _read_first_line(src_for_provenance)
        hinfo = parse_header(header_line)
        provenance.append({
            "file_name": name,
            "selected_source": "ames" if selected == "Ames_sub1" else "osu",
            "source_repository": BOOTSTRAP_SWATPLUS_REPOSITORY,
            "source_path": source_path_rel,
            "source_branch": BOOTSTRAP_SWATPLUS_BRANCH,
            "source_commit": commit,
            "source_file_header": hinfo.header_line,
            "source_editor_version": hinfo.editor_version,
            "source_swatplus_revision": hinfo.swatplus_revision,
            "bootstrap_date": today,
            "content_sha256": sha256_file(dest),
            "direct_read": spec["direct_read"],
            "notes": "Initial authoritative import"
            + (" (direct-read database)" if spec["direct_read"] else ""),
        })

    # write provenance
    prov_doc = {
        "bootstrap_swatplus_repository": BOOTSTRAP_SWATPLUS_REPOSITORY,
        "bootstrap_swatplus_branch": BOOTSTRAP_SWATPLUS_BRANCH,
        "bootstrap_swatplus_commit": commit,
        "bootstrap_source_priority": BOOTSTRAP_SOURCE_PRIORITY,
        "files": provenance,
    }
    (repo_root / METADATA_DIR / "bootstrap_sources.json").write_text(
        json.dumps(prov_doc, indent=2) + "\n", encoding="utf-8")

    # regenerate manifest (derived)
    write_manifest(repo_root)

    # bootstrap report
    _write_report(repo_root, commit, report_rows, provenance, failures)

    print(f"Bootstrap complete: {len(provenance)} files imported from "
          f"{BOOTSTRAP_SWATPLUS_REPOSITORY}@{commit[:10]}")
    for name, msg in report_rows:
        print(f"  {name:18} {msg}")

    if failures:
        print(f"\nERROR: required file(s) unavailable: {', '.join(failures)}",
              file=sys.stderr)
        return 1
    return 0


def _read_first_line(path: Path) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.readline().rstrip("\n")


def _write_report(repo_root, commit, report_rows, provenance, failures):
    lines = ["# Bootstrap Report", "",
             f"Source: `{BOOTSTRAP_SWATPLUS_REPOSITORY}` @ `{commit}`  ",
             f"Priority: {' -> '.join(BOOTSTRAP_SOURCE_PRIORITY)}", "",
             "## Source selection", "",
             "| File | Result |", "|---|---|"]
    for name, msg in report_rows:
        lines.append(f"| `{name}` | {msg} |")
    lines += ["", "## Parsed provenance", "",
              "| File | Source | Editor version | SWAT+ rev | SHA-256 |",
              "|---|---|---|---|---|"]
    for p in provenance:
        lines.append(
            f"| `{p['file_name']}` | {p['selected_source']} | "
            f"{p['source_editor_version'] or 'null'} | "
            f"{p['source_swatplus_revision'] or 'null'} | "
            f"`{p['content_sha256'][:12]}…` |")
    if failures:
        lines += ["", "## Required files unavailable", ""]
        lines += [f"- `{f}`" for f in failures]
    lines.append("")
    (repo_root / "docs" / "bootstrap_report.md").write_text(
        "\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
