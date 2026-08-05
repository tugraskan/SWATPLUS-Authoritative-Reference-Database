"""Manifest integrity (spec tests 3, 8, 22, 23) against the real repository."""

from __future__ import annotations

import json

from swat_config import EXPECTED_BY_NAME


def _manifest(repo_root):
    return json.loads((repo_root / "internal" / "metadata" / "database_manifest.json").read_text())


def test_every_expected_file_in_manifest(repo_root):
    m = _manifest(repo_root)
    names = {f["name"] for f in m["files"]}
    assert names == set(EXPECTED_BY_NAME)


def test_available_entry_has_matching_file(repo_root):
    m = _manifest(repo_root)
    for f in m["files"]:
        if f["status"] in ("available", "needs_review"):
            assert (repo_root / "database_files" / f["name"]).is_file(), \
                f"{f['name']} marked {f['status']} but file missing"


def test_unavailable_entry_has_no_file(repo_root):
    m = _manifest(repo_root)
    for f in m["files"]:
        if f["status"] == "unavailable":
            assert not (repo_root / "database_files" / f["name"]).exists()


def test_official_dataset_source_recorded(repo_root):
    m = _manifest(repo_root)
    assert m["source_type"] == "swatplus_editor_official_reference_dataset"
    assert m["source_repository"] == "swat-model/swatplus-editor"
    assert m["source_dataset_version"] == "4.0.0"
    assert m["source_swatplus_revision"] == "62"


def test_no_sqlite_committed(repo_root):
    # spec test 23: no SQLite database is produced/committed
    for pat in ("*.sqlite", "*.sqlite3", "*.db"):
        assert not list(repo_root.rglob(pat))


def test_direct_read_files_present_and_flagged(repo_root):
    m = _manifest(repo_root)
    by = {f["name"]: f for f in m["files"]}
    for name in ("manure_db.frt", "manure_om.frt", "puddle.ops", "transplant.plt"):
        assert by[name]["direct_read"] is True
        assert by[name]["status"] == "available"
