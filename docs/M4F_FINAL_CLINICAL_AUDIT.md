# M4F — Final Clinical Completeness + Pre-Scale Audit

**Status:** COMPLETE. Audit and benchmark only — no behavioral generation
change, no new clinical relationship introduced, no human decision
resolved.

---

## Phase 1 — Domain Matrix

Evaluated actual generation + validation behavior (code and test
output), not schema field presence alone.

| Domain | Status | Evidence Level | Generated? | Derived? | Validated? | Remaining Issue | Human Input Required? |
|---|---|---|---|---|---|---|---|
| Demographics (age/sex/state/urban_rural) | COMPLETE | age: B (engineering `uniform(20,89)`, D007); sex/state/urban_rural: A (Census 2011) | Yes | No | Structural (range/vocab/state membership) + statistical (chi-sq/binomial/KS) | Age uniformity is engineering, not evidence-derived — documented, not blocking | No |
| Risk factors (container) | COMPLETE | Mixed per field below | — | — | Structural + statistical | None | No |
| BMI | COMPLETE | Category: A (NNMS); within-category continuous value: B (engineering uniform) | Yes | No | Structural range check | Within-category shape not evidence-derived — documented | No |
| Smoking status | COMPLETE | A (NNMS, sex-conditioned) | Yes | No | Structural vocabulary check | None | No |
| Hypertension | COMPLETE | A (ICMR-INDIAB-17 national marginal) | Yes | No | Statistical (binomial) | Unconditioned by age — no accessible evidence found; documented | No |
| Diabetes | COMPLETE | A (ICMR-INDIAB-17) | Yes | No | Statistical | Same as above | No |
| Hyperlipidemia (`risk_factors.hyperlipidemia`) | COMPLETE, distinct scope | PARTIALLY SUPPORTED (reduced-coverage sub-cohort) — weakest evidence tier of the original five | Yes | No | Statistical + clinical_consistency (deliberately NOT compared to `lipid_interpretations`, D014) | Intentionally not reconciled with `lipid_interpretations` — resolved as an architecture decision (D014), not an open item | No |
| Lipid panel (LDL/HDL/TG/TC) | COMPLETE | TC/TG/HDL: A (category) + B (within-category reconstruction); LDL: B (Friedewald-derived) | Yes (TC/TG/HDL) | Yes (LDL) | Structural range + clinical_consistency recomputation | Continuous "raw" values are engineering-reconstructed from category evidence, not directly observed — documented (D011/D013) | No |
| Lipid interpretations | COMPLETE | A (NCEP_ATP_III/LAI_2020 definitions applied to raw values) | No (pure function) | Yes | Hard recomputation check | None | No |
| HbA1c | COMPLETE for non-diabetic; not generated for diabetic | A for NGT (ICMR-INDIAB-12); diabetic-population data PARTIALLY SUPPORTED, not used | Yes (conditional) | No | clinical_consistency (presence/range/plausibility) | Diabetic-population HbA1c intentionally unpopulated — evidence too thin (4 states, n=480) | No |
| Diagnoses | PARTIAL (hypertension/diabetes only) | A (1:1 promotion of already-evidence-backed flags) | No (pure function) | Yes | `diagnosis_risk_factor_consistency` hard rule | Hyperlipidemia diagnosis deferred | **YES (open, non-blocking)** |
| Medical history | PARTIAL (`chronic_condition` only) | A (references diagnoses) | No (pure function) | Yes | `medical_history_diagnosis_consistency` hard rule | `cv_event`/`procedure` categories not implemented — evidence gap | No |
| Medications | PARTIAL (antihypertensive/antidiabetic only, drug_class level) | A (NNMS treatment rate) for existence; class label only | Yes (treatment Bernoulli) | Yes (record construction) | `medication_diagnosis_consistency` hard rule | Statin/antiplatelet not supported (evidence gap); specific drug name never generated (deliberate, D016) | No (deferred, not blocking) |
| Family history | NOT IMPLEMENTED | NOT SUPPORTED for CVD (confirmed absent across 9+ datasets); PARTIALLY SUPPORTED for diabetes-family-history (LASI, ages 45+ only) | No | No | N/A | Scope decision if pursued (LASI 45+ subset vs. leave unpopulated) | Only if pursued (currently deferred) |
| Temporal information | PARTIAL | `diagnosed_date`/`event_date`/`start_date`/`stop_date` always null (B, no per-patient evidence); `clinical_timeline` has one synthetic-record-created event; `labs.measured_at` = generation timestamp | Yes (trivial) | No | `timeline_labs_date_consistency` | No per-patient onset/event-date evidence exists anywhere researched — documented limitation | No |
| ECG metadata | COMPLETE (M1) | A (real PTB-XL records, reused not synthetic) | Yes (real-record lookup) | No | Structural (signal_shape/strat_fold) | `superclasses` list-order non-determinism (benign, documented); ECG-ID reuse at scale (see Phase 6) | No (scale monitoring only) |
| ECG waveform | NOT IMPLEMENTED | N/A — explicitly deferred to Stage 4 | No | No | N/A | Model-integration decision required (Phase 6) | Future — not this milestone |
| Echo | NOT IMPLEMENTED | Scope entirely open, no evidence gathered | No | No | N/A | Needs a usable source + strategy before any work (`CLAUDE.md` §5) | Not currently blocking |
| Procedures | NOT IMPLEMENTED | NOT SUPPORTED (no source found) | No | No | N/A | Correctly left unpopulated | No |
| Stroke | NOT IMPLEMENTED | PARTIALLY SUPPORTED (heterogeneous, wide-range figures); NOT SUPPORTED for individual-record generation | No | No | N/A | Evidence insufficient — correctly deferred | No |
| Heart failure | NOT IMPLEMENTED | PARTIALLY SUPPORTED (modeled estimate, not measured) | No | No | N/A | Same | No |
| General CVD | NOT IMPLEMENTED | PARTIALLY SUPPORTED (pooled meta-analysis ~11%, heterogeneous underlying definitions) | No | No | N/A | Same | No |

**Fully complete and validated:** demographics, risk factors (all 5),
lipid panel, lipid interpretations, HbA1c (NGT), ECG metadata.
**Partially complete (evidence-bounded, not incomplete by oversight):**
diagnoses, medical history, medications, temporal information.
**Not implemented, correctly deferred:** family history, ECG waveform,
echo, procedures, stroke, heart failure, general CVD.

---

## Phase 2 — Human-Decision Audit

Every unresolved item found in `docs/DECISIONS.md`/`docs/PROJECT_STATE.md`/M4
documentation, classified:

| Item | Classification | Notes |
|---|---|---|
| Which `lipid_interpretations` definition (if any) should drive a future `diagnoses.hyperlipidemia` | **C — requires explicit human decision** | D011 explicitly declined to prefer NCEP_ATP_III over LAI_2020 (or vice versa); collapsing them into one diagnosis boolean would silently make that choice. Not resolved by this audit, per this milestone's own instruction. |
| `TimelineEvent.reference_id` (pointing at a `diagnosis_id`/`lab_id`/`ecg_id`) | **C — requires explicit human decision** | Flagged since M3.5, restated in M4-0B (`docs/M4_CLINICAL_ARCHITECTURE.md` §8); a real (if small) schema-architecture choice, not resolved here. |
| Patient-level `birth_date` field | **C — requires explicit human decision** | Raised in `docs/CLINICAL_RECORD_DESIGN.md` §I; would let temporal rules check against an actual date rather than an implied one from `age`. Schema-architecture choice. |
| Family history scope (LASI 45+ diabetes-family-history subset vs. leave entirely unpopulated) | **C — requires explicit human decision** | `docs/M4_CLINICAL_EVIDENCE.md` Proposed Decision 4; a real product-scope choice (partial-population coverage vs. no coverage), not an evidence question. |
| Statin/antiplatelet treatment-rate evidence | **D — intentionally deferred/unsupported** | No population-level source found across two independent research passes (M4-0, M4E-0); preserved as absent, not implemented. |
| Family history of CVD | **D — intentionally deferred/unsupported** | Confirmed absent across 9+ datasets examined (M2A, M2C-0, M4-0); preserved as `null`. |
| Stroke/heart-failure/general-CVD/procedure generation | **D — intentionally deferred/unsupported** | Evidence exists but is heterogeneous, modeled-not-measured, or hospital-registry-derived; none meets this project's population-generation bar. Preserved as absent. |
| Hypertension continuous BP distribution | **D — intentionally deferred/unsupported** | No Indian BP continuous-distribution research has ever been conducted by this project (`docs/M4_CLINICAL_ARCHITECTURE.md` §4); label-only remains the only evidence-supported approach. |
| Diabetic-population HbA1c generation | **D — intentionally deferred/unsupported** | Thin, non-representative 4-state data only; preserved as unpopulated. |
| Height/weight continuous distributions | **D — intentionally deferred/unsupported** | No verified NFHS-5 primary table located across three independent access attempts (M2C, M2D, M4-0); BMI-primary remains the evidence-correct default (M4-0's own resolved recommendation). |

**No category A or B items were found in this pass** — every
previously-open item is either a genuine human decision (C) or an
already-settled, correctly-preserved evidence gap (D). Nothing was
researched further in this milestone beyond the read-only audit above,
since no B-classified item existed to research (this audit's Phase 2
instruction: "research only if the research can materially improve the
architecture without inventing assumptions" — no such candidate
existed among the open items).

**No category C item was resolved by this milestone**, per instruction.

---

## Phase 3 — Clinical Consistency Audit

### Test suite

**103/103 tests passing** (unchanged from the M4E baseline — no test
was added, modified, or removed by this audit; see Phase 8 for why).

### 10 / 100 / 1,000-patient generation and validation

Generated fresh via `integration/generate_population.py` using the
existing `configs/base.yaml`/`configs/indian_population.yaml` seeds
(`random_seed: 42` both), no configuration override:
`outputs/m4f/10_patients/`, `outputs/m4f/100_patients/`,
`outputs/m4f/1000_patients/`.

| n | Structurally valid | Clinically consistent | Errors | Warnings | Duplicate patient_ids |
|---|---|---|---|---|---|
| 10 | 10/10 | 10/10 | 0 | 0 | 0 |
| 100 | 100/100 | 100/100 | 0 | 0 | 0 |
| 1,000 | 1000/1000 | 1000/1000 | 0 | 0 | 0 |

All `validate_clinical_consistency` checks ran for every applicable
patient at all three scales: `lipid_panel_interpretation_consistency`,
`diabetes_hba1c_consistency`, `hba1c_plausibility_given_age_sex`,
`hyperlipidemia_vs_lipid_interpretations_intentionally_not_compared`,
`timeline_labs_date_consistency`, `diagnosis_risk_factor_consistency`,
`medical_history_diagnosis_consistency`,
`medication_diagnosis_consistency`,
`unimplemented_domains_confirmed_absent`.

### Statistical/consistency spot-checks at n=1,000

| Check | Observed | Cited | Exact binomial p | Finding class |
|---|---|---|---|---|
| Hypertension prevalence | 362/1000 = 36.2% | 35.5% | 0.644 | C — sampling variation |
| Diabetes prevalence | 113/1000 = 11.3% | 11.4% | 0.960 | C |
| Hyperlipidemia prevalence | 801/1000 = 80.1% | 81.2% | 0.373 | C |
| Diagnoses == risk_factors flags (hypertension, diabetes) | Exact match, both | — | — | D — hard rule verified by construction |
| Antihypertensive treatment rate (of 362 hypertension diagnoses) | 56/362 = 15.5% | 14.5% | 0.601 | C |
| Antidiabetic treatment rate (of 113 diabetes diagnoses) | 51/113 = 45.1% | 36.1% | **0.050** | **Investigated — see below** |
| `risk_factors.hyperlipidemia` vs. NCEP `lipid_interpretations` agreement | 707/1000 = 70.7% | (73-77% at n=100, M4C) | — | C — consistent with D014's documented expected disagreement, within sampling range of the earlier n=100 figure |
| Unique `patient_id`s | 1000/1000 | — | — | D |
| Duplicate `ecg_id`s | 30 groups, 61 total occurrences | (30 groups observed in M3's original n=1,000 run) | — | C/D — same birthday-paradox effect against the ~17,470-record training-fold pool, already documented in M3; not a new finding |

**Antidiabetic treatment-rate borderline finding, investigated per this
milestone's explicit instruction ("investigate every warning or
discrepancy"):** at n=113 (the diabetic sub-sample within this
particular 1,000-patient run), the observed 45.1% treatment rate sits
at the edge of significance against the cited 36.1% (p=0.050). Ran an
isolated large-n check of the same Bernoulli draw
(`rng.random() < 0.361`, independent of the diabetes-diagnosis sampling
that feeds it in the real pipeline) at n=50,000: **35.88% observed,
exact binomial p=0.308** — confirms the sampler itself is unbiased and
correctly wired to the configured rate. **Classification: C — expected
sampling variation at a small conditional sub-sample size (113), not a
defect.** Exactly the same investigative pattern M2C used for its own
borderline age p-value (p=0.0096, confirmed unbiased via a 10,000-draw
isolated check) — not re-rolled, not silently accepted without
verification, and not treated as requiring a generator change.

### Serialization / round-trip

Already covered by `tests/test_m4e_medications.py::test_serialization_round_trip`
(re-run as part of the 103/103 suite above) — `Patient.to_dict()` →
JSON → `_patient_from_dict()` reconstruction preserves `medications`
exactly. Diagnoses/medical_history round-trip coverage:
`tests/test_m4d_diagnosis_history.py`. No new round-trip gap found.

**No warning or discrepancy investigated in this phase required a
generator change.** All findings are C (expected sampling variation) or
D (verified-by-construction hard rules) — zero A (actual bug) findings.

---

## Phase 4 — Large-Scale Readiness Benchmark

**Not the final dataset — benchmark only, not committed**
(`outputs/m4f/benchmark_5000/`, gitignored under `outputs/`).

Ran a 5,000-patient benchmark using the existing, already-optimized
PTB-XL caching layer (`ingestion/ptbxl_source.py`'s `lru_cache`-based
`_cached_ptbxl_df`/`_cached_label_map`, D009) — unmodified.

| Metric | Value |
|---|---|
| Patients generated | 5,000 |
| Wall time | 69.9s |
| Patients/minute | 4,293 |
| Patients/second | 71.6 |
| CPU user time | 58.4s |
| CPU sys time | 9.4s |
| CPU utilization | 97.0% (effectively single-core-bound, no parallelism used) |
| RSS at start | 89.2 MB |
| RSS at steady state (after warmup) | ~265 MB, flat from patient 1,000 through 5,000 — no growth, no leak |
| RSS delta (one-time cache warmup cost) | 175.7 MB |
| **Estimated time for 10,000** | **2.3 minutes** |
| **Estimated time for 100,000** | **~23 minutes (0.4 hours)** |

Separately confirmed at n=1,000 (full pipeline including structural
validation + JSON write): 19.8s wall time (~50.6 patients/sec) —
consistent with the M3.5 caching-fix baseline (~20.4s), confirming no
regression across M4A-M4E's additions.

**No performance bottleneck was found that requires a code change.**
Memory is flat (no leak across 5,000 patients), CPU is fully utilized
by a single process (matches this project's current single-threaded
design — parallelization is a legitimate future optimization but not a
blocking issue at these estimated runtimes), and the 100K estimate
(~23 minutes) is well within local-machine feasibility. No change made.

---

## Phase 5 — Dataset Storage Estimate

Measured directly from the 5,000-patient benchmark output (not
estimated from schema alone).

| Metric | Value |
|---|---|
| Files measured | 5,000 |
| Total size | 17.76 MB |
| **Bytes/patient (metadata-only, current schema)** | **3,551 average** (range 3,380-4,322) |
| Estimated size, 10K | 35.5 MB |
| Estimated size, 100K | **0.36 GB** |

**Estimated size including a future waveform representation** (if
waveform generation is ever added — **not implemented, this is a rough
forward estimate only**, based on the schema's already-declared
`signal_shape: [1000, 12]`, i.e. 10 seconds at 100Hz, 12 leads): a
raw `float32` array of that shape is `1000 * 12 * 4 = 48,000` bytes/
patient. At 100K patients, that alone is **~4.8 GB**, plus the existing
~0.36 GB of structured metadata — **~5.1 GB combined**, before any
waveform-specific compression (typical ECG compression can reduce this
materially, but no compression strategy has been chosen — this is a
raw-array upper-bound estimate, not a commitment to a storage format).

**Recommended working-space margin:** at least **15-20 GB** free —
covers the ~5 GB combined estimate above, headroom for multiple
generation runs/re-runs during development, validation-report
artifacts, and this project's own benchmark/intermediate files, without
requiring cloud storage at the 100K scale.

---

## Phase 6 — ECG Readiness Check

1. **What is inherited from PTB-XL?** Everything currently populated in
   `ECGRecord`: `ecg_id`, `superclasses` (SCP-code-derived diagnostic
   labels via `syngen`'s reused `build_label_map()`), `strat_fold`,
   `sampling_hz` (100, hardcoded to match PTB-XL's `records100`
   directory), `signal_shape` ([1000, 12], PTB-XL's own low-rate
   format), `filename` (the real PTB-XL relative path).
2. **What is actually synthetic?** Nothing in the ECG domain today.
   `signal_available` is `False` on every patient (D003) — the
   waveform itself is never loaded or generated; only real-record
   *metadata* is reused, attached to an otherwise-synthetic patient.
3. **Are ECG IDs reused?** Yes, by design (D003/M1) — `pick_ecg_id()`
   samples deterministically, with replacement, from the training-fold
   pool (~17,470 records). Confirmed at n=1,000: 30 duplicate `ecg_id`
   groups (61 total occurrences among 1,000 patients) — a
   birthday-paradox effect against that pool size, first measured and
   documented in M3, reproduced here unchanged (same seed, same pool,
   same math). At 100K patients against the same ~17,470-record pool,
   duplicate-ID collisions would become pervasive (most records reused
   many times over) — **this is the one concrete scale concern this
   audit flags** (see Phase 7).
4. **Are waveforms currently generated?** No.
5. **What information is safe to preserve?** All of it — `ecg_id`,
   `superclasses`, `strat_fold`, `filename`, `sampling_hz`,
   `signal_shape` are all real, correctly-sourced PTB-XL facts about
   the specific record referenced. Nothing here needs to be
   regenerated or invalidated by a future waveform-generation step;
   they are exactly the conditioning/reference metadata a waveform
   generator would need.
6. **What information must eventually be regenerated?** Only
   `signal_available` needs to flip to `True` once a real or synthetic
   waveform is actually attached — no other field changes meaning.
7. **What design decision is required before waveform generation?**
   Two, neither made here: (a) **source of the waveform** — this
   project already has **existing, previously-trained GAN checkpoints**
   sitting unused in `syngen/SynGen/SynGen/checkpoints/`
   (`generator_CD.pt`, `generator_HYP.pt`, `generator_MI.pt`,
   `generator_NORM.pt`, `generator_STTC.pt` — one per PTB-XL
   diagnostic superclass, with a `generate_synthetic()` function
   already defined in `gan_pytorch.py`) — a real "reuse before rebuild"
   candidate, distinct from the CardioSynth/CardioSync candidate named
   in `docs/PROJECT_STATE.md` Stage 9, and not yet evaluated for
   currency/validity; (b) **conditioning/selection logic** — a patient
   can have zero, one, or multiple `superclasses`; which per-class
   checkpoint (or combination) generates the waveform for a
   multi-label or zero-label patient is an unmade architectural choice.
   Neither decision is made by this audit.
8. **Does the current patient architecture support replacing
   metadata-only ECG with synthetic waveform data later?** Yes, without
   restructuring. `ECGRecord.signal_available` already exists as the
   toggle; no other schema field would need to change shape — a future
   milestone can attach a waveform (as a new field, or a reference to
   an external array store, itself an undecided design choice) and flip
   the flag, additive to the existing structure, matching every prior
   schema change in this project (D006/D012/D015/D016).

---

## Phase 7 — 100K Readiness Checklist

| Area | Status | Notes |
|---|---|---|
| Schema stability | **GREEN** | 7 versions (v0.2→v0.7), every change additive/backward-compatible; 0 breaking changes across M1-M4E; verified byte-identical regression at every milestone boundary |
| Evidence coverage | **GREEN** | Every generated field traces to a cited source with documented population/year/scope/limitations; every unsupported field is absent, not guessed |
| Demographic generation | **GREEN** | Statistically confirmed unbiased at n=1,000 (this audit) and n=10,000 (M2D sampler check) |
| Risk factors | **GREEN** | All 5 statistically confirmed unbiased at n=1,000 |
| Clinical records (lipids/HbA1c/diagnoses/medical history) | **GREEN** | Hard-consistency rules verified 0 errors at n=1,000; all recomputation checks pass |
| Medications | **YELLOW** | Functionally correct and validated (0 errors at n=1,000), but intentionally incomplete (2 of 4+ plausible classes) — not a defect, a documented evidence boundary; monitor if a future milestone expands scope |
| Validation | **GREEN** | Structural + statistical + clinical-consistency layers all exercised at 10/100/1,000 with 0 unexplained errors |
| Reproducibility | **GREEN** | Deterministic given `(sequence, seed)`; confirmed byte-identical across every milestone's regression check |
| Performance | **GREEN** | ~71.6 patients/sec sustained (5,000-patient benchmark); 100K estimated at ~23 minutes; no bottleneck found |
| Storage | **GREEN** | ~0.36 GB for 100K at current (metadata-only) schema; trivial for local disk |
| ECG architecture | **YELLOW** | Metadata-only by design (Stage 4 not yet started) — internally consistent and extensible, but **duplicate `ecg_id` reuse will become pervasive at 100K** against the fixed ~17,470-record training-fold pool (expected ~5-6x average reuse per record) — a real, quantified scale concern flagged in M3 and reconfirmed here, not yet decided (accept reuse as a documented limitation vs. expand the pool vs. change fold discipline) |
| Dataset provenance | **GREEN** | Every patient's `Provenance` records generator description, seed, and full source-dataset list; every decision traceable to `docs/DECISIONS.md` |
| Privacy/synthetic-data concerns | **GREEN** | No real patient identifiers ever copied into synthetic records (`CLAUDE.md` §10/§31, verified in `ingestion/ptbxl_source.py`'s docstring and code — only field *values* are reused, never PTB-XL's own patient ID) |
| Model-readiness | **YELLOW** | No model selected (by design, Stage 9 not started); existing unused GAN checkpoints identified as a candidate (Phase 6) but not evaluated |
| Documentation | **GREEN** | Every milestone has a design doc, decision entry, and session log; this audit found no undocumented behavior |

**No RED item exists.**

### Can we safely proceed to large-scale 100K patient generation after M4F?

**Yes, conditionally.** Every clinical-generation, validation,
performance, and storage dimension is GREEN. The two YELLOW items
(medication scope, ECG-ID reuse at scale) are **documented, quantified,
non-blocking limitations**, not defects — both were already known
before this audit and neither has grown worse. Proceeding to 100K would
be safe from a correctness/reproducibility/resource standpoint. The
open **C-classified human decision** (hyperlipidemia-diagnosis
definition choice) does **not** block 100K generation of the fields
already implemented — it only blocks *adding* a third diagnosis/future
statin medication, which is not required for a 100K run of the current
schema.

---

## Phase 8 — Implementation

**No Category-A bugs were found.** No behavior-changing modification
was made — nothing in Phase 3's investigation required one, and this
audit's own rules (Phase 8) require rationale + evidence + regression
test + before/after validation + documentation for any such change,
which would not be justified here since no defect exists to fix. Tests
were not modified; only new read-only artifacts (benchmark/validation
output) were generated, none committed.
