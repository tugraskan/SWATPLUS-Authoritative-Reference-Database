"""Manure cross-reference validation (spec tests 16, 17, 18)."""

from __future__ import annotations

import json

import validate_database_files as vdb

OM = ("manure_om.frt: manure organic matter database\n"
      "name  frac_water  fcbn  fminn  fminp  forgn  forgp  fnh3n  description\n"
      "mw_bf_lq  0.99  0.1  0.01  0.01  0.02  0.01  0.9  Midwest_Beef_Liquid\n")
DB_OK = ("manure_db.frt: manure database\n"
         "name  org_min  pests  paths  hmets  salts  constit  description\n"
         "mw_bf_lq  mw_bf_lq  null  null  null  null  null  Beef\n")
DB_BAD = ("manure_db.frt: manure database\n"
          "name  org_min  pests  paths  hmets  salts  constit  description\n"
          "mw_bf_lq  DOES_NOT_EXIST  null  null  null  null  null  Beef\n")


def _repo(tmp_path, db, om):
    (tmp_path / "database_files").mkdir()
    (tmp_path / "database_files" / "manure_db.frt").write_text(db)
    (tmp_path / "database_files" / "manure_om.frt").write_text(om)
    mf = {
        "manure_db.frt": dict(name="manure_db.frt", status="available"),
        "manure_om.frt": dict(name="manure_om.frt", status="available"),
    }
    return mf


def test_valid_orgmin_reference_resolves(tmp_path):
    mf = _repo(tmp_path, DB_OK, OM)
    P = vdb.Problems()
    vdb._check_manure(P, tmp_path / "database_files", mf)
    assert P.errors == []


def test_broken_orgmin_reference_detected(tmp_path):
    mf = _repo(tmp_path, DB_BAD, OM)
    P = vdb.Problems()
    vdb._check_manure(P, tmp_path / "database_files", mf)
    assert any("org_min reference 'DOES_NOT_EXIST'" in e for e in P.errors)


def test_empty_manure_file_flagged(tmp_path):
    mf = _repo(tmp_path, "", OM)
    P = vdb.Problems()
    vdb._check_manure(P, tmp_path / "database_files", mf)
    assert any("manure file" in e and "empty" in e for e in P.errors)


def test_real_repo_manure_references_resolve(repo_root):
    manifest = json.loads(
        (repo_root / "metadata" / "database_manifest.json").read_text())
    mf = {f["name"]: f for f in manifest["files"]}
    P = vdb.Problems()
    vdb._check_manure(P, repo_root / "database_files", mf)
    assert P.errors == [], "\n".join(P.errors)
