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

## Explicitly out of scope now

Modifying SWAT+ Editor — changing its table models or writers, generating
`swatplus_datasets.sqlite`, or submitting any SWAT+ Editor pull request — is
**not** part of this repository's workflow. This repository consumes the
official dataset read-only; corrections to what the editor writes belong
upstream in SWAT+ Editor.
