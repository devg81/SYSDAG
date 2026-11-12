# v0.11 sample records for validation (5)

The same 5 patients (same seeds) as `review_samples_v010/`, upgraded to schema
v0.11 (D023: `risk_factors.hyperlipidemia` is now **derived** from the patient's
own lipid panel, using the NCEP ATP III dyslipidemia verdict, instead of being an
independent 81.2% coin flip). Compare file by file with `review_samples_v010/`.

All 5 are structurally valid and clinically consistent, with 0 warnings. The new
check `hyperlipidemia_derived_from_lipid_interpretations` ran on every record.

| File | v0.10 → v0.11 |
|---|---|
| urban_UP_age65_PAT_000001 | No value change (flag true, NCEP abnormal: TG, HDL, LDL). |
| young_healthy_PAT_000011 | No value change (flag true, NCEP abnormal: HDL 47 < 50 for women). |
| elderly_female_PAT_000013 | No value change (flag true, NCEP abnormal: HDL). |
| rural_smoker_PAT_000015 | No value change (flag true, NCEP abnormal: TC, TG, HDL, LDL). |
| htn_dm_untreated_PAT_000095 | **hyperlipidemia true → false.** Panel 143.2 / 70.4 / 45.8 / 83.3 (TC/TG/HDL/LDL) is normal under NCEP and LAI, so the old "true" was the contradiction D023 removes. |

Changed in every file: `provenance.schema_version` (0.10 → 0.11),
`provenance.generator` (states that hyperlipidemia is derived, D023) and
`provenance.generated_at`. Nothing else changed: demographics, risk-factor flags,
lipids, HbA1c, BP, medications, family history, AQI, onset, ECG metadata and
timeline are byte-identical to v0.10.

How these were produced: `python integration/rederive_review_samples.py
review_samples_v010 review_samples_v011`. The script re-runs the real generator
with each record's seed, **asserts** every stored generated field is identical
(proving the D023 placeholder draw kept the random-number stream aligned), and
then swaps in the derived flag and re-runs the real structural and clinical
validators. `build_patient()` was not used because the machine that produced
these had no PTB-XL CSVs or working pandas. The ECG metadata is carried over
from v0.10 unchanged.

The frozen 100K dataset hasn't been touched and is still v0.9.
