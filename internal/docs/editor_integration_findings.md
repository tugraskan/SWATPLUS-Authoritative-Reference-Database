# SWAT+ Editor Integration Findings (read-only)

> The authoritative core files are serialized **from** the official SWAT+
> Editor reference dataset (`swatplus_datasets.sqlite`, v4.0.0, SWAT+ rev. 62)
> using the editor's own `fileio` writers. This is a **read-only** use of SWAT+
> Editor: no Editor code was changed and no Editor pull request was opened.

The notes below summarize **read-only** observations of
`swat-model/swatplus-editor`.

## Canonical pesticide filename: `pesticide.pes` (resolved)

The authoritative repository uses **`pesticide.pes`**. This is the text filename
used by current SWAT+ source, and it is confirmed in the Editor itself:

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

## Reader/data inconsistencies found (2026-08-05, via patch testing)

Proving out a "patch the editor's sqlite from our text" workflow (see below)
surfaced two real bugs in `swatplus-editor`'s own code — both independent of
anything in this repository, and both reproducible against the editor's own
currently-shipped data:

* **`Septic_sep.read()` (`src/api/fileio/hru_parm_db.py`) expects 13
  whitespace-delimited columns in `septic.sep`.** The actual `septic_sep`
  table schema has 12 real data columns (`name` through `description`; 13
  including `id`, which isn't in the text file) — confirmed both by reading
  the schema directly and by a screenshot of `septic_sep` in a real project
  database (`robit_demo_4.0.sqlite`). There is no 13th field anywhere in the
  schema for the "extra numeric column" the code's own docstring mentions. A
  text file generated to match the real 12-column schema (which is what this
  repository's `database_files/septic.sep` is) fails `check_cols(val, 13,
  'septic')`. In other words: if the editor team tried to reload their own
  current `septic.sep` data through their own reader today, it would fail the
  same way.
* **`Cal_parms_cal.read()` (`src/api/fileio/change.py`) force-lowercases every
  parameter name** (`'name': val[0].lower()`). The live `cal_parms_cal` table
  in the shipped `swatplus_datasets.sqlite` (v4.0.0) has three mixed-case
  names — `aquifer_K`, `aquifer_Sy`, `stream_K` — that would silently become
  `aquifer_k`, `aquifer_sy`, `stream_k` if ever reloaded through this reader.
  Whether that casing is load-bearing anywhere (Fortran variable matching,
  UI) hasn't been checked; flagging it here rather than guessing.

Both are pre-existing: neither is something this repository's data caused,
and neither should be worked around on our side — they're bugs in the
reader/data relationship inside `swatplus-editor` itself.

(Separately, and already fixed on our side: the decision-table writer's
default 5-decimal precision truncated a handful of deliberately-offset
boundary values in `scen_lu.dtl`/`flo_con.dtl` — e.g. `0.020001` round-tripped
to `0.02`. Regenerated at 6 decimals; see `internal/CHANGELOG.md`.)

## A patch-and-submit workflow, tested and working

Rather than trying to get `swatplus-editor` to adopt this repository's text
files as its own build source (a bigger ask — see "questions requiring SWAT+
team approval" above), a narrower workflow was prototyped and verified: take
the editor's **current** `swatplus_datasets.sqlite`, and replace only the
~26 tables this repository maintains text for (deleting and re-reading each
one via the editor's own `fileio` classes, each in its own transaction so a
failure rolls back instead of corrupting the table), leaving every other
table — soils, weather generator, land-use rules, project config, and the two
tables noted above as buggy — completely untouched.

Verified end to end against the real shipped database: every one of the ~20
patched tables came back byte-for-byte correct, and every one of the ~22
untouched/skipped tables was confirmed byte-for-byte identical to the
original afterward. This is the mechanism a periodic "submit our accumulated
changes to the editor" step would use — see the process note in
`CONTRIBUTING.md` / discussion history for the intended cadence.

## Explicitly out of scope for THIS repository's automation

Modifying SWAT+ Editor's table models or writers is not something this
repository's tooling does. What changed from the original read-only framing:
this repository is now expected to **periodically submit a patched
`swatplus_datasets.sqlite`** to `swatplus-editor` as a pull request (using the
tested patch approach above), carrying forward whatever record changes were
accepted here since the last sync. That hand-off is a deliberate, manual,
maintainer-driven step — not an automated one, and not something a random
contributor's PR ever triggers directly. Corrections to the editor's own
reader/writer code (like the two bugs above) belong upstream in SWAT+ Editor
— this repository's automation doesn't attempt to fix them.
