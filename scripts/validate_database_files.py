#!/usr/bin/env python3
"""Validate the authoritative reference database (self-contained).

Runs entirely within this repository; it never requires SWAT+ or SWAT+ Editor.
Validation errors report: filename, record name, line number, reason, e.g.

    ERROR: fire.ops, line 8, record tree_low: duplicate record name

Checks (spec section 21):
  1  every available file exists
  2  unavailable files do not fail
  3  files are not empty
  4  no unresolved git merge markers
  5  headers can be read
  6  required record names are not blank
  7  record names are unique within a name-keyed file
  8  field counts match where a schema is defined
  9  numeric fields are numeric where a schema defines them
  10 filename case matches the manifest
  11 fire.ops present (burn.ops rejected)
  12 canonical pesticide filename (pesticide.pes) enforced
  13 bootstrap checksums match (with --verify-bootstrap-checksums)
  14 manure_db.frt org_min references resolve to manure_om.frt
  15 available manure files are non-empty
  16 no SQLite database committed as an authoritative source
  17 manifest and provenance records agree

Usage:
    python scripts/validate_database_files.py [--repo-root .] \
        [--verify-bootstrap-checksums]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from swat_common import (  # noqa: E402
    find_merge_markers, is_number, parse_decision_file,
    parse_name_keyed_table, sha256_file,
)
from swat_config import (  # noqa: E402
    DATABASE_FILES_DIR, EXPECTED_BY_NAME, FILE_SCHEMAS, FMT_CONSTANTS,
    FMT_DECISION, MANURE_DB_FILE, MANURE_DB_ORGMIN_COLUMN, MANURE_OM_FILE,
    METADATA_DIR, NAME_KEYED_FORMATS,
)


class Problems:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, filename, reason, record=None, line=None):
        loc = f"{filename}"
        if line is not None:
            loc += f", line {line}"
        if record is not None:
            loc += f", record {record}"
        self.errors.append(f"ERROR: {loc}: {reason}")

    def warn(self, filename, reason):
        self.warnings.append(f"WARNING: {filename}: {reason}")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def validate(repo_root: str | Path, verify_bootstrap_checksums=False) -> Problems:
    repo_root = Path(repo_root)
    db_dir = repo_root / DATABASE_FILES_DIR
    meta = repo_root / METADATA_DIR
    P = Problems()

    manifest = _load(meta / "database_manifest.json")
    if manifest is None:
        P.err("database_manifest.json", "manifest missing")
        return P
    bootstrap = _load(meta / "bootstrap_sources.json") or {"files": []}
    external = _load(meta / "external_sources.json") or {"files": []}

    manifest_files = {f["name"]: f for f in manifest["files"]}

    # (16) no committed SQLite as authoritative source
    for p in db_dir.glob("*"):
        if p.suffix.lower() in (".sqlite", ".sqlite3", ".db"):
            P.err(p.name, "SQLite database must not be committed as an "
                          "authoritative source")

    # (11) burn.ops rejected / fire.ops required
    if (db_dir / "burn.ops").exists():
        P.err("burn.ops", "use fire.ops, not burn.ops")
    fire = manifest_files.get("fire.ops")
    if fire and fire["status"] in ("available", "needs_review") \
            and not (db_dir / "fire.ops").exists():
        P.err("fire.ops", "fire.ops marked available but missing")

    # (12) canonical pesticide filename
    if (db_dir / "pesticide.pst").exists():
        P.err("pesticide.pst", "canonical text filename is pesticide.pes")

    # per-file checks
    for name, entry in manifest_files.items():
        status = entry["status"]
        path = db_dir / name

        # (1)(2) availability
        if status in ("available", "needs_review"):
            if not path.is_file():
                P.err(name, f"marked {status} but file is missing")
                continue
        else:
            # unavailable/excluded/deprecated -> absence is fine
            if not path.is_file():
                continue

        # (10) exact filename case
        actual = {p.name for p in db_dir.iterdir()}
        if name not in actual:
            # case-only mismatch?
            lowmap = {n.lower(): n for n in actual}
            if name.lower() in lowmap:
                P.err(name, f"filename case mismatch: found {lowmap[name.lower()]}")
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        # (3) non-empty
        if text.strip() == "":
            P.err(name, "file is empty")
            continue
        # (4) merge markers
        for ln in find_merge_markers(text):
            P.err(name, "unresolved git merge marker", line=ln)

        spec = EXPECTED_BY_NAME.get(name)
        fmt = spec["fmt"] if spec else "flat_named"

        if fmt == FMT_DECISION:
            _check_decision(P, name, path)
        elif fmt == FMT_CONSTANTS:
            _check_constants(P, name, text)
        elif fmt in NAME_KEYED_FORMATS:
            _check_name_keyed(P, name, path, fmt)

    # (14)(15) manure cross-reference
    _check_manure(P, db_dir, manifest_files)

    # (17) manifest and provenance agree
    _check_provenance_agreement(P, manifest_files, bootstrap, external, db_dir)

    # (13) bootstrap checksums
    if verify_bootstrap_checksums:
        for e in bootstrap.get("files", []):
            fp = db_dir / e["file_name"]
            if fp.is_file():
                cur = sha256_file(fp)
                if cur != e["content_sha256"]:
                    P.err(e["file_name"],
                          f"bootstrap checksum mismatch "
                          f"(recorded {e['content_sha256'][:12]}…, "
                          f"current {cur[:12]}…)")

    return P


def _check_name_keyed(P: Problems, name: str, path: Path, fmt: str) -> None:
    schema = FILE_SCHEMAS.get(name)
    cols = schema["columns"] if schema else None
    table = parse_name_keyed_table(path, fmt, cols)

    # (5) header readable -> parse_name_keyed_table already read line 0
    seen: dict[str, int] = {}
    for rec in table.records:
        # (6) blank record name (an empty or 'null' key is effectively unnamed)
        if rec.name.strip() == "" or rec.name.strip().lower() == "null":
            P.err(name, "blank or 'null' record name", line=rec.line_no)
            continue
        # (7) duplicate record name
        if rec.name in seen:
            P.err(name, "duplicate record name", record=rec.name, line=rec.line_no)
        else:
            seen[rec.name] = rec.line_no

        if schema:
            # (8) field count. A free-text trailing column (text_tail) may
            # contain spaces, so require at least len(cols) tokens in that case
            # rather than an exact match.
            text_tail = schema.get("text_tail", False)
            n_fields = len(rec.fields)
            bad_count = (n_fields < len(cols)) if text_tail else (n_fields != len(cols))
            if bad_count:
                rel = "at least " if text_tail else ""
                P.err(name,
                      f"expected {rel}{len(cols)} fields, found {n_fields}",
                      record=rec.name, line=rec.line_no)
                continue
            # (9) numeric fields
            for idx in schema["numeric"]:
                if idx < len(rec.fields) and not is_number(rec.fields[idx]):
                    P.err(name,
                          f"non-numeric value '{rec.fields[idx]}' in column "
                          f"'{cols[idx]}'", record=rec.name, line=rec.line_no)

    if not table.records:
        P.warn(name, "no data records parsed")

    # count-prefixed: declared count vs actual
    if table.count_declared is not None \
            and table.count_declared != len(table.records):
        P.warn(name, f"declared record count {table.count_declared} != "
                     f"{len(table.records)} parsed records")


def _check_decision(P: Problems, name: str, path: Path) -> None:
    parsed = parse_decision_file(path)
    seen: dict[str, int] = {}
    for t in parsed.tables:
        if t.name.strip() == "":
            P.err(name, "blank decision-table name", line=t.name_line_no)
        if t.name in seen:
            P.err(name, "duplicate decision-table name",
                  record=t.name, line=t.name_line_no)
        else:
            seen[t.name] = t.name_line_no
        for label, val in (("conds", t.conds), ("alts", t.alts), ("acts", t.acts)):
            if val < 0:
                P.err(name, f"negative {label} count ({val})",
                      record=t.name, line=t.name_line_no)
    if not parsed.tables:
        P.warn(name, "no decision tables parsed")
    if parsed.declared_count is not None \
            and parsed.declared_count != len(parsed.tables):
        P.warn(name, f"declared table count {parsed.declared_count} != "
                     f"{len(parsed.tables)} parsed tables")


def _check_constants(P: Problems, name: str, text: str) -> None:
    # Light structural check: must have a title line and at least one data line.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        P.err(name, "constants file has too few lines")


def _check_manure(P: Problems, db_dir: Path, manifest_files: dict) -> None:
    db_path = db_dir / MANURE_DB_FILE
    om_path = db_dir / MANURE_OM_FILE
    db_entry = manifest_files.get(MANURE_DB_FILE)
    om_entry = manifest_files.get(MANURE_OM_FILE)

    # (15) available manure files non-empty
    for entry, p in ((db_entry, db_path), (om_entry, om_path)):
        if entry and entry["status"] in ("available", "needs_review"):
            if not p.is_file() or p.read_text(errors="replace").strip() == "":
                P.err(p.name, "manure file is required/available but empty or missing")

    if not (db_path.is_file() and om_path.is_file()):
        return

    om_table = parse_name_keyed_table(om_path, "flat_named",
                                      FILE_SCHEMAS[MANURE_OM_FILE]["columns"])
    om_names = {r.name for r in om_table.records}

    db_table = parse_name_keyed_table(db_path, "flat_named",
                                      FILE_SCHEMAS[MANURE_DB_FILE]["columns"])
    cols = FILE_SCHEMAS[MANURE_DB_FILE]["columns"]
    om_idx = cols.index(MANURE_DB_ORGMIN_COLUMN)
    # (14) each org_min reference resolves
    for rec in db_table.records:
        if om_idx < len(rec.fields):
            ref = rec.fields[om_idx]
            if ref.lower() != "null" and ref not in om_names:
                P.err(MANURE_DB_FILE,
                      f"org_min reference '{ref}' not found in {MANURE_OM_FILE}",
                      record=rec.name, line=rec.line_no)


def _check_provenance_agreement(P, manifest_files, bootstrap, external, db_dir):
    boot_names = {e["file_name"] for e in bootstrap.get("files", [])}
    ext_names = {e["file_name"] for e in external.get("files", [])}
    for name, entry in manifest_files.items():
        if entry["status"] not in ("available", "needs_review"):
            continue
        bpk = entry.get("bootstrap_provenance_key")
        epk = entry.get("external_provenance_key")
        if bpk is None and epk is None:
            P.err(name, "available file has no provenance record "
                        "(neither bootstrap nor external)")
        if bpk and name not in boot_names:
            P.err(name, "manifest cites bootstrap provenance but none recorded")
        if epk and name not in ext_names:
            P.err(name, "manifest cites external provenance but none recorded")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--verify-bootstrap-checksums", action="store_true")
    args = ap.parse_args(argv)

    P = validate(args.repo_root, args.verify_bootstrap_checksums)
    for w in P.warnings:
        print(w)
    for e in P.errors:
        print(e)
    if P.errors:
        print(f"\nFAILED: {len(P.errors)} error(s), {len(P.warnings)} warning(s)")
        return 1
    print(f"OK: validation passed ({len(P.warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
