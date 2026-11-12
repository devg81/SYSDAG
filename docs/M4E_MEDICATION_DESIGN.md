# M4E — Medication Evidence + Architecture + Implementation Design

**Status:** COMPLETE.

## M4E-1 — Medication representation audit

**Current schema** (`schemas/patient_schema.py`, before this milestone):
```python
medications: Optional[list[Any]] = None  # not yet implemented — Stage 3
```
Untyped placeholder, `None` for every patient generated so far (M1-M4D)
— the same pattern `diagnoses`/`medical_history` were in before M4D, no
surprise here (unlike M4D's `medical_history` dict/list discrepancy).

`docs/M4_CLINICAL_ARCHITECTURE.md` §8 already scoped this: "`Medication`
container (schema shape only, empty until content is evidence-backed) —
READY FOR M4 IMPLEMENTATION (shape); generation logic itself NEEDS MORE
EVIDENCE." §6 rule 3 already specified: "every medication references a
`diagnosis_id` that actually exists on the same patient." §10 rule 7
already anticipated a `medication_id`.

**Field-by-field classification** (per this milestone's A/B/C/D scheme):

| Field | Classification | Reasoning |
|---|---|---|
| `medication_id` | **A** | Trivial engineering identifier, same pattern as `diagnosis_id` |
| `drug_class` | **A** | Evidence-supported at the coarse level actually measured (NNMS reports treatment *for a condition*, i.e. "antihypertensive"/"antidiabetic" as therapeutic categories) — see below for why no finer-grained pharmacological subclass (ACE-i vs. CCB vs. ARB) is used |
| `diagnosis_id` (indication reference) | **A** | Directly required by `docs/M4_CLINICAL_ARCHITECTURE.md` §6 rule 3; mirrors `MedicalHistoryEntry.diagnosis_id`'s already-implemented pattern (M4D) |
| `current_status` | **A** | NNMS measures point-prevalence of "currently on treatment" — this maps directly to `"active"` with no invented assumption; `"discontinued"` reserved in the vocabulary but never produced (no discontinuation-rate evidence) |
| `start_date` | **B** | Engineering placeholder, always `None` — no per-patient initiation-date evidence exists (mirrors `Diagnosis.diagnosed_date`) |
| `stop_date` | **B** | Same — always `None`; only relevant once `current_status="discontinued"` is ever produced, which it isn't |
| `source` | **A** | Same provenance-string pattern as `Diagnosis.source` |
| Specific drug **name** (e.g. "amlodipine") | **D — should NOT be represented** | NLEM confirms availability, not prescribing share; no Indian source anywhere researched reports what fraction of treated hypertensives get which specific drug or even which pharmacological subclass. Generating one would be inventing a distribution, exactly what this milestone forbids. |
| Dose | **D** | No evidence; not attempted |
| Frequency | **D** | No evidence; not attempted |
| Route | **D** | Not evidence-relevant (all NLEM-confirmed candidates are oral) and not needed by any downstream consumer — skipped per YAGNI, not because it's unsupported per se |
| Prescription status | **D** | Redundant with `current_status`; not added as a separate field |
| Adherence | **D** | Evidence conflicting/non-representative (M4E-0) |
| Duration | **D** | No evidence found |
| Per-medication `source`/provenance detail beyond the string field | **D (not needed)** | Already covered at `Patient.provenance` level, the existing project-wide pattern — no new mechanism required |

**Why `drug_class` stops at "antihypertensive"/"antidiabetic" and not a
pharmacological subclass:** NNMS's own treatment-rate figures are
reported *per diagnosed condition* ("is this hypertensive patient
currently treated"), not per pharmacological subclass. There is no
Indian population-level figure anywhere researched for "what fraction
of treated hypertensives receive an ACE inhibitor vs. a CCB vs. an
ARB." Stopping at the therapeutic-category level is the evidence's own
natural resolution — going finer would require inventing a class-share
distribution NLEM's mere availability listing cannot supply.

## M4E-2 — Medication generation architecture

```text
patient demographics (existing)
        ↓
risk_factors.hypertension / diabetes (existing, M2C)
        ↓
diagnoses["hypertension"/"diabetes"] (existing, M4D, D015)
        ↓
treatment probability (NEW — NNMS treatment-rate Bernoulli)
        ↓
treated / untreated (NEW)
        ↓
drug_class label ("antihypertensive"/"antidiabetic") (NEW — same draw, no separate step)
        ↓
[STOP — no specific medication selection step exists]
        ↓
temporal metadata (NEW — always null, engineering placeholder)
```

| Edge | Classification | Justification |
|---|---|---|
| `hypertension` diagnosis → probability of antihypertensive treatment | **EVIDENCE-SUPPORTED** | NNMS 2017-18 national cascade, 14.5% |
| `diabetes` diagnosis → probability of antidiabetic treatment | **EVIDENCE-SUPPORTED** | NNMS 2017-18 national cascade, 36.1% |
| treated=True → `current_status="active"` | **EVIDENCE-SUPPORTED** | Direct mapping of NNMS's own point-prevalence measurement, no invented assumption |
| treatment → drug_class (coarse therapeutic category) | **EVIDENCE-SUPPORTED** (at this coarse level only) | Matches exactly what NNMS measured — a condition-level treatment rate, not a class-share distribution |
| drug_class → specific drug name | **NOT IMPLEMENTED — no edge exists** | Would require inventing a class-share/drug-share distribution; explicitly not attempted (M4E-1) |
| specific drug → dose/frequency/duration/adherence | **NOT IMPLEMENTED — no edge exists** | Same reason, one level further; moot since the previous edge doesn't exist either |
| hyperlipidemia diagnosis → statin treatment | **NOT IMPLEMENTED** | Doubly blocked: hyperlipidemia's diagnosis itself is deferred (D015), and no statin population treatment-rate evidence exists (M4E-0) |
| (any diagnosis) → antiplatelet treatment | **NOT IMPLEMENTED** | No evidence; also no CVD-event/primary-prevention-score variable exists to gate it against |

This is the exact "diagnosis → treatment probability → treated/
untreated → drug class → specific drug ONLY if justified" chain this
milestone's own M4E-4 section specifies — truncated at the point the
evidence actually stops, not one step further.

## M4E-3 — Human checkpoint determination

Checked against every listed STOP trigger:

- **Two incompatible treatment-rate estimates that materially affect
  generation?** The adherence conflict (NFHS-4 26.78% vs. meta-analysis
  15.8%, M4E-0) is real, but adherence is not generated at all (neither
  figure is used) — does not materially affect any generation decision.
  Documented, not silently resolved, not blocking.
- **Population mismatch changing the target-population
  interpretation?** NNMS's 18-69 sampled range vs. this project's 20-89
  scope is the same class of extrapolation gap already accepted and
  documented for BMI/smoking (D008) — not new, not a reinterpretation
  of the target population.
- **Evidence supports treatment class but not specific medication?**
  Yes — this milestone's own M4E-4 instructions already say how to
  handle exactly this case ("stop at class level"), so it is resolved
  by following the milestone's own instruction, not a checkpoint
  requiring a stop.
- **Evidence supports availability but not prevalence?** Yes (NLEM vs.
  statins/antiplatelets) — same: resolved by deferring generation
  entirely for those classes, per this milestone's own explicit
  warning against conflating the two.
- **Schema restructuring?** No — additive `Medication` dataclass,
  identical pattern to `Diagnosis`/`MedicalHistoryEntry` (D015
  precedent).
- **Medically consequential assumption not already authorized?** No —
  the only assumption made (treated-at-survey-time ≈
  `current_status="active"`) is a direct, non-inventive mapping of what
  NNMS actually measured.

**Conclusion: no genuine conflict exists. Proceeding to implementation
without a human checkpoint**, per this milestone's own M4E-3 rule.

## M4E-5 — Temporal design

**`start_date`/`stop_date`: always `None`.** No Indian source gives a
per-patient medication-initiation-date distribution (same conclusion as
`Diagnosis.diagnosed_date`, M4D). `current_status` is always `"active"`
(the only value NNMS's point-prevalence design can support) — per this
milestone's own rule, "active medication → stop_date = null" is
therefore satisfied by construction, not by a separate check. No
discontinued medication is ever generated (no discontinuation-rate
evidence, M4E-0), so the `stop_date`-may-be-populated-only-if-justified
branch of this milestone's rule is simply never reached.

## M4E-6 — Validation rule classification

| Rule | Classification |
|---|---|
| `drug_class` ∈ `MEDICATION_DRUG_CLASSES` | **Hard structural rule** (`validation/structural.py`) |
| `current_status` ∈ `MEDICATION_STATUSES` | **Hard structural rule** |
| `medication.diagnosis_id` resolves to a real diagnosis on the same patient | **Hard consistency rule** (`validation/clinical_consistency.py`, mirrors `medical_history`'s orphan check) |
| `medication.drug_class` matches the referenced diagnosis's code (`antihypertensive` ↔ `hypertension`, `antidiabetic` ↔ `diabetes`) | **Hard consistency rule** — the one controlled mapping that does exist |
| `current_status="active"` ⟹ `stop_date is None` | **Engineering invariant** (always true today by construction; checked anyway, defense-in-depth, same discipline as the lipid-recomputation check) |
| `start_date <= stop_date` when both populated | **Engineering invariant** (never triggered today; general-purpose, matches `docs/CLINICAL_RECORD_DESIGN.md` §I's already-designed rule) |
| No duplicate `medication_id` within a patient | **Hard structural rule** |
| At most one medication per `diagnosis_id` | **Engineering invariant** (the derivation function only ever produces one; checked as defense-in-depth) |
| `medications == []` is valid | **Missingness semantics**, not a rule — untreated/no-qualifying-diagnosis patients correctly get an empty list, never `None` |
| Whether a specific patient *should* have been treated | **Not checkable** — unlike `lipid_interpretations` (a pure function of stored raw values), the treatment Bernoulli draw is not itself re-derivable from other stored fields (the consumed random number isn't stored) — same situation as `risk_factors.hypertension` itself, a sampled primitive, not a checkable derivation. A population-level statistical check (binomial test against the cited rate) belongs in the batch-validation report, not the per-patient validator — same precedent as M4B's dyslipidemia-rate check. |

No validator encodes `risk_factor == medication` or `diagnosis ==
medication` as an automatic rule — only the specific,
evidence-justified `drug_class ↔ diagnosis.code` mapping is enforced.
