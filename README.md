# SWAT+ Authoritative Reference Database

> The text files in this repository are the authoritative source for shared
> SWAT+ reference records. The core files were bootstrapped from the **official
> SWAT+ Editor reference dataset** (`swatplus_datasets.sqlite`) with the Editor's
> own file writers. That bootstrap snapshot matched the Editor byte for byte;
> accepted changes here may differ until the next upstream Editor sync. A small
> set of real SWAT+ files that the official dataset does not carry (the manure
> databases and a few others) are retained as clearly marked supplements.

This repository is the permanent, authoritative home for the shared SWAT+
reference database text files (`plants.plt`, `fertilizer.frt`, the manure
databases, decision tables, structural databases, and so on). It exists to make
every reference record traceable: where it came from, who changed it, why, and
which review accepted it. It also exists so the wider SWAT+ community has one
shared place to propose a new plant, fertilizer, tillage operation, or other
reference record — through an ordinary pull request — instead of every
modeling group maintaining and re-discovering the same corrections privately.

## Source of record: the official SWAT+ Editor dataset

* **The core files originated in the official dataset.** Each authoritative
  file under `database_files/` was bootstrapped from a table in the SWAT+
  Editor official reference dataset,
  `release/build/swatplus_datasets.sqlite` (**version 4.0.0**, **SWAT+ rev.
  62**), using the Editor's own `fileio` writers. The bootstrap snapshot was
  identical to what the Editor wrote into a project; later reviewed edits are
  intentionally preserved here until they are synced upstream.
* **This repository is authoritative for edits.** Curation and corrections
  happen here, through pull requests. Regeneration is only for adopting a new
  official dataset release.
* **Per-file bootstrap provenance** — which SQLite table each file came from,
  its original record count, and its original content checksum — is recorded in
  `internal/metadata/bootstrap_sources.json`.

## Proposing and changing records

1. Create a branch.
2. Edit the file under `database_files/`.
3. Open a pull request.

That's genuinely it. Nothing in the PR template is required — if you know a
reason or source for the change, the template has optional spots for them,
but a PR with neither still goes through cleanly. Opening the PR also runs
file validation, schema-drift checking, and the full test suite (that's what
the scripts and workflows under [`internal/`](internal/) are for). A reviewer
must approve before merge. `internal/CHANGELOG.md` is an ongoing history a
maintainer updates when it's worth summarizing, not something every PR
touches. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full rules.

## What's in here

```
database_files/     the authoritative SWAT+ reference text files
CONTRIBUTING.md      how to propose a change (start here)
internal/            everything else: metadata, schemas, scripts, tests, docs
  metadata/           manifest, provenance, schema-drift waivers
  schemas/            SWAT+ source-derived input schemas, one per SWAT+ release
  scripts/            validation, schema sync/diff, the patch-editor-dataset
                      sync tool
  tests/              unit + integration tests
  docs/               provenance report, editor-integration findings
  CHANGELOG.md         ongoing change history
  CONTRIBUTOR_GUIDE.md detailed contributor/maintainer rules
.github/              validation workflows, PR template
```

`.github/`, `LICENSE`, and `pyproject.toml` stay at the repository root because
GitHub and Python tooling only discover them there; everything else that isn't
the reference data or the top-level `README`/`CONTRIBUTING` lives under
`internal/`.

## Checked against what SWAT+ actually reads

`internal/schemas/swatplus-<version>.json` records, for every input database
file, the fields SWAT+ reads — name, Fortran type, units — in order. It is
generated from the SWAT+ Fortran source by
[`swatplus-doc-builder`](https://github.com/tugraskan/swatplus-doc-builder), and
`internal/scripts/schema_sync.py` compares it against this repository's data on
every pull request. That is what catches a file drifting out of step with the
model that consumes it, rather than discovering it during a run.

Known differences are recorded in `internal/metadata/schema_drift_waivers.json`
and reported on every run. **The one that matters today:** the official
dataset writes `plants.plt` ending at `rsd_covfac` + a free-text `description`,
while SWAT+ 62 reads four further carbon-module fields (`meta_frac`,
`str_frac`, `lig_frac`, `pl_class`). Those are on the conditional carbon-module
read path and default otherwise, so the file runs on the default/mainline path
exactly as SWAT+ Editor ships it. The gap is **waived** (tracked, not hidden)
until the editor dataset itself emits those columns. Separately, a review note
records that `pesticide.pes` carries the editor's uniform `0.01` `pl_uptake`
migration default rather than curated per-pesticide values.

## What counts as a "database file" here

A SWAT+ project reads on the order of **147 distinct input file types**
(per SWAT+ Editor's own file inventory, `file_cio_classification`). The large
majority of those — connectivity (`hru.con`, `channel.con`, ...), the physical
properties of a specific watershed's channels/reservoirs/aquifers, climate
station files, spatial region definitions, initial conditions, calibration
regions, and so on — are **project-specific**. They describe *one* model setup
and get regenerated by QSWAT+/the editor for every new project; there is
nothing to share, so they don't belong in a reference-data repository.

This repository carries only the other kind: **shared, name-keyed lookup
tables** whose values are reused as-is across projects — a plant named `corn`
or a tillage operation named `moldboard_plow` means the same thing in every
watershed. 33 files today:

26 from the official SWAT+ Editor dataset:

```
cal_parms.cal     chem_app.ops      cntable.lum       cons_practice.lum
fertilizer.frt    filterstrip.str   fire.ops          bmpuser.str
grassedww.str     graze.ops         harv.ops          irr.ops
ovn_table.lum     pesticide.pes     plants.plt        septic.sep
septic.str        snow.sno          sweep.ops         tiledrain.str
tillage.til       urban.urb         flo_con.dtl       lum.dtl
res_rel.dtl       scen_lu.dtl
```

7 supplemental — real SWAT+ inputs the official dataset doesn't carry (see
"Supplemental files" below):

```
manure_db.frt     manure_om.frt     transplant.plt    puddle.ops
salt.slt          pathogens.pth     metals.mtl
```

A filename appearing in `file.cio` is **not** proof a file is one of these
lookup tables, and conversely some lookup tables are read by SWAT+ under a
**hard-coded filename** that never appears in `file.cio` at all —
`manure_db.frt`, `manure_om.frt`, `puddle.ops`, and `transplant.plt` are read
this way (confirmed against `src/manure_db_read.f90`,
`src/manure_orgmin_read.f90`, `src/mgt_read_puddle.f90`, and
`src/plant_transplant_read.f90`). They are included here as **supplemental**
files because none of the four is managed by the SWAT+ Editor dataset — there
is no table for them in `swatplus_datasets.sqlite` — even though they are
exactly the kind of shared, name-keyed data this repository exists to hold.
`manure_db.frt` also references entries in `manure_om.frt` via its `org_min`
column; validation checks that every such reference resolves.

## Supplemental files (not in the official dataset)

Seven files are **real SWAT+ inputs that the official SWAT+ Editor dataset does
not carry**, so they cannot be regenerated from it. They are retained so no data
is lost, and their provenance is kept **separate** from the official-dataset
provenance in `internal/metadata/external_sources.json`:

| File | Why supplemental | Reproducible? | Status |
|---|---|---|---|
| `manure_db.frt` | direct-read DB; not managed by the editor dataset | yes (swatplus distribution) | available |
| `manure_om.frt` | direct-read DB; not managed by the editor dataset | yes (swatplus distribution) | available |
| `transplant.plt` | direct-read DB; not managed by the editor dataset | yes (swatplus distribution) | available |
| `puddle.ops` | direct-read DB; not managed by the editor dataset | yes (swatplus distribution) | available |
| `salt.slt` | no editor table; confirmed unread by SWAT+ 62 | no (maintainer) | available |
| `pathogens.pth` | editor table ships **empty**; example/seed values | no (maintainer) | needs_review |
| `metals.mtl` | no editor table; confirmed unread by SWAT+ 62 | no (maintainer) | needs_review (example/seed) |

**`salt.slt` and `metals.mtl` are confirmed unread by SWAT+ 62.** Both filenames
are declared in `input_file_module.f90` but referenced nowhere else in the
source — no subroutine opens either file, and the model's salt chemistry uses
hardcoded constants rather than reading `salt.slt`'s table. Their content
currently has zero effect on any simulation. See
`internal/metadata/schema_drift_waivers.json` for the full evidence.

Re-bootstrapping from a newer official dataset is a scripted, repeatable
operation: point SWAT+ Editor's `fileio` writers at the new
`swatplus_datasets.sqlite` and regenerate. Curating the `needs_review` files, or
adding any future new database file, is an ordinary edit through the normal
pull-request workflow above.

## Source versions are provenance, not tested compatibility

The regenerated files' headers name the official dataset's version and SWAT+
revision (SWAT+ Editor v4.0.0 / SWAT+ rev. 62). **This is source provenance
only.** It is *not* a claim that this data has been tested against
that SWAT+ or Editor version. No testing has been done against a specific
SWAT+/Editor version yet; if and when it is, record the result in the PR
description and, if worth calling out project-wide, in
`internal/CHANGELOG.md`.

## Syncing changes back to SWAT+ Editor

This repository doesn't publish its own versioned releases. There's no
independent audience downloading a ZIP of this data — the actual destination
for an accepted change is SWAT+ Editor's own `swatplus_datasets.sqlite`, and
that's a periodic, maintainer-driven step rather than a per-PR or scheduled
one:

1. Community PRs accumulate here — reviewed, validated, logged — same as
   always. Nothing further happens automatically after merge.
2. When a maintainer decides enough has accumulated to be worth syncing, they
   run `internal/scripts/patch_editor_dataset.py` against a local
   `swatplus-editor` checkout. It takes the editor's **current**
   `swatplus_datasets.sqlite`. It reads 24 official-dataset files from this
   repository: 20 map one-to-one to Editor tables, while the four `.dtl` files
   are loaded together as one decision-table group. It leaves every other
   owned table (soils, weather generator, and project config) untouched. The
   seven supplemental files are outside the patcher, and two official tables
   with known Editor-side reader bugs are explicitly skipped — see
   `internal/docs/editor_integration_findings.md`.
   Patch testing verified the touched data and confirmed the untouched tables
   stayed byte-for-byte identical.
3. The maintainer opens a pull request on `swat-model/swatplus-editor` with
   the resulting file. The editor team reviews and merges it like any other
   PR to their repo. It ships in their next release.

That patched `.sqlite` — not a ZIP of this repository — is the actual
deliverable. See `internal/CONTRIBUTOR_GUIDE.md` for how to run the sync.

## Not built here

* **No SQLite database is committed in this repository** — the source of
  record for the official data is SWAT+ Editor's `swatplus_datasets.sqlite`;
  this repository holds the human-readable, version-controlled text files
  originally regenerated from it (and, periodically, patched back into a copy
  of it — see above).
* **No changes are made to SWAT+ or SWAT+ Editor source code** as part of
  this repository's own automation. Submitting a patched dataset upstream is
  a deliberate, manual, maintainer-driven pull request, not something any
  automation here triggers on its own.
