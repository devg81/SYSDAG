# Synthetic Cardiovascular Patient Dataset & Generative System

## 1. PROJECT IDENTITY

This repository is being developed into a multimodal synthetic cardiovascular patient-record generation system.

The project has a 4–5 week development timeline.

The project is currently at the early implementation stage.

A detailed analysis of the existing codebase has already been completed. That analysis should be treated as an important source of context for implementation.

The project is NOT being built entirely from scratch.

The core principle is:

> REUSE → ADAPT → BUILD

Existing useful functionality should be reused wherever practical.

---

# 2. PROJECT VISION

## 2.1 Long-Term Objective

The primary objective is to generate approximately **100,000+ coherent synthetic cardiovascular patient records**.

These should not be simple randomly generated rows.

The intended records should represent complete synthetic patient histories containing multiple interconnected clinical components.

Depending on available datasets and generation capabilities, a patient record may contain:

* Demographics
* Cardiovascular risk factors
* Family history
* Medical history
* Diagnoses
* Medications
* Laboratory results
* Clinical encounters
* ECG
* Echocardiography
* Other investigations where appropriate
* Clinical timeline
* Provenance metadata
* Validation metadata

The synthetic records should be internally coherent and structured.

---

# 3. IMPORTANT: THE 100K DATASET IS NOT THE FINAL PRODUCT

The 100,000+ patient dataset is an intermediate foundation for the later stages of the project.

The intended overall pipeline is:

```text
Existing Code + Relevant Datasets
              ↓
Synthetic Patient Generation
              ↓
~100,000+ Complete Synthetic Medical Records
              ↓
Validation & Quality Control
              ↓
Pattern / Relationship Analysis
              ↓
Population-Level Pattern Discovery
              ↓
Indian Demographic Characteristics
              ↓
Selected Existing Generative Model
              ↓
Generate New Synthetic Patient Fields / Records
              ↓
Validation
```

The final objective is therefore not simply:

> "Generate 100,000 fake patients."

The intended objective is:

> Generate a large, coherent synthetic cardiovascular population, validate it, discover meaningful patterns from it, incorporate relevant Indian demographic characteristics, and eventually use a suitable existing generative model to generate new synthetic patient information.

Every major implementation decision should be evaluated against this end goal.

---

# 4. NOVELTY / INDIAN DEMOGRAPHIC DIRECTION

A key intended aspect of the project is the use of **Indian demographic characteristics and population-specific patterns** in the downstream generation process.

The intended conceptual flow is:

```text
Large synthetic cardiovascular population
                ↓
Validation
                ↓
Pattern discovery
                ↓
Indian demographic characteristics
                ↓
Selected generative model
                ↓
New synthetic patient fields / records
```

The project should NOT make unsupported claims that the synthetic dataset represents the Indian population.

Indian demographic characteristics and population-specific patterns must be based on the data and evidence available to the project.

Do not invent population-level relationships simply because they appear medically plausible.

Distinguish clearly between:

* Observed patterns
* Generated patterns
* Assumptions
* Rule-based relationships
* External evidence
* Model-generated relationships

---

# 5. EXISTING CODEBASE

## 5.1 Existing Analysis

A detailed codebase analysis has already been performed.

Do NOT repeatedly perform a full repository audit unless a concrete contradiction or new repository component requires investigation.

Use the existing analysis as the starting point.

The purpose of development is to build on top of the existing work.

---

# 6. KNOWN REUSABLE COMPONENTS

The existing project contains useful work related to areas including:

* PTB-XL dataset handling
* ECG metadata
* SCP/diagnostic label mapping
* ECG preprocessing
* ECG evaluation
* Stratified/fold handling
* Existing ECG generation/inference functionality

These components should be reused where technically compatible.

Do not rewrite working functionality simply because another implementation would look cleaner.

Before creating a new component:

1. Search the repository.
2. Identify existing functionality.
3. Determine whether it can be reused.
4. Adapt it if necessary.
5. Only build new functionality when required.

---

# 7. LEGACY GAN / SYSDAG CODE

The existence of legacy GAN/SysDaG-related code does NOT automatically mean it should become the foundation of the new architecture.

Treat it as an existing asset.

Reuse it only when:

* It works,
* It solves a current project requirement,
* It is compatible with the new architecture,
* And using it reduces rather than increases project overhead.

Do not force the new project architecture around legacy components.

---

# 8. CURRENT DATA CONTRACT — SCHEMA V0.2

Schema v0.2 is the current working patient-record data contract.

Do not casually redesign it.

The patient record conceptually contains:

```text
Patient
│
├── Patient metadata
│
├── Demographics
│
├── Risk factors
│
├── Family history
│
├── Medical history
│
├── Diagnoses
│
├── Medications
│
├── Labs
│
├── Encounters
│
├── ECG
│
├── Echo
│
├── Clinical timeline
│
├── Provenance
│
└── Validation metadata
```

The schema should remain extensible but should not become unnecessarily complicated.

If implementation reveals that Schema v0.2 is technically insufficient, document the problem before making a major change.

---

# 9. PATIENT RECORD PHILOSOPHY

The target is a **complete synthetic patient record**, not independent synthetic columns.

The following relationships should eventually be represented:

```text
Demographics
      ↓
Risk Factors
      ↓
Conditions / Diagnoses
      ↓
Medical History
      ↓
Medications
      ↓
Labs
      ↓
Investigations
      ↓
ECG / Echo
      ↓
Clinical Timeline
```

This does NOT mean every relationship must be hard-coded.

The goal is to avoid obviously independent random generation.

For example, the system should avoid producing records where clinically related fields are generated independently without considering their relationships.

---

# 10. SYNTHETIC DATA PRINCIPLE

All generated records must remain explicitly identifiable as synthetic.

Synthetic data must not be represented as real patient data.

Do not copy real patient identifiers into synthetic records.

Do not expose source patient identifiers unnecessarily.

Maintain provenance information so that we can determine:

* Which components were generated
* Which model generated them
* Which dataset influenced generation
* Which generation configuration was used
* Which validation version was used

---

# 11. PROJECT DEVELOPMENT PHASES

The project should progress through the following stages.

---

## STAGE 0 — PROJECT DEFINITION

Status:

COMPLETE

Completed:

* Project scope
* Long-term objective
* High-level architecture
* Schema direction
* Existing-code reuse strategy
* Model strategy
* Development strategy

---

# STAGE 1 — EXISTING CODEBASE UNDERSTANDING

Status:

COMPLETE

A detailed codebase analysis has already been performed.

Do not restart this stage unless required by new evidence.

---

# STAGE 2 — FOUNDATION

Status:

CURRENT

Objective:

Build the basic infrastructure around the existing codebase.

Components include:

* Formal machine-readable patient schema
* Patient data model
* Serialization
* Patient ID generation
* Basic validation
* Provenance tracking
* Clinical timeline representation
* Generation interfaces
* Existing ECG integration interface

### Stage 2 milestone

Generate:

```text
PAT_000001
```

as a structurally valid synthetic patient record.

The record should pass structural validation.

---

# STAGE 3 — PATIENT GENERATION

Objective:

Generate coherent synthetic patient attributes.

Potential fields:

* Demographics
* Risk factors
* Family history
* Medical history
* Diagnoses
* Medications
* Labs
* Encounters
* Clinical timeline

Initially, controlled distributions and rules may be used.

Do not claim that rule-based generation represents clinical reality unless validated.

### Milestone

Generate approximately:

```text
100 synthetic patients
```

and validate them.

---

# STAGE 4 — ECG / MULTIMODAL INTEGRATION

Objective:

Integrate the existing ECG functionality into the patient-generation pipeline.

Conceptually:

```text
Patient characteristics
        ↓
ECG generation request
        ↓
Existing ECG pipeline/model
        ↓
ECG output
        ↓
Patient record
```

The patient generator should interact with the ECG system through a clean integration interface.

Avoid coupling the patient generator to internal details of the ECG model.

### Milestone

Generate complete synthetic patient records containing valid ECG metadata and/or ECG signal outputs where supported.

---

# STAGE 5 — ADDITIONAL MODALITIES

Potential modalities include:

* Echocardiography
* Additional laboratory information
* Additional clinical investigations

Do not add modalities simply for the sake of completeness.

Each modality must have:

1. A usable source
2. A generation strategy
3. A representation in the patient schema
4. A validation strategy

If these are not available, leave the modality appropriately empty/null and document the limitation.

---

# STAGE 6 — VALIDATION

Validation is a major project component.

Validation should eventually include several layers.

## 6.1 Structural Validation

Check:

* Schema compliance
* Required fields
* Data types
* Allowed categorical values
* Valid dates
* Unique patient IDs
* Correct ECG metadata
* Correct provenance metadata

---

## 6.2 Statistical Validation

Check:

* Age distributions
* Sex distributions
* Risk-factor distributions
* Diagnosis distributions
* Medication distributions
* Lab distributions
* ECG distributions
* Missingness
* Outliers
* Duplicate/similar records

---

## 6.3 Temporal Validation

Check:

* Event ordering
* Diagnosis dates
* Medication start/stop dates
* Investigation dates
* Encounter dates
* Clinical timeline consistency

---

## 6.4 Logical Validation

Check for obvious contradictions.

Examples:

* Invalid combinations of dates
* Impossible medication states
* Contradictory event sequences
* Invalid demographic combinations
* Impossible values

Do not attempt to encode every possible medical rule manually.

---

## 6.5 Cross-Modal Validation

Where data availability allows, examine relationships between:

```text
Clinical information
        ↕
Labs
        ↕
ECG
        ↕
Echo
```

Cross-modal validation should identify obvious inconsistencies.

It should not be represented as a clinical diagnostic system.

---

# STAGE 7 — PROGRESSIVE SCALING

Never jump directly to 100,000 records.

Scale progressively:

```text
10
 ↓
100
 ↓
1,000
 ↓
10,000
 ↓
100,000+
```

Each scale should pass appropriate validation before moving to the next.

Measure:

* Generation time
* Throughput
* CPU usage
* GPU usage
* RAM usage
* Storage usage
* Failure rate
* Validation pass rate
* Duplicate rate
* Output size

---

# STAGE 8 — LARGE DATASET CREATION

Target:

```text
~100,000+ synthetic patient records
```

This stage should only begin after smaller-scale validation has passed.

The large dataset should have:

* Consistent schema
* Provenance
* Validation results
* Reproducibility information
* Generation configuration
* Dataset-level metadata

---

# STAGE 9 — PATTERN DISCOVERY

Once the large synthetic dataset has been validated, analyze it.

Potential analyses:

* Demographic distributions
* Risk-factor relationships
* Disease patterns
* Medication patterns
* Laboratory relationships
* ECG patterns
* Echo patterns
* Temporal relationships
* Combinations of cardiovascular conditions
* Missingness patterns
* Population clusters
* Correlations and dependencies

The analysis should distinguish:

```text
Observed in generated data
vs.
Assumed
vs.
Externally supported
```

Do not turn correlation into unsupported medical causation.

---

# STAGE 10 — INDIAN DEMOGRAPHIC CONDITIONING

After pattern analysis, incorporate relevant Indian demographic characteristics.

The exact conditioning mechanism is not yet finalized.

Potential conditioning variables may depend on:

* Available datasets
* Available demographic information
* External evidence
* Selected model capabilities

Do not assume that a variable should be used merely because it is available.

The conditioning strategy should be documented.

---

# STAGE 11 — GENERATIVE MODEL INTEGRATION

The project does NOT aim to train multiple models from scratch.

The preferred strategy is:

```text
Existing validated dataset
        +
Discovered patterns
        +
Indian demographic characteristics
        ↓
Existing suitable generative model
        ↓
New synthetic patient information
```

The current candidate is:

```text
CardioSynth / CardioSync
```

However:

**This is NOT a final architectural decision.**

The final model should be selected based on:

* Functional suitability
* Input compatibility
* Output compatibility
* Existing pretrained/inference capability
* Integration complexity
* Computational cost
* Fine-tuning requirements
* Ability to incorporate relevant patterns
* Ability to support the intended downstream generation task

Do not introduce multiple models unless they solve clearly different required problems.

---

# STAGE 12 — FINAL GENERATION PIPELINE

The intended final architecture is approximately:

```text
Indian demographic/context information
                 +
Relevant patient context
                 +
Validated population patterns
                 ↓
        Selected existing model
                 ↓
       Synthetic patient fields
        / synthetic records
                 ↓
             Validator
                 ↓
          Final output
```

The generated output must pass through validation.

The generative model must not bypass the validation layer.

---

# 12. MODEL DEVELOPMENT PHILOSOPHY

The project is NOT a model-development project in the traditional sense.

The objective is to minimize unnecessary ML engineering overhead.

Prefer:

* Existing pretrained models
* Existing inference pipelines
* Existing checkpoints
* Minimal integration
* Minimal fine-tuning
* Thin adapter layers

Avoid:

* Training four separate models
* Building models from scratch unnecessarily
* Fine-tuning models without a demonstrated need
* Maintaining a large model stack

A model should only be introduced if it fills a concrete capability gap.

---

# 13. MODEL DECISION PROCESS

Before integrating a new model, answer:

1. What exact problem does it solve?
2. What input does it require?
3. What output does it produce?
4. Do we already have another component that solves the same problem?
5. Does it require training?
6. Does it require fine-tuning?
7. What GPU/compute does it require?
8. What integration work is required?
9. Can the project proceed without it?
10. Does it improve the final project enough to justify its complexity?

If the answer to the last question is unclear, do not integrate it immediately.

---

# 14. COMPUTE STRATEGY

The project should use local hardware during development wherever practical.

Small-scale development, inference, testing, and generation should preferably run locally.

AWS should NOT be introduced simply because it is available.

Cloud infrastructure should only be introduced when there is a demonstrated need.

Potential reasons may include:

* Large-scale generation exceeds practical local runtime
* GPU memory limitations
* Parallel generation requirement
* Storage requirements
* Team access requirements
* Deployment requirements

Before using paid cloud infrastructure, estimate:

* Runtime
* GPU type
* Storage
* Data transfer
* Approximate cost

---

# 15. EXPENSIVE OPERATION POLICY

Do NOT automatically perform:

* Full model training
* Model fine-tuning
* Large dataset downloads
* 100K+ generation
* AWS deployment
* Large cloud GPU jobs
* Destructive migrations
* Deletion of large datasets/checkpoints

Small local tests and inference runs are allowed.

Before a significant expensive operation:

STOP.

Report:

* What will be run
* Why it is required
* Expected runtime
* Expected compute
* Expected storage
* Estimated cost if cloud is involved
* What milestone it enables

Wait for human approval.

---

# 16. AUTONOMOUS DEVELOPMENT LOOP

Claude Code should operate using a checkpoint-driven autonomous loop.

For each development cycle:

```text
READ STATE
    ↓
IDENTIFY NEXT MILESTONE
    ↓
INSPECT EXISTING CODE
    ↓
IMPLEMENT
    ↓
TEST
    ↓
EXECUTE
    ↓
INSPECT OUTPUT
    ↓
FIX
    ↓
RE-TEST
    ↓
VALIDATE
    ↓
DOCUMENT
    ↓
UPDATE PROJECT STATE
    ↓
SESSION LOG + GIT PUSH
    ↓
MOVE TO NEXT MILESTONE
```

Do not stop merely because code has been written.

---

# 17. READ PROJECT STATE FIRST

At the beginning of every autonomous cycle, read:

```text
docs/PROJECT_STATE.md
docs/ROADMAP.md
docs/DECISIONS.md
```

Determine:

* Current stage
* Current milestone
* Completed tasks
* Known blockers
* Next action

Do not assume the previous task is incomplete or complete without checking the state.

---

# 18. INSPECT BEFORE IMPLEMENTING

Before creating new code:

Search the repository.

Determine:

* Whether equivalent functionality exists
* Whether an existing utility can be reused
* Whether a model interface already exists
* Whether tests already exist
* Whether configuration already exists

Avoid duplicate implementations.

---

# 19. IMPLEMENT THE SMALLEST REQUIRED CHANGE

Do not implement speculative features.

Focus on the current milestone.

Avoid unnecessary refactoring.

Avoid changing unrelated code.

Avoid architecture changes unless they are required by concrete implementation evidence.

---

# 20. TEST AFTER IMPLEMENTATION

Run the relevant tests after changes.

If a test fails:

1. Diagnose the cause.
2. Fix the underlying problem.
3. Re-run the test.
4. Do not weaken the test simply to make it pass.

---

# 21. EXECUTE REAL PIPELINES

Whenever practical, run the actual relevant pipeline.

Do not consider a component complete because:

* It imports
* It compiles
* It passes a trivial unit test

Actual output should be generated where practical.

---

# 22. INSPECT ACTUAL OUTPUTS

Programmatically inspect generated outputs.

Depending on the component, inspect:

* File format
* Schema validity
* Dimensions
* Signal shape
* Value ranges
* Missing values
* IDs
* Dates
* Labels
* Relationships
* Provenance

If visualization already exists in the repository, use it where useful.

Do not introduce unnecessary visualization frameworks.

---

# 23. FIX-AND-RETEST LOOP

If the generated output is invalid:

```text
Diagnose
   ↓
Fix
   ↓
Test
   ↓
Generate
   ↓
Inspect
```

Repeat until:

* The milestone passes
* Or a genuine blocker is identified.

Do not hide errors.

Do not silently discard failed outputs without recording why.

---

# 24. DOCUMENTATION LOOP

After every meaningful development cycle, update:

```text
docs/PROJECT_STATE.md
```

Record:

* What was implemented
* What was reused
* What was modified
* What tests passed
* What outputs were generated
* Output locations
* Current limitations
* Current stage
* Current milestone
* Next action
* Blockers

## 24.1 Session Log (every session, mandatory)

Every session — including research, planning, decisions and Q&A sessions,
not only implementation — creates one file:

```text
docs/session_logs/YYYY-MM-DD_<milestone>-<short-topic>.md
```

Log everything: user requests, what was done, files changed, commands/tests
run and results, datasets generated or modified (path, size, record count,
seed, config), decisions taken, open questions, roadmap/next steps, and the
git commit hash pushed (§37.1). Then commit and push.

---

# 25. ARCHITECTURAL DECISIONS

When an important architectural decision is made, record it in:

```text
docs/DECISIONS.md
```

Include:

* Decision
* Reason
* Alternatives considered
* Consequences

Do not repeatedly revisit decisions that have already been documented unless new evidence invalidates them.

---

# 26. MILESTONE COMPLETION RULE

A milestone is NOT complete because implementation exists.

A milestone is complete only when:

```text
IMPLEMENTED
     ↓
TESTED
     ↓
EXECUTED
     ↓
OUTPUT INSPECTED
     ↓
VALIDATED
     ↓
DOCUMENTED
```

Only then update the milestone status to COMPLETE.

---

# 27. PROGRESSIVE DATA GENERATION

For dataset generation, always use:

```text
10
 ↓
100
 ↓
1,000
 ↓
10,000
 ↓
100,000+
```

At each stage evaluate:

* Validity
* Failure rate
* Duplicate rate
* Distribution quality
* Runtime
* Resource usage
* Storage
* Output integrity

Do not scale because the code "should work."

Scale because the previous level demonstrated that it works.

---

# 28. HUMAN CHECKPOINTS

Claude should operate autonomously for routine work.

However, stop when a human decision is materially required.

Examples:

### Model selection

Multiple suitable models require architectural choice.

### New dataset

A new external dataset needs to be selected or downloaded.

### Major schema change

Schema v0.2 requires significant restructuring.

### Expensive computation

Large-scale GPU work is required.

### Cloud infrastructure

AWS would incur meaningful cost.

### Destructive operation

Data/code deletion or irreversible migration is required.

### Major architecture change

A decision would significantly alter the project direction.

---

# 29. HUMAN CHECKPOINT FORMAT

When stopping for a human checkpoint, report:

```text
CURRENT STAGE:
...

CURRENT MILESTONE:
...

COMPLETED:
...

EVIDENCE:
...

TESTS:
...

OUTPUTS:
...

BLOCKER / DECISION:
...

OPTIONS:
...

RECOMMENDED NEXT STEP:
...
```

Do not silently make a major architectural decision.

---

# 30. FAILURE HANDLING

If implementation fails:

1. Diagnose.
2. Attempt a reasonable local fix.
3. Test again.
4. Inspect logs/output.
5. Try an alternative implementation if appropriate.
6. Document the failure if unresolved.

If repeated attempts fail:

STOP.

Do not create increasingly complicated workarounds without understanding the underlying problem.

---

# 31. SECURITY / DATA SAFETY

Do not:

* Commit secrets
* Commit API keys
* Commit credentials
* Expose private patient information
* Copy real patient identifiers into synthetic records
* Upload sensitive data unnecessarily

Use environment variables/configuration for credentials.

---

# 32. REPRODUCIBILITY

Where practical, record:

* Random seeds
* Generation configuration
* Model version
* Dataset version
* Code version/commit
* Schema version
* Validation version

A generated dataset should be reproducible as far as technically possible.

---

# 33. EXPERIMENT TRACKING

For meaningful experiments, record:

* Experiment ID
* Date
* Configuration
* Dataset
* Model
* Parameters
* Output location
* Results
* Notes

Do not rely on memory.

---

# 34. CODE QUALITY

Prioritize:

* Clear naming
* Small modules
* Reusable interfaces
* Type safety where practical
* Tests
* Logging
* Configuration over hard-coded values

Avoid:

* Giant scripts
* Hard-coded paths
* Hidden global state
* Duplicated logic
* Unnecessary abstraction
* Premature optimization

---

# 35. DIRECTORY ORGANIZATION

Prefer a structure similar to:

```text
project/
│
├── CLAUDE.md
│
├── docs/
│   ├── PROJECT_STATE.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   └── existing_analysis.md
│
├── schemas/
│   └── patient_schema.json
│
├── src/
│   ├── patient/
│   ├── generation/
│   ├── validation/
│   ├── ecg/
│   ├── echo/
│   ├── timeline/
│   ├── provenance/
│   └── analysis/
│
├── tests/
│
├── configs/
│
├── scripts/
│
├── data/
│
└── outputs/
```

Do not reorganize the entire existing repository merely to match this structure.

Adapt the existing structure where practical.

---

# 36. OUTPUT ORGANIZATION

Keep generated outputs separate from source code.

Prefer:

```text
outputs/
├── test/
├── validation/
├── datasets/
├── reports/
└── experiments/
```

Large generated datasets should not be accidentally committed to Git.

---

# 37. GIT / VERSION CONTROL

Make changes in logical increments.

Prefer meaningful commits such as:

```text
feat: add patient schema validation
feat: add synthetic patient generator
feat: integrate ECG inference
test: add patient validation tests
docs: update project state
```

Do not create huge meaningless commits containing unrelated changes.

## 37.1 Push Every Session to GitHub

Remote: `https://github.com/devg81/SYSDAG` (branch `main`, private).

At the end of EVERY session (after the session log in §24.1 is written):

1. `git status` — review what changed.
2. Commit everything except what `.gitignore` excludes: code, tests, configs,
   schemas, docs, roadmap/next-steps notes, decisions, session logs, reports,
   validation summaries and dataset metadata/reports.
3. `git push origin main`.
4. State the commit hash in the session log and in the final reply.

Never commit (kept out via `.gitignore`):

* Secrets: `.env*`, keys, tokens, credentials.
* Full generated datasets under `outputs/` (100K+ JSON records — too large;
  regenerate from code + seed + config). Their *reports and summaries* in
  `docs/` ARE committed.
* Downloaded third-party datasets (PTB-XL) and model weights (`*.pt`,
  checkpoints) — re-downloadable / license-restricted.
* Office lock files (`~$*`), caches.

If a new file appears that must NOT go to GitHub, add it to `.gitignore` and
tell the user explicitly, naming the file and why.

---

# 38. WHAT NOT TO DO

Do NOT:

* Restart the repository analysis unnecessarily
* Rewrite the entire existing codebase
* Replace working ECG functionality without reason
* Train multiple models without justification
* Fine-tune models prematurely
* Generate 100K records immediately
* Add AWS before demonstrating a need
* Add external models merely because they exist
* Over-engineer the schema
* Treat synthetic data as real clinical data
* Claim clinical validity without validation
* Turn correlations into causal medical claims
* Hide failed experiments
* Silently make major architectural decisions

---

# 39. CURRENT PROJECT MILESTONES

The high-level milestones are:

```text
M1  — Foundation
      ↓
M2  — One valid patient
      ↓
M3  — 100 patients
      ↓
M4  — ECG integration
      ↓
M5  — Multimodal patient
      ↓
M6  — Validation framework
      ↓
M7  — 1,000 patients
      ↓
M8  — 10,000 patients
      ↓
M9  — 100,000+ patients
      ↓
M10 — Pattern discovery
      ↓
M11 — Indian demographic conditioning
      ↓
M12 — Generative model selection
      ↓
M13 — Model integration
      ↓
M14 — Final generation pipeline
      ↓
M15 — Final validation & documentation
```

The exact ordering may change if implementation evidence requires it.

Any deviation should be documented.

---

# 40. FINAL OPERATING PRINCIPLE

The project should always move through:

```text
UNDERSTAND
    ↓
REUSE
    ↓
IMPLEMENT
    ↓
TEST
    ↓
EXECUTE
    ↓
INSPECT
    ↓
VALIDATE
    ↓
DOCUMENT
    ↓
SCALE
```

Do not optimize for writing the maximum amount of code.

Optimize for:

> **WORKING → TESTED → VALIDATED → REPRODUCIBLE → DOCUMENTED**

---

# 41. AUTONOMOUS LOOP COMMAND

When the user asks to continue autonomous development, execute the following process:

```text
1. Read CLAUDE.md.
2. Read PROJECT_STATE.md.
3. Read ROADMAP.md.
4. Read DECISIONS.md.
5. Identify the current milestone.
6. Inspect existing implementation.
7. Implement the smallest required change.
8. Test it.
9. Execute the relevant pipeline.
10. Inspect actual outputs.
11. Fix failures.
12. Re-test.
13. Validate.
14. Update PROJECT_STATE.md.
15. Update DECISIONS.md if required.
16. Determine whether the next milestone can begin.
17. Continue until a human checkpoint or expensive operation is reached.
18. Write the session log (§24.1).
19. Commit and push everything to GitHub (§37.1); report the commit hash.
```

Routine implementation should not require user confirmation.

Strategic decisions and expensive operations do.

---

# 42. FINAL PROJECT SUCCESS CRITERIA

The project is ultimately successful when we have:

### Dataset

Approximately 100,000+ coherent synthetic cardiovascular patient records.

### Validation

A documented validation framework demonstrating structural, statistical, temporal, logical, and where possible cross-modal quality.

### Pattern Analysis

A documented analysis of relationships and patterns within the generated population.

### Indian Demographic Layer

A documented approach for incorporating relevant Indian demographic characteristics.

### Generative Model

A suitable existing generative model integrated with minimal unnecessary overhead.

### Final Pipeline

A reproducible pipeline capable of:

```text
Patient demographic/context input
          ↓
Relevant learned/discovered patterns
          ↓
Selected existing model
          ↓
Synthetic patient information
          ↓
Validation
          ↓
Final output
```

### Documentation

The complete system should be understandable and reproducible by another developer.

---

# END OF CLAUDE.md
