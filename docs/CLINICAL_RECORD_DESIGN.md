# Clinical Record Design (M3.5)

**Purpose:** design (not implement) how this project transitions from a
"synthetic population generator" (demographics + risk factors, M1-M3) to
a "synthetic longitudinal patient-record generator" (family history,
medical history, diagnoses, medications, labs, ECG, echo, timeline). No
code changes result from this document — it is the blueprint M4 builds
against.

**Governing principle, restated up front:** every dependency proposed
below is classified as **evidence-supported**, **engineering
relationship**, or **future research requirement**. Nothing here invents
medical causality. Where a relationship *sounds* medically obvious but
this project has not located Indian evidence for it, it is marked future
research requirement, not quietly assumed.

---

## A. Patient Generation Order

Proposed sequence, extending the existing (already-implemented) order:

```text
1.  Patient identity (patient_id)                    [DONE — M1]
2.  Demographics (age, sex, state, urban_rural)       [DONE — M2C]
3.  Baseline anthropometrics (height_cm, weight_kg)   [NOT DONE — see tension below]
4.  Risk factors (BMI, smoking, HTN, diabetes,
    hyperlipidemia)                                   [DONE — M2C]
5.  Family history                                    [DESIGN ONLY — §C]
6.  Medical history / diagnoses                       [DESIGN ONLY — §D/§E]
7.  Medications                                        [DESIGN ONLY — §F]
8.  Labs                                               [DESIGN ONLY — §G]
9.  Investigations / ECG / Echo                       [ECG partially DONE — M1; Echo open]
10. Clinical timeline                                  [DESIGN ONLY — §H]
```

**Justification:** identity and demographics must come first because
every other component either directly conditions on them (BMI, smoking —
already true) or *should eventually* (diagnoses, medications). Risk
factors precede diagnoses because, per §E below, diagnoses for
hypertension/diabetes/hyperlipidemia are proposed to be **derived from**
the already-generated risk-factor flags, not independently re-rolled —
they must exist first. Medications and labs follow diagnoses because both
are proposed to depend on *which* diagnoses exist. Clinical timeline is
last because it is a chronological index over already-generated dated
records (§H), not a source of new information.

**Anthropometrics tension (not resolved here):** BMI is currently
generated directly (category from NNMS evidence, then a continuous value
within that category — `configs/indian_population.yaml`
`risk_factors.bmi`). Height/weight are *not* generated. Two future options
exist: (a) keep BMI primary and back-derive a plausible height/weight pair
(would need Indian population height-distribution evidence, not yet
researched, or an engineering assumption disclosed as such), or (b)
research Indian height/weight distributions directly and derive BMI from
them instead (would change which figure is "primary evidence" vs.
"derived"). **This is a design fork requiring either new evidence or an
explicit engineering-assumption decision — flagged for M4 planning, not
resolved in this document.**

---

## B. Dependency Graph

| Dependency | Classification | Notes |
|---|---|---|
| Sex → BMI | **Evidence-supported** | NNMS, already implemented |
| Sex → Smoking status | **Evidence-supported** | NNMS, already implemented |
| Age → Hypertension/Diabetes/Hyperlipidemia | **Future research requirement** | No accessible age-stratified table (M2D-4 audit); do NOT add without one |
| Risk factors (HTN/diabetes/hyperlipidemia) → Diagnoses | **Engineering relationship** | Proposed: promote an existing `True` risk-factor flag into a structured, dated diagnosis record. This is *reformatting already-evidence-backed data*, not inventing new prevalence — but the **onset date** itself would be an engineering assumption (no evidence for *when* onset occurs), and must be labeled as such |
| Family history → Diagnoses | **Future research requirement** | Medically plausible, but no Indian quantitative evidence located in M2A or M2C-0 research — do not add |
| Diagnoses → Medications | **Future research requirement** | No Indian prescribing-pattern/standard-of-care evidence has been researched at all (§F) |
| Diagnoses/Risk factors → Labs | **Partially evidence-supported** | ICMR-INDIAB ties glucose/lipid *measurement* to diabetes/hyperlipidemia diagnostic criteria (already embedded in `configs/indian_population.yaml`'s diabetes/hyperlipidemia `definition` fields) — but generating an actual lab *value* consistent with diagnosis status is an **engineering coherence rule** (e.g., a diabetic patient's generated glucose should exceed the diagnostic threshold), not itself new evidence |
| Diagnoses/Investigations → ECG/Echo reference | **Engineering relationship** | The ECG *signal* itself remains independently PTB-XL-sourced (D003) — a diagnosis doesn't generate a matching signal. Only the *clinical-narrative link* ("ECG ordered as part of hypertension workup") is proposed, at the timeline level, as a reference — not a content dependency |
| Clinical events → Timeline | **Engineering relationship** | The timeline is a chronological view/index over already-generated dated records, referenced by ID (§H), not new information |

**Explicitly not proposed, and why:** BMI/smoking/HTN/diabetes/
hyperlipidemia → Diagnosis-severity or → CVD-event-risk scoring. No
accessible Indian evidence supports a quantitative CVD-risk function
conditioned on these variables (`docs/INDIAN_GENERATION_STRATEGY.md` §5's
"documented multivariable association" tier was never populated with a
citable source). This stays a future research requirement, explicitly
flagged rather than silently assumed away.

---

## C. Family History

**Proposed future structure** (design only, not implemented):

```text
FamilyHistoryEntry:
    relation: str        # e.g. "mother", "father", "sibling"
    condition: str        # e.g. "diabetes", "cvd", "hypertension"
    age_of_onset: Optional[int]
```

**What can safely be generated using existing evidence:** ICMR-INDIAB
captures a *family history of Type 2 diabetes* variable (yes/no) —
confirmed captured in the source, but this project's own research
(M2A, M2C-0) never located the **actual prevalence percentage** for it.
Before generating even a simple boolean `family_history_of_diabetes`
marginal, that specific number must be located and cited — not assumed.

**What requires future evidence, and must not be populated now:**
- Family history of CVD specifically — **confirmed absent** from every
  dataset examined across M2A and M2C-0 (`docs/DECISIONS.md` D004).
- Relation-specific breakdown (mother vs. father vs. sibling) — no source
  found.
- Age of onset — no source found.
- Any condition other than diabetes — no source found.

**Conclusion:** the `FamilyHistoryEntry` structure above is a reasonable
future shape, but at most one field (`condition="diabetes"`, boolean
presence only, no relation/age-of-onset detail) could ever be populated
from currently-known evidence, and only after locating the actual INDIAB
percentage. Everything else stays `null`/absent, per this project's
standing rule against filling fields with unsupported distributions.

---

## D. Medical History

**Proposed categories:** diagnosis, cardiovascular event, procedure,
chronic condition.

**Design principle — avoid duplicate independent generation.** Currently,
`risk_factors.hypertension/diabetes/hyperlipidemia` are the *only*
evidence-backed presence/absence flags this project has. `medical_history`
must not independently re-roll "does this patient have hypertension" —
that would create two separately-random, potentially-inconsistent
representations of the same fact, exactly what `CLAUDE.md` §9 and
`docs/DECISIONS.md` D004 already warn against for a different pair of
fields.

| Category | Source | Generation approach |
|---|---|---|
| Chronic condition | `risk_factors` (existing) | **Derived** — mirror the already-generated boolean flags, not re-generated |
| Diagnosis | `risk_factors` (existing) → promoted, or new categories | **Derived** for HTN/diabetes/hyperlipidemia (see §E); **future research requirement** for anything else |
| Cardiovascular event (MI, stroke, etc.) | None currently | **Future research requirement** — M2A found CREATE/STEMI-ACT (the only Indian clinical-event sources) practically inaccessible and not population-representative even where accessible |
| Procedure (angioplasty, bypass, etc.) | None currently | **Future research requirement** — no source researched at all |

---

## E. Diagnoses

**Relationship to other components:**
- **Risk factors:** the three existing boolean risk factors
  (hypertension, diabetes, hyperlipidemia) are proposed as the direct
  source for three corresponding diagnosis entries — a 1:1 promotion, not
  new prevalence. **Do not invent additional disease-prevalence numbers**
  (e.g., a specific "myocardial infarction" diagnosis rate) — none is
  currently evidence-backed at usable granularity (M2A's CREATE data is
  a dated, non-representative hospital cohort, not a population rate).
- **Medical history:** diagnoses and medical-history "chronic condition"
  entries should reference the *same* underlying fact, not duplicate it
  (see §D).
- **Medications:** proposed to depend on which diagnoses exist (§F) —
  not yet implementable, evidence gap.
- **Labs:** proposed coherence relationship (§G) — a diabetes diagnosis
  should correspond to a generated glucose value above the diagnostic
  threshold already embedded in the config.
- **ECG/Echo:** no content dependency (ECG remains independently sourced,
  D003); only a narrative timeline reference is proposed (§H).

**Proposed future structure:**

```text
Diagnosis:
    diagnosis_id: str        # e.g. "PAT_000001_DX01"
    code: str                 # condition name; ICD-coding is a future decision, not made here
    onset_date: str            # engineering-assumption date, not evidence-derived (see §A anthropometrics-style caveat)
    source: str                # "derived_from_risk_factors" | future values as new evidence arrives
```

---

## F. Medications

**Design (dependency chain, not implemented):**

```text
diagnosis
    ↓
drug class
    ↓
medication
    ↓
start/stop dates
```

**Evidence status: every link in this chain currently requires external
evidence this project has not yet researched.** Even the first link
(diagnosis → drug class) — while medically standard internationally
(e.g., hypertension typically treated with an ACE inhibitor or similar
class) — should not be encoded from general medical knowledge alone. This
project's own discipline (verify, don't assume medically-plausible
relationships) argues for locating an actual Indian standard-of-care
source (e.g., an ICMR treatment guideline, or a WHO Essential Medicines
List localized for India) before encoding **any** drug-class mapping, not
just the prevalence numbers within it. **No medication prevalence
assumptions are introduced by this document.** This entire component is
flagged as a future research requirement in full, likely the
slowest-moving part of the clinical layer.

---

## G. Labs

**Proposed future structure:**

```text
Lab:
    lab_id: str
    analyte: str        # e.g. "fasting_glucose", "total_cholesterol"
    value: float
    unit: str
    measured_at: str     # date
```

**Which labs should exist:** analytes already implied by existing
diagnostic *definitions* in `configs/indian_population.yaml` — fasting
glucose / OGTT (diabetes's own definition already cites the ≥126 mg/dL /
≥200 mg/dL thresholds) and a lipid panel (hyperlipidemia's definition
references a composite dyslipidaemia measure; a **different**, earlier,
smaller ICMR-INDIAB paper — already documented as NOT used for the
headline hyperlipidemia figure — does have component-level percentages:
hypercholesterolemia 13.9%, hypertriglyceridemia 29.5%, low HDL-C 72.3%,
high LDL-C 11.8%. If labs are pursued, this earlier paper becomes
directly relevant evidence — but see the "don't blend non-identical
studies" caveat already established for hyperlipidemia; using it for
component-level lab detail while the *diagnosis* itself uses the newer
INDIAB-17 figure needs to be handled as two explicitly-separate pieces of
evidence, not merged).

**Which are conditional:** a diagnosed-diabetic patient's generated
glucose value should exceed the diagnostic threshold; a
non-diabetic patient's should not. This is an **engineering coherence
rule** (internal consistency), not itself a new evidentiary claim.

**Reference ranges:** **not invented here.** If pursued, must cite a real
source (WHO or ICMR-published reference intervals) — or explicitly
disclose "using standard international reference ranges, not verified as
Indian-population-specific" as a limitation, never silently assumed.

---

## H. Clinical Timeline

**Design principle:** the timeline should **reference**, not duplicate,
other records:

```text
Patient
  ↓
Encounter --reference_id--> (nothing yet; encounters unimplemented)
  ↓
Investigation --reference_id--> lab_id / ecg_id
  ↓
Diagnosis --reference_id--> diagnosis_id
  ↓
Medication --reference_id--> medication_id (which itself references diagnosis_id)
  ↓
Follow-up
```

**Schema implication (not implemented now):** `TimelineEvent` currently
has only `{event_type, date}` — no reference mechanism exists yet. A
future `reference_id: Optional[str]` field (pointing at a `diagnosis_id`,
`lab_id`, or the existing `ecg.ecg_id`) would be a small, additive schema
change, consistent with this project's D005/D006 pattern — but is a
schema change, and per Step 9's instruction, is not made in this
document.

---

## I. Temporal Consistency

Rules to design against (none implemented yet):

- A diagnosis's `onset_date` cannot precede the patient's implied birth
  date (derivable from generated `age`, though this project doesn't
  currently store an explicit `birth_date` — worth flagging as a possible
  M4 schema consideration, not decided here).
- A medication's `start_date` should not precede its linked diagnosis's
  `onset_date`, **only when the model explicitly links them** (per this
  milestone's own wording) — an unlinked medication has no such
  constraint to check.
- A medication's `stop_date` cannot precede its `start_date`.
- All `clinical_timeline` events must be sortable into a coherent,
  non-contradictory chronological order.
- A `FamilyHistoryEntry.age_of_onset`, if ever populated, must be
  biologically plausible relative to `relation` and the patient's own
  age (e.g., a parent's onset age should fit a parent's generation) — an
  engineering plausibility check, not an evidence-derived rule.

**Design note for M4:** these rules extend `validation/structural.py`'s
existing pattern (deterministic, generator-independent checks) — a
natural, additive extension of already-working code, not a new validation
paradigm.

---

## J. Provenance

This project has already been using an informal five-tier evidence
classification since M2D (`configs/indian_population.yaml`'s
`evidence_tier` fields: source-backed / derived-from-source-backed /
engineering assumption / model-generated / unavailable — matching this
milestone's A/B/C/D/E framework almost exactly). **Proposal: extend this
same discipline to per-field provenance on generated patients
themselves**, not just the population-level config.

Currently, `Patient.provenance` is a single whole-patient free-text
`generator: str` field describing everything generated at once (see
`integration/build_patient.py`'s `provenance.generator` string). As the
clinical layer grows, a single free-text field will become harder to
parse programmatically. A future per-field-group tag (e.g., "diagnoses:
tier B, derived from risk_factors"; "medications: tier E, not generated")
would make the distinction A-E machine-checkable, not just readable prose
— directly useful when evaluating the eventual 100K dataset, as this
milestone's own instructions anticipate. **This is a recommended pattern
for M4 to adopt, not a schema change made here.**

---

## Summary

Every component above is either (a) already implemented and evidence-
backed, (b) a well-scoped engineering relationship that reformats
existing evidence rather than inventing new claims, or (c) explicitly
marked as blocked on evidence this project has not yet located. Nothing
in this document should be read as authorizing implementation — it is
input to `docs/M4_CLINICAL_GENERATION_PLAN.md`.
