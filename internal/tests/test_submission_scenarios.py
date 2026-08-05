"""End-to-end checks for the ways a submitted row can be wrong.

Each test builds a small file that is valid apart from one defect and asserts
the validator reports it.  These are written against a file that has a schema
(`fire.ops`) so the strict field/type/header rules apply.
"""

from __future__ import annotations

import validate_database_files as vdb

HEADER = ("fire.ops: written by SWAT+ editor v2.2.0 for SWAT+ rev.60.5.4\n"
          "name                   chg_cn2     frac_burn  description\n")
GOOD = "grass                  8.00000       1.00000  \n"


def _errors(tmp_path, body, header=HEADER, filename="fire.ops"):
    p = tmp_path / filename
    p.write_text(header + body, encoding="utf-8")
    P = vdb.Problems()
    vdb._check_name_keyed(P, filename, p, "flat_named")
    return P.errors


def test_valid_row_accepted(tmp_path):
    assert _errors(tmp_path, GOOD) == []


def test_trailing_description_may_be_absent(tmp_path):
    """fire.ops rows legitimately omit the trailing free-text column."""
    assert _errors(tmp_path, "grass                  8.00000       1.00000\n") == []


def test_trailing_description_may_contain_spaces(tmp_path):
    """urban.urb-style descriptions with spaces must not trip field counting."""
    body = "grass    8.00000   1.00000   a description with spaces\n"
    assert _errors(tmp_path, body) == []


def test_too_few_columns_detected(tmp_path):
    errs = _errors(tmp_path, "grass  8.0\n")
    assert any("expected at least 3 fields, found 2" in e for e in errs)


def test_wrong_data_type_detected(tmp_path):
    errs = _errors(tmp_path, "grass  NOT_A_NUMBER  1.0  x\n")
    assert any("non-numeric value 'NOT_A_NUMBER' in column 'chg_cn2'" in e
               for e in errs)


def test_duplicate_record_detected(tmp_path):
    errs = _errors(tmp_path, GOOD + GOOD)
    assert any("duplicate record name" in e for e in errs)


def test_blank_record_name_detected(tmp_path):
    errs = _errors(tmp_path, "null  8.0  1.0  x\n")
    assert any("blank or 'null' record name" in e for e in errs)


def test_upstream_added_column_detected(tmp_path):
    """A new upstream column must not pass silently via the free-text tail."""
    hdr = HEADER.rstrip("\n") + "  new_col\n"
    errs = _errors(tmp_path, "grass  8.0  1.0  desc  99\n", header=hdr)
    assert any("column header does not match the expected schema" in e
               for e in errs)
    assert any("new: ['new_col']" in e for e in errs)


def test_renamed_column_detected(tmp_path):
    hdr = HEADER.replace("frac_burn", "burn_fraction")
    errs = _errors(tmp_path, GOOD, header=hdr)
    assert any("renamed 'frac_burn' -> 'burn_fraction'" in e for e in errs)


def test_removed_column_detected(tmp_path):
    hdr = HEADER.replace("     frac_burn  description", "  description")
    errs = _errors(tmp_path, "grass  8.0  x\n", header=hdr)
    assert any("column header does not match the expected schema" in e
               for e in errs)


def test_corrupt_header_row_detected(tmp_path):
    """A garbled header means the read scheme is broken, not just one row."""
    hdr = "fire.ops: title\n### CORRUPTED ###\n"
    errs = _errors(tmp_path, GOOD, header=hdr)
    assert errs, "a corrupted column-header row must be reported"
