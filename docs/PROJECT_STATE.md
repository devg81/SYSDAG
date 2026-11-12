# Project State

## Project

Synthetic Cardiovascular Patient Dataset & Generative System

## Current Stage

Stage 2 — Foundation

## Overall Objective

Build a validated population of approximately 100,000+ coherent synthetic cardiovascular patient records, analyze the resulting population for meaningful patterns, incorporate Indian demographic characteristics, and eventually integrate a suitable existing generative model to generate new synthetic patient fields/records.

## Target Population

**The target synthetic population is the general Indian population.**
(Decided 2026-09-26, `docs/DECISIONS.md` D008 — supersedes M2D's
previously-open question.)

It is explicitly **NOT**:
- a cardiovascular-disease-only population
- a hospital population
- a cardiology-clinic population
- a high-risk cardiovascular cohort
- an Indian CVD patient registry

**Target:** General Indian population (specifically the general **adult**
Indian population, ages 20-89 — the age scoping is a separate, prior
decision, `docs/DECISIONS.md` D004/M1/M2C, not extended or narrowed by
this one).

**Geographic scope:** India.

**Intended use:** Generation of a broad synthetic Indian population that
will later be enriched with medical history, cardiovascular risk factors,
investigations, and multimodal clinical data (Stage 3+ / M2E onward, this
document's own roadmap).

**Important limitation:** This population is synthetic and assembled from
multiple source distributions with different years, populations, and
geographic scopes — Census of India 2011 (general population, all ages,
for demographics), ICMR-NNMS 2017-18 (surveyed adults 18-69, for BMI/
smoking), and ICMR-INDIAB-17/2023 publication (surveyed adults 20+, for
hypertension/diabetes/hyperlipidemia). These three sources do **not**
combine into one single, internally consistent *observed* population —
each is evidence informing a different component of one assembled,
synthetic general-population target, not three measurements of the same
cohort. Full per-source mapping: `docs/DECISIONS.md` D008;
per-parameter evidence detail:
`configs/indian_population.yaml`.

---

# Current Milestone

## M1 — Generate One Valid Synthetic Patient

Status: COMPLETE (2026-09-25)

Success criteria:

* [x] Schema v0.2 implemented — `schemas/patient_schema.py`
* [x] Patient data model implemented — `schemas/patient_schema.py` (`Patient` dataclass)
* [x] Patient ID generation implemented — `integration/patient_id.py`
* [x] Provenance implemented — `Provenance` dataclass, populated per patient
* [x] Timeline representation implemented — `TimelineEvent`, `clinical_timeline`
* [x] Basic validation implemented — `validation/structural.py`
* [x] Existing reusable ECG functionality connected where practical —
      `ingestion/ptbxl_source.py` reuses syngen's `build_label_map()`
      (metadata only; see `docs/DECISIONS.md` D003)
* [x] One synthetic patient generated — `outputs/test/PAT_000001.json`
* [x] Generated record passes structural validation — `validated: true`, 0 errors
* [x] Tests pass — `tests/test_stage2_foundation.py`, 5/5 passed
* [x] Output is reproducible — same `(sequence, seed)` deterministically
      reselects the same PTB-XL record (`test_reproducibility_same_seed_same_patient`)

## M2A — Indian Population Data Research

Status: COMPLETE (2026-09-25) — `docs/INDIAN_DATA_SOURCES.md`

## M2B — Indian Generation Strategy

Status: COMPLETE (2026-09-25) — `docs/INDIAN_GENERATION_STRATEGY.md`

## M2C — Indian Conditioning Implementation

Status: COMPLETE (2026-09-25)

Success criteria:

* [x] Evidence verified for every generation parameter — 3 parallel
      research forks + direct follow-up fetches; full per-parameter
      SUPPORTED/PARTIALLY SUPPORTED/NOT SUPPORTED table in
      `docs/session_logs/2026-09-25_M2C-indian-conditioning.md`
* [x] Unsupported parameters identified — age (no adult age-band
      distribution found → documented uniform(20,89) engineering default),
      family_history_cvd (no source → left null, per D004)
* [x] `configs/indian_population.yaml` — every parameter traceable
      (source/year/population/geographic_scope/definition/stratification/
      marginal-or-conditional/transformation/limitations)
* [x] Age, sex, state, urban_rural generation — `generation/indian_population.py`
* [x] BMI, smoking_status (sex-conditioned), hypertension, diabetes,
      hyperlipidemia (marginal) generation — same module
* [x] Evidence-supported dependencies implemented (sex→BMI, sex→smoking);
      unsupported ones (age-conditioning of risk factors, multivariate
      joint distributions) NOT invented
* [x] `family_history` remains unpopulated — `docs/DECISIONS.md` D004
* [x] Structural validation extended — `validation/structural.py`
      (state membership, BMI range, smoking_status vocabulary)
* [x] Statistical validation — `validation/statistical.py` (chi-square,
      exact binomial, one-sample KS via scipy — reused, not rebuilt)
* [x] M1 tests still pass — `tests/test_stage2_foundation.py`, 5/5
* [x] 10 patients generated and inspected — `outputs/m2c/10_patients/`,
      10/10 structurally valid, no anomalies found
* [x] 100 patients generated and validated — `outputs/m2c/100_patients/`,
      100/100 structurally valid; `outputs/m2c/validation_summary.json`,
      `outputs/m2c/validation_plot.png`
* [x] Reproducibility confirmed — `tests/test_m2c_indian_conditioning.py`
* [x] Documentation updated (this file); session log created

See `docs/session_logs/2026-09-25_M2C-indian-conditioning.md` for full
detail, including the one notable finding (age's KS test came back
p=0.0096 for this specific 100-patient sample — independently confirmed
via an isolated 10,000-draw check that the sampler itself is unbiased;
documented as sampling variance, not a defect, rather than silently
re-rolled for a nicer p-value).

## M2D — Indian Population Calibration & Quality Gate

Status: COMPLETE (2026-09-25) — `docs/session_logs/2026-09-25_M2D-calibration-quality-gate.md`

Audited all 7 limitations M2C flagged (age, BMI, smoking, hypertension,
diabetes, hyperlipidemia, state/urban-rural). Result: **zero behavioral
code changes** — every audit concluded the M2C implementation was already
the evidence-correct choice; only documentation/traceability was
strengthened (`configs/indian_population.yaml` gained `evidence_tier`
classifications and several newly-identified limitations). One new,
better-sourced age figure was found and explicitly, quantifiably rejected
(`docs/DECISIONS.md` D007) rather than adopted uncritically. The central
finding: **the generator currently has no single consistent target
population** — demographics come from Census 2011's general population,
BMI/smoking from NNMS's adults-18-69, and hypertension/diabetes/
hyperlipidemia from INDIAB's adults-20+ — recorded as an open question
(`configs/indian_population.yaml`'s `population.target_population_ambiguity_M2D6`),
not silently resolved. 16/16 tests still pass; 100-patient regression
confirmed byte-identical demographics/risk_factors vs. the M2C baseline;
10,000-draw isolated sampler checks confirm no implementation bias.

## M2D-DECISION — Target Population Definition

Status: COMPLETE (2026-09-26) — `docs/DECISIONS.md` D008

Resolved the population-target ambiguity M2D surfaced (above): **the
target synthetic population is the general Indian population** — see
"Target Population" near the top of this document for the full statement.
No generator behavior changed; this is a documentation/decision-recording
action only, per its own instructions. All existing `evidence_tier`
classifications in `configs/indian_population.yaml` preserved unchanged;
16/16 tests re-confirmed passing.

## M3 — 1,000-Patient Population Validation & Pattern Analysis

Status: COMPLETE (2026-09-26) — `docs/session_logs/2026-09-26_M3-1000-patient-validation.md`

1,000 patients generated with the unmodified M2C/M2D generator, all
1,000/1,000 structurally valid, 0 duplicate IDs. No implementation bias
detected: every configured distribution matched its observed sample
(p=0.25-0.96 across chi-square/binomial/KS tests), and relationship
analysis confirmed the two intentionally-modeled dependencies (sex→BMI,
sex→smoking) show real association while all 11 independent-by-design
pairs showed p>0.10 — exactly the expected result. Two scaling blockers
were measured (not fixed, per M3's own instruction not to modify the
generator yet): a 37-minute wall time for 1,000 patients (I/O-bound CSV
re-reads, ~60+ hours projected at 100K) and ECG-record reuse across
patients (30 duplicate `ecg_id`s at n=1,000, a birthday-paradox effect
against the ~17,470-record training-fold pool). A high-confidence,
low-effort improvement was also identified: NNMS's urban/rural BMI
stratification was found during M2C-0's own research but never wired into
the generator. All findings documented in `docs/M3_PATTERN_INVENTORY.md`
and `docs/M3_DATA_QUALITY_REPORT.md`, with a full Candidate Generator
Improvements list (4 items, none implemented) in the session log. 16/16
tests still passing; a hardcoded-output-path bug in
`integration/validate_population.py` (found when it silently overwrote
M2C's validation summary) was fixed as tooling, not generator behavior.

## M3.5 — Candidate Improvements + Clinical Layer Design

Status: COMPLETE (2026-09-26) — `docs/session_logs/2026-09-26_M3_5-clinical-layer-design.md`

Audited all four M3 candidate improvements independently (not just from
M3's summary): **implemented** the I/O performance fix (process-level
caching in `ingestion/ptbxl_source.py` — the real bottleneck was
CPU-bound `ast.literal_eval` parsing re-run per patient, not raw
filesystem I/O as M3 had imprecisely characterized it; 1,000-patient
generation dropped from ~40min to 20.4s, verified zero content change,
`docs/DECISIONS.md` D009); **deferred** urban/rural-conditioned BMI
(NNMS's sex- and urban/rural-conditional figures are two separate 2-way
tables, not one joint table — combining them would require inventing a
methodology), ECG-ID reuse policy (semantics depend on an unmade Stage 4
decision), and state-boundary updates (no current-boundary source exists
— preserving Census 2011 fidelity, D010). Designed the full clinical
record layer (`docs/CLINICAL_RECORD_DESIGN.md`) — generation order,
dependency graph with evidence classification, and per-component design
for family history, medical history, diagnoses, medications, labs, and
timeline, all without inventing unsupported relationships. Reviewed
schema readiness (`docs/session_logs/2026-09-26_M3_5-clinical-layer-design.md`
§6) and produced a staged M4 plan (`docs/M4_CLINICAL_GENERATION_PLAN.md`)
starting with an evidence-verification stage. 20/20 tests passing (16
original + 4 new caching tests); no schema or generation-content change.

## M4-0 / M4-0A / M4-0B — Clinical Evidence Verification & Architecture

Status: COMPLETE (2026-09-26)

M4-0 audited evidence for family history, medical history, diagnoses,
medications, and labs (`docs/M4_CLINICAL_EVIDENCE.md`) — found HbA1c
(non-diabetic) has strong age×sex×urban/rural evidence, resolved
BMI-vs-height/weight in favor of keeping BMI-primary, and surfaced a
material dyslipidemia-evidence conflict as a human checkpoint. M4-0A
deep-researched that conflict (`docs/M4-0A_DYSLIPIDEMIA_DECISION_BRIEF.md`)
and found it was a definitional difference (NCEP LDL≥130 vs. LAI
LDL≥100), not a contradiction — correcting the reported new figure to
87.3% (not "~90%"). M4-0B converted the resulting human decision into a
formal architecture (`docs/M4_CLINICAL_ARCHITECTURE.md`,
`docs/DECISIONS.md` D011): continuous lipid values as primary data, with
multiple tagged definitions deriving labels from them; a documented
reversed-direction exception for HbA1c (generated conditional on the
already-primary diabetes label, not the other way around); hypertension
staying label-only pending BP-distribution research never yet conducted.
No code, schema, or generator change across all three sub-milestones.

## M4A — Evidence-Backed Clinical Schema Implementation

Status: COMPLETE (2026-09-26)

Implemented the minimum schema required by D011/M4-0B's approved
architecture — Schema v0.4 → **v0.5** (`docs/DECISIONS.md` D012):
`LipidPanel` (raw LDL/HDL/triglycerides/total cholesterol, mg/dL),
`LipidInterpretation` (derived, tagged by definition — e.g. NCEP_ATP_III,
LAI_2020 — never independently sampled), and a generic `Lab` structure
(reused for HbA1c rather than a dedicated type). `Patient.labs` retyped
from placeholder `Any` to `Lab` (open since M1). Structural (not
clinical) validation added: lipid-value sanity ranges, interpretation
well-formedness, analyte/unit matching. No generation logic — every new
field stays `null` until a future milestone populates it. Verified: a
regenerated 10-patient sample has **0 differences** in demographics/
risk_factors vs. the original M2C baseline (full backward determinism
preserved); 31/31 tests passing (11 new,
`tests/test_m4a_clinical_schema.py`).

## M4B — Clinical Value Generation + Validation

Status: COMPLETE (2026-09-26)

Implemented the generation logic approved by D011/D012
(`docs/DECISIONS.md` D013, `docs/M4B_GENERATION_DESIGN.md`): total
cholesterol/triglycerides/HDL sampled (category-then-uniform, ICMR-
INDIAB-17 marginals, same pattern as BMI); **LDL derived via the
Friedewald equation** (not independently sampled) — chosen after a
quantified check showed full independence would overstate the composite
dyslipidemia rate (86.5% implied vs. 81.2% actual cited); lipid
interpretations computed (never sampled) for both NCEP_ATP_III and
LAI_2020 definitions; HbA1c generated only for non-diabetic patients,
age×sex-conditioned on ICMR-INDIAB-12's trend, conditional on the
already-generated diabetes label (never the reverse). Verified: **0
differences** in demographics/risk_factors vs. the M4A baseline at both
10 and 100 patients; at n=100, NCEP composite dyslipidemia (84.0%,
binomial p=0.52) and LAI composite (88.0%, p=1.00) both statistically
indistinguishable from their cited rates; 6/100 patients hit the LDL
floor-clip safeguard (0 hit the ceiling); 0 structural validation
failures. 42/42 tests passing (11 new).

## M4C — Integrated Clinical Consistency + Patient Record Validation

Status: COMPLETE (2026-09-26)

Audited how every clinical field is actually generated today
(`docs/M4C_CONSISTENCY_AUDIT.md`) — found `diagnoses`/`medical_history`/
`medications`/`encounters` remain entirely unimplemented (designed in
M3.5, never coded), correcting this milestone's own initial framing.
Implemented `validation/clinical_consistency.py`
(`ClinicalValidationResult`: valid/errors/warnings/checks_performed),
validating the two "hard rule" relationships that actually exist today:
lipid panel → lipid interpretations (recomputed and compared exactly)
and diabetes → HbA1c (presence/absence/range). **Surfaced a real,
previously-unnoticed architecture inconsistency**: `risk_factors.
hyperlipidemia` (M2C) and `lipid_interpretations` (M4B) disagree 23-27%
of the time — recorded as a human-checkpoint finding
(see "Human Decisions Required" above), not silently fixed. 10/10 and
100/100 patients: 0 clinical-consistency errors, 0 warnings, both
structurally and clinically valid. 55/55 tests passing (13 new). No
generation behavior, schema, or population distribution changed.

## M4C — Hyperlipidemia Semantic Audit + Option B Resolution

Status: COMPLETE (2026-09-26)

Resolved the M4C human checkpoint above. Human decision: **Option B —
keep `risk_factors.hyperlipidemia` and `lipid_interpretations` as
distinct variables.** Before implementing, ran a semantic audit tracing
`risk_factors.hyperlipidemia` to its M2C origin
(`docs/M4C_HYPERLIPIDEMIA_RESOLUTION.md`): it was always designed and
built as a population/background risk-factor attribute (unconditioned
`Bernoulli(0.812)` from ICMR-INDIAB-17, same role as
`hypertension`/`diabetes`), never as a per-patient claim derived from
lipid measurements. **Conclusion: PARTIALLY CONFIRMED** — Option B is
compatible with everything actually built and with the field's
original documented intent; only D011's own wording ("LDL and
hyperlipidemia must never be independently generated as unrelated
random variables") was imprecise and needed scoping, not reversal —
narrowed via `docs/DECISIONS.md` D014 to apply only to the raw
LDL↔lipid_interpretations pair it was actually about. Recorded the
formal contract: `lipid_panel` ↔ `lipid_interpretations` remains
**hard consistency** (unchanged); `risk_factors.hyperlipidemia` ↔
`lipid_interpretations` is an **expected semantic difference**, never a
validation error. Updated `validation/clinical_consistency.py`'s
docstring/comments to cite D014; added 3 new tests covering all
agreement/disagreement combinations. Verified on real pipeline output
(`outputs/m4c/100_patients/`, unregenerated — no generation code
touched): 73/100 patients disagree/agree exactly as before, yet 0
clinical-consistency errors/warnings at both 10 and 100 patients.
58/58 tests passing (3 new). No generation, schema, or distribution
change. No remaining human checkpoint from this question.

## M4D — Diagnoses + Medical History Generation

Status: COMPLETE (2026-09-26)

Audited actual current state first (`docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md`)
— found `diagnoses` was an untyped `list[Any]` placeholder and
`medical_history` was, unexpectedly, an untyped **dict** (not a list),
both `None` for every patient M1-M4C; the milestone prompt's own assumed
shape didn't match the code. Implemented `generation/clinical_history.py`
(`derive_diagnoses()`/`derive_medical_history()`, pure/deterministic, no
RNG): hypertension/diabetes diagnoses are a 1:1 promotion of the
already-generated risk_factors flags (no new prevalence); medical_history
`chronic_condition` entries reference those diagnoses by id rather than
re-deriving them. **Hyperlipidemia's diagnosis deliberately deferred** —
collapsing the two coexisting `lipid_interpretations` definitions
(NCEP_ATP_III, LAI_2020) into one boolean would silently make the
canonical-definition choice D011 declined to make; not resolved
unilaterally. `diagnosed_date`/`event_date` always `None` — no
per-patient onset-date evidence exists. Schema change (`Diagnosis`,
`MedicalHistoryEntry` dataclasses, `SCHEMA_VERSION` 0.5→0.6) determined
additive/precedented (matches D006/D012), not a human-checkpoint-triggering
"significant restructuring" — proceeded autonomously, recorded as
`docs/DECISIONS.md` D015. Extended `validation/structural.py`
(`DIAGNOSIS_CODES`/`MEDICAL_HISTORY_CATEGORIES` vocabulary checks) and
`validation/clinical_consistency.py` (`diagnosis_risk_factor_consistency`/
`medical_history_diagnosis_consistency` hard rules). Verified at n=100:
0 differences in demographics/risk_factors/lipid_panel/
lipid_interpretations/labs vs. the M4C baseline (a pre-existing,
unrelated `ecg.superclasses` list-order non-determinism was observed and
documented, not caused by this milestone); diagnosis counts match
risk-factor counts exactly (34 hypertension, 9 diabetes); only
`chronic_condition`/`hypertension`/`diabetes` ever appear — no
cv_event/procedure/hyperlipidemia diagnosis accidentally generated.
78/78 tests passing (20 new). 10/10 and 100/100 patients: 0
clinical-consistency errors, 0 warnings.

## M4E — Medication Evidence + Architecture + Implementation

Status: COMPLETE (2026-09-27)

Evidence audit (`docs/M4E_MEDICATION_EVIDENCE.md`, two parallel
research passes): ICMR-NNMS 2017-18 national treatment-rate cascades
confirmed SUPPORTED for antihypertensive (14.5%) and antidiabetic
(36.1%) treatment. Statin/antiplatelet population treatment rates: NOT
SUPPORTED (only hospital-registry data found, excluded per this
project's standing non-representative-cohort rule). NLEM 2022 drug-name
evidence remains secondary-source-only (same PDF-access wall as prior
research); confirmed it establishes availability, not prescribing
share — no specific drug name is generated.

Implemented `Medication` (drug_class/diagnosis_id/current_status/
start_date/stop_date, `drug_class` ∈ {antihypertensive, antidiabetic}
only) via `generation.indian_population.sample_medication_treatment()`
(NNMS-rate Bernoulli, additive at the end of the existing draw sequence)
and `generation.clinical_history.derive_medications()` (deterministic
construction, references diagnoses, never resamples). Statin/
antiplatelet medications not generated — doubly blocked for statins
(no rate evidence AND hyperlipidemia's diagnosis itself is deferred,
D015); antiplatelet has no evidence and no diagnosis to gate against
either. `start_date`/`stop_date` always null; `current_status` always
`"active"` (direct mapping of NNMS's own point-prevalence measurement).
Schema change (`SCHEMA_VERSION` 0.6→0.7) determined additive/
precedented, proceeded autonomously, recorded as `docs/DECISIONS.md`
D016. Extended structural + clinical-consistency validation
(`medication_diagnosis_consistency`: orphan-reference, drug_class↔
diagnosis-code mapping, active/stop_date invariant, date ordering,
one-medication-per-diagnosis). No human checkpoint required — checked
against every listed STOP trigger, none applied (`docs/
M4E_MEDICATION_DESIGN.md` M4E-3).

Verified at n=100: 0 differences in demographics/risk_factors/
lipid_panel/lipid_interpretations/labs/diagnoses/medical_history vs.
the M4D baseline (700/700 field comparisons exact); observed treatment
rates (5/34 hypertension=14.7%, 3/9 diabetes=33.3%) statistically
indistinguishable from cited rates (exact binomial p=1.000 both).
103/103 tests passing (25 new). 10/10 and 100/100 patients: 0
clinical-consistency errors, 0 warnings.

## M4F — Final Clinical Completeness + Pre-Scale Audit

Status: COMPLETE (2026-09-27)

Full domain matrix (`docs/M4F_FINAL_CLINICAL_AUDIT.md`): demographics,
all 5 risk factors, lipid panel/interpretations, HbA1c (NGT), ECG
metadata are fully complete and validated; diagnoses/medical_history/
medications are correctly partial (evidence-bounded, not oversight);
family history/ECG waveform/echo/procedures/stroke/heart-failure/
general-CVD remain correctly unimplemented. Human-decision audit found
**no new category-C items** — the one already-open item
(hyperlipidemia-diagnosis definition choice) remains the only genuine
human decision outstanding; three narrower items
(`TimelineEvent.reference_id`, `birth_date`, family-history scope) were
already known, restated not rediscovered. **Zero Category-A bugs
found.** Full suite (103/103) re-confirmed unchanged; fresh 10/100/1,000-
patient generation and validation: 0 structural errors, 0
clinical-consistency errors/warnings at all three scales. One
statistically borderline finding (antidiabetic treatment rate, 45.1%
observed vs. 36.1% cited at n=113, p=0.050) investigated via an isolated
50,000-draw sampler check (35.88% observed, p=0.308) — confirmed
sampling variation at a small conditional sub-sample, not a defect,
same method M2C used for its own borderline finding.

Scale benchmark (5,000 patients, existing caching unmodified): 71.6
patients/sec, memory flat (~265MB steady-state, no leak), 100K
estimated at **~23 minutes**. Storage measured directly: 3,551
bytes/patient average, **100K ≈ 0.36 GB** (metadata-only); a future
waveform representation (schema's own declared [1000,12] float32
shape) would add ~4.8GB at 100K — not implemented, estimate only.

ECG readiness audit: metadata-only architecture is internally
consistent and additively extensible for a future waveform (no
restructuring needed); identified **existing, previously-trained,
unused per-superclass GAN checkpoints**
(`syngen/SynGen/SynGen/checkpoints/generator_{CD,HYP,MI,NORM,STTC}.pt`)
as a real future candidate, distinct from CardioSynth/CardioSync — not
evaluated or selected. Duplicate `ecg_id` reuse (30 groups/1,000
patients, unchanged from M3) will become pervasive at 100K against the
fixed ~17,470-record pool — flagged as the one real scale concern
(YELLOW), not blocking.

**100K readiness: READY (conditionally) — no RED item, two documented
YELLOW items (medication scope, ECG-ID reuse at scale), no human
checkpoint blocks proceeding with the current schema.** No behavioral
change, no schema change, no new dataset introduced this milestone.
`docs/DECISIONS.md` not updated — no genuine new decision was made,
per this milestone's own instruction.

## M5 — 100K Baseline Synthetic Population Generation

Status: COMPLETE (2026-09-27)

Generated the project's first complete 100,000-patient baseline dataset
(`outputs/m5/100k_patients/`, gitignored) using the existing, unmodified
production pipeline, seed 42, Schema v0.7. **0 generation errors, 0
duplicate patient IDs, 100,000/100,000 structurally valid, 100,000/
100,000 clinically consistent (0 errors, 0 warnings).** Full report:
`docs/M5_100K_DATASET_REPORT.md`; machine-readable manifest:
`outputs/m5/dataset_manifest.json`.

Generation: 23.3 minutes, 71.5 patients/sec, memory flat (small ~9MB
drift over the full run, negligible). Storage: 355.12 MB measured
(matches M4F's 0.36GB projection almost exactly). Every statistically-
checked demographic/risk-factor/lipid-category variable within expected
sampling variation of its cited target (p=0.17-0.92). One expected
finding newly visible at this scale: the NCEP/LAI composite dyslipidemia
rates (82.99%/85.58%) are now statistically distinguishable from their
cited headline figures (81.2%/87.3%) — **not a new problem**, D013
already quantified and accepted this exact structural gap (full
independence would imply 86.5%; Friedewald reduces but doesn't
eliminate it) when the small-n sampling noise at n=100 masked it;
**not corrected**, per this milestone's explicit instruction not to
modify evidence-backed behavior for statistical appearance. Relationship
checks confirmed sex×BMI and sex×smoking strongly present (as designed)
and hypertension×smoking negligible-effect-size independent (Cramér's
V=0.0049, as intended — no relationship modeled there). ECG-ID reuse
quantified at scale (17,386 unique IDs, max reuse 17×, mean 5.75×) —
not solved, recorded as evidence for a future ECG-architecture decision.
**Zero Category-A bugs. Zero behavioral code changes. Zero schema
changes. No new datasets. No human checkpoint.** 103/103 tests
unchanged. Full session record:
`docs/session_logs/2026-09-27_M5-100k-baseline-generation.md`.

## M5.5 — Clinical Field Completion (Blood Pressure, Encounters, Timeline References) + Full-Dataset Migration & Validation, Schema v0.7 → v0.8

Status: COMPLETE (2026-10-20) — `docs/DECISIONS.md` D017,
`docs/M8_FULL_DATASET_VALIDATION_REPORT.md`,
`docs/M8_ECG_HELDOUT_PILOT_REPORT.md`

**Naming note:** referred to as "M8" in D017, `integration/
migrate_v07_to_v08.py`, and `validation/pilot_50_records/` (that work
predates this PROJECT_STATE.md update). Numbered M5.5 here instead,
between M5 and M6, because `ROADMAP.md`'s own placeholder "M8" label
means "integrate ECG generation" and was never kept in sync with this
file's actual milestone numbering — this entry is unrelated to ECG and
sits chronologically right after M5.

Implemented the blood-pressure, encounters, and timeline-reference
fields `docs/CLINICAL_RECORD_DESIGN.md` §A/§H had flagged as open
design forks, piloted on 50 records first, then migrated and validated
at full 100,000-record scale:

* **Blood pressure** (`BloodPressure` dataclass) — generated
  CONDITIONAL on the already-primary `risk_factors.hypertension` label
  (never the reverse), using NFHS-5 age-band × sex evidence (PLOS ONE
  2025) with SDs and an SBP/DBP correlation (r=0.7255) DERIVED from
  published variances, not assumed. A treated hypertensive's reading is
  left unconstrained rather than forced to confirm the label. One
  explicit engineering assumption (a 20mmHg pulse-pressure floor,
  measured to remove a 10.7%→0% narrow-PP artefact) — fully disclosed.
* **Encounters** (`Encounter` dataclass) — one declared structural
  container per record (`synthetic_baseline_assessment`), NOT a claimed
  healthcare visit; names the measurement cross-section an already-
  existing date owned but previously had no identifier for.
* **Timeline** — `TimelineEvent.reference_id` added (the additive change
  `docs/CLINICAL_RECORD_DESIGN.md` §H proposed), indexing the encounter.
* **Height/weight** — still NOT generated; 6 total research attempts
  (3 in M4-0, 3 here) found no national mean+SD of Indian adult height
  by sex. `sample_height_cm()` is a tested no-op that raises if the
  config ever gains height evidence while still returning `None`.
* **Family history** — still NOT generated; scope remains an open human
  decision (unchanged from M4F), not resolved here.

Schema v0.7 → v0.8. Migration (`integration/migrate_v07_to_v08.py`) is
idempotent, deterministic, and **replays each record's own recorded
seed** to generate BP — verifying every pre-existing field matches
before accepting the new one, so migration and fresh generation agree.

**Full-dataset results (100,000 records, `outputs/m8/100k_patients_
v08/`):** 100,000/100,000 structurally valid (recomputed, not trusted
from the stored flag), 100,000/100,000 clinically consistent (0
errors), 0 duplicate IDs, **100,000/100,000 migration-integrity exact
matches** (every record re-derived fresh from its untouched v0.7 source
and diffed byte-for-byte against disk — 0 differences, 0 orphans either
direction). Source dataset (`outputs/m5/100k_patients/`) confirmed
unmodified. 16,297 clinical warnings, all pre-existing/documented (see
below) — none newly introduced. Dataset frozen:
`outputs/m8/dataset_manifest.json` (same convention as M5's manifest).

**Headline unresolved issue, surfaced not introduced:** `lipid_panel`'s
TC/TG/HDL are sampled as independent marginals (pre-existing M4B
design), so 2,283 records (2.28%) are internally impossible (TC below
HDL+TG/5) and 9,831 (9.83%) have LDL at the documented clip floor
rather than a derivation. Flagged as a validator WARNING (not an error —
the stored LDL does follow its documented clip rule); fixing it is a
D011-level sampling decision, not made in this milestone. Full detail:
`validation/pilot_50_records/reports/validation_report.md` §6.1.

**ECG track (separate, engineering-only, does not cross the M6/M7
model-selection checkpoint):** re-evaluated the inherited per-class GAN
(`syngen/SynGen/SynGen`) against truly held-out (fold 9, never-trained-
on) real PTB-XL data instead of the training-fold data
`docs/syngen-codebase-analysis.md` §12.1 had flagged as a measurement
bug. Held-out KS statistics are within ±0.008 of the (leaky) originally-
reported ones across all 5 classes — the model is not memorizing its
training set, though absolute quality (KS≈0.07-0.10) sits at the
boundary of the scripts' own "excellent" threshold, not comfortably
inside it. Confirmed via the architecture (not assumed): the 5
generators share no weights and take no class-conditioning vector, so
**no patient demographic/clinical field conditions this model** — a
waveform from it would carry no model-conditioned relationship to its
patient. Amplitude calibration remains unconfirmed (pre-existing gap,
§12.5 — per-record normalization stats are discarded, not persisted).
Full detail: `docs/M8_ECG_HELDOUT_PILOT_REPORT.md`. **Model selection
(this GAN vs. SSSD-ECG vs. anything else) remains the open human
checkpoint M6/M7 already established — not decided, not advanced, by
this pilot.**

Two bugs were found and fixed in the validation tooling itself while
scaling it to 100,000 records (an accidental O(n²) directory re-scan,
and unbounded memory growth from holding three full-population lists
at once — rewritten as a single streaming pass, confirmed flat at
~185-205MB regardless of population size). Both are recorded in
`docs/M8_FULL_DATASET_VALIDATION_REPORT.md` §8 for transparency; neither
affected the dataset itself. 142/142 project tests passing throughout
(104 pre-M8 + 38 new M8 unit tests), plus 37 pilot-batch gates.

## M9 — Field-Completeness Audit, Lipid Sampling Fix (D019), Family-History & AQI Strategy Planning

Status: IN PROGRESS (2026-10-30) — audit + one fix complete; two
strategy plans written, awaiting human sign-off before implementation.

Ran a new read-only field-completeness audit
(`integration/audit_field_completeness.py`) against the full frozen
100,000-record v0.8 dataset for the first time — full output
`docs/M9_FIELD_COMPLETENESS_AUDIT.json`, summarized in `docs/
Further_Steps_for_patient-Record_complete.txt` §1. **Result: every
currently-implemented field is 100% valid at full scale; zero defects
found anywhere** (HbA1c's 11.457% null exactly matches the diabetic
population as designed; height/weight/family_history remain 100% null
exactly as documented; 0 BP label-region violations across all 39
audited cells; 0 unexpected/undocumented keys). All remaining record
work is new scope, not bug-fixing.

Implemented `docs/DECISIONS.md` D019 (human-approved): lipid panel
TC/TG/HDL triples that make the Friedewald LDL negative (~2.28% of
draws) are now rejected and redrawn in
`generation/indian_population.py`'s `sample_lipid_panel()` — marginals
unchanged, only infeasible triples excluded. Verified 0/200,000
infeasible triples post-fix. **Not yet applied to the frozen
dataset** — only the generation code changed; a re-freeze is a
separate, deliberately deferred decision (see Next Action below).
145/145 tests passing (142 prior + 1 new regression test + 2
pre-existing M9 tests run for the first time).

Did deep evidence research (not reused from any prior summary) for two
new attributes, per explicit user request, and wrote two standalone
strategy documents rather than implementing either yet:
- **Family history**: confirmed no national source covers the full
  20-89 target age range for any condition. LASI Wave 1 (45+, national)
  has two usable figures — diabetes 14.33%, CVD 11.61% (PMC11659756,
  newly confirmed this session) — ICMR-INDIAB collects but never
  publishes a usable prevalence; WHO STEPS has age-appropriate but only
  state-level figures. Full findings + a D017-precedented tiered
  recommendation (45+ partial coverage, explicitly flagged, nothing
  invented for 20-44): `docs/Family_history_Strategy_plan.txt`.
- **AQI (new attribute)**: investigated CPCB official/ODbL sources;
  found the central blocker is schema granularity (state+urban/rural
  only, no city/district) combined with CPCB's urban-biased monitoring
  network. Recommended approach (state-level annual-mean AQI with an
  explicit urban-bias disclosure field, additive schema change, full
  provenance) and a 7-step implementation sequence, once approved:
  `docs/Further_Steps_for_patient-Record_complete.txt` §3.

Full session record:
`docs/session_logs/2026-10-30_M9-lipid-fix-family-history-aqi-planning.md`.

**Family history implemented (2026-11-10, `docs/DECISIONS.md` D020,
human-approved):** a second source search confirmed no national
family-history figure exists for ages 20-44 (CARRS, urban 20+, kept as
a cross-check only). `family_history` = `{diabetes,
cardiovascular_disease, derivation}`: LASI observed marginals for 45+;
for 20-44 a parent simulation over LASI age-band × sex prevalence,
calibrated (k) to reproduce the 45+ figure; diabetes family history
conditioned on the patient's diabetes via LASI's crude OR 3.80. 50,000-
draw check: 45+ 14.40% / 11.33% (targets 14.33 / 11.61), 20-44 12.2% /
8.9% (≤ CARRS urban 22.2 / 9.0). 1,000-record pilot
`outputs/m9/pilot_1000_family_history/`: 1000/1000 valid and
consistent, 0 errors. 157/157 tests. **Frozen 100K dataset not yet
regenerated** (still null there): re-freeze remains the open bundling
decision below.

**Air quality implemented (2026-11-10, `docs/DECISIONS.md` D021,
human-approved), schema v0.8 → v0.9:** new `Patient.air_quality`, a
deterministic lookup by state of the 2023 CPCB annual-mean AQI
(CAAQMS hourly station data via the ODbL Vonter republication;
station → city → state; CPCB National AQI scale), urban-station bias
flagged on every record, null with a reason for 9 states/UTs (~3.4%).
Reproducible via `ingestion/cpcb_state_aqi.py`. Delhi 212.3 vs official
204 (+4%). 1,000-record v0.9 pilot `outputs/m9/pilot_1000_v09/`:
1000/1000 valid and consistent, 0 errors. 174/174 tests.

**100K re-freeze at v0.9 COMPLETE (2026-11-10):** fresh generation of
all 100,000 records (`outputs/m9/100k_patients_v09/`, seed 42), bundling
D019 + D020 + D021. 100,000/100,000 structurally valid and clinically
consistent, 0 errors; family history 45+ 14.41% / 11.62% (targets
14.33 / 11.61), 20-44 11.97% / 8.37%; AQI null 3.37% (expected 3.43%,
all with a reason); 0 impossible lipid panels. Manifest
`outputs/m9/dataset_manifest.json` (checksum 53fcae20…).
`integration/freeze_dataset_manifest.py` now supports fresh (non-
migrated) datasets and v0.9 limitations text. **Open issue:** generation
took 118 min wall-clock vs M5's 23 min although per-record cost is
unchanged (~12 ms, profiled; new code ~0.6 ms) — likely the script
holding all 100K records in memory before writing; not yet investigated.

## M6 (next — not started)

Status: ECG MODEL SELECTED (2026-10-21, `docs/DECISIONS.md` D018 —
inherited per-class GAN; SSSD-ECG/CardioSynth rejected). M7 waveform
integration engineering not yet started.

Awaiting explicit authorization. Candidates once authorized: ECG
architecture decision (reuse-policy at scale, or begin Stage 4 waveform
work); resolve the hyperlipidemia-diagnosis question; pattern discovery
over the 100K baseline (Stage 7); model selection (Stage 9). Deliberately
NOT started by M5: ECG waveform generation, CardioSynth/CardioSync
integration/selection, any model training, AWS, or 1M-scale generation.

**Research pre-work done (2026-09-27), no milestone/decision change:**
five parallel research tracks gathered evidence for the eventual model-
selection checkpoint — hardware/VRAM/storage feasibility (no RED cell
found up to 1M patients on an 8GB or 36GB local GPU; AWS not required),
ECG generative-model landscape (**SSSD-ECG** is the strongest verified
lead — MIT-licensed, weights on Figshare, conditions on PTB-XL SCP
labels matching this project's `ecg.superclasses`), a CardioSynth/
CardioSync identification audit (confirmed **not viable as-is** — the
one real GitHub match is an unlicensed single-lead demo scaffold, not
12-lead/PTB-XL-compatible), synthetic-ECG validation methods (NeuroKit2
and a health-data membership-inference method are ready to reuse
directly), and a broader licensing audit (**failed**, rate-limited,
needs a retry). Full detail: `docs/session_logs/2026-09-27_M6-model-selection-research.md`.
Per CLAUDE.md §11/§28, model selection remains a human checkpoint —
this is evidence, not a decision.

**Compatibility/licensing audit completed (2026-09-27), no milestone/
decision change:** SSSD-ECG's native format confirmed PARTIALLY
compatible — sample count (1000) and rate (100Hz) match directly;
tensor axis order and lead order need a lossless conversion;
conditioning labels do not match without new work (pretrained
checkpoint expects 71-dim raw PTB-XL SCP codes, this project has only
5-class superclasses). Licensing audit PARTIAL — code (MIT), PTB-XL
(CC BY 4.0), and NeuroKit2 (MIT) confirmed; the SSSD-ECG pretrained-
weight license remains UNKNOWN (Figshare access blocked, needs a human
with an authenticated session). Full detail: `docs/M6_SSDD_ECG_COMPATIBILITY.md`,
`docs/M6_MODEL_SELECTION_DECISION_BRIEF.md`, `docs/M6_ECG_VALIDATION_PLAN.md`,
`docs/session_logs/2026-09-27_M6-ecg-compatibility-audit.md`. Model
selection remains an open human checkpoint.

**Decision phase completed (2026-09-27), still no milestone/decision
change — model selection remains open:** assembled the full M6 decision
package. New findings this pass: (1) the SSSD-ECG conditioning-label
figure needed a correction — the actual `label_diag` construction code
uses 44 diagnostic-flagged SCP codes, not 71, an unresolved discrepancy
against the checkpoint config's `label_embed_classes: 71`; (2) the raw
`scp_codes` data SSSD-ECG-style conditioning would need is **already
present locally** in this project's existing PTB-XL CSVs — no new
dataset required, just an unwritten extraction function; (3) a
dedicated audit of four alternative candidates (DiffuSETS, FlowECG,
cNVAE-ECG, a FEM-simulator VAE) found none displaces SSSD-ECG as the
only candidate with both runnable inference code and a real (if
license-unresolved) pretrained checkpoint; (4) a new leakage
consideration specific to third-party pretrained models (this
project's own fold-1-8 discipline doesn't guarantee the *external
model's own training* avoided PTB-XL folds 9/10). Full package:
`docs/M6_ECG_MODEL_SELECTION.md` (decision brief), `docs/
M7_ECG_IMPLEMENTATION_PLAN.md` (staged M7-0 through M7-8 engineering
plan, not started), `docs/session_logs/2026-09-27_M6-model-selection.md`.
103/103 tests re-confirmed passing, no code changed. Recommended next
step: M7-0 — a human manually confirms the pretrained-weight license
before any further SSSD-ECG-specific work proceeds.

---

# Project Stages

## Stage 0 — Definition

Status: COMPLETE

## Stage 1 — Existing Codebase Understanding

Status: COMPLETE

## Stage 2 — Foundation

Status: IN PROGRESS

Target:

One complete, structurally valid synthetic patient.

## Stage 3 — Patient Population Generation

Status: COMPLETE (2026-09-27, M5) — target exceeded 1000x

Target:

100 validated synthetic patients. **Achieved: 100,000/100,000
validated (M5).**

## Stage 4 — ECG / Multimodal Integration

Status: NOT STARTED

Target:

Complete patient records with available modalities.

## Stage 5 — Validation & Quality Control

Status: NOT STARTED

Target:

Automated validation and quality reports.

## Stage 6 — Scaling

Status: 100K baseline COMPLETE (2026-09-27, M5); 1M not yet attempted

Target:

1K → 10K → 100K+ validated records. **Achieved: 1K (M3), 100K (M5,
`outputs/m5/100k_patients/`, 0 errors). 1M not yet generated — M4F/M5
benchmarks project ~3.55 GB / ~4 hours linearly extrapolated, not
independently verified at that scale.**

## Stage 7 — Pattern Discovery

Status: NOT STARTED

Target:

Identify meaningful population-level patterns and relationships.

## Stage 8 — Indian Demographic Conditioning

Status: NOT STARTED

Target:

Represent relevant Indian demographic characteristics and patterns appropriately.

## Stage 9 — Generative Model Integration

Status: NOT STARTED

Target:

Integrate the selected existing generative model with minimal unnecessary overhead.

Current candidate:

CardioSynth/CardioSync

IMPORTANT:
This is not yet a final model decision.

## Stage 10 — Final Generation Pipeline

Status: NOT STARTED

Target:

Demographic/context input
→ learned/discovered patterns
→ selected model
→ synthetic patient fields/records
→ validation

---

# Current Work

Nothing currently blocked.

M2C complete. Next: M2D/Stage 3 continuation — height_cm/weight_kg,
medical_history/diagnoses/medications/labs/encounters, still without
claiming clinical validity.

---

# Completed Work

* Project scope defined
* Schema v0.2 defined
* Existing codebase analysis completed
* Existing reusable components identified
* High-level architecture defined
* Development strategy defined
* Repository structure decision recorded (Candidate A, flat — `docs/DECISIONS.md` D001)
* Schema v0.2 implemented as dataclasses (`schemas/patient_schema.py`)
* Patient ID generation (`integration/patient_id.py`)
* PTB-XL ECG-metadata ingestion adapter reusing syngen's `build_label_map()`
  (`ingestion/ptbxl_source.py`)
* Structural validation (`validation/structural.py`)
* Patient-assembly orchestration (`integration/build_patient.py`)
* One structurally valid synthetic patient generated and inspected
  (`outputs/test/PAT_000001.json`)
* 5/5 tests passing (`tests/test_stage2_foundation.py`)
* `.gitignore` updated to exclude syngen's large binary assets while keeping
  its reused `.py` code tracked
* M2A: Indian population dataset research completed
  (`docs/INDIAN_DATA_SOURCES.md`)
* M2B: Indian generation strategy designed
  (`docs/INDIAN_GENERATION_STRATEGY.md`)
* Schema v0.3: `Demographics` gained `state` and `urban_rural` fields
  (`docs/DECISIONS.md` D005)
* M2C: Indian-conditioned demographic + risk-factor generation implemented
  and validated — Schema v0.4 (`RiskFactors` dataclass, `docs/DECISIONS.md`
  D006), `configs/indian_population.yaml`,
  `generation/indian_population.py`, `validation/statistical.py`; 10 and
  100 synthetic patients generated and inspected
  (`outputs/m2c/10_patients/`, `outputs/m2c/100_patients/`); full record in
  `docs/session_logs/2026-09-25_M2C-indian-conditioning.md`
* M2D: all 7 M2C-flagged limitations audited; existing implementation
  confirmed evidence-correct (zero behavioral changes); age's alternative
  source found and quantifiably rejected (`docs/DECISIONS.md` D007);
  population-target ambiguity surfaced (general Census demographics vs.
  NNMS-18-69 vs. INDIAB-20+ risk factors — not resolved, recorded in
  `configs/indian_population.yaml`); 100-patient regression confirmed
  byte-identical output; 10,000-draw sampler checks confirm no
  implementation bias; full record in
  `docs/session_logs/2026-09-25_M2D-calibration-quality-gate.md`

---

# Reusable Existing Components

Refer to the existing codebase analysis.

Known areas of interest include:

* PTB-XL handling
* ECG metadata
* SCP/diagnostic label mapping
* ECG preprocessing
* ECG evaluation
* Fold handling
* Existing ECG generation/inference functionality

---

# Current Dataset Counts

Synthetic patients generated:

**CURRENT: 100,000 at schema v0.9 (M9, 2026-11-10,
`outputs/m9/100k_patients_v09/`, fresh generation, seed 42; frozen
`outputs/m9/dataset_manifest.json`, `sysdag_m9_100k_v09` 0.9.0)** —
includes D019 lipid fix, D020 family history, D021 air quality.
Previous: 100,000 at schema v0.8 (M5.5, `outputs/m8/100k_patients_v08/`,
migrated from the M5 v0.7 baseline, 50-record pilot preceded it at
`validation/pilot_50_records/`)** — the M5 v0.7 baseline
(`outputs/m5/100k_patients/`) is preserved unmodified as its source +
1,000 (M3 development run) + 1,000/100/10 from M4F + a 5,000-patient
M4F scale benchmark + 100 each from M4B/M4C/M4D/M4E + 10-patient runs
across M2C/M4A-M4E and M1's original `PAT_000001`; none are tracked
dataset artifacts, see `.gitignore`

Validated synthetic patients:

**CURRENT: 100,000/100,000 structurally + clinically valid at schema
v0.9 (0 errors, 0 duplicate IDs, 0 internally impossible lipid panels
(was 2,283), 14,206 WARNINGS of two pre-existing kinds: LDL at clip
floor 7,740 (was 9,831), empty PTB-XL superclasses 6,466)** —
`outputs/m9/100k_v09_validation_report.json`; every distribution
within sampling error of its config target (max |z| 1.14,
`outputs/m9/100k_v09_distribution_check.txt`). Previous:
100,000/100,000 structurally + clinically valid at schema v0.8 (M5.5,
0 structural errors, 0 clinical errors, 16,297 clinical WARNINGS —
all pre-existing/documented, none newly introduced) + 100,000/100,000
migration-integrity exact matches against the untouched v0.7 source**
— full detail `docs/M8_FULL_DATASET_VALIDATION_REPORT.json`. Superseded
the prior M5 v0.7 validation (100,000/100,000, 0 errors/warnings) as the
current full-scale figure; 50/50 at pilot scale
(`validation/pilot_50_records/reports/validation_report.md`); sampler
correctness confirmed at n=10,000 (M2D) and n=50,000 (M4F); relationship/
dependency audit confirms no implementation bias (M3,
`docs/M3_PATTERN_INVENTORY.md`; reconfirmed at n=100,000 in M5)

Target:

100,000+ — **first 100,000 target met (M5), now at schema v0.8 (M5.5)**.
Next: pattern discovery/scaling decisions per Stage 7+, or the M6/M7
ECG model-selection checkpoint.

---

# Current Models

No final generative model has been selected.

Do not introduce or train additional models unless a concrete project requirement is identified.

---

# Current Validation

Foundation-level validation:

IMPLEMENTED — `validation/structural.py`: patient_id format, schema_version
match, demographics range/type checks (incl. state membership, urban_rural,
BMI range, smoking_status vocabulary), ECG signal_shape/strat_fold checks,
non-empty timeline, duplicate-ID detection. Extended M5.5 for schema v0.8:
blood_pressure type/unit/bounds/systolic>diastolic, encounter_type/
timeline event_type vocabulary checks.

Population-level validation:

IMPLEMENTED (M2C) — `validation/statistical.py`: chi-square goodness-of-fit
(categorical), exact binomial test (Bernoulli risk factors), one-sample KS
(uniform age) via `scipy.stats`, compared against
`configs/indian_population.yaml`'s own parameters. Sanity check only — see
`docs/session_logs/2026-09-25_M2C-indian-conditioning.md` for the
overclaiming caveat.

Full-population structural + clinical + migration-integrity validation:

IMPLEMENTED (M4C, extended M5.5) — `integration/validate_clinical_
population.py`: single streaming pass (memory-bounded regardless of
population size — see `docs/M8_FULL_DATASET_VALIDATION_REPORT.md` §8)
over an entire output directory; recomputes structural + clinical
validity per record (never trusts the record's own stored flag);
`--compare-source` re-derives each record from its untouched source via
the real migration function and diffs byte-for-byte against disk;
`--stats` for population-level distribution/missingness/duplicate
summaries. Run at full 100,000-record scale in M5.5 with 0 errors and
100,000/100,000 migration-integrity exact matches.

Cross-modal validation:

NOT IMPLEMENTED (ECG held-out re-evaluation in M5.5 is a within-modality
GAN quality check, not cross-modal patient-record validation)

---

# Current Compute Strategy

Development:

Local machine preferred.

Large-scale compute:

To be evaluated only when necessary.

AWS:

Not currently required.

---

# Active Blockers

None.

---

# Human Decisions Required

**Consolidated decision brief: `docs/M8_DECISION_BRIEF.md`** — all
seven currently-open items below (five from M5.5 + two carried
forward), each with question/options/evidence/risk/recommendation kept
separate, plus the full ECG model comparison and M6 sequencing
analysis. This section remains the live summary; the brief is the
detailed reference.

**Five new open items from M5.5 (schema v0.8), none blocking the
current freeze — all documented, none resolved unilaterally:**

1. **Lipid independent-marginal sampling.** TC/TG/HDL are sampled as
   three independent values (pre-existing M4B design), producing 2.28%
   internally-impossible panels and 9.83% LDL-at-clip-floor at full
   scale. Fixing requires a D011-level decision (constrain sampling to
   keep triples feasible, or redefine which quantity is primary) — not
   made here. `validation/pilot_50_records/reports/validation_report.md`
   §6.1, `docs/M8_FULL_DATASET_VALIDATION_REPORT.md` §4/§7.
2. **Family-history scope — DECIDED 2026-11-10, `docs/DECISIONS.md`
   D020** (LASI 45+ observed, calibrated parent simulation 20-44,
   diabetes-conditioned). Implemented in generation code and piloted on
   1,000 records; the frozen 100,000 v0.8 records are still null until
   a re-freeze is approved.
3. **Whether `encounters` should hold a structural container at all.**
   M5.5 populated it as a declared non-clinical container
   (`synthetic_baseline_assessment`) naming an already-existing
   measurement date. A reviewer may prefer `null` pending a different
   care-utilization model. Cheap to reverse.
4. **The 20mmHg blood-pressure pulse-pressure floor** — the one value in
   the BP design that was set (to remove a measured 10.7%→0% narrow-PP
   artefact) rather than read off or derived from a source. Declared,
   measured, reversible.
5. **ECG model selection — DECIDED 2026-10-21, `docs/DECISIONS.md`
   D018.** Inherited per-class GAN selected (own asset, held-out
   validated, zero licensing risk); SSSD-ECG rejected (pretrained-weight
   license unresolvable — DOI does not resolve, share link streams only
   a raw `.pkl` with no license, two automated fetches 403'd, a human
   confirmed directly); CardioSynth/CardioSync rejected (not viable,
   unchanged from M6). Known accepted limitation: the GAN's waveform is
   diagnosis-class-conditioned only, not patient/demographic-conditioned
   — must be disclosed in product/provenance metadata, not overclaimed.
   See `docs/M8_ECG_HELDOUT_PILOT_REPORT.md` for the GAN's validation
   evidence.

The `risk_factors.hyperlipidemia` vs.
`lipid_interpretations` question raised by M4C was resolved by explicit
human decision (Option B — keep both as distinct variables) and a
follow-up semantic audit confirming compatibility
(`docs/M4C_HYPERLIPIDEMIA_RESOLUTION.md`, `docs/DECISIONS.md` D014).
No reconciliation was made; disagreement between the two fields is
documented as an expected semantic difference, not an error.

**One open, non-blocking item (M4D, still unresolved after M4E):**
which `lipid_interpretations` definition (NCEP_ATP_III, LAI_2020, both,
or neither) should drive a future `diagnoses.hyperlipidemia` entry is
undecided — deferred rather than resolved unilaterally, since D011
explicitly declined to prefer one definition over the other and this
would silently make that choice. Does not block any current milestone;
`docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md` §3/§11. (M4E confirmed this also
blocks a future statin medication — no treatment-rate evidence exists
for statins either, so this item is not currently urgent, but would
need resolving before either could be added.)

The dyslipidemia evidence conflict M4-0A surfaced
(81.2% NCEP-based vs. 87.3% LAI-based, differing LDL cutoffs) was
resolved 2026-09-26 by architectural decision rather than picking a
winner: continuous LDL/HDL/TG/TC become the primary generated value,
with both (and any future) definitions preserved as separately-tagged
derived interpretations. See `docs/DECISIONS.md` D011 and
`docs/M4_CLINICAL_ARCHITECTURE.md`. Of the narrower items this once
listed as open: `TimelineEvent.reference_id` is now IMPLEMENTED (M5.5,
D017) — the one remaining open item from that list is a patient-level
`birth_date` field (still not added; the LASI-45+ family-history scope
question is covered above as item 2).

Population-target ambiguity: resolved 2026-09-26 — see "Target
Population" above and `docs/DECISIONS.md` D008.

---

# Last Completed Action

M5.5 completed: migrated the full M5 100,000-record baseline from
schema v0.7 to v0.8 (`outputs/m8/100k_patients_v08/`), adding blood
pressure, encounters, and timeline references (`docs/DECISIONS.md`
D017). Piloted on 50 records first (`validation/pilot_50_records/`),
then applied full-scale via `integration/migrate_v07_to_v08.py`. **Full
100,000-record validation: 100,000/100,000 structurally valid
(recomputed), 100,000/100,000 clinically consistent (0 errors),
100,000/100,000 migration-integrity exact matches against the untouched
v0.7 source (0 differences, 0 orphans), 0 duplicate IDs.** 16,297
clinical warnings, all pre-existing/documented, none newly introduced
— dominated by the pre-existing M4B lipid-sampling artefact (9.83% of
records have LDL at the clip floor, 2.28% internally impossible; not
corrected, flagged for a future D011-level decision) and a pre-existing
ECG PTB-XL label gap (6.47%). Source dataset confirmed unmodified.
Dataset frozen: `outputs/m8/dataset_manifest.json`. Full report:
`docs/M8_FULL_DATASET_VALIDATION_REPORT.md`.

Separately, ran a controlled ECG pilot on the inherited per-class GAN:
fixed a measurement bug `docs/syngen-codebase-analysis.md` §12.1 had
flagged (the existing eval compared generated samples to training-fold
data, not held-out data) by re-evaluating the already-generated
synthetic samples against true held-out (fold 9) real data. Held-out KS
statistics are within ±0.008 of the original (leaky) ones across all 5
classes — confirms the model isn't memorizing its training set, though
absolute quality sits at the boundary of "excellent," not comfortably
inside it. Confirmed from the architecture that no patient
demographic/clinical field conditions this GAN (5 independent
generators, one per superclass, no shared weights, no conditioning
vector) and that amplitude calibration remains unconfirmed (pre-existing
gap). **Model selection (M6/M7) is unaffected and remains the open human
checkpoint** — this was an engineering fix to the evaluation
methodology, not a model-selection decision. Full report:
`docs/M8_ECG_HELDOUT_PILOT_REPORT.md`.

Two bugs were found and fixed in the validation tooling itself while
scaling it to 100,000 records (accidental O(n²) directory re-scan;
unbounded memory growth, rewritten as a single streaming pass, confirmed
flat at ~185-205MB regardless of population size — the first full-scale
attempt had been killed by the host for memory pressure). 142/142
project tests passing (104 pre-M5.5 + 38 new), plus 37 pilot-batch
gates. No destructive action taken; `outputs/m5/100k_patients/` (v0.7)
and `outputs/m8/100k_patients_v08/` (v0.8) both exist, independently
verified consistent with each other.

Preceded by M5: generated the project's first 100,000-patient baseline
synthetic population (`outputs/m5/100k_patients/`, seed 42, Schema
v0.7) using the existing, unmodified production pipeline. **0
generation errors, 0 duplicate patient IDs, 100,000/100,000 structurally
valid, 100,000/100,000 clinically consistent (0 errors, 0 warnings).**
23.3 minutes, 71.5 patients/sec (matches M4F's benchmark projection);
355.12 MB (matches M4F's 0.36GB projection almost exactly). Every
statistically-checked variable within expected sampling variation of
its cited target, except the NCEP/LAI composite dyslipidemia rates,
now statistically distinguishable from their headline figures at this
scale — a previously-documented (D013), not-newly-discovered structural
consequence of category-based lipid reconstruction, explicitly not
corrected per this milestone's instruction. Relationship checks
confirmed sex×BMI/sex×smoking present as designed and
hypertension×smoking negligible-effect-size independent as intended.
ECG-ID reuse quantified at scale (17,386 unique IDs, max reuse 17×) —
not solved, recorded as future-decision evidence. **Zero Category-A
bugs, zero behavioral/schema changes, no new datasets, no human
checkpoint.** 103/103 tests unchanged. Full report:
`docs/M5_100K_DATASET_REPORT.md`; manifest:
`outputs/m5/dataset_manifest.json`; session log:
`docs/session_logs/2026-09-27_M5-100k-baseline-generation.md`.

Preceded by M4F (final pre-scale audit,
`docs/M4F_FINAL_CLINICAL_AUDIT.md`)
— full domain matrix, human-decision audit (no new C items; the
hyperlipidemia-diagnosis question remains the only open one),
consistency audit (103/103 tests, fresh 10/100/1,000-patient generation,
0 errors/warnings at all three scales; one borderline statistical
finding investigated and confirmed as sampling variation via an isolated
50,000-draw check, not a defect), 5,000-patient scale benchmark
(71.6 patients/sec, memory flat, 100K estimated ~23 minutes), storage
estimate (3,551 bytes/patient measured, 100K ≈ 0.36 GB), and an ECG
readiness audit (metadata-only architecture extensible without
restructuring; identified existing unused per-superclass GAN checkpoints
as a future candidate; flagged ECG-ID reuse at 100K scale as the one
real, non-blocking concern). **Zero Category-A bugs found. 100K
readiness: READY (conditionally) — no RED item.** No behavioral,
schema, or dataset change; `docs/DECISIONS.md` not updated (no genuine
new decision made). Full session record:
`docs/session_logs/2026-09-27_M4F-final-clinical-audit.md`.

Preceded by M4E (evidence audit confirmed ICMR-NNMS 2017-18 national
treatment-rate cascades SUPPORTED for antihypertensive (14.5%) and
antidiabetic (36.1%) treatment; statin/antiplatelet rates NOT SUPPORTED
(only hospital-registry data found, excluded). Implemented `Medication`
(drug_class ∈ {antihypertensive, antidiabetic} only, never a specific
drug name) via `sample_medication_treatment()` (NNMS-rate Bernoulli) +
`derive_medications()` (deterministic construction referencing
diagnoses). `start_date`/`stop_date` always null; `current_status`
always `"active"`. Schema change (`Medication`, v0.6→v0.7) determined
additive/precedented, recorded as `docs/DECISIONS.md` D016. No human
checkpoint required (checked against every listed STOP trigger, none
applied). Verified 0 differences in demographics/risk_factors/lipid/
diagnoses/medical_history vs. the M4D baseline at n=100 (700/700 exact);
observed treatment rates statistically indistinguishable from cited
rates (binomial p=1.000 both). 103/103 tests passing (25 new). Full
session record: `docs/session_logs/2026-09-27_M4E-medications.md`.

Preceded by M4D (implemented `generation/clinical_history.py`
(`derive_diagnoses()`/`derive_medical_history()`, pure/deterministic);
hypertension/diabetes diagnoses are a 1:1 promotion of already-generated
risk_factors flags; medical_history `chronic_condition` entries
reference those diagnoses; hyperlipidemia's diagnosis deliberately
deferred; Schema v0.5→v0.6, D015). 78/78 tests passing (20 new). Full
session record: `docs/session_logs/2026-09-26_M4D-diagnosis-history.md`.

Preceded by M4C-Hyperlipidemia Resolution (human decision Option B —
keep `risk_factors.hyperlipidemia` and `lipid_interpretations` distinct;
semantic audit PARTIALLY CONFIRMED; D014). Full session record:
`docs/session_logs/2026-09-26_M4C-hyperlipidemia-resolution.md`.

Preceded by M4C (audited the actual generation state across every
clinical field, implemented `validation/clinical_consistency.py`,
validated 10 and 100 patients with 0 errors/warnings, surfaced the
hyperlipidemia/lipid_interpretations inconsistency as a human
checkpoint). 55/55 tests passing (13 new). Full session record:
`docs/session_logs/2026-09-26_M4C-clinical-consistency.md`.

Preceded by M4B (lipid panel + HbA1c generation logic, D013). Full
session record: `docs/session_logs/2026-09-26_M4B-clinical-generation.md`.

Preceded by M4A (implemented the `LipidPanel`/`LipidInterpretation`/`Lab`
schema required by D011, Schema v0.4→v0.5, D012, no generation logic yet).
Full session record: `docs/session_logs/2026-09-26_M4A-clinical-schema-implementation.md`.

Earlier: M4-0B (converted human decisions into formal architecture,
D011), M4-0A (dyslipidemia conflict research, corrected to 87.3%), and
M4-0 (evidence verification). Full chain of prior milestones (M1 through
M3.5) is summarized in the milestone sections above; see
`docs/session_logs/` for each one's full record.

---

# Next Action

M5.5 is complete and the schema-v0.8 dataset (`outputs/m8/
100k_patients_v08/`) is the current authoritative population — resuming
from here needs no repeated work on migration or full-dataset
validation. Two independent, non-blocking threads are available next,
neither requiring the other:

1. **A lipid-sampling decision** (Human Decisions Required, item 1) —
   whether/how to constrain TC/TG/HDL sampling so every panel is
   internally feasible. Safe to action independently of M6/M7.
2. **M6: still awaiting explicit authorization**, unchanged. Candidates
   once authorized: ECG architecture decision (reuse-policy at scale, or
   begin Stage 4 waveform work — the inherited GAN's reported quality is
   now confirmed trustworthy per M5.5's held-out re-evaluation, but its
   no-patient-conditioning and amplitude-calibration gaps are unresolved);
   resolve the hyperlipidemia-diagnosis question; pattern discovery over
   the 100K baseline (Stage 7); model selection (Stage 9, blocked on the
   SSSD-ECG pretrained-weight license — a human with authenticated
   Figshare access). ECG waveform generation, model selection,
   CardioSynth/CardioSync integration, AWS, and 1M-scale generation
   remain explicitly deferred.

---

**M7-0 readiness spike completed (2026-09-27), still no model selected,
no implementation, no schema/code change:** verified SSSD-ECG's
architecture directly from source. New findings: (1) the 44-vs-71
conditioning discrepancy is now resolved with high confidence (not
proven) — the model's conditioning input is architecturally hard-wired
to 71 dimensions (a matmul shape constraint), and the likely source
array is `label_all` (all 71 unfiltered SCP codes), not the 44-code
`label_diag` the prior session assumed; (2) this project's own local
PTB-XL files can already supply that 71-dim vector, no new dataset
needed; (3) a partial, code-verified parameter count (~26.5M, excluding
unvendored S4-kernel internals) grounds a much stronger "8GB VRAM
likely sufficient" conclusion than before; (4) a new open question
surfaced — the model's raw output amplitude convention (physical mV vs.
some other scale) could not be confirmed from the fetched training
code. Pretrained-weight license remains UNKNOWN (unchanged blocker).
Full package: `docs/M7_0_ECG_READINESS_REPORT.md`, `docs/
M7_0_CONDITIONING_AUDIT.md`, `docs/M7_0_ECG_IMPLEMENTATION_CONTRACT.md`,
`docs/session_logs/2026-09-27_M7-0-ecg-readiness.md`. 103/103 tests
re-confirmed passing, no code changed. Recommended next step: a human
manually confirms the weight license, then (if permitted) a read-only
checkpoint load to confirm the conditioning shape and get a real
parameter count.

# Last Updated

2026-11-12 (latest, -jatin) — v0.10 open questions 4–7 researched
(`docs/OPEN_QUESTIONS_4-7_EVIDENCE-jatin.md`). **No generator change.**
- Q4: the onset skew is a model assumption, so a new source would not fix it.
- Q5: needs the LASI India Report PDF (download not yet approved).
- Q6: no Indian lipid correlation matrix exists.
- Q7: no undiagnosed-HbA1c distribution; LASI 45.7% control kept as a cross-check.
- **New key finding:** hypertension and diabetes flags are flat with age (HTN
  ~35% at 20–34 and at 70+, vs LASI 47–60% at 70+), because of D006's
  unconditioned marginals. Age × sex conditioning, calibrated to the INDIAB-17
  marginals, awaits a user decision.

2026-11-12 (latest, -jatin) — Schema v0.12 plus three human decisions:
- **D024:** the LAI_2020 interpretation now carries a rule-based risk tier and
  LDL goal, computed from modelled factors only and enforced by the validator.
  On 5,000 seeds: low 30.8 / moderate 33.9 / high 27.1 / very high 8.2%, and 0
  other fields changed.
- **D025:** TG > 400 panels stay rejected.
- **D026:** the pilot is rebuilt at v0.12 (`validation/pilot_50_records/rebuild_v012.py`
  + `tests/test_pilot_v012.py`), and heavy work runs on AWS
  (`docs/AWS_RUN_PLAN-jatin.md`: 1 CPU instance, ~3 h, estimated under US$5;
  **not launched**).
- Samples: `review_samples_v012/`, all 5 valid.
- Tests: `tests/test_v012_lai_risk.py` 12/12 passed locally (no PTB-XL needed).
  The rest of the suite still needs PTB-XL and has not run since D023.
- Open: v0.10 questions 4–7 (evidence searches).
- Next action: go-ahead to launch the AWS phase-1 instance (tests → pilot →
  10…10K → approve 100K).

2026-11-12 (latest, -jatin) — Schema v0.11 (D023, human-approved): D014 reversed.
`risk_factors.hyperlipidemia` is now derived from the patient's own panel
(NCEP_ATP_III dyslipidemia), with a hard validator rule. A placeholder draw
keeps every other field byte-identical to v0.10 (verified on 5,000 seeds:
0 non-flag differences, flag == NCEP 5,000/5,000, prevalence 80.86%, 30.96% of
flags changed). The 5 review samples were re-derived into `review_samples_v011/`
(only PAT_000095 changed, true → false; all 5 valid, 0 warnings).
**Unverified:** the pytest suite was NOT run. This machine lacks the PTB-XL
CSVs (gitignored) and Windows Application Control blocks a pandas DLL, so
`build_patient()` cannot run here. Tests changed: 3 schema-version asserts,
the 4 D014 tests in `test_m4c_clinical_consistency.py` were replaced with 4
D023 tests, and 2 related tests (m4d/m4e) were renamed. Next action: run
`pytest tests` on a machine with PTB-XL; open v0.10 questions 2–4 remain; then
approve a v0.11 100K regeneration (~2 h). Frozen dataset still v0.9.

2026-11-12 (later) — Schema v0.10 (D022) implemented from the external
review: joint lipid model with no LDL clamp, HbA1c for diabetics, BP
SBP-trend extrapolation with confidence flag, modeled onset ages. 187/187
tests; 5,000-record cohort checks in `docs/V010_CHANGE_REPORT.md`. The
frozen dataset is still v0.9 (`outputs/m9/100k_patients_v09/`). Next
action: human decisions on the report's open questions (esp. D014
hyperlipidemia derivation), then approve a v0.10 100K regeneration (~2 h).

2026-11-12 — Pre-ECG patient layer CONFIRMED COMPLETE: D019 + D020 + D021
are all in the frozen v0.9 dataset (`outputs/m9/100k_patients_v09/`,
100,000 records, 0 errors, checksum `53fcae20…d1e`, generated 2026-11-10).
Re-verified today: 100,000 files on disk, 174/174 tests in `tests/` pass.
`validation/pilot_50_records/` tests (5) fail because that pilot is still v0.8;
it is a stale side artifact, not a dataset defect. Next action: the ECG
discussion (weights licence + M6 model decision).

2026-10-30 — M9 (in progress): full-scale field-completeness audit run
for the first time (0 defects found); D019 lipid-sampling reject-and-
redraw fix implemented and verified (not yet applied to the frozen
dataset); family-history and AQI deep-evidence research completed and
written up as two standalone, not-yet-implemented strategy plans
(`docs/Family_history_Strategy_plan.txt`,
`docs/Further_Steps_for_patient-Record_complete.txt`). Next action:
get sign-off on both plans, then bundle them with D019 into one
dataset re-freeze rather than three. ECG/M6/M7 untouched, per the
standing patient-record-completion gate.

Preceded by (2026-10-20) — M5.5 completed: schema v0.7 → v0.8 migration (blood
pressure, encounters, timeline references) applied and validated at
full 100,000-record scale, 0 structural/clinical errors, 100,000/100,000
migration-integrity exact matches; dataset frozen at `outputs/m8/
100k_patients_v08/`. ECG held-out re-evaluation pilot completed
(engineering fix to a measurement bug, not a model-selection decision —
M6/M7 checkpoints unchanged). Five new open items recorded under Human
Decisions Required. See `docs/M8_FULL_DATASET_VALIDATION_REPORT.md`,
`docs/M8_ECG_HELDOUT_PILOT_REPORT.md`, `docs/DECISIONS.md` D017.

Preceded by (2026-09-27) — M7-0 readiness spike completed; model
selection and pretrained-weight license both remain open human
checkpoints. See also: M6 decision package assembled
(`docs/M6_ECG_MODEL_SELECTION.md`, `docs/M7_ECG_IMPLEMENTATION_PLAN.md`);
M5 completed (100K baseline synthetic population generated and fully
validated; 0 errors).
