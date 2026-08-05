# SWAT+ Source Inventory

> **Historical (superseded).** This inventory documents the *initial*
> `Ames_sub1` / `Osu_1hru` bootstrap. As of release `2026.2.0` the core files
> are regenerated from the official SWAT+ Editor reference dataset
> (`swatplus_datasets.sqlite`); see `docs/bootstrap_report.md`. The direct-read
> discovery below still stands — those four files remain supplemental because
> the editor dataset does not manage them. The "missing from both sources"
> list is also superseded: `flo_con.dtl` and `scen_lu.dtl` are present in the
> official dataset and are now sourced from it.

Source: `swat-model/swatplus` @ `cb442f7c05fc3bfc34349c446010f452d2737ca0`  
Priority: Ames_sub1 -> Osu_1hru

- Ames_sub1 files: 110
- Osu_1hru files: 100
- In both directories: 45

## Fixed-filename (direct-read) databases

Discovered by inspecting the SWAT+ source. These are opened by a literal filename and are **not** driven by `file.cio`.

| File | Reader source |
|---|---|
| `manure_db.frt` | `src/manure_db_read.f90` |
| `manure_om.frt` | `src/manure_orgmin_read.f90` |
| `puddle.ops` | `src/mgt_read_puddle.f90` |
| `transplant.plt` | `src/plant_transplant_read.f90` |

## Expected files missing from both sources

- `flo_con.dtl`
- `metals.mtl`
- `pathogens.pth`
- `salt.slt`
- `scen_lu.dtl`

## Duplicate filenames (in both directories)

| File | Ames vs OSU |
|---|---|
| `aqu_catunit.ele` | differ |
| `cntable.lum` | differ |
| `codes.bsn` | differ |
| `cons_practice.lum` | differ |
| `erosion.txt` | identical |
| `fertilizer.frt` | differ |
| `file.cio` | differ |
| `filterstrip.str` | differ |
| `grassedww.str` | differ |
| `graze.ops` | differ |
| `harv.ops` | differ |
| `hru-data.hru` | differ |
| `hru.con` | differ |
| `hydrology.hyd` | differ |
| `irr.ops` | differ |
| `landuse.lum` | differ |
| `ls_unit.ele` | differ |
| `lum.dtl` | differ |
| `management.sch` | differ |
| `manure_db.frt` | differ |
| `manure_om.frt` | differ |
| `mgt_out.txt` | differ |
| `object.cnt` | differ |
| `ovn_table.lum` | differ |
| `parameters.bsn` | differ |
| `pcp.cli` | differ |
| `plant.ini` | differ |
| `plants.plt` | differ |
| `print.prt` | differ |
| `salt_aqu.ini` | identical |
| `salt_channel.ini` | identical |
| `salt_hru.ini` | identical |
| `septic.str` | differ |
| `snow.sno` | differ |
| `soil_plant.ini` | differ |
| `soils.sol` | differ |
| `sweep.ops` | differ |
| `tiledrain.str` | differ |
| `tillage.til` | differ |
| `time.sim` | differ |
| `tmp.cli` | differ |
| `topography.hyd` | differ |
| `treatment.trt` | identical |
| `weather-sta.cli` | differ |
| `weather-wgn.cli` | differ |

## Classification

| File | In Ames | In OSU | Classification |
|---|:---:|:---:|---|
| `.testfiles.txt` | x |  | model output |
| `2010` |  | x | unknown, needs review |
| `Imsilpcp.pcp` |  | x | project-specific input |
| `Imsilsol.slr` |  | x | project-specific input |
| `Imsiltmp.tmp` |  | x | project-specific input |
| `Imsilwind.wnd` |  | x | project-specific input |
| `ames.pcp` | x |  | project-specific input |
| `ames.tem` | x |  | project-specific input |
| `ames.tmp` | x |  | project-specific input |
| `aqu_catunit.ele` | x | x | project-specific input |
| `aqu_dr.swf` |  | x | project-specific input |
| `aquifer.aqu` |  | x | project-specific input |
| `aquifer.con` |  | x | project-specific input |
| `area_calc.out` | x |  | model output |
| `basin_aqu_aa.txt` | x |  | model output |
| `basin_carbon_aa.txt` | x |  | model output |
| `basin_carbon_all.txt` | x |  | model output |
| `basin_cha_aa.txt` | x |  | model output |
| `basin_crop_yld_aa.txt` | x |  | model output |
| `basin_crop_yld_yr.txt` | x |  | model output |
| `basin_ls_aa.txt` | x |  | model output |
| `basin_nb_aa.txt` | x |  | model output |
| `basin_psc_aa.txt` | x |  | model output |
| `basin_pw_aa.txt` | x |  | model output |
| `basin_res_aa.txt` | x |  | model output |
| `basin_sd_cha_aa.txt` | x |  | model output |
| `basin_sd_chamorph_aa.txt` | x |  | model output |
| `basin_sd_chanbud_aa.txt` | x |  | model output |
| `basin_totc.txt` | x |  | model output |
| `basin_wb_aa.txt` | x |  | model output |
| `bmpuser.str` |  | x | shared reference database |
| `cal_parms.cal` |  | x | shared reference database |
| `calibration.cal` |  | x | unknown, needs review |
| `calibration.cal.org` |  | x | unknown, needs review |
| `carbon.bsn` | x |  | project-specific input |
| `carbon_lyr.bsn` | x |  | project-specific input |
| `chan_dat.swf` |  | x | project-specific input |
| `chan_dr.swf` |  | x | project-specific input |
| `chandeg.con` |  | x | project-specific input |
| `channel-lte.cha` |  | x | project-specific input |
| `checker.out` | x |  | model output |
| `chem_app.ops` |  | x | shared reference database |
| `cntable.lum` | x | x | shared reference database |
| `co2.out` | x |  | model output |
| `codes.bsn` | x | x | project-specific input |
| `cons_practice.lum` | x | x | shared reference database |
| `crop_yld_aa.txt` | x |  | model output |
| `crop_yld_yr.txt` | x |  | model output |
| `cs_aqu.ini` | x |  | project-specific input |
| `cs_channel.ini` | x |  | project-specific input |
| `cs_hru.ini` | x |  | project-specific input |
| `deposition_aa.txt` | x |  | model output |
| `diagnostics.out` | x |  | model output |
| `erosion.out` | x |  | model output |
| `erosion.txt` | x | x | model output |
| `fertilizer.frt` | x | x | shared reference database |
| `field.fld` |  | x | project-specific input |
| `file.cio` | x | x | unknown, needs review |
| `file_cio.swf` |  | x | project-specific input |
| `files_out.out` | x |  | model output |
| `filterstrip.str` | x | x | shared reference database |
| `fire.ops` |  | x | shared reference database |
| `fort.2222` |  | x | model output |
| `fort.7777` | x |  | model output |
| `grassedww.str` | x | x | shared reference database |
| `graze.ops` | x | x | shared reference database |
| `harv.ops` | x | x | shared reference database |
| `hru-data.hru` | x | x | project-specific input |
| `hru.con` | x | x | project-specific input |
| `hru_carbon_aa.txt` | x |  | model output |
| `hru_cbn_lyr.txt` | x |  | model output |
| `hru_dat.swf` |  | x | model output |
| `hru_exco.swf` |  | x | model output |
| `hru_ls_aa.txt` | x |  | model output |
| `hru_nb_aa.txt` | x |  | model output |
| `hru_ncycle_aa.txt` | x |  | model output |
| `hru_nut_carb_gl_aa.txt` | x |  | model output |
| `hru_orgc.txt` | x |  | model output |
| `hru_plc_stat.txt` | x |  | model output |
| `hru_plcarb_aa.txt` | x |  | model output |
| `hru_pw_aa.txt` | x |  | model output |
| `hru_resc_stat.txt` | x |  | model output |
| `hru_rescarb_aa.txt` | x |  | model output |
| `hru_scf_aa.txt` | x |  | model output |
| `hru_soilc_stat.txt` | x |  | model output |
| `hru_soilcarb_aa.txt` | x |  | model output |
| `hru_totc.txt` | x |  | model output |
| `hru_wb_aa.txt` | x |  | model output |
| `hru_wet.swf` |  | x | model output |
| `hyd-sed-lte.cha` |  | x | project-specific input |
| `hydin_aa.txt` | x |  | model output |
| `hydout_aa.txt` | x |  | model output |
| `hydrology.hyd` | x | x | project-specific input |
| `hydrology.wet` |  | x | project-specific input |
| `initial.aqu` |  | x | project-specific input |
| `initial.cha` |  | x | project-specific input |
| `initial.res` |  | x | project-specific input |
| `irr.ops` | x | x | shared reference database |
| `landuse.lum` | x | x | project-specific input |
| `ls_unit.def` |  | x | project-specific input |
| `ls_unit.ele` | x | x | project-specific input |
| `lu_change_out.txt` | x |  | model output |
| `lum.dtl` | x | x | shared reference database |
| `management(CTcorn).sch` | x |  | project-specific input |
| `management.sch` | x | x | project-specific input |
| `manure_db.frt` | x | x | shared reference database |
| `manure_om.frt` | x | x | shared reference database |
| `mgt_out.txt` | x | x | model output |
| `nutrients.cha` |  | x | project-specific input |
| `nutrients.res` |  | x | project-specific input |
| `nutrients.sol` |  | x | project-specific input |
| `object.cnt` | x | x | project-specific input |
| `om_water.ini` |  | x | project-specific input |
| `ovn_table.lum` | x | x | shared reference database |
| `parameters.bsn` | x | x | project-specific input |
| `pcp.cli` | x | x | project-specific input |
| `pesticide.pes` |  | x | shared reference database |
| `plant.ini` | x | x | project-specific input |
| `plants.plt` | x | x | shared reference database |
| `precip.swf` |  | x | project-specific input |
| `print.prt` | x | x | project-specific input |
| `puddle.ops` |  | x | shared reference database |
| `recall.con` |  | x | project-specific input |
| `recall.rec` |  | x | project-specific input |
| `recall.swf` |  | x | project-specific input |
| `recall_aa.txt` | x |  | model output |
| `res_dat.swf` |  | x | project-specific input |
| `res_dr.swf` |  | x | project-specific input |
| `res_rel.dtl` |  | x | shared reference database |
| `reservoir_sed.txt` | x |  | model output |
| `rout_unit.con` |  | x | project-specific input |
| `rout_unit.def` |  | x | project-specific input |
| `rout_unit.ele` |  | x | project-specific input |
| `rout_unit.rtu` |  | x | project-specific input |
| `ru_aa.txt` | x |  | model output |
| `salt_aqu.ini` | x | x | project-specific input |
| `salt_channel.ini` | x | x | project-specific input |
| `salt_hru.ini` | x | x | project-specific input |
| `sd_chanbud_aa.txt` | x |  | model output |
| `sediment.res` |  | x | project-specific input |
| `septic.sep` |  | x | shared reference database |
| `septic.str` | x | x | shared reference database |
| `simulation.out` | x |  | model output |
| `slr.cli` |  | x | project-specific input |
| `snow.sno` | x | x | shared reference database |
| `soil_lyr_depths.sol` | x |  | project-specific input |
| `soil_plant.ini` | x | x | project-specific input |
| `soils.sol` | x | x | project-specific input |
| `success.fin` | x |  | model output |
| `sweep.ops` | x | x | shared reference database |
| `tiledrain.str` | x | x | shared reference database |
| `tillage.til` | x | x | shared reference database |
| `time.sim` | x | x | project-specific input |
| `tmp.cli` | x | x | project-specific input |
| `topography.hyd` | x | x | project-specific input |
| `transplant.plt` |  | x | shared reference database |
| `treatment.trt` | x | x | project-specific input |
| `urban.urb` |  | x | shared reference database |
| `weather-sta.cli` | x | x | project-specific input |
| `weather-wgn.cli` | x | x | project-specific input |
| `weir.res` |  | x | project-specific input |
| `wetland.wet` |  | x | project-specific input |
| `wetland_aa.txt` | x |  | model output |
| `wnd.cli` |  | x | project-specific input |
| `yield.out` | x |  | model output |

## file.cio references absent on disk

Filenames referenced by a `file.cio` slot but not present on disk (a name in `file.cio` is not proof a file exists).

### Ames_sub1

- `AMES` (category `file.cio:`)
- `nbull` (category `aquifer`)
- `bmpuser.str` (category `structural`)
- `pesticide.pes` (category `hru_parm_db`)
- `urban.urb` (category `hru_parm_db`)
- `septic.sep` (category `hru_parm_db`)
- `chem_app.ops` (category `ops`)
- `fire.ops` (category `ops`)
- `nutrients.sol` (category `soils`)

### Osu_1hru

- `written` (category `file.cio:`)
- `by` (category `file.cio:`)
- `SWAT+` (category `file.cio:`)
- `editor` (category `file.cio:`)
- `v2.2.0` (category `file.cio:`)
- `on` (category `file.cio:`)
- `2023-03-22` (category `file.cio:`)
- `04:25` (category `file.cio:`)
- `for` (category `file.cio:`)
- `SWAT+` (category `file.cio:`)
- `rev.60.5.4` (category `file.cio:`)
