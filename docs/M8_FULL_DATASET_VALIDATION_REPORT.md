# M8 — Full-Dataset Validation Report: Schema v0.7 → v0.8 Migration at 100,000 Records

**Status:** COMPLETE (2026-10-20). All quality gates PASS. Dataset frozen at
`outputs/m8/100k_patients_v08/`, manifest `outputs/m8/dataset_manifest.json`.

Raw machine-readable report: `docs/M8_FULL_DATASET_VALIDATION_REPORT.json`.
Validator: `integration/validate_clinical_population.py` (extended, not
duplicated, from the M4C population validator). Migration: `integration/
migrate_v07_to_v08.py`.

---

## 1. Executive Summary

Schema v0.8 (blood pressure, encounters, timeline references —
`docs/DECISIONS.md` D017) was migrated across the full 100,000-record
M5 baseline and validated at full scale, not sampled. Every record was
independently re-derived from its own untouched v0.7 source and
compared byte-for-byte against what the migration had written to disk.

* **100,000 / 100,000 structurally valid** (recomputed via
  `validate_patient`, not trusted from the record's own stored flag)
* **100,000 / 100,000 clinically consistent** (0 errors via
  `validate_clinical_consistency`)
* **0 duplicate patient IDs**, **100,000 unique IDs**
* **100,000 / 100,000 migration-integrity exact matches** — every
  output record, re-derived fresh from its v0.7 source via
  `migrate_record()`, is byte-identical to what is on disk. 0 records
  differ, 0 orphaned in either direction (no output without a source, no
  source without an output)
* **16,297 clinical warnings**, all pre-existing/documented limitations
  (none newly introduced — see §4)
* Original v0.7 dataset confirmed **untouched**: still 100,000 records,
  still schema 0.7

This is the strongest form of migration verification available short of
a second independent implementation: not "the output looks right," but
"re-running the exact migration logic against the exact original input
reproduces the exact file on disk, for all 100,000 records."

---

## 2. Validation Methodology

Reused, not duplicated: `integration/validate_clinical_population.py`
already existed (M4C) for structural + clinical consistency validation
over a population directory. Extended for v0.8 (new `_dict_to_patient`
import from the migration module, which handles `BloodPressure`/
`Encounter`/`TimelineEvent.reference_id`; structural validity recomputed
rather than trusted from the stored flag) rather than writing a second
validator.

Three checks run in a single streaming pass over all 100,000 files
(memory-bounded — see §6):

1. **Structural** — `validation/structural.py` `validate_patient()`,
   independently recomputed per record.
2. **Clinical consistency** — `validation/clinical_consistency.py`
   `validate_clinical_consistency()`, which itself recomputes expected
   values from the generation functions rather than trusting stored
   derivations.
3. **Migration integrity** (`--compare-source`) — for every record, the
   matching v0.7 source file is loaded and run back through
   `migrate_record()` (the real migration function), and the result is
   compared field-for-field against the actual v0.8 file on disk. This
   catches disk corruption, truncation, and migration non-determinism —
   not just "does this record look structurally fine in isolation."

---

## 3. Structural Validation

| Check | Result |
|---|---|
| Records processed | 100,000 |
| Load errors (bad JSON, truncated, unreadable) | **0** |
| Structurally valid (recomputed) | **100,000 / 100,000** |
| Duplicate patient IDs | **0** |
| Unique patient IDs | **100,000** |
| Schema version | **100,000 / 100,000 at v0.8** |

---

## 4. Clinical Consistency

| Check | Result |
|---|---|
| Clinically consistent (0 errors) | **100,000 / 100,000** |
| Total clinical warnings | 16,297 |

### Warnings by kind — all pre-existing, none introduced by this migration

| Warning | Count | % of dataset | Status |
|---|---|---|---|
| LDL clipped at the documented floor (feasible, < 30 mg/dL) | 7,548 | 7.55% | Pre-existing M4B sampling artefact (independent TC/TG/HDL marginals) |
| `ecg.superclasses` empty (PTB-XL label gap) | 6,466 | 6.47% | Pre-existing, unrelated to this migration |
| Lipid panel internally impossible (TC < HDL + TG/5) | 2,283 | 2.28% | Pre-existing M4B sampling artefact |

**Combined, 9,831 records (9.83%) have an LDL value that is the clip
floor rather than a Friedewald derivation** (7,548 feasible-but-clipped
+ 2,283 internally impossible) — consistent with the 50-record pilot's
estimate (9.8%) and the earlier 2,000-record sample (9.6%), now an exact
full-dataset count. **This is a known limitation carried from M4B, not
introduced by schema v0.8** (see `validation/pilot_50_records/reports/
validation_report.md` §6.1 for the full root-cause analysis and
remediation options — not actioned here per this task's explicit
instruction not to change lipid sampling/clipping without a separate
decision).

Checks performed (all 100,000 records): `blood_pressure_hypertension_
label_consistency`, `bmi_height_weight_arithmetic_skipped_height_
weight_unpopulated`, `diabetes_hba1c_consistency`, `diagnosis_risk_
factor_consistency`, `ecg_remains_metadata_only`, `encounter_timeline_
referential_integrity`, `hba1c_plausibility_given_age_sex`, `hyper
lipidemia_vs_lipid_interpretations_intentionally_not_compared`, `lipid_
panel_internal_feasibility`, `lipid_panel_interpretation_consistency`,
`medical_history_diagnosis_consistency`, `medication_diagnosis_
consistency`, `timeline_labs_date_consistency`, `unimplemented_domains_
confirmed_absent`.

---

## 5. Migration Integrity

| Check | Result |
|---|---|
| Source records (v0.7) checked | 100,000 |
| **Matching recomputation exactly** | **100,000 / 100,000** |
| Differing from recomputation | **0** |
| `migrate_record()` internal errors | **0** |
| Output records with no matching source | **0** |
| Source records with no matching output | **0** |

Every field the migration is allowed to change (`blood_pressure`,
`encounters`, `clinical_timeline`, `provenance`, `validation`,
`demographics.height_cm`/`weight_kg`) matches a fresh re-derivation
exactly. Every field the migration must preserve (`patient_id`,
`risk_factors`, `lipid_panel`, `lipid_interpretations`, `diagnoses`,
`medical_history`, `medications`, `labs`, `ecg`, `echo`,
`family_history`) is confirmed unmodified — enforced both by the
migration's own `_UNCHANGED_FIELDS` check at write time and
independently re-verified here by this separate validator.

**No partial writes, no truncated files, no unintended schema mixing,
no record orphaned by the migration in either direction.**

---

## 6. New-Field Statistics (Full Dataset)

### Blood pressure

| Statistic | Systolic (mmHg) | Diastolic (mmHg) | Pulse pressure (mmHg) |
|---|---|---|---|
| n | 100,000 | 100,000 | 100,000 |
| mean | 125.04 | 82.53 | 42.51 |
| sd | 15.54 | 10.26 | 10.47 |
| min | 70 | 41 | 20 |
| max | 191 | 130 | 89 |

Reference: published NFHS-5 pulse pressure 42.9 ± 9.5 mmHg — this
dataset's 42.51 mean matches to within 1%.

| Check | Result |
|---|---|
| Present (all records) | 100,000 / 100,000 |
| Systolic > diastolic violations | **0** |
| Pulse pressure < 20 mmHg (the declared engineering floor) | **0** |
| Raised BP (SBP≥140 or DBP≥90) | 31,655 (31.66%) |
| Age-band held constant beyond NFHS-5 source coverage | 52,684 (52.68%) |
| Distinct systolic values observed | 120 |
| Distinct diastolic values observed | 83 |

The 52.68% age-extrapolation rate is the single largest disclosed
limitation of the blood-pressure design — see
`configs/indian_population.yaml` `risk_factors.blood_pressure.
limitations` (a) and `validation/pilot_50_records/reports/
evidence_and_assumptions.md` §1.5(a) for the full rationale (the oldest
available NFHS-5 band is held constant rather than extrapolated
further, which understates rather than invents BP in older patients).

### Encounters / timeline

| Check | Result |
|---|---|
| Records with `encounters` populated | 100,000 / 100,000 (0% missing) |
| Records with `blood_pressure` populated | 100,000 / 100,000 (0% missing) |

### Missingness, with reason — none accidental

| Field | Missing | % | Reason |
|---|---|---|---|
| `family_history` | 100,000 | 100% | Open human scope decision, not an evidence gap |
| `echo` | 100,000 | 100% | Scope entirely open |
| `labs` | 11,457 | 11.46% | Exactly the diabetic patients — HbA1c generated only for non-diabetics |
| `medications` | 90,795 | 90.80% | Treatment-rate gated (NNMS 14.5%/36.1%) — matches design |
| `diagnoses` / `medical_history` | 57,179 | 57.18% | Patients with neither the hypertension nor diabetes flag |
| `encounters` | 0 | 0% | Newly populated by this migration |

### Duplicates, ECG

| Check | Result |
|---|---|
| Exact duplicate records (full-record hash) | **0** |
| `ecg.signal_available = true` | **0** (unchanged — D003 boundary intact) |
| `ecg.superclasses` empty | 6,466 (6.47%) — pre-existing PTB-XL label gap, unrelated to this migration |

---

## 7. Remediation Classification

Per the task's four-way classification:

| Category | Findings |
|---|---|
| **1. Safe automatic fixes** | None required at the dataset level — 0 structural errors, 0 clinical errors, 0 migration-integrity mismatches across all 100,000 records. (One safe fix WAS made in the validator tooling itself during this pass — see §8.) |
| **2. Engineering issues** | None found in the dataset. (The ECG evaluation methodology fix — re-evaluating the inherited GAN against held-out rather than training data — is a separate Category-2 fix; see `docs/M8_ECG_HELDOUT_PILOT_REPORT.md`.) |
| **3. Clinical/statistical decisions (deferred, not actioned)** | Lipid panel independent-marginal sampling (9.83% LDL-at-floor); hyperlipidemia diagnosis definition; family-history scope; BP pulse-pressure-floor value; whether `encounters` should remain a structural container |
| **4. Accepted limitations (documented)** | Height/weight (no evidence), family_history (scope decision), echo (scope open), BP age-extrapolation (52.68%), ECG waveform (not generated, D003) |

No category-3 item was resolved unilaterally in this pass, per the
task's explicit instruction.

---

## 8. Note: A Defect Found and Fixed in the Validation Tooling Itself

Two bugs were found and fixed in `integration/validate_clinical_
population.py` while bringing it up to full-dataset scale — both are
engineering fixes to the *validator*, not the dataset, and are recorded
here for transparency:

1. **An accidental O(n²) scan.** An early version of the migration-
   integrity check re-globbed the entire 100,000-file source directory
   inside a per-output-record list comprehension. Fixed by computing
   the source-file set once, outside the loop.
2. **Unbounded memory growth.** The first full-scale attempt held three
   full 100,000-record populations in memory simultaneously (raw
   dicts, reconstructed `Patient` objects, and validation results) and
   was killed by the host for memory pressure (~4GB free at the time).
   Rewritten as a single streaming pass that visits each file once and
   keeps only small aggregates (counts, `Counter`s, and a Welford
   running-statistics accumulator for BP mean/SD) — confirmed flat at
   ~185-205MB resident memory regardless of population size, rather
   than growing with it.

Both fixes were regression-tested against a 99-record sample (identical
output before and after) and the full 142-test project suite (142/142
passing) before being used for this report's full-scale run.

---

## 9. Final Dataset Status

**READY.** `outputs/m8/100k_patients_v08/` is the authoritative
schema-v0.8 dataset: 100,000 records, 0 structural errors, 0 clinical
errors, 100,000/100,000 migration-integrity exact matches against the
untouched v0.7 source at `outputs/m5/100k_patients/`. Frozen with a
manifest at `outputs/m8/dataset_manifest.json` (same convention as
`outputs/m5/dataset_manifest.json`), recording the git HEAD commit,
validation results, and accepted limitations.

**Not yet resolved** (tracked, not blocking this freeze): the lipid
independent-sampling artefact (§4, §7), which would require a
D011-level decision to correct, and the four other open questions in
`validation/pilot_50_records/reports/validation_report.md` §6.
