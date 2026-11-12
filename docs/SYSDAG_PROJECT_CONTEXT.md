# SysDaG — Full Project Context

**Synthetic Cardiovascular Patient Dataset & Generative System**

**Purpose of this document:** a single, self-contained narrative of the
entire project — where it started, every decision and milestone between
then and now, the exact current state of every artifact, every known
limitation and open question, and the full future direction as
originally specified and as currently understood. Written so a new
reader (human or agent) can reconstruct the whole project from this file
alone, without having to re-read forty separate documents in the right
order.

**This document does not replace the project's live tracking files** —
it is a synthesis of them, frozen at the point in time it was written.
The authoritative, continuously-updated sources remain:

| File | Role |
|---|---|
| `docs/Claude.md` | The original project specification / operating instructions. Static — not updated per-milestone. |
| `docs/PROJECT_STATE.md` | The live milestone tracker. Updated at every completed milestone. **If this document and `PROJECT_STATE.md` ever disagree, `PROJECT_STATE.md` is correct** — it is updated more often than this synthesis will be. |
| `docs/DECISIONS.md` | The append-only architectural decision log (D001 onward, newest first). |
| `docs/M8_DECISION_BRIEF.md` | The current consolidated list of every open human decision, with options and recommendations. |

**Written:** 2026-10-21. **Covers milestones through:** M5.5 (also
referred to as "M8" in earlier artifact names — see §3.1 for the naming
note) and the M8 Decision Brief.

---

## Table of Contents

1. [What SysDaG Is](#1-what-sysdag-is)
2. [Project Vision and the Full Intended Pipeline](#2-project-vision-and-the-full-intended-pipeline)
3. [Operating Principles That Govern Every Decision](#3-operating-principles-that-govern-every-decision)
4. [Repository Structure](#4-repository-structure)
5. [Schema Evolution: v0.2 → v0.8](#5-schema-evolution-v02--v08)
6. [The Full Decision Log (D001–D017)](#6-the-full-decision-log-d001d017)
7. [Milestone-by-Milestone Narrative](#7-milestone-by-milestone-narrative)
8. [Data Sources and Evidence Base](#8-data-sources-and-evidence-base)
9. [The Generation Pipeline, As It Exists Today](#9-the-generation-pipeline-as-it-exists-today)
10. [The Validation Framework](#10-the-validation-framework)
11. [Current Dataset State — Exact Figures](#11-current-dataset-state--exact-figures)
12. [The ECG / Multimodal Track](#12-the-ecg--multimodal-track)
13. [Known Limitations and Accepted Gaps — Complete List](#13-known-limitations-and-accepted-gaps--complete-list)
14. [Every Currently Open Human Decision](#14-every-currently-open-human-decision)
15. [Future Plan and Direction](#15-future-plan-and-direction)
16. [Stage-Numbering Note: Two Schemes Exist](#16-stage-numbering-note-two-schemes-exist)
17. [Quick-Reference: Entry Points and Reusable Components](#17-quick-reference-entry-points-and-reusable-components)
18. [Project Governance and Conventions](#18-project-governance-and-conventions)
19. [How to Resume Work From Here](#19-how-to-resume-work-from-here)

---

## 1. What SysDaG Is

SysDaG is a project to build a **large-scale, evidence-grounded synthetic
cardiovascular patient dataset** representing the general Indian adult
population (ages 20–89), and — once that dataset is validated — to use
it as the foundation for a later generative-modeling stage that produces
*new* synthetic patient data conditioned on discovered population
patterns and Indian demographic characteristics.

It is explicitly **not**:
- a project to generate "100,000 fake rows" as an end in itself;
- a project targeting a cardiovascular-disease-only, hospital, or
  cardiology-clinic population (`docs/DECISIONS.md` D008);
- a from-scratch build — it is built on top of an inherited codebase
  (PTB-XL ECG handling, a per-superclass GAN, notebooks, and an earlier
  "SynGen" subproject) that the project reuses, adapts, and extends
  rather than replaces (`CLAUDE.md` §5–7, the "REUSE → ADAPT → BUILD"
  principle).

The project has a stated 4–5 week development timeline (per `CLAUDE.md`
§1) and is tracked as a sequence of milestones (M1, M2A…M2D, M3, M3.5,
M4-0/M4A…M4F, M5, M5.5) inside `docs/PROJECT_STATE.md`, each gated by
tests and, where a decision carries real weight, by an explicit human
checkpoint recorded in `docs/DECISIONS.md`.

---

## 2. Project Vision and the Full Intended Pipeline

Quoting `CLAUDE.md` §3 directly, because this is the single most
important framing in the whole project and is easy to lose sight of
mid-implementation:

> The 100,000+ patient dataset is an intermediate foundation for the
> later stages of the project.

The intended end-to-end pipeline:

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

The project is therefore not finished when the 100,000-record dataset
exists and validates — it is roughly **half-way** through its own stated
arc. Everything built so far (schema, generation, validation, the
100K+ dataset itself) is the *input* to a pattern-discovery and
generative-modeling phase that has not yet started.

### 2.1 The Indian-demographic novelty

A specific, deliberate design goal (`CLAUDE.md` §4) is to ground Indian
demographic conditioning in **actual evidence**, not in medically
plausible-sounding assumptions:

> The project should NOT make unsupported claims that the synthetic
> dataset represents the Indian population. Indian demographic
> characteristics and population-specific patterns must be based on the
> data and evidence available to the project. Do not invent
> population-level relationships simply because they appear medically
> plausible.

Every generated field in this project traces to one of: an observed
population distribution, an observed conditional distribution, an
explicit disclosed engineering assumption, or "not supportable with
current evidence — deferred." This discipline is why so much of the
project's documentation is about *evidence provenance* rather than just
code.

---

## 3. Operating Principles That Govern Every Decision

These are drawn from `CLAUDE.md`'s numbered sections and are worth
stating up front because they explain *why* so many design choices in
this project look the way they do.

- **REUSE → ADAPT → BUILD** (§5–7): search the existing codebase before
  writing anything new; adapt working code before replacing it; only
  build new functionality when nothing existing solves the problem.
  Legacy GAN code is "an existing asset," not automatically the
  foundation of the new architecture — reused only when it actually
  solves a current requirement.
- **Raw value primary, derived interpretation secondary — where
  evidence supports it** (D011): applied to lipids (raw TC/HDL/TG/LDL
  primary, clinical interpretations derived) and, in the reverse
  direction where the evidence runs the other way, to HbA1c (the
  diabetes label is primary, HbA1c is generated conditional on it) and
  blood pressure (the hypertension label is primary, BP is generated
  conditional on it, D017).
- **Never duplicate an already-generated fact as a second independent
  random variable** (`docs/CLINICAL_RECORD_DESIGN.md` §D, reused
  throughout): medical history references diagnoses rather than
  re-rolling them; medications reference diagnoses; encounters
  reference measurements.
- **Progressive scaling, never jump straight to 100,000** (`CLAUDE.md`
  Stage 7 / PROJECT_STATE Stage 6): 10 → 100 → 1,000 → 10,000 → 100,000,
  each scale validated before the next. The 50-record pilot pattern used
  for schema v0.8 (§7.9 below) is this same discipline applied again at
  a schema-migration scale.
- **Human checkpoints for genuine decisions, not for routine work**
  (`CLAUDE.md` §28/§29): model selection, new external datasets, major
  schema changes, expensive computation, cloud infrastructure cost, and
  destructive/irreversible operations all require an explicit human
  decision, reported in a fixed format (CURRENT STAGE / CURRENT
  MILESTONE / COMPLETED / EVIDENCE / TESTS / OUTPUTS / BLOCKER-DECISION
  / OPTIONS / RECOMMENDED NEXT STEP). Routine, reversible, in-scope work
  does not stop for approval.
- **Document the limitation rather than fabricate the data**
  (restated in nearly every M4/M8 document): a field with insufficient
  evidence stays `null`, explicitly, with the exact missing evidence
  named — never filled with a plausible-looking placeholder.

### 3.1 A naming note worth stating once, clearly

Two independent numbering/naming collisions exist in this project's
history, both already identified and resolved by disambiguation rather
than renaming everything retroactively:

1. **"M8" means two different things.** `docs/ROADMAP.md` (an early,
   generic placeholder roadmap that was never kept in sync with the
   project's real milestone tracking) labels its own "M8" as "Integrate
   ECG generation." Separately, the blood-pressure/encounters/timeline
   work done in October 2026 was built and documented under the
   shorthand "M8" (`docs/DECISIONS.md` D017, `integration/
   migrate_v07_to_v08.py`, `validation/pilot_50_records/`, and the
   `docs/M8_*.md` report filenames) **before** it was formally slotted
   into `docs/PROJECT_STATE.md`'s own milestone sequence. When it was
   slotted in, it was numbered **M5.5** (between M5 and M6) instead,
   specifically to avoid colliding with ROADMAP.md's ECG-labeled "M8."
   The `M8_*` filenames were kept as-is rather than renamed, to avoid
   unnecessary churn. **Net effect: "M5.5" in `PROJECT_STATE.md` and
   "M8" in file/decision names refer to the same body of work.**
2. **Two stage-numbering schemes exist** (`CLAUDE.md`'s 13 stages,
   Stage 0–12, vs. `PROJECT_STATE.md`'s compressed 11 stages, Stage
   0–10). See §16 for the exact mapping — do not assume "Stage 7" means
   the same thing in both documents.

---

## 4. Repository Structure

Flat, root-level layout (`docs/DECISIONS.md` D001 — chosen over a
`src/`-nested layout specifically because it required the least forced
adaptation of the inherited code):

```text
Sysdag_development/
├── schemas/              Patient data model (dataclasses), schema version, vocabularies
├── generation/           Deterministic, evidence-traceable sampling + derivation logic
│   ├── indian_population.py    Demographics, risk factors, lipids, HbA1c, blood pressure
│   └── clinical_history.py     Diagnoses, medical history, medications, encounters, timeline
├── ingestion/            PTB-XL ECG metadata adapter (reuses syngen's build_label_map())
├── integration/          Orchestration: patient assembly, migration, validation runners, freezing
│   ├── build_patient.py              Fresh-generation entry point (one patient, schema v0.8)
│   ├── migrate_v07_to_v08.py         Reusable, idempotent schema migration (the "M8" migration)
│   ├── validate_clinical_population.py   Full-population structural+clinical+migration-integrity validator
│   ├── freeze_dataset_manifest.py    Dataset-version freezing/manifest tool
│   ├── ecg_pilot_heldout_evaluation.py   ECG GAN held-out re-evaluation pilot
│   ├── generate_population.py        Bulk patient generation driver
│   └── patient_id.py                 Canonical patient ID scheme/validation
├── validation/           Structural, clinical-consistency, and statistical validators
│   ├── structural.py             Schema-compliance checks (generator-independent)
│   ├── clinical_consistency.py   Cross-field clinical rules (recomputes, never trusts)
│   ├── statistical.py            Population-level distribution checks (chi-square, binomial, KS)
│   └── pilot_50_records/         The 50-record v0.8 validation pilot (input/output/reports/tests)
├── configs/
│   ├── base.yaml                  PTB-XL paths, training folds, random seed
│   └── indian_population.yaml     Every generation parameter, with full evidence provenance
├── tests/                 142 tests across 9 files, one per milestone's generation logic
├── syngen/                Inherited codebase: PTB-XL dataset, per-superclass GAN, evaluation scripts
├── ml/                    Model-agnostic interfaces (DatasetInterface/ModelInterface/
│                          TrainerInterface/EvaluatorInterface) for the future generative-model stage
├── outputs/               Generated datasets, one subdirectory per milestone (m2c, m3, m4a…m4f, m5, m8, test)
└── docs/                  Every design document, decision log, milestone report, and this file
```

`.gitignore` excludes `outputs/` (generated datasets are not committed)
and syngen's large re-downloadable/regeneratable binary assets
(PTB-XL's raw dataset, trained GAN checkpoints, generated `.npy` arrays)
while keeping syngen's reused `.py` code tracked.

**This project does not commit per-milestone by standing convention** —
the working tree accumulates uncommitted milestone work between
deliberate commits, and `docs/PROJECT_STATE.md`/`docs/DECISIONS.md` are
the authoritative change record, not git history.

---

## 5. Schema Evolution: v0.2 → v0.8

| Version | Milestone | What changed |
|---|---|---|
| v0.2 | M1 | Initial schema: patient identity, demographics, provenance, timeline, basic validation. |
| v0.3 | M2C (D005) | `Demographics` gained `state` and `urban_rural` as first-class fields. |
| v0.4 | M2C (D006) | `RiskFactors` formalized as a typed schema field (BMI, smoking, hypertension, diabetes, hyperlipidemia) superseding a placeholder. |
| v0.5 | M4A (D012) | `LipidPanel`, `LipidInterpretation`, `Lab` dataclasses added — schema only, no generation logic yet. |
| v0.6 | M4D (D015) | `Diagnosis` and `MedicalHistoryEntry` added — diagnoses as a 1:1 promotion of risk-factor flags. |
| v0.7 | M4E (D016) | `Medication` added — drug-class only (antihypertensive/antidiabetic), NNMS treatment-rate gated. **This is the schema of the M5 100,000-record baseline dataset.** |
| v0.8 | M5.5 / "M8" (D017) | `BloodPressure` and `Encounter` dataclasses added; `TimelineEvent` gained `reference_id`. **This is the schema of the current frozen `outputs/m8/100k_patients_v08/` dataset.** |

Every version bump followed the same pattern: additive dataclasses,
never a destructive restructuring, and every bump is recorded in
`docs/DECISIONS.md` with its own numbered decision entry.

---

## 6. The Full Decision Log (D001–D017)

`docs/DECISIONS.md` is append-only, newest first. Summarized here in
chronological order (oldest first) for narrative readability — **always
treat `docs/DECISIONS.md` itself as the authoritative text**, this is a
summary.

| # | Date | Decision |
|---|---|---|
| **D001** | 2026-09-25 | Repository structure: flat, root-level layout (Candidate A), not a `src/`-nested layout — chosen to minimize forced adaptation of inherited code. |
| **D002** | 2026-09-25 | Use the Anaconda Python interpreter (`C:\Users\devg8\anaconda3\python.exe`) for this project, with `wfdb` added to it — the default PATH `python` (3.14) lacked the scientific-computing stack this project needs. |
| **D003** | 2026-09-25 | ECG integration for M1 is **metadata-only** — `ecg_id`, superclass labels, fold, sampling rate, signal shape are reused from a real PTB-XL record, but no waveform is attached (`signal_available: false`). Signal generation is explicitly deferred to Stage 4. **This boundary has been preserved through every subsequent milestone, including M5.5/M8.** |
| **D004** | 2026-09-25 | For M1, demographics (age/sex/height/weight) are read directly from the linked PTB-XL record rather than independently randomized — avoiding two separately-random representations of what should be one coherent fact. (Superseded for `age`/`sex`/`state`/`urban_rural` by D006's Indian-conditioned generation; `height`/`weight` remain unaddressed through M5.5.) |
| **D005** | 2026-09-25 | `state` and `urban_rural` adopted as first-class `Demographics` fields (Schema v0.3), ahead of having generation logic for them — the fields exist so generation has somewhere to write to. |
| **D006** | 2026-09-25 | `risk_factors` formalized as a typed schema field (Schema v0.4); M2C's Indian-conditioned generation supersedes D004's demographics placeholder for age/state/urban_rural/BMI/smoking/hypertension/diabetes/hyperlipidemia. |
| **D007** | 2026-09-25 | M2D: kept `age ~ uniform(20, 89)` despite locating a better-sourced but still too coarse alternative age distribution — a documented, deliberate non-adoption, not an oversight. |
| **D008** | 2026-09-26 | **Target population defined**: the synthetic population represents the **general** Indian adult population (ages 20–89) — explicitly NOT a cardiovascular-disease-only, hospital, cardiology-clinic, high-risk-CVD-cohort, or CVD-patient-registry population. This resolved an open question from M2D and governs every subsequent evidence-sourcing decision. |
| **D009** | 2026-09-26 | Performance fix, zero content change: PTB-XL CSV/label-map parsing cached per-process (`functools.lru_cache`) instead of per-patient, after M3.5 profiling found the true bottleneck was CPU-bound label-map construction, not I/O. |
| **D010** | 2026-09-26 | M3.5's three candidate improvements each resolved with a distinct documented reason: urban/rural-conditioned BMI **deferred** (no joint sex×urban/rural×BMI table exists in the evidence, only two separate marginals — combining them would invent a correlation); ECG-ID reuse **deferred to Stage 4** (a real question, not urgent until waveforms are generated); state boundaries **preserved** as-is. |
| **D011** | 2026-09-26 | **The project's central architectural pattern.** Raw/continuous value primary, derived interpretation secondary, *where the evidence supports it*. Resolved the M4-0A dyslipidemia conflict (81.2% NCEP-based vs. 87.3% LAI-based prevalence, different LDL cutoffs) not by picking a winner but by making LDL/HDL/TG/TC the primary generated value and preserving *both* clinical interpretations as separately-tagged derivations. Also established the explicit exception: HbA1c's evidence runs the *reverse* direction (diabetes label is primary; HbA1c is generated conditional on it) — later extended to blood pressure (D017) on the same reasoning. |
| **D012** | 2026-09-26 | Implemented the `LipidPanel`/`LipidInterpretation`/`Lab` schema (v0.4 → v0.5) that D011 required — schema only, no generation logic yet. |
| **D013** | 2026-09-26 | Implemented the generation logic D011/D012 authorized: TC/TG/HDL sampled (category-then-uniform from ICMR-INDIAB-17 marginals); **LDL derived via the Friedewald equation** (`LDL = TC − HDL − TG/5`), never independently sampled; lipid interpretations computed per named clinical definition, never sampled; HbA1c generated conditional on the (already-primary) diabetes label, for non-diabetic patients only. |
| **D014** | 2026-09-26 | `risk_factors.hyperlipidemia` (a population-level background risk-factor Bernoulli) and `lipid_interpretations` (a per-patient measurement-derived label) are **intentionally distinct, non-agreeing variables** (human-decided "Option B") — their ~73–77% disagreement rate is expected, not a bug, and the validator never compares them. |
| **D015** | 2026-09-26 | Diagnoses and `medical_history` implemented as a strict **1:1 promotion** of the hypertension/diabetes risk-factor flags (Schema v0.5 → v0.6) — never independently sampled. Hyperlipidemia's own diagnosis is **deliberately deferred** (which lipid definition should drive it remains unresolved — carried forward as Decision 6 in the current open-decisions list, §14). |
| **D016** | 2026-09-27 | `Medication` implemented at **drug-class level only** (antihypertensive/antidiabetic — never a specific drug name), gated on ICMR-NNMS national treatment-rate Bernoulli draws (14.5%/36.1%). Schema v0.6 → v0.7. Statin/antiplatelet medications deliberately excluded — no population treatment-rate evidence exists for either. **This is the schema of the M5 100,000-record baseline.** |
| **D017** | 2026-10-20 | **Blood pressure** implemented as a label-conditional measurement (never independently generated, never used to re-derive the hypertension label); **encounters** implemented as a declared non-clinical structural container; height/weight still deferred (no national adult-height SD located after 6 total research attempts). Schema v0.7 → v0.8. This is the decision behind the current `outputs/m8/100k_patients_v08/` dataset. Full detail in §7.9/§9 below. |

---

## 7. Milestone-by-Milestone Narrative

### 7.1 M1 — Generate One Valid Synthetic Patient (COMPLETE 2026-09-25)

Established Schema v0.2, the `Patient` dataclass, patient-ID generation,
provenance, timeline, and basic structural validation. ECG metadata
reused from a real PTB-XL record via syngen's `build_label_map()` (D003
— metadata-only, a boundary preserved ever since). One patient
generated and verified structurally valid and reproducible.

### 7.2 M2A/M2B — Indian Population Research and Strategy (COMPLETE 2026-09-25)

M2A: researched available Indian population datasets (Census 2011,
ICMR-NNMS, ICMR-INDIAB, LASI, NSS) and recorded what each one does and
does not support (`docs/INDIAN_DATA_SOURCES.md`). M2B: designed the
generation strategy for applying that evidence (`docs/
INDIAN_GENERATION_STRATEGY.md`).

### 7.3 M2C — Indian-Conditioned Generation Implementation (COMPLETE 2026-09-25)

Implemented age/sex/state/urban_rural demographics and BMI/smoking/
hypertension/diabetes/hyperlipidemia risk factors, each sourced from a
cited Indian dataset where evidence existed, and left `family_history`
unpopulated where it didn't (D004 no-evidence finding for CVD family
history). Schema v0.4 (D006). `configs/indian_population.yaml` and
`generation/indian_population.py` originate here. 10- and 100-patient
runs generated and statistically checked.

### 7.4 M2D — Calibration & Quality Gate (COMPLETE 2026-09-25)

Audited all 7 limitations M2C itself had flagged. Result: **zero
behavioral code changes** — every audit concluded the M2C implementation
was already the evidence-correct choice. One better-sourced age figure
was found and explicitly, quantifiably **rejected** (D007) rather than
adopted uncritically — a deliberate demonstration that "found a new
source" does not automatically mean "use the new source."

### 7.5 M3 / M3.5 — 1,000-Patient Validation, Candidate Improvements, Clinical Layer Design (COMPLETE 2026-09-26)

M3: generated and validated 1,000 patients, confirming no implementation
bias via relationship/dependency audits (`docs/M3_PATTERN_INVENTORY.md`,
`docs/M3_DATA_QUALITY_REPORT.md`). M3.5: investigated 4 candidate
improvements (D009/D010 — the performance fix, and the three
disposition decisions) and produced `docs/CLINICAL_RECORD_DESIGN.md`,
the design blueprint the entire M4 clinical layer was built from.

### 7.6 M4-0 / M4-0A / M4-0B — Clinical Evidence Verification & Architecture (COMPLETE 2026-09-26)

A dedicated evidence-verification pass before any clinical-layer code
was written: confirmed the dyslipidemia prevalence conflict (M4-0A),
converted the resulting human decisions into a formal raw/derived
architecture (M4-0B → D011). `docs/M4_CLINICAL_EVIDENCE.md` and
`docs/M4_CLINICAL_ARCHITECTURE.md` are the record of this pass.

### 7.7 M4A → M4F — The Clinical Layer, Built in Stages (COMPLETE 2026-09-26 → 2026-09-27)

- **M4A** (D012): schema only — `LipidPanel`/`LipidInterpretation`/`Lab`.
- **M4B** (D013): lipid + HbA1c generation logic (Friedewald LDL, computed interpretations, diabetes-conditional HbA1c).
- **M4C**: two sub-milestones — (1) implemented `validation/
  clinical_consistency.py` and validated 10/100 patients; (2) the
  hyperlipidemia/lipid_interpretations semantic audit and human decision
  (D014).
- **M4D** (D015): diagnoses + medical_history, 1:1 promotion of risk
  factors, hyperlipidemia diagnosis deferred.
- **M4E** (D016): medications, drug-class only, NNMS treatment-rate
  gated. Schema v0.7.
- **M4F**: final pre-scale audit — full domain matrix, human-decision
  audit (only the hyperlipidemia-diagnosis-definition question remained
  open), consistency re-confirmation at 10/100/1,000 patients, a
  5,000-patient scale benchmark (71.6 patients/sec, memory flat), and an
  ECG-readiness audit. **Zero Category-A bugs found. 100K readiness:
  READY (conditionally).**

### 7.8 M5 — 100K Baseline Synthetic Population (COMPLETE 2026-09-27)

Generated the project's first 100,000-patient dataset
(`outputs/m5/100k_patients/`, seed 42, Schema v0.7) using the existing,
unmodified pipeline. **0 generation errors, 0 duplicate IDs,
100,000/100,000 structurally valid, 100,000/100,000 clinically
consistent (0 errors, 0 warnings).** 23.3 minutes, 71.5 patients/sec,
355.12 MB. Every statistically-checked variable within expected sampling
variation of its cited target except the NCEP/LAI composite dyslipidemia
rates — a previously-documented (D013), not-newly-discovered structural
consequence of category-based lipid reconstruction, explicitly not
corrected. ECG-ID reuse quantified (17,386 unique IDs, max reuse 17×) —
recorded as future-decision evidence, not solved. Full report:
`docs/M5_100K_DATASET_REPORT.md`.

**This is the dataset `outputs/m5/100k_patients/` — still present,
still unmodified, and now the immutable source input to every
subsequent migration.**

### 7.9 M5.5 / "M8" — Clinical Field Completion + Full-Dataset Migration (COMPLETE 2026-10-20)

The most recent completed milestone, and the one this document's
surrounding session work was about. In order:

1. **Gap assessment.** Inspected the actual M5 dataset and found several
   intended fields genuinely unimplemented: `blood_pressure` didn't
   exist as a field at all; `encounters` and `clinical_timeline` beyond
   a single creation event were null/minimal; `height_cm`/`weight_kg`
   remained null.
2. **Evidence research.** Located NFHS-5 age-band × sex blood-pressure
   evidence (previously unresearched — M2D/M4 had confirmed "BP
   continuous distribution NEVER RESEARCHED") via a PLOS ONE 2025 paper
   and a corroborating paper with independently-published SDs. Height
   evidence was searched again (3 more attempts, on top of 3 from
   M4-0) and still not found at the standard this project requires
   (mean **and** SD, not mean alone).
3. **Implementation (D017).** `BloodPressure` dataclass, generated
   **conditional on the hypertension label** using that label's own
   published clinical definition as the truncation boundary — the same
   label-primary architecture D011 established for HbA1c. SBP/DBP
   correlation (r=0.7255) derived from published variances, not
   assumed. One explicit engineering assumption (a 20mmHg
   pulse-pressure floor) added after *measuring* that independent
   sampling produced a 10.7% rate of clinically-implausible narrow
   pulse pressure. `Encounter` dataclass added as a declared,
   non-clinical structural container. `TimelineEvent.reference_id`
   added. Schema v0.7 → v0.8.
4. **50-record pilot first** (`validation/pilot_50_records/`), per the
   project's progressive-scaling discipline — selected via a documented
   uniform random sample, validated, reported, before touching the full
   100,000.
5. **Full-scale migration and validation.** `integration/
   migrate_v07_to_v08.py` — idempotent, deterministic, and replays each
   record's own recorded random seed to regenerate its new fields,
   verifying every pre-existing field still matches before accepting
   the new one. Run over all 100,000 M5 records, writing to a **new**
   directory (`outputs/m8/100k_patients_v08/`) — the M5 source was never
   modified. Independently re-validated by `integration/
   validate_clinical_population.py`: **100,000/100,000 structurally
   valid, 100,000/100,000 clinically consistent, 100,000/100,000
   migration-integrity exact matches** (every output record re-derived
   fresh from its source and diffed byte-for-byte against disk).
6. **Dataset frozen** — `outputs/m8/dataset_manifest.json`, same
   convention as M5's manifest, with a recomputed directory checksum.
7. **A real pre-existing defect surfaced, not introduced:** the lipid
   panel's independent TC/TG/HDL sampling (a design choice from M4B,
   unchanged by this milestone) produces internally-impossible panels
   in 2.28% of records and LDL-at-clip-floor in 9.83%. Counted and
   disclosed rather than hidden; not corrected (fixing it is reserved as
   a separate human decision, §14 Decision 1).
8. **A separate, engineering-only ECG pilot** fixed a measurement bug in
   the *inherited* GAN's existing evaluation (it had been comparing
   generated samples to its own training-fold data, not held-out data)
   — re-evaluated using already-existing checkpoints and already-
   generated samples, no retraining, no new model. See §12.

Full detail: `docs/M8_FULL_DATASET_VALIDATION_REPORT.md`,
`docs/M8_ECG_HELDOUT_PILOT_REPORT.md`, `validation/pilot_50_records/`,
`docs/DECISIONS.md` D017.

### 7.10 M8 Decision Brief (COMPLETE 2026-10-21)

Immediately following M5.5, a consolidated decision brief
(`docs/M8_DECISION_BRIEF.md`) was produced, listing every open human
decision separately (not combined), a full ECG model comparison, and an
M6 scope/sequencing analysis — see §14 and §12 below, which summarize
it. **No decision was made in that brief; it is a menu, not a
resolution.**

---

## 8. Data Sources and Evidence Base

Every generated field traces to a cited source. The major sources in
use, and what each one actually supports (not more):

| Source | Used for | What it does / does not support |
|---|---|---|
| **PTB-XL 1.0.1** | ECG metadata (ecg_id, superclass labels, strat_fold, sampling rate, signal shape); the GAN's training/held-out data | Real, licensed (CC BY 4.0) 12-lead ECG database with diagnostic superclass labels and a pre-defined 10-fold stratified split (1–8 train, 9 validation, 10 test) — **signal itself not yet attached to any synthetic patient record** (D003). |
| **Census of India 2011** | age (engineering default, not evidence-backed — see below), sex, state, urban/rural marginals | National, all-ages general population — the broadest demographic source, but not health-specific. |
| **ICMR-NNMS 2017-18** (National NCD Monitoring Survey) | BMI, smoking status, antihypertensive/antidiabetic treatment rates | Adults 18–69 (narrower than this project's 20–89 generator range — an accepted, documented extrapolation). Category-level prevalence only for BMI, not a continuous distribution. |
| **ICMR-INDIAB-17** (2023, Anjana et al., *Lancet Diabetes & Endocrinology*) | Hypertension and diabetes national marginals, lipid marginals | Adults 20+, 113,043 participants, all states/UTs — this project's single most evidence-backed variable (diabetes label). Marginal only, no accessible age/sex-stratified table. |
| **ICMR-INDIAB-25** (2026) | LAI_2020 lipid interpretation definition | A second, independently-evidenced clinical lipid threshold, preserved alongside NCEP rather than chosen over it (D011/D014). |
| **ICMR-INDIAB-12** (2022) | HbA1c age/sex-conditioned trend, non-diabetic only | Supports the *reverse-direction* architecture (diabetes label primary, HbA1c conditional on it) — insufficient diabetic-population HbA1c evidence exists. |
| **NFHS-5** (National Family Health Survey, 2019–21) | Blood pressure age-band × sex means and (derived) SDs | The newest evidence addition (M5.5). Covers men to age 54, women to 49 — narrower than this project's 20–89 range; the oldest available band is held constant above that, not extrapolated further. **Must not be read as this project's blood-pressure marginal** — BP is truncated to the hypertension label's definition, so the generated distribution is NFHS-5's shape reweighted to INDIAB-17's prevalence, not a direct reproduction of NFHS-5 itself. |
| **LASI** (Longitudinal Ageing Study in India) | Candidate for family-history-of-diabetes (14.33%, ages 45+ only) | **Not currently used** — an open scope decision (§14 Decision 2), not an evidence gap. |
| **NSS 75th Round** | Considered for healthcare-utilization/encounters | **Not used** — measures expenditure behavior, not clinical encounters; classified "E — Not Used" in `docs/INDIAN_GENERATION_STRATEGY.md`. |

**What has no evidence at all, and is therefore not generated:** a
national mean *and* standard deviation of Indian adult height by sex (6
total research attempts across M4-0 and M5.5); family history of CVD
specifically (confirmed absent across 9+ datasets examined); any
disease beyond hypertension/diabetes/hyperlipidemia at the diagnosis
level; any cardiovascular event (MI, stroke) or procedure history.

---

## 9. The Generation Pipeline, As It Exists Today

Dependency order (`generation/indian_population.py`
`generate_indian_attributes()`, `generation/clinical_history.py`):

```text
patient_id
   ↓
age → sex → state → urban_rural               (Census 2011 + engineering default for age)
   ↓
BMI (sex-conditioned)  →  smoking_status (sex-conditioned)        (NNMS)
   ↓
hypertension  →  diabetes  →  hyperlipidemia   (unconditioned national marginals, INDIAB-17)
   ↓
lipid panel: TC, TG, HDL sampled independently; LDL DERIVED (Friedewald)
   ↓
lipid_interpretations: COMPUTED per definition (NCEP_ATP_III, LAI_2020) — never sampled
   ↓
HbA1c: generated conditional on diabetes label, non-diabetics only   (INDIAB-12)
   ↓
medication_treatment: Bernoulli per diagnosed condition present      (NNMS treatment rates)
   ↓
height_cm: returns None (no evidence) — weight_kg: derived from BMI×height, None while height is None
   ↓
blood_pressure: generated CONDITIONAL on hypertension label + medication_treatment   (NFHS-5, D017)
   ↓
diagnoses: 1:1 PROMOTION of hypertension/diabetes flags — never independently sampled
   ↓
medical_history: REFERENCES diagnoses — never re-derived
   ↓
medications: REFERENCES diagnoses + medication_treatment outcome — never resampled
   ↓
encounters: ONE structural container naming which measurements exist  (D017)
   ↓
clinical_timeline: INDEXES the encounter by reference_id — never a new date source
```

Every arrow above is either "sampled from a cited evidence distribution"
or "deterministically derived/referenced from something already
generated earlier in the chain" — there is exactly one random draw per
evidence-backed quantity, never two independent rolls of the same fact.

Blood pressure is deliberately drawn **last** in this order so that, for
any already-migrated or already-generated record, every field before it
is byte-identical regardless of whether BP is present — this is what
lets the v0.7→v0.8 migration *replay* a record's own seed rather than
regenerate it from scratch.

---

## 10. The Validation Framework

Four distinct layers, each with its own module, none duplicating
another:

1. **Structural** (`validation/structural.py`) — schema compliance:
   patient_id format, schema_version match, field types/ranges/allowed
   values, duplicate-ID detection. Generator-independent — it does not
   know or care *how* a record was produced, only whether it is
   well-formed.
2. **Clinical consistency** (`validation/clinical_consistency.py`) —
   cross-field rules: does the hypertension diagnosis match the
   risk-factor flag; does blood pressure satisfy its own label's
   definition; does the derived LDL match a fresh Friedewald
   recomputation; is HbA1c present exactly for non-diabetics; are
   encounters/timeline references internally consistent. Recomputes
   expected values from the generation functions themselves rather than
   keeping an independent second copy of each rule — "a second,
   independent implementation of the same rule would itself become a
   consistency risk."
3. **Statistical** (`validation/statistical.py`) — population-level
   distribution checks (chi-square goodness-of-fit, exact binomial,
   one-sample KS) comparing observed generation output against
   `configs/indian_population.yaml`'s own cited parameters. A sanity
   check, explicitly not proof the output matches any real population.
4. **Migration integrity** (`integration/validate_clinical_population.py`
   `--compare-source`) — added at M5.5: re-derives every output record
   fresh from its untouched source via the actual migration function,
   and diffs the result byte-for-byte against what is on disk. Catches
   disk corruption, truncation, and non-determinism — not just "does
   this record look fine in isolation."

All four layers were run at full 100,000-record scale for the current
v0.8 dataset (§11) — not sampled, not estimated.

---

## 11. Current Dataset State — Exact Figures

Two full-scale datasets currently exist, both intact and independently
verified as of this writing:

### 11.1 `outputs/m5/100k_patients/` — Schema v0.7, the M5 baseline

- 100,000 records, seed 42.
- **Immutable source input** to the v0.8 migration — never modified.
- `blood_pressure` field does not exist; `encounters` null;
  `TimelineEvent` has no `reference_id`.
- Validated at generation time: 0 generation errors, 0 duplicate IDs,
  100,000/100,000 structurally valid, 100,000/100,000 clinically
  consistent, 0 errors, 0 warnings (under the v0.7 validator — the
  lipid-feasibility check did not exist yet at that time).

### 11.2 `outputs/m8/100k_patients_v08/` — Schema v0.8, the current authoritative dataset

- 100,000 records, migrated from the M5 baseline via `integration/
  migrate_v07_to_v08.py`.
- **Frozen** — `outputs/m8/dataset_manifest.json`, directory checksum
  `8f14c4b6c42d671344b69174e1066f4cd1dd07df159d25ef14404b4d5f6a9aa6`
  (independently recomputed and matched at the time of this writing).
- **100,000/100,000 structurally valid** (recomputed, not trusted from
  the stored flag).
- **100,000/100,000 clinically consistent** (0 errors).
- **0 duplicate patient IDs.**
- **100,000/100,000 migration-integrity exact matches** — 0 differences,
  0 orphaned records in either direction against the v0.7 source.
- **16,297 clinical warnings**, all pre-existing/documented, none newly
  introduced:
  - 7,548 (7.55%) — LDL clipped at its documented floor, feasible but
    not a Friedewald derivation.
  - 6,466 (6.47%) — `ecg.superclasses` empty (a PTB-XL label gap,
    unrelated to this migration).
  - 2,283 (2.28%) — lipid panel internally impossible (total
    cholesterol below the sum of its own HDL + triglyceride
    components).
- **Blood pressure:** mean SBP 125.04 (sd 15.54), mean DBP 82.53 (sd
  10.26), mean pulse pressure 42.51 (sd 10.47) — matches the published
  NFHS-5 pulse-pressure figure (42.9 ± 9.5) to within 1%. 0
  systolic≤diastolic violations. 0 pulse-pressure-below-20mmHg
  violations (the declared engineering floor holds exactly). 31,655
  (31.66%) raised-BP records. 52,684 (52.68%) age-band-extrapolated
  records (flagged per-record via `extrapolated_beyond_source_
  age_range`).
- **Missingness, with reason** (none accidental): `family_history`/
  `echo` 100% null (open scope decision / scope entirely open);
  `labs` 11.46% null (exactly the diabetic patients); `medications`
  90.80% null (treatment-rate gated, matches NNMS design); `diagnoses`/
  `medical_history` 57.18% null (patients with neither hypertension nor
  diabetes); `encounters` 0% null (newly populated).
- **ECG:** `signal_available: false` on all 100,000 records (D003
  boundary intact, re-verified explicitly, not assumed).

### 11.3 What changed between the two datasets, precisely

Only: `demographics.height_cm`/`weight_kg` (written as explicit `null`
rather than absent), `blood_pressure` (new), `encounters` (new),
`clinical_timeline` (extended with `reference_id`), `provenance`
(schema_version bump + appended generator string), `validation` (re-run
result). **Every other field is enforced byte-identical** by the
migration's own `_UNCHANGED_FIELDS` check and independently reconfirmed
by the migration-integrity validator.

---

## 12. The ECG / Multimodal Track

### 12.1 What already existed (inherited, not built by this project)

`syngen/SynGen/SynGen/` contains a complete, already-trained DCGAN-style
ECG generator: 5 independent `Generator`/`Discriminator` pairs, one per
PTB-XL diagnostic superclass (NORM, MI, STTC, CD, HYP), with trained
checkpoints (~135MB each) already on disk, plus already-generated
synthetic samples (500 per class) and a prior evaluation pipeline. A
thorough prior audit (`docs/syngen-codebase-analysis.md`) catalogued
this codebase file-by-file, including a file-identity mismatch problem
(several files' docstrings don't match their actual contents — a sign
of two disconnected AI-assisted authoring sessions) and one **HIGH**
finding: the existing evaluation compared generated samples against the
GAN's own **training**-fold data, not held-out data, overstating
quality.

### 12.2 What M6/M7 did (research only, no model selected)

Five research tracks were run to evaluate replacing or supplementing
the inherited GAN:
- Hardware/compute feasibility: no blocking case found up to 1M
  waveforms on local hardware (8GB or 36GB GPU); AWS not required.
- Candidate landscape: **SSSD-ECG** identified as the strongest
  alternative (MIT-licensed code, PTB-XL SCP-code conditioning).
  CardioSynth/CardioSync (the spec's originally-named candidate,
  `CLAUDE.md` Stage 11) — **confirmed not viable as-is**, the only real
  GitHub match is an unlicensed single-lead demo scaffold.
- Three further candidates (DiffuSETS, FlowECG, cNVAE-ECG) audited and
  found less suitable than SSSD-ECG (no conditioning match, no released
  weights, or an unclear/restrictive license respectively). A fourth
  (FEM-simulator VAE) rejected outright — promised code release not
  present, zero real-patient training data.
- SSSD-ECG compatibility: shape/rate partially compatible (needs a
  lossless tensor-axis/lead-order conversion); a conditioning-vector
  dimension discrepancy (44 vs. 71) remains unresolved; the data needed
  to build its conditioning vector is already present locally, just not
  yet extracted into code.
- **The single blocking unknown, unchanged through M5.5:** SSSD-ECG's
  pretrained-weight license. The Figshare share link returns HTTP 403
  on every automated fetch — **requires a human with an authenticated
  browser session.** Code license (MIT), PTB-XL license (CC BY 4.0), and
  NeuroKit2 license (MIT) are all confirmed; only the weight license
  remains open.

**No model has been selected.** This is an explicit, repeatedly
reaffirmed human checkpoint (`CLAUDE.md` §28 "Model selection"),
unaffected by any subsequent milestone.

### 12.3 What M5.5 added to this track (engineering only)

Re-evaluated the inherited GAN's **already-generated** samples against
true held-out (PTB-XL fold 9, never-trained-on) real data, fixing the
training-fold-leakage bug the prior audit had found — no retraining, no
new generation, no new dependency. Result: held-out KS statistics are
within ±0.008 of the originally-reported (leaky) ones across all 5
classes — the model is **not** memorizing its training set, though
absolute quality (KS≈0.07–0.10) sits at the boundary of the scripts' own
"excellent" (<0.1) threshold, not comfortably inside it. Confirmed from
the architecture itself (not assumed) that **no patient demographic or
clinical field conditions this model** — the 5 generators share no
weights and take no conditioning vector; "conditioning" is only "which
of 5 files to sample from." Amplitude calibration remains unconfirmed
(per-record normalization statistics are computed and discarded, never
persisted — a generated value cannot be mapped back to physical mV).

### 12.4 Current status, precisely

| Model | License | Patient conditioning | Held-out evaluation | Amplitude calibration | Status |
|---|---|---|---|---|---|
| Inherited GAN | No LICENSE file (internal project code) | **None** — class-only, 5 independent generators | **Done** (M5.5) — no memorization evidence, quality at the boundary of "excellent" | **Not calibrated** — confirmed gap | Usable as a pilot candidate; two disclosed gaps |
| SSSD-ECG | Code MIT (confirmed); **weights UNKNOWN** | SCP-code vector — dimension mismatch unresolved | Not possible — no checkpoint loaded | Unconfirmed | **Blocked** on a credential this project cannot obtain itself |

**Neither model is cleared for large-scale generation.** No ECG
waveform exists for any synthetic patient record in this project as of
this writing. `ecg.signal_available` is `false` on every record in
both the v0.7 and v0.8 datasets.

---

## 13. Known Limitations and Accepted Gaps — Complete List

Organized by whether each is (a) a disclosed engineering assumption,
(b) a genuinely unresolved evidence gap, or (c) an open scope/policy
decision. None of these are hidden — every one is cited in at least one
of `docs/DECISIONS.md`, `configs/indian_population.yaml`, or the M8
reports.

**Engineering assumptions (disclosed, measured, reversible):**
- Blood-pressure pulse-pressure floor of 20mmHg — the only *set* (not
  derived or read-off) value in the BP design.
- Age held constant above NFHS-5's source coverage (men>54, women>49)
  rather than extrapolated further — deliberately conservative
  (understates rather than invents a continuing trend).
- Within-BMI-category continuous sampling is uniform (no evidence for
  the interior shape) — the oldest such assumption in the project,
  predating M4.

**Evidence gaps (no source found despite genuine search):**
- Height/weight: no national adult-height mean+SD by sex, after 6 total
  research attempts. BMI remains the evidence-primary anthropometric
  variable instead.
- Age distribution itself: no adult age-band distribution found;
  `uniform(20,89)` is an engineering default, explicitly reconfirmed as
  such at M2D even after locating a better-sourced but still too coarse
  alternative.
- Family history of CVD: confirmed absent across 9+ datasets examined.
- Any disease beyond hypertension/diabetes/hyperlipidemia at the
  diagnosis level; any cardiovascular event or procedure history.
- Medication start/stop dates: NNMS gives only a point-prevalence
  "currently treated" figure, no initiation-date or duration evidence.
- ECG amplitude/physical-unit calibration (inherited GAN); SSSD-ECG's
  output convention also unconfirmed.

**Open scope/policy decisions (evidence may exist, but the choice of
what to do with it is not an implementer's call):**
- Family-history-of-diabetes (LASI, 45+ only) — populate for a
  sub-population, or not at all.
- Which lipid definition (if any) should drive a future hyperlipidemia
  diagnosis.
- Whether `encounters` should remain a structural container or revert
  to null.
- ECG model selection (§12, and the license credential specifically).

**Pre-existing defects, surfaced not introduced:**
- Lipid panel internal-feasibility: 2.28% of the full dataset have an
  internally impossible panel (TC below the sum of its own
  components); 9.83% have LDL at the clip floor rather than a true
  derivation. Root cause: TC/TG/HDL sampled as independent marginals
  (an M4B design decision, unchanged since). Counted and disclosed as a
  validator **warning** (the stored LDL does follow its documented
  clip rule), not promoted to an error; not corrected without a
  separate decision.
- `ecg.superclasses` empty in 6.47% of records — a genuine PTB-XL label
  gap, not something this project invented or should guess at.

---

## 14. Every Currently Open Human Decision

Full detail, options, evidence, and recommendations for each of these
live in **`docs/M8_DECISION_BRIEF.md`** — summarized here for
completeness of this context document. **None of these has been
resolved; none should be inferred as approved by silence.**

1. **Lipid panel sampling** — keep independent TC/TG/HDL sampling
   (current), or constrain it so every triple is feasible? Blocks
   nothing currently; would improve clinical-review credibility if
   resolved.
2. **Family-history scope** — populate the one LASI-sourced 45+
   diabetes-family-history figure for part of the population, or leave
   the field null entirely?
3. **`encounters` field shape** — keep the declared structural
   container, or revert to `null` pending a different care-utilization
   model?
4. **Blood-pressure pulse-pressure floor** — is 20mmHg an acceptable
   engineering threshold?
5. **ECG model selection** — inherited GAN, SSSD-ECG (license-blocked),
   or neither yet? Blocks all of Stage 4/ECG-related M6 work.
6. **Hyperlipidemia-diagnosis definition** (carried forward from M4D) —
   which lipid interpretation, if any, should drive a future diagnosis
   entry? Also blocks a potential future statin medication.
7. **Patient-level `birth_date` field** (carried forward from M4) — add
   it to support future date-consistency checks?

**Recommended unblocked next actions** (per the decision brief, not
requiring any of the above to be resolved first): M6 candidates (b)
hyperlipidemia-diagnosis resolution and (c) pattern discovery over the
v0.8 baseline, and/or Decision 1 (the lipid-sampling fix) — all three
are independent of each other and of the ECG-licensing blocker.

---

## 15. Future Plan and Direction

Restating `CLAUDE.md`'s own later stages verbatim in intent (§2.1
onward), since this is the part of the project not yet begun and
therefore the part most important to preserve accurately:

### Stage 7 (CLAUDE.md numbering) — Progressive Scaling

**Already satisfied** through 100,000 records at both schema v0.7 (M5)
and v0.8 (M5.5), each validated before scaling further. 1,000,000-record
scale has been estimated (linearly extrapolated: ~3.55GB, ~4 hours) but
**not independently verified at that scale**.

### Stage 8 — Large Dataset Creation

**Satisfied** — the v0.8 dataset carries consistent schema, provenance,
full validation results, reproducibility information (every record's
generation seed is recorded and replayable), and dataset-level metadata
(the manifest).

### Stage 9 — Pattern Discovery (PROJECT_STATE Stage 7 — NOT STARTED)

The next substantive unstarted phase. Intended analyses per `CLAUDE.md`:
demographic distributions, risk-factor relationships, disease patterns,
medication patterns, lab relationships, ECG patterns (once waveforms
exist), temporal relationships, combinations of cardiovascular
conditions, missingness patterns, population clusters, correlations and
dependencies — each explicitly required to distinguish **observed in
generated data** vs. **assumed** vs. **externally supported**, and
explicitly forbidden from turning a correlation into unsupported medical
causation.

### Stage 10 — Indian Demographic Conditioning (PROJECT_STATE Stage 8 — NOT STARTED)

After pattern analysis, incorporate Indian demographic characteristics
into *downstream* generation specifically (distinct from the
demographic generation already done for the 100K baseline itself). The
exact conditioning mechanism is explicitly **not yet finalized** in the
spec — it depends on what Stage 9's pattern discovery actually finds,
what the selected generative model can accept, and what further
evidence is available. The spec is explicit that a variable should not
be used merely because it happens to be available.

### Stage 11 — Generative Model Integration (PROJECT_STATE Stage 9 — NOT STARTED, partially researched)

The project does **not** aim to train a model from scratch; the
intended strategy is "validated dataset + discovered patterns + Indian
demographic characteristics → an existing suitable generative model →
new synthetic patient information." The spec's originally-named
candidate, CardioSynth/CardioSync, has since been **found not viable**
(§12.2) — this is itself useful evidence that the spec's named
candidate was provisional, not committal, exactly as the spec itself
states ("This is NOT a final architectural decision"). SSSD-ECG is the
current strongest researched alternative, blocked on a license
credential (§12, §14 Decision 5). Model selection remains a human
checkpoint regardless of which candidate is eventually chosen.

### Stage 12 — Final Generation Pipeline (PROJECT_STATE Stage 10 — NOT STARTED)

The intended final architecture: Indian demographic/context information
+ relevant patient context + validated population patterns → the
selected model → synthetic patient fields/records → a validator the
generative model is explicitly forbidden from bypassing → final output.

### Separately — Echo

Echocardiography remains completely unaddressed (`echo: null` in 100%
of records) — the spec itself states its scope is "entirely open" and
that no placeholder measurement, image, video, or report should be
fabricated before its source, representation, and generation method are
established. This is a distinct future workstream from ECG, not a
sub-part of it.

---

## 16. Stage-Numbering Note: Two Schemes Exist

`CLAUDE.md` §11 defines **13 stages (Stage 0–12)**. `docs/
PROJECT_STATE.md`'s own "Project Stages" section tracks a **compressed
11-stage version (Stage 0–10)**, merging CLAUDE.md's Stage 5
("Additional Modalities") into its own Stage 4, and shifting everything
from Stage 6 onward down by one, with Stages 7+8 (Progressive
Scaling + Large Dataset Creation) further merged into a single Stage 6
("Scaling"). Exact mapping:

| CLAUDE.md Stage | PROJECT_STATE.md Stage | Name |
|---|---|---|
| 0 | 0 | Project Definition |
| 1 | 1 | Existing Codebase Understanding |
| 2 | 2 | Foundation |
| 3 | 3 | Patient Generation |
| 4 | 4 | ECG/Multimodal Integration |
| 5 | *(merged into 4)* | Additional Modalities |
| 6 | 5 | Validation & Quality Control |
| 7 + 8 | 6 | Scaling (Progressive Scaling + Large Dataset Creation merged) |
| 9 | 7 | Pattern Discovery |
| 10 | 8 | Indian Demographic Conditioning |
| 11 | 9 | Generative Model Integration |
| 12 | 10 | Final Generation Pipeline |

**When reading any document, check which numbering it uses** — this
document uses `PROJECT_STATE.md`'s numbering when citing "Stage N"
without further qualification, and names `CLAUDE.md`'s numbering
explicitly when citing it.

---

## 17. Quick-Reference: Entry Points and Reusable Components

| Need to… | Use |
|---|---|
| Generate one fresh patient at the current schema | `integration/build_patient.py` |
| Migrate existing v0.7 records to v0.8 | `integration/migrate_v07_to_v08.py` (`migrate_record()` / `migrate_paths()` / CLI with `--dry-run`) |
| Validate an entire population directory | `integration/validate_clinical_population.py` (`--compare-source`, `--stats`, `--json-out`) |
| Freeze/manifest a dataset version | `integration/freeze_dataset_manifest.py` |
| Re-evaluate the inherited ECG GAN | `integration/ecg_pilot_heldout_evaluation.py` |
| Look up every generation parameter's evidence | `configs/indian_population.yaml` |
| Look up the patient schema / controlled vocabularies | `schemas/patient_schema.py` |
| Look up a past architectural decision | `docs/DECISIONS.md` (D001–D017) |
| Check the live milestone/decision status | `docs/PROJECT_STATE.md` |
| Check every currently-open decision at once | `docs/M8_DECISION_BRIEF.md` |
| Reuse PTB-XL loading / label mapping | `ingestion/ptbxl_source.py` (wraps syngen's `build_label_map()`) |
| Reuse the inherited GAN | `syngen/SynGen/SynGen/gan_pytorch.py` (the only file anything else in that subtree actually imports — see `docs/syngen-codebase-analysis.md` §13 before trusting any other file's docstring) |
| Run the test suite | `pytest tests/` — 142 tests across 9 files, one per milestone's generation logic |

---

## 18. Project Governance and Conventions

- **Reproducibility is mandatory**: every generated patient's seed is
  recorded in its own provenance; the same `(sequence, seed)` always
  reselects the same underlying PTB-XL record and regenerates the same
  Indian-conditioned attributes.
- **Tests are added per milestone**, not retrofitted later — each
  `tests/test_m*.py` file corresponds to the milestone that introduced
  the logic it tests. 142/142 currently passing.
- **No per-milestone git commits** by standing convention — the
  working tree accumulates milestone work; `docs/PROJECT_STATE.md` and
  `docs/DECISIONS.md` are the change record, not git log.
- **Generated datasets are never committed** (`.gitignore` excludes
  `outputs/`); large inherited binary assets (PTB-XL raw data, GAN
  checkpoints, generated `.npy` arrays) are excluded the same way, while
  the inherited `.py` code that produced them stays tracked.
- **"What not to do"** (`CLAUDE.md` §38, worth internalizing): don't
  restart the codebase audit without new evidence; don't introduce
  speculative abstractions; don't skip validation to move faster; don't
  silently make a major architectural decision; don't fabricate data to
  fill a gap.

---

## 19. How to Resume Work From Here

1. Read `docs/PROJECT_STATE.md`'s "Last Completed Action" and "Next
   Action" sections first — they are the single most current summary.
2. Read `docs/M8_DECISION_BRIEF.md` for every open decision, with
   options and a recommendation for each.
3. **Do not** re-run the v0.7→v0.8 migration, re-validate the full
   100,000-record dataset from scratch, or regenerate ECG evaluation
   artifacts unless there is a specific reason to believe something has
   changed since this document was written — all of that has already
   been done and independently verified (§11).
4. The two genuinely unblocked next steps, per the decision brief, are:
   resolving the hyperlipidemia-diagnosis-definition question (M4D/M6
   candidate b) and/or pattern discovery over the v0.8 baseline (Stage
   9/M6 candidate c) — neither requires the ECG-licensing blocker to be
   resolved first.
5. ECG work of any kind beyond what's already been done (§12) requires
   either a human confirming the SSSD-ECG pretrained-weight license, or
   a human explicitly deciding to proceed with the inherited GAN despite
   its two disclosed gaps (no patient conditioning, no amplitude
   calibration) — this agent cannot resolve either on its own.
