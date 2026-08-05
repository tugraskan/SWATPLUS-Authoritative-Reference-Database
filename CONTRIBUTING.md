# Contributing

Thank you for helping maintain the SWAT+ authoritative reference database. All
changes to authoritative data go through branches and pull requests so that
every record stays traceable and validated.

## Branch and pull-request workflow

1. Create a branch off `main`.
2. Modify the appropriate file under `database_files/`.
3. Open a pull request using the template and fill in every section.
4. A reviewer must approve; automated validation must pass before merge.

You do **not** need to hand-edit `metadata/database_changes.csv`. The
`sync-change-log` check reads your filled-out PR description and commits the
matching row onto your branch for you — see "The PR template is the
change-log" below. `CHANGELOG.md` is a release-level summary a maintainer
writes when cutting a release, not something every PR updates.

Branch protection on `main` is recommended (require PR review + passing
`validate-database` and `sync-change-log` checks). Do **not** commit directly
to `main`.

Ordinary database-row changes do **not** require a SWAT+ Editor code change or an
Editor pull request.

## Technical or scientific source is required

Every added or modified record must cite a real source: a publication, dataset,
official documentation, a GitHub issue, or a named subject-matter expert. "It
looked right" is not a source. Do not invent scientific values.

## The PR template is the change-log

Fill in every section of the PR template — `Database file`, `Record`,
`Change type`, `Reason`, `Source`, and (if known) the version notes. The
`sync-change-log` workflow parses your description and writes the matching row
into `metadata/database_changes.csv` for you, then commits it onto your PR
branch. If a required field is missing, blank, or `Change type` doesn't have
exactly one box checked, that check fails and tells you which field to fix;
editing the PR description re-runs it.

A few things worth knowing about how the row is built:

* **`Record`** accepts a single stable name, a comma-separated list (one row
  is created per name), or `*` for a file-wide change.
* **`change_id`** is derived from the PR number (`pr-<number>`, or
  `pr-<number>-<n>` when multiple records are listed) — you never choose one.
* Editing the PR description **updates that PR's row in place** rather than
  adding a duplicate; a row's `date` and `review_status` are preserved across
  edits.
* **`review_status`** starts `pending` and reflects that the row was
  auto-generated, not yet human-reviewed; the merged, approved PR is itself
  the approval record.
* **`swatplus_version` / `editor_version`** default to `not_tested` if left
  blank. Do not claim tested compatibility that hasn't happened.
* **Fork pull requests**: the workflow can't push a commit onto a branch it
  doesn't own, so the required-field check still runs, but a maintainer will
  need to add the row (or push it on your behalf) before merge.

Every new or modified authoritative record still needs a corresponding entry —
that coverage is checked by `scripts/validate_change_log.py` against the pull
request's merge base, independently of how the row was created. (A
`metadata/bootstrap_exception` marker file, if present, skips that per-record
coverage — used only for a wholesale dataset import, not ordinary edits.)

`metadata/database_changes.csv` columns, for reference:

```
change_id,file_name,record_name,change_type,date,submitted_by,source,reason,
swatplus_version,editor_version,review_status,notes
```

`change_type` is one of `added`, `modified`, `deprecated`, `removed`;
`change_id` must be unique; `reason` and `source` are required for `added` /
`modified` — all enforced whether the row came from the template or was
edited by hand.

## Stable row keys

Use the record **name** (or another stable key) as a record's identity — never a
line number. Renaming a record is a `removed` + `added` pair, documented as such.

## Filename rules

* Use `fire.ops` — never `burn.ops`.
* Use `pesticide.pes` — the canonical text filename used by SWAT+ source and the
  reference projects. (The SQLite model name may differ; that does not change the
  text filename. See `docs/editor_integration_findings.md`.)
* Filename case must match the manifest exactly.
* Never commit a SQLite database as an authoritative source.

## Column schemas, and what to do when SWAT+ changes a file's format

Every name-keyed database file has an entry in `FILE_SCHEMAS`
(`scripts/swat_config.py`) listing its columns in order and which of them must
be numeric. That entry is what lets validation catch a row with the wrong
number of columns, a text value where a number belongs, or a header row that no
longer matches the file. A test enforces that **every** name-keyed file has a
schema, so adding a new database file means adding its schema in the same pull
request.

A schema entry supports:

* `columns` — the column names, in order, exactly as they appear in the file's
  header row.
* `numeric` — indices (0-based) of columns whose values must parse as numbers.
* `text_tail` — set when the **last** column is free text (a `description`).
  Such a column may contain spaces or be left empty, so the row is required to
  have at least `len(columns) - 1` fields rather than an exact count.

If validation reports:

```text
ERROR: <file>, line 2: column header does not match the expected schema: ...
```

then the file's format no longer matches what this repository expects. That is
almost always one of two things:

1. **The header was damaged** in editing — fix the file.
2. **An upstream SWAT+ release changed the format** (added, removed, or renamed
   a column, or changed a column's type). In that case:
   * update the file's `FILE_SCHEMAS` entry to the new layout;
   * fill in the PR template as a file-wide `modified` change (`Record: *`),
     with `Source`/`Reason` naming which SWAT+ release changed it, so the
     schema change can be traced to a version;
   * do not silently widen a schema to make an error go away — a column count
     that drifts without explanation is exactly the failure this check exists
     to surface.

## Adopting a new SWAT+ release (the schema cadence)

`schemas/swatplus-<version>.json` describes, for every input database file,
the fields SWAT+ actually **reads** — name, Fortran type, and units — in order.
It is generated from the SWAT+ Fortran source by
[`swatplus-doc-builder`](https://github.com/tugraskan/swatplus-doc-builder);
it is not hand-written here. `scripts/schema_sync.py` compares it against our
schemas and our data on every pull request.

When a new SWAT+ version is approved:

1. Regenerate the artifact in `swatplus-doc-builder` for that release and copy
   it into `schemas/`.
2. Run the diff to see exactly what changed:

   ```bash
   python scripts/schema_diff.py --from 62.0.0 --to <new> --repo-root .
   ```

3. Paste that output into the pull request. Pay particular attention to
   **moved** fields: a reordered read assigns existing values to different
   variables, so data that still parses can silently become wrong.
4. Update `FILE_SCHEMAS` for each changed file and update the affected data
   files. The PR template covers one file per pull request (`Record: *` for a
   file-wide format change) — a release that changes several files' formats at
   once means either one pull request per file, or a maintainer adding the
   extra rows to `metadata/database_changes.csv` by hand. If you add rows by
   hand for a PR the sync workflow is also managing, give them a `change_id`
   that does **not** start with `pr-<that PR's number>` (e.g. `sft-migration-
   62-soils`, not `pr-50-soils`) — the workflow deletes and regenerates every
   row whose `change_id` starts with `pr-<number>` on each sync, and cannot
   tell your hand-added row from its own.
5. Run `python scripts/schema_sync.py --repo-root .` until it is clean.

### Why our column counts differ from the artifact

Our schemas count the columns in a file's **header row**. The artifact counts
the fields SWAT+ **consumes**. These differ legitimately: SWAT+ reads each
record with list-directed I/O over a whole derived type, so any column beyond
the last component — usually a free-text `description` — is never read. 14
files are in this state and are correct as they are.

The reverse is not benign. If a file supplies **fewer** columns than SWAT+
reads, list-directed input does not stop at the end of the line: it keeps
consuming to satisfy the remaining variables, so SWAT+ reads the next record's
tokens into the current one. `schema_sync.py` reports this as `underfilled`
and fails.

### Waivers and review notes

`metadata/schema_drift_waivers.json` holds two kinds of entry:

* **`waivers`** — drift that is known and awaiting a decision. A waiver stops
  CI failing but does **not** hide the finding; every run still prints it with
  its reason. Add one only with an `action_required` describing what would
  resolve it, and remove it as soon as the data is fixed.
* **`review_notes`** — findings that the tooling cannot detect on its own. An
  extra column inserted *mid-row* is the important case: it shifts every later
  value into the wrong variable, silently and with plausible numbers. Text
  column names do not map to Fortran component names by any reliable rule
  (`falltmp`/`fall_tmp`, but also `timp`/`tmp_lag`), so this is found by human
  inspection and recorded here to keep it visible.

## Version notes and compatibility status

Source-file header versions describe **provenance**, not tested compatibility.
Record real test outcomes only in `metadata/compatibility_matrix.csv`, using
`not_tested`, `passed`, or `failed`. Leave test dates/suites blank unless a test
actually ran.

## Validation commands

These all run automatically in CI on every pull request — you don't need to
run them yourself. If you want faster feedback while iterating on a change
than waiting for CI, you can run the same checks locally:

```bash
python scripts/validate_database_files.py --repo-root .
python scripts/validate_change_log.py --repo-root .
python scripts/schema_sync.py --repo-root .
python -m pytest -q
```

## Review expectations

Reviewers confirm: a source was provided, the auto-generated change-log row
matches the actual data change, no duplicate record names were introduced,
filenames follow the rules above, and no unrelated SWAT+ or SWAT+ Editor
changes are bundled in.
