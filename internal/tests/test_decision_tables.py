"""Structural validation for SWAT+ decision-table blocks."""

from __future__ import annotations

import validate_database_files as vdb


GOOD = """example.dtl
1

name conds alts acts
example 1 1 1
var obj obj_num lim_var lim_op lim_const alt1
jday hru 0 null - 100 =
act_typ obj obj_num name option const const2 fp outcome
plant hru 0 plant corn 0 0 null y
"""


def _problems(tmp_path, text):
    path = tmp_path / "example.dtl"
    path.write_text(text)
    problems = vdb.Problems()
    vdb._check_decision(problems, path.name, path)
    return problems


def test_valid_decision_table_passes(tmp_path):
    problems = _problems(tmp_path, GOOD)
    assert problems.errors == []


def test_missing_condition_row_is_rejected(tmp_path):
    bad = GOOD.replace("jday hru 0 null - 100 =\n", "")
    problems = _problems(tmp_path, bad)
    assert any("declares 1 condition rows but contains 0" in e
               for e in problems.errors)


def test_missing_action_row_is_rejected(tmp_path):
    bad = GOOD.replace("plant hru 0 plant corn 0 0 null y\n", "")
    problems = _problems(tmp_path, bad)
    assert any("declares 1 action rows but contains 0" in e
               for e in problems.errors)


def test_wrong_alternative_column_count_is_rejected(tmp_path):
    bad = GOOD.replace("jday hru 0 null - 100 =", "jday hru 0 null - 100")
    problems = _problems(tmp_path, bad)
    assert any("condition row has 6 fields; expected 7" in e
               for e in problems.errors)


def test_declared_table_count_mismatch_is_an_error(tmp_path):
    problems = _problems(tmp_path, GOOD.replace("\n1\n", "\n2\n", 1))
    assert any("declared table count 2 != 1" in e for e in problems.errors)
