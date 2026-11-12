# M4C — Clinical Consistency Audit

**Milestone:** M4C (audit + validator implementation). No generation
behavior changed by this document or its implementation.
**Date:** 2026-09-26

Maps every field currently in `Patient` (per `schemas/patient_schema.py`,
read fresh for this milestone, not assumed) to how it's actually
generated today, and classifies each cross-field relationship.

---

## Current Generation State (verified against the actual repository, not assumed)

| Field | Populated? | Source |
|---|---|---|
| `demographics.{age,sex,state,urban_rural}` | Always | `generation/indian_population.py` |
| `demographics.{height_cm,weight_kg}` | Never (`None`) | Not modeled (M2C scope decision) |
| `risk_factors.{bmi,smoking_status,hypertension,diabetes,hyperlipidemia}` | Always | `generation/indian_population.py`, M2C |
| `lipid_panel` | Always | `generation/indian_population.py`, M4B |
| `lipid_interpretations` | Always (2 entries) | Computed from `lipid_panel`, M4B |
| `labs` | Non-diabetic only | `generation/indian_population.py`, M4B |
| `family_history` | Never (`None`) | Not implemented |
| `medical_history` | Never (`None`) | Not implemented |
| `diagnoses` | Never (`None`) | **Designed** (`docs/CLINICAL_RECORD_DESIGN.md` §E) but **not yet implemented in code** |
| `medications` | Never (`None`) | Not implemented, blocked on evidence |
| `encounters` | Never (`None`) | Not implemented |
| `echo` | Never (`None`) | Scope open (spec) |
| `ecg` | Always | `ingestion/ptbxl_source.py`, M1, unchanged |
| `clinical_timeline` | Always (1 event) | `integration/build_patient.py`, M1, unchanged |

**Important correction to this milestone's own framing:** M4C's brief
describes "diagnoses ↔ risk factors," "medications ↔ diagnoses," and
"medical history ↔ diagnoses" as if these relationships are already
implemented and need validating. **They are not implemented.**
`diagnoses`/`medical_history`/`medications`/`encounters` are all
unconditionally `None` for every patient today — the "derive diagnoses
from risk factors" design (`docs/CLINICAL_RECORD_DESIGN.md` §E,
reiterated as M4B's own "next step" recommendation) has not been coded.
Per this milestone's own instruction ("do not assume the architecture
from this prompt if the repository contains more specific implementation
details"), sections 4.3/4.4/4.5 below reflect this actual state, not the
prompt's assumption.

---

## Dependency Table

| Source | Dependent field | Relationship | Current enforcement | M4C action |
|---|---|---|---|---|
| `demographics.sex` | `risk_factors.bmi` | Sex-conditioned category sampling | A (enforced at generation) | B — validate the generated value falls within a range the sex-conditioned config could have produced |
| `demographics.sex` | `risk_factors.smoking_status` | Sex-conditioned category sampling | A | B — validate value ∈ `SMOKING_STATUSES` |
| `demographics.sex` | `lipid_panel.hdl_mg_dl` | Sex-specific range | A | B — validate value ∈ sex-appropriate outer bound |
| `demographics.age`, `demographics.sex`, `risk_factors.diabetes` | `labs[HbA1c]` | Conditional generation (M4B, D011) | A | **B — hard rule, see §4.1** |
| `lipid_panel.{ldl,hdl,tg,tc}_mg_dl` | `lipid_interpretations[*].dyslipidemia` | Computed, not sampled (D011) | A | **B — hard rule, see §4.2** |
| `risk_factors.hyperlipidemia` | `lipid_interpretations[*].dyslipidemia` | **NONE — independently generated** | **C, but see finding below** | **E — architecture issue, human checkpoint** |
| `risk_factors.{hypertension,diabetes,hyperlipidemia}` | `diagnoses` | Designed (derive, don't duplicate) | **Not implemented** | D — future research/implementation, not validated (nothing to validate yet) |
| `diagnoses` | `medications` | Designed (medication depends on diagnosis) | Not implemented | D |
| `diagnoses` | `medical_history` | Designed (chronic-condition slice mirrors diagnoses) | Not implemented | D |
| `clinical_timeline` | `labs[*].measured_at` | Both derived from the same generation-time snapshot date | A (same date source in code) | B — validate they actually match |
| `ecg.*` | (nothing depends on it yet) | N/A | A (structural, unchanged since M1) | C — already covered by `validation/structural.py`, not duplicated here |
| `demographics.age` | `demographics.state`/`urban_rural` | None (independent, Census-based) | C (correctly unconditioned, per M2C/M2D findings) | C — no evidence supports conditioning; correctly left alone |

---

## Finding: `risk_factors.hyperlipidemia` vs. `lipid_interpretations` disagree substantially

**This is the most important finding of this audit.** `risk_factors.
hyperlipidemia` (M2C: an unconditioned `Bernoulli(0.812)` draw from
ICMR-INDIAB-17's headline composite figure) and `lipid_interpretations`
(M4B: computed from the actual generated `lipid_panel` values against
NCEP/LAI thresholds) are **two entirely independent generation
processes** describing what is conceptually the same fact — whether the
patient has dyslipidemia. They were never reconciled when M4B was built.

**Measured on the existing 100-patient M4B output**
(`outputs/m4b/100_patients/`): `risk_factors.hyperlipidemia` agrees with
the NCEP-based `lipid_interpretations` entry only **73/100** times, and
with the LAI-based entry only **77/100** times. If these represented the
same underlying fact, we would expect agreement close to 100% (bounded
below by how far the marginal `p` used for the Bernoulli, 0.812,
differs from the *effective* composite rate the lipid panel actually
produces, ~84-88% per M4B's own validation) — 73-77% is far short of
that, confirming these are genuinely uncoordinated, not just
statistically noisy versions of the same thing.

**This is exactly the "two independently-random, inconsistent
representations of the same fact" problem `docs/DECISIONS.md` D004 and
`docs/CLINICAL_RECORD_DESIGN.md` §D already warn against for other field
pairs** — it was introduced across two different milestones (M2C, M4B)
without being caught until this consistency audit, which is precisely
what M4C exists to surface.

**Classification: E — architecture issue.** **Not fixed in this
milestone** — resolving it means choosing one of several possible
directions (deprecate `risk_factors.hyperlipidemia` in favor of
`lipid_interpretations`; keep both but document `risk_factors.
hyperlipidemia` as a legacy/independent field explicitly not meant to
agree; or retrofit `risk_factors.hyperlipidemia` to be derived from
`lipid_interpretations`, changing M2C generation behavior) — each is a
genuine judgment call this milestone's own restrictions don't authorize
making unilaterally ("do not change existing risk-factor distributions,"
"a schema redesign" and "a change to D011/D012" are explicit STOP
triggers, and any of the three resolutions above touches at least one of
these). **Recorded as a human checkpoint — see the final report.**

**RESOLVED (2026-09-26, follow-up milestone):** human decision Option B
— keep both as distinct variables. See
`docs/M4C_HYPERLIPIDEMIA_RESOLUTION.md` and `docs/DECISIONS.md` D014
for the semantic audit and formal contract. `risk_factors.
hyperlipidemia` ↔ `lipid_interpretations` disagreement is an expected
semantic difference, not a clinical-consistency error — the "E —
architecture issue" classification above is superseded by that
resolution, not by a code change (no generation behavior changed).

---

## Supported / Unsupported / Future Research Summary

| Relationship | Classification |
|---|---|
| Sex → BMI/smoking category | A (enforced), validated as B |
| Sex → HDL range | A (enforced), validated as B |
| Age+sex+diabetes → HbA1c | A (enforced), validated as B (hard rule) |
| Lipid panel → lipid interpretations | A (enforced), validated as B (hard rule) |
| `risk_factors.hyperlipidemia` ↔ `lipid_interpretations` | **C/E — unsupported, architecture issue, human checkpoint** |
| Timeline date ↔ labs measured_at | A (same source), validated as B |
| Risk factors → diagnoses | D — designed, not implemented, nothing to validate yet |
| Diagnoses → medications | D — not implemented |
| Diagnoses → medical_history | D — not implemented |
| Family history (any form) | D — not implemented, LASI-scope decision still pending (`docs/M4_CLINICAL_EVIDENCE.md` Proposed Decision 4) |
| Echo (any form) | D — scope entirely open |
| ECG structural validity | C — already covered by `validation/structural.py`, unchanged |

---

## Temporal Consistency — What Actually Exists to Check

Only **one** generation-time snapshot date exists per patient today:
`provenance.generated_at` (full datetime) → its date part is copied into
both `clinical_timeline[0].date` and, when present, `labs[0].measured_at`.
**There are no other dated fields** (no diagnosis dates, no medication
start/stop dates, no multiple lab measurements) — so the only meaningful
temporal check available is **internal self-consistency**: do these two
independently-set date strings actually match? (If a future refactor
changed one code path's date source without the other, this would catch
it.) No "stop_date < start_date" or "event before required preceding
event" checks are possible yet — there is nothing else with a date.
This is a **narrower** temporal audit than the M4C brief's framing
assumed, again because those richer dated fields don't exist in the
repository yet.

---

## Missingness Audit

| Field | Missingness rule | Classification |
|---|---|---|
| `lipid_panel` | Never missing | ENGINEERING (M4B-0 §A5 — survey sub-sampling ≠ real missingness) |
| `labs` (HbA1c) | Missing iff `diabetes=True` | SUPPORTED (M4-0's evidence gap for diabetic-population HbA1c) |
| `family_history` | Always missing | FUTURE RESEARCH (D004; LASI-scope decision still pending) |
| `medical_history` | Always missing | FUTURE RESEARCH (designed, not implemented) |
| `diagnoses` | Always missing | FUTURE RESEARCH (designed, not implemented) |
| `medications` | Always missing | FUTURE RESEARCH (blocked on evidence depth, partial evidence now exists per M4-0 but not implemented) |
| `echo` | Always missing | FUTURE RESEARCH (scope open) |

No missingness behavior was changed. All are either already-correct
engineering decisions or explicitly-scoped future work, per this
milestone's restriction against forcing completeness.

---

## What This Audit Does Not Claim

Per this milestone's explicit instruction: **"no contradictions found"
in the two validated hard rules (lipid interpretation, HbA1c) is not the
same claim as "these patients are medically realistic" or
"representative of the Indian population."** Both hard rules are
internal-consistency checks (does the code do what it says it does) —
neither checks, nor could check, whether the underlying generation
targets (NCEP/LAI marginal rates, INDIAB-12's HbA1c trend) are
themselves clinically accurate for any individual, only that this
project's own documented evidence was applied without contradiction.
