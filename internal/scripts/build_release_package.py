#!/usr/bin/env python3
"""Build a versioned text-file release package.

Produces a ``dist/`` staging tree and a deterministic ZIP:

    dist/
      database_files/
      database_manifest.json
      database_changes.csv
      bootstrap_sources.json
      compatibility_matrix.csv
      external_sources.json
      DATABASE_VERSION
      checksums.txt
    swatplus-authoritative-reference-database-<version>.zip

The package contains only authoritative text data and supporting metadata; it
never contains a SQLite database, SWAT+ Editor source, model binaries, or
project output files.  The build first runs validation and refuses to package
an invalid repository (no unvalidated releases).  The ZIP is built
deterministically (fixed timestamps, sorted entries) so rebuilding from the
same commit yields identical bytes and checksums.

Usage:
    python internal/scripts/build_release_package.py [--repo-root .] [--output-dir dist] \
        [--version X.Y.Z] [--skip-validation]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_database_files as vdb  # noqa: E402
from swat_common import sha256_file  # noqa: E402
from swat_config import (  # noqa: E402
    DATABASE_FILES_DIR, DATABASE_VERSION_FILE, METADATA_DIR,
)

METADATA_FILES = [
    "database_manifest.json",
    "database_changes.csv",
    "bootstrap_sources.json",
    "compatibility_matrix.csv",
    "external_sources.json",
    # Ships with the package on purpose: it records where the data is known to
    # differ from what SWAT+ reads (see schema_sync.py), which a consumer of a
    # release needs in order to judge whether a file is safe to use as-is.
    "schema_drift_waivers.json",
]
FIXED_DATE = (1980, 1, 1, 0, 0, 0)  # deterministic ZIP timestamps


def build(repo_root, output_dir="dist", version=None, skip_validation=False):
    repo_root = Path(repo_root).resolve()
    dist = repo_root / output_dir

    if not skip_validation:
        P = vdb.validate(repo_root, verify_bootstrap_checksums=False)
        if P.errors:
            for e in P.errors:
                print(e)
            raise SystemExit("Refusing to build release: validation failed")

    version = version or (repo_root / DATABASE_VERSION_FILE).read_text().strip()

    if dist.exists():
        shutil.rmtree(dist)
    (dist / DATABASE_FILES_DIR).mkdir(parents=True)

    # copy database files
    for f in sorted((repo_root / DATABASE_FILES_DIR).iterdir()):
        if f.is_file():
            shutil.copyfile(f, dist / DATABASE_FILES_DIR / f.name)

    # copy metadata + version
    for meta in METADATA_FILES:
        src = repo_root / METADATA_DIR / meta
        if src.exists():
            shutil.copyfile(src, dist / meta)
    shutil.copyfile(repo_root / DATABASE_VERSION_FILE, dist / "DATABASE_VERSION")

    # checksums over every packaged file (except checksums.txt itself)
    checks = []
    for p in sorted(dist.rglob("*")):
        if p.is_file():
            rel = p.relative_to(dist).as_posix()
            checks.append(f"{sha256_file(p)}  {rel}")
    (dist / "checksums.txt").write_text("\n".join(checks) + "\n", encoding="utf-8")

    # guard: nothing forbidden slipped in
    forbidden = [p for p in dist.rglob("*")
                 if p.suffix.lower() in (".sqlite", ".sqlite3", ".db", ".exe")]
    if forbidden:
        raise SystemExit(f"Forbidden artifacts in package: {forbidden}")

    zip_path = repo_root / \
        f"swatplus-authoritative-reference-database-{version}.zip"
    _deterministic_zip(dist, zip_path)

    return zip_path, dist


def _deterministic_zip(dist: Path, zip_path: Path) -> None:
    files = sorted(p for p in dist.rglob("*") if p.is_file())
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            # in-zip path is independent of the staging dir name (reproducible)
            arc = p.relative_to(dist)
            zi = zipfile.ZipInfo(arc.as_posix(), date_time=FIXED_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, p.read_bytes())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--output-dir", default="dist")
    ap.add_argument("--version", default=None)
    ap.add_argument("--skip-validation", action="store_true")
    args = ap.parse_args(argv)

    zip_path, dist = build(args.repo_root, args.output_dir, args.version,
                           args.skip_validation)
    n = sum(1 for _ in (dist / DATABASE_FILES_DIR).iterdir())
    print(f"Built {zip_path.name}")
    print(f"  {n} database files + {len(METADATA_FILES)} metadata files + "
          f"DATABASE_VERSION + checksums.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
