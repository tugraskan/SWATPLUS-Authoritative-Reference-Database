# SWAT+ Editor Integration Findings (read-only)

> This repository setup phase does not modify SWAT+ Editor. Editor integration,
> SQLite generation, project database copying, and TxtInOut export are deferred
> to a future implementation.

The notes below summarize **read-only** observations of
`swat-model/swatplus-editor` gathered while setting up this repository. Nothing
in the Editor was changed, and no Editor pull request was opened.

## Canonical pesticide filename: `pesticide.pes` (resolved)

The authoritative repository uses **`pesticide.pes`**. This is the text filename
used by current SWAT+ source and the reference projects (`Ames_sub1`,
`Osu_1hru`), and it is confirmed in the Editor itself:

* `src/api/database/datasets/setup.py` maps the text file to a SQLite table:

  ```python
  {'default_file_name': 'pesticide.pes', 'database_table': 'pesticide_pst', ...}
  ```

So the **text filename is `pesticide.pes`** while the **SQLite model/table name
is `pesticide_pst`**. These intentionally differ; the SQLite model name does not
have to match the text filename. This repository standardizes on the text
filename `pesticide.pes` and validation rejects a `pesticide.pst` text file.

## Existing Editor architecture (observed)

* Peewee + SQLite, with a **datasets** layer (`src/api/database/datasets/`) and a
  **project** layer (`src/api/database/project/`).
* A shipped **`swatplus_datasets.sqlite`** provides seed reference data; the
  Editor checks/updates its version (`datasets/setup.py: check_version`) and asks
  users to update the datasets file when out of date.
* `datasets/setup.py` carries a table registry mapping each reference text file
  to its SQLite table (the `default_file_name` / `database_table` pairs).
* The project layer copies tables from the datasets DB into a project DB
  (e.g. `project/setup.py: lib.copy_table('pesticide_pst', ...)`).

## Known gaps for a future integration

* **Manure:** the Editor's `database/` layer has essentially no
  `manure_db.frt` / `manure_om.frt` model or import/export support. Future
  integration would need to add these models and readers/writers.
* **Newly included direct-read databases:** `puddle.ops` and `transplant.plt`
  have **no** corresponding Editor models (no references found in the Editor
  source). Future integration would need table models and import/export for
  them.
* **Optional / external files:** `pathogens.pth`, `metals.mtl`, `salt.slt`, and
  `flo_con.dtl` would each need mapping decisions (table names, whether they ship
  in `swatplus_datasets.sqlite`, and how `needs_review` example data is handled).

## Likely future integration points

1. Extend the `datasets/setup.py` table registry to cover every authoritative
   file in this repository (including the manure and direct-read databases).
2. Generate / update `swatplus_datasets.sqlite` from a validated authoritative
   release ZIP produced by this repository.
3. Add missing Peewee models and import/export (TxtInOut) support.
4. Copy the relevant tables into the project database during project setup.

## Questions requiring SWAT+ team approval

* Which authoritative files should ship inside `swatplus_datasets.sqlite`, and at
  what dataset version?
* Table naming for the manure and newly discovered direct-read databases.
* Handling of `needs_review` example data (`pathogens.pth`, `metals.mtl`) — ship,
  omit, or replace with curated values first.
* The process and cadence for regenerating the datasets SQLite from an
  authoritative release.

## SWAT+ source divergence: the NAM variant

This repository's bootstrap and every schema check are pinned to
`swat-model/swatplus` @ `cb442f7c05fc3bfc34349c446010f452d2737ca0` (SWAT+
revision 62) -- the public mainline. Several files supplied for this
repository, however, trace back to an internal **NAM (National Assessment
Model)** SWAT+ project run (`scen_lu.dtl`'s header records
`M:\Constructor\HUC8_models\models\12070204.accdb`).

Auditing `scen_lu.dtl` against the mainline source found two of its action
keywords, `tillage` and `ch_change`, used the wrong mainline spelling and were
corrected to `till` / `chan_change`. A third, `ceap_svi`, has **zero matches
anywhere** in the mainline source tree -- not as an action, not as a
condition, not even as a substring (checked for `svi`, `vuln` too). Unlike the
other two, no plausible mainline replacement exists.

The most likely explanation is that `ceap_svi` (CEAP surface vulnerability
index) is a real action/condition type in whatever SWAT+ build the NAM project
actually runs, and that build carries source changes beyond the
`swat-model/swatplus` mainline this repository tracks. That is speculation,
not confirmed -- this repository has no access to a NAM-specific SWAT+ source
tree to check against.

**This has a real consequence for future releases.** If the NAM SWAT+ variant
has action/condition types, file formats, or database structures that differ
from mainline, then a single authoritative release pinned only to mainline
cannot correctly serve both audiences. A NAM-consuming project would need
either:

* its own authoritative release tagged against the NAM source revision, with
  its own schema artifacts and validation, tracked separately from the
  mainline-pinned release this repository currently produces; or
* confirmation that the NAM variant's action vocabulary is a strict superset
  of mainline's (i.e. NAM adds keywords like `ceap_svi` but never removes or
  renames a mainline one), in which case a single release could serve both,
  with NAM-only keywords simply undetectable by mainline-derived schema
  checks rather than incorrect.

Determining which of these is true requires visibility into the NAM SWAT+
source that this repository does not currently have. See
`metadata/schema_drift_waivers.json` (`scen_lu.dtl` entry) for the specific
unresolved keyword this surfaced.

## Explicitly out of scope now

Generating `swatplus_datasets.sqlite`, adding Editor table models, adding manure
readers/writers, packaging the database with the Editor, project initialization,
writing TxtInOut files, and submitting any SWAT+ Editor pull request are all
deferred to a future implementation and are **not** part of this repository's
current workflow.
