# SysDaG — Synthetic Multimodal Cardiovascular Patient Dataset: Project Spec

**Status:** New source of truth for project requirements/design (supersedes the two source reports as the working reference; `Claude.md` is being amended to align with it).
**Date:** 2026-09-19
**Sources:** `Synthetic_Cardiovascular_Project_Stage_0_Audit.docx` ("Stage 0 Audit"), `Synthetic_Multimodal_Cardiovascular_Patient_Dataset_Master_Project_Plan.docx` ("Master Plan"), and `Claude.md` (existing project instructions) as they stood before this spec.

---

## 1. Executive Summary

The project is expanding from its prior scope — synthetic 12-lead ECG generation from PTB-XL — into a **patient-centric, multimodal synthetic cardiovascular dataset**: approximately 100,000 synthetic patients/records, each connected through one canonical `patient_id` across demographics, risk factors, family history, medical history, diagnoses, medications, labs, ECG, echo, and clinical timeline.

The prior SysDaG work (ECG pipeline, GAN experiments, evaluation metrics) is a **reusable technical foundation for the ECG modality**, not the architecture for the whole project. The previous GAN roadmap (five separate vanilla GANs, one per diagnostic subclass) is explicitly **not** being carried forward as the new default.

Timeline: 4–5 weeks. Working sequence: **Audit → Reuse → Build Foundation → Integrate → Validate → Scale → Analyze**, run in parallel rather than sequentially gated — foundation components that don't depend on the final generator choice can be built now.

The original SysDaG codebase referenced throughout this spec is **not yet available** (expected Monday). Nothing in this spec should be read as authorizing implementation of dataset loading, preprocessing, model, or generation code before that audit happens — see `ml/TODO.md` Phase A and Section 8 below.

---

## 2. Project Requirements

### 2.1 Scope

Not limited to ECG. Target modalities per patient:

| Modality | Status |
|---|---|
| Demographics (age, sex) | Required |
| Cardiovascular risk factors (hypertension, diabetes, BMI, smoking, family history of CVD, hyperlipidemia) | Required (initial schema) |
| Family history | Candidate |
| Medical history (prior diagnoses, cardiovascular events, procedures, chronic conditions) | Candidate |
| Diagnoses (hypertension, diabetes, CAD, MI, arrhythmia, heart failure, other CV conditions) | Required — ontology to finalize |
| Medications (name, class, start/stop dates, current status) | Candidate |
| Laboratory data (glucose, HbA1c, cholesterol, LDL, HDL, triglycerides, creatinine, etc.) | Candidate |
| ECG (ecg_id, sampling rate, duration, 12-lead signal, diagnostic metadata) | Core modality — established from prior work |
| Echo (structured measurements, physiological attributes, or images) | Open decision — scope not yet fixed |
| Clinical timeline (encounters, diagnoses, investigations, labs, medications, ECG, follow-up) | Optional / open |

A patient is the parent object. All modalities for `patient_000123` must describe the *same* synthetic patient — not be generated independently and randomly combined.

### 2.2 Core Principle

> Do not build what we do not yet understand. Build the foundation that is known to be required, keep the generation layer modular, and validate every scale-up.

### 2.3 What should NOT happen

1. Building everything from scratch when reusable technical work already exists.
2. Training four or five independent models without a demonstrated need.
3. Starting at 100K instead of validating at smaller scales (1K → 10K → 100K).
4. Hard-coding CardioSynth (or any one framework) throughout the codebase.
5. Building infrastructure before the required output is understood.
6. Using synthetic data to validate synthetic data when held-out real data, independent reference distributions, clinical constraints, or downstream utility tests are available instead.

### 2.4 Success Criteria (currently known — see Section 7 for what's still unresolved)

Concrete thresholds are **not yet defined** for distribution similarity, ECG quality, diversity, duplicate rate, clinical consistency, downstream utility, missingness, or privacy. This is an open question (Section 7, Q13) and must not be assumed.

---

## 3. Existing Assets & Reuse Status (from the Stage 0 Audit)

### 3.1 What the prior SysDaG work established

Source: the uploaded March 2025 SysDaG Monthly Project Completion Report — a healthcare synthetic-data project focused on PTB-XL ECG generation, documenting the existing data pipeline, GAN architecture, evaluation work, challenges, and future plans.

| Area | Established by prior SysDaG work | Reuse status |
|---|---|---|
| PTB-XL structure | 21,799 records / 18,869 patients; 12-lead ECG; 100 Hz and 500 Hz representations; 10-second recordings | KEEP |
| Signal loading | WFDB-based loading of `.dat`/`.hea` files into 1000×12 arrays | DIRECT REUSE |
| Metadata mapping | `ecg_id`, `patient_id`, `scp_codes`, `filename_lr`, `strat_fold`, `age`, `sex`, quality flags, pacemaker fields | DIRECT REUSE |
| Diagnostic labels | SCP-ECG diagnostic codes mapped to five superclasses: NORM, MI, STTC, CD, HYP | DIRECT REUSE |
| Patient-level splitting | Folds 1–8 training, 9 validation, 10 test; patients do not cross folds | DIRECT REUSE |
| Multi-label handling | Sigmoid/BCE strategy — records can carry multiple diagnostic superclasses | REUSE / VERIFY |
| ECG normalization | Per-lead z-score normalization, clipped to [-1, +1] | REUSE / VERIFY |
| Quality evaluation | Variance, mean difference, std-dev difference, KS statistic, KL divergence, MSE | REUSE AS BASELINE |
| Downstream utility | Real-only fold 10 proposed as ground-truth evaluation set for synthetic-data utility | KEEP |

### 3.2 Coverage gap (what the ECG-era work does NOT cover)

| Component | Coverage | Implication |
|---|---|---|
| ECG waveform / diagnostic labels | Strong | Becomes the ECG layer; supports CV conditioning and validation |
| Demographics attached to ECG | Partial (in PTB-XL) | Not sufficient as a standalone population model |
| Longitudinal patient history | Not established | Must be added via another source/system |
| Medications / encounters | Not established | New requirement |
| Laboratory data | Not established | New requirement |
| Family history | Not established | New requirement |
| Echocardiography | Not established | New modality to source/evaluate |
| Multimodal patient integration | Not established | Major new engineering layer |
| ~100K complete patients | Not established | Future scale target, not an existing capability |

### 3.3 Model-work reuse decisions

| Previous direction | Decision | Reason |
|---|---|---|
| Five separate Vanilla GANs | Do not adopt as new default | Phase-1 design; multi-model training/maintenance overhead |
| WGAN / WGAN-GP upgrade | Keep as prior experimental knowledge | Useful if an in-house ECG generator is eventually needed |
| Conditional GAN | Keep as fallback | Test whether an existing framework removes this burden first |
| PDE-GAN | Defer | Identified as future work in the source report; not needed for Stage 0 |
| Existing ECG quality metrics | Adopt | Provides a starting validation framework |
| Real-only test fold | Adopt | Protects evaluation integrity — synthetic data is not used as test truth |

### 3.4 Findings to carry forward

- ~40% of ECG records carry more than one diagnostic superclass — a single-label assumption is unsafe for the ECG layer.
- Sparse diagnostic subclasses can make subclass-level GAN training unreliable.
- Class imbalance was significant, particularly for hypertrophy.
- Vanilla GAN mode collapse is a real risk; variance monitoring was used as a diagnostic.
- Generated ECGs matched broad amplitude statistics reasonably, but beat morphology (QRS/T-wave shape) remained imperfect — a known morphology gap.
- Age values above 89 are encoded anomalies; the prior work proposed clipping to 89.

### 3.5 Decision gate

**No new model should be trained at Stage 0.** The generation architecture decision comes only after the source-to-field audit (Section 6, Stage 0). Existing work should be reused wherever it reduces engineering effort; external/pre-existing frameworks should be preferred over new custom models where they remove a multi-model maintenance burden without a demonstrated need for custom training.

---

## 4. Structure & Dependencies (Open — pending Monday's audit)

Per your decision, the repository structure is **intentionally left open** rather than fixed by this spec. Three descriptions exist and are not yet reconciled:

### 4.1 Candidate A — `Claude.md`'s current structure (flat, root-level)

```
schemas/       patient schemas and canonical data definitions
ingestion/     source-data loading and preprocessing
integration/   patient-ID and cross-source integration
validation/    data-quality and consistency validation
export/        dataset generation/export utilities
generation/    synthetic-data generators
tests/         unit/integration tests
configs/       YAML configuration files
experiments/   experiment metadata/results
docs/          technical documentation
```

### 4.2 Candidate B — Master Plan's structure (nested under `src/`)

```
synthetic-cardio/
├── config/
│   └── project.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── reference/
│   └── generated/
├── src/
│   ├── schemas/patient.py
│   ├── ingestion/{base.py, ptbxl.py}
│   ├── integration/patient_builder.py
│   ├── generation/[framework-dependent]
│   ├── validation/{ecg.py, distribution.py, consistency.py, dataset_report.py}
│   └── export/dataset_writer.py
├── experiments/
├── tests/
├── notebooks/
└── README.md
```

### 4.3 Candidate C — Today's `ml/` scaffolding (already created)

```
ml/            model-agnostic Dataset/Model/Trainer/Evaluator contracts
configs/       placeholder for YAML config
docs/          ml_architecture.md, this spec
```

`ml/` was deliberately framework- and structure-agnostic; it does not assume Candidate A's flat layout or Candidate B's `src/`-nesting, and can sit inside either without modification. It is **not** itself a fourth competing structure — it's designed to be structure-neutral.

### 4.4 Open reconciliation questions

- Flat root-level folders (A) vs. `src/`-nested (B): does the arriving codebase already assume one of these? This is unknowable until the Monday audit.
- Does a top-level `data/` directory (raw/processed/reference/generated) get added regardless of which layout wins? (Both source reports imply yes; `Claude.md` doesn't currently mention one.)
- `config/` (singular, Master Plan) vs. `configs/` (plural, `Claude.md`) — naming to reconcile.
- Where does `ml/` (today's contracts layer) live relative to `generation/`? Candidate: `ml/` hosts the generator-agnostic training/eval contracts; `generation/` hosts the concrete generator implementation(s) that satisfy those contracts once chosen.

**Resolution point:** Stage 0, Action 1 (Section 6) — after the original codebase is audited, pick the structure that requires the least forced adaptation of working code, and record the decision here.

### 4.5 Dependencies (known/candidate, not fixed)

No dependency list is fixed yet — exact versions depend on what the original codebase already pins. What's known or implied by the source material:

- **Existing (from prior SysDaG work):** PyTorch, WFDB (signal loading), presumably NumPy/Pandas for tabular handling.
- **Candidate external frameworks under evaluation, not yet committed to:** CardioSynth (primary candidate for multimodal generation — requires an audit before commitment), Synthea (candidate for patient/EHR timeline backbone).
- **Configuration:** YAML-based (`Claude.md` §6), implying PyYAML or equivalent.
- **Principle carried forward from `Claude.md`:** avoid unnecessary dependencies; do not install new ones until a demonstrated need exists.

Do not pin exact versions or add libraries to any requirements file until the Phase A audit (Section 6) reveals what the original codebase already depends on.

---

## 5. Design

### 5.1 Patient-centric architecture

All modalities connect through a canonical `patient_id`. A patient is the parent object; a valid synthetic patient must have internally consistent modalities (e.g., a patient with a diabetes diagnosis should have a plausible medication/lab profile, not a randomly paired one from a different patient).

### 5.2 Generator-agnostic principle

The generation layer must stay swappable:

```
generation/
    cardiosynth/           # if selected
```
or
```
generation/
    alternative_framework/ # if another framework is selected
```

No generator architecture (GAN/VAE/diffusion/CardioSynth/etc.) is chosen by this spec. This mirrors today's `ml/interfaces.py`, which defines `DatasetInterface`, `ModelInterface`, `TrainerInterface`, and `EvaluatorInterface` without assuming what satisfies them.

### 5.3 Dedicated ECG generation decision path

```
Check selected framework's ECG capability
        |
        v
If adequate -> use/integrate it
        |
        v
If inadequate -> reuse/adapt prior SysDaG ECG capability
        |
        v
Only if necessary -> consider another dedicated ECG generator
```

### 5.4 Layered validation architecture

| Layer | Checks |
|---|---|
| 1. Schema | Missing required fields, incorrect data types, invalid ranges/categories, broken patient IDs |
| 2. Distribution | Real/reference vs. synthetic distributions for age, sex, risk factors, conditions, labs, etc. |
| 3. ECG | Reuse/adapt prior metrics: mean, std dev, variance, MSE, KS, KL, morphology, QRS characteristics, signal diversity |
| 4. Diversity | Exact duplicates, near-duplicates, mode collapse, distribution coverage, patient diversity |
| 5. Clinical Consistency | Diagnosis↔medication, diagnosis↔lab, risk factor↔diagnosis, age↔condition, ECG↔diagnosis |
| 6. Cross-Modal Consistency | Whether modalities describe one coherent patient state without implausible contradictions |

### 5.5 Scaling strategy

```
Build -> Smoke Test -> 1K -> Validate -> 10K -> Validate -> 100K -> Validate
```

Each scale step must pass validation before proceeding to the next.

---

## 6. Stage Plan & Decision Gates

| Stage | Objective | Expected output |
|---|---|---|
| 0 — Audit & Reuse | Audit prior SysDaG work, PTB-XL, preprocessing, ECG label mapping, validation, CardioSynth requirements, Synthea's potential role | REUSE / ADAPT / RETIRE / BUILD NEW matrix |
| 1 — Foundation & Schema | Build master patient schema, configuration, ingestion interfaces, patient-ID integration, validation, export, experiment tracking | Stable foundation independent of the final generator |
| 2 — Source Integration & 1K Pilot | Connect the selected framework; produce ~1,000 coherent multimodal patients | End-to-end proof of IDs, linkage, ECG, validation, export, reproducibility |
| 3 — Multimodal Integration & 10K | Scale to ~10,000; test consistency, diversity, storage, runtime, failure rates | Evidence the architecture is stable at intermediate scale |
| 4 — Scale to ~100K | Freeze schema, configuration, generator version, validation rules, output format, seed strategy, source versions; scale 10K→25K→50K→100K | Final generation candidate |
| 5 — Final Validation & Pattern Extraction | Validate distributions, diversity, duplicates, ECG quality, clinical consistency, cross-modal consistency, utility | Validation report + pattern-analysis report |

### Decision gates

| Gate | Question |
|---|---|
| 1 — Reuse | What can be directly reused from prior SysDaG work? |
| 2 — Framework | Which framework reaches the multimodal goal with the least unnecessary engineering? |
| 3 — 1K Pilot | Can ~1K coherent multimodal patients be produced? |
| 4 — 10K | Does the system remain stable and coherent at 10K? |
| 5 — 100K | Is the system stable enough to produce the final dataset? |

### Indicative 4–5 week timeline

| Week | Primary target | Main work |
|---|---|---|
| 1 | Audit + foundation | Audit prior work/ECG; define patient schema, modality structure, patient ID, configuration; build validation skeleton; audit CardioSynth, assess Synthea |
| 2 | ~1,000 patients | First complete generation path: generation, patient integration, ECG integration, validation, export, debugging |
| 3 | ~10,000 patients | Multimodal integration, consistency fixes, distribution validation, duplicate detection, ECG quality, performance testing, initial pattern analysis |
| 4 | ~100,000 patients | Final generation, storage, validation, quality filtering, documentation, dataset packaging |
| 5 | Buffer / hardening | Fix weak modalities, improve validation/consistency, re-run failed components, deeper analysis, final documentation/presentation |

This timeline is **indicative**, carried from the Master Plan; it has not been re-validated against the actual original codebase and may shift after the Stage 0 audit.

### Build now vs. wait

| Build now | Wait until requirements are clear |
|---|---|
| Patient schema | Full CardioSynth-specific pipeline |
| Patient ID system | Custom multimodal neural network |
| PTB-XL loader (once codebase available) | Multiple independent generative models |
| Configuration system | Large AWS infrastructure |
| Validation framework | 100K generation pipeline |
| Export framework | Complicated UI |
| Experiment tracking | New GAN architecture |
| Dataset versioning | Multiple modality-specific training pipelines |
| Basic tests | |
| Source/modality mapping | |
| Data dictionary | |

**Note:** several "build now" items (patient schema, configuration system, validation framework skeleton, patient-ID system) are new engineering for the multimodal project and do not require the original SysDaG codebase. They are not blocked by the "wait until Monday" constraint that applies to dataset-loading/preprocessing/model code tied to the *existing* PTB-XL pipeline. Whether to start any of this before Monday is a scoping decision for you, not something this spec authorizes on its own — see Section 8.

---

## 7. Open Questions (carried forward from the Master Plan, unresolved)

1. What exactly does "100K" mean — unique patients, snapshots, longitudinal records, or complete timelines?
2. What are the mandatory modalities, beyond ECG?
3. How important is signal-level ECG — is a 12×1000 signal required, or is a structured representation sufficient for an MVP?
4. What does "Echo" mean — images, waveforms, structured measurements, or physiological parameters?
5. Do we need longitudinal patients, or are snapshots sufficient?
6. What population are we representing (Indian population, general, CV high-risk, specific age distribution, specific hospital population)?
7. How exactly should ICMR-INDIAB be used — which variables condition generation, and is it a sufficient population reference alone?
8. How deeply do we use CardioSynth — complete generator, or framework + existing components + our integration layer?
9. What role should Synthea play — full EHR backbone, timeline/event generator, workflow reference, or none?
10. What should happen with prior SysDaG ECG generation — reuse directly, adapt/improve, use only preprocessing/validation, or replace it?
11. What clinical consistency rules are mandatory (e.g., diabetes↔glucose/HbA1c, hypertension↔BP state, CAD↔CV history, medication↔diagnosis, ECG↔CV condition)?
12. What will be the real validation benchmark — which datasets for development, validation, and final evaluation?
13. What are the success thresholds for distribution similarity, ECG quality, diversity, duplicate rate, clinical consistency, downstream utility, missingness, privacy?
14. What privacy standard is required — membership inference, nearest-neighbor checks, record linkage, memorization tests, and/or differential privacy?
15. What patterns are expected (disease prevalence, risk-factor relationships, age-related patterns, medication patterns, ECG patterns, lab patterns, multimodal correlations, clusters, longitudinal trajectories)?
16. What real datasets can actually be accessed (dataset, access, license, modality, size, population, use restrictions)?
17. When should the project move to AWS — what workload justifies cloud compute (training time, 100K generation time, memory limits, parallel generation)?
18. What should the final output format be — CSV, Parquet, JSON, FHIR, HDF5, database, or a combination?
19. How reproducible must generation be — exact regeneration from a seed, versus configuration/model version/seed/dataset version/generation manifest?
20. What is the MVP cut line — if one modality becomes too difficult within 4–5 weeks, which can be deferred without compromising the core objective?

These remain genuinely open. Do not assume answers to any of them when implementing.

---

## 8. Immediate Next Actions

Merged and de-duplicated from the Stage 0 Audit, the Master Plan, and today's `ml/TODO.md`:

1. **Audit the original SysDaG implementation** (arrives Monday) — see `ml/TODO.md` Phase A: dataset loaders, preprocessing, normalization, labels, patient IDs, train/val/test splitting, PyTorch code, existing models, metrics, checkpoints, configuration, dependencies. Do not modify or overwrite the original implementation during the audit.
2. **Classify components** as REUSE / ADAPT / RETIRE / BUILD NEW (extends the Section 3 tables with anything the audit reveals that the reports didn't cover).
3. **Define the master patient schema** — target structure for one complete synthetic patient (Section 2.1), with datatype, required/optional status, candidate source, and validation method per field.
4. **Resolve the repository structure** (Section 4) — pick between Candidates A/B (or a merge) based on what the audited codebase actually assumes.
5. **Build the source-to-field map** — for every target field, mark available / partially available / unavailable / requires synthesis. This exposes real gaps before any model or infrastructure is chosen.
6. **Create the configuration system, patient-ID integration layer, validation framework skeleton, and export framework** — model-independent, can proceed once the structure decision (Section 4) is made.
7. **Audit CardioSynth's implementation requirements**, and **determine whether Synthea provides useful components** (data requirements, modalities supported, training needs, pretrained components, customization effort, patient-level linkage support, target-scale feasibility, hardware fit, output format, integration difficulty).
8. **Resolve architecture-changing open questions** (Section 7) enough to unblock Stage 1.
9. **Run a local end-to-end smoke test** before committing to the 1K pilot (Stage 2).
10. **Map existing code to `ml/interfaces.py`** (`ml/TODO.md` Phase B) once concrete implementations exist to map.

---

## 9. Source Notes

- Sections 1, 3, 6 (Stage 0 row) draw primarily from the **Stage 0 Audit** report.
- Sections 2, 4.2, 4.5, 5, 6 (Stages 1–5, timeline, build-now table), 7 draw primarily from the **Master Plan** report.
- Sections 4.1, 4.3, 4.4, 8 (items 4, 6, 10) draw from `Claude.md` and this project's own prior session work (`ml/` scaffolding, `ml/TODO.md`).
- Where the two reports' terminology differed (e.g., "config/" vs. "configs/"), both are preserved verbatim in Section 4 rather than silently reconciled.
