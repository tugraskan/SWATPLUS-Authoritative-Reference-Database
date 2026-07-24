"""Change-log validation (spec test 13) — structural rules."""

from __future__ import annotations

import csv

import validate_change_log as vcl

HEADER = vcl.REQUIRED_COLUMNS


def _write(tmp_path, rows):
    (tmp_path / "metadata").mkdir()
    p = tmp_path / "metadata" / "database_changes.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in HEADER})
    return tmp_path


def _row(**kw):
    base = dict(change_id="c1", file_name="plants.plt", record_name="corn",
                change_type="added", date="2026-07-24", submitted_by="me",
                source="paper X", reason="new cultivar",
                swatplus_version="not_tested", editor_version="not_tested",
                review_status="approved", notes="")
    base.update(kw)
    return base


def test_valid_log_passes(tmp_path):
    _write(tmp_path, [_row()])
    assert vcl.validate(tmp_path) == []


def test_duplicate_change_id_detected(tmp_path):
    _write(tmp_path, [_row(change_id="dup"), _row(change_id="dup", record_name="soy")])
    errs = vcl.validate(tmp_path)
    assert any("duplicate change_id" in e for e in errs)


def test_invalid_change_type_detected(tmp_path):
    _write(tmp_path, [_row(change_type="frobnicated")])
    errs = vcl.validate(tmp_path)
    assert any("invalid change_type" in e for e in errs)


def test_missing_reason_detected(tmp_path):
    _write(tmp_path, [_row(reason="")])
    errs = vcl.validate(tmp_path)
    assert any("reason is required" in e for e in errs)


def test_missing_source_detected(tmp_path):
    _write(tmp_path, [_row(source="")])
    errs = vcl.validate(tmp_path)
    assert any("source is required" in e for e in errs)


def test_real_repo_change_log_structural_ok(repo_root):
    assert vcl.validate(repo_root) == []
