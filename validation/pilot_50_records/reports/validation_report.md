# Validation Report — 50-Record Pilot, Schema v0.8

| | |
|---|---|
| **Batch** | `validation/pilot_50_records/output/patient_records_50.json` |
| **Records** | exactly 50, all unique patient ids, all schema v0.8 |
| **Source** | `outputs/m5/100k_patients/` (100,000 records, schema v0.7) — opened read-only, unmodified |
| **Selection** | `numpy.random.default_rng(8).choice(100000, size=50, replace=False)` → `PAT_%06d` of index+1, sorted. Uniform without replacement; **not** purposive or hand-picked |
| **Entry point** | `integration/migrate_v07_to_v08.py` |
| **Tests** | **142 passed, 0 failed** (104 pre-existing + 38 new M8 unit tests), plus **37 passed** pilot gates |
| **Recommendation** | **READY TO SEND WITH DISCLOSED LIMITATIONS** — see §7 |

Structural validation, cross-field consistency and clinical-plausibility
review are reported **separately** below, as required. Passing JSON
validation is not treated as clinical validation anywhere in this report.

---

## 1. What changed

| Field | Change |
|---|---|
| `blood_pressure` | **NEW.** SBP/DBP in whole mmHg, conditional on the already-primary hypertension label, using that label's own published definition as the boundary. Carries `measured_at`, `age_band_source`, `extrapolated_beyond_source_age_range`, `source` |
| `encounters` | **NEW.** One `synthetic_baseline_assessment` per record — a declared structural container for the record's single measurement cross-section, **not** a healthcare visit |
| `clinical_timeline` | **EXTENDED.** `TimelineEvent` gained `reference_id`; two events per record, the second indexing the encounter by id |
| `demographics.height_cm` / `weight_kg` | Written as explicit `null` (previously absent-by-default). Still not generated — no evidence |
| `provenance` | `schema_version` 0.7 → 0.8; generator string **appended** to (never replaced); NFHS-5 added to `source_datasets` |
| `validation` | Re-run; `validation_version` now `structural-0.3+clinical-0.2` |

**Everything else is byte-identical**, and that is enforced in code, not
asserted in prose: `migrate_v07_to_v08.py`'s `_UNCHANGED_FIELDS`
compares `patient_id`, `risk_factors`, `family_history`,
`medical_history`, `diagnoses`, `medications`, `labs`, `lipid_panel`,
`lipid_interpretations`, `ecg` and `echo` before and after, and a
difference is a hard error that blocks the write.

---

## 2. Structural validation — PASS

Run via the project's own `validation/structural.py` (extended for the
new fields), not a reimplementation.

| Check | Result |
|---|---|
| Exactly 50 records in the batch | **PASS** |
| Valid JSON | **PASS** |
| Unique patient ids | **PASS** (50/50 distinct) |
| Schema compliance, all records | **PASS** (0 errors) |
| All records at schema v0.8 | **PASS** (50/50) |
| `validated: true` and empty `errors` in every record | **PASS** |
| BP types are whole-mmHg `int` (not float, not bool) | **PASS** |
| BP within physiological bounds (70–260 / 40–160) | **PASS** |
| BP provenance fields present and non-null | **PASS** |
| `encounter_type` within `ENCOUNTER_TYPES` | **PASS** |
| `event_type` within `TIMELINE_EVENT_TYPES` | **PASS** |
| Deferred fields present-and-null, not absent | **PASS** |
| No encounter with empty `recorded_measurements` | **PASS** |

---

## 3. Referential integrity — PASS

| Check | Result |
|---|---|
| Diagnosis ids unique within each patient, prefixed with the patient id | **PASS** |
| Every `medical_history.diagnosis_id` resolves to a real diagnosis | **PASS** |
| Every medication resolves to a diagnosis **and** its drug class matches that diagnosis's code | **PASS** |
| Every encounter's `patient_id` equals the record's own | **PASS** |
| Encounter ids unique within each patient | **PASS** |
| Every encounter is indexed by exactly one timeline event | **PASS** |
| No `reference_id` appears in more than one timeline event | **PASS** |
| No dangling `reference_id` | **PASS** |
| Encounters only claim measurements that exist on the record | **PASS** |
| Encounter date agrees with `labs.measured_at` and `blood_pressure.measured_at` | **PASS** |
| No timeline event predates `synthetic_record_created` | **PASS** |

---

## 4. Clinical consistency — PASS

Run via `validation/clinical_consistency.py`, which recomputes expected
values from the generation functions rather than keeping a second copy
of each rule.

| Check | Result |
|---|---|
| Systolic exceeds diastolic wherever both are populated | **PASS** (50/50) |
| BP agrees with the hypertension label's own definition | **PASS** (50/50) |
| Treated hypertensives are **not** forced to look uncontrolled | **PASS** — 1 of 3 treated patients is controlled |
| Diagnoses are exactly the promotion of their risk-factor flags | **PASS** |
| Hyperlipidemia diagnosis still absent (D015) | **PASS** |
| `medical_history` matches recomputation from diagnoses | **PASS** |
| Medication eligibility follows the approved treatment logic | **PASS** |
| LDL = Friedewald, subject to its documented clip range | **PASS** |
| Lipid interpretations match recomputation from raw values | **PASS** |
| HbA1c present for non-diabetics, absent for diabetics, 4.0–6.4%, unit `%` | **PASS** (46 present / 4 absent) |
| Timeline dates do not contradict linked record dates | **PASS** |
| BMI ↔ height/weight arithmetic | **SKIPPED, recorded as skipped** — height/weight unpopulated; the check self-reports as `bmi_height_weight_arithmetic_skipped_height_weight_unpopulated` rather than silently passing |
| No unsupported family history, encounter type or diagnosis code introduced | **PASS** |
| No existing valid value silently overwritten | **PASS** (enforced in code) |
| ECG still metadata-only, `signal_available: false` | **PASS** (50/50) |
| Echo still null | **PASS** (50/50) |

### Warnings raised — 6 across the batch (disclosure, not failure)

| Warning | Count |
|---|---|
| `lipid_panel` internally impossible (TC < HDL + TG/5) | 2 |
| LDL clipped at the floor but feasible | 2 |
| `ecg.superclasses` empty (genuine PTB-XL gap, not guessed) | 2 |

All six are **pre-existing** conditions in the preserved data that M8
surfaced; none was introduced by this work. See §6.1.

---

## 5. Clinical plausibility review — PASS with one caveat

Reported separately from the mechanical checks above, because a record
can satisfy every rule and still be clinically absurd.

| Observation | Assessment |
|---|---|
| SBP 126.4 ± 15.8, DBP 84.2 ± 11.3 mmHg | Plausible for a cohort of mean age 59.8 with 38% hypertension |
| Pulse pressure 42.1 ± 10.9 mmHg (range 23–69) | **Matches the published Indian mean of 42.9 ± 9.5 to within 2%** |
| Narrow pulse pressure (< 20 mmHg) | **0 records** — this is what the declared PP floor exists for; it was 10.7% with independent SBP/DBP and 2.0% with correlation alone |
| Isolated diastolic hypertension present (e.g. 110/91 in a young adult) | Clinically real and expected in younger adults; not an artefact |
| One treated hypertensive with controlled BP | Correct — treatment can control BP, and the design must allow it |
| BP values are not repeated placeholders | 38 distinct systolic, 30 distinct diastolic, ≥45 distinct pairs in 50 records |
| Encounter contents vary with what was measured | 46 records include HbA1c; the 4 diabetic records correctly do not |
| **Caveat — 2 records assert a total cholesterol below the sum of their own fractions** | A reviewer will reasonably read this as a data error. Pre-existing; see §6.1 |

**A reviewer should not read the BP marginal as a reproduction of
NFHS-5's observed distribution.** It is NFHS-5's per-band shape
reweighted to agree with INDIAB-17's hypertension prevalence — an
unavoidable consequence of two sources disagreeing, and the reason the
label remains primary. Full statement:
`evidence_and_assumptions.md` §1.5(b).

---

## 6. Unresolved issues

### 6.1 HEADLINE — lipid panels that are internally impossible (pre-existing)

`lipid_panel`'s TC, TG and HDL are sampled as three **independent**
marginals, but Friedewald requires `TC ≥ HDL + TG/5`. When a draw
violates that, LDL's documented clip floor of 30 mg/dL absorbs it.

**Measured across all 100,000 records:**

| Condition | Count | % |
|---|---|---|
| LDL clipped at the floor but feasible | 7,548 | 7.5% |
| **Internally impossible — TC below the sum of its components** | **2,283** | **2.3%** |
| Triglycerides > 400 mg/dL (Friedewald invalid) | 0 | 0% |
| **Total LDL values that are the clip floor, not a derivation** | **9,831** | **9.8%** |

Example (`PAT_044552`, in this batch): TC 129.8, HDL 89.5, TG 260.1 →
implied LDL **−11.7**, stored as 30.0.

Not introduced by M8, and the stored LDL does follow its documented clip
rule — so it is a warning, not an error. But **this is the one issue I
would want resolved before external *clinical* review**, because the
contradiction is visible in a single record without any tooling.

Fixing it is a **D011-level decision**, not a validator's call. Options:
(a) sample TC first, then HDL/TG conditioned to keep the triple
feasible; (b) sample LDL/HDL/TG and derive TC additively — changes which
quantity is "primary", so needs the same kind of explicit decision D011
itself was; (c) reject and redraw infeasible triples. Option (c) is the
smallest change and preserves every existing marginal's evidence basis.

### 6.2 BP age coverage — 52.7% of the dataset is extrapolated

NFHS-5 covers men to 54 and women to 49; this project generates 20–89.
Above coverage the oldest band's mean and SD are **held constant** —
conservative (it understates BP in the elderly rather than inventing a
trend), but it affects **52,680 of 100,000 records** (64% of this
batch, a small-sample fluctuation).

Mitigated, not hidden: every record carries `age_band_source` and
`extrapolated_beyond_source_age_range`, so the affected population is
filterable in one line. **To close it:** a verified age-banded mean+SD
table from LASI Wave 1 (45+, 2017–18).

### 6.3 Open human decisions — not mine to make

| Decision | Why it is blocked |
|---|---|
| **Family history scope** | Generate the LASI 45+ diabetes-family-history figure (14.33%) for part of the population, or leave the field null? `docs/M4F_FINAL_CLINICAL_AUDIT.md` already classifies this "C — requires explicit human decision". Left null. |
| **Whether `encounters` should hold a structural container at all** | M8 populated it as a declared non-clinical container. A reviewer may prefer `null` plus a separate `measurement_session` concept. Cheap to reverse. |
| **The 20 mmHg pulse-pressure floor** | The only invented shaping parameter in the BP design. Declared, measured, reversible. |
| **Hyperlipidemia diagnosis** | Still deferred (D015) — which lipid definition should drive it is unresolved. Unchanged by M8. |

### 6.4 Smaller items

- **`ecg.superclasses` empty in 6,466 records (6.5%).** A genuine PTB-XL
  label gap, warned about and deliberately not guessed. Belongs to the
  ECG workstream.
- **HbA1c-missingness perfectly predicts diabetes** (by design — HbA1c
  is only generated for non-diabetics). Matters for the downstream
  pattern-discovery stage; not a defect in this batch.
- **SBP/DBP correlation is sex- and age-unstratified** (r = 0.7255,
  derived from a men-only analysis).
- **`.gitignore` does not cover `validation/`.** The project ignores
  `outputs/` and `CLAUDE.md` §36 says not to commit generated datasets,
  but this batch sits under `validation/`, so it would be committed.
  **I have not changed the ignore rules and have not committed
  anything** — flagging it as your call (§8).

---

## 7. Recommendation

### **READY TO SEND FOR EXTERNAL VALIDATION, WITH DISCLOSED LIMITATIONS**

Every automated quality gate passes: 142 project tests, 37 pilot gates,
0 structural errors, 0 consistency errors, 0 physiological-invariant
violations across the batch, and the full-dataset audit migrates
100,000/100,000 records cleanly.

**Send it with these three disclosures attached** (all are in
`evidence_and_assumptions.md`, which should go with the batch):

1. **2 of 50 records have an internally impossible lipid panel** (§6.1) —
   pre-existing, affecting 2.3% of the full dataset. Say so up front
   rather than letting a reviewer find it; it is the one finding likely
   to read as carelessness if undisclosed.
2. **BP is conditional on the hypertension label, not an independent
   measurement** — so the BP marginal is not NFHS-5's observed
   distribution and must not be validated against it (§5).
3. **52.7% of BP values use an age band held constant beyond the
   source's coverage** (§6.2), and the batch's own rate is 64%.

**If the reviewer's remit is specifically clinical plausibility rather
than architecture, fix §6.1 first.** It is the only finding that looks
like an error rather than a documented limitation, and option (c)
(reject-and-redraw infeasible lipid triples) is a small, evidence-neutral
change.

**What the batch cannot support:** any statistical claim about treated
hypertensives (n=3) or diabetics (n=4). Those are generator properties
asserted over hundreds of draws in `tests/test_m8_bp_encounters.py`, not
claims this sample can make.

---

## 8. Full-dataset readiness

Measured, not estimated — the migration was dry-run over all 100,000
records (`full_dataset_dryrun_audit.json`):

| Criterion | Status |
|---|---|
| **Records migrating cleanly** | **100,000 / 100,000. Zero failures.** |
| **Seed-replay provenance audit** | Passed for every record — every stored generated value matches what its own recorded seed reproduces |
| **Idempotence** | Verified: re-migrating a v0.8 record yields a byte-identical result (no duplicated encounter, timeline event or provenance block) |
| **Determinism** | Verified: same input + same config → identical output |
| **Patient ids and validated fields preserved** | Enforced in code, verified by test |
| **Dry-run / audit mode** | `--dry-run` writes nothing; always safe |
| **Measured runtime** | 68.3 s for 100,000 records (0.683 ms/record), single process, dry-run. **~1.2 min + write I/O for the real run** |
| **Originals preserved** | Source dataset still 100,000 records, still v0.7, every selected file's SHA-256 unchanged |

**Full-scale run is NOT started, and should not be until you decide
§6.1.** Migrating now would mean re-migrating 100,000 records if the
lipid sampling changes — cheap in compute (~1 minute) but it would
invalidate any review already done against the output.

When approved:

```bash
python integration/migrate_v07_to_v08.py \
    --input-dir outputs/m5/100k_patients \
    --output-dir outputs/m8/100k_patients_v08 \
    --dry-run                               # audit first; writes nothing

python integration/migrate_v07_to_v08.py \
    --input-dir outputs/m5/100k_patients \
    --output-dir outputs/m8/100k_patients_v08 \
    --summary-out outputs/m8/migration_summary.json
```

Writes to a **new** directory; the v0.7 dataset is never modified in
place. Note `outputs/` is already git-ignored, unlike this pilot folder
(§6.4).
