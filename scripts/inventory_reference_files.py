#!/usr/bin/env python3
"""Inventory the SWAT+ reference sources (Ames_sub1, Osu_1hru).

Read-only inspection of a pinned SWAT+ checkout.  Produces
``docs/source_inventory.md`` and never modifies the source checkout or copies
files into the authoritative repository.

It classifies every source file as one of:

    shared reference database
    project-specific input
    model output
    unknown, needs review

and reports duplicate filenames (with checksum equality), expected files
missing from both sources, ``file.cio`` references (including names referenced
but absent on disk), and the hard-coded fixed-filename readers discovered in the
SWAT+ source.

Usage:
    python scripts/inventory_reference_files.py \
        --swatplus-checkout /path/to/swat-model/swatplus [--repo-root .]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from swat_common import sha256_file  # noqa: E402
from swat_config import (  # noqa: E402
    BOOTSTRAP_SOURCE_PRIORITY,
    DIRECT_READ_FILES,
    EXPECTED_BY_NAME,
)

REFDATA = "refdata"

# Discovered fixed-filename readers (see the Phase 1 report). These open a
# literal filename via inquire(file="...") and are NOT driven by file.cio.
FIXED_FILENAME_READERS = [
    ("manure_db.frt", "src/manure_db_read.f90"),
    ("manure_om.frt", "src/manure_orgmin_read.f90"),
    ("puddle.ops", "src/mgt_read_puddle.f90"),
    ("transplant.plt", "src/plant_transplant_read.f90"),
]

# Classification hints -----------------------------------------------------
_OUTPUT_SUFFIXES = (".out", ".fin")
_OUTPUT_MARKERS = ("_aa.txt", "_yr.txt", "_stat.txt", "_all.txt", ".txt")
_INPUT_SUFFIXES = (
    ".con", ".cli", ".sim", ".bsn", ".sol", ".ini", ".hru", ".sch", ".pcp",
    ".tem", ".tmp", ".wnd", ".slr", ".rtu", ".def", ".ele", ".hyd", ".cha",
    ".res", ".aqu", ".rec", ".trt", ".fld", ".wet", ".prt", ".cnt", ".swf",
    ".wgn", ".sta", ".fig",
)
_KNOWN_OUTPUT_NAMES = {
    "area_calc.out", "checker.out", "co2.out", "diagnostics.out",
    "erosion.out", "erosion.txt", "files_out.out", "simulation.out",
    "success.fin", "yield.out", "mgt_out.txt", "lu_change_out.txt",
    "deposition_aa.txt", "reservoir_sed.txt",
}


def classify(name: str) -> str:
    if name in EXPECTED_BY_NAME or name in DIRECT_READ_FILES:
        return "shared reference database"
    lname = name.lower()
    if name in _KNOWN_OUTPUT_NAMES or lname.startswith("fort.") \
            or lname.startswith("basin_") or lname.startswith("hru_") \
            or lname.startswith("crop_yld") or lname.endswith("_aa.txt") \
            or lname.startswith("hyd") and lname.endswith("_aa.txt"):
        return "model output"
    if lname.endswith(_OUTPUT_SUFFIXES):
        return "model output"
    if any(lname.endswith(s) for s in _INPUT_SUFFIXES):
        return "project-specific input"
    if lname.endswith(".txt"):
        return "model output"
    if name in ("landuse.lum", "management.sch", "plant.ini",
                "soil_plant.ini", "landuse.lum"):
        return "project-specific input"
    return "unknown, needs review"


def list_dir(checkout: Path, sub: str) -> dict[str, Path]:
    d = checkout / REFDATA / sub
    if not d.is_dir():
        return {}
    return {p.name: p for p in d.iterdir() if p.is_file()}


def parse_file_cio(path: Path) -> list[tuple[str, list[str]]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        toks = line.split()
        if not toks:
            continue
        cat, refs = toks[0], [t for t in toks[1:] if t != "null"]
        rows.append((cat, refs))
    return rows


def resolve_commit(checkout: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--swatplus-checkout", required=True)
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args(argv)

    checkout = Path(args.swatplus_checkout).resolve()
    repo_root = Path(args.repo_root).resolve()
    commit = resolve_commit(checkout)

    ames = list_dir(checkout, "Ames_sub1")
    osu = list_dir(checkout, "Osu_1hru")

    all_names = sorted(set(ames) | set(osu))
    in_both = sorted(set(ames) & set(osu))
    ames_only = sorted(set(ames) - set(osu))
    osu_only = sorted(set(osu) - set(ames))

    # duplicate checksum comparison
    dup_rows = []
    for name in in_both:
        same = sha256_file(ames[name]) == sha256_file(osu[name])
        dup_rows.append((name, "identical" if same else "differ"))

    # expected files missing from both
    missing_expected = [n for n in EXPECTED_BY_NAME
                        if n not in ames and n not in osu]

    # file.cio inspection
    ames_cio = parse_file_cio(checkout / REFDATA / "Ames_sub1" / "file.cio")
    osu_cio = parse_file_cio(checkout / REFDATA / "Osu_1hru" / "file.cio")

    def cio_absent(cio, present):
        absent = []
        for cat, refs in cio:
            for r in refs:
                if r not in present:
                    absent.append((cat, r))
        return absent

    ames_absent = cio_absent(ames_cio, ames)
    osu_absent = cio_absent(osu_cio, osu)

    _write_inventory(repo_root, commit, ames, osu, all_names, in_both,
                     ames_only, osu_only, dup_rows, missing_expected,
                     ames_cio, osu_cio, ames_absent, osu_absent)

    print(f"Inventory written. Ames={len(ames)} OSU={len(osu)} "
          f"both={len(in_both)} missing_expected={len(missing_expected)}")
    return 0


def _write_inventory(repo_root, commit, ames, osu, all_names, in_both,
                     ames_only, osu_only, dup_rows, missing_expected,
                     ames_cio, osu_cio, ames_absent, osu_absent):
    L = []
    L += ["# SWAT+ Source Inventory", "",
          f"Source: `swat-model/swatplus` @ `{commit}`  ",
          f"Priority: {' -> '.join(BOOTSTRAP_SOURCE_PRIORITY)}", "",
          f"- Ames_sub1 files: {len(ames)}",
          f"- Osu_1hru files: {len(osu)}",
          f"- In both directories: {len(in_both)}", ""]

    L += ["## Fixed-filename (direct-read) databases", "",
          "Discovered by inspecting the SWAT+ source. These are opened by a "
          "literal filename and are **not** driven by `file.cio`.", "",
          "| File | Reader source |", "|---|---|"]
    for name, srcfile in FIXED_FILENAME_READERS:
        L.append(f"| `{name}` | `{srcfile}` |")

    L += ["", "## Expected files missing from both sources", ""]
    if missing_expected:
        for n in sorted(missing_expected):
            L.append(f"- `{n}`")
    else:
        L.append("_none_")

    L += ["", "## Duplicate filenames (in both directories)", "",
          "| File | Ames vs OSU |", "|---|---|"]
    for name, verdict in dup_rows:
        L.append(f"| `{name}` | {verdict} |")

    L += ["", "## Classification", "",
          "| File | In Ames | In OSU | Classification |",
          "|---|:---:|:---:|---|"]
    for name in all_names:
        L.append(f"| `{name}` | {'x' if name in ames else ''} | "
                 f"{'x' if name in osu else ''} | {classify(name)} |")

    L += ["", "## file.cio references absent on disk", "",
          "Filenames referenced by a `file.cio` slot but not present on disk "
          "(a name in `file.cio` is not proof a file exists).", "",
          "### Ames_sub1", ""]
    L += ([f"- `{r}` (category `{c}`)" for c, r in ames_absent] or ["_none_"])
    L += ["", "### Osu_1hru", ""]
    L += ([f"- `{r}` (category `{c}`)" for c, r in osu_absent] or ["_none_"])
    L.append("")

    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "source_inventory.md").write_text(
        "\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
