"""Drift detection against the SWAT+ source-derived schema artifact."""

from __future__ import annotations

import json

import pytest

import schema_diff
import schema_sync


def _artifact(files, version="62.0.0", unresolved=None):
    return {
        "swatplus_version": version,
        "source_repository": "swat-model/swatplus",
        "source_ref": version,
        "files": files,
        "unresolved": unresolved or [],
    }


def _fields(*specs):
    """specs: (name, type) pairs -> artifact field dicts."""
    return [
        {"fortran_name": n, "fortran_type": t, "numeric": t != "character",
         "position": i, "units": None, "doc": None}
        for i, (n, t) in enumerate(specs)
    ]


def _write(tmp_path, artifact, waivers=None):
    (tmp_path / "schemas").mkdir(exist_ok=True)
    (tmp_path / "schemas" / f"swatplus-{artifact['swatplus_version']}.json"
     ).write_text(json.dumps(artifact))
    (tmp_path / "metadata").mkdir(exist_ok=True)
    if waivers is not None:
        (tmp_path / "metadata" / "schema_drift_waivers.json").write_text(
            json.dumps(waivers))
    return tmp_path


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------

def test_trailing_columns_are_harmless():
    """Columns beyond the read set are never consumed, whatever they're called."""
    header = ["name", "a", "b", "pathogens", "description"]
    schema = {"columns": header, "numeric": [1, 2]}
    read = _fields(("nm", "character"), ("a", "real"), ("b", "real"))
    f = schema_sync._classify("x.frt", header, schema, read)
    assert f.kind == schema_sync.TRAILING_UNREAD


def test_underfilled_is_detected_and_names_the_missing_field():
    """The report must name the field the file is short of, not the last one."""
    header = ["name", "a", "description"]
    schema = {"columns": header, "numeric": [1]}
    read = _fields(("nm", "character"), ("a", "real"),
                   ("pl_uptake", "real"), ("descrip", "character"))
    f = schema_sync._classify("pesticide.pes", header, schema, read)
    assert f.kind == schema_sync.UNDERFILLED
    assert "pl_uptake" in f.detail
    assert "4 fields" in f.detail and "supplies 3" in f.detail


def test_type_mismatch_detected():
    header = ["name", "a", "b"]
    schema = {"columns": header, "numeric": [1, 2]}      # we expect both numeric
    read = _fields(("nm", "character"), ("a", "real"), ("b", "character"))
    f = schema_sync._classify("x.frt", header, schema, read)
    assert f.kind == schema_sync.TYPE_MISMATCH
    assert "'b'" in f.detail or "b" in f.detail


def test_exact_match_is_not_reported():
    header = ["name", "a"]
    schema = {"columns": header, "numeric": [1]}
    read = _fields(("nm", "character"), ("a", "real"))
    assert schema_sync._classify("x.frt", header, schema, read).kind == \
        schema_sync.MATCH


# --------------------------------------------------------------------------
# waivers / reporting
# --------------------------------------------------------------------------

def test_waiver_suppresses_failure_but_keeps_finding(tmp_path, monkeypatch):
    header = ["name", "description"]
    artifact = _artifact({"f.frt": {"fields": _fields(
        ("nm", "character"), ("x", "real"), ("descrip", "character"))}})
    waivers = {"waivers": [{"file": "f.frt", "kind": "underfilled",
                            "reason": "pending decision"}]}
    root = _write(tmp_path, artifact, waivers)
    monkeypatch.setattr(schema_sync, "FILE_SCHEMAS",
                        {"f.frt": {"columns": header, "numeric": []}})
    monkeypatch.setattr(schema_sync, "EXPECTED_BY_NAME",
                        {"f.frt": {"fmt": "flat_named"}})
    rep = schema_sync.analyze(root)
    assert len(rep.findings) == 1
    assert rep.findings[0].waived is True
    assert rep.blocking == []          # waived -> not blocking
    assert len(rep.waived) == 1        # but still reported


def test_unwaived_drift_blocks(tmp_path, monkeypatch):
    header = ["name", "description"]
    artifact = _artifact({"f.frt": {"fields": _fields(
        ("nm", "character"), ("x", "real"), ("descrip", "character"))}})
    root = _write(tmp_path, artifact, {"waivers": []})
    monkeypatch.setattr(schema_sync, "FILE_SCHEMAS",
                        {"f.frt": {"columns": header, "numeric": []}})
    monkeypatch.setattr(schema_sync, "EXPECTED_BY_NAME",
                        {"f.frt": {"fmt": "flat_named"}})
    rep = schema_sync.analyze(root)
    assert len(rep.blocking) == 1


def test_real_repo_has_no_unwaived_drift(repo_root):
    """The committed data must not drift from SWAT+ except where waived."""
    rep = schema_sync.analyze(repo_root)
    assert rep.blocking == [], \
        "unwaived schema drift: " + "; ".join(f.detail for f in rep.blocking)


def test_pesticide_drift_is_tracked(repo_root):
    """The known pl_uptake gap must stay visible until it is fixed."""
    rep = schema_sync.analyze(repo_root)
    waived = {f.file for f in rep.waived}
    assert "pesticide.pes" in waived, (
        "pesticide.pes drift is no longer waived -- if the file was fixed, "
        "remove the waiver from metadata/schema_drift_waivers.json"
    )


# --------------------------------------------------------------------------
# version diff
# --------------------------------------------------------------------------

def test_diff_reports_added_and_moved_fields():
    old = _artifact({"a.sno": {"fields": _fields(
        ("nm", "character"), ("x", "real"), ("y", "real"))}})
    new = _artifact({"a.sno": {"fields": _fields(
        ("nm", "character"), ("newcol", "real"), ("x", "real"), ("y", "real"))}},
        version="63.0.0")
    lines, changed = schema_diff.diff(old, new)
    text = "\n".join(lines)
    assert changed
    assert "+ added   newcol" in text
    assert "! moved   x: position 1 -> 2" in text


def test_diff_reports_type_change():
    old = _artifact({"a.sno": {"fields": _fields(("nm", "character"),
                                                 ("x", "real"))}})
    new = _artifact({"a.sno": {"fields": _fields(("nm", "character"),
                                                 ("x", "integer"))}},
                    version="63.0.0")
    lines, changed = schema_diff.diff(old, new)
    assert changed and "! type    x: real -> integer" in "\n".join(lines)


def test_diff_quiet_when_identical():
    a = _artifact({"a.sno": {"fields": _fields(("nm", "character"))}})
    lines, changed = schema_diff.diff(a, a)
    assert changed is False
