# M5 — 100K Baseline Synthetic Population Dataset Report

**Status:** COMPLETE. Dataset generated, fully validated, no behavioral
code change, no schema change, no human checkpoint triggered.

---

## 1. Executive Summary

Generated the project's first complete 100,000-patient baseline
synthetic Indian population dataset using the existing, unmodified
production pipeline (`integration.build_patient.build_patient`,
Schema v0.7). **0 generation errors, 0 duplicate patient IDs, 0
structural validation failures, 0 clinical-consistency errors, 0
clinical-consistency warnings** across all 100,000 records. Every
statistically-checked demographic and risk-factor distribution is
within expected sampling variation of its configured/cited target.
One expected, previously-documented structural finding is now visible
at this scale for the first time (§9) — not a defect. Generation took
23.3 minutes at ~71.5 patients/second; the dataset occupies 355.1 MB.
**Final dataset status: READY.**

---

## 2. Generation Configuration

- Pipeline: `integration.build_patient.build_patient()`, called once
  per sequence 1-100,000 via `integration.generate_population`'s
  orchestration pattern (unmodified).
- Config files: `configs/base.yaml`, `configs/indian_population.yaml`
  (both `random_seed: 42`, unmodified from the M4F-audited state).
- Schema version: **0.7** (every generated record).
- Output: `outputs/m5/100k_patients/` (gitignored, not committed).

## 3. Reproducibility Information

| Field | Value |
|---|---|
| Seed | 42 (project-established, unchanged) |
| Per-patient seed | `config["random_seed"] + sequence` (43 through 100042) |
| Schema version | 0.7 |
| Generation window (UTC) | 2026-09-26T19:27:20 → 2026-09-26T19:50:34 |
| Git HEAD commit | `4ce0e72ea27ecf224dc1008501c85b8c7f97ce9f` (extensive uncommitted local milestone work on top, per this project's standing no-per-milestone-commit convention) |
| Patient count | 100,000 |

Full machine-readable manifest: `outputs/m5/dataset_manifest.json`.

---

## 4. Generation Performance

| Metric | Value |
|---|---|
| Patients requested | 100,000 |
| Patients generated | 100,000 |
| Wall time | 1,398.2s (23.30 minutes) |
| Throughput | 71.5 patients/second, 4,291 patients/minute |
| CPU utilization | 97.6% (single-process, no parallelism — matches this project's current design) |
| RSS at steady state | ~269-275 MB (small ~9MB drift over the full run — see §14 note) |
| Generation errors | **0** |
| Malformed records | **0** |
| Duplicate patient IDs | **0** |

No expensive static resource (PTB-XL CSV, SCP label map) was reloaded
per-patient — the existing `lru_cache`-based caching (D009) held for
the entire run, confirmed by the flat memory profile.

---

## 5. Structural Validation

Ran `validation.structural.validate_patient()` (existing, unmodified)
against every one of the 100,000 reconstructed records (via
`integration.validate_clinical_population._patient_from_dict()`, the
same reconstruction path used since M4C).

| Result | Count |
|---|---|
| Valid | 100,000 / 100,000 |
| Invalid | 0 |
| Structural errors | 0 |
| Unique patient IDs | 100,000 / 100,000 |
| Duplicate patient IDs | 0 |

Checked: patient_id format, schema_version match, demographic
ranges/vocabularies (state membership, urban_rural, BMI range,
smoking_status), diagnosis code / medical_history category / medication
drug_class / medication status vocabularies, ECG signal_shape/
strat_fold, lipid range and interpretation well-formedness, lab
unit-matching, non-empty clinical_timeline. **Zero failures across every
check, at full scale.**

---

## 6. Clinical Consistency

Ran `validation.clinical_consistency.validate_clinical_consistency()`
(existing, unmodified) against every record.

| Result | Count |
|---|---|
| Clinically consistent | 100,000 / 100,000 |
| Clinical errors | **0** |
| Clinical warnings | **0** |

Checks performed (every applicable patient, all 9 checks):
`lipid_panel_interpretation_consistency` (100,000/100,000),
`diabetes_hba1c_consistency` (100,000/100,000),
`hba1c_plausibility_given_age_sex` (88,543/100,000 — exactly the
non-diabetic count, confirming the conditional gate is exact),
`hyperlipidemia_vs_lipid_interpretations_intentionally_not_compared`
(100,000/100,000 — see below),
`timeline_labs_date_consistency` (100,000/100,000),
`diagnosis_risk_factor_consistency` (100,000/100,000),
`medical_history_diagnosis_consistency` (100,000/100,000),
`medication_diagnosis_consistency` (100,000/100,000),
`unimplemented_domains_confirmed_absent` (100,000/100,000).

**D014 intentional non-reconciliation, confirmed at scale, not
"fixed":** `risk_factors.hyperlipidemia` agrees with the NCEP-based
`lipid_interpretations` entry in 70,491/100,000 (70.5%) records —
consistent with the 73-77% range M4C found at n=100 and the 70.7%
M4F found at n=1,000. Per D014 (Option B), this disagreement is an
**expected semantic difference between two independently-evidenced
variables**, not a validation error, and was correctly never flagged
as one across all 100,000 records.

---

## 7. Demographic Distributions

| Variable | Configured/cited target | Observed (n=100,000) | Exact binomial / chi-square p | Interpretation |
|---|---|---|---|---|
| Sex = male | 51.47% | 51.454% | p=0.919 | C — sampling variation |
| Urban/rural = rural | 68.84% | 68.887% | p=0.751 | C |
| Age (uniform 20-89) | mean 54.500, std 19.919 | mean 54.496, std 19.905 | — | C — matches expected uniform moments closely |
| State (35 categories, Census 2011 weights) | — | — | chi²=48.13, df=34, p=0.0549 | C — not significant at α=0.05; expected residual noise across 35 categories at n=100,000 |

---

## 8. Risk-Factor Distributions

| Variable | Configured/cited target | Observed | Exact binomial p | Interpretation |
|---|---|---|---|---|
| Hypertension | 35.5% | 35.398% | p=0.502 | C |
| Diabetes | 11.4% | 11.457% | p=0.571 | C |
| Hyperlipidemia (`risk_factors`) | 81.2% | 81.226% | p=0.837 | C |
| BMI, male (normal/overweight/obese) | 72.4% / 23.3% / 4.3% | 72.6% / 23.3% / 4.2% | — | C — essentially exact |
| BMI, female | 62.4% / 29.3% / 8.3% | 62.3% / 29.5% / 8.2% | — | C |
| Smoking, male (current) | 51.2% | 50.9% | — | C |
| Smoking, female (current) | 13.0% | 13.0% | — | C |

All five original M2C risk factors and BMI/smoking's sex-conditioned
categories remain statistically indistinguishable from their cited
targets at full scale — no implementation bias detected.

---

## 9. Clinical Distributions

| Variable | Configured/cited target | Observed | p / diff | Interpretation |
|---|---|---|---|---|
| Total cholesterol = normal | 76.0% | 76.25% | — | C |
| Triglycerides = normal | 67.9% | 68.03% | — | C |
| HDL = low, male | 66.9% | 66.66% | — | C |
| HDL = low, female | 66.9% | 67.02% | — | C |
| HbA1c generated (non-diabetic only) | exactly `n - diabetes_count` | 88,543 (== 100,000 − 11,457 exactly) | exact | D — hard rule, verified by construction |
| HbA1c mean | ≈5.16-5.49% (age-band trend) | 5.373% | — | C — consistent with the age×sex-conditioned trend at this population's mean age |
| Diagnoses == risk_factors flags (hypertension, diabetes) | exact | exact | exact | D — hard rule, verified by construction, 0 exceptions across 100,000 |
| Antihypertensive treatment rate (of hypertension diagnoses) | 14.5% | 14.72% (5,211/35,398) | p=0.239 | C |
| Antidiabetic treatment rate (of diabetes diagnoses) | 36.1% | 36.72% (4,207/11,457) | p=0.167 | C |

**NCEP/LAI composite dyslipidemia rate — investigated, not a bug:**

| Definition | Cited | Observed (n=100,000) | Exact binomial p |
|---|---|---|---|
| NCEP_ATP_III | 81.2% | 82.99% | **p<0.0001** |
| LAI_2020 | 87.3% | 85.58% | **p<0.0001** |

Both composite rates are now statistically distinguishable from their
cited headline figures — this is **expected and was already
quantified before this milestone**, not a new problem. The composite
dyslipidemia rate is not itself an independently-sampled Bernoulli
parameter; it **emerges mechanically** from three separately-sampled
category-level distributions (TC/TG/HDL, each individually confirmed
correct above) plus Friedewald-derived LDL, evaluated against each
definition's thresholds (D011/D013). D013 itself already computed that
**full independence** among the four components would imply an 86.5%
composite rate — "materially higher than the actual cited 81.2%" — and
chose Friedewald-derived LDL specifically because it "reduces but
doesn't eliminate" that gap. The M4B session log recorded this
explicitly: "empirically measured at n=100 to land at 84.0%,
intermediate between naive independence and the real figure ... not
statistically distinguishable from either" — i.e., the small-n
sampling noise was large enough to mask this already-known structural
gap. At n=100,000, that same structural gap (observed 82.99%/85.58%,
both between the cited figures and the naive-independence figure) is
now statistically visible because sampling noise has shrunk, **not
because anything changed in the generator.** Per this milestone's
explicit instruction ("do not modify established evidence-backed
generation behavior merely to improve statistical appearance"), **no
change was made.** Classification: **B — evidence/architecture
limitation, previously documented and quantified (D013), now
confirmed at scale** — not Category A.

---

## 10. Relationship Analysis

| Relationship | Type | Result | Interpretation |
|---|---|---|---|
| Sex × BMI category | **EVIDENCE-SUPPORTED RELATIONSHIP** (NNMS sex-conditioned categories) | χ²=1,425.85, df=2, p≈0 | Strongly significant, as designed — male 72.6%/23.3%/4.2% vs. female 62.3%/29.5%/8.2%, matching NNMS's documented sex differential |
| Sex × Smoking status | **EVIDENCE-SUPPORTED RELATIONSHIP** (NNMS sex-conditioned categories) | χ²=16,327.99, df=1, p≈0 | Strongly significant, as designed — male 50.9% current vs. female 13.0% current |
| Hypertension × Smoking status | **INTENTIONAL INDEPENDENCE** (no relationship modeled — no accessible adjusted-odds-ratio source, M2D-4 audit) | χ²=2.43, df=1, p=0.119; **Cramér's V=0.0049** (negligible effect size) | Not significant, and the effect size itself is essentially zero — confirms the generator does not encode a relationship here, which is exactly correct: this is a statement about generator behavior, **not** a clinical claim that hypertension and smoking are unrelated in reality |

At n=100,000, a p-value alone is not sufficient to conclude
"independence" (even a trivial real effect could reach significance at
this scale) — Cramér's V=0.0049 confirms the *effect size* is
negligible, not just that the p-value happens to exceed 0.05.

---

## 11. Missingness Analysis

| Field | Missing count | Present count | Classification |
|---|---|---|---|
| `family_history` | 100,000 (100%) | 0 | **Evidence-supported missingness** — no Indian CVD family-history source exists (D004), confirmed absent across 9+ datasets |
| `encounters` | 100,000 (100%) | 0 | **Unsupported/deferred domain** — not yet implemented |
| `echo` | 100,000 (100%) | 0 | **Unsupported/deferred domain** — scope entirely open |
| `labs` | 11,457 missing (11.457%) | 88,543 present | **Evidence-supported missingness** — `labs` (HbA1c) is `None` for every diabetic patient and only every diabetic patient (11,457 missing == 11,457 diabetes count, exact match); insufficient diabetic-population HbA1c evidence (M4-0) |
| `medications` | 0 (list, never `None`) | 100,000 | Not missing — always a list (possibly empty); untreated/no-diagnosis patients correctly show `[]`, not `None` |
| `diagnoses` | 0 (list, never `None`) | 100,000 | Not missing — same pattern |
| `medical_history` | 0 (list, never `None`) | 100,000 | Not missing — same pattern |

**No unexpected/accidental missingness was found.** Every missing
field's absence is either a documented evidence gap (`family_history`,
`labs` for diabetics) or a documented deferred domain (`encounters`,
`echo`) — none is a defect.

---

## 12. ECG Metadata Analysis

| Metric | Value |
|---|---|
| Patients | 100,000 |
| ECG records | 100,000 (1:1, every patient has metadata-only ECG) |
| Unique ECG IDs | 17,386 |
| IDs used exactly once (not reused) | 341 |
| IDs reused 2+ times | 17,045 |
| Total reuse occurrences | 100,000 (by definition) |
| Maximum reuse count (single ECG ID) | **17** |
| Mean reuse | 5.75× per distinct record |
| Empty-superclass records | 6,466 (6.466%) |

**Quantifying, not solving, the ECG-ID-reuse issue** (per this
milestone's explicit instruction): at 100K scale against the
~17,470-record training-fold pool, reuse is now pervasive by design —
98% of distinct records are used more than once, one record as many as
17 times. This is the same birthday-paradox effect first measured in
M3 (30 duplicate groups at n=1,000) and M4F, now fully quantified at
the target scale. The empty-superclass rate (6.466%) matches PTB-XL's
own documented ~6.5% zero-superclass rate at the 50%-confidence
threshold (M3), confirming this is an inherited characteristic of the
reused metadata source, not a defect introduced by this project. This
data is recorded as evidence for the (not-yet-made) future ECG
architecture decision — no decision is made here.

---

## 13. Storage Analysis

| Metric | Value |
|---|---|
| Total dataset size (100K, metadata-only) | 355.12 MB |
| Average bytes/patient | 3,551.2 |
| M4F 5,000-patient benchmark estimate for 100K | 0.36 GB (355 MB projected) |
| **M5 actual measurement** | **355.12 MB — matches the M4F projection almost exactly** |

Extrapolated (metadata-only schema, unchanged):

| Scale | Estimated size |
|---|---|
| 10,000 | ~35.5 MB |
| 100,000 (measured) | **355.12 MB** |
| 1,000,000 (not generated) | ~3.55 GB (linear extrapolation; not independently verified) |

**Future waveform-inclusive estimate** (rough, schema's declared
`[1000, 12]` float32 shape — not implemented, not a committed format):
+48,000 bytes/patient → +4.8 GB at 100K, +48 GB at 1M. Kept explicitly
separate from the metadata-only figures above, per this milestone's
instruction.

No cloud storage was introduced or considered necessary at this scale.

---

## 14. Known Limitations

- **Hyperlipidemia diagnosis remains undecided** (open since M4D) —
  unaffected by this milestone, does not block the 100K baseline.
- **Statin/antiplatelet medications remain ungenerated** — no
  population treatment-rate evidence exists (M4E-0); unaffected.
- **ECG-ID reuse is now pervasive at 100K** (§12) — a real, quantified,
  not-yet-decided policy question for a future ECG-architecture
  milestone; does not affect the validity of the demographic/clinical
  fields in this dataset.
- **Composite lipid-interpretation rates are now statistically
  distinguishable from their cited headline figures** (§9) — a
  previously-documented (D013), now scale-confirmed structural
  consequence of reconstructing lipid values from category-level
  evidence rather than sampling the composite directly. Not a defect;
  not corrected, per this milestone's explicit instruction.
- **A small (~9MB) memory drift** was observed over the full 100,000-
  patient run (RSS: ~266MB at patient 5,000 → ~275MB at patient
  100,000) — negligible at this scale (under 100 bytes/patient
  average) and did not cause any failure; noted for awareness, not
  investigated further as a defect, since it caused zero errors and
  would remain trivial even at 1M (~90MB extrapolated).
- **ECG waveform generation, model selection, CardioSynth/CardioSync,
  and AWS remain entirely out of scope**, as instructed.

## 15. Comparison with M4F

| Metric | M4F (5,000-patient benchmark) | M5 (100,000 actual) |
|---|---|---|
| Throughput | 71.6 patients/sec | 71.5 patients/sec — consistent |
| Memory | Flat ~265MB | ~266→275MB (small drift, see §14) — consistent order of magnitude |
| Bytes/patient | 3,551 (measured at n=5,000) | 3,551.2 (measured at n=100,000) — **identical** |
| Estimated 100K time | ~23 minutes | **23.3 minutes actual** — matches the projection closely |
| Estimated 100K storage | ~0.36 GB | **355.12 MB actual** — matches almost exactly |
| Structural/clinical validity | 100/100 at n=100 | 100,000/100,000 at n=100,000 |

M4F's benchmark projections held accurately at full scale — no
surprises in performance, memory, or storage behavior between the
5,000-patient benchmark and the actual 100,000-patient run.

## 16. Final Dataset Status

**READY.**

- Generation: 100,000/100,000 patients, 0 errors.
- Structural validation: 100,000/100,000 valid, 0 errors.
- Clinical consistency: 100,000/100,000 valid, 0 errors, 0 warnings.
- Statistical validation: every checked variable within expected
  sampling variation of its cited/configured target, except the
  already-anticipated (D013), now scale-confirmed composite
  lipid-interpretation gap (§9) — documented, not corrected.
- Relationship validation: both modeled relationships (sex×BMI,
  sex×smoking) strongly present as designed; the one checked unmodeled
  relationship (hypertension×smoking) confirmed negligible-effect-size
  independent, as intended.
- Missingness: 100% accounted for, no accidental missingness.
- ECG metadata: fully quantified, reuse pervasive at scale but
  unchanged in kind from smaller runs — a documented limitation, not a
  defect.
- Storage: 355.12 MB, well within local-machine capacity.
- **Zero behavioral code changes. Zero schema changes. No new
  datasets introduced. No human checkpoint triggered.**
