# SysDaG — Claude Code Project Instructions

> **Detailed reference:** `docs/superpowers/specs/2026-09-19-multimodal-cardio-dataset-spec-design.md`
> (also delivered as `docs/SysDaG_Project_Spec_2026-09-19.docx`) is the authoritative,
> detailed project spec — requirements, reuse status, structure candidates, design,
> stage plan, and open questions. This file stays the concise day-to-day operating
> instructions; when the two would conflict on project facts (scope, structure,
> stage plan), the spec wins and this file should be updated to match.

## 1. Project Context

SysDaG is expanding from synthetic 12-lead ECG generation (PTB-XL) into a
**patient-centric, multimodal synthetic cardiovascular dataset**: approximately
100,000 synthetic patients/records, each connected through one canonical
`patient_id` across demographics, risk factors, family history, medical history,
diagnoses, medications, labs, ECG, echo, and clinical timeline. See the spec's
Section 2 for the full modality requirements table — several modalities (echo
scope, longitudinal vs. snapshot, mandatory list beyond ECG) are still open
questions (spec Section 7), not settled requirements.

Development timeline: approximately 4–5 weeks.

Current phase: Stage 0–1.

The project is being developed in parallel:
- Audit existing code and datasets.
- Reuse working components wherever possible.
- Build downstream/model-independent infrastructure early.
- Avoid blocking foundational work on final generator/model decisions.

The primary goal is to produce a reproducible, validated and extensible pipeline rather than a collection of disconnected scripts.

---

## 2. Current Data / Existing Assets

These are the **ECG-modality** assets established by the prior SysDaG work. They
are not the whole project's data — other modalities (labs, medications, family
history, echo, clinical timeline) have no established source yet; see the spec's
Section 3.2 for the coverage gap and Section 3.1 for the per-item reuse status
(DIRECT REUSE / REUSE-VERIFY / KEEP).

- PTB-XL / WFDB pipeline
- `ptbxl_database.csv`
- `scp_statements.csv`
- 12-lead ECG data
- ECG representation: 100 Hz, approximately `(1000, 12)`
- Patient-level dataset folds:
  - 1–8 → training
  - 9 → validation
  - 10 → test
- Multi-label diagnostic mapping
- Existing PyTorch infrastructure
- ECG evaluation / metrics infrastructure

Known findings to carry forward when working with this data (spec Section 3.4):
~40% of ECG records carry more than one diagnostic superclass (a single-label
assumption is unsafe), class imbalance is significant (notably hypertrophy), and
age values above 89 are encoded anomalies (prior work clipped them to 89).

Do NOT duplicate existing functionality without first checking whether it can be reused.

---

## 3. Development Principles

### Reuse before rebuild

Before implementing a new component:

1. Search the repository.
2. Identify existing implementations.
3. Determine whether they can be reused or adapted.
4. Only create a new implementation when necessary.

Prefer:
- small reusable modules
- clear interfaces
- configuration-driven behavior
- testable functions
- reproducible experiments

Avoid:
- giant scripts
- hard-coded paths
- duplicated logic
- hidden global state
- unnecessary dependencies

---

## 4. Architecture Direction

Keep foundational components independent of the final synthetic-data generator.

Important model-independent components include:

- patient schema / data model
- data ingestion interfaces
- canonical patient-ID integration
- YAML configuration
- generator-independent validation
- dataset export
- experiment logging
- testing

The `generation/` layer should remain isolated from the rest of the pipeline.

Generator-specific implementation should not leak into ingestion, validation, schema or export code.

---

## 5. Repository Structure

**Open — not finalized.** This is one candidate structure (Candidate A in the
spec's Section 4), kept here as the working default because it's what the
codebase currently follows. A second candidate (`src/`-nested, with a top-level
`data/` directory) comes from the Master Project Plan; the `ml/` layer created
during Stage 0 prep is structure-neutral and fits either. The decision is
deferred to the Stage 0 audit (spec Section 8, item 4) — resolve it against
whatever layout the arriving original codebase already assumes, then update
this section to match.

Working default structure:

schemas/
    patient schemas and canonical data definitions

ingestion/
    source-data loading and preprocessing

integration/
    patient-ID and cross-source integration

validation/
    data-quality and consistency validation

export/
    dataset generation/export utilities

generation/
    synthetic-data generators

tests/
    unit/integration tests

configs/
    YAML configuration files

experiments/
    experiment metadata/results

docs/
    technical documentation

---

## 6. Configuration

Avoid hard-coding:

- dataset paths
- patient IDs
- random seeds
- model parameters
- output directories
- experiment settings

Use YAML configuration where practical.

Example:

configs/
    base.yaml
    development.yaml
    experiment_01.yaml

---

## 7. Data Integrity Rules

Patient identity must be handled consistently.

Never introduce accidental patient leakage between:

- train
- validation
- test

Respect the existing patient-level folds.

Do not randomly split ECG records when a patient-level split is required.

Validation should check:

- missing values
- duplicate patient IDs
- invalid identifiers
- inconsistent dimensions
- invalid labels
- train/validation/test leakage
- malformed ECG records
- unexpected data distributions

---

## 8. Testing Rules

Every significant new component should have tests.

Prioritize tests for:

- schema validation
- ingestion
- patient-ID handling
- preprocessing
- validation
- dataset export
- metric calculations

Before considering a feature complete:

1. Run relevant tests.
2. Check existing functionality.
3. Check edge cases.
4. Check that no train/test leakage was introduced.

---

## 9. Experiment Reproducibility

Experiments should record:

- configuration
- random seed
- dataset/version
- code version/commit where practical
- model/generator configuration
- evaluation metrics
- output location

Do not rely on undocumented manual steps.

---

## 10. Coding Style

Prefer readable Python.

Use:

- type hints where useful
- descriptive names
- docstrings for important public functions
- small functions
- explicit interfaces
- meaningful exceptions

Do not over-engineer simple functionality.

---

## 11. Claude Code Workflow

Before making substantial changes:

1. Inspect the repository.
2. Understand existing implementation.
3. Identify dependencies.
4. Create a short implementation plan.
5. Implement incrementally.
6. Run tests.
7. Review the diff.
8. Fix issues.
9. Summarize what changed.

Do not immediately start writing code when the task requires repository-wide understanding.

---

## 12. Plugin Usage

### Superpowers

Use Superpowers for:
- brainstorming
- implementation planning
- complex debugging
- TDD
- multi-step development tasks

Prefer planning before substantial implementation.

### Ponytail

Use Ponytail for:
- agent orchestration
- parallelizable development/research tasks
- coordinating independent subtasks

Do not parallelize tasks that modify the same files unless conflicts are explicitly managed.

### Context7

Use current documentation when:
- implementing external libraries
- using APIs
- dealing with version-sensitive behavior
- uncertain about current library syntax

Prefer official documentation when available.

### Code Review

After substantial implementation:
- review the diff
- look for bugs
- check project conventions
- check tests
- check unintended changes

### Security

Before major releases or when handling external/untrusted input:
- perform a security review
- check secrets
- check unsafe file/network operations
- check dependency usage

---

## 13. Stage Discipline

The project currently uses staged development.

At every stage:

- clearly identify the objective
- document completed work
- document unresolved issues
- identify dependencies on future stages

Do not prematurely lock in generator-specific decisions.

Build interfaces early where later stages are expected to depend on them.

---

## 14. Important Rule

When uncertain:

DO NOT invent project requirements.

Instead:

1. Inspect existing code/documentation.
2. Look for project decisions already made.
3. Identify assumptions explicitly.
4. Ask for clarification when the decision materially affects architecture.

Maintain compatibility with existing working code whenever possible.

---

## 15. Definition of Done

A feature is not considered complete merely because the code runs once.

Consider it complete when:

- implementation is integrated
- relevant tests pass
- existing functionality still works
- configuration is reproducible
- documentation is updated when necessary
- no obvious data leakage/integrity issue exists
- the Git diff contains only intended changes