"""Central configuration for the SWAT+ Authoritative Reference Database.

This module is the single source of truth for:

* the expected authoritative files, their categories, and required-ness;
* the format class of each file (flat name-keyed table, count-prefixed table,
  decision table, or constants block); and
* column schemas for the subset of files whose headers have been verified
  against the pinned SWAT+ commit.

Schemas are intentionally partial.  Field-count and numeric checks only run for
files listed in :data:`FILE_SCHEMAS`; every other file still receives the
generic checks (non-empty, no merge markers, unique / non-blank record names
where it is a name-keyed table).  This follows the specification, which only
requires strict field validation "where the format is known".

Nothing in this module contacts the network or the SWAT+ checkout; it is pure
data so that both the scripts and the tests can import it cheaply.

Note: the one-time bootstrap/inventory/external-import scripts (and the
constants that only they consumed -- the pinned-commit/source-priority
constants, the direct-read filename list, and the external-file provenance
table) have been retired now that the initial import is complete and merged.
That history -- the pinned commit, which direct-read databases were
discovered, and every external file's origin -- is preserved permanently in
``metadata/bootstrap_sources.json``, ``metadata/external_sources.json``, and
git history; it doesn't need to be duplicated here as unused code.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Format classes
# ---------------------------------------------------------------------------

FMT_FLAT = "flat_named"          # title? + column header + name-keyed rows
FMT_COUNT = "count_prefixed"     # title + integer count line + column header + rows
FMT_DECISION = "decision_table"  # named decision-table blocks (conds/alts/acts)
FMT_CONSTANTS = "constants"      # keyed constants blocks, not one-record-per-row

#: Format classes that are name-keyed (first token of each data row is the
#: stable record name).  Duplicate / blank record-name checks apply to these.
NAME_KEYED_FORMATS = {FMT_FLAT, FMT_COUNT}


# ---------------------------------------------------------------------------
# Expected authoritative files
# ---------------------------------------------------------------------------
# Each entry:
#   name             file name in database_files/
#   category         manifest category
#   required         True -> a missing file is a hard failure
#   record_key       stable identity column ("name", "table_name", or None)
#   fmt              format class (see above)
#   direct_read      True -> hard-coded filename in SWAT+ source
#   origin           "bootstrap" (imported from Ames/OSU) or "external"
#                    (supplied outside the approved sources) -- informational
#                    only; the authoritative record of each file's provenance
#                    is metadata/bootstrap_sources.json or
#                    metadata/external_sources.json, not this field.

EXPECTED_FILES = [
    # -- calibration --
    dict(name="cal_parms.cal", category="calibration", required=True,
         record_key="name", fmt=FMT_COUNT, direct_read=False, origin="bootstrap"),

    # -- HRU parameter databases --
    dict(name="plants.plt", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="fertilizer.frt", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="tillage.til", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="pesticide.pes", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="pathogens.pth", category="hru_parameter_database", required=False,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="external"),
    dict(name="metals.mtl", category="hru_parameter_database", required=False,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="external"),
    dict(name="salt.slt", category="hru_parameter_database", required=False,
         record_key=None, fmt=FMT_CONSTANTS, direct_read=False, origin="external"),
    dict(name="urban.urb", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="septic.sep", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="snow.sno", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    # transplant.plt is a plant database read directly by SWAT+ (hard-coded).
    dict(name="transplant.plt", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=True, origin="bootstrap"),

    # -- manure databases (direct-read) --
    dict(name="manure_db.frt", category="manure_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=True, origin="bootstrap"),
    dict(name="manure_om.frt", category="manure_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=True, origin="bootstrap"),

    # -- operation databases --
    dict(name="harv.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="graze.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="irr.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="chem_app.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="fire.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="sweep.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    # puddle.ops is read directly by SWAT+ (hard-coded); OSU only.
    dict(name="puddle.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=True, origin="bootstrap"),

    # -- decision tables --
    dict(name="lum.dtl", category="decision_table", required=True,
         record_key="table_name", fmt=FMT_DECISION, direct_read=False, origin="bootstrap"),
    dict(name="res_rel.dtl", category="decision_table", required=True,
         record_key="table_name", fmt=FMT_DECISION, direct_read=False, origin="bootstrap"),
    dict(name="scen_lu.dtl", category="decision_table", required=False,
         record_key="table_name", fmt=FMT_DECISION, direct_read=False,
         origin="external"),
    dict(name="flo_con.dtl", category="decision_table", required=False,
         record_key="table_name", fmt=FMT_DECISION, direct_read=False, origin="external"),

    # -- structural databases --
    dict(name="tiledrain.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="septic.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="filterstrip.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="grassedww.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="bmpuser.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),

    # -- additional shared reference tables --
    dict(name="cntable.lum", category="lum_reference", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="cons_practice.lum", category="lum_reference", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
    dict(name="ovn_table.lum", category="lum_reference", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="bootstrap"),
]

#: Convenience lookup by file name.
EXPECTED_BY_NAME = {f["name"]: f for f in EXPECTED_FILES}

# Per-file provenance for the five externally supplied files (pathogens.pth,
# metals.mtl, salt.slt, flo_con.dtl, scen_lu.dtl) -- including which are
# needs_review example/seed data and which origins are independently
# reproducible -- lives permanently in metadata/external_sources.json.


# ---------------------------------------------------------------------------
# Column schemas (verified files only)
# ---------------------------------------------------------------------------
# For a schema entry:
#   columns    ordered column names (the column-header line must match these)
#   numeric    indices (0-based) of columns whose data values must parse as float
#   text_tail  True when the LAST column is free text (a description) that may
#              contain spaces; field-count then requires >= len(columns) tokens
#              rather than an exact match, so a spaced description is not an error.
#
# The column-header line is located by content (its first token equals the
# first column name), so files with and without a leading title/version line
# are both handled without assuming a fixed header-line count.

FILE_SCHEMAS = {
    "snow.sno": dict(
        columns=["name", "fall_tmp", "melt_tmp", "melt_max", "melt_min",
                 "tmp_lag", "snow_h2o", "cov50", "snow_init"],
        numeric=[1, 2, 3, 4, 5, 6, 7, 8],
    ),
    "tillage.til": dict(
        columns=["name", "mix_eff", "mix_dp", "rough", "ridge_ht",
                 "ridge_sp", "description"],
        numeric=[1, 2, 3, 4, 5],
        text_tail=True,
    ),
    "cal_parms.cal": dict(
        columns=["name", "obj_typ", "abs_min", "abs_max", "units"],
        numeric=[2, 3],
    ),
    "manure_om.frt": dict(
        columns=["name", "frac_water", "fcbn", "fminn", "fminp",
                 "forgn", "forgp", "fnh3n", "description"],
        numeric=[1, 2, 3, 4, 5, 6, 7],
        text_tail=True,
    ),
    "manure_db.frt": dict(
        columns=["name", "org_min", "pests", "paths", "hmets",
                 "salts", "constit", "description"],
        numeric=[],
        text_tail=True,
    ),
    "metals.mtl": dict(
        columns=["name", "kd", "half_life", "bio_avail"],
        numeric=[1, 2, 3],
    ),
    "pathogens.pth": dict(
        columns=["BACTNM", "DO_SOLN", "GR_SOLN", "DO_SORB", "GR_SORB", "KD",
                 "T_ADJ", "WASHOFF", "DO_PLNT", "GR_PLNT", "FR_MANURE", "PERCO",
                 "DET_THRSHD", "DO_STREAM", "GR_STREAM", "DO_RES", "GR_RES",
                 "SWF", "CONC_MIN"],
        numeric=list(range(1, 19)),
    ),
}


# ---------------------------------------------------------------------------
# Manure cross-reference configuration
# ---------------------------------------------------------------------------
# manure_db.frt has an 'org_min' column whose value names an entry in
# manure_om.frt (verified in src/manure_orgmin_read.f90 / the file headers).
# 'null' means "no reference".
MANURE_DB_FILE = "manure_db.frt"
MANURE_OM_FILE = "manure_om.frt"
MANURE_DB_ORGMIN_COLUMN = "org_min"

DATABASE_FILES_DIR = "database_files"
METADATA_DIR = "metadata"
