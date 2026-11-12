# M8 Decision Brief — Outstanding Human Decisions After Schema v0.8 Migration

**Purpose:** per `CLAUDE.md` §28/§29 ("Human Checkpoints" / checkpoint
report format), this is the single consolidated decision brief for
every unresolved human decision currently open in the project. It does
not make any of these decisions. It does not start M6. It does not
touch either frozen dataset or generate any ECG waveform (verified in
§7).

**Verification method:** every claim below was re-read from the actual
current files in this pass (not reused from a prior session's summary).
File paths and line-level citations are given throughout.

---

## 1. Verified Current Checkpoint

Re-read directly from source, this session:

| Item | Verified state | Source |
|---|---|---|
| v0.7 source dataset | 100,000 files, schema 0.7, **unmodified** | `outputs/m5/100k_patients/` — `PAT_000001.json` re-checked: `schema_version: "0.7"`, `blood_pressure: null` |
| v0.8 migrated dataset | 100,000 files, schema 0.8 | `outputs/m8/100k_patients_v08/` — `PAT_000001.json` re-checked: `schema_version: "0.8"`, `blood_pressure` populated |
| v0.8 dataset integrity | **Directory checksum recomputed fresh and compared against the frozen manifest: exact match** (`8f14c4b6c42d671344b69174e1066f4cd1dd07df159d25ef14404b4d5f6a9aa6`) | `outputs/m8/dataset_manifest.json` vs. live recomputation |
| Full-dataset validation | 100,000/100,000 structurally valid, 100,000/100,000 clinically consistent, 100,000/100,000 migration-integrity exact matches, 0 duplicate IDs | `docs/M8_FULL_DATASET_VALIDATION_REPORT.json` (re-read) |
| ECG held-out pilot | Completed; held-out KS within ±0.008 of originally-reported (leaky) KS across all 5 classes; variance 0.25–0.31 (no mode-collapse signal) | `docs/M8_ECG_HELDOUT_PILOT_REPORT.json` (re-read) |
| Test suite | 142/142 passing | re-run this session |
| Project milestone tracker | `docs/PROJECT_STATE.md` — M5.5 marked COMPLETE; M6 marked NOT STARTED, "awaiting explicit authorization" (unchanged wording from before M5.5) | re-read, lines 488–581, 582–650 |
| Architectural decision log | `docs/DECISIONS.md` D017 (schema v0.8) is the newest entry; no entry has been added since | re-read, lines 1–20 |
| Existing loop/milestone mechanism | No separate scheduler or loop codebase exists. The project's "loop" is `CLAUDE.md` §11 (static stage/phase definitions) driving `docs/PROJECT_STATE.md` (the live, hand-maintained tracker) plus the §28/§29 human-checkpoint convention this brief follows | confirmed by repo-wide search; no `loop.py`/scheduler file found anywhere in the tree |
| Stray processes | None | `Get-Process python` returns empty |

**No milestone was rerun. No file under either dataset directory was
written to in this pass.**

---

## 2. Clarifying "two independent sampling decisions"

**That exact phrase does not appear anywhere in this project's
documentation.** It does not appear in `docs/PROJECT_STATE.md`,
`docs/DECISIONS.md`, or either M8 report. It is not guessed at further
below — instead, here is what it most likely derives from, stated
plainly so the discrepancy is visible rather than silently resolved:

The prior session's closing summary said: *"two independent threads are
available next, neither requiring the other: 1. A lipid-sampling
decision... 2. M6: still awaiting explicit authorization."* That is
**one sampling decision and one milestone-authorization decision** —
not two sampling decisions. M6 is not itself a sampling question; it is
a bucket of candidate next milestones (§4 below), only one of which
(ECG model selection) is even evidence-and-permissions-gated the way a
sampling decision is.

If a second genuine *sampling* decision was intended, the only other
candidate in the current documentation is the **blood-pressure
pulse-pressure floor** (item 4 in §3) — also a sampling-design choice,
distinct from the lipid one. Both are listed separately below. No
single documented source currently groups them as a pair called
"sampling decisions," so this brief treats them as two of **seven**
separate open items, not as "the two sampling decisions."

---

## 3. Every Outstanding Human Decision, Listed Separately

Five from M5.5 (schema v0.8) plus two carried forward unresolved from
earlier milestones. Each is independent — resolving one does not
require or imply resolving another.

### Decision 1 — Lipid panel sampling (clinical/statistical)

- **Exact question:** Should `total_cholesterol`, `triglycerides`, and
  `HDL` continue to be sampled as three independent marginals (current,
  pre-existing M4B design), or should sampling be constrained so every
  generated triple satisfies `TC ≥ HDL + TG/5` (Friedewald feasibility)?
- **Why it matters:** independence is what produces infeasible panels.
  At full scale: **2,283 records (2.28%)** have a total cholesterol
  below the sum of their own HDL and triglyceride components (a
  physical impossibility); **9,831 records (9.83%)** have an LDL value
  that is the documented clip floor (30 mg/dL) rather than a Friedewald
  derivation. A clinical reviewer will reasonably read the 2.28% as a
  data error.
- **Options:**
  1. Leave as-is, documented as an accepted limitation (current state).
  2. Constrain sampling (e.g., sample TC first, then HDL/TG conditioned
     to keep the triple feasible) — preserves existing marginals as
     closely as possible.
  3. Redefine which quantity is "primary" (e.g., sample LDL/HDL/TG,
     derive TC additively) — a larger architectural change, reopens the
     raw-value-primary pattern D011 established for lipids.
  4. Reject-and-redraw infeasible triples — smallest code change,
     preserves every existing marginal's evidence basis exactly, no new
     assumption introduced.
- **Evidence already gathered:** exact rates recomputed from the full
  100,000-record output this session (`docs/
  M8_FULL_DATASET_VALIDATION_REPORT.json`); root-cause analysis in
  `validation/pilot_50_records/reports/validation_report.md` §6.1.
- **Risks / downstream consequences:** leaving it unresolved risks a
  credibility finding in any external clinical review. Option 4 is
  believed lowest-risk but has not been implemented or tested — doing
  so without approval would be exactly the kind of clinical/statistical
  decision this task reserves for a human.
- **Recommendation:** Option 4 (reject-and-redraw) as the smallest,
  evidence-neutral fix, **contingent on approval** — not implemented.
- **Blocks:** no current milestone. Does not block M6. Would need to
  precede any dataset re-freeze intended to resolve it.

### Decision 2 — Family-history scope (clinical/statistical)

- **Exact question:** Generate the one evidence-backed figure (LASI
  2017-18, diabetes family history, ages 45+ only, 14.33% prevalence)
  for the sub-population it actually covers, or leave `family_history`
  null for the entire population as now?
- **Why it matters:** partial-population coverage (younger patients
  would have no value while older ones would) vs. no coverage at all is
  a product-scope choice, not an evidence gap — the evidence exists but
  only for part of the target population.
- **Options:** (a) leave null (current), (b) populate for ages 45+ only
  and leave null below that, (c) do not pursue further.
- **Evidence already gathered:** `docs/M4F_FINAL_CLINICAL_AUDIT.md`
  classifies this "C — requires explicit human decision" (pre-dates
  M5.5, unchanged by it).
- **Risks:** populating only part of the population without clearly
  flagging the age cutoff could read as inconsistent coverage.
- **Recommendation:** no recommendation offered — this is a scope
  preference, not an evidence question this brief can resolve.
- **Blocks:** nothing currently.

### Decision 3 — `encounters` field shape (engineering/design)

- **Exact question:** Should `encounters` keep holding one declared
  structural container (`synthetic_baseline_assessment`, naming the
  single measurement date a record already has) per record, or should
  it revert to `null` pending a different, evidence-backed
  care-utilization model?
- **Why it matters:** the current container is explicitly **not** a
  claimed healthcare visit, but a reviewer unfamiliar with that
  distinction could misread it as one.
- **Options:** (a) keep as-is, (b) revert to `null`, re-migrate.
- **Evidence:** `docs/CLINICAL_RECORD_DESIGN.md` §H (the original design
  fork); no Indian healthcare-utilization evidence source was found
  (NSS 75th Round measures expenditure, not clinical encounters, per
  `docs/INDIAN_GENERATION_STRATEGY.md`).
- **Risks:** low either way — cheap to reverse (one field, no
  downstream dependency on its contents besides the timeline reference,
  which would simply shrink to one event).
- **Recommendation:** keep as-is; the distinction is already documented
  in the schema docstring and every report. No recommendation to change
  without a specific reviewer objection.
- **Blocks:** nothing.

### Decision 4 — Blood-pressure pulse-pressure floor (clinical/statistical, the second genuine sampling decision)

- **Exact question:** Is a 20 mmHg minimum pulse pressure (systolic −
  diastolic) an acceptable engineering threshold for the blood-pressure
  generator?
- **Why it matters:** it is the **only** value in the entire BP design
  that was set by judgement rather than read off a source or derived
  from one. Measured effect: independent SBP/DBP sampling produced
  pulse pressure <20 mmHg in 10.70% of draws (clinically implausible at
  those absolute BP levels); adding a derived SBP/DBP correlation
  (r=0.7255, itself derived from published variances) cut that to
  1.98%; the floor removes the remainder, to 0%.
- **Options:** (a) keep 20 mmHg (current), (b) choose a different
  threshold, (c) remove the floor and accept the 1.98% residual.
- **Evidence:** `configs/indian_population.yaml`
  `risk_factors.blood_pressure.distribution.min_pulse_pressure_mm_hg`
  and its surrounding comment carry the full measured progression.
- **Risks:** too high a floor would silently exclude real narrow-PP
  physiology; too low reintroduces implausible records. 20 mmHg was
  chosen as the conventional clinical boundary for "narrow pulse
  pressure," not derived from an Indian-specific source.
- **Recommendation:** keep 20 mmHg; it is disclosed, asymmetric (no
  upper cap, since wide PP is real in older hypertensives), and
  measured to be the smallest intervention that resolves the defect.
- **Blocks:** nothing.

### Decision 5 — ECG model selection (architectural / external-dependency / licensing)

- **Exact question:** Which model, if any, should generate synthetic
  ECG waveforms for this dataset: the inherited per-class GAN, SSSD-ECG,
  one of the three other audited candidates, or none yet?
- **Full comparison:** §5 below (kept separate from every other
  decision per instruction — this is an architecture/external-dependency
  question, not a clinical-data-generation one).
- **Blocks:** all of Stage 4 (ECG/multimodal integration) and any work
  under M6's "ECG architecture decision" candidate.

### Decision 6 — Hyperlipidemia-diagnosis definition (carried forward, pre-M5.5, still open)

- **Exact question:** Should a future `diagnoses` entry for
  hyperlipidemia be derived from the NCEP_ATP_III `lipid_interpretations`
  definition, the LAI_2020 one, both, or neither?
- **Why it matters:** D011 explicitly declined to prefer one lipid
  definition over the other; picking one now to drive a diagnosis would
  silently make that choice. Also blocks a future statin-medication
  addition (no treatment-rate evidence exists for statins regardless).
- **Evidence:** `docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md` §3/§11.
- **Recommendation:** none offered — this is the same kind of
  guideline-preference question D011 already declined to resolve
  unilaterally.
- **Blocks:** no current milestone; would block a future statin
  medication addition.

### Decision 7 — Patient-level `birth_date` field (carried forward, pre-M5.5, still open)

- **Exact question:** Should a `birth_date` field be added so age-
  relative dates (e.g., a future diagnosis onset) can be validated
  against it?
- **Evidence:** `docs/M4_CLINICAL_ARCHITECTURE.md` §8.
- **Recommendation:** none offered; narrow, not urgent.
- **Blocks:** nothing currently; would matter if/when onset dates are
  ever added (no evidence for those exists either, per
  `docs/M4_CLINICAL_EVIDENCE.md` §7).

---

## 4. ECG Model Comparison (Decision 5, Full Detail)

All of the following is drawn from existing audits
(`docs/syngen-codebase-analysis.md`, `docs/M6_ECG_MODEL_SELECTION.md`,
`docs/M6_SSDD_ECG_COMPATIBILITY.md`, `docs/M7_0_*`,
`docs/M8_ECG_HELDOUT_PILOT_REPORT.md`) — **nothing new was downloaded,
trained, or evaluated for this brief.**

### 4.1 Head-to-head: inherited GAN vs. SSSD-ECG

| Dimension | Inherited per-class GAN (`syngen/SynGen/SynGen`) | SSSD-ECG |
|---|---|---|
| **Verified license — code** | No LICENSE file found in this subtree; treated as internal/inherited project code, not third-party redistributed software | **MIT — CONFIRMED** |
| **Verified license — pretrained weights** | N/A (weights are this project's own, already present locally) | **UNKNOWN.** Figshare link (`figshare.com/s/81834b24a4711c2a5c55`, DOI `10.6084/m9.figshare.21922875`) returns HTTP 403 on every automated fetch attempt across two sessions. **Requires a human with an authenticated browser session** — not resolved, not assumed resolved, not routed around |
| **Patient-specific clinical conditioning** | **None.** Confirmed from the architecture: 5 independent `Generator`/`Discriminator` pairs, one per diagnostic superclass, no shared weights, no class-conditioning vector. Selecting which checkpoint to sample from is the only "conditioning" — no age/sex/risk-factor field is read by the model | Conditions on a PTB-XL SCP-code vector — but the **exact dimensionality is unresolved**: the pretrained checkpoint's embedding layer expects 71 dimensions; this project's own label construction naturally produces a 44-code `label_diag`-style vector. Unresolved discrepancy (`docs/M6_ECG_MODEL_SELECTION.md` §2), not just an implementation detail — affects whether the checkpoint can even be loaded against this project's labels without further investigation |
| **Held-out evaluation completed** | **Yes, this session.** Fixed a pre-existing methodology bug (original eval compared against training-fold data) by re-evaluating against true held-out fold 9. Held-out KS stays within ±0.008 of the original (leaky) numbers across all 5 classes — not memorizing, but absolute KS (0.07–0.10) sits at the boundary of the scripts' own "excellent" (<0.1) threshold, not comfortably inside it | **Not evaluated at all in this project.** No checkpoint has been loaded (blocked on the license above), so no held-out or any other quality metric exists locally for this model |
| **Evaluation limitations** | Metrics are global/per-lead statistical comparisons (KS, KL, MSE, variance) — no beat-level morphology (QRS detection, interval measurement) has been run. A favorable KS/variance number is evidence against mode collapse and gross distributional mismatch; it is **not** evidence of clinical realism, which these metrics do not measure | N/A — no evaluation possible pre-license |
| **Signal amplitude calibration** | **Not calibrated — confirmed gap.** Per-record, per-lead z-score normalization is computed and discarded (`_normalise()`); a generated `[-1,1]` value cannot be mapped back to physical mV from the artifacts alone | **Unconfirmed.** M7-0's readiness spike could not determine the model's raw output amplitude convention from its fetched training code — an open question, not evaluated further because it's downstream of the license step |
| **Duplicate generation / mode collapse** | **No evidence of mode collapse.** Variance 0.25–0.31 (both held-out and original), far above the inherited code's own warning thresholds (<0.01 severe, <0.05 partial) | Not evaluated — no local instance to test |
| **Training data / leakage** | PTB-XL folds 1–8 (training), confirmed respecting this project's own `training_folds` config. The *held-out* re-evaluation this session used fold 9, never seen by any of the 5 generators | PTB-XL is the **sole** training data per the paper, but a leakage question specific to *reusing a third-party pretrained model* is open: this project's own fold discipline does not guarantee SSSD-ECG's **own** training run excluded folds 9/10 — unverified, flagged in `docs/PROJECT_STATE.md` M6 section as a "new leakage consideration specific to third-party pretrained models" |
| **Required implementation work before any generation** | None for continued use as-is; fixing amplitude calibration would require changing the normalization scheme (architecture-level change, not attempted here) | Lossless tensor-axis/lead-order conversion (native format partially incompatible); resolving the 44-vs-71 conditioning-vector discrepancy; writing an unwritten SCP-code extraction function (data for it already exists locally, per `docs/M6_ECG_MODEL_SELECTION.md` §2) — all **deferred to M7-0 onward in the existing implementation plan**, none attempted |
| **Compute / time / cost** | Already trained; inference on already-generated samples cost nothing further this session (existing `.npy` files reused) | **Estimates only, not measurements** — downloading the checkpoint would be required to measure for real. RTX 4060 (8GB) estimated practical based on architecture size (8-channel, 36-layer WaveNet/S4 hybrid); no VRAM figure published in SSSD-ECG's own sources. AWS not required per every estimate gathered. Nothing was downloaded or benchmarked, per `CLAUDE.md` §15 (no code execution/download before the license step) |
| **Current verified status** | Candidate, evaluated, usable as-is for a pilot (already was). Two unresolved gaps (no conditioning, no amplitude calibration) | **Candidate, not usable** — blocked on an external credential this project cannot resolve itself |

### 4.2 Other audited candidates — for completeness, none change the recommendation

| Candidate | License status | Why not pursued further |
|---|---|---|
| DiffuSETS | Code repo has no LICENSE file (terms unclear); HF weights are MIT | No SCP/superclass conditioning at all — would need a label→free-text translation layer, the furthest architectural gap from this project's current label scheme |
| FlowECG | No repository or weights released anywhere | Paper-only; nothing to run |
| cNVAE-ECG | Code repo has no LICENSE file; underlying paper is CC BY-NC-ND (non-commercial, no-derivatives) if that governs code use; no pretrained weights | Would require training from scratch under an unclear/restrictive license |
| FEM-simulator VAE | Promised GitHub release confirmed not present | No code, no weights, 100% simulator-generated training data (no real-patient provenance) |

### 4.3 What must pass before any large-scale ECG generation, regardless of which model is chosen

Per the existing M7 implementation plan and this session's own pilot
findings, not newly invented here:

1. Pretrained-weight license (if a third-party model) confirmed by a
   human with the required access — **not satisfiable by this agent**.
2. Conditioning-vector shape/semantics resolved and verified against an
   actually-loaded checkpoint (not just read from config files).
3. Held-out (never-trained-on) evaluation — now established practice
   for this project per this session's GAN fix — showing no severe
   generalization gap.
4. Mode-collapse / diversity check passing its documented thresholds.
5. Amplitude-calibration method defined and verified, if waveforms are
   to carry any physical-unit claim.
6. A small controlled pilot (the project's own established pattern: 50
   records before 100,000) evaluated against all of the above —
   **before** any run at full dataset scale.

**A favorable KS/variance result from either model does not by itself
satisfy items 2, 4, or 5 above, and is not treated as sufficient
evidence of clinical realism in this brief.**

---

## 5. M6 — Scope, Prerequisites, Sequencing

Re-read directly from `docs/PROJECT_STATE.md` (lines 582–650) and
`docs/ROADMAP.md`:

- **M6 is not one task.** It is a named slot for "the next milestone,"
  explicitly "awaiting explicit authorization," with **four
  independent candidates** listed: (a) an ECG architecture decision
  (reuse the inherited GAN at scale, or begin new waveform work), (b)
  resolving the hyperlipidemia-diagnosis question (Decision 6 above),
  (c) pattern discovery over the 100K baseline (Stage 7 of `CLAUDE.md`
  §11), (d) generative-model selection (Stage 9).
- **Prerequisites already satisfied for (a), (b), (c):** none of these
  three require anything blocked. They could each start independently
  the moment a human authorizes M6 (or a specific candidate within it).
- **Prerequisite NOT satisfied for (d) and the ECG-generation half of
  (a):** the SSSD-ECG pretrained-weight license (Decision 5) is an
  external credential this agent cannot obtain. Proceeding with (a) via
  the *inherited* GAN instead does not have this blocker, but still
  carries its two open gaps (no conditioning, no amplitude calibration)
  that a human should weigh before authorizing further ECG work.
- **Cost implications:** (b) and (c) are compute-light (CPU, existing
  data). (a)/(d) could require a GPU run; per the existing hardware
  research, no case has been found requiring AWS or incurring
  meaningful cloud cost — but no actual GPU run has been measured, only
  estimated.
- **Approval requirements:** M6 itself requires "explicit authorization"
  per the project's own standing instruction (unchanged by M5.5). Model
  selection specifically (candidate d) is additionally a `CLAUDE.md`
  §28 "Model selection" human-checkpoint category on top of that.

### Recommended sequencing

**Decisions 1–4 and 6–7 (lipid sampling, family history, encounters
shape, BP pulse-pressure floor, hyperlipidemia-diagnosis definition,
birth_date) can be authorized and actioned independently of M6 and of
each other** — none depends on ECG work, and M6 does not depend on any
of them either (M6's candidate (b) only *overlaps* with Decision 6, it
doesn't require the others).

**M6 candidates (b) and (c) (hyperlipidemia-diagnosis resolution,
pattern discovery) can proceed before the ECG model-selection decision**
— they are unrelated tracks and do not need to wait on a license
confirmation that has been outstanding since M6's first research pass.

**M6 candidate (a)/(d) (ECG architecture/model selection) should wait on
Decision 5 being explicitly addressed** — either by a human confirming
the SSSD-ECG license, or by a human explicitly deciding to proceed with
the inherited GAN despite its two disclosed gaps. Proceeding with ECG
work before one of those two things happens would mean either
fabricating a license status or silently picking a model without the
architecture-level sign-off `CLAUDE.md` §28 requires.

---

## 6. Single Recommended Next Action

**Authorize M6 candidates (b) and/or (c)** (hyperlipidemia-diagnosis
resolution and/or pattern discovery over the v0.8 baseline) **and/or
Decision 1** (the lipid-sampling fix) **— these are the only items
currently unblocked, independent of each other, and independent of any
external credential.** Everything else in this brief (Decisions 2–4,
6–7, and all of ECG/Decision 5) is either a smaller-stakes preference
with no urgency, or is genuinely blocked on a human action this agent
cannot perform (an authenticated Figshare session, or an architectural
sign-off on a model with known gaps).

No single action is forced; this is a menu, not a queue — the project's
own instruction not to interpret silence as approval applies to every
item above equally.

---

## 7. Explicit Confirmation

Verified fresh in this pass, not assumed:

- **`outputs/m5/100k_patients/` (v0.7 source): unmodified.** 100,000
  files, schema 0.7 confirmed on a spot-checked record.
- **`outputs/m8/100k_patients_v08/` (v0.8 frozen dataset): unmodified.**
  Directory checksum recomputed fresh and matches the manifest exactly
  (`8f14c4b6c42d671344b69174e1066f4cd1dd07df159d25ef14404b4d5f6a9aa6`).
- **No ECG waveform was generated.** `ecg.signal_available` is `false`
  on all 100,000 v0.8 records (checked directly, not sampled). No file
  under `syngen/SynGen/SynGen/synthetic_data/` is newer than the
  dataset-freeze manifest.
- **No migration was rerun.** No new write to either dataset directory
  occurred in this pass.
- **No model was downloaded, trained, or deployed.** No new dependency
  was added. No cloud resource was provisioned.
- **142/142 tests passing**, re-run this session without modification.

**This brief stops here.** No further milestone is started pending a
response to §3/§5/§6 above.
