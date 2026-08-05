"""Tests for scripts/sync_change_log_from_pr.py (PR-template -> change-log sync)."""

from __future__ import annotations

import csv

import sync_change_log_from_pr as sync_mod

GOOD_BODY = """\
<!-- intro comment, ignored -->

## Database file

<!-- e.g. plants.plt -->
plants.plt

## Record

<!-- Stable record name(s), comma-separated, or `*` for a file-wide change -->
corn_new

## Change type

- [ ] Added
- [x] Modified
- [ ] Deprecated
- [ ] Removed

## Reason

<!-- Why this change is needed -->
Updated yield parameters from field trial data.

## Source

<!-- publication etc -->
Smith et al. 2026, Journal of Agronomy

## Version notes

- SWAT+ version associated with this change, if known: 62.0.0
- SWAT+ Editor version associated with this change, if known:

## Notes

<!-- optional -->
"""


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sync_mod.REQUIRED_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# parse_pr_body
# ---------------------------------------------------------------------------

def test_valid_body_parses_cleanly():
    fields, errors = sync_mod.parse_pr_body(GOOD_BODY)
    assert errors == []
    assert fields["file_name"] == "plants.plt"
    assert fields["records"] == ["corn_new"]
    assert fields["change_type"] == "modified"
    assert fields["reason"] == "Updated yield parameters from field trial data."
    assert fields["source"] == "Smith et al. 2026, Journal of Agronomy"
    assert fields["swatplus_version"] == "62.0.0"
    assert fields["editor_version"] == "not_tested"
    assert fields["notes"] == ""


def test_comma_separated_records_split():
    body = GOOD_BODY.replace("corn_new", "corn_new, soy_new , wheat_new")
    fields, errors = sync_mod.parse_pr_body(body)
    assert errors == []
    assert fields["records"] == ["corn_new", "soy_new", "wheat_new"]


def test_star_record_for_file_wide_change():
    body = GOOD_BODY.replace("corn_new", "*")
    fields, errors = sync_mod.parse_pr_body(body)
    assert errors == []
    assert fields["records"] == ["*"]


def test_empty_template_reports_all_required_fields_missing():
    blank = "## Database file\n\n## Record\n\n## Change type\n\n" \
            "- [ ] Added\n- [ ] Modified\n- [ ] Deprecated\n- [ ] Removed\n\n" \
            "## Reason\n\n## Source\n\n## Version notes\n\n## Notes\n"
    fields, errors = sync_mod.parse_pr_body(blank)
    assert fields == {}
    assert any("Database file" in e for e in errors)
    assert any("Record" in e for e in errors)
    assert any("Change type" in e for e in errors)
    assert any("Reason" in e for e in errors)
    assert any("Source" in e for e in errors)


def test_no_change_type_checked_is_an_error():
    body = GOOD_BODY.replace("- [x] Modified", "- [ ] Modified")
    _, errors = sync_mod.parse_pr_body(body)
    assert any("Change type" in e and "exactly one" in e for e in errors)


def test_multiple_change_types_checked_is_an_error():
    body = GOOD_BODY.replace("- [ ] Added", "- [x] Added")
    _, errors = sync_mod.parse_pr_body(body)
    assert any("exactly ONE box" in e for e in errors)


def test_version_fields_do_not_bleed_into_each_other():
    """Regression: the two Version notes bullets must parse independently --
    an earlier bug let SWAT+ version's capture swallow the newline and run
    on into the SWAT+ Editor version line's text."""
    body = GOOD_BODY.replace(
        "- SWAT+ Editor version associated with this change, if known:",
        "- SWAT+ Editor version associated with this change, if known: 4.0.0")
    fields, errors = sync_mod.parse_pr_body(body)
    assert errors == []
    assert fields["swatplus_version"] == "62.0.0"
    assert fields["editor_version"] == "4.0.0"


def test_missing_reason_only():
    body = GOOD_BODY.replace(
        "Updated yield parameters from field trial data.", "")
    _, errors = sync_mod.parse_pr_body(body)
    assert len(errors) == 1
    assert "Reason" in errors[0]


# ---------------------------------------------------------------------------
# sync() -- CSV read/write behavior
# ---------------------------------------------------------------------------

def test_sync_creates_row_for_new_pr(tmp_path):
    (tmp_path / "metadata").mkdir()
    _write_csv(tmp_path / "metadata" / "database_changes.csv", [])

    errors = sync_mod.sync(tmp_path, "42", "alice", GOOD_BODY)
    assert errors == []

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert len(rows) == 1
    r = rows[0]
    assert r["change_id"] == "pr-42"
    assert r["file_name"] == "plants.plt"
    assert r["record_name"] == "corn_new"
    assert r["change_type"] == "modified"
    assert r["submitted_by"] == "alice"
    assert r["review_status"] == "pending"
    assert r["date"]  # today's date, non-empty


def test_sync_invalid_body_leaves_csv_untouched(tmp_path):
    (tmp_path / "metadata").mkdir()
    original = [{"change_id": "pr-1", "file_name": "x", "record_name": "y",
                 "change_type": "added", "date": "2026-01-01",
                 "submitted_by": "bob", "source": "s", "reason": "r",
                 "swatplus_version": "not_tested", "editor_version": "not_tested",
                 "review_status": "pending", "notes": ""}]
    _write_csv(tmp_path / "metadata" / "database_changes.csv", original)

    bad_body = "## Database file\n\n## Record\n\n"
    errors = sync_mod.sync(tmp_path, "99", "carol", bad_body)
    assert errors != []

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert rows == original


def test_sync_multiple_records_creates_one_row_each(tmp_path):
    (tmp_path / "metadata").mkdir()
    _write_csv(tmp_path / "metadata" / "database_changes.csv", [])
    body = GOOD_BODY.replace("corn_new", "corn_new, soy_new")

    errors = sync_mod.sync(tmp_path, "7", "dave", body)
    assert errors == []

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert {r["change_id"] for r in rows} == {"pr-7-1", "pr-7-2"}
    assert {r["record_name"] for r in rows} == {"corn_new", "soy_new"}


def test_sync_rerun_updates_row_in_place_not_duplicated(tmp_path):
    (tmp_path / "metadata").mkdir()
    _write_csv(tmp_path / "metadata" / "database_changes.csv", [])
    sync_mod.sync(tmp_path, "42", "alice", GOOD_BODY)

    edited_body = GOOD_BODY.replace(
        "Updated yield parameters from field trial data.",
        "Updated yield parameters from a corrected field trial dataset.")
    errors = sync_mod.sync(tmp_path, "42", "alice", edited_body)
    assert errors == []

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert len(rows) == 1
    assert "corrected" in rows[0]["reason"]


def test_sync_rerun_preserves_date_and_review_status(tmp_path):
    (tmp_path / "metadata").mkdir()
    _write_csv(tmp_path / "metadata" / "database_changes.csv", [])
    sync_mod.sync(tmp_path, "42", "alice", GOOD_BODY)

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    rows[0]["review_status"] = "approved"
    rows[0]["date"] = "2020-01-01"
    _write_csv(tmp_path / "metadata" / "database_changes.csv", rows)

    edited_body = GOOD_BODY.replace(
        "Smith et al. 2026, Journal of Agronomy", "Smith et al. 2026 (revised)")
    sync_mod.sync(tmp_path, "42", "alice", edited_body)

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert len(rows) == 1
    assert rows[0]["review_status"] == "approved"
    assert rows[0]["date"] == "2020-01-01"
    assert rows[0]["source"] == "Smith et al. 2026 (revised)"


def test_sync_does_not_touch_other_prs_rows(tmp_path):
    (tmp_path / "metadata").mkdir()
    other = {"change_id": "pr-1", "file_name": "x", "record_name": "y",
             "change_type": "added", "date": "2026-01-01",
             "submitted_by": "bob", "source": "s", "reason": "r",
             "swatplus_version": "not_tested", "editor_version": "not_tested",
             "review_status": "pending", "notes": ""}
    _write_csv(tmp_path / "metadata" / "database_changes.csv", [other])

    sync_mod.sync(tmp_path, "42", "alice", GOOD_BODY)

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert len(rows) == 2
    assert other in rows


def test_sync_shrinking_record_list_drops_stale_rows(tmp_path):
    (tmp_path / "metadata").mkdir()
    _write_csv(tmp_path / "metadata" / "database_changes.csv", [])
    body_two = GOOD_BODY.replace("corn_new", "corn_new, soy_new")
    sync_mod.sync(tmp_path, "7", "dave", body_two)

    body_one = GOOD_BODY  # back to a single record
    sync_mod.sync(tmp_path, "7", "dave", body_one)

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert len(rows) == 1
    assert rows[0]["change_id"] == "pr-7"
    assert rows[0]["record_name"] == "corn_new"
