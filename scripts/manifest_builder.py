"""Derive metadata/database_manifest.json from the repository's current state.

The manifest is a *derived* artifact: it is rebuilt from
``database_files/`` plus the two provenance files.  Keeping it derived (rather
than hand-edited) means the bootstrap script and the external-import script can
each regenerate it and always agree.

A file is only ever marked ``available`` when it physically exists in
``database_files/`` (spec: "A file must not be marked available unless it
exists in database_files/").
"""

from __future__ import annotations

import json
from pathlib import Path

from swat_config import (
    BOOTSTRAP_SOURCE_PRIORITY,
    BOOTSTRAP_SWATPLUS_COMMIT,
    BOOTSTRAP_SWATPLUS_REPOSITORY,
    DATABASE_FILES_DIR,
    EXPECTED_FILES,
    EXTERNAL_BY_NAME,
    METADATA_DIR,
)

MANIFEST_SCHEMA_VERSION = 1
REPOSITORY = "tugraskan/SWATPLUS-Authoritative-Reference-Database"
COMPATIBILITY_MATRIX = "metadata/compatibility_matrix.csv"


def _load_json(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def build_manifest(repo_root: str | Path) -> dict:
    repo_root = Path(repo_root)
    db_dir = repo_root / DATABASE_FILES_DIR
    meta_dir = repo_root / METADATA_DIR

    version = (repo_root / "DATABASE_VERSION").read_text(encoding="utf-8").strip()

    bootstrap = _load_json(meta_dir / "bootstrap_sources.json") or {"files": []}
    external = _load_json(meta_dir / "external_sources.json") or {"files": []}
    bootstrap_names = {e["file_name"] for e in bootstrap.get("files", [])}
    external_names = {e["file_name"] for e in external.get("files", [])}

    files = []
    for spec in EXPECTED_FILES:
        name = spec["name"]
        exists = (db_dir / name).is_file()

        if exists:
            ext_cfg = EXTERNAL_BY_NAME.get(name)
            if ext_cfg and ext_cfg.get("status") == "needs_review":
                status = "needs_review"
            else:
                status = "available"
        else:
            status = "unavailable"

        entry = {
            "name": name,
            "category": spec["category"],
            "status": status,
            "required": spec["required"],
            "canonical_record_key": spec["record_key"],
            "source_format": "SWAT+ text database",
            "direct_read": spec["direct_read"],
            "bootstrap_provenance_key": name if name in bootstrap_names else None,
            "external_provenance_key": name if name in external_names else None,
            "notes": _note_for(spec, status),
        }
        files.append(entry)

    return {
        "database_version": version,
        "repository": REPOSITORY,
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "bootstrap_swatplus_repository": BOOTSTRAP_SWATPLUS_REPOSITORY,
        "bootstrap_swatplus_commit": BOOTSTRAP_SWATPLUS_COMMIT,
        "bootstrap_source_priority": BOOTSTRAP_SOURCE_PRIORITY,
        "compatibility_matrix": COMPATIBILITY_MATRIX,
        "files": files,
    }


def _note_for(spec: dict, status: str) -> str:
    origin = spec["origin"]
    if origin == "external":
        base = "Supplied from outside the approved Ames/OSU sources; see external_sources.json"
    elif origin == "unavailable_expected":
        base = "Expected file with no approved bootstrap source found"
    else:
        base = "Imported during initial bootstrap; see bootstrap_sources.json"
    if spec["direct_read"]:
        base += " (direct-read database: hard-coded filename in SWAT+ source)"
    if status == "needs_review":
        base += " [example/seed values pending curation]"
    return base


def write_manifest(repo_root: str | Path) -> dict:
    manifest = build_manifest(repo_root)
    out = Path(repo_root) / METADATA_DIR / "database_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    m = write_manifest(root)
    print(f"Wrote manifest with {len(m['files'])} file entries")
