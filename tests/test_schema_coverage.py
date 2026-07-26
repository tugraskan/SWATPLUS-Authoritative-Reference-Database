"""Every name-keyed database file must carry a column schema.

Without a schema a file gets only the generic checks (non-empty, no merge
markers, unique/non-blank record names).  Field counts, data types, and header
drift all go unchecked -- which is how a malformed submission slipped through
before these schemas existed.  These tests keep that gap from reopening
silently when a new file is added to EXPECTED_FILES.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swat_common import RECORD_KEY_LABELS, parse_name_keyed_table
from swat_config import EXPECTED_FILES, FILE_SCHEMAS, NAME_KEYED_FORMATS

NAME_KEYED = [f for f in EXPECTED_FILES if f["fmt"] in NAME_KEYED_FORMATS]


def test_every_name_keyed_file_has_a_schema():
    missing = [f["name"] for f in NAME_KEYED if f["name"] not in FILE_SCHEMAS]
    assert missing == [], (
        "these name-keyed files have no FILE_SCHEMAS entry, so their field "
        f"counts and data types are unvalidated: {missing}"
    )


def test_no_schema_for_unknown_file():
    """FILE_SCHEMAS must not drift out of sync with EXPECTED_FILES."""
    known = {f["name"] for f in EXPECTED_FILES}
    assert set(FILE_SCHEMAS) <= known, \
        f"schemas for files not in EXPECTED_FILES: {set(FILE_SCHEMAS) - known}"


@pytest.mark.parametrize("spec", NAME_KEYED, ids=lambda s: s["name"])
def test_schema_matches_committed_header(repo_root, spec):
    """The schema's columns must equal the file's actual header row."""
    name = spec["name"]
    path = repo_root / "database_files" / name
    if not path.is_file():
        pytest.skip(f"{name} not present")
    schema = FILE_SCHEMAS[name]
    table = parse_name_keyed_table(path, spec["fmt"], schema["columns"])
    assert table.columns == schema["columns"], (
        f"{name}: header row and schema disagree "
        f"(schema={len(schema['columns'])} cols, file={len(table.columns)})"
    )


@pytest.mark.parametrize("spec", NAME_KEYED, ids=lambda s: s["name"])
def test_schema_numeric_indices_are_in_range(spec):
    schema = FILE_SCHEMAS[spec["name"]]
    ncols = len(schema["columns"])
    bad = [i for i in schema["numeric"] if not 0 < i < ncols]
    assert bad == [], f"{spec['name']}: numeric indices out of range: {bad}"


@pytest.mark.parametrize("spec", NAME_KEYED, ids=lambda s: s["name"])
def test_header_row_is_locatable_without_a_schema(repo_root, spec):
    """The schema-less fallback must still find the real column header.

    Regression guard: files whose first line is a bare filename
    (plants.plt), an unpunctuated sentence (harv.ops), or absent entirely so
    the header is line 1 (tillage.til, puddle.ops) were all misparsed by the
    previous version-string heuristic, which silently swallowed the header row
    as a data record.
    """
    name = spec["name"]
    path = repo_root / "database_files" / name
    if not path.is_file():
        pytest.skip(f"{name} not present")
    table = parse_name_keyed_table(path, spec["fmt"], None)  # force fallback
    assert table.columns, f"{name}: no column header found"
    assert table.columns[0].strip().lower() in RECORD_KEY_LABELS, (
        f"{name}: fallback picked {table.columns[0]!r} as the key column"
    )
    first = table.records[0].name.lower() if table.records else ""
    assert first not in RECORD_KEY_LABELS, (
        f"{name}: header row was swallowed as a data record ({first!r})"
    )
