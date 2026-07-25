# Changelog

All notable changes to this repository and its database releases are recorded
here. Row-level changes are tracked in `metadata/database_changes.csv`; this file
summarizes releases and significant events.

The format follows a lightweight version of Keep a Changelog. Database releases
are versioned `YEAR.MAJOR.MINOR` and tagged `database-v<version>`.

## [Unreleased]

### Removed

* The one-time `scripts/inventory_reference_files.py`,
  `scripts/bootstrap_database_files.py`, `scripts/import_external_files.py`,
  and their now-orphaned helper `scripts/manifest_builder.py`, along with the
  tests written specifically for them (`tests/test_source_priority.py`,
  `tests/test_inventory.py`). The initial bootstrap and external import are
  complete and merged; these scripts have no further job in this repository's
  normal workflow (they never ran in CI) and their logic remains available in
  git history if a future re-bootstrap is ever needed. Adding a new database
  file going forward — whether a real upstream file or another external
  supply — is an ordinary pull request, not a script run.

## [2026.1.0] — Initial bootstrap

Initial workflow setup and authoritative import.

### Added

* Authoritative import of shared SWAT+ reference files, bootstrapped from
  `swat-model/swatplus` @ `cb442f7c05fc3bfc34349c446010f452d2737ca0`
  (`refdata/Ames_sub1` first, `refdata/Osu_1hru` fallback).
* Two direct-read databases discovered by inspecting the SWAT+ source and
  included as authoritative: `puddle.ops` and `transplant.plt`.
* Five externally supplied files with separate provenance
  (`metadata/external_sources.json`): `flo_con.dtl` (reproducible public
  commit), `salt.slt`, `scen_lu.dtl` (maintainer's internal NAM HUC8 model
  run), and the example/seed `pathogens.pth` and `metals.mtl` (marked
  `needs_review`).
* Metadata: `database_manifest.json`, `bootstrap_sources.json`,
  `external_sources.json`, `compatibility_matrix.csv` (all `not_tested`),
  `excluded_files.json`, and `database_changes.csv`.
* Tooling: inventory, bootstrap, external-import, validation, change-log
  validation, and release-packaging scripts, plus a unit/integration test suite.
* GitHub Actions: `validate-database` and `release-text-database`.

### Notes

* Source-file header versions are provenance only, not tested compatibility.
* No SQLite database is built or committed. No SWAT+ or SWAT+ Editor code is
  changed.
