# Jeff Arnold's plants.plt update (email of 2026-11-04)

These are the files Jeff Arnold sent with the email "plants.plt database"
on 2026-11-04. They're kept here unchanged, as the source of the
`database_files/plants.plt` update on `dev`. `.gitattributes` in this folder
stops Git from changing their line endings, so the checksums below match the
files as sent.

The code that reads the new layout is swat-model/swatplus
[`9360565`](https://github.com/swat-model/swatplus/commit/9360565)
("11/10 updates", 2026-11-10).

| File | What it covers | plants.plt columns |
|---|---|---|
| `plants.plt` | The database itself: 265 plants, 55 tab-separated columns | all |
| `plant_parm_changes.xlsx` | Name, units, range and default of the new and renamed parameters | 28, 50, 52, 53, `class`, `description` |
| `Herbaceous_Perennials.docx` | The new `herb_perennial` plant type, its dormancy code, and the grasses moved to it | 2 (`plnt_typ`) |
| `USLE C Factor.docx` | The simplified USLE C factor and its two coefficients | 52 `rsd_cov`, 53 `bio_cov` |
| `plant_parm_updates1.docx` | Background: perennial root depth, APEX C factor, leaf mass fractions | 28, 50, 52, 53 |
| `plant_parm_updates2.docx` | Background: APEX C factor and its coefficients | 52, 53 |
| `plant_parm_updates3.docx` | Background: perennial root depth by tree type | 50 `rt_depco` |

SHA-256:

```
19651891c1340a449968417fd7719c14047fa9704d901c3743b938c7ad1dc337  plants.plt
93137effb620f7d611b86bbe89b2ba79fe96e9797be19f4c6b4a022518982e5f  plant_parm_changes.xlsx
930885806358610e355e789e97ee5aa8704f3fd4a444d04bc50b119ad013491b  Herbaceous_Perennials.docx
8b2624cad327e8ffe43d6934cbbab04f53f8558e285eda018e28ebe9b64e29bf  USLE C Factor.docx
90fd7db68b517f656ae0a1fe16e573324be7cba7109d04c86e897d50619d1c1f  plant_parm_updates1.docx
81095614f61f7af27542515a18670c3d3cfc606bab119ede33237883c7b6ee25  plant_parm_updates2.docx
85fac1b7c0a6aa074bb89f6e51023309c0d84774263bc24323300bf2e0c9830f  plant_parm_updates3.docx
```

## Where the notes and the code differ (swatplus `e8cbd13`)

- **Root depth (column 50):** the code uses
  `rdmx * (1 - exp(-rt_depco * years))` (`pl_root_gro.f90`), the form in
  `plant_parm_updates3.docx`, with `rt_depco` per year. The
  `k * Y / Ymat` form in `plant_parm_updates1.docx` isn't what the code does,
  and the spreadsheet's unit for `rt_depco` (ha/t) should be 1/yr.
  `rt_depco` is 0 for 121 plants in the file; the model uses 0.2 for those.
- **Leaf mass fraction (column 28):** 0 for every plant in the file; the model
  uses 0.03 for 0.
- **Carbon columns:** the spreadsheet lists `meta_frac`, `str_frac`,
  `lig_frac`. Those are SWAT+ 62's carbon columns. Dev reads three lignin
  columns instead (`avg_lig_frac`, `ab_lig_frac`, `bg_lig_frac`, needed only
  with `codes.bsn` carbon = 2), and this file has none of them.
- **Herbaceous grasses:** the note calls `swgr` switchgrass and `bbls` little
  bluestem; in the file they're slender wheatgrass and big bluestem. The note's
  `timh` and `jngr` are `timo` and `jhgr` in the file.
