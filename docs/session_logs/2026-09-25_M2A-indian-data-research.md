# Session Log — 2026-09-25 — M2A: Indian Population Data Research

**Milestone hit:** M2A — Indian Population Data Research (research/
documentation-only checkpoint, per explicit user instruction).

## What was done

1. Read project context already established in this session
   (`docs/Claude.md`, `docs/PROJECT_STATE.md`, `docs/ROADMAP.md`,
   `docs/DECISIONS.md`, `docs/syngen-codebase-analysis.md`, the M1 session
   log, and the current `schemas/patient_schema.py`) — did not re-derive any
   of it, per the instruction not to repeat completed analysis.
2. Launched 4 parallel research forks (fork subagents, inheriting this
   session's context) to deep-research, with citations, in parallel:
   - ICMR-INDIAB
   - ICMR National NCD Monitoring Survey (NNMS)
   - India Human Development Survey (IHDS)
   - Up to 5 additional Indian datasets with concrete CV/demographic
     relevance
3. Synthesized all four forks' findings into a single deliverable:
   `docs/INDIAN_DATA_SOURCES.md` (19 sections, per the milestone's required
   structure: executive summary, project context, 3 mandated-dataset
   analyses, 5 additional datasets, comparison table, schema mapping,
   individual-vs-aggregate breakdown, access/licensing table, data
   quality/representativeness, freshness, compatibility concerns, proposed
   (not implemented) combination strategy, proposed dataset roles, explicit
   "what this milestone does not decide" section, open questions,
   recommended next research step, and full source list).

## Key findings worth flagging explicitly

- **Every health-survey dataset examined (ICMR-INDIAB, NNMS, NFHS-5, LASI)
  gates individual-level microdata** behind registration/request/query-
  approval — none offer a free direct download of row-level clinical data.
- **IHDS and the NSS 75th Round** are the only two datasets with openly
  downloadable individual-level microdata — but neither has strong direct
  cardiovascular clinical variables; their strength is socioeconomic/
  household context and healthcare-utilization behavior, respectively.
- **IHDS's (ICPSR) terms explicitly bar feeding its data to any LLM that
  retains or trains on it** (ChatGPT/Copilot/Gemini named as examples),
  characterized by ICPSR as a form of redistribution. This is directly
  relevant to this project's eventual generative-model integration stage
  and is called out as the report's top open question.
- **No dataset's license was found to explicitly address synthetic-data
  generation**, one way or the other, for any of the 8 sources researched —
  every instance is marked `Not verified` rather than assumed permitted.
- The India State-Level Disease Burden Initiative (GBD) is a modeled
  aggregate synthesis, not a primary survey — its correct role is
  validation/reference against a generated population, never a direct
  generation input, and using it alongside its own likely underlying input
  surveys (e.g., NFHS/INDIAB/NNMS) as independent calibration sources would
  double-count evidence.
- ICMR's CREATE/STEMI-ACT acute coronary syndrome registries are the only
  genuinely clinical-event (not risk-factor-survey) Indian sources found,
  but are the weakest on practical accessibility — no confirmed data-access
  path for CREATE, and STEMI-ACT's external-researcher access status is
  unresolved.

## What was reused (not rebuilt)

- All project context from this session (no re-audit of the repository or
  the syngen codebase).

## What was modified

- **Code: NONE.** `schemas/`, `integration/`, `validation/`, `tests/`,
  `ingestion/`, `configs/` were not touched.
- `docs/INDIAN_DATA_SOURCES.md` — created (the milestone's sole intended
  deliverable).
- This session log — created, per the standing instruction to write one
  after every milestone.
- `docs/PROJECT_STATE.md` and `docs/DECISIONS.md` were **deliberately left
  untouched** this session — M2A's instructions scoped the only repository
  modification to `docs/INDIAN_DATA_SOURCES.md`, and this is a research
  checkpoint, not an implementation milestone that changes project state.

## What was NOT done (explicitly out of scope for M2A)

- No dataset was selected as final.
- No schema changes.
- No generator/pipeline changes.
- No dependencies added.
- No datasets downloaded.
- No architecture changes.

## Blockers

None for the research itself. The report's top open question (whether
synthetic-data generation from any of these datasets is actually permitted)
is a prerequisite for any future implementation decision involving them —
flagged in the report, not resolved here.

## Next milestone

M2 (Stage 3 implementation): real synthetic demographic generation
(`docs/PROJECT_STATE.md`'s existing "Next Action"), independent of and not
blocked by M2A — M2A's findings inform Stage 10 (Indian demographic
conditioning), a later stage, not M2/M3's initial generation logic.
