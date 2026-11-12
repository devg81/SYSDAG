# v0.13 sample records for validation (5) -jatin

Prepared by -jatin on 2026-11-12. These are the same 5 patients (same seeds) as
`review_samples_v012/`, at schema v0.13 (D027). Hypertension now follows an
**age × sex** curve and diabetes an **age** curve, both from observed Indian
surveys (NFHS-5 / ICMR-NNMS under 45, LASI 45+). Previously both were flat national rates.

All 5 are structurally valid and clinically consistent, with 0 warnings.
Unlike earlier upgrades, these were **regenerated from scratch with the real
`build_patient()`**:

    python integration/regenerate_review_samples.py review_samples_v012 review_samples_v013 --reuse-ecg-from review_samples_v012

ECG metadata is reused from v0.12 because this machine has no PTB-XL. It is
picked by seed alone, so PTB-XL would return the same values.

| File | Age / sex | HTN | Diabetes | What changed vs v0.12 |
|---|---|---|---|---|
| urban_UP_age65_PAT_000001 | 65 M | yes | no | HTN onset 25.8 → 28.3 |
| young_healthy_PAT_000011 | 20.8 F | no | no | nothing (version only) |
| elderly_female_PAT_000013 | 77 F | no | yes | DM onset 50.1 → 46.0 |
| rural_smoker_PAT_000015 | 67 M | no | no | nothing (version only) |
| htn_dm_untreated_PAT_000095 | 79 M | yes | yes | HTN onset 26.3 → 27.6, DM onset 67.9 → 71.8 |

**Why the flags didn't change:** each patient's single random draw still falls
on the same side of the new age-specific probability. Across 20,000 patients the
gradient is clear. HTN is ~10% (men) / 5% (women) at 20–29, rising to 47% / 61% at 75+.
Diabetes is 2.7% at 20–29, rising to 21–24% at 60+. Onset tags now name the shared curve
(`modeled_from_age_prevalence_curve_nfhs5_lasi` / `..._nnms_lasi`).

Everything else (BP, labs, medications, family history, LAI tier, ECG) is
identical to v0.12. The frozen 100K hasn't been touched and is still v0.9.
