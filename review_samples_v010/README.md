# v0.10 sample records for validation (5)

Same 5 patients (same seeds) as `review_samples_v09/`, regenerated with schema
v0.10 (D022). Compare file-by-file. Each file carries its own validation
result under `validation` (structural) and `validation.clinical_consistency`.
All 5: structurally valid, clinically consistent, 0 warnings.

| File | v0.9 -> v0.10, what to check |
|---|---|
| urban_UP_age65_PAT_000001 | Lipids 307/77.8/20.1/271.3 -> 197.7/154.7/34.5/132.3. HTN onset 25.8 (modeled). |
| young_healthy_PAT_000011 | Within NFHS-5 age range: BP confidence "moderate". |
| elderly_female_PAT_000013 | Diabetic: labs was null, now HbA1c 10.41 (treated, observed distribution). BP 119/84 (PP 35) -> 125/77 (PP 48). |
| rural_smoker_PAT_000015 | TG 390/LDL 37 -> TG 275/LDL 136 (high TG now goes with higher TC). |
| htn_dm_untreated_PAT_000095 | BP 184/118 -> 141/86. HbA1c 9.58, tagged borrowed/low (untreated). Was "on meds" in v0.9; the treatment draw moved with the RNG change, now untreated. |

Fields new in v0.10: `labs[].derivation/confidence`, `blood_pressure.confidence`,
`diagnoses[].age_at_onset_years/onset_date/onset_derivation/onset_confidence`,
timeline event `condition_onset_modeled`. `diagnosed_date` stays null on purpose.
Ages are rounded to 2 decimals. Unchanged between versions: age, sex, state,
urban/rural, BMI, smoking, the three risk-factor flags, AQI. Re-drawn (same
distributions, different random numbers, because the RNG order changed after
the lipid step): medication treatment, BP, family history. This is why
PAT_000013 is now treated and PAT_000095 untreated, and why family history
differs for PAT_000001 and PAT_000013.
