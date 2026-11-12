# Session Log — 2026-09-26 — M4-0B: Clinical Variable Architecture Decision

**Milestone hit:** M4-0B — Clinical Variable Architecture Decision
(COMPLETE, design/documentation only).

## Objective

Convert the three human-authoritative decisions (dyslipidemia
representation, LDL generation order, project-wide raw→derived
principle) into a formal M4 architecture. No code, schema, or generator
change.

## Human Decisions Applied

Recorded exactly as given: (1) continuous LDL/HDL/TG/TC is primary data;
multiple documented definitions derive tagged labels from it, none
treated as universal truth. (2) Generate the raw LDL value first, derive
interpretations afterward — never independently generate LDL and
hyperlipidemia as unrelated variables. (3) Apply
`raw value → derived interpretation` project-wide wherever evidence
supports it, not by force. Recorded as `docs/DECISIONS.md` D011.

## Method

Read `schemas/patient_schema.py` directly (confirmed unchanged since
M3.5/M4-0/M4-0A) plus all listed context documents — all already current
in this session, no re-research needed. This was a pure architecture-
design exercise applying already-gathered evidence, not a new research
pass.

## Key Design Outcomes

1. **Lipid architecture** (`docs/M4_CLINICAL_ARCHITECTURE.md` §2): a
   `LipidPanel` (raw LDL/HDL/TG/TC, mg/dL) plus a list of tagged
   `LipidInterpretation` entries (one per definition: NCEP_ATP_III,
   LAI_2020, etc.), each computed — never independently sampled — from
   the raw values against a small, citable reference-definition table.
   This directly resolves the M4-0A ambiguity by design: a consumer
   always knows which guideline produced any given label.
2. **HbA1c — a genuine refinement, not a contradiction, of Decision 3**
   (§3): the diabetes label is already this project's most
   evidence-backed variable; HbA1c should be generated *conditionally
   on* that label (NGT-population evidence for non-diabetics, thin data
   for diabetics), not the other way around. This is exactly the kind of
   evidence-driven exception Decision 3 itself anticipated ("must not
   force this pattern where evidence does not support it") — reported
   as a finding, not treated as a human-checkpoint contradiction, per
   this milestone's own instruction on when to stop.
3. **Hypertension stays label-only** (§4): no BP continuous-distribution
   research has ever been conducted by this project — explicitly marked
   future research, not invented to satisfy the general principle.
4. **Full schema audit table** (§1) and per-domain A/B/C/D
   classification (§5) covering every current and planned clinical
   field.
5. **Consistency rules** (§6) — the strongest one is architectural, not
   just a validation check: computing (not sampling) lipid
   interpretations makes the "LDL=85, hyperlipidemia=true under a
   definition where 85 doesn't qualify" contradiction structurally
   impossible, with a validation check as defense-in-depth on top.
6. **Generation dependency graph** (§9) updated to insert the raw-lipid
   → interpretation → diagnosis chain, and to place HbA1c generation
   after (not before) the diabetes label, reflecting finding #2.
7. **Schema-change classification** (§8): lipid/HbA1c/reference-
   definition schema additions marked READY FOR M4 IMPLEMENTATION on the
   basis that this session's decisions already constitute their human
   checkpoint — no second sign-off needed before mechanical
   implementation. Several other items (BP fields, `TimelineEvent.
   reference_id`, `birth_date`, family history structure) remain
   REQUIRES HUMAN DECISION or NEEDS MORE EVIDENCE, explicitly not
   resolved by this session's narrower, lipid-focused decisions.

## No Contradiction Found

Per this milestone's instruction to STOP and report if a direct
contradiction in existing project evidence was discovered: none was.
The HbA1c reversed-direction finding is a correct, anticipated
*application* of Decision 3, not a conflict with it.

## Files Created/Modified

**Created:** `docs/M4_CLINICAL_ARCHITECTURE.md`, this session log.
**Modified:** `docs/DECISIONS.md` (D011, finalized — unlike M4-0A's
proposals, this session's decisions were explicitly authoritative and
final, per the user's framing).
**Not modified:** `schemas/`, `generation/`, `integration/`,
`validation/`, `configs/` — no code or schema change, per instructions.

## Tests

No code was changed. Existing test suite unaffected — see the tool-call
record for this session's confirmation run.

## Recommendation

M4 can now implement the `LipidPanel`/`LipidInterpretation` schema
addition and the HbA1c (NGT-conditioned) field without a further
architecture checkpoint, since D011 already constitutes that sign-off.
Before generation *logic* is written, M4C should still resolve the
practical question of how to reconstruct raw LDL/HDL/TG/TC values from
category-level evidence only (the same engineering-reconstruction
problem BMI already solved) — this document designs the *shape*, not the
*sampling method*, which remains M4's implementation work.
