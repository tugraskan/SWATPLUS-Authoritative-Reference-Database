# SWAT+ Editor Integration Findings

> The authoritative core files are serialized **from** the official SWAT+
> Editor reference dataset (`swatplus_datasets.sqlite`, v4.0.0, SWAT+ rev. 62)
> using the Editor's own `fileio` writers. That bootstrap extraction was
> read-only. The current hand-off workflow creates a patched **copy** of the
> Editor dataset for a deliberate upstream pull request; it still does not
> modify Editor source code or the input SQLite file.

The source and schema observations below were made against
`swat-model/swatplus-editor`. The patch behavior described later is implemented
in `internal/scripts/patch_editor_dataset.py`.

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

## Files outside the current patcher's coverage

* **Manure:** the Editor's `database/` layer has essentially no
  `manure_db.frt` / `manure_om.frt` model or import/export support. Future
  integration would need to add these models and readers/writers.
* **Newly included direct-read databases:** `puddle.ops` and `transplant.plt`
  have **no** corresponding Editor models (no references found in the Editor
  source). Future integration would need table models and import/export for
  them.
* **Optional / external files:** `pathogens.pth`, `metals.mtl`, and `salt.slt`
  would each need a mapping decision (table name, whether it should ship in
  `swatplus_datasets.sqlite`, and how `needs_review` example data is handled).
* **Temporarily excluded official tables:** `septic.sep` and `cal_parms.cal`
  exist in the Editor dataset but cannot be safely reloaded through the current
  Editor readers. The specific defects are documented below.

`flo_con.dtl` is not a gap: the patcher loads it with `lum.dtl`, `res_rel.dtl`,
and `scen_lu.dtl` into the Editor's shared decision-table hierarchy.

## Possible broader integration work

1. Extend the `datasets/setup.py` table registry to cover every authoritative
   file in this repository (including the manure and direct-read databases).
2. Add missing Peewee models and import/export (TxtInOut) support.
3. Decide which supplemental data belongs in the official dataset, then add
   only the approved tables to the maintainer patch workflow.
4. Copy any newly approved tables into project databases during project setup.

## Questions requiring SWAT+ team approval

* Which authoritative files should ship inside `swatplus_datasets.sqlite`, and at
  what dataset version?
* Table naming for the manure and newly discovered direct-read databases.
* Handling of `needs_review` example data (`pathogens.pth`, `metals.mtl`) — ship,
  omit, or replace with curated values first.
* Whether and when the two excluded Editor readers should be fixed upstream so
  `septic.sep` and `cal_parms.cal` can join the patch workflow.

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

Rather than making `swatplus-editor` adopt this repository as a new build
system, the verified workflow starts with the Editor's **current**
`swatplus_datasets.sqlite` and patches a copy. The script reads 24 of the 26
official-dataset files held here: 20 map one-to-one to Editor tables, and the
four `.dtl` files are loaded together as one decision-table group. Each
delete-and-reload runs in its own transaction so a failure rolls that group
back instead of leaving it empty.

The seven supplemental files are not patched because the Editor does not
manage them, and `septic.sep` / `cal_parms.cal` are explicitly excluded because
of the reader defects above. Soils, weather generator data, land-use rules,
project configuration, and every other unowned table remain untouched.

End-to-end testing against the shipped database verified the patched data and
confirmed the untouched/skipped tables stayed byte-for-byte identical to the
original. This is the mechanism used for periodic upstream submission; see
`internal/CONTRIBUTOR_GUIDE.md` for the command and review steps.

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
