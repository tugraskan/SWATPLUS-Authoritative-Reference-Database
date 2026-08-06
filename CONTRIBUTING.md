# Contributing

Thank you for helping maintain the SWAT+ authoritative reference database. All
changes to authoritative data go through branches and pull requests so that
every record stays traceable and validated.

## Branch and pull-request workflow

1. Create a branch off `main`.
2. Modify the appropriate file under `database_files/`.
3. Open a pull request. Filling in the template is welcome but **entirely
   optional** — nothing you type is required.
4. A reviewer must approve before merge.

Ordinary database-row changes do **not** require a SWAT+ Editor code change or
an Editor pull request.

## A source is welcome, but not required

If you have one, cite it in the PR template's `Source` section: a publication,
dataset, official documentation, a GitHub issue, or a named subject-matter
expert. It's optional, but it helps whoever reviews your change.

## Stable row keys

Use the record **name** (or another stable key) as a record's identity — never
a line number. Renaming a record is a `removed` + `added` pair, documented as
such.

## Filename rules

* Use `fire.ops` — never `burn.ops`.
* Use `pesticide.pes` — the canonical text filename used by SWAT+ source.
* Filename case must match the manifest exactly.
* Never commit a SQLite database as an authoritative source.

## Where things live

Everything beyond the reference data itself — validation scripts, the test
suite, schemas, metadata, and detailed contributor/maintainer rules — lives
under [`internal/`](internal/). If you're doing more than proposing a single
record change (adopting a new SWAT+ release, changing a file's schema,
reviewing PRs, or working on the validation tooling itself), see
[`internal/CONTRIBUTOR_GUIDE.md`](internal/CONTRIBUTOR_GUIDE.md) for the full
detail.
