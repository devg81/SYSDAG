# M4 Clinical Variable Architecture (M4-0B)

**Milestone:** M4-0B — Clinical Variable Architecture Decision
(design/documentation only). No code, schema, or generator change.
**Date:** 2026-09-26
**Builds on:** `docs/CLINICAL_RECORD_DESIGN.md` (M3.5), `docs/M4_CLINICAL_EVIDENCE.md`
(M4-0), `docs/M4-0A_DYSLIPIDEMIA_DECISION_BRIEF.md` (M4-0A). Converts the
three human decisions below into a formal architecture for M4.

---

## Human Decisions Applied (authoritative, recorded exactly)

1. **Dyslipidemia representation:** continuous LDL (and, by the same
   logic, HDL/triglycerides/total cholesterol) is the **primary** data.
   Multiple documented clinical definitions (NCEP/ATP III, LAI, and any
   future one) derive categorical labels **from** that value. No single
   threshold is treated as universal medical truth.
2. **LDL generation architecture:** generate the continuous/raw value
   first; derive categorical interpretations from it afterward using
   explicitly documented definitions. LDL and hyperlipidemia are never
   independently generated as unrelated random variables.
3. **Project-wide clinical architecture:** apply
   `RAW/CONTINUOUS VALUE → DERIVED INTERPRETATION` wherever the evidence
   supports it — but **not** where it doesn't. Forcing this pattern
   without evidence would violate this project's core discipline
   (`CLAUDE.md` §14/§19, already invoked throughout M2A-M4-0A).

No contradiction with existing project evidence was found while applying
these decisions — see §3 (HbA1c) and §4 (hypertension) for two places
where the *direction* of the pattern needed a documented refinement, not
a reversal of the decision itself; neither constitutes a human-checkpoint
contradiction.

---

## 1. Schema Audit

| Clinical Domain | Raw Variable | Derived Variable | Evidence Status | Architecture |
|---|---|---|---|---|
| Lipids | LDL, HDL, triglycerides, total cholesterol (mg/dL) | Dyslipidemia interpretation(s), tagged by definition | Category-level prevalence SUPPORTED for both NCEP (INDIAB-17) and LAI (INDIAB-25) definitions; **continuous mean/SD distribution NOT SUPPORTED** (confirmed absent, M4-0) | Raw → Derived (per Decisions 1/2) — but the "raw" value must itself be *reconstructed* from category evidence (an engineering step, same spirit as BMI), not directly observed |
| Glycemic (HbA1c) | HbA1c (%) | — (not a diabetes-diagnosis derivation; see §3) | Non-diabetic (NGT) age×sex×urban/rural trend **SUPPORTED** (ICMR-INDIAB-12); diabetic-population HbA1c **PARTIALLY SUPPORTED** (thin, 4-state, non-representative) | **Reversed direction**: diabetes label (already primary evidence) → conditional HbA1c value — see §3 |
| Glycemic (diabetes) | Fasting glucose / OGTT (mg/dL) | Diabetes label | Diagnostic criterion already embedded in the label's own definition text; **no continuous glucose value generated today** | Currently label-only; a future raw glucose value would need to be *consistent with* the already-generated label, same reversed direction as HbA1c |
| Blood pressure / hypertension | SBP/DBP (mmHg) | Hypertension label | Label prevalence SUPPORTED (INDIAB-17 marginal); **BP continuous distribution NEVER RESEARCHED — NOT SUPPORTED** | Label-only for now; raw→derived NOT YET SUPPORTED — future research (§4) |
| BMI / anthropometrics | height_cm, weight_kg | BMI | BMI category prevalence SUPPORTED (NNMS); height/weight distributions **NOT SUPPORTED** (M4-0, 3 failed access attempts) | **BMI is the raw/primary variable today** — the inverse of the general pattern, justified because no height/weight evidence exists to invert it (M4-0's own resolved recommendation, unchanged) |
| Smoking | — | Smoking status label | Category-level, sex-conditioned, SUPPORTED (NNMS) | Label-only — smoking status has no continuous "raw" analogue; Architecture D |
| Family history | — | Family-history-of-diabetes label | PARTIALLY SUPPORTED (LASI, 45+ only, M4-0) | Label-only, Architecture D |
| Medical history | — | Chronic-condition entries | Derived from risk_factors (M3.5 design) | Label → associated data (Architecture B) |
| Diagnoses | — (except where chained from lipids) | HTN/diabetes/hyperlipidemia diagnosis entries | SUPPORTED for these three; NOT SUPPORTED for CVD events/procedures | Mostly B; hyperlipidemia's diagnosis becomes a **two-hop chain** (A→B) once lipid architecture lands: raw LDL → interpretation label → diagnosis entry |
| Medications | — | Drug class / medication entries | NLEM 2022 PARTIALLY SUPPORTED (drug classes); NNMS treatment rates SUPPORTED; discontinuation NOT SUPPORTED | Label → associated data (Architecture B), gated by diagnosis + treatment-rate evidence |
| Labs (container) | Houses LDL/HDL/TG/TC/HbA1c | — | Mixed, per-analyte as above | This container **is** the raw-value layer |
| ECG | `ecg_id` (source pointer, PTB-XL) | `superclasses` (diagnostic labels) | Already implemented (M1); signal itself deferred to Stage 4 | **Already Architecture C (both)** — a derived label exists today; the raw signal is the missing half, explicitly deferred |
| Echo | — | — | Scope entirely open (spec §2.1/§7) | Architecture D — insufficient information to design yet |

---

## 2. Lipid Architecture

**Continuous (raw, primary):** `ldl_mg_dl`, `hdl_mg_dl`,
`triglycerides_mg_dl`, `total_cholesterol_mg_dl` — all `float`, unit
`mg/dL` (both cited sources use this unit; no conversion needed).

**Derived:** a list of tagged interpretations, not a single flat boolean
— this directly avoids the ambiguity that caused the M4-0A conflict in
the first place (a bare `hyperlipidemia: bool` can't say *which*
definition produced it).

```text
LipidPanel:
    ldl_mg_dl: float
    hdl_mg_dl: float
    triglycerides_mg_dl: float
    total_cholesterol_mg_dl: float
    interpretations: list[LipidInterpretation]

LipidInterpretation:
    definition: str            # e.g. "NCEP_ATP_III" | "LAI_2020"
    source_citation: str        # traceability, matching this project's existing config-metadata discipline
    dyslipidemia: bool
    components_abnormal: list[str]   # which of TC/TG/HDL/LDL triggered it under this definition
```

**Should reference definitions be stored?** Yes — as a small, named,
citable table (not per-patient data, closer to how
`configs/indian_population.yaml` already stores per-parameter metadata),
e.g.:

```text
NCEP_ATP_III: {ldl_threshold: 130, tc_threshold: 200, tg_threshold: 150, hdl_threshold_male: 40, hdl_threshold_female: 50, source: "INDIAB-17 / NCEP ATP III"}
LAI_2020: {ldl_threshold: 100, tc_threshold: 200, tg_threshold: 150, hdl_threshold_male: 40, hdl_threshold_female: 50, source: "INDIAB-25 / Lipid Association of India"}
```

This lets `interpretations` be **computed**, not independently sampled —
see §6 for why this is the key consistency guarantee.

**How multiple definitions coexist without ambiguity:** each
`LipidInterpretation` is self-labeled with its `definition` — a consumer
of this data always knows which guideline produced any given `True`/
`False`, and a new guideline (a future LAI update, or an ICMR-specific
one) can be added as a new list entry without touching existing ones or
re-litigating which one is "correct."

**Important caveat, restated from M4-0A:** Decision 1/2 settle the
*architecture* (value-first, label-derived). They do **not** retroactively
create continuous-distribution evidence that doesn't exist. The "raw"
LDL/TC/TG/HDL values will still need to be generated via the same
category-then-reconstruction engineering approach already used for BMI —
"raw" here means "the single quantity multiple interpretations derive
from," not "directly observed data." This must be disclosed in provenance
exactly as prominently as BMI's existing disclosure.

---

## 3. HbA1c Architecture

**Measured value:** HbA1c (%), continuous.

**Population distribution:** genuinely the strongest continuous-variable
evidence this entire project has found — ICMR-INDIAB-12 (n=14,222,
confirmed-NGT adults 20+): age-decade trend 5.16±0.71% (20-29y) to
5.49±0.69% (70+y), **with real age×sex and age×urban/rural conditional
detail** (females +0.10%/decade vs. males +0.06%/decade; urban
+0.10%/decade vs. rural +0.08%/decade).

**Clinical interpretation:** standard international ADA thresholds exist
(<5.7% normal, 5.7-6.4% prediabetic, ≥6.5% diabetic) but were **not**
confirmed as India-verified in this project's own research, and
ICMR-INDIAB's own diabetes *definition* uses FPG/OGTT, not HbA1c, as its
primary criterion. If HbA1c-based labeling is ever added, it must be
disclosed as using **standard international cutoffs, not verified
India-specific** — the same discipline already applied to BMI/lipid
reference ranges.

**Diagnostic label — the reversed-direction finding:** HbA1c is **not**
an appropriate variable to derive the diabetes label *from*, in this
project's architecture. The diabetes label is already this project's
*most* evidence-backed variable (a national-marginal Bernoulli directly
from ICMR-INDIAB-17's own FPG/OGTT-based definition). Re-deriving it from
a generated HbA1c value would risk creating an inconsistency with that
already-more-authoritative source. Instead:

```text
diabetes label (already generated, primary)
        ↓
HbA1c value generated CONDITIONALLY on the label:
  - if diabetes = False: sample from the INDIAB-12 NGT distribution
    (age/sex/urban-rural-conditioned) — SUPPORTED
  - if diabetes = True: only thin, non-representative 4-state evidence
    exists — generate cautiously with a heavy caveat, or leave
    unpopulated pending better evidence — NOT recommended to generate
    confidently yet
```

**This is exactly the case Decision 3 anticipated** ("must NOT force
this pattern where the available evidence does not support it") — here,
the evidence supports the *reverse* direction for this one variable, not
no pattern at all.

---

## 4. Hypertension Architecture

**Current state:** `risk_factors.hypertension` is a boolean, generated
directly as an unconditioned `Bernoulli(0.355)` from ICMR-INDIAB-17's
national marginal (BP≥140/90 mmHg or on antihypertensive medication).

**Should the project represent BP measurements, status, or both?**
Evidence-dependent, and the evidence isn't there yet: **no Indian BP
continuous-distribution research (mean/SD by age/sex) has been conducted
by this project at all** — unlike lipids and HbA1c, this specific
question was never asked in M4-0 or M4-0A's research passes.

**Can hypertension status be legitimately derived from generated BP
measurements using evidence already available?** **No.** Without a BP
continuous distribution, there is nothing to generate a raw value from.
The current label-only approach (hypertension as the primary generated
variable) remains the only evidence-supported approach today —
**explicitly marked as future research**, not attempted here, and not
treated as a gap in applying Decision 3 (the decision itself says not to
force the pattern without evidence).

**Recommendation:** keep hypertension as a label-only boolean until a
dedicated evidence pass (BP distribution research, analogous to what
this session did for lipids/HbA1c) is conducted. Do not invent a BP
distribution to enable the raw→derived pattern prematurely.

---

## 5. Other Clinical Domains

| Domain | Classification | Reasoning |
|---|---|---|
| Family history | **D — Neither** | No raw-measurement concept applies; if implemented (LASI 45+ finding), it's a standalone label with nothing to derive it from |
| Medical history | **B — Label → associated data** | Chronic-condition entries mirror/derive from `risk_factors` labels (M3.5 design), not from a raw measurement |
| Diagnoses | **C — Both** (domain-dependent) | HTN/diabetes diagnoses: B (label-sourced). Hyperlipidemia diagnosis: A→B chained (raw lipid values → interpretation label → diagnosis entry), once lipid architecture lands |
| Medications | **B — Label → associated data** | Existence/class gated by diagnosis + NNMS treatment-rate evidence, not a raw measurement |
| Labs | **A — Raw → derived** | This is the container where the new raw-value architecture actually lives |
| ECG | **C — Both** (already true today) | `superclasses` (derived label) already exists; raw signal deferred to Stage 4 — this domain already partially matches the target architecture |
| Echo | **D — Insufficient evidence** | Scope entirely open per the spec; nothing to classify yet |

---

## 6. Internal Consistency Rules

**The strongest guarantee is architectural, not just a validation
check:** if `LipidInterpretation.dyslipidemia` is **computed** from the
stored raw values and definition thresholds (a pure function, never
independently sampled), the contradiction "LDL=85, hyperlipidemia=true
under a definition where 85 doesn't qualify" becomes **structurally
impossible**, not just detectable after the fact. This is the single most
important consequence of Decision 2.

Rules to design against (none implemented yet):

1. **Lipid label ≡ f(raw value, definition thresholds).** No
   `LipidInterpretation` may ever be generated independently of its
   corresponding raw values — computed only. A validation check should
   still re-verify this (defense in depth, matching this project's
   existing "trust but verify" pattern from the M3.5 caching-fix
   regression tests) in case of a future refactor bug.
2. **HbA1c must be drawn from the distribution matching the
   already-generated diabetes label** (NGT distribution if
   `diabetes=False`; the thin diabetic-population data, or unpopulated,
   if `diabetes=True`) — never the wrong branch.
3. **Every medication references a `diagnosis_id` that actually exists**
   on the same patient — no medication may exist "floating," unrelated
   to any diagnosis.
4. **No clinical event may precede the patient's implied birth date**
   (age-derived) — already designed in `docs/CLINICAL_RECORD_DESIGN.md`
   §I, restated here as it directly applies to lab `measured_at` dates
   too.
5. **Every unpopulated field carries a documented reason**, extending
   this project's existing discipline (e.g., "medications: None — NLEM
   full-extraction/discontinuation evidence insufficient, see
   `docs/M4_CLINICAL_EVIDENCE.md`") rather than silent absence.
6. **Every `LipidInterpretation.definition` must resolve to a recognized,
   documented definition** (from the small reference table in §2) — no
   interpretation may cite an undocumented, untraceable threshold.

---

## 7. Temporal Architecture

**Evidence-supported temporal relationships (narrow):**
- LASI's age-band diagnosis-*rate* peaks (hypertension 75+, diabetes
  55-64) — real population-level evidence, but restricted to ages 45+,
  and describes a *rate by band*, not a per-patient onset distribution.

**Everything else remains engineering-generated**, and must be labeled
as such: exact `onset_date` values, medication `start_date`/`stop_date`
timing, lab `measured_at` scheduling, and any diagnosis dating outside
the LASI 45+ band. No source in this project's research gives a
per-patient temporal distribution for any of these.

This matches `docs/CLINICAL_RECORD_DESIGN.md` §I's already-designed rules
(diagnosis ≥ birth date; medication stop ≥ start; chronological
sortability) — restated here as directly applicable to the new lipid/
HbA1c `measured_at` fields, not a new design.

---

## 8. Schema Changes Required Later

| Proposed change | Classification |
|---|---|
| `LipidPanel`/`LipidInterpretation` dataclasses (§2) | **READY FOR M4 IMPLEMENTATION** — the architecture is now human-decided (Decisions 1-3); this session's decisions constitute the required checkpoint, no further sign-off needed before mechanical implementation |
| HbA1c field (NGT-conditioned generation) | **READY FOR M4 IMPLEMENTATION** for non-diabetic patients; **NEEDS MORE EVIDENCE** for diabetic-population values |
| SBP/DBP raw fields | **NEEDS MORE EVIDENCE** — no BP distribution research conducted yet |
| Reference-definition table (NCEP/LAI thresholds) | **READY FOR M4 IMPLEMENTATION** — data already gathered in M4-0A |
| `Diagnosis`/`RiskFactors`-derived medical_history (M3.5 design) | **READY FOR M4 IMPLEMENTATION** for HTN/diabetes/hyperlipidemia slice; **NOT REQUIRED** beyond that (CVD events/procedures blocked on evidence) |
| `Medication` container (schema shape only, empty until content is evidence-backed) | **READY FOR M4 IMPLEMENTATION** (shape); generation logic itself **NEEDS MORE EVIDENCE** |
| `TimelineEvent.reference_id` | **REQUIRES HUMAN DECISION** — flagged in M3.5, not addressed by this session's decisions (which were lipid-specific) |
| Patient-level `birth_date` field | **REQUIRES HUMAN DECISION** — raised in `docs/CLINICAL_RECORD_DESIGN.md` §I, not addressed here |
| Family history structure | **REQUIRES HUMAN DECISION** — the LASI-45+-scope question from `docs/M4_CLINICAL_EVIDENCE.md` Proposed Decision 4 remains open |
| ECG synthetic-signal fields | **DEFERRED TO ECG STAGE** |
| Echo fields | **DEFERRED TO ECHO STAGE** |

No schema is modified in this document.

---

## 9. Generation Dependency Graph

```text
1. Patient identity (patient_id)                              [unchanged]
2. Demographics (age, sex, state, urban_rural)                 EVIDENCE-SUPPORTED [unchanged]
3. Risk-factor labels already primary-evidence-backed:
   hypertension, diabetes (Bernoulli, INDIAB-17);
   smoking_status (sex-conditioned, NNMS)                       EVIDENCE-SUPPORTED [unchanged]
4. BMI (category then engineering-reconstructed value)          EVIDENCE-SUPPORTED (category) /
                                                                  ENGINEERING (continuous value) [unchanged]
5. Raw lipid panel (LDL, HDL, TG, TC)                            ENGINEERING (reconstructed from
                                                                  category-level evidence, NOT
                                                                  directly observed)
6. Derived lipid interpretations (per definition)                ENGINEERING (pure computation
                                                                  from step 5 + stored thresholds —
                                                                  not a new sampling step)
7. HbA1c (conditioned on step 3's diabetes label)                EVIDENCE-SUPPORTED for NGT;
                                                                  FUTURE RESEARCH for diabetic pop.
8. Diagnoses (derived from steps 3 and 6)                        ENGINEERING (promotion of
                                                                  existing labels; onset_date
                                                                  itself is ENGINEERING)
9. Medications (depends on step 8 + NNMS treatment-rate gate)    PARTIALLY EVIDENCE-SUPPORTED
                                                                  (treatment rate) / FUTURE
                                                                  RESEARCH (drug-class specifics,
                                                                  discontinuation)
10. Clinical timeline (references all of the above by ID)        ENGINEERING (chronological index,
                                                                  not new information)
```

**Note on ordering rationale:** step 5 (raw lipids) must precede step 6
(interpretations) because interpretations are computed, not sampled —
this is the direct implementation of Decision 2. Step 7 (HbA1c) must
follow step 3 because it's conditioned on the already-generated diabetes
label (§3's reversed-direction finding) — placing it earlier would have
nothing to condition on.

---

## 10. Validation Architecture

Extending `validation/structural.py`'s existing pattern (deterministic,
generator-independent checks — not implemented in this document):

1. **Range validity:** lipid values within physiologically plausible
   outer bounds (e.g., LDL 20-400 mg/dL) — an engineering sanity check,
   distinct from the *clinical* interpretation thresholds in §2.
2. **Unit validity:** every lab value carries an explicit unit string;
   validation checks it matches the expected unit (`"mg/dL"`, `"%"` for
   HbA1c) rather than assuming.
3. **Raw-value/label consistency:** re-compute each
   `LipidInterpretation` from its patient's raw values + the named
   definition's thresholds; assert it matches what's stored (§6, rule 1
   — should always pass by construction; tested anyway).
4. **Temporal consistency:** extends `docs/CLINICAL_RECORD_DESIGN.md`
   §I's rules — onset/measured dates ≥ implied birth date; medication
   stop ≥ start; global chronological sortability.
5. **Medication/diagnosis consistency:** every medication's
   `diagnosis_id` resolves to a real diagnosis on the same patient (§6,
   rule 3).
6. **Demographic/clinical consistency:** HbA1c's generating distribution
   matches the patient's already-generated diabetes label (§6, rule 2).
7. **Duplicate identifiers:** extend the existing
   `check_duplicate_ids`-style pattern to new record-type IDs
   (`diagnosis_id`, `lab_id`, `medication_id`) — uniqueness at minimum
   within one patient.
8. **Missingness:** every unpopulated new field has a documented reason
   in provenance, not silent absence (§6, rule 5).
9. **Unsupported combinations:** a lipid interpretation citing an
   undocumented `definition` value is rejected (§6, rule 6).

---

## Summary

This document formalizes the three human-approved architectural
decisions into a concrete design: lipids get a genuine raw-value-first
architecture (the clearest evidence-supported case); HbA1c gets a
*reversed*-direction application of the same principle (label-first,
conditional value); hypertension stays label-only pending BP-distribution
research that has never been conducted; and every other domain is
classified honestly rather than forced into a pattern the evidence
doesn't support. Nothing here is implemented — it is the blueprint for
M4's actual generation-code work.
