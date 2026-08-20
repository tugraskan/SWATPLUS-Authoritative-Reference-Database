# Contributor & Maintainer Guide (detail)

This is the detailed half of [`CONTRIBUTING.md`](../CONTRIBUTING.md), split out
because most contributors proposing a single record change don't need any of
it — read the root `CONTRIBUTING.md` first. This file is for adopting a new
SWAT+ release, changing a file's schema, reviewing PRs, or working on the
validation tooling itself.

## What tracks a change, and what doesn't

Nothing here is required in the PR template. `Reason` and `Source` are the
only fields a contributor might fill in, and both are optional. What actually
records a change is the ordinary git/GitHub trail: the commit history, the
PR diff, and the PR description/discussion are the change log — there is no
separate file to keep in sync with them. If you want to look up what changed
in a given file and why, `git log -p -- database_files/<file>` and the PRs
that touched it are the source of truth.

## Column schemas, and what to do when SWAT+ changes a file's format

Every name-keyed database file has an entry in `FILE_SCHEMAS`
(`internal/scripts/swat_config.py`) listing its columns in order and which of
them must be numeric. That entry is what lets validation catch a row with the
wrong number of columns, a text value where a number belongs, or a header row
that no longer matches the file. A test enforces that **every** name-keyed
file has a schema, so adding a new database file means adding its schema in
the same pull request.

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
   * name, in the PR description, which SWAT+ release changed it, so the
     schema change can be traced to a version;
   * do not silently widen a schema to make an error go away — a column count
     that drifts without explanation is exactly the failure this check exists
     to surface.

## Adopting a new SWAT+ release (the schema cadence)

`internal/schemas/swatplus-<version>.json` describes, for every input database
file, the fields SWAT+ actually **reads** — name, Fortran type, and units — in
order. It is generated from the SWAT+ Fortran source by
[`swatplus-doc-builder`](https://github.com/tugraskan/swatplus-doc-builder);
it is not hand-written here. `internal/scripts/schema_sync.py` compares it
against our schemas and our data on every pull request.

When a new SWAT+ version is approved:

1. Regenerate the artifact in `swatplus-doc-builder` for that release and copy
   it into `internal/schemas/`.
2. Run the diff to see exactly what changed:

   ```bash
   python internal/scripts/schema_diff.py --from 62.0.0 --to <new> --repo-root .
   ```

3. Paste that output into the pull request. Pay particular attention to
   **moved** fields: a reordered read assigns existing values to different
   variables, so data that still parses can silently become wrong.
4. Update `FILE_SCHEMAS` for each changed file and update the affected data
   files. Note in the PR description which SWAT+ release drove the change,
   even if the migration only renames/reorders headers without changing any
   record's actual values — the PR is the record of the schema change.
5. Run `python internal/scripts/schema_sync.py --repo-root .` until it is
   clean.

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

`internal/metadata/schema_drift_waivers.json` holds two kinds of entry:

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
No file's header being SWAT+ Editor v4.0.0 / SWAT+ rev. 62 is a claim that a
change has been tested against that version. If you do test a change against
a specific SWAT+/Editor version, say so — and what the result was — in the PR
description; do not claim tested compatibility that hasn't happened.

## Validation commands

These all run automatically in CI on every pull request. If you want faster
feedback while iterating on a change than waiting for CI, you can run the
same checks locally:

```bash
python internal/scripts/validate_database_files.py --repo-root .
python internal/scripts/schema_sync.py --repo-root .
python -m pytest -q
```

## Review expectations

Reviewers confirm: the diff matches what the PR description says changed and
why, no duplicate record names were introduced, filenames follow the rules in
`CONTRIBUTING.md`, and no unrelated SWAT+ or SWAT+ Editor changes are bundled
in.

## Syncing accepted changes to SWAT+ Editor

This repository does not publish its own versioned releases -- there's no
audience downloading a ZIP of this data. The real destination for an
accepted change is SWAT+ Editor's own `swatplus_datasets.sqlite`, and getting
it there is a periodic, maintainer-run step, not something any automation
here triggers.

When it's time to sync (no fixed cadence -- whenever enough has accumulated
to be worth a PR to the editor team):

1. Get a local checkout of `swat-model/swatplus-editor` and its current
   `release/build/swatplus_datasets.sqlite`.
2. Run:

   ```bash
   python internal/scripts/patch_editor_dataset.py \
       --editor-repo /path/to/swatplus-editor \
       --editor-sqlite /path/to/swatplus-editor/release/build/swatplus_datasets.sqlite \
       --output /path/to/patched_swatplus_datasets.sqlite \
       --repo-root .
   ```

   This copies the editor's current dataset and reads 24 official-dataset
   files from this repository: 20 map one-to-one to Editor tables, and the
   four `.dtl` files are loaded together as one decision-table group (see
   `EXCLUDED_TABLES` and `build_jobs()` in the script for the exact list).
   Every other table -- soils, weather generator, project config, the seven
   supplemental files, and the two official tables the script deliberately
   skips (see below) -- is left byte-for-byte untouched. The script prints a
   before/after row count for every table group it touches; review that output
   before doing anything with the result.
3. Open a pull request on `swat-model/swatplus-editor` replacing
   `release/build/swatplus_datasets.sqlite` with the patched file. Since a
   binary can't be reviewed line-by-line, describe in the PR body which of
   *this* repository's merged PRs are included -- `git log --merges` (or the
   list of closed PRs on GitHub) since the last sync is the list.
4. The editor team reviews and merges it like any other change to their
   repo. It ships in their next release.

**Two tables are deliberately never patched:** `septic_sep` and
`cal_parms_cal`. Both have real bugs in `swatplus-editor`'s own reader code
(`Septic_sep.read()` expects a column that doesn't exist in the real schema;
`Cal_parms_cal.read()` force-lowercases names, which would rename three real
mixed-case parameters) -- see `internal/docs/editor_integration_findings.md`
for the evidence. These are bugs in the editor, not something to route around
here; once fixed upstream, remove them from `EXCLUDED_TABLES` in the script.

This tool requires a local `swatplus-editor` checkout to import its peewee
models and file readers, so it is not wired into this repository's CI --
CI has no editor checkout to run it against.
