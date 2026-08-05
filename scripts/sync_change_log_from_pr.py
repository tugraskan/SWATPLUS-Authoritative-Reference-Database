#!/usr/bin/env python3
"""Generate metadata/database_changes.csv row(s) from a filled-out PR template.

Contributors fill in the pull request description
(`.github/pull_request_template.md`); they never hand-edit
`database_changes.csv`. This script parses that description and keeps the CSV
in sync with it, so it can be re-run every time the PR description changes.

Required fields (missing/blank -> validation error, CSV left untouched):
  Database file, Record, Change type (exactly one box checked), Reason, Source

Optional fields default sensibly: SWAT+ version / SWAT+ Editor version default
to "not_tested"; Notes defaults to empty.

`Record` may be a single stable record name, a comma-separated list (one
change-log row is created per name), or `*` for a file-wide change. Each row's
`change_id` is derived from the PR number (`pr-<number>`, or `pr-<number>-<i>`
for multiple records) so re-running this script for the same PR updates its
own row(s) in place rather than duplicating them; a row's `date` and
`review_status` are preserved across re-runs rather than reset.

Usage (normally invoked by .github/workflows/sync-change-log.yml, which sets
the environment variables from the pull_request event):
    PR_NUMBER=42 PR_AUTHOR=someone PR_BODY="$(cat body.md)" \
        python scripts/sync_change_log_from_pr.py --repo-root .
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import re
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "change_id", "file_name", "record_name", "change_type", "date",
    "submitted_by", "source", "reason", "swatplus_version", "editor_version",
    "review_status", "notes",
]

CHANGE_TYPE_CHOICES = ("Added", "Modified", "Deprecated", "Removed")


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


def _parse_change_type(sections: dict[str, str]) -> list[str]:
    raw = _strip_comments(sections.get("Change type", ""))
    pattern = "|".join(CHANGE_TYPE_CHOICES)
    return re.findall(rf"-\s*\[[xX]\]\s*({pattern})", raw)


def _parse_version_field(sections: dict[str, str], label: str) -> str:
    raw = _strip_comments(sections.get("Version notes", ""))
    # [^:\n]* and [ \t]* (not \s*) keep the match confined to a single line,
    # so the capture can't cross the newline into the next bullet's text.
    m = re.search(rf"{re.escape(label)}[^:\n]*:[ \t]*(.*)", raw)
    val = m.group(1).strip() if m else ""
    return val or "not_tested"


def parse_pr_body(body: str) -> tuple[list[dict], list[str]]:
    """Parse a PR body into change-log field values, or a list of errors.

    Returns (fields, errors). fields is a dict with keys: file_name,
    records (list[str]), change_type, reason, source, swatplus_version,
    editor_version, notes. Non-empty errors means fields is incomplete/invalid
    and must not be used to write a row.
    """
    sections = _parse_sections(body)

    file_name = _field_text(sections, "Database file")
    record_raw = _field_text(sections, "Record")
    change_types = _parse_change_type(sections)
    reason = _field_text(sections, "Reason")
    source = _field_text(sections, "Source")
    notes = _field_text(sections, "Notes")
    swatplus_version = _parse_version_field(sections, "SWAT+ version")
    editor_version = _parse_version_field(sections, "SWAT+ Editor version")

    errors = []
    if not file_name:
        errors.append("`Database file` is required (which file under "
                       "database_files/ is this PR changing?).")
    if not record_raw:
        errors.append("`Record` is required (a stable record name, "
                       "comma-separated names, or `*` for a file-wide change).")
    if len(change_types) == 0:
        errors.append("`Change type` is required: check exactly one box "
                       "(Added/Modified/Deprecated/Removed).")
    elif len(change_types) > 1:
        errors.append("`Change type`: check exactly ONE box, not multiple.")
    if not reason:
        errors.append("`Reason` is required: explain why this change is needed.")
    if not source:
        errors.append("`Source` is required: cite a publication, dataset, "
                       "documentation, GitHub issue, or a named subject-matter "
                       "expert.")

    if errors:
        return {}, errors

    records = [r.strip() for r in record_raw.split(",") if r.strip()] or ["*"]

    return {
        "file_name": file_name,
        "records": records,
        "change_type": change_types[0].lower(),
        "reason": reason,
        "source": source,
        "swatplus_version": swatplus_version,
        "editor_version": editor_version,
        "notes": notes,
    }, []


def build_rows(fields: dict, pr_number: str, pr_author: str,
                existing_rows: list[dict]) -> list[dict]:
    """Build this PR's change-log row(s), preserving date/review_status
    for any change_id that already existed."""
    prefix = f"pr-{pr_number}"
    preserved = {r["change_id"]: r for r in existing_rows
                 if r["change_id"] == prefix or r["change_id"].startswith(prefix + "-")}

    today = datetime.date.today().isoformat()
    records = fields["records"]
    rows = []
    for i, record in enumerate(records, start=1):
        change_id = prefix if len(records) == 1 else f"{prefix}-{i}"
        prior = preserved.get(change_id)
        rows.append({
            "change_id": change_id,
            "file_name": fields["file_name"],
            "record_name": record,
            "change_type": fields["change_type"],
            "date": prior["date"] if prior else today,
            "submitted_by": pr_author,
            "source": fields["source"],
            "reason": fields["reason"],
            "swatplus_version": fields["swatplus_version"],
            "editor_version": fields["editor_version"],
            "review_status": prior["review_status"] if prior else "pending",
            "notes": fields["notes"],
        })
    return rows


def sync(repo_root: Path, pr_number: str, pr_author: str, body: str) -> list[str]:
    """Parse `body` and sync metadata/database_changes.csv. Returns errors
    (empty list on success); the CSV is left untouched if there are errors."""
    fields, errors = parse_pr_body(body)
    if errors:
        return errors

    csv_path = repo_root / "metadata" / "database_changes.csv"
    existing_rows = []
    if csv_path.is_file():
        with open(csv_path, newline="", encoding="utf-8") as fh:
            existing_rows = list(csv.DictReader(fh))

    prefix = f"pr-{pr_number}"
    kept = [r for r in existing_rows
            if not (r["change_id"] == prefix or r["change_id"].startswith(prefix + "-"))]
    new_rows = build_rows(fields, pr_number, pr_author, existing_rows)

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=REQUIRED_COLUMNS)
        w.writeheader()
        for r in kept + new_rows:
            w.writerow(r)

    return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args(argv)

    pr_number = os.environ.get("PR_NUMBER")
    pr_author = os.environ.get("PR_AUTHOR", "unknown")
    body = os.environ.get("PR_BODY") or ""

    if not pr_number:
        print("ERROR: PR_NUMBER environment variable is required")
        return 1

    errors = sync(Path(args.repo_root), pr_number, pr_author, body)
    if errors:
        print("PR template incomplete:\n")
        for e in errors:
            print(f"  - {e}")
        print("\nFill in the missing section(s) above (edit the PR "
              "description) and this check will re-run.")
        return 1

    print(f"OK: synced change-log row(s) for PR #{pr_number}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
