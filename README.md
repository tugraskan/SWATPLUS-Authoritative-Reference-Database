# SWAT+ Authoritative Reference Database

> The text files in this repository are the authoritative source for shared
> SWAT+ reference records. The repository was initially populated from the
> official SWAT+ Ames_sub1 reference dataset, using the official SWAT+ Osu_1hru
> reference dataset only when an Ames file was unavailable. SWAT+ Editor
> integration and SQLite generation are planned future work and are not part of
> the current repository setup.

This repository is the permanent, authoritative home for the shared SWAT+
reference database text files (`plants.plt`, `fertilizer.frt`, the manure
databases, decision tables, structural databases, and so on). It exists to make
every reference record traceable: where it came from, who changed it, why, and
which release contains it.

## Authoritative after bootstrap

* After the initial bootstrap was reviewed, **this repository is
  authoritative**. Edits happen here, through pull requests.
* **Ames was used first, OSU second.** During bootstrap each expected file was
  taken from `refdata/Ames_sub1`; `refdata/Osu_1hru` was used only when Ames
  lacked the file.
* **Upstream datasets are provenance only.** Normal validation and releases use
  the files committed here. Workflows never pull live files from Ames or OSU,
  and upstream files never silently overwrite authoritative files.

The pinned bootstrap source is `swat-model/swatplus` @
`cb442f7c05fc3bfc34349c446010f452d2737ca0`.

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
reported on every run. **One matters today:** `pesticide.pes` gained a
`pl_uptake` column to match SWAT+ 62, but every one of its 233 values is a
`0.0` placeholder, not a real measurement — the file is `needs_review` until
the SWAT+ team provides approved per-pesticide values. See that file for the
detail and what would resolve it.

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

`puddle.ops` and `transplant.plt` were **discovered during this inspection** and
are not in the original expected-file list; they are included here as
authoritative direct-read databases. See `docs/source_inventory.md`.

## Why the manure files are included

`manure_db.frt` and `manure_om.frt` are read directly by SWAT+ and are central
to manure handling. `manure_db.frt` references entries in `manure_om.frt` via its
`org_min` column; validation checks that every such reference resolves.

## Externally supplied files

Five expected files had no approved Ames/OSU source and were supplied from
outside those sources. Their provenance is kept **separate** from bootstrap
provenance in `metadata/external_sources.json`:

| File | Origin | Reproducible? | Status |
|---|---|---|---|
| `flo_con.dtl` | `biopsichas/soft_cal_crop_paper` @ `f58c684` | yes (public commit) | available |
| `salt.slt` | maintainer local drive | no | available |
| `scen_lu.dtl` | maintainer's internal NAM HUC8 model run (`12070204.accdb`) | no | available |
| `pathogens.pth` | maintainer local drive | no | needs_review (example/seed) |
| `metals.mtl` | maintainer local drive | no | needs_review (example/seed) |

Every expected file now has an authoritative source; none remain unavailable.

The scripts that performed the one-time inventory, bootstrap, and external
import (`inventory_reference_files.py`, `bootstrap_database_files.py`,
`import_external_files.py`) have been removed now that the initial import is
complete and merged — they have no further job to do, and their logic is
preserved in git history if a future re-bootstrap (e.g. against a newer
pinned SWAT+ commit) is ever needed. Curating the `needs_review` files, or
adding any future new database file, is an ordinary edit through the normal
pull-request workflow below — no special tooling required.

## Source versions are provenance, not tested compatibility

Each bootstrapped file's header may name a SWAT+ Editor version and SWAT+
revision (e.g. Editor 2.3.3 / rev 60.5.7). **This is source provenance only.**
It is *not* a claim that a database release has been tested against that SWAT+ or
Editor version. `metadata/compatibility_matrix.csv` records real test status,
which is `not_tested` in this phase. Some files (e.g. Ames `tillage.til`) carry
no version header; those are recorded as `null`, never guessed.

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
python scripts/validate_change_log.py --repo-root .
python -m pytest -q
```

## Releases

Releases are versioned `YEAR.MAJOR.MINOR` (see `DATABASE_VERSION`, currently
`2026.1.0`) and tagged `database-v<version>`. Pushing such a tag runs validation
and tests, verifies the tag matches `DATABASE_VERSION`, and publishes a
text-file ZIP with metadata and checksums. To build a package locally:

```bash
python scripts/build_release_package.py --repo-root .
```

The first release, **[`database-v2026.1.0`][rel]**, is published with the
text-file ZIP (`swatplus-authoritative-reference-database-2026.1.0.zip`),
`database_manifest.json`, and `checksums.txt` attached. Compatibility test
status is `not_tested` (source-file header versions are provenance only).

[rel]: https://github.com/tugraskan/SWATPLUS-Authoritative-Reference-Database/releases/tag/database-v2026.1.0

## Not built yet

* **No SQLite database** is built or committed in this phase.
* **SWAT+ Editor integration is future work** (see
  `docs/editor_integration_findings.md`).
* **No changes are made to SWAT+ or SWAT+ Editor** as part of this workflow.
