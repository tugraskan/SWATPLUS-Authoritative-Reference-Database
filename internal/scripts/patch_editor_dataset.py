#!/usr/bin/env python3
"""Patch a copy of SWAT+ Editor's swatplus_datasets.sqlite from this
repository's database_files/, so it can be submitted as a pull request to
swatplus-editor.

This is the tool behind the "sync to the editor" step of the workflow:
contributors propose record changes here (via PR); a maintainer periodically
takes whatever accumulated and runs this script against the editor's current
dataset to produce an updated .sqlite to PR upstream.

It touches ONLY the tables this repository maintains text for -- every other
table (soils, weather generator, land-use rules, project config, and the two
tables in EXCLUDED_TABLES below) is left byte-for-byte untouched. Table-group
updates use savepoints inside one outer transaction, so any read failure rolls
back every change and leaves the output as an unmodified copy of the input.
The patch behavior is verified against a real shipped dataset; see
internal/docs/editor_integration_findings.md.

Requires a local checkout of swat-model/swatplus-editor (the script imports
its peewee models and fileio readers directly -- it has no other way to
write the same tables the editor itself writes). This is a maintainer tool
run by hand; it is deliberately NOT wired into this repository's CI, since
CI has no editor checkout to import from.

EXCLUDED_TABLES are skipped because reloading them through the editor's
current reader code is known to corrupt or misrepresent the data -- these
are bugs in swatplus-editor itself (see internal/docs/
editor_integration_findings.md for the evidence), not something to route
around here. Once fixed upstream, remove the exclusion.

Usage:
    python internal/scripts/patch_editor_dataset.py \
        --editor-repo /path/to/swatplus-editor \
        --editor-sqlite /path/to/swatplus_datasets.sqlite \
        --output /path/to/patched_swatplus_datasets.sqlite \
        --repo-root .
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

EXCLUDED_TABLES = {
    "septic_sep": (
        "swatplus-editor's Septic_sep.read() expects 13 whitespace-delimited "
        "file columns; the real septic_sep schema only has 12 data columns. "
        "Reloading our septic.sep (which matches the real 12-column schema) "
        "fails the reader's own check_cols(13). Bug in the editor's reader, "
        "not in our data -- see editor_integration_findings.md."
    ),
    "cal_parms_cal": (
        "swatplus-editor's Cal_parms_cal.read() force-lowercases every "
        "parameter name. The live dataset has 3 mixed-case names "
        "(aquifer_K, aquifer_Sy, stream_K) that would be silently renamed if "
        "reloaded. Bug in the editor's reader, not in our data -- see "
        "editor_integration_findings.md."
    ),
}


def _import_editor_modules(editor_repo: Path):
    """Import the editor's peewee models / fileio readers from a local
    checkout. Returns a namespace-like object with everything patch() needs."""
    api_dir = editor_repo / "src" / "api"
    if not (api_dir / "database" / "datasets").is_dir():
        raise SystemExit(
            f"{api_dir} doesn't look like a swatplus-editor checkout "
            "(expected src/api/database/datasets/)."
        )
    sys.path.insert(0, str(api_dir))

    from database.datasets import base as datasets_base
    from database.datasets import hru_parm_db as ds_parmdb, ops as ds_ops, \
        structural as ds_str, lum as ds_lum, change as ds_change, \
        decision_table as ds_dtable
    from fileio import hru_parm_db as files_parmdb, ops as files_ops, \
        structural as files_str, lum as files_lum, change as files_change, \
        decision_table as files_dtable

    class M:
        pass
    m = M()
    m.datasets_base = datasets_base
    m.ds_parmdb, m.ds_ops, m.ds_str = ds_parmdb, ds_ops, ds_str
    m.ds_lum, m.ds_change, m.ds_dtable = ds_lum, ds_change, ds_dtable
    m.files_parmdb, m.files_ops, m.files_str = files_parmdb, files_ops, files_str
    m.files_lum, m.files_change, m.files_dtable = files_lum, files_change, files_dtable
    return m


def build_jobs(m, text_dir: Path):
    """(peewee model, callable that re-reads the matching text file) pairs
    for every table this repository maintains -- everything NOT in
    EXCLUDED_TABLES."""
    def p(name):
        return str(text_dir / name)

    return [
        (m.ds_parmdb.Plants_plt,     lambda: m.files_parmdb.Plants_plt(p("plants.plt")).read(database='datasets')),
        (m.ds_parmdb.Fertilizer_frt, lambda: m.files_parmdb.Fertilizer_frt(p("fertilizer.frt")).read(database='datasets')),
        (m.ds_parmdb.Tillage_til,    lambda: m.files_parmdb.Tillage_til(p("tillage.til")).read(database='datasets')),
        (m.ds_parmdb.Pesticide_pst,  lambda: m.files_parmdb.Pesticide_pst(p("pesticide.pes")).read(database='datasets')),
        (m.ds_parmdb.Urban_urb,      lambda: m.files_parmdb.Urban_urb(p("urban.urb")).read(database='datasets')),
        (m.ds_parmdb.Snow_sno,       lambda: m.files_parmdb.Snow_sno(p("snow.sno")).read(database='datasets')),

        (m.ds_str.Bmpuser_str,     lambda: m.files_str.Bmpuser_str(p("bmpuser.str")).read(database='datasets')),
        (m.ds_str.Filterstrip_str, lambda: m.files_str.Filterstrip_str(p("filterstrip.str")).read(database='datasets')),
        (m.ds_str.Grassedww_str,   lambda: m.files_str.Grassedww_str(p("grassedww.str")).read(database='datasets')),
        (m.ds_str.Septic_str,      lambda: m.files_str.Septic_str(p("septic.str")).read(database='datasets')),
        (m.ds_str.Tiledrain_str,   lambda: m.files_str.Tiledrain_str(p("tiledrain.str")).read(database='datasets')),

        (m.ds_lum.Cntable_lum,   lambda: m.files_lum.Cntable_lum(p("cntable.lum")).read(database='datasets')),
        (m.ds_lum.Cons_prac_lum, lambda: m.files_lum.Cons_prac_lum(p("cons_practice.lum")).read(database='datasets')),
        (m.ds_lum.Ovn_table_lum, lambda: m.files_lum.Ovn_table_lum(p("ovn_table.lum")).read(database='datasets')),

        (m.ds_ops.Harv_ops,     lambda: m.files_ops.Harv_ops(p("harv.ops")).read(database='datasets')),
        (m.ds_ops.Graze_ops,    lambda: m.files_ops.Graze_ops(p("graze.ops")).read(database='datasets')),
        (m.ds_ops.Irr_ops,      lambda: m.files_ops.Irr_ops(p("irr.ops")).read(database='datasets')),
        (m.ds_ops.Chem_app_ops, lambda: m.files_ops.Chem_app_ops(p("chem_app.ops")).read(database='datasets')),
        (m.ds_ops.Fire_ops,     lambda: m.files_ops.Fire_ops(p("fire.ops")).read(database='datasets')),
        (m.ds_ops.Sweep_ops,    lambda: m.files_ops.Sweep_ops(p("sweep.ops")).read(database='datasets')),
    ]
    # cal_parms_cal and septic_sep intentionally omitted -- see EXCLUDED_TABLES.


def _apply_jobs(m, text_dir: Path) -> tuple[int, int]:
    """Apply every table group, returning successful and failed counts."""
    print("=== tables replaced from database_files/ ===")
    ok, fail = 0, 0
    for model, reader in build_jobs(m, text_dir):
        name = model._meta.table_name
        n_before = model.select().count()
        try:
            with m.datasets_base.db.atomic():
                model.delete().execute()
                reader()
            n_after = model.select().count()
            print(f"  {name:20s} {n_before:4d} -> {n_after:4d} rows")
            ok += 1
        except Exception as e:
            n_after = model.select().count()
            status = "rolled back, untouched" if n_after == n_before else "!! DATA LOSS !!"
            print(f"  {name:20s} FAILED: {e}\n{'':22s}-> {status}")
            fail += 1

    print("\n=== decision tables (lum.dtl, res_rel.dtl, scen_lu.dtl, flo_con.dtl) ===")
    n_before = m.ds_dtable.D_table_dtl.select().count()
    try:
        with m.datasets_base.db.atomic():
            m.ds_dtable.D_table_dtl_act_out.delete().execute()
            m.ds_dtable.D_table_dtl_act.delete().execute()
            m.ds_dtable.D_table_dtl_cond_alt.delete().execute()
            m.ds_dtable.D_table_dtl_cond.delete().execute()
            m.ds_dtable.D_table_dtl.delete().execute()
            for fname in ("lum.dtl", "res_rel.dtl", "scen_lu.dtl", "flo_con.dtl"):
                m.files_dtable.D_table_dtl(str(text_dir / fname), file_type=fname).read(database='datasets')
        n_after = m.ds_dtable.D_table_dtl.select().count()
        print(f"  d_table_dtl (all 4 files) {n_before:4d} -> {n_after:4d} tables")
        ok += 1
    except Exception as e:
        n_after = m.ds_dtable.D_table_dtl.select().count()
        status = "rolled back, untouched" if n_after == n_before else "!! DATA LOSS !!"
        print(f"  d_table_dtl FAILED: {e}\n  -> {status}")
        fail += 1

    print("\n=== tables intentionally left untouched (editor-side bugs; see docstring) ===")
    for name, reason in EXCLUDED_TABLES.items():
        print(f"  {name}: {reason}")

    print(f"\n{ok} table group(s) patched, {fail} failed.")
    return ok, fail


class _PatchFailed(RuntimeError):
    """Internal signal used to roll back the outer transaction."""


def patch(editor_repo: Path, editor_sqlite: Path, output: Path, repo_root: Path) -> bool:
    text_dir = repo_root / "database_files"
    if not text_dir.is_dir():
        raise SystemExit(f"{text_dir} not found -- is --repo-root correct?")

    shutil.copyfile(editor_sqlite, output)

    m = _import_editor_modules(editor_repo)
    m.datasets_base.db.init(str(output))

    print(f"Patching {output} (leaving {editor_sqlite.name} itself untouched)\n")
    fail = 0
    try:
        with m.datasets_base.db.atomic():
            _, fail = _apply_jobs(m, text_dir)
            if fail:
                raise _PatchFailed
    except _PatchFailed:
        print("All table changes were rolled back; the output remains an "
              "unmodified copy of the input database.")
    finally:
        if not m.datasets_base.db.is_closed():
            m.datasets_base.db.close()

    if fail:
        print("Do not submit this file upstream until failures are resolved.")
        return False
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--editor-repo", required=True, type=Path,
                    help="Path to a local swat-model/swatplus-editor checkout")
    ap.add_argument("--editor-sqlite", required=True, type=Path,
                    help="Path to the swatplus_datasets.sqlite to patch (read-only; never modified)")
    ap.add_argument("--output", required=True, type=Path,
                    help="Where to write the patched copy")
    ap.add_argument("--repo-root", default=".", type=Path,
                    help="This repository's root (finds database_files/ here)")
    args = ap.parse_args(argv)

    succeeded = patch(args.editor_repo.resolve(), args.editor_sqlite.resolve(),
                      args.output.resolve(), args.repo_root.resolve())
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
