# Session Log — 2026-09-26 — M3.5: Candidate Improvements + Clinical Layer Design

**Milestone hit:** M3.5 — Candidate Improvements + Clinical Layer Design
(COMPLETE).

## 1. Objective

Two parts: (1) independently audit M3's four candidate generator
improvements and implement only what's justified; (2) design (not
implement) the clinical-record layer so M4 can build on a stable
foundation.

## 2. Candidate Improvement Audit

Investigated each by reading the actual implementation, not just M3's
summary, per instructions. Full detail: `docs/M3_5_CANDIDATE_IMPROVEMENTS.md`.

1. **Urban/rural BMI — DEFERRED.** Re-reading the actual NNMS evidence
   (not just M3's characterization) found the sex-conditional and
   urban/rural-conditional BMI figures come from the same national paper
   but as **two separate 2-way breakdowns, not one joint table**. No
   evidence-supported way exists to combine them for a specific (sex,
   urban_rural) pair without inventing a combination method. This
   contradicts M3's initial "low-effort, high-confidence" framing — the
   deeper investigation this milestone required surfaced a real
   methodological snag. Recorded in `docs/DECISIONS.md` D010.
2. **ECG-ID reuse — DEFERRED to Stage 4.** `ecg_id` is confirmed to be
   purely an inherited PTB-XL source-record identifier (D003), not a
   synthetic-ECG identifier. Whether reuse across patients is
   "legitimate" depends on a Stage 4 design decision (how ECG signals
   will eventually be produced) that hasn't been made. Changing the
   sampling scheme now would also be a real architecture change
   (stateful vs. today's clean per-patient-independent determinism), not
   a small tweak. Recorded in D010.
3. **I/O performance — IMPLEMENTED.** Profiled before touching anything
   (`integration/profile_generation.py`) and found M3's "I/O-bound"
   characterization was imprecise: the actual bottleneck is **CPU-bound**
   — `build_label_map()`'s `ast.literal_eval` parsing of ~21,837
   `scp_codes` values, measured at ~4.9s/call, was running fresh for
   every single patient (plus 3 more redundant CSV reads/patient). Fixed
   with process-level caching (`functools.lru_cache`) in
   `ingestion/ptbxl_source.py` — a pure performance change verified to
   alter zero generated content. Recorded in D009.
4. **State boundaries — PRESERVED, not changed.** No current-boundary
   Census-quality source exists; changing without one would reduce, not
   improve, fidelity to the cited Census 2011 source. No new dataset
   introduced, per this milestone's restriction. Recorded in D010.

## 3. I/O Performance — Measurement Detail

| Metric | Before | After |
|---|---|---|
| `build_label_map()` single call | 4.90s | 4.78s (unchanged — only called once per process now, not per patient) |
| Raw `pd.read_csv` single call | 0.26s | — |
| 1,000-patient generation (measured this session) | ~40 min (reproduced) | **20.4s** |
| Full test suite | 265s | **11s** |
| Projected 100,000-patient generation | ~67 hours | minutes |

**Verification:** regenerated the full 1,000-patient population
(`outputs/m3_5/1000_patients/`) with the fix and diffed against M3's
original (`outputs/m3/1000_patients/`) — **0 differences in demographics
or risk_factors, 0 real ECG content differences** (only the pre-existing,
already-documented ECG-superclass-ordering noise from Python's `set()`
iteration, unrelated to this change). Added
`tests/test_ingestion_caching.py` (4 new tests) confirming the cache
correctly distinguishes different `scp_threshold` values rather than just
trusting the implementation worked.

## 4. Clinical Record Design

Full document: `docs/CLINICAL_RECORD_DESIGN.md` (sections A-J, per this
milestone's required structure). Headline decisions/findings:

- **Generation order** extends the existing identity→demographics→
  risk-factors sequence with family history→medical history/diagnoses→
  medications→labs→investigations→timeline, justified by what
  legitimately depends on what.
- **Key design principle:** diagnoses for hypertension/diabetes/
  hyperlipidemia should be **derived from** the already-generated
  risk-factor booleans, not independently re-generated — avoiding the
  "two independently-random, inconsistent representations of the same
  fact" problem this project has already guarded against once (D004).
- **Family history:** at most one field (diabetes family history,
  boolean) could ever be evidence-supported, and only after locating the
  actual INDIAB percentage (not yet done) — everything else (CVD family
  history, relation, age of onset) has no evidence and must stay
  unpopulated.
- **Medications:** the entire diagnosis→drug-class→medication→dates
  chain requires evidence this project has never researched — flagged in
  full, no assumptions made even where "medically obvious."
- **Labs:** glucose/lipid values proposed, tied to diagnosis status via
  an engineering coherence rule (not new evidence); reference ranges
  explicitly not invented.
- **Timeline:** should reference other records by ID, not duplicate
  content — requires a small additive `TimelineEvent.reference_id`
  schema field (not made now).
- **Provenance:** recommends extending the informal A-E evidence-tier
  discipline already used in `configs/indian_population.yaml` since M2D
  to per-field patient provenance, not just population config.
- **An unresolved design tension surfaced**, not present in M3's own
  findings: height_cm/weight_kg vs. BMI — which should be primary
  evidence and which derived is genuinely unresolved and needs either new
  research or an explicit engineering-assumption decision at M4.

## 5. Model-Readiness Requirements

Documented in `docs/CLINICAL_RECORD_DESIGN.md`'s Step 8 discussion
(folded into the design document rather than a separate file, since it's
short and directly informs the schema-readiness review below): stable
versioned schema (already practiced), consistent controlled vocabularies
(already practiced via `SMOKING_STATUSES`-style constants), documented
missing-value conventions (`None` with a reason, already practiced),
consistent temporal representation, explicit units on every numeric
value, ID-based modality references, machine-readable provenance tiers,
and synthetic-patient-level (not record-level) train/val/test separation
once this population needs its own split. No model selected or
integrated, per instructions.

## 6. Schema Readiness

| Field | Classification |
|---|---|
| `patient_id` | READY |
| `demographics` (age/sex/state/urban_rural) | READY |
| `demographics.height_cm/weight_kg` | NOT YET IMPLEMENTED |
| `risk_factors` | READY |
| `family_history` | NEEDS FUTURE REDESIGN |
| `medical_history` | NEEDS FUTURE REDESIGN |
| `diagnoses` | NEEDS FUTURE REDESIGN |
| `medications` | NEEDS FUTURE REDESIGN (blocked on evidence too) |
| `labs` | NEEDS FUTURE REDESIGN |
| `ecg` | READY |
| `echo` | NOT YET IMPLEMENTED |
| `clinical_timeline` | NEEDS MINOR EXTENSION (`reference_id`) |
| `provenance` | NEEDS MINOR EXTENSION (per-field tiering, optional) |

**No schema change made in this milestone** — all of the above is
classification only, per Step 9's explicit instruction.

## 7. M4 Plan

Full document: `docs/M4_CLINICAL_GENERATION_PLAN.md`. Adjusted from the
illustrative M4A-M4G template: added **M4-0 (evidence verification)**
ahead of everything else, since the design phase found several components
(family history detail, medications, lab reference ranges) are blocked on
evidence gaps that should be resolved (or confirmed unresolvable) before
writing generation code that would otherwise sit idle. Every stage lists
its own human-checkpoint requirement explicitly; M4D (medications) is
flagged as needing sign-off **regardless of outcome**, not just if a gap
is found, since it's a new category of clinical assumption (prescribing
behavior) this project hasn't made before.

## 8. Tests

- **Baseline** (before any change): 16/16 passing, 265.42s.
- **After the I/O fix + new caching tests**: **20/20 passing, 11.07s.**
- No test was weakened or removed to make this pass — 4 new tests added,
  0 changed, 0 deleted.

## 9. Files Created/Modified

**Created:** `docs/M3_5_CANDIDATE_IMPROVEMENTS.md`,
`docs/CLINICAL_RECORD_DESIGN.md`, `docs/M4_CLINICAL_GENERATION_PLAN.md`,
this session log, `integration/profile_generation.py`,
`tests/test_ingestion_caching.py`.
**Modified (behavioral):** `ingestion/ptbxl_source.py` (caching only,
verified zero content change).
**Modified (documentation):** `docs/DECISIONS.md` (D009, D010),
`docs/PROJECT_STATE.md`.
**Not modified:** `schemas/patient_schema.py`, `generation/`,
`configs/indian_population.yaml`'s distribution values, `validation/` —
no schema or generation-content change occurred this session.

## 10. Remaining Limitations

All limitations carried forward from M2C/M2D/M3 remain (age's uniform
engineering default, BMI/smoking's NNMS 18-69 extrapolation,
unconditioned HTN/diabetes/lipid marginals, 2011 state/UT boundaries,
PTB-XL/German ECG source, family history unpopulated). Newly identified,
not newly created: the urban/rural-BMI combination-methodology gap, the
ECG-ID reuse policy gap (now explicitly deferred to Stage 4 rather than
implicitly present), and the height/weight-vs-BMI design tension.

## 11. Human Checkpoints Encountered

Per Step 13's list, none of the hard STOP conditions were triggered mid-
session (no target-population change, no new dataset, no ECG-identifier-
semantics change, no unsupported clinical assumption, no material schema
change, no new disease prevalence, no model introduction, no 10K/100K
generation). However, this milestone's own design work identified several
items that **will** need explicit human sign-off before M4 proceeds past
them — listed individually in `docs/M4_CLINICAL_GENERATION_PLAN.md` per
stage (most notably M4A/M4B/M4E's schema additions, and M4D's blanket
sign-off requirement for medications regardless of evidence outcome).

## 12. Recommendation

M4 should begin with M4-0 (evidence verification) rather than jumping to
implementation, exactly because this design phase found more evidence
gaps than M3's summary-level pass suggested. The I/O fix removes what was
the single largest practical blocker to eventually scaling — this
project can now consider larger validation runs (still following
progressive scaling, still not jumping to 10K/100K) without a
multi-hour wait dominating the session.
