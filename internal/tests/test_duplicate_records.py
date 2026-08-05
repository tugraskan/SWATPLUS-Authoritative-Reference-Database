"""Record-level validation checks (spec tests 9, 10, 11, 12).

These exercise the format-aware validator on small synthetic files named after a
schema-bearing file (snow.sno) so field-count and numeric rules apply.
"""

from __future__ import annotations

import validate_database_files as vdb

HEADER = ("snow.sno: written by SWAT+ editor v2.3.3 for SWAT+ rev.60.5.7\n"
          "name  fall_tmp  melt_tmp  melt_max  melt_min  tmp_lag  snow_h2o  "
          "cov50  snow_init\n")
GOOD_ROW = "snow001  1.0  0.5  4.5  4.5  1.0  1.0  0.5  0.0\n"


def _check(tmp_path, body):
    p = tmp_path / "snow.sno"
    p.write_text(HEADER + body, encoding="utf-8")
    P = vdb.Problems()
    vdb._check_name_keyed(P, "snow.sno", p, "flat_named")
    return P.errors


def test_clean_file_has_no_errors(tmp_path):
    assert _check(tmp_path, GOOD_ROW) == []


def test_duplicate_record_name_detected(tmp_path):
    errs = _check(tmp_path, GOOD_ROW + GOOD_ROW)
    assert any("duplicate record name" in e for e in errs)


def test_blank_or_null_record_name_detected(tmp_path):
    errs = _check(tmp_path, "null  1.0  0.5  4.5  4.5  1.0  1.0  0.5  0.0\n")
    assert any("blank or 'null' record name" in e for e in errs)


def test_bad_field_count_detected(tmp_path):
    # one column short
    errs = _check(tmp_path, "snow002  1.0  0.5  4.5  4.5  1.0  1.0  0.5\n")
    assert any("expected 9 fields" in e for e in errs)


def test_non_numeric_value_detected(tmp_path):
    errs = _check(tmp_path, "snow003  ABC  0.5  4.5  4.5  1.0  1.0  0.5  0.0\n")
    assert any("non-numeric" in e for e in errs)


def test_line_number_reported(tmp_path):
    errs = _check(tmp_path, GOOD_ROW + GOOD_ROW)
    # duplicate is on line 4 (2 header + 2 data)
    assert any("line 4" in e for e in errs)
