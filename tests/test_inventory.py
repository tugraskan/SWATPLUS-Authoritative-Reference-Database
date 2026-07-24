"""Inventory classification & file.cio-vs-disk (spec test 3)."""

from __future__ import annotations

import inventory_reference_files as inv
from conftest import make_fake_checkout


def test_classify_shared_reference_database():
    assert inv.classify("plants.plt") == "shared reference database"
    assert inv.classify("manure_db.frt") == "shared reference database"
    # discovered direct-read databases are shared reference databases
    assert inv.classify("puddle.ops") == "shared reference database"
    assert inv.classify("transplant.plt") == "shared reference database"


def test_classify_project_input_and_output():
    assert inv.classify("hru.con") == "project-specific input"
    assert inv.classify("soils.sol") == "project-specific input"
    assert inv.classify("basin_wb_aa.txt") == "model output"
    assert inv.classify("simulation.out") == "model output"


def test_inventory_runs_and_reports_missing_expected(tmp_path):
    checkout = make_fake_checkout(tmp_path)
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    rc = inv.main(["--swatplus-checkout", str(checkout), "--repo-root", str(repo)])
    assert rc == 0
    doc = (repo / "docs" / "source_inventory.md").read_text()
    # scen_lu.dtl is expected but present in neither source
    assert "scen_lu.dtl" in doc
    assert "Fixed-filename (direct-read) databases" in doc


def test_file_cio_reference_not_proof_of_existence(tmp_path):
    # file.cio references pesticide.pes but the fake checkout has no such file
    checkout = make_fake_checkout(tmp_path)
    for sub in ("Ames_sub1", "Osu_1hru"):
        (checkout / "refdata" / sub / "file.cio").write_text(
            "hru_parm_db  plants.plt  ghost_file.xyz  null\n", encoding="utf-8")
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    inv.main(["--swatplus-checkout", str(checkout), "--repo-root", str(repo)])
    doc = (repo / "docs" / "source_inventory.md").read_text()
    # a name referenced by file.cio but absent on disk is reported as absent
    assert "ghost_file.xyz" in doc
