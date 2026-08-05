"""Tests for scripts/sync_change_log_from_pr.py.

The script derives file/record/change_type from a real git diff (the same
approach validate_change_log.py's coverage check uses), so most tests here
work against a real, throwaway git repo rather than mocking git.
"""

from __future__ import annotations

import csv
import subprocess

import sync_change_log_from_pr as sync_mod

SNOW_HEADER = "name  fall_tmp  melt_tmp  melt_max  melt_min  tmp_lag  snow_h2o  cov50  snow_init\n"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                    capture_output=True, text=True)


def _init_repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "database_files").mkdir()
    (tmp_path / "metadata").mkdir()
    with open(tmp_path / "metadata" / "database_changes.csv", "w", newline="") as fh:
        csv.DictWriter(fh, fieldnames=sync_mod.REQUIRED_COLUMNS).writeheader()
    return tmp_path


def _write_snow(repo, rows: dict[str, list[str]]):
    lines = [SNOW_HEADER]
    for name, vals in rows.items():
        lines.append(" ".join([name] + vals) + "\n")
    (repo / "database_files" / "snow.sno").write_text("".join(lines))


def _commit_base(repo) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True)
    return out.stdout.strip()


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# parse_pr_body -- everything optional, never an error
# ---------------------------------------------------------------------------

def test_blank_body_parses_with_defaults():
    fields = sync_mod.parse_pr_body("")
    assert fields["reason"] == ""
    assert fields["source"] == ""
    assert fields["swatplus_version"] == "not_tested"
    assert fields["editor_version"] == "not_tested"
    assert fields["notes"] == ""


def test_filled_reason_and_source_parsed():
    body = ("## Reason\n\nField trial update\n\n## Source\n\nSmith 2026\n\n"
            "## Version notes\n\n- SWAT+ version associated with this change, "
            "if known: 62.0.0\n- SWAT+ Editor version associated with this "
            "change, if known:\n")
    fields = sync_mod.parse_pr_body(body)
    assert fields["reason"] == "Field trial update"
    assert fields["source"] == "Smith 2026"
    assert fields["swatplus_version"] == "62.0.0"
    assert fields["editor_version"] == "not_tested"


def test_version_fields_do_not_bleed_into_each_other():
    """Regression: the two Version notes bullets must parse independently."""
    body = ("## Version notes\n\n"
            "- SWAT+ version associated with this change, if known: 62.0.0\n"
            "- SWAT+ Editor version associated with this change, if known: 4.0.0\n")
    fields = sync_mod.parse_pr_body(body)
    assert fields["swatplus_version"] == "62.0.0"
    assert fields["editor_version"] == "4.0.0"


# ---------------------------------------------------------------------------
# detect_changes -- diffing database_files/ against a base ref
# ---------------------------------------------------------------------------

def test_new_record_detected_as_added(tmp_path):
    _init_repo(tmp_path)
    _write_snow(tmp_path, {"snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"]})
    base = _commit_base(tmp_path)

    _write_snow(tmp_path, {
        "snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"],
        "snow002": ["2.0", "1.5", "5.5", "5.5", "2.0", "2.0", "1.5", "1.0"],
    })

    changes = sync_mod.detect_changes(tmp_path, base)
    assert changes == [{"file_name": "snow.sno", "record_name": "snow002",
                        "change_type": "added"}]


def test_modified_record_detected(tmp_path):
    _init_repo(tmp_path)
    _write_snow(tmp_path, {"snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"]})
    base = _commit_base(tmp_path)

    _write_snow(tmp_path, {"snow001": ["9.9", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"]})

    changes = sync_mod.detect_changes(tmp_path, base)
    assert changes == [{"file_name": "snow.sno", "record_name": "snow001",
                        "change_type": "modified"}]


def test_removed_record_detected(tmp_path):
    _init_repo(tmp_path)
    _write_snow(tmp_path, {
        "snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"],
        "snow002": ["2.0", "1.5", "5.5", "5.5", "2.0", "2.0", "1.5", "1.0"],
    })
    base = _commit_base(tmp_path)

    _write_snow(tmp_path, {"snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"]})

    changes = sync_mod.detect_changes(tmp_path, base)
    assert changes == [{"file_name": "snow.sno", "record_name": "snow002",
                        "change_type": "removed"}]


def test_unchanged_file_no_changes_detected(tmp_path):
    _init_repo(tmp_path)
    _write_snow(tmp_path, {"snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"]})
    base = _commit_base(tmp_path)

    changes = sync_mod.detect_changes(tmp_path, base)
    assert changes == []


def test_decision_table_file_gets_one_file_wide_row(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "database_files" / "lum.dtl").write_text("lum.dtl: title\n0\n\n")
    base = _commit_base(tmp_path)

    (tmp_path / "database_files" / "lum.dtl").write_text(
        "lum.dtl: title\n1\n\nname  conds  alts  acts\nirr_demo  1  1  1\n"
        "var obj obj_num lim_var lim_op lim_const alt1\nx hru 1 null - 0.0 y\n"
        "act_typ obj obj_num name option const const2 fp\nirr hru 1 auto n 0 0 null y\n")

    changes = sync_mod.detect_changes(tmp_path, base)
    assert changes == [{"file_name": "lum.dtl", "record_name": "*",
                        "change_type": "modified"}]


def test_no_database_file_changes_returns_empty(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("hello\n")
    base = _commit_base(tmp_path)
    (tmp_path / "README.md").write_text("hello world\n")

    changes = sync_mod.detect_changes(tmp_path, base)
    assert changes == []


# ---------------------------------------------------------------------------
# sync() -- end to end, including CSV read/write behavior
# ---------------------------------------------------------------------------

def test_sync_writes_row_with_optional_fields_blank(tmp_path):
    _init_repo(tmp_path)
    _write_snow(tmp_path, {"snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"]})
    base = _commit_base(tmp_path)
    _write_snow(tmp_path, {
        "snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"],
        "snow002": ["2.0", "1.5", "5.5", "5.5", "2.0", "2.0", "1.5", "1.0"],
    })

    rows = sync_mod.sync(tmp_path, "42", "alice", "", base)
    assert len(rows) == 1
    assert rows[0]["reason"] == ""
    assert rows[0]["source"] == ""
    assert rows[0]["review_status"] == "pending"

    csv_rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert len(csv_rows) == 1
    assert csv_rows[0]["change_id"] == "pr-42-snow.sno-snow002"


def test_sync_no_database_changes_returns_empty_list(tmp_path):
    _init_repo(tmp_path)
    base = _commit_base(tmp_path)
    rows = sync_mod.sync(tmp_path, "42", "alice", "", base)
    assert rows == []


def test_sync_rerun_preserves_date_and_review_status(tmp_path):
    _init_repo(tmp_path)
    _write_snow(tmp_path, {"snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"]})
    base = _commit_base(tmp_path)
    _write_snow(tmp_path, {
        "snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"],
        "snow002": ["2.0", "1.5", "5.5", "5.5", "2.0", "2.0", "1.5", "1.0"],
    })
    sync_mod.sync(tmp_path, "42", "alice", "", base)

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    rows[0]["review_status"] = "approved"
    rows[0]["date"] = "2020-01-01"
    with open(tmp_path / "metadata" / "database_changes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sync_mod.REQUIRED_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    body = "## Reason\n\nUpdated reason\n"
    sync_mod.sync(tmp_path, "42", "alice", body, base)

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert len(rows) == 1
    assert rows[0]["review_status"] == "approved"
    assert rows[0]["date"] == "2020-01-01"
    assert rows[0]["reason"] == "Updated reason"


def test_sync_does_not_touch_other_prs_rows(tmp_path):
    _init_repo(tmp_path)
    other = {"change_id": "pr-1-plants.plt-corn", "file_name": "plants.plt",
              "record_name": "corn", "change_type": "added", "date": "2026-01-01",
              "submitted_by": "bob", "source": "s", "reason": "r",
              "swatplus_version": "not_tested", "editor_version": "not_tested",
              "review_status": "pending", "notes": ""}
    with open(tmp_path / "metadata" / "database_changes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sync_mod.REQUIRED_COLUMNS)
        w.writeheader()
        w.writerow(other)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed")
    base = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
                           check=True, capture_output=True, text=True).stdout.strip()

    _write_snow(tmp_path, {"snow001": ["1.0", "0.5", "4.5", "4.5", "1.0", "1.0", "0.5", "0.0"]})
    _git(tmp_path, "add", "-A")  # stage the new file so `git diff <base>` sees it
    sync_mod.sync(tmp_path, "42", "alice", "", base)

    rows = _read_csv(tmp_path / "metadata" / "database_changes.csv")
    assert len(rows) == 2
    assert other in rows
