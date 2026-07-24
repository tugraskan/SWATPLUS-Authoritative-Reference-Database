"""Bootstrap source-priority and safety (spec tests 1, 2, 4, 5, 6, 7, 16)."""

from __future__ import annotations

import json

import bootstrap_database_files as boot
from conftest import make_fake_checkout


def _run(checkout, repo_root, extra=None):
    argv = ["--swatplus-checkout", str(checkout), "--repo-root", str(repo_root),
            "--commit", "TESTSHA123"]
    if extra:
        argv += extra
    return boot.main(argv)


def test_ames_selected_when_both_present(tmp_path):
    checkout = make_fake_checkout(tmp_path)
    repo = tmp_path / "repo"
    (repo / "database_files").mkdir(parents=True)
    (repo / "DATABASE_VERSION").write_text("2026.1.0\n")
    assert _run(checkout, repo) == 0
    # plants.plt exists in both -> must come from Ames
    assert "from_ames" in (repo / "database_files" / "plants.plt").read_text()


def test_osu_used_when_ames_absent(tmp_path):
    # fire.ops present only in OSU
    checkout = make_fake_checkout(tmp_path, osu_only=("fire.ops",))
    repo = tmp_path / "repo"
    (repo / "database_files").mkdir(parents=True)
    (repo / "DATABASE_VERSION").write_text("2026.1.0\n")
    assert _run(checkout, repo) == 0
    prov = json.loads((repo / "metadata" / "bootstrap_sources.json").read_text())
    fire = next(f for f in prov["files"] if f["file_name"] == "fire.ops")
    assert fire["selected_source"] == "osu"


def test_manure_files_selected_from_ames(tmp_path):
    checkout = make_fake_checkout(tmp_path)
    repo = tmp_path / "repo"
    (repo / "database_files").mkdir(parents=True)
    (repo / "DATABASE_VERSION").write_text("2026.1.0\n")
    _run(checkout, repo)
    prov = json.loads((repo / "metadata" / "bootstrap_sources.json").read_text())
    by = {f["file_name"]: f for f in prov["files"]}
    assert by["manure_db.frt"]["selected_source"] == "ames"
    assert by["manure_om.frt"]["selected_source"] == "ames"


def test_exact_commit_recorded(tmp_path):
    checkout = make_fake_checkout(tmp_path)
    repo = tmp_path / "repo"
    (repo / "database_files").mkdir(parents=True)
    (repo / "DATABASE_VERSION").write_text("2026.1.0\n")
    _run(checkout, repo)
    prov = json.loads((repo / "metadata" / "bootstrap_sources.json").read_text())
    assert prov["bootstrap_swatplus_commit"] == "TESTSHA123"
    assert all(f["source_commit"] == "TESTSHA123" for f in prov["files"])


def test_required_missing_fails(tmp_path):
    checkout = make_fake_checkout(tmp_path)
    # remove a required file (plants.plt) from both sources
    for sub in ("Ames_sub1", "Osu_1hru"):
        (checkout / "refdata" / sub / "plants.plt").unlink()
    repo = tmp_path / "repo"
    (repo / "database_files").mkdir(parents=True)
    (repo / "DATABASE_VERSION").write_text("2026.1.0\n")
    assert _run(checkout, repo) == 1  # clear failure


def test_optional_missing_marked_unavailable(tmp_path):
    # scen_lu.dtl is optional and never in sources -> unavailable, no failure
    checkout = make_fake_checkout(tmp_path)
    repo = tmp_path / "repo"
    (repo / "database_files").mkdir(parents=True)
    (repo / "DATABASE_VERSION").write_text("2026.1.0\n")
    assert _run(checkout, repo) == 0
    manifest = json.loads((repo / "metadata" / "database_manifest.json").read_text())
    entry = next(f for f in manifest["files"] if f["name"] == "scen_lu.dtl")
    assert entry["status"] == "unavailable"


def test_existing_file_not_overwritten_without_flag(tmp_path):
    checkout = make_fake_checkout(tmp_path)
    repo = tmp_path / "repo"
    (repo / "database_files").mkdir(parents=True)
    (repo / "DATABASE_VERSION").write_text("2026.1.0\n")
    # pre-place a plants.plt with sentinel content
    (repo / "database_files" / "plants.plt").write_text("DO_NOT_OVERWRITE\n")
    _run(checkout, repo)  # no --overwrite-bootstrap
    assert (repo / "database_files" / "plants.plt").read_text() == "DO_NOT_OVERWRITE\n"
    # with the flag it is replaced
    _run(checkout, repo, extra=["--overwrite-bootstrap"])
    assert "from_ames" in (repo / "database_files" / "plants.plt").read_text()
