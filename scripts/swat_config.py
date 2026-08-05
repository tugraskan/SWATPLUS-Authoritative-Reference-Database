"""Central configuration for the SWAT+ Authoritative Reference Database.

This module is the single source of truth for:

* the expected authoritative files, their categories, and required-ness;
* the format class of each file (flat name-keyed table, count-prefixed table,
  decision table, or constants block); and
* column schemas for every name-keyed file.

:data:`FILE_SCHEMAS` covers all name-keyed files, and ``tests/
test_schema_coverage.py`` enforces that it stays that way -- a new database
file must arrive with its schema.  The schemas drive the field-count, numeric,
and header-drift checks; decision tables and constants files are not
name-keyed and receive structural checks instead.

Each schema's ``columns`` were taken from the committed file's own header row
and cross-checked against the SWAT+ source: a reader either lists the fields
explicitly in its ``read`` statement or reads a derived type whose components
give the same arity and types (verified for ``snow.sno`` /
``manure_om.frt``).  See CONTRIBUTING.md for what to do when an upstream SWAT+
release changes a file's format.

Nothing in this module contacts the network or the SWAT+ checkout; it is pure
data so that both the scripts and the tests can import it cheaply.

Note: the authoritative reference files are regenerated from the official
SWAT+ Editor reference dataset (``swatplus_datasets.sqlite``) using the
editor's own file writers, so they match, byte for byte, what SWAT+ Editor
ships into every project. Seven files that the official dataset does not
carry -- the manure databases, metals, salt, transplant, puddle, and the
pathogens example set -- are retained as supplemental and tracked in
``metadata/external_sources.json``. The per-file source table, dataset
version, and checksums live in ``metadata/bootstrap_sources.json`` and
``metadata/external_sources.json``; they are not duplicated here.
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
#   origin           "official" (regenerated from the SWAT+ Editor official
#                    reference dataset, swatplus_datasets.sqlite) or
#                    "supplemental" (a real SWAT+ file the official dataset
#                    does not carry, retained from the earlier import) --
#                    informational only; the authoritative record of each
#                    file's provenance is metadata/bootstrap_sources.json or
#                    metadata/external_sources.json, not this field.

EXPECTED_FILES = [
    # -- calibration --
    dict(name="cal_parms.cal", category="calibration", required=True,
         record_key="name", fmt=FMT_COUNT, direct_read=False, origin="official"),

    # -- HRU parameter databases --
    dict(name="plants.plt", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="fertilizer.frt", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="tillage.til", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="pesticide.pes", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="pathogens.pth", category="hru_parameter_database", required=False,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="supplemental"),
    dict(name="metals.mtl", category="hru_parameter_database", required=False,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="supplemental"),
    dict(name="salt.slt", category="hru_parameter_database", required=False,
         record_key=None, fmt=FMT_CONSTANTS, direct_read=False, origin="supplemental"),
    dict(name="urban.urb", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="septic.sep", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="snow.sno", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    # transplant.plt is a plant database read directly by SWAT+ (hard-coded).
    dict(name="transplant.plt", category="hru_parameter_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=True, origin="supplemental"),

    # -- manure databases (direct-read) --
    dict(name="manure_db.frt", category="manure_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=True, origin="supplemental"),
    dict(name="manure_om.frt", category="manure_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=True, origin="supplemental"),

    # -- operation databases --
    dict(name="harv.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="graze.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="irr.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="chem_app.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="fire.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="sweep.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    # puddle.ops is read directly by SWAT+ (hard-coded).
    dict(name="puddle.ops", category="operation_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=True, origin="supplemental"),

    # -- decision tables --
    dict(name="lum.dtl", category="decision_table", required=True,
         record_key="table_name", fmt=FMT_DECISION, direct_read=False, origin="official"),
    dict(name="res_rel.dtl", category="decision_table", required=True,
         record_key="table_name", fmt=FMT_DECISION, direct_read=False, origin="official"),
    dict(name="scen_lu.dtl", category="decision_table", required=True,
         record_key="table_name", fmt=FMT_DECISION, direct_read=False,
         origin="official"),
    dict(name="flo_con.dtl", category="decision_table", required=True,
         record_key="table_name", fmt=FMT_DECISION, direct_read=False, origin="official"),

    # -- structural databases --
    dict(name="tiledrain.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="septic.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="filterstrip.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="grassedww.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="bmpuser.str", category="structural_database", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),

    # -- additional shared reference tables --
    dict(name="cntable.lum", category="lum_reference", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="cons_practice.lum", category="lum_reference", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
    dict(name="ovn_table.lum", category="lum_reference", required=True,
         record_key="name", fmt=FMT_FLAT, direct_read=False, origin="official"),
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
        # SWF removed: it is not a field of SWAT+ 62's pathogen_db (verified
        # against pathogen_data_module.f90, path_parm_read.f90, and
        # swatplus-enhanced-docs' pth reference page -- three independent
        # sources agree on 18 fields ending at CONC_MIN, none mention SWF).
        columns=["BACTNM", "DO_SOLN", "GR_SOLN", "DO_SORB", "GR_SORB", "KD",
                 "T_ADJ", "WASHOFF", "DO_PLNT", "GR_PLNT", "FR_MANURE", "PERCO",
                 "DET_THRSHD", "DO_STREAM", "GR_STREAM", "DO_RES", "GR_RES",
                 "CONC_MIN"],
        numeric=list(range(1, 18)),
    ),

    # ---- derived from the committed header rows (see CONTRIBUTING) ----
    "plants.plt": dict(
        # The official SWAT+ Editor dataset (swatplus_datasets.sqlite v4.0.0)
        # writes plants.plt with 52 numeric parameters ending at 'rsd_covfac'
        # followed by a free-text 'description'. SWAT+ 62's read statement
        # continues past rsd_covfac to four carbon-module fields --
        # meta_frac, str_frac, lig_frac (all real) and pl_class -- which the
        # official dataset does not emit. Those trailing fields are read
        # conditionally (the carbon module / bsn_cc%nam1 path) and default
        # otherwise, so the official file runs on the default/mainline path;
        # the arity gap is recorded in metadata/schema_drift_waivers.json.
        columns=['name', 'plnt_typ', 'gro_trig', 'nfix_co',
                 'days_mat', 'bm_e', 'harv_idx', 'lai_pot',
                 'frac_hu1', 'lai_max1', 'frac_hu2', 'lai_max2',
                 'hu_lai_decl', 'dlai_rate', 'can_ht_max',
                 'rt_dp_max', 'tmp_opt', 'tmp_base', 'frac_n_yld',
                 'frac_p_yld', 'frac_n_em', 'frac_n_50',
                 'frac_n_mat', 'frac_p_em', 'frac_p_50',
                 'frac_p_mat', 'harv_idx_ws', 'usle_c_min',
                 'stcon_max', 'vpd', 'frac_stcon', 'ru_vpd',
                 'co2_hi', 'bm_e_hi', 'plnt_decomp', 'lai_min',
                 'bm_tree_acc', 'yrs_mat', 'bm_tree_max', 'ext_co',
                 'leaf_tov_mn', 'leaf_tov_mx', 'bm_dieoff',
                 'rt_st_beg', 'rt_st_end', 'plnt_pop1', 'frac_lai1',
                 'plnt_pop2', 'frac_lai2', 'frac_sw_gro',
                 'aeration', 'rsd_pctcov', 'rsd_covfac',
                 'description'],
        numeric=list(range(3, 53)),
        text_tail=True,
    ),
    "fertilizer.frt": dict(
        columns=['name', 'min_n', 'min_p', 'org_n', 'org_p',
                 'nh3_n', 'pathogens', 'description'],
        numeric=[1, 2, 3, 4, 5],
        text_tail=True,
    ),
    "pesticide.pes": dict(
        # pl_uptake added to match SWAT+ 62 (type pesticide_db in
        # pesticide_data_module.f90); the file predated this column. Every
        # value is currently a 0.0 placeholder -- see
        # metadata/schema_drift_waivers.json.
        columns=['name', 'soil_ads', 'frac_wash', 'hl_foliage',
                 'hl_soil', 'solub', 'aq_hlife', 'aq_volat',
                 'mol_wt', 'aq_resus', 'aq_settle', 'ben_act_dep',
                 'ben_bury', 'ben_hlife', 'pl_uptake', 'description'],
        numeric=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        text_tail=True,
    ),
    "urban.urb": dict(
        columns=['name', 'frac_imp', 'frac_dc_imp', 'curb_den',
                 'urb_wash', 'dirt_max', 't_halfmax', 'conc_totn',
                 'conc_totp', 'conc_no3n', 'urb_cn', 'description'],
        numeric=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        text_tail=True,
    ),
    "septic.sep": dict(
        columns=['name', 'q_rate', 'bod', 'tss', 'nh4_n', 'no3_n',
                 'no2_n', 'org_n', 'min_p', 'org_p', 'fcoli',
                 'description'],
        numeric=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        text_tail=True,
    ),
    "transplant.plt": dict(
        columns=['NAME', 'LAI_INI', 'BM_INI', 'PHU_ACC_INI',
                 'FR_YRMAT', 'POP'],
        numeric=[1, 2, 3, 4, 5],
    ),
    "harv.ops": dict(
        columns=['name', 'harv_typ', 'harv_idx', 'harv_eff',
                 'harv_bm_min', 'description'],
        numeric=[2, 3, 4],
        text_tail=True,
    ),
    "graze.ops": dict(
        columns=['name', 'fert', 'bm_eat', 'bm_tramp', 'man_amt',
                 'grz_bm_min', 'description'],
        numeric=[2, 3, 4, 5],
        text_tail=True,
    ),
    "irr.ops": dict(
        columns=['name', 'amt_mm', 'eff_frac', 'sumq_frac',
                 'dep_sub', 'salt_ppm', 'no3_ppm', 'po4_ppm',
                 'description'],
        numeric=[1, 2, 3, 4, 5, 6, 7],
        text_tail=True,
    ),
    "chem_app.ops": dict(
        columns=['name', 'chem_form', 'app_typ', 'app_eff',
                 'foliar_eff', 'inject_dp', 'surf_frac',
                 'drift_pot', 'aerial_unif', 'description'],
        numeric=[3, 4, 5, 6, 7, 8],
        text_tail=True,
    ),
    "fire.ops": dict(
        columns=['name', 'chg_cn2', 'frac_burn', 'description'],
        numeric=[1, 2],
        text_tail=True,
    ),
    "sweep.ops": dict(
        columns=['name', 'swp_eff', 'frac_curb', 'description'],
        numeric=[1, 2],
        text_tail=True,
    ),
    "puddle.ops": dict(
        columns=['name', 'hydcon_mm/h', 'sed_ppm', 'orgn_ppm',
                 'sedp_ppm', 'no3_ppm', 'solp_ppm', 'nh3_ppm',
                 'no2_ppm'],
        numeric=[1, 2, 3, 4, 5, 6, 7, 8],
    ),
    "tiledrain.str": dict(
        columns=['name', 'dp', 't_fc', 'lag', 'rad', 'dist',
                 'drain', 'pump', 'lat_ksat'],
        numeric=[1, 2, 3, 4, 5, 6, 7, 8],
    ),
    "septic.str": dict(
        columns=['name', 'typ', 'yr', 'operation', 'residents',
                 'area', 't_fail', 'dp_bioz', 'thk_bioz',
                 'cha_dist', 'sep_dens', 'bm_dens', 'bod_decay',
                 'bod_conv', 'fc_lin', 'fc_exp', 'fecal_decay',
                 'tds_conv', 'mort', 'resp', 'slough1', 'slough2',
                 'nit', 'denit', 'p_sorp', 'p_sorp_max', 'solp_slp',
                 'solp_int'],
        numeric=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27],
    ),
    "filterstrip.str": dict(
        columns=['name', 'flag', 'fld_vfs', 'con_vfs', 'cha_q',
                 'description'],
        numeric=[1, 2, 3, 4],
        text_tail=True,
    ),
    "grassedww.str": dict(
        columns=['name', 'flag', 'mann', 'sed_co', 'dp', 'wd',
                 'len', 'slp', 'description'],
        numeric=[1, 2, 3, 4, 5, 6, 7],
        text_tail=True,
    ),
    "bmpuser.str": dict(
        columns=['name', 'flag', 'sed_eff', 'ptlp_eff', 'solp_eff',
                 'ptln_eff', 'soln_eff', 'bact_eff', 'description'],
        numeric=[1, 2, 3, 4, 5, 6, 7],
        text_tail=True,
    ),
    "cntable.lum": dict(
        columns=['name', 'cn_a', 'cn_b', 'cn_c', 'cn_d',
                 'description', 'treat', 'cond_cov'],
        numeric=[1, 2, 3, 4],
    ),
    "cons_practice.lum": dict(
        columns=['name', 'usle_p', 'slp_len_max', 'description'],
        numeric=[1, 2],
        text_tail=True,
    ),
    "ovn_table.lum": dict(
        columns=['name', 'ovn_mean', 'ovn_min', 'ovn_max',
                 'description'],
        numeric=[1, 2, 3],
        text_tail=True,
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
