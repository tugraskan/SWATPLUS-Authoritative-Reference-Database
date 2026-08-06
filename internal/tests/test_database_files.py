"""File-level validation rules (spec tests 14, 15, 23) + real-repo integration."""

from __future__ import annotations

import json

import validate_database_files as vdb
from swat_config import METADATA_DIR


def _min_repo(tmp_path, manifest_files, db_files=None):
    (tmp_path / "database_files").mkdir()
    (tmp_path / METADATA_DIR).mkdir(parents=True)
    (tmp_path / "DATABASE_VERSION").write_text("2026.1.0\n")
    manifest = {
        "database_version": "2026.2.0", "repository": "x",
        "manifest_schema_version": 1,
        "source_type": "swatplus_editor_official_reference_dataset",
        "source_repository": "swat-model/swatplus-editor",
        "files": manifest_files,
    }
    (tmp_path / METADATA_DIR / "database_manifest.json").write_text(json.dumps(manifest))
    for name, content in (db_files or {}).items():
        (tmp_path / "database_files" / name).write_text(content)
    return tmp_path


def test_burn_ops_rejected(tmp_path):
    _min_repo(tmp_path, [], {"burn.ops": "burn.ops: x\nname\nx\n"})
    P = vdb.validate(tmp_path)
    assert any("use fire.ops, not burn.ops" in e for e in P.errors)


def test_pesticide_pst_rejected(tmp_path):
    _min_repo(tmp_path, [], {"pesticide.pst": "pesticide.pst: x\nname\nx\n"})
    P = vdb.validate(tmp_path)
    assert any("pesticide.pes" in e for e in P.errors)


def test_sqlite_rejected(tmp_path):
    _min_repo(tmp_path, [], {"swatplus_datasets.sqlite": "binary"})
    P = vdb.validate(tmp_path)
    assert any("SQLite" in e for e in P.errors)


def test_available_but_missing_file_flagged(tmp_path):
    entry = dict(name="plants.plt", category="hru_parameter_database",
                 status="available", required=True, canonical_record_key="name",
                 source_format="SWAT+ text database", direct_read=False,
                 bootstrap_provenance_key="plants.plt",
                 external_provenance_key=None, notes="")
    _min_repo(tmp_path, [entry])  # file not created
    P = vdb.validate(tmp_path)
    assert any("plants.plt" in e and "missing" in e for e in P.errors)


def test_real_repo_validates_clean(repo_root):
    # verify_bootstrap_checksums is deliberately False here, matching what CI
    # actually runs. bootstrap_sources.json records each file's checksum at the
    # moment it was imported, and CONTRIBUTING.md is explicit that provenance is
    # never rewritten when a file is later edited -- so once any bootstrapped
    # file receives a legitimate post-bootstrap edit (e.g. pesticide.pes gaining
    # pl_uptake), its current checksum will diverge from that recorded value by
    # design. That divergence is what git history is for;
    # --verify-bootstrap-checksums is a tool for checking a fresh bootstrap
    # import immediately after it runs, not an ongoing invariant of the repo.
    P = vdb.validate(repo_root, verify_bootstrap_checksums=False)
    assert P.errors == [], "unexpected errors:\n" + "\n".join(P.errors)
