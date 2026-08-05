#!/usr/bin/env python3
"""Generate metadata/database_changes.csv row(s) from a PR's actual file diff.

Contributors don't type which file or record they changed -- that's derived
directly by diffing database_files/ against the pull request's base commit,
reusing the same record-level parsing validate_change_log.py's coverage check
uses. Contributors never hand-edit database_changes.csv, and there is no
required field: the PR template's Reason/Source are both optional free text,
and a PR with neither still gets a row, just with those columns blank.

Re-running this script (on every PR edit/push) updates that PR's row(s) in
place -- keyed by (PR number, file, record) -- rather than duplicating them;
a row's `date` and `review_status` are preserved across re-runs so editing
the PR description doesn't reset them.

Usage (normally invoked by .github/workflows/sync-change-log.yml, which sets
the environment variables from the pull_request event):
    PR_NUMBER=42 PR_AUTHOR=someone PR_BODY="$(cat body.md)" \
        python internal/scripts/sync_change_log_from_pr.py --repo-root . \
        --base-ref <base-commit-sha>
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from swat_common import parse_name_keyed_table  # noqa: E402
from swat_config import (  # noqa: E402
    DATABASE_FILES_DIR, EXPECTED_BY_NAME, FILE_SCHEMAS, METADATA_DIR,
    NAME_KEYED_FORMATS,
)

REQUIRED_COLUMNS = [
    "change_id", "file_name", "record_name", "change_type", "date",
    "submitted_by", "source", "reason", "swatplus_version", "editor_version",
    "review_status", "notes",
]


# ---------------------------------------------------------------------------
# PR body -- Reason / Source / version notes are the only human input, and
# all of it is optional.
# ---------------------------------------------------------------------------

def _strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def _parse_sections(body: str) -> dict[str, str]:
    """Split a PR body into {header text -> raw section body} by '## ' headers."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf)
            current = m.group(1).strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def _field_text(sections: dict[str, str], name: str) -> str:
    raw = _strip_comments(sections.get(name, ""))
    lines = [l.strip() for l in raw.splitlines()]
    return "\n".join(l for l in lines if l).strip()


def _parse_version_field(sections: dict[str, str], label: str) -> str:
    raw = _strip_comments(sections.get("Version notes", ""))
    # [^:\n]* and [ \t]* (not \s*) keep the match confined to a single line,
    # so the capture can't cross the newline into the next bullet's text.
    m = re.search(rf"{re.escape(label)}[^:\n]*:[ \t]*(.*)", raw)
    val = m.group(1).strip() if m else ""
    return val or "not_tested"


def parse_pr_body(body: str) -> dict:
    """Everything here is optional; there is no invalid PR body."""
    sections = _parse_sections(body)
    return {
        "reason": _field_text(sections, "Reason"),
        "source": _field_text(sections, "Source"),
        "swatplus_version": _parse_version_field(sections, "SWAT+ version"),
        "editor_version": _parse_version_field(sections, "SWAT+ Editor version"),
        "notes": _field_text(sections, "Notes"),
    }


# ---------------------------------------------------------------------------
# Diff-based change detection (same git plumbing as validate_change_log.py's
# coverage check, plus per-record added/modified/removed classification).
# ---------------------------------------------------------------------------

def _git_show(repo_root: Path, ref: str, rel: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "show", f"{ref}:{rel}"],
            stderr=subprocess.DEVNULL).decode("utf-8", "replace")
    except subprocess.CalledProcessError:
        return None  # file did not exist at base -> whole file is new


def _changed_database_files(repo_root: Path, base_ref: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "diff", "--name-only", base_ref,
             "--", DATABASE_FILES_DIR], stderr=subprocess.DEVNULL).decode()
    except subprocess.CalledProcessError:
        return []
    return [line.split("/", 1)[1] for line in out.splitlines() if "/" in line]


def _record_map_from_text(text: str, name: str, fmt: str,
                           cols: list[str] | None) -> dict[str, list[str]]:
    with tempfile.NamedTemporaryFile("w", suffix="_" + name, delete=False,
                                     encoding="utf-8") as fh:
        fh.write(text)
        tp = fh.name
    try:
        table = parse_name_keyed_table(tp, fmt, cols)
        return {r.name: r.fields for r in table.records}
    finally:
        Path(tp).unlink(missing_ok=True)


def detect_changes(repo_root: Path, base_ref: str) -> list[dict]:
    """Diff database_files/ (working tree) against base_ref.

    Returns one dict per changed record: {file_name, record_name,
    change_type}. Decision-table / constants files (not name-keyed) get a
    single file-wide row (record_name="*") since there's no cheap per-record
    diff for their structure.
    """
    changes = []
    for name in _changed_database_files(repo_root, base_ref):
        spec = EXPECTED_BY_NAME.get(name)
        fmt = spec["fmt"] if spec else "flat_named"
        cur_path = repo_root / DATABASE_FILES_DIR / name

        if fmt not in NAME_KEYED_FORMATS:
            change_type = "modified" if cur_path.is_file() else "removed"
            changes.append({"file_name": name, "record_name": "*",
                             "change_type": change_type})
            continue

        cols = FILE_SCHEMAS.get(name, {}).get("columns")
        cur_records: dict[str, list[str]] = {}
        if cur_path.is_file():
            table = parse_name_keyed_table(cur_path, fmt, cols)
            cur_records = {r.name: r.fields for r in table.records}

        base_text = _git_show(repo_root, base_ref, f"{DATABASE_FILES_DIR}/{name}")
        base_records = (_record_map_from_text(base_text, name, fmt, cols)
                         if base_text else {})

        for rec_name in sorted(set(cur_records) | set(base_records)):
            in_cur, in_base = rec_name in cur_records, rec_name in base_records
            if in_cur and not in_base:
                change_type = "added"
            elif in_base and not in_cur:
                change_type = "removed"
            elif cur_records[rec_name] != base_records[rec_name]:
                change_type = "modified"
            else:
                continue  # unchanged
            changes.append({"file_name": name, "record_name": rec_name,
                             "change_type": change_type})

    return changes


# ---------------------------------------------------------------------------
# CSV sync
# ---------------------------------------------------------------------------

def _slug(record_name: str) -> str:
    return "all" if record_name == "*" else record_name


def sync(repo_root: Path, pr_number: str, pr_author: str, body: str,
         base_ref: str) -> list[dict]:
    """Detect changes vs base_ref and sync metadata/database_changes.csv to
    match. Returns the row(s) written for this PR (empty if the PR touches
    no recognized database file)."""
    fields = parse_pr_body(body)
    detected = detect_changes(repo_root, base_ref)

    csv_path = repo_root / METADATA_DIR / "database_changes.csv"
    existing_rows = []
    if csv_path.is_file():
        with open(csv_path, newline="", encoding="utf-8") as fh:
            existing_rows = list(csv.DictReader(fh))

    prefix = f"pr-{pr_number}-"
    preserved = {r["change_id"]: r for r in existing_rows
                 if r["change_id"].startswith(prefix)}
    kept = [r for r in existing_rows if not r["change_id"].startswith(prefix)]

    today = datetime.date.today().isoformat()
    new_rows = []
    for change in detected:
        change_id = f"{prefix}{change['file_name']}-{_slug(change['record_name'])}"
        prior = preserved.get(change_id)
        new_rows.append({
            "change_id": change_id,
            "file_name": change["file_name"],
            "record_name": change["record_name"],
            "change_type": change["change_type"],
            "date": prior["date"] if prior else today,
            "submitted_by": pr_author,
            "source": fields["source"],
            "reason": fields["reason"],
            "swatplus_version": fields["swatplus_version"],
            "editor_version": fields["editor_version"],
            "review_status": prior["review_status"] if prior else "pending",
            "notes": fields["notes"],
        })

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=REQUIRED_COLUMNS)
        w.writeheader()
        for r in kept + new_rows:
            w.writerow(r)

    return new_rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--base-ref", required=True,
                    help="Git ref/SHA to diff database_files/ against")
    args = ap.parse_args(argv)

    pr_number = os.environ.get("PR_NUMBER")
    pr_author = os.environ.get("PR_AUTHOR", "unknown")
    body = os.environ.get("PR_BODY") or ""

    if not pr_number:
        print("ERROR: PR_NUMBER environment variable is required")
        return 1

    rows = sync(Path(args.repo_root), pr_number, pr_author, body, args.base_ref)

    if not rows:
        print("No database_files/ changes detected in this PR; nothing to log.")
        return 0

    print(f"OK: synced {len(rows)} change-log row(s) for PR #{pr_number}:")
    for r in rows:
        print(f"  - {r['file_name']} :: {r['record_name']} ({r['change_type']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
