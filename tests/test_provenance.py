"""Provenance & header-version parsing (spec tests 6, 19, 20, 21, 22)."""

from __future__ import annotations

import csv
import json

from swat_common import parse_header


def test_editor_version_parsed():
    h = parse_header("snow.sno: written by SWAT+ editor v2.3.3 on 2023-10-25 "
                     "08:58 for SWAT+ rev.60.5.7")
    assert h.editor_version == "2.3.3"


def test_swatplus_revision_parsed():
    h = parse_header("cal_parms.cal: written by SWAT+ editor v2.2.0 on "
                     "2023-03-22 for SWAT+ rev.60.5.4")
    assert h.swatplus_revision == "60.5.4"


def test_missing_version_is_null_not_guessed():
    # Ames tillage.til has no version header; first line is the column header.
    h = parse_header("name  mix_eff  mix_dp  rough  ridge_ht  ridge_sp  description")
    assert h.editor_version is None
    assert h.swatplus_revision is None


def test_real_bootstrap_provenance_present(repo_root):
    prov = json.loads((repo_root / "metadata" / "bootstrap_sources.json").read_text())
    assert prov["bootstrap_swatplus_commit"].startswith("cb442f7")
    # tillage.til came from Ames and legitimately has no version header -> null
    by = {f["file_name"]: f for f in prov["files"]}
    assert by["tillage.til"]["source_editor_version"] is None
    # snow.sno (Ames) carries a version header
    assert by["snow.sno"]["source_editor_version"] == "2.3.3"
    assert by["snow.sno"]["source_swatplus_revision"] == "60.5.7"


def test_compatibility_matrix_defaults_not_tested(repo_root):
    path = repo_root / "metadata" / "compatibility_matrix.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "compatibility matrix should have seed rows"
    assert all(r["test_status"] == "not_tested" for r in rows)
    assert all(r["test_date"].strip() == "" for r in rows)


def test_external_provenance_separate_from_bootstrap(repo_root):
    boot = json.loads((repo_root / "metadata" / "bootstrap_sources.json").read_text())
    ext = json.loads((repo_root / "metadata" / "external_sources.json").read_text())
    boot_names = {f["file_name"] for f in boot["files"]}
    ext_names = {f["file_name"] for f in ext["files"]}
    # the four external files must NOT appear in bootstrap provenance
    assert ext_names == {"pathogens.pth", "metals.mtl", "salt.slt", "flo_con.dtl"}
    assert boot_names.isdisjoint(ext_names)
