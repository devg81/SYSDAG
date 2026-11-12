# Summary of Changes — Schema, Generator, Validation (M8)

Every file touched, what changed in it, and why. Deliverable #7.

---

## 1. Schema — `schemas/patient_schema.py`

| Change | Detail |
|---|---|
| `SCHEMA_VERSION` | `"0.7"` → `"0.8"` |
| **New** `BloodPressure` dataclass | `systolic_mm_hg`, `diastolic_mm_hg`, `measured_at`, `age_band_source`, `extrapolated_beyond_source_age_range`, `source` |
| **New** `Encounter` dataclass | `encounter_id`, `encounter_type`, `date`, `patient_id`, `recorded_measurements`, `source` |
| **New** `ENCOUNTER_TYPES` | `{"synthetic_baseline_assessment"}` — exactly one value, named for what it is |
| **New** `TIMELINE_EVENT_TYPES` | `{"synthetic_record_created", "synthetic_baseline_assessment"}` |
| `TimelineEvent` | gained `reference_id: Optional[str]` — the additive change `docs/CLINICAL_RECORD_DESIGN.md` §H proposed |
| `Patient.blood_pressure` | **new field**, `Optional[BloodPressure]` |
| `Patient.encounters` | retyped `Optional[list[Any]]` → `Optional[list[Encounter]]` |
| `Demographics.height_cm` / `weight_kg` | unchanged in type; comment now records the 6-attempt evidence search and points at the config entry |

**Backward compatibility:** every addition is optional and defaults to
`None`/empty, so a v0.7 record dict rehydrates without error. Only
`SCHEMA_VERSION` is a breaking change, and `validate_patient()` checks it
explicitly.

---

## 2. Config — `configs/indian_population.yaml`

Two new blocks under `risk_factors`, both following the file's existing
per-parameter traceability convention (source / year / population /
geographic_scope / definition / available_stratification /
marginal_or_conditional / transformation / limitations / evidence_tier).

### `risk_factors.blood_pressure`

- Age-band × sex mean SBP/DBP with **derived** SDs (men 15–19…50–54,
  women 15–19…45–49).
- `source_reported_means_and_cis` — the raw published mean/CI/n retained
  so the SD derivation is re-checkable without refetching the paper.
- `sbp_dbp_correlation` — r = 0.7255, **derived** from the published
  SD(SBP)/SD(DBP)/SD(PP) triple, with the formula and both
  corroborations recorded.
- `label_conditioning` — the three regions, each tied to the hypertension
  label's own published definition.
- `min_pulse_pressure_mm_hg: 20` — the design's **only** invented shaping
  parameter, declared as an explicit engineering assumption with the
  three measurements that forced it (10.70% → 1.98% → 0%).
- `sbp_bounds` / `dbp_bounds` — outer physiological clamp.
- Five lettered limitations, including the two that matter most: age
  coverage (52.7% extrapolated) and the fact that the generated BP
  marginal is **not** NFHS-5's marginal.

### `risk_factors.anthropometrics_height_weight`

Not a distribution — a recorded **gap**, kept where every other
parameter's evidence lives: `status: NOT SUPPORTED`, exactly what is
missing, all 6 failed research attempts with URLs and what each actually
reported, why generating anyway was declined, and two concrete routes to
unblock. `evidence_tier: E (unavailable)`.

---

## 3. Generation — `generation/indian_population.py`

| Function | Status |
|---|---|
| `sample_blood_pressure()` | **new** — draws from the cached joint PMF for this patient's (sex, age band, label region) |
| `_bp_joint_pmf()` | **new** — builds the bivariate-normal PMF on the integer mmHg grid, zeroes cells outside the label region / violating `SBP > DBP` / below the PP floor, renormalises, caches (45 distributions total) |
| `_bp_band()` | **new** — age-band selection with **half-open** `[low, high+1)` matching, and the beyond-coverage hold-last-band rule |
| `_bp_region()` | **new** — maps (hypertension, on_antihypertensive) to the admissible region |
| `sample_height_cm()` | **new, deliberate no-op** — returns `None`, and **raises `NotImplementedError` if the config ever gains height evidence** while this still returns `None`, so the gap cannot rot silently |
| `derive_weight_kg()` | **new** — `bmi × (height/100)²`; implemented and tested now, returns `None` while height is `None` |
| `generate_indian_attributes()` | BP and height appended **last** in the draw order, so every pre-existing field is byte-identical for the same seed; `demographics` now carries `height_cm`/`weight_kg` |
| `validate_config()` | extended — BP band contiguity, no gaps/overlaps, positive SDs, mean SBP > mean DBP, thresholds inside bounds, coverage-max matches the last band |

**Why a grid PMF rather than truncated marginals or rejection
sampling:** one code path covers all three regions exactly; no retry
budget and therefore no bail-out bias in the thin tails young patients
fall into (the raised region sits ~2.6 SD out for women aged 20–24);
whole-mmHg rounding is intrinsic rather than a post-step that can push a
value back across its own truncation threshold; and `SBP > DBP` holds by
construction rather than by repair.

That rounding point was a real bug found during development: truncating
at the threshold itself let a normotensive draw of 139.6 round to 140,
breaking the label rule in 1.7% of 20,000 records. Now 0%.

---

## 4. Generation — `generation/clinical_history.py`

| Function | Status |
|---|---|
| `derive_encounters()` | **new** — one `synthetic_baseline_assessment` naming the measurements that actually exist; returns `[]` when nothing was measured, so an empty container is never emitted |
| `derive_timeline()` | **new** — rebuilds the timeline from scratch (that is what makes re-migration idempotent); one event per encounter, **not** one per measurement; emits no onset/start/follow-up event |

Both are pure and deterministic, consistent with the module's existing
no-RNG contract.

---

## 5. Validation — `validation/structural.py`

Extended, not replaced:

- Blood pressure: both values present, **whole-mmHg `int`** (explicitly
  rejecting `bool`), within physiological bounds, `systolic > diastolic`,
  `measured_at` present, and both provenance fields non-null.
- Encounters: `encounter_type` in vocabulary, ids unique within the
  patient, `patient_id` matches the record's own, date present,
  `recorded_measurements` non-empty.
- Timeline: `event_type` in vocabulary, date present (previously only
  emptiness was checked).
- Height/weight bounds — currently inert, correct in advance.

---

## 6. Validation — `validation/clinical_consistency.py`

New checks:

| Check | Severity |
|---|---|
| BP vs. the hypertension label's own definition (all three cases, with the treated case asserting **nothing** about the value) | error |
| `systolic > diastolic` | error |
| `blood_pressure.measured_at` vs. the timeline date | error |
| BMI ↔ height/weight arithmetic (tolerance 0.15, covering stored rounding) | error; **self-reports as skipped** when height/weight are unpopulated, rather than silently passing |
| Encounter `patient_id` ownership | error |
| Encounters only claim measurements that exist | error |
| Encounter date vs. `labs.measured_at` / `blood_pressure.measured_at` | error |
| Timeline `reference_id` resolves; no duplicate references; every encounter indexed exactly once | error |
| No timeline event predates `synthetic_record_created` | error |
| `ecg.signal_available` must stay `false` (D003) | error |
| **`lipid_panel` internal feasibility** — `TC ≥ HDL + TG/5`; LDL clipped at the floor; TG > 400 | **warning** |
| `ecg.superclasses` empty | warning |

Changed: `encounters` left the "unimplemented domains confirmed absent"
warning list (it is implemented now); `family_history` and `echo` remain
on it.

The lipid-feasibility check is a **warning, not an error**, on purpose:
the stored LDL does follow its documented clip rule, so erroring would
fail 9.8% of the dataset over a decision that is not a validator's to
make. It is counted instead — see `validation_report.md` §6.1.

---

## 7. Migration — `integration/migrate_v07_to_v08.py` (new, 500 lines)

The reusable entry point. Public API:

```python
migrate_record(record: dict, indian_config, *, states=None)
    -> (migrated: dict, errors: list[str], notes: list[str])

migrate_paths(input_paths, output_dir, indian_config, *, dry_run=False)
    -> summary: dict
```

CLI: `--input-dir`, `--output-dir`, `--ids-file`, `--limit`,
`--dry-run`, `--summary-out`.

Properties, each verified by test:

- **Replay-and-extend, not regenerate.** Replays
  `generate_indian_attributes()` from the record's own recorded seed and
  **verifies** every pre-existing field matches before accepting the new
  one — so migration and fresh generation agree, and the replay doubles
  as a provenance audit. A mismatch is an error, never migrated around.
- **Idempotent.** Derived fields are rebuilt, never appended; the
  provenance block is appended only once.
- **Pure.** The input dict is never mutated.
- **No silent overwrite.** `_UNCHANGED_FIELDS` compares 11 top-level
  fields plus 4 demographics keys before and after; a difference blocks
  the write.
- **All-or-nothing.** Nothing is written unless every record migrated
  cleanly — a partial batch is worse than none, because it looks
  complete.
- **Dry-run.** Writes nothing, always safe.

---

## 8. Fresh generation — `integration/build_patient.py`

Updated so new records are born at v0.8 and agree with migrated ones:
builds `BloodPressure`, `Encounter` list and the referenced timeline;
passes `height_cm`/`weight_kg` through from the generator; provenance
generator string and `source_datasets` extended.

---

## 9. Tests

| File | Count | Scope |
|---|---|---|
| `tests/test_m8_bp_encounters.py` | **38 new** | Reusable layer: label-rule properties over hundreds of draws per region, physiological invariants, age-band half-open semantics + extrapolation flag, determinism, **the byte-identical-pre-existing-fields guarantee against real stored records**, height deferral (including that the hook refuses to stay a no-op once evidence arrives), encounter/timeline derivation, structural-validator rejections |
| `validation/pilot_50_records/tests/test_pilot_50_records.py` | **37 new** | Batch gates in five families: structural, referential integrity, clinical consistency, data quality, reusability (idempotence, determinism, batch re-derivable from the preserved originals, originals hash-verified, production dataset still 100,000 records at v0.7) |

### Pre-existing tests modified — 3, all asserting the pre-M8 state

| Test | Change | Why |
|---|---|---|
| `test_m4a_clinical_schema.py::test_minimal_patient_still_works` | `== "0.7"` → `== "0.8"` | Hardcoded the old schema version |
| `test_m4c_clinical_consistency.py::test_unimplemented_domains_absent_is_not_an_error` | asserts `family_history`/`echo` absent instead of `encounters` | `encounters` is implemented now; the test's intent (absence is not an error) is preserved against the domains still absent |
| `test_m4c_clinical_consistency.py::test_unexpectedly_populated_unimplemented_domain_warns` | uses `family_history` instead of `encounters` | Same reason; `family_history` is the still-unimplemented domain |

A fourth test was **added** to the same file —
`test_encounters_are_now_generated_and_indexed_by_the_timeline` — so the
coverage the first two tests gave up is replaced rather than lost.

**No test was weakened to make the suite pass.** One of my own new tests
was corrected during development:
`test_ldl_is_still_the_friedewald_derivation` initially ignored LDL's
documented `clip_range` and failed on `PAT_044552`. Investigating that
failure is what surfaced the internally-impossible-lipid defect
(`validation_report.md` §6.1) — the test was rewritten to assert
derived-then-clipped, and a second test was added to **count** the
infeasible records rather than tolerate them silently.

### Results

| Suite | Result |
|---|---|
| `tests/` | **142 passed, 0 failed** (104 pre-existing + 38 new) |
| `validation/pilot_50_records/tests/` | **37 passed, 0 failed** |
| Combined | **179 passed, 0 failed** |

---

## 10. Files changed

**New (5):**
```
integration/migrate_v07_to_v08.py
tests/test_m8_bp_encounters.py
validation/pilot_50_records/run_pilot.py
validation/pilot_50_records/tests/test_pilot_50_records.py
validation/pilot_50_records/README.md  (+ reports/, input/, output/)
```

**Modified (9):**
```
schemas/patient_schema.py
configs/indian_population.yaml
generation/indian_population.py
generation/clinical_history.py
validation/structural.py
validation/clinical_consistency.py
integration/build_patient.py
tests/test_m4a_clinical_schema.py
tests/test_m4c_clinical_consistency.py
```

**Not modified:** the 100,000-record dataset at `outputs/m5/100k_patients/`
(read-only; verified still 100,000 records at v0.7, hashes unchanged),
`.gitignore` (see README's git note), and every ECG/echo module.
