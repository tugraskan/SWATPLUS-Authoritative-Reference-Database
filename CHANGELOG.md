# Changelog

All notable changes to this repository and its database releases are recorded
here. Row-level changes are tracked in `metadata/database_changes.csv`; this file
summarizes releases and significant events.

The format follows a lightweight version of Keep a Changelog. Database releases
are versioned `YEAR.MAJOR.MINOR` and tagged `database-v<version>`.

## [Unreleased]

_Nothing yet._

## [2026.1.0] — Initial bootstrap

Released 2026-07-24 · tag `database-v2026.1.0` · published with the text-file
ZIP, `database_manifest.json`, and `checksums.txt` attached.

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

Final manifest status: 31 `available`, 2 `needs_review` (`pathogens.pth`,
`metals.mtl`), 0 `unavailable` — every expected file now has an authoritative
source.

### Changed

* Retired the `metadata/bootstrap_exception` marker once the initial import was
  in place. Per-record change-log coverage against the pull-request merge base
  is now enforced for every added or modified authoritative record.

### Notes

* Source-file header versions are provenance only, not tested compatibility.
* No SQLite database is built or committed. No SWAT+ or SWAT+ Editor code is
  changed.
