# M4 — Clinical Generation Plan

Staged implementation plan for the clinical record layer designed in
`docs/CLINICAL_RECORD_DESIGN.md`. **Not implemented in M3.5** — this is
the plan M4 will execute, adjusted from the illustrative M4A-M4G template
based on what the design phase actually found (most notably: several
components are blocked on evidence that doesn't exist yet, so evidence
verification is pulled forward as its own stage rather than assumed
available when each component's turn comes).

---

## M4-0 — Evidence Verification (new stage, not in the original template)

**Objective:** resolve the evidence gaps `docs/CLINICAL_RECORD_DESIGN.md`
found before committing to any generation logic that would otherwise sit
idle waiting on a citation.

**Inputs:** `docs/CLINICAL_RECORD_DESIGN.md` §C/§F/§G's flagged gaps.

**Outputs:** a verification note per question, in the same
SUPPORTED/PARTIALLY SUPPORTED/NOT SUPPORTED style as M2C-0/M2D.

**Dependencies:** none — can start immediately.

**Evidence required (the questions themselves):**
1. What is ICMR-INDIAB's actual reported family-history-of-diabetes
   percentage? (Captured as a variable per M2A; percentage never located.)
2. Does an Indian standard-of-care/treatment-guideline source exist for
   hypertension/diabetes/hyperlipidemia drug classes (e.g., an ICMR
   guideline, or a WHO Essential Medicines List India adaptation)?
3. Are there Indian (or credibly-adaptable international, explicitly
   disclosed as such) lab reference ranges for fasting glucose and lipid
   panel components?
4. Can the anthropometrics tension (`docs/CLINICAL_RECORD_DESIGN.md` §A)
   be resolved with real Indian height/weight distribution evidence, or
   does it stay an engineering assumption?

**Tests required:** none (research stage).

**Validation required:** none (research stage).

**Human checkpoint:** report findings before M4A begins; if any answer is
NOT SUPPORTED, that component's stage below is scoped down accordingly
(matching `docs/CLINICAL_RECORD_DESIGN.md`'s own conclusions) rather than
proceeding with an invented number.

---

## M4A — Family History

**Objective:** implement the narrowest evidence-supported slice — at most
a single boolean (`family_history_of_diabetes`), only if M4-0 located a
citable percentage.

**Inputs:** M4-0's finding on question 1.

**Outputs:** `schemas/patient_schema.py` gains a minimal
`FamilyHistory` structure (additive — human review required per Step 9);
`configs/indian_population.yaml` gains the new parameter, with full
traceability metadata matching the existing pattern.

**Dependencies:** M4-0.

**Evidence required:** the specific INDIAB percentage (M4-0, question 1).
If not found: this stage produces **no generation change**, only the
schema field (left `null`), matching `docs/DECISIONS.md` D004's existing
treatment of family-history-of-CVD.

**Tests required:** presence check, boundary check (0-1 probability),
reproducibility check — same pattern as `tests/test_m2c_indian_conditioning.py`.

**Validation required:** structural (extend `validation/structural.py`).

**Human checkpoint:** schema change requires review before implementation
(Step 9's own rule), even though it's additive/low-risk, per this
project's established D005/D006 precedent.

---

## M4B — Medical History / Diagnoses (unified)

**Objective:** implement `docs/CLINICAL_RECORD_DESIGN.md` §D/§E's
"derive, don't duplicate" design — promote the three existing risk-factor
booleans into structured, dated diagnosis entries; leave cardiovascular-
event and procedure categories unpopulated (no evidence).

**Inputs:** `risk_factors.{hypertension,diabetes,hyperlipidemia}`
(already generated).

**Outputs:** `Diagnosis` dataclass instances derived 1:1 from existing
`True` risk-factor flags; `medical_history`'s "chronic condition" slice
mirrors the same facts (not re-generated).

**Dependencies:** none beyond existing M2C/M2D output — this is the
lowest-evidence-risk stage since it introduces no new prevalence claims.

**Evidence required:** none new for the derivation itself. The
`onset_date` generation rule is an **engineering assumption**
(e.g., uniform between some plausible minimum age and the patient's
current age) and must be labeled as such in provenance, not presented as
evidence-derived.

**Tests required:** confirm every `True` risk-factor flag produces
exactly one corresponding diagnosis entry (no duplication, no omission);
confirm no diagnosis exists for a `False`/`None` risk factor;
reproducibility.

**Validation required:** structural (new checks); a regression comparison
against the existing risk-factor prevalence (diagnosis prevalence must
exactly equal risk-factor prevalence, since it's derived, not resampled).

**Human checkpoint:** schema change (new `Diagnosis` type,
`Patient.diagnoses` gets real content) — review before implementation.

---

## M4C — Labs

**Objective:** implement glucose/lipid-panel values for patients with the
corresponding diagnosis, using M4-0's reference-range findings.

**Inputs:** M4B's diagnosis entries; M4-0's reference-range findings.

**Outputs:** `Lab` dataclass instances, values internally consistent with
diagnosis status (diabetic → glucose above threshold; non-diabetic →
below) via the engineering coherence rule from §G.

**Dependencies:** M4B (diagnoses must exist first), M4-0 (reference
ranges).

**Evidence required:** M4-0 question 3. If NOT SUPPORTED for
Indian-specific ranges: proceed only with international ranges,
explicitly disclosed as a limitation in provenance, not silently used as
if Indian-specific.

**Tests required:** value-vs-threshold coherence check per diagnosis
status; unit consistency; reproducibility.

**Validation required:** structural + a coherence-specific check (new).

**Human checkpoint:** none required if using already-disclosed
international ranges with the limitation stated; required if a new
external reference-range dataset would need introducing (Step 13's STOP
condition: "a new dataset is required").

---

## M4D — Medications

**Objective:** likely blocked; implement only what M4-0 supports.

**Inputs:** M4-0's findings (question 2); M4B's diagnoses.

**Outputs:** `Medication` dataclass, populated only if a citable Indian
(or explicitly-disclosed adapted-international) standard-of-care source
was found.

**Dependencies:** M4-0, M4B.

**Evidence required:** M4-0 question 2 — the entire chain (diagnosis →
drug class → medication → dates) needs this before any generation logic
is written, per `docs/CLINICAL_RECORD_DESIGN.md` §F.

**Tests required:** TBD, contingent on what evidence (if any) is found.

**Validation required:** TBD.

**Human checkpoint:** **required regardless of outcome** — even a
well-sourced drug-class mapping represents a new category of clinical
assumption this project hasn't made before (prescribing behavior, not
population prevalence), and per Step 13's STOP conditions ("you believe a
medically important relationship needs to be invented/assumed") this
should get explicit sign-off before implementation, not just before a
gap is found.

---

## M4E — Clinical Timeline

**Objective:** implement `docs/CLINICAL_RECORD_DESIGN.md` §H's
reference-based design — add `TimelineEvent.reference_id`, wire it to
diagnosis/lab/ECG IDs, generate a coherent chronological view.

**Inputs:** M4B (diagnoses), M4C (labs), existing ECG records.

**Outputs:** `TimelineEvent` gains `reference_id: Optional[str]`;
timeline entries generated for each dated record already produced by
earlier stages (not new content, an index over existing content).

**Dependencies:** M4B, M4C (whatever exists by this point — M4D may still
be blocked, and the timeline should degrade gracefully without it).

**Evidence required:** none new — pure engineering/structural work.

**Tests required:** every `reference_id` resolves to a real record;
timeline is chronologically sortable with no contradictions.

**Validation required:** the temporal-consistency rules from
`docs/CLINICAL_RECORD_DESIGN.md` §I, implemented as new
`validation/structural.py` checks (or a new `validation/temporal.py`
module, following the existing `structural.py`/`statistical.py` split
pattern).

**Human checkpoint:** schema change (`reference_id` field) — review
before implementation.

---

## M4F — Temporal Consistency Validation

**Objective:** implement §I's rules as reusable, generator-independent
checks (extending, not replacing, `validation/structural.py`'s pattern).

**Inputs:** M4B-M4E's generated dated fields.

**Outputs:** new validation functions; a `birth_date` field consideration
(§I flagged this as an open schema question, not decided) resolved one
way or the other, with reasoning recorded.

**Dependencies:** M4B-M4E.

**Evidence required:** none — this is pure consistency-rule engineering.

**Tests required:** each rule gets a positive case (valid record passes)
and a negative case (deliberately broken record is caught).

**Validation required:** this stage *is* validation.

**Human checkpoint:** none anticipated, unless a `birth_date` schema
addition is chosen (then: standard additive-schema review).

---

## M4G — Integrated Patient Validation

**Objective:** confirm the fully-assembled clinical-layer patient record
is internally coherent, structurally valid, and reproducible — at the
**same scale discipline** this project has followed throughout (10 → 100
→ 1,000, never jumping ahead).

**Inputs:** everything from M4A-M4F.

**Outputs:** a regression population (10, then 100, then 1,000 patients —
**not beyond**, matching M3's own scale), statistical/relationship
analysis in the same style as `docs/M3_DATA_QUALITY_REPORT.md`, and an
updated pattern inventory.

**Dependencies:** all prior M4 stages that were actually implemented (some
may remain blocked on evidence, e.g. M4D — that's an acceptable outcome,
not a failure of this plan).

**Evidence required:** none new — this is validation of what was built.

**Tests required:** full-suite regression (all M1-M3.5 tests plus every
new M4 test) must pass.

**Validation required:** structural + statistical + the new temporal
checks (M4F) + a relationship/dependency audit in the M3 style
(classify every new pairwise relationship EXPLICITLY MODELED /
INDEPENDENT BY DESIGN / etc., exactly as `docs/M3_PATTERN_INVENTORY.md`
did).

**Human checkpoint:** report results before any scale increase beyond
1,000, before any ECG waveform work, and before model selection — all
already-standing project rules, restated here so M4G doesn't silently
drift past them.

---

## Cross-Cutting Notes

- **Progressive scaling applies throughout M4**, not just at M4G — no
  stage should jump to 1,000 patients before 10/100 pass, mirroring
  `CLAUDE.md` §27's principle already followed in M1-M3.
- **Every new schema field is additive** (`Optional`, following the
  D005/D006/D007 pattern) — no stage in this plan proposes a breaking
  change.
- **Every stage with a human checkpoint is listed above explicitly** —
  M4 should not proceed past any of them without the review noted.
