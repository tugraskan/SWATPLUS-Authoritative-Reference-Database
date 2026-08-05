# SWAT+ Authoritative Reference Database

> The text files in this repository are the authoritative source for shared
> SWAT+ reference records. The core files are regenerated from the **official
> SWAT+ Editor reference dataset** (`swatplus_datasets.sqlite`), serialized with
> SWAT+ Editor's own file writers, so each file matches — byte for byte — what
> SWAT+ Editor ships into every new project. A small set of real SWAT+ files
> that the official dataset does not carry (the manure databases and a few
> others) are retained as clearly-marked supplements.

This repository is the permanent, authoritative home for the shared SWAT+
reference database text files (`plants.plt`, `fertilizer.frt`, the manure
databases, decision tables, structural databases, and so on). It exists to make
every reference record traceable: where it came from, who changed it, why, and
which release contains it.

## Source of record: the official SWAT+ Editor dataset

* **The core files come from the official dataset.** Each authoritative file
  under `database_files/` was regenerated from a table in the SWAT+ Editor
  official reference dataset, `release/build/swatplus_datasets.sqlite`
  (**version 4.0.0**, **SWAT+ rev. 62**), using the editor's own `fileio`
  writers. That is the same dataset SWAT+ Editor copies into a project as its
  reference database, so the authoritative files here are identical to what a
  user gets from the editor.
* **This repository is authoritative for edits.** Curation and corrections
  happen here, through pull requests. Regeneration is only for adopting a new
  official dataset release.
* **Per-file provenance** — which sqlite table each file came from, its record
  count, and a content checksum — is recorded in
  `metadata/bootstrap_sources.json`.

> **History:** the repository was *initially* bootstrapped from the
> `Ames_sub1` / `Osu_1hru` datasets in `swat-model/swatplus`. Those are
> **model-specific watershed inputs**, not the official shared reference
> dataset, so they diverged from what SWAT+ Editor distributes (for example the
> official `plants.plt` has 266 records; the Ames file had 126). That import was
> replaced by this re-bootstrap from the official dataset in release `2026.2.0`.
> The earlier provenance is preserved in git history and `CHANGELOG.md`.

## What's in here

```
database_files/     the authoritative SWAT+ reference text files
metadata/           manifest, provenance, change log, compatibility matrix,
                    exclusions, schema-drift waivers
schemas/            SWAT+ source-derived input schemas, one per SWAT+ release
scripts/            validation, schema sync/diff, change-log validation, release
tests/              unit + integration tests
docs/               source inventory, bootstrap report, editor-integration findings
.github/            validation + release workflows, PR template
```

## Checked against what SWAT+ actually reads

`schemas/swatplus-<version>.json` records, for every input database file, the
fields SWAT+ reads — name, Fortran type, units — in order. It is generated from
the SWAT+ Fortran source by
[`swatplus-doc-builder`](https://github.com/tugraskan/swatplus-doc-builder), and
`scripts/schema_sync.py` compares it against this repository's data on every
pull request. That is what catches a file drifting out of step with the model
that consumes it, rather than discovering it during a run.

Known differences are recorded in `metadata/schema_drift_waivers.json` and
reported on every run. **The one that matters today:** the official dataset
writes `plants.plt` ending at `rsd_covfac` + a free-text `description`, while
SWAT+ 62 reads four further carbon-module fields (`meta_frac`, `str_frac`,
`lig_frac`, `pl_class`). Those are on the conditional carbon-module read path
and default otherwise, so the file runs on the default/mainline path exactly as
SWAT+ Editor ships it. The gap is **waived** (tracked, not hidden) until the
editor dataset itself emits those columns. Separately, a review note records
that `pesticide.pes` carries the editor's uniform `0.01` `pl_uptake` migration
default rather than curated per-pesticide values.

## Why `file.cio` alone is not enough for discovery

A filename appearing in `file.cio` is **not** proof the file exists, and some
databases are read by SWAT+ under a **hard-coded filename** that never appears
in the `file.cio` database list. Inspecting the SWAT+ source
(`src/proc_db.f90` and the individual readers) shows four such direct-read
databases:

| File | Reader | Included because |
|---|---|---|
| `manure_db.frt` | `src/manure_db_read.f90` | direct-read (`inquire(file="manure_db.frt")`) |
| `manure_om.frt` | `src/manure_orgmin_read.f90` | direct-read |
| `puddle.ops` | `src/mgt_read_puddle.f90` | direct-read |
| `transplant.plt` | `src/plant_transplant_read.f90` | direct-read |

None of these four is managed by the SWAT+ Editor dataset (there is no table for
them in `swatplus_datasets.sqlite`), so they cannot be regenerated from it. They
are retained as **supplemental** direct-read databases (see below and
`docs/source_inventory.md`).

## Why the manure files are included

`manure_db.frt` and `manure_om.frt` are read directly by SWAT+ and are central
to manure handling. `manure_db.frt` references entries in `manure_om.frt` via its
`org_min` column; validation checks that every such reference resolves.

## Supplemental files (not in the official dataset)

Seven files are **real SWAT+ inputs that the official SWAT+ Editor dataset does
not carry**, so they cannot be regenerated from it. They are retained unchanged
from the earlier import so no data is lost, and their provenance is kept
**separate** from the official-dataset provenance in
`metadata/external_sources.json`:

| File | Why supplemental | Reproducible? | Status |
|---|---|---|---|
| `manure_db.frt` | direct-read DB; not managed by the editor dataset | yes (swatplus refdata) | available |
| `manure_om.frt` | direct-read DB; not managed by the editor dataset | yes (swatplus refdata) | available |
| `transplant.plt` | direct-read DB; not managed by the editor dataset | yes (swatplus refdata) | available |
| `puddle.ops` | direct-read DB; not managed by the editor dataset | yes (swatplus refdata) | available |
| `salt.slt` | no editor table; confirmed unread by SWAT+ 62 | no (maintainer) | available |
| `pathogens.pth` | editor table ships **empty**; example/seed values | no (maintainer) | needs_review |
| `metals.mtl` | no editor table; confirmed unread by SWAT+ 62 | no (maintainer) | needs_review (example/seed) |

**`salt.slt` and `metals.mtl` are confirmed unread by SWAT+ 62.** Both filenames
are declared in `input_file_module.f90` but referenced nowhere else in the
source — no subroutine opens either file, and the model's salt chemistry uses
hardcoded constants rather than reading `salt.slt`'s table. Their content
currently has zero effect on any simulation. See
`metadata/schema_drift_waivers.json` for the full evidence.

Re-bootstrapping from a newer official dataset is a scripted, repeatable
operation: point SWAT+ Editor's `fileio` writers at the new
`swatplus_datasets.sqlite` and regenerate. Curating the `needs_review` files, or
adding any future new database file, is an ordinary edit through the normal
pull-request workflow below.

## Source versions are provenance, not tested compatibility

The regenerated files' headers name the official dataset's version and SWAT+
revision (SWAT+ Editor v4.0.0 / SWAT+ rev. 62). **This is source provenance
only.** It is *not* a claim that a database release has been tested against that
SWAT+ or Editor version. `metadata/compatibility_matrix.csv` records real test
status, which is `not_tested` in this phase.

## Proposing and changing records

1. Create a branch.
2. Edit the file under `database_files/`.
3. Add a row to `metadata/database_changes.csv` (stable record name, reason,
   scientific/technical source).
4. Update `CHANGELOG.md` when appropriate.
5. Run validation locally (below) and open a pull request.

See `CONTRIBUTING.md` for the full rules. Branch protection on `main` is
recommended so every change is reviewed and validated.

## Running validation locally

```bash
python scripts/validate_database_files.py --repo-root .
python scripts/schema_sync.py --repo-root .
python scripts/validate_change_log.py --repo-root .
python -m pytest -q
```

## Releases

Releases are versioned `YEAR.MAJOR.MINOR` (see `DATABASE_VERSION`, currently
`2026.2.0`) and tagged `database-v<version>`. Pushing such a tag runs validation
and tests, verifies the tag matches `DATABASE_VERSION`, and publishes a
text-file ZIP with metadata and checksums. To build a package locally:

```bash
python scripts/build_release_package.py --repo-root .
```

## Not built here

* **No SQLite database** is built or committed in this repository — the source
  of record for the official data is SWAT+ Editor's `swatplus_datasets.sqlite`;
  this repository holds the human-readable, version-controlled text files
  regenerated from it.
* **No changes are made to SWAT+ or SWAT+ Editor** as part of this workflow.
