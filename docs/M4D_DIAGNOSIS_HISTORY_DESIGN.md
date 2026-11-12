# M4D — Diagnoses + Medical History Design

**Status:** COMPLETE (2026-09-26).

## 0. Current-state audit (before writing code)

Read the actual code, not the milestone prompt's assumed shape.

**What the prompt assumed exists** (its own Phase 5 illustration):
```text
diagnoses[code, diagnosed_date]
medical_history[category, description, event_date]
```

**What actually existed** (`schemas/patient_schema.py`, pre-M4D):
```python
diagnoses: Optional[list[Any]] = None       # not yet implemented — Stage 3
medical_history: Optional[dict[str, Any]] = None  # not yet implemented — Stage 3
```
`diagnoses` was an untyped list-of-`Any` placeholder; `medical_history`
was, unexpectedly, an untyped **dict** (not a list at all) — a
different container shape than either the prompt's illustration or
`docs/CLINICAL_RECORD_DESIGN.md` §D's own proposed list-of-categorized-
entries shape. Both were `None` for every patient generated so far
(M1-M4C). Confirmed by direct inspection, not by trusting any prior
milestone's description — exactly this audit's own instruction.

A full repo-wide grep for `diagnosis`/`medical_history`/`cv_event`/
`chronic_condition`/`diagnosed_date`/`event_date` found the real design
work already sitting in `docs/CLINICAL_RECORD_DESIGN.md` §D/§E (M3.5)
and `docs/M4_CLINICAL_EVIDENCE.md` §2/§3/§7 (M4-0) — this milestone
implements those, not a new design.

## 1. Evidence used

From `docs/M4_CLINICAL_EVIDENCE.md` (M4-0, already collected, no new
research performed):

| Candidate | Source | Population | Status |
|---|---|---|---|
| Hypertension diagnosis | ICMR-INDIAB-17 (already generated as `risk_factors.hypertension`) | 113,043 adults 20+ | **SUPPORTED** — 1:1 promotion of existing evidence-backed flag |
| Diabetes diagnosis | ICMR-INDIAB-17 (already generated as `risk_factors.diabetes`) | 113,043 adults 20+ | **SUPPORTED** — same |
| Hyperlipidemia diagnosis | `risk_factors.hyperlipidemia` (population marginal) OR `lipid_interpretations` (measurement-derived) | — | **DEFERRED** — see §3 |
| Stroke | Systematic review, heterogeneous studies, 26-757/100,000 range | Varies | **NOT SUPPORTED** for individual-record generation — range too wide |
| Heart failure | Modeled estimate, not measured | National | **NOT SUPPORTED** — modeled, not surveyed |
| General CVD | Meta-analysis of 15 heterogeneous studies, ~11% pooled | National | **NOT SUPPORTED** — definitions vary across underlying studies |
| Cardiac procedures | None found | — | **NOT SUPPORTED** |
| Diagnosis onset date | None found | — | **NOT SUPPORTED** — only population rates by age band exist (LASI, 45+ only), never a per-patient onset distribution |

No new epidemiological numbers were located or invented in this
milestone — everything above restates M4-0's existing findings.

## 2. Supported diagnoses

**Hypertension, diabetes.** Both already exist as evidence-backed
`risk_factors` booleans (ICMR-INDIAB-17 national marginals). Promoting
them into `Diagnosis` entries adds no new prevalence claim — it is a
lossless reformat of already-generated data, per
`docs/CLINICAL_RECORD_DESIGN.md` §E's explicit design ("a 1:1 promotion,
not new prevalence").

## 3. Unsupported / deferred diagnoses

- **Hyperlipidemia.** Deferred, not merely unsupported by evidence —
  the evidence for the underlying *presence* of dyslipidemia is fine
  (that's what M4B/M4C already generate two ways). The block is
  architectural: `docs/PROJECT_STATE.md`'s M4D placeholder (written at
  the end of the M4C-Hyperlipidemia-Resolution milestone) already
  committed to sourcing the future `diagnoses.hyperlipidemia` entry from
  `lipid_interpretations` (the measurement-derived chain), not from
  `risk_factors.hyperlipidemia` — following
  `docs/M4_CLINICAL_ARCHITECTURE.md`'s original two-hop-chain design.
  But `lipid_interpretations` holds **two** coexisting, sometimes-
  disagreeing definitions (NCEP_ATP_III, LAI_2020) by deliberate human
  decision (D011) — no single one was ever declared canonical.
  Collapsing them into one boolean diagnosis would silently make exactly
  the choice D011 declined to make. This is "a choice between
  incompatible clinical interpretations," one of this milestone's own
  named STOP conditions. **Deferred, not implemented**, rather than
  resolved unilaterally. See §11 for what a future milestone needs to
  decide.
- **Stroke, heart failure, general CVD, cardiac procedures.** Deferred —
  no population-representative, sufficiently-precise source exists
  (§1). Not generated.
- **Any diagnosis onset date.** Deferred — see §7.

## 4. Risk-factor vs. diagnosis semantics

```text
risk_factors.hypertension          risk_factors.diabetes
    =                                   =
population/background                population/background
risk-factor state                    risk-factor state
    ↓ (1:1 promotion, D015)              ↓ (1:1 promotion, D015)
diagnoses["hypertension"]           diagnoses["diabetes"]
    =                                   =
synthetic patient's                  synthetic patient's
represented diagnosis                represented diagnosis
```

Not every risk factor automatically becomes a diagnosis — this was
evaluated per-field, not assumed. `bmi`/`smoking_status` have no
diagnosis-shaped analogue in the existing evidence or design (they are
continuous/categorical *behavioral or anthropometric* attributes, not
conditions); `hyperlipidemia` is deliberately excluded per §3.

This is the *same* semantic distinction already established by D014
for hyperlipidemia (population attribute vs. patient-level
representation) — hypertension/diabetes simply have a *direct*,
uncontested 1:1 relationship where hyperlipidemia does not, because
only hyperlipidemia has a second, independently-evidenced
measurement pathway (`lipid_panel`/`lipid_interpretations`) that could
disagree with it.

## 5. Diagnosis-generation dependency

```text
risk_factors (already generated)
        ↓
generation/clinical_history.derive_diagnoses()   -- pure, deterministic, no RNG
        ↓
Patient.diagnoses
```

`derive_diagnoses()` never samples — it reads the already-generated
`hypertension`/`diabetes` booleans and promotes each `True` value into
one `Diagnosis` entry. No independent re-roll, per
`docs/CLINICAL_RECORD_DESIGN.md` §D's explicit warning against
"two separately-random, potentially-inconsistent representations of
the same fact" (the exact failure mode D004 first flagged, and the one
M4C's audit found actually happened for hyperlipidemia/
lipid_interpretations — not repeated here).

## 6. Medical-history dependency

```text
Patient.diagnoses (already generated, above)
        ↓
generation/clinical_history.derive_medical_history()   -- pure, references diagnosis_id
        ↓
Patient.medical_history
```

Each `MedicalHistoryEntry` is `category="chronic_condition"`,
`description=<diagnosis code>`, `diagnosis_id=<the Diagnosis it
references>`, `event_date=<mirrors diagnosed_date>`. This is a
**reference**, not a second generator — `medical_history` is never
computed from `risk_factors` directly, only from the already-derived
`diagnoses` list, so the two can never disagree by construction (unlike
the hyperlipidemia/lipid_interpretations pair, which disagree by
construction because they come from two independent evidence sources).

`cv_event` and `procedure` categories are **never generated** this
milestone — deferred per §3. `diagnosis` (as a medical_history
category, distinct from the `Diagnosis` dataclass) is also not
generated — `chronic_condition` is the only category populated,
matching `docs/CLINICAL_RECORD_DESIGN.md` §D's own table entry for
hypertension/diabetes.

## 7. Temporal / date strategy

**Chose Option A: `diagnosed_date = None` always.**

`docs/M4_CLINICAL_EVIDENCE.md` §7 is explicit: "What remains
necessarily engineering-derived: any specific `onset_date` value for an
individual generated patient (no source gives a per-patient onset
distribution, only population rates by band)." Even the one real
temporal evidence found (LASI's age-band diagnosis-rate peaks) is
scoped to ages 45+ and gives a *rate*, not an *onset-date distribution*
— there is no defensible way to sample a specific date from it. Per
this milestone's own instruction ("Prefer A unless existing
architecture/evidence gives us a defensible reason to use B"), no such
reason exists. `diagnosed_date` stays `None` for every patient,
consistent with `labs.measured_at` being the only date-bearing field
this project currently populates from a real timestamp (generation
time, not a clinical event time) and with `family_history` remaining
`null` under the same "don't invent" discipline (D004).

`Diagnosis.diagnosed_date` and `MedicalHistoryEntry.event_date` remain
in the schema (not removed) so a future milestone with genuine
age-of-onset evidence has somewhere to write to, matching this
project's existing pattern (e.g. `height_cm`/`weight_kg` existing,
unpopulated, since M1).

## 8. Missingness strategy

- `diagnoses`: always a list (never `None`) — the generation layer runs
  for every patient; an empty list (`[]`) means "ran, found zero
  qualifying risk factors," distinct from `None` ("not implemented"),
  matching `lipid_interpretations`' existing convention of always being
  a populated container once its generation layer exists.
- `medical_history`: same — always a list, `[]` when `diagnoses` is
  empty, since it is purely a reference view over `diagnoses`.
- `diagnosed_date`/`event_date`: always `None` (§7) — not missingness
  in the "evidence exists but wasn't generated" sense, but a
  permanent, documented architectural choice for this milestone.

## 9. Schema review and decision

**Determination: a schema change was genuinely required**, but it is
additive, backward-compatible, and directly implements this milestone's
own explicit deliverable — not a "significant restructuring" in the
sense `CLAUDE.md` §28 reserves for a mandatory human checkpoint. It
follows the exact precedent of D006 (`RiskFactors` formalization) and
D012 (`LipidPanel`/`LipidInterpretation`/`Lab`), both of which retyped
an untyped placeholder field into a real dataclass and proceeded
autonomously, recording only a decision-log entry.

**What changed** (`schemas/patient_schema.py`, `SCHEMA_VERSION`
`0.5` → `0.6`):
- New `Diagnosis` dataclass: `diagnosis_id`, `code`, `diagnosed_date`
  (default `None`), `source` (default `"derived_from_risk_factors"`).
- New `MedicalHistoryEntry` dataclass: `category`, `description`,
  `diagnosis_id`, `event_date`.
- New controlled vocabularies: `DIAGNOSIS_CODES = {"hypertension",
  "diabetes"}`, `MEDICAL_HISTORY_CATEGORIES = {"diagnosis", "cv_event",
  "procedure", "chronic_condition"}` (the last is a 4-entry future-proof
  vocabulary per `docs/CLINICAL_RECORD_DESIGN.md` §D's proposed
  categories — only `chronic_condition` is ever produced today).
- `Patient.diagnoses`: `Optional[list[Any]]` → `Optional[list[Diagnosis]]`.
- `Patient.medical_history`: `Optional[dict[str, Any]]` →
  `Optional[list[MedicalHistoryEntry]]` — a container-shape change
  (dict → list), not just a type narrowing, but harmless: the field was
  `None` for every patient ever generated (M1-M4C), so no existing data
  or code path depended on the old dict shape.

No other schema field changed. Recorded as `docs/DECISIONS.md` D015.

## 10. Validation rules

`validation/structural.py` (schema-level, unchanged pattern):
- `diagnoses[i].code` must be in `DIAGNOSIS_CODES`.
- `medical_history[i].category` must be in `MEDICAL_HISTORY_CATEGORIES`.

`validation/clinical_consistency.py` (cross-field, new checks):
- `diagnosis_risk_factor_consistency` (hard rule): recomputes expected
  diagnosis codes from `risk_factors` via `derive_diagnoses()` and
  compares exactly; also asserts no code outside `DIAGNOSIS_CODES`
  appears (defense-in-depth beyond structural).
- `medical_history_diagnosis_consistency` (hard rule): recomputes
  expected `medical_history` from `diagnoses` via
  `derive_medical_history()` and compares exactly; separately checks
  every entry's category is `chronic_condition` and every
  `diagnosis_id` reference resolves to a real diagnosis on the same
  patient (no orphans).
- Existing checks (`lipid_panel_interpretation_consistency`,
  `diabetes_hba1c_consistency`, `hba1c_plausibility_given_age_sex`,
  `hyperlipidemia_vs_lipid_interpretations_intentionally_not_compared`,
  `timeline_labs_date_consistency`) are **unchanged** — verified by the
  full M4B/M4C regression suite still passing.
- `unimplemented_domains_confirmed_absent` narrowed to
  `family_history`/`medications`/`encounters`/`echo` — `diagnoses`/
  `medical_history` removed from this list since they are now
  implemented.

This validator never assumes `risk_factor == diagnosis` as a general
rule — it recomputes the *specific*, evidence-justified relationship
(`derive_diagnoses`) rather than a blanket equality check, so adding a
future risk factor with no diagnosis relationship would not need a
validator change.

## 11. Known limitations

- Hyperlipidemia's diagnosis remains unimplemented pending a human
  decision on which `lipid_interpretations` definition (NCEP_ATP_III,
  LAI_2020, both as separate entries, or neither) should drive it —
  not blocking this milestone, but blocking any future one that wants
  a complete three-condition diagnosis set.
- `diagnosed_date`/`event_date` are permanently `None` under current
  evidence — any future population/pattern analysis must not treat
  their absence as informative missingness.
- Stroke/heart-failure/general-CVD/procedures remain entirely
  unrepresented, per M4-0's evidence findings — this project's general
  population target (D008) is not a CVD-specific cohort, and no
  evidence exists at the precision needed to generate individual
  records for these conditions responsibly.
- A pre-existing, unrelated non-determinism was observed while
  regression-testing (not introduced by this milestone): `ecg.
  superclasses` list *order* (not content) can differ between separate
  process runs at the same seed, traced to a `set()`→`list()` conversion
  in the reused `syngen/SynGen/SynGen/gan_pytorch.py:55-61`
  (`build_label_map()`), whose iteration order depends on Python's
  per-process hash seed. Out of scope to fix here (refactoring
  unrelated, working, reused code); noted for a future milestone if
  ECG-order-sensitive comparisons are ever needed.

## 12. Future dependencies for medications/timeline

- **Medications**: per `docs/CLINICAL_RECORD_DESIGN.md` §F, the
  dependency chain is `diagnosis → drug class → medication → start/stop
  dates`. `Patient.diagnoses` now exists and is real, so the first link
  in that chain is ready; drug-class evidence (NLEM 2022) remains only
  partially extracted (`docs/M4_CLINICAL_EVIDENCE.md` §4) — still
  blocked on evidence, not on schema.
- **Timeline/encounters**: `docs/CLINICAL_RECORD_DESIGN.md` §H proposes
  a future `TimelineEvent.reference_id` field so timeline entries could
  point at a `diagnosis_id` — not added in this milestone (a distinct,
  already-flagged, not-yet-approved schema question, unchanged by
  M4D).
