# 2026-11-12 — M9: v0.10 generator improvements from external review

## Request
Reviewer scored 10 records 7.9/10. Fix in order: lipid realism (incl. LDL=30
clamp), BP above NFHS-5 range, HbA1c for diabetics plus empty convention,
longitudinal dimension, hyperlipidemia prevalence, LAI vs NCEP, small items.
Protect 9 behaviours. Deliver code, report, before/after, 5K cohort checks,
regression tests, open questions. Also: gave the user 5 v0.9 sample records
(`review_samples_v09/`) and stopped 2 stuck background `du`/`find` scans.

## Evidence gathered (web)
- ICMR-INDIAB phase I lipids (PMC4016101, Table 3): TC 158+/-40, HDL 39+/-12,
  LDL 91+/-32, TG GM 116. No correlation coefficients.
- ICMR-INDIAB-13 (PMID 35461575): 36.3% of self-reported diabetics HbA1c<7%.
- INDIAB phase I glycaemic (PMC4135327): regional HbA1c 8.0-9.1, SD 2.0-2.4.
- Not found: Indian lipid correlation matrix, LASI BP means by age,
  INDIAB-17 age-specific prevalence, national mean HbA1c.

## Changes
- `generation/indian_population.py`: joint lipid sampler (reject, never clamp),
  diabetic HbA1c, BP extrapolation + confidence, onset model, age 2 dp, child
  RNG streams for lipids/HbA1c.
- `configs/indian_population.yaml`: lipid_panel.joint_model, hba1c_diabetes,
  blood_pressure.beyond_coverage_extrapolation, onset_model, LAI note.
- `schemas/patient_schema.py`: v0.10; Lab.derivation/confidence,
  BloodPressure.confidence, Diagnosis onset fields, condition_onset_modeled event,
  empty-value + treatment notes.
- `generation/clinical_history.py`, `integration/build_patient.py`: onset wiring,
  provenance text (also fixed stale "SBP/DBP correlation not modeled").
- `validation/clinical_consistency.py`: HbA1c for all, LDL==Friedewald check,
  onset checks, onset timeline events.
- Tests: 6 old tests updated to the v0.10 contract; new
  `tests/test_v010_review_fixes.py` (12 tests incl. the 9 protected behaviours).
- `integration/review_v010_report.py` -> `docs/V010_REVIEW_COHORT_CHECKS.json`.
- Reports: `docs/V010_CHANGE_REPORT.md`, `docs/DECISIONS.md` D022, PROJECT_STATE.

## Results
187/187 tests pass. 5,000 records: r(lnTG,HDL) -0.36 (was -0.03); LDL at 30.0
0% (was 7.26%); LDL != Friedewald 0% (was 7.18%); LDL>=130 22.8% (target 20.9);
NCEP dyslipidaemia 80.9% (81.2); treated-diabetic HbA1c<7 34.7% (36.3); older
pulse pressure now widens (women 80-89 PP 62, was 44).

## Datasets
None regenerated. Frozen 100K stays v0.9. v0.10 regeneration (~2 h) awaits approval.

## Open questions
See `docs/V010_CHANGE_REPORT.md` (9 items; #1 = reversing D014 needs the user).

## Follow-up: 5 v0.10 sample records
Generated the same 5 patients as `review_samples_v09/` at v0.10 into
`review_samples_v010/` (with README). All 5 structurally valid and clinically
consistent, 0 warnings. Unchanged vs v0.9: demographics, BMI, smoking, flags,
AQI. Re-drawn by the RNG-order change: treatment, BP, family history.
