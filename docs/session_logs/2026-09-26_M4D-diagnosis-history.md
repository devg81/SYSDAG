# Session Log — 2026-09-26 — M4D: Diagnoses + Medical History Generation

**Milestone hit:** M4D, COMPLETE.

## Objective

Build the next foundational clinical-record layer — `diagnoses` and
`medical_history` — deriving from already-generated risk factors rather
than independently resampling, per the dependency direction:
demographics → risk factors → clinical diagnoses → medical history.

## Phase 0 — Current-state audit

Read the actual code before trusting the milestone prompt's own
illustration (`diagnoses[code, diagnosed_date]`,
`medical_history[category, description, event_date]`). Found the real
state differed: `Patient.diagnoses` was `Optional[list[Any]]` and
`Patient.medical_history` was, unexpectedly, an untyped **dict**, not a
list at all — a different container shape than either the prompt's
illustration or `docs/CLINICAL_RECORD_DESIGN.md` §D's own proposed
shape. Both were `None` for every patient generated so far (M1-M4C).

A repo-wide grep for `diagnosis`/`medical_history`/`cv_event`/
`chronic_condition`/`diagnosed_date`/`event_date` found the real design
already sitting in `docs/CLINICAL_RECORD_DESIGN.md` §D/§E (M3.5) and
`docs/M4_CLINICAL_EVIDENCE.md` §2/§3/§7 (M4-0) — this milestone
implements those, not a new design.

## Phase 1 — Evidence boundary

Restated from `docs/M4_CLINICAL_EVIDENCE.md` (no new research):
hypertension/diabetes diagnoses SUPPORTED (1:1 promotion of already-
generated flags); hyperlipidemia's diagnosis architecturally blocked
(see Phase 2); stroke/heart-failure/general-CVD/procedures NOT
SUPPORTED for individual-record generation (heterogeneous, modeled-not-
measured, or hospital-registry-derived); diagnosis onset dates NOT
SUPPORTED (no per-patient distribution exists).

## Phase 2 — Diagnosis semantics

```text
risk_factors.hypertension/diabetes  (population/background state)
        ↓ 1:1 promotion, D015
diagnoses["hypertension"/"diabetes"]  (patient's represented diagnosis)
```

**Hyperlipidemia's diagnosis deliberately deferred**, not merely
unsupported. `docs/PROJECT_STATE.md`'s own M4D placeholder (written at
the end of the prior M4C-Hyperlipidemia-Resolution milestone) had
already committed to sourcing it from `lipid_interpretations`, not
`risk_factors.hyperlipidemia`. But `lipid_interpretations` holds two
coexisting, sometimes-disagreeing definitions (NCEP_ATP_III, LAI_2020)
by deliberate human decision (D011) — collapsing them into one boolean
would silently make the canonical-definition choice D011 declined to
make. This is exactly this milestone's own "choice between incompatible
clinical interpretations" STOP condition — deferred, not resolved
unilaterally.

## Phase 3 — Temporal design

**Chose Option A: `diagnosed_date = None` always.** No source gives a
per-patient onset-date distribution (`docs/M4_CLINICAL_EVIDENCE.md`
§7); the one real temporal finding (LASI age-band diagnosis-rate
peaks) is scoped to 45+ and gives a rate, not a distribution to sample
from. Consistent with this project's standing "don't invent" discipline
(same precedent as `family_history` staying null, D004).

## Phase 4 — Medical history

Only `chronic_condition` populated, one entry per diagnosis,
**referencing** it by `diagnosis_id` rather than re-deriving from
`risk_factors` — avoids the exact "two separately-random
representations of the same fact" failure mode
`docs/CLINICAL_RECORD_DESIGN.md` §D warns against (the one M4C's audit
found had actually happened for hyperlipidemia/lipid_interpretations).
`cv_event`/`procedure` never generated.

## Phase 5 — Schema review and decision

Determined a schema change was genuinely required (existing containers
couldn't hold structured data at all), but additive/backward-compatible
and directly implementing this milestone's own deliverable — matching
the exact precedent of D006/D012 (retype an untyped placeholder,
proceed autonomously, record the decision), not a "significant
restructuring" requiring a mandatory human checkpoint. Proceeded;
recorded as `docs/DECISIONS.md` D015.

**Schema changes** (`SCHEMA_VERSION` `0.5` → `0.6`):
- New `Diagnosis` dataclass (`diagnosis_id`, `code`, `diagnosed_date`,
  `source`).
- New `MedicalHistoryEntry` dataclass (`category`, `description`,
  `diagnosis_id`, `event_date`).
- New vocabularies `DIAGNOSIS_CODES`, `MEDICAL_HISTORY_CATEGORIES`.
- `Patient.diagnoses`: `list[Any]` → `list[Diagnosis]`.
- `Patient.medical_history`: `dict` → `list[MedicalHistoryEntry]`
  (container-shape change, harmless since always `None` before).

## Phase 6 — Implementation

`generation/clinical_history.py` (new, small, pure/deterministic, no
RNG): `derive_diagnoses(risk_factors, patient_id)`,
`derive_medical_history(diagnoses)`. Wired into
`integration/build_patient.py` after risk_factors generation.
`sample_hyperlipidemia()`, `sample_lipid_panel()`,
`derive_lipid_interpretations()` byte-for-byte unchanged.

## Phase 7 — Validation

`validation/structural.py`: `DIAGNOSIS_CODES`/
`MEDICAL_HISTORY_CATEGORIES` membership checks.
`validation/clinical_consistency.py`: new
`diagnosis_risk_factor_consistency` (hard rule, recomputes from
risk_factors) and `medical_history_diagnosis_consistency` (hard rule,
recomputes from diagnoses, checks for orphan references and
unsupported categories) checks. `unimplemented_domains_confirmed_absent`
narrowed — `diagnoses`/`medical_history` removed (now implemented),
`medications`/`encounters`/`echo`/`family_history` remain. Existing
lipid/HbA1c/hyperlipidemia-semantic checks unchanged and re-verified
passing.

## Phase 8 — Testing

New: `tests/test_m4d_diagnosis_history.py` (20 tests) — pure-function
unit tests, real-pipeline integration tests (hypertensive patients get
the diagnosis, non-hypertensive/non-diabetic patients get none,
hyperlipidemia never promoted, dates always null, medical_history
mirrors diagnoses 1:1), structural-vocabulary rejection tests, clinical-
consistency hard-rule tests (mismatch detection, missing-diagnosis
detection, unsupported-code rejection, orphan-reference detection,
procedure/cv_event category rejection), and explicit regression checks
that demographics/risk_factors/lipids/HbA1c and the D014 hyperlipidemia
semantic distinction remain intact.

Two pre-existing tests became outdated by this milestone's own schema
bump and now-implemented diagnoses field (not regressions — the same
"outdated test expectation" pattern already documented for M4B):
`test_m4a_clinical_schema.py::test_minimal_patient_still_works`
(SCHEMA_VERSION literal `"0.5"` → `"0.6"`) and
`test_m4c_clinical_consistency.py::test_unimplemented_domains_absent_is_not_an_error`
(narrowed to check only `medications`, since `diagnoses` is no longer
unimplemented).

**Full suite: 78/78 passing** (58 existing + 20 new).

## Phase 9 — Real pipeline validation

Generated `outputs/m4d/10_patients/` and `outputs/m4d/100_patients/`
via `integration/generate_population.py` (unchanged orchestration).

- 10/10 and 100/100 structurally valid, clinically consistent, 0
  errors, 0 warnings.
- Regression check against `outputs/m4c/100_patients/`: demographics/
  risk_factors/lipid_panel/lipid_interpretations/labs **byte-identical**
  for all 100 patients (592/600 field comparisons exact; the remaining
  8 were `ecg.superclasses` list-*order* differences only, traced to a
  pre-existing `set()`→`list()` conversion in reused
  `syngen/SynGen/SynGen/gan_pytorch.py`'s `build_label_map()` —
  unrelated to anything changed this milestone, semantic content
  identical).
- Diagnosis counts exactly match risk-factor counts: 34/100
  hypertension diagnoses (34 `risk_factors.hypertension=True`), 9/100
  diabetes diagnoses (9 `risk_factors.diabetes=True`).
- Only `{"hypertension", "diabetes"}` ever appear as diagnosis codes;
  only `{"chronic_condition"}` ever appears as a medical_history
  category — confirmed programmatically, not assumed.

## Phase 10 — Pattern inventory update

`docs/M3_PATTERN_INVENTORY.md` updated: hypertension/diabetes→diagnosis
promotion added to §A (encoded/evidence-backed); medical_history's
reference-not-regenerate mechanism and the newly-observed ECG-order
non-determinism added to §B (mechanical/engineering); stroke/heart-
failure/CVD/procedures and diagnosis onset dates added to §C (not
represented); the hyperlipidemia-diagnosis definition question added
to §D (requiring a decision, not new evidence).

## Problems found

None (category A). The only "problem"-shaped thing surfaced was the
pre-existing `medical_history` dict/list container mismatch (Phase 0)
and the pre-existing `ecg.superclasses` ordering non-determinism
(Phase 9) — both documented, neither a defect introduced this
milestone.

## Human checkpoints

**None required to complete M4D.** One deferred, non-blocking item for
a future milestone: which `lipid_interpretations` definition should
drive `diagnoses.hyperlipidemia` (`docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md`
§3/§11).

## Files Created/Modified

Created: `generation/clinical_history.py`,
`tests/test_m4d_diagnosis_history.py`,
`docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md`, this session log.
Modified: `schemas/patient_schema.py` (Diagnosis, MedicalHistoryEntry,
DIAGNOSIS_CODES, MEDICAL_HISTORY_CATEGORIES, SCHEMA_VERSION 0.5→0.6),
`integration/build_patient.py`, `validation/structural.py`,
`validation/clinical_consistency.py`,
`integration/validate_clinical_population.py`,
`tests/test_m4a_clinical_schema.py` (schema-version literal),
`tests/test_m4c_clinical_consistency.py` (outdated assertion),
`docs/DECISIONS.md` (D015), `docs/PROJECT_STATE.md`,
`docs/M3_PATTERN_INVENTORY.md`.
Not modified: `generation/indian_population.py`,
`configs/indian_population.yaml`, `docs/DECISIONS.md` D011/D014's own
text (append-only convention).

## Recommendation

M4E: resolve the deferred hyperlipidemia-diagnosis question, then
medications (`diagnosis → drug class → medication`, per
`docs/CLINICAL_RECORD_DESIGN.md` §F) — now unblocked on the diagnosis
side, still gated on completing NLEM 2022 drug-class evidence
extraction.
