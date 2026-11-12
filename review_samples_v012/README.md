# v0.12 sample records for validation (5) -jatin

Prepared by -jatin on 2026-11-12. These are the same 5 patients (same seeds) as
`review_samples_v011/`, upgraded to schema v0.12 (D024). The LAI_2020 lipid
interpretation now carries a **rule-based LAI risk tier** and a personal LDL goal.
All 5 are structurally valid and clinically consistent, with 0 warnings. The
new check `lai_risk_tier_consistency` ran on every record.

| File | LAI risk factors counted | Diabetes | Tier | LDL goal | LDL | Above goal |
|---|---|---|---|---|---|---|
| urban_UP_age65_PAT_000001 | age, hypertension, low HDL (3) | no | high | <70 | 132.3 | yes |
| young_healthy_PAT_000011 | low HDL (1) | no | low | <100 | 100.6 | yes (just) |
| elderly_female_PAT_000013 | age, low HDL (2) | yes | very high | <50 | 96.3 | yes |
| rural_smoker_PAT_000015 | age, current smoking, low HDL (3) | no | high | <70 | 135.9 | yes |
| htn_dm_untreated_PAT_000095 | age, hypertension (2) | yes | very high | <50 | 83.3 | yes |

**Rule:**
- Major risk factors: age (men ≥45, women ≥55), current smoking, hypertension, low HDL (men <40, women <50).
- Diabetes + ≥2 risk factors → very high; diabetes + 0–1 → high.
- No diabetes: ≥3 → high; 2 → moderate; 0–1 → low.
- Goals: low and moderate <100, high <70, very high <50 mg/dL.
- Full evidence and limits are in `docs/DECISIONS.md` D024.

**Not modelled:** ASCVD (so no "extreme" tier), premature family CAD, organ
damage, CKD and smokeless tobacco. A real patient's tier could therefore be
higher than shown here, never lower.

**Changed vs v0.11:** the 5 new fields on the LAI_2020 interpretation, plus
provenance (schema version, generator text and timestamp). Everything else is
byte-identical, including the hyperlipidemia flag from D023.

**How these were produced:** `python integration/rederive_review_samples.py
review_samples_v011 review_samples_v012`. This runs the real generator, asserts
RNG alignment, and re-runs both validators. The frozen 100K hasn't been touched
and is still v0.9.
