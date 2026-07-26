"""Shared helpers for reading and validating SWAT+ reference text files.

Pure-Python, no third-party dependencies, no network access.  Imported by the
scripts and the tests.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from swat_config import (
    FMT_COUNT,
    FMT_DECISION,
    NAME_KEYED_FORMATS,
)

# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Header / version parsing
# ---------------------------------------------------------------------------

_EDITOR_RE = re.compile(r"SWAT\+\s*editor\s*v?([0-9][0-9.]*)", re.IGNORECASE)
_REV_RE = re.compile(r"SWAT\+\s*rev\.?\s*([0-9][0-9.]*)", re.IGNORECASE)


@dataclass
class HeaderInfo:
    header_line: str
    editor_version: Optional[str]
    swatplus_revision: Optional[str]


def parse_header(first_line: str) -> HeaderInfo:
    """Parse a SWAT+ file's first line for editor version / SWAT+ revision.

    Missing information is returned as ``None`` -- never guessed.  Many valid
    SWAT+ files (e.g. Ames tillage.til) carry no version line at all, in which
    case the first line is really the column header and both fields are None.
    """
    line = (first_line or "").rstrip("\n")
    ed = _EDITOR_RE.search(line)
    rev = _REV_RE.search(line)
    return HeaderInfo(
        header_line=line,
        editor_version=ed.group(1) if ed else None,
        swatplus_revision=rev.group(1) if rev else None,
    )


def read_first_line(path: str | Path) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.readline().rstrip("\n")


# ---------------------------------------------------------------------------
# Merge-marker detection
# ---------------------------------------------------------------------------

_MERGE_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")

#: Labels that open the column-header row of a SWAT+ name-keyed table.  Every
#: authoritative name-keyed file uses one of these as its first column, so the
#: header row can be found by content instead of by position.  Compared
#: lower-cased (files vary between ``name``, ``NAME``, and ``BACTNM``).
RECORD_KEY_LABELS = {"name", "bactnm"}

#: How far into a file to look for the column-header row.  Titles/version
#: banners and a count line occupy at most the first few lines; searching the
#: whole file risks matching a data record that happens to be called "name".
HEADER_SEARCH_LINES = 6


def find_merge_markers(text: str) -> list[int]:
    """Return 1-based line numbers that look like unresolved git merge markers."""
    hits = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.rstrip()
        if stripped.startswith(("<<<<<<< ", ">>>>>>> ")) or stripped in _MERGE_MARKERS:
            hits.append(i)
    return hits


# ---------------------------------------------------------------------------
# Record parsing for name-keyed tables
# ---------------------------------------------------------------------------


@dataclass
class Record:
    name: str
    fields: list[str]
    line_no: int  # 1-based line number in the file


@dataclass
class ParsedTable:
    header_info: HeaderInfo
    column_header_line_no: Optional[int]
    columns: list[str]
    records: list[Record]
    count_declared: Optional[int] = None  # for count-prefixed files
    problems: list[str] = field(default_factory=list)


def parse_name_keyed_table(
    path: str | Path,
    fmt: str,
    schema_columns: Optional[list[str]] = None,
) -> ParsedTable:
    """Parse a flat / count-prefixed name-keyed SWAT+ table.

    The column-header line is located by content when ``schema_columns`` is
    provided (first token equals ``schema_columns[0]``).  Without a schema it
    is found by recognizing the record-key label that opens every SWAT+
    name-keyed header row (see :data:`RECORD_KEY_LABELS`); anything above that
    line is a title / version banner.

    The label search is what keeps files apart that a version-string test
    cannot distinguish: some files open with a bare filename
    (``plants.plt``), some with an unpunctuated sentence
    (``harv_ops Generated from ...``), and some have no title line at all so
    that line 1 *is* the column header (``tillage.til``, ``puddle.ops``).

    Records are every subsequent non-empty line; the first whitespace token is
    the record name.
    """
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    # keep original 1-based line numbers alongside content
    numbered = [(i + 1, ln) for i, ln in enumerate(lines)]
    non_empty = [(n, ln) for (n, ln) in numbered if ln.strip() != ""]

    header_info = parse_header(lines[0] if lines else "")
    count_declared: Optional[int] = None
    problems: list[str] = []

    header_idx = None  # index into non_empty of the column-header line

    if schema_columns:
        first_col = schema_columns[0]
        for idx, (n, ln) in enumerate(non_empty):
            if ln.split() and ln.split()[0] == first_col:
                header_idx = idx
                break

    if header_idx is None:
        # No schema (or the schema's first column was not found): locate the
        # column-header line by its record-key label.
        for idx, (n, ln) in enumerate(non_empty[:HEADER_SEARCH_LINES]):
            toks = ln.split()
            if toks and toks[0].strip().lower() in RECORD_KEY_LABELS:
                header_idx = idx
                break

        if header_idx is None:
            # Last-resort positional fallback.
            if fmt == FMT_COUNT:
                # title, then an integer count line, then the column header.
                for idx, (n, ln) in enumerate(non_empty):
                    if ln.strip().isdigit():
                        header_idx = idx + 1
                        break
                if header_idx is None:
                    header_idx = 1
            else:
                header_idx = 1 if len(non_empty) > 1 else 0
            problems.append(
                "column-header row not recognized; fell back to position "
                f"{header_idx} (expected a row starting with one of: "
                f"{sorted(RECORD_KEY_LABELS)})"
            )

    if fmt == FMT_COUNT and header_idx is not None and count_declared is None:
        # Count-prefixed files declare their record count on a bare-integer
        # line above the column header.
        for j in range(header_idx - 1, -1, -1):
            if non_empty[j][1].strip().isdigit():
                count_declared = int(non_empty[j][1].strip())
                break

    columns: list[str] = []
    column_header_line_no: Optional[int] = None
    if header_idx is not None and header_idx < len(non_empty):
        column_header_line_no, header_line = non_empty[header_idx]
        columns = header_line.split()
        data = non_empty[header_idx + 1:]
    else:
        data = []

    records: list[Record] = []
    for n, ln in data:
        toks = ln.split()
        if not toks:
            continue
        records.append(Record(name=toks[0], fields=toks, line_no=n))

    return ParsedTable(
        header_info=header_info,
        column_header_line_no=column_header_line_no,
        columns=columns,
        records=records,
        count_declared=count_declared,
        problems=problems,
    )


def is_number(token: str) -> bool:
    try:
        float(token)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Decision-table (.dtl) structural parsing
# ---------------------------------------------------------------------------


@dataclass
class DecisionTable:
    name: str
    conds: int
    alts: int
    acts: int
    name_line_no: int


@dataclass
class ParsedDecisionFile:
    header_line: str
    declared_count: Optional[int]
    tables: list[DecisionTable]
    problems: list[str] = field(default_factory=list)


def parse_decision_file(path: str | Path) -> ParsedDecisionFile:
    """Parse a SWAT+ decision-table (.dtl) file into its named blocks.

    Structure (per SWAT+ convention):

        <title line>
        <integer: number of decision tables>
        name   conds  alts  acts     # a header row
        <table_name>  <conds> <alts> <acts>
        var  ... (conds rows)
        act_typ ... (acts rows)
        ... (next table)

    We locate each table by the ``name ... conds ... alts ... acts`` header row
    followed by a data row whose 2nd/3rd/4th tokens are integers.
    """
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    numbered = [(i + 1, ln) for i, ln in enumerate(lines)]
    non_empty = [(n, ln) for (n, ln) in numbered if ln.strip() != ""]

    header_line = lines[0] if lines else ""
    declared_count: Optional[int] = None
    problems: list[str] = []
    tables: list[DecisionTable] = []

    # declared count is the first bare-integer line
    for n, ln in non_empty:
        if ln.strip().isdigit():
            declared_count = int(ln.strip())
            break

    i = 0
    while i < len(non_empty):
        n, ln = non_empty[i]
        toks = ln.split()
        low = [t.lower() for t in toks]
        # a block-header row starts with the table-name column label -- seen
        # as "name" or "dtbl_name" (any case) -- followed by conds/alts/acts.
        if low and low[0] in ("name", "dtbl_name") and "conds" in low:
            if i + 1 < len(non_empty):
                dn, dln = non_empty[i + 1]
                dtoks = dln.split()
                if len(dtoks) >= 4 and all(t.lstrip("-").isdigit() for t in dtoks[1:4]):
                    tables.append(DecisionTable(
                        name=dtoks[0],
                        conds=int(dtoks[1]),
                        alts=int(dtoks[2]),
                        acts=int(dtoks[3]),
                        name_line_no=dn,
                    ))
                    i += 2
                    continue
        i += 1

    return ParsedDecisionFile(
        header_line=header_line,
        declared_count=declared_count,
        tables=tables,
        problems=problems,
    )


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def is_name_keyed(fmt: str) -> bool:
    return fmt in NAME_KEYED_FORMATS


def is_decision(fmt: str) -> bool:
    return fmt == FMT_DECISION
