# Re-bootstrap Report (2026.2.0)

Source: **official SWAT+ Editor reference dataset**  
`swat-model/swatplus-editor` — `release/build/swatplus_datasets.sqlite` v4.0.0 (SWAT+ rev. 62)  
Method: serialized directly from the sqlite tables using SWAT+ Editor's own `fileio` writers.

This replaces the initial `Ames_sub1` / `Osu_1hru` import (see the *Superseded* section at the end). Those were model-specific watershed inputs; the files below are the official shared reference dataset, byte-for-byte what SWAT+ Editor writes into a project.

## Regenerated from the official dataset

| File | Source sqlite table | Records | SHA-256 |
|---|---|---|---|
| `cal_parms.cal` | `cal_parms_cal` | 221 | `cf2fcfc22a42…` |
| `plants.plt` | `plants_plt` | 266 | `2cbe38529769…` |
| `fertilizer.frt` | `fertilizer_frt` | 59 | `0c1a3f9dfe15…` |
| `tillage.til` | `tillage_til` | 78 | `4aeacb384c93…` |
| `pesticide.pes` | `pesticide_pst` | 233 | `02a2e98e8620…` |
| `urban.urb` | `urban_urb` | 18 | `6cb90fd05c38…` |
| `septic.sep` | `septic_sep` | 26 | `80539db6b5b9…` |
| `snow.sno` | `snow_sno` | 1 | `4f6a2acb0561…` |
| `bmpuser.str` | `bmpuser_str` | 1 | `25e144c3802c…` |
| `filterstrip.str` | `filterstrip_str` | 2 | `f060b701955d…` |
| `grassedww.str` | `grassedww_str` | 3 | `ca4c6d71c608…` |
| `septic.str` | `septic_str` | 2 | `3361d5745a8a…` |
| `tiledrain.str` | `tiledrain_str` | 1 | `9ac8069273df…` |
| `cntable.lum` | `cntable_lum` | 52 | `a4362215f2a2…` |
| `cons_practice.lum` | `cons_prac_lum` | 38 | `ec13773bbc99…` |
| `ovn_table.lum` | `ovn_table_lum` | 20 | `b4e5b17db4d3…` |
| `harv.ops` | `harv_ops` | 16 | `25222d3ea913…` |
| `graze.ops` | `graze_ops` | 12 | `6915ed7648da…` |
| `irr.ops` | `irr_ops` | 4 | `21c465338241…` |
| `chem_app.ops` | `chem_app_ops` | 12 | `d94b0bd77d33…` |
| `fire.ops` | `fire_ops` | 3 | `5d4a399fa5e5…` |
| `sweep.ops` | `sweep_ops` | 1 | `1d0bd66c8a12…` |
| `lum.dtl` | `d_table_dtl` | 40 | `bd9c5197f49b…` |
| `res_rel.dtl` | `d_table_dtl` | 160 | `5d314eafbe0b…` |
| `scen_lu.dtl` | `d_table_dtl` | 13 | `05877d330e75…` |
| `flo_con.dtl` | `d_table_dtl` | 14 | `f6341e0ec90f…` |

Decision-table files (`lum.dtl`, `res_rel.dtl`, `scen_lu.dtl`, `flo_con.dtl`) are all drawn from the shared `d_table_dtl` table, split by its `file_name` column; the record count is the number of decision tables in each.

## Supplemental files (not in the official dataset)

These real SWAT+ files have no table in `swatplus_datasets.sqlite`, so they cannot be regenerated from it. They are retained unchanged from the earlier import and tracked in `metadata/external_sources.json`.

| File | Why supplemental | Status |
|---|---|---|
| `manure_db.frt` | direct-read DB, not managed by the editor dataset | available |
| `manure_om.frt` | direct-read DB, not managed by the editor dataset | available |
| `transplant.plt` | direct-read DB, not managed by the editor dataset | available |
| `puddle.ops` | direct-read DB, not managed by the editor dataset | available |
| `pathogens.pth` | editor table ships empty; example/seed values retained | needs_review |
| `metals.mtl` | no editor table; confirmed unread by SWAT+ 62 | needs_review |
| `salt.slt` | no editor table; confirmed unread by SWAT+ 62 | available |

## Superseded: initial Ames/OSU bootstrap

Release `2026.1.0` imported each file from `swat-model/swatplus` @ `cb442f7c05fc3bfc34349c446010f452d2737ca0` (`refdata/Ames_sub1` first, `refdata/Osu_1hru` fallback). That import — and the interim per-file schema corrections applied to it — is preserved in git history and `CHANGELOG.md`. It was replaced wholesale by this re-bootstrap because the Ames/OSU files are model-specific inputs, not the official shared reference dataset.

