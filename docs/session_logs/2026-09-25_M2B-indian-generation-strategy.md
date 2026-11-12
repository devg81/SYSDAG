# Session Log — 2026-09-25 — M2B: Indian Generation Strategy

**Milestone hit:** M2B — Indian Generation Strategy (design/research
checkpoint, no implementation, per explicit user instruction).

## What was done

Synthesized `docs/INDIAN_DATA_SOURCES.md` (M2A) plus this session's own M1
artifacts (`schemas/patient_schema.py`, `docs/DECISIONS.md`,
`docs/session_logs/2026-09-25_M1-foundation.md`) into a design document,
`docs/INDIAN_GENERATION_STRATEGY.md`, covering all 18 requested sections.
No new web research was performed — this was a pure synthesis/design task
using facts already gathered in M2A, per the instruction not to repeat
completed research.

## Key design decisions proposed (not implemented — all pending the M2C
human checkpoint)

- Classified each M2A dataset into a role: ICMR-INDIAB/NNMS/NFHS-5 as
  primary Calibration Sources (split by strength — clinical/behavioral/
  demographic respectively); LASI scoped to 45+ only; IHDS/NSS as deferred
  Contextual sources; GBD India as Validation-only; CREATE/STEMI-ACT as Not
  Used (inaccessible).
- Defined the minimum viable Indian-conditioning variable set: age, sex,
  BMI, smoking status, hypertension, diabetes, dyslipidemia (with a
  flagged sub-sample caveat) — all resolvable from already-public aggregate
  statistics. Explicitly excluded family history of CVD from the minimum
  set — no Indian source was found in M2A to support it, so it should be
  left unpopulated rather than invented.
- Distinguished marginal / simple stratified-conditional / documented
  multivariable association / full joint distribution as four separate
  evidentiary tiers, and stated plainly that only the first two (and
  cautiously the third, per-citation) are supported by M2A's findings — no
  full joint clinical-risk-factor distribution is claimed as available.
- Proposed a 14-step generation dependency graph (age → sex → [urban/rural]
  → BMI → smoking → hypertension → diabetes → dyslipidemia → family history
  → medical history/diagnoses → medications → labs → encounters/timeline →
  ECG/echo), with an explicit rationale for each ordering choice tied back
  to M2A evidence, not invented medical plausibility.
- Proposed a fallback hierarchy (published stratified stats → broader
  aggregate → public individual-level data for non-clinical fields →
  transparent assumption → documented limitation) so development doesn't
  depend on ever obtaining restricted ICMR/NFHS/LASI microdata.
- Proposed restricting the first implementation (M2C) to already-public
  aggregate statistics only, explicitly as a design rationale (not a legal
  conclusion) to sidestep the "does the license permit synthetic-data
  generation" question M2A left unresolved for every dataset.
- Schema gap analysis: classified `risk_factors`/`family_history`
  sub-field formalization as REQUIRED (additive, low-risk, still flagged
  as needing a human checkpoint per `CLAUDE.md` §28); `urban_rural` as
  USEFUL (strongest contextual candidate, given its outsized reported
  effect); `region`/`state` as USEFUL but weaker case; `socioeconomic_context`
  as OPTIONAL/deferred. No schema was actually changed.
- Proposed a minimal architecture:
  `configs/indian_population.yaml` → `generation/indian_calibration.py` →
  `integration/build_patient.py` (extended) → `schemas/patient_schema.py`
  (extended) → `validation/` (extended, reusing syngen's existing KS/KL
  distribution-comparison approach from `evaluate_class.py` rather than
  building new statistics). Placement under `generation/` follows the
  existing Candidate A architecture decision (`docs/DECISIONS.md` D001) and
  the `generation/`-isolation rule already in `CLAUDE.md` §4.
- Wrote a 9-step M2C implementation plan (M2C-0 definition verification
  through M2C-9 documentation/checkpoint), adjusted from the illustrative
  template based on this document's actual findings.

## Non-obvious finding surfaced during this milestone

While designing the generation dependency graph and representativeness
language, noticed and explicitly flagged that the project's only ECG source
so far (PTB-XL, established in M1) is a **German**, not Indian, population
dataset. Generating Indian-conditioned demographics/risk-factors next to a
non-Indian-sourced ECG is an internal-coherence gap in the eventual complete
patient record. This was not raised in M2A (out of its scope) or M1 (ECG
scope was metadata-only there); it's recorded here as an open question for
Stage 4/10, not resolved.

## What was reused (not rebuilt)

- All M2A findings (no re-research).
- M1's existing reproducibility pattern (`(sequence, seed)` determinism) as
  the model for the proposed calibration layer's determinism.
- `ml/interfaces.py`'s existing model-agnostic-contract pattern as the
  model for a proposed future `CalibrationSource` interface.
- syngen's existing `evaluate_class.py` KS/KL distribution-comparison
  statistics as the proposed basis for statistical validation, rather than
  designing new comparison statistics.

## What was modified

- **Code: NONE.** `schemas/`, `integration/`, `validation/`, `tests/`,
  `ingestion/`, `configs/` were not touched — verified via `git status`.
- `docs/INDIAN_GENERATION_STRATEGY.md` — created (the milestone's sole
  intended deliverable).
- This session log — created, per the standing per-milestone log
  instruction.
- `docs/PROJECT_STATE.md` and `docs/DECISIONS.md` were **deliberately left
  untouched**, consistent with how M2A was handled — this is a design
  checkpoint, not an implementation milestone that changes project state.

## What was NOT done (explicitly out of scope for M2B)

- No generator implementation.
- No schema modification (proposed only, pending human checkpoint).
- No new dependencies.
- No dataset downloads or integration.
- No ML training/fine-tuning/GAN/LLM generation/AWS infrastructure.
- No 100K (or any) generation run.

## Blockers

None for the design itself. Several items are explicitly `OPEN` in the
document (§17) and require a human decision before M2C can fully proceed —
most notably whether to adopt `urban_rural`/`region` in the schema, and
whether to populate or leave null `family_history.cvd`.

## Next milestone

M2C (implementation, pending human checkpoint on the schema questions
raised in §15/§17 of the strategy document): begin with M2C-0 (definition
verification) before encoding any numeric calibration parameter.
