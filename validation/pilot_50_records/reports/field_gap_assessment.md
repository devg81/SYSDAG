# Field-Level Gap and Missingness Report — 50-Record Pilot

Baseline: schema v0.7 (the 100,000-record dataset at
`outputs/m5/100k_patients/`). Target: schema v0.8.
Counts are over the 50-record batch at `../output/patient_records_50.json`.

Status key: **IMPLEMENTED (M8)** = newly populated by this work ·
**PRESERVED** = already populated, asserted byte-identical ·
**DEFERRED** = deliberately unpopulated, reason given.

---

## 1. Gap assessment: every attribute, before and after

| Field | v0.7 baseline | v0.8 status | Evidence basis | Action taken |
|---|---|---|---|---|
| `patient_id` | populated | **PRESERVED** | Canonical ids from the source dataset | Unchanged; enforced in code |
| `demographics.age` | populated | **PRESERVED** | uniform(20,89) engineering default (no Indian adult age-band table — D007) | Unchanged |
| `demographics.sex` | populated | **PRESERVED** | Census 2011 national marginal | Unchanged |
| `demographics.state` | populated | **PRESERVED** | Census 2011, full state/UT table | Unchanged |
| `demographics.urban_rural` | populated | **PRESERVED** | Census 2011 marginal | Unchanged |
| `demographics.height_cm` | **null** | **DEFERRED** | Tier E — no national mean+SD by sex found in 6 attempts | Written as explicit `null`; hook + tests in place |
| `demographics.weight_kg` | **null** | **DEFERRED** | Derivable as `bmi × (height/100)²` — blocked only on height | `derive_weight_kg()` implemented and tested; returns `None` while height is `None` |
| `risk_factors.bmi` | populated | **PRESERVED** | NNMS sex-conditional category prevalence | Unchanged — remains the evidence-primary anthropometric |
| `risk_factors.smoking_status` | populated | **PRESERVED** | NNMS sex-conditional | Unchanged |
| `risk_factors.hypertension` | populated | **PRESERVED** | INDIAB-17 national marginal 35.5% | Unchanged — and now the *conditioning input* for BP |
| `risk_factors.diabetes` | populated | **PRESERVED** | INDIAB-17 national marginal | Unchanged |
| `risk_factors.hyperlipidemia` | populated | **PRESERVED** | INDIAB-17 marginal | Unchanged; still intentionally distinct from `lipid_interpretations` (D014) |
| **`blood_pressure`** | **null (field absent)** | **IMPLEMENTED (M8)** | NFHS-5 age-band×sex means (PLOS ONE 2025); SDs derived from mean/CI/n and externally validated; r derived from published variances | New field; conditional on the hypertension label's own published definition |
| `family_history` | null | **DEFERRED** | Diabetes-family-history exists (LASI, 45+ only, 14.33%); CVD confirmed absent | Left `null` — scope is an **open human decision**, not an evidence gap |
| `medical_history` | populated | **PRESERVED** | Derived from diagnoses | Unchanged; **not expanded** — no evidence for surgeries/admissions/CV events |
| `diagnoses` | populated | **PRESERVED** | 1:1 promotion of HTN/diabetes flags (D015) | Unchanged; hyperlipidemia diagnosis still deferred |
| `medications` | populated | **PRESERVED** | NNMS treatment rates, drug-class only (D016) | Unchanged; dates reviewed and still `null`; no statin/antiplatelet added |
| `labs` (HbA1c) | populated for non-diabetics | **PRESERVED** | ICMR-INDIAB-12 age+sex trend, conditional on the diabetes label | Unchanged; no new analyte added |
| `lipid_panel` | populated | **PRESERVED** | TC/TG/HDL sampled; LDL Friedewald-derived then clipped | Unchanged — but see §4, defect surfaced |
| `lipid_interpretations` | populated | **PRESERVED** | Computed per named definition (D011) | Unchanged |
| **`encounters`** | **null** | **IMPLEMENTED (M8)** | Tier EA — structural container only, no utilization evidence | One `synthetic_baseline_assessment` per record; **not** a healthcare visit |
| **`clinical_timeline`** | 1 event, no references | **EXTENDED (M8)** | Tier EA — indexes existing dated records only | Gained `reference_id`; 2 events; no onset/start/follow-up dates invented |
| `ecg` | metadata only | **PRESERVED** | PTB-XL, D003 | Unchanged; `signal_available: false` in all 50; no superclass guessed |
| `echo` | null | **DEFERRED** | Scope entirely open (spec §2.1/§7) | Left `null`; no placeholder measurement, image or report |
| `provenance` | populated | **EXTENDED** | — | `schema_version` 0.7→0.8; generator string appended (not replaced); NFHS-5 added to `source_datasets` |
| `validation` | `structural-0.2` | **EXTENDED** | — | Re-run; now `structural-0.3+clinical-0.2`, covering both check families |

---

## 2. Missingness by field, with reasons

All 50 records. "Expected" means the absence is a documented decision,
not an omission.

| Field | Missing | % | Reason | Expected? |
|---|---|---|---|---|
| `demographics.height_cm` | 50 | 100% | Tier E — no national mean+SD of Indian adult height by sex located (6 attempts) | **Yes** |
| `demographics.weight_kg` | 50 | 100% | Derived from height; blocked on the same gap | **Yes** |
| `family_history` | 50 | 100% | Open human scope decision (LASI 45+ subset vs. none) | **Yes** |
| `echo` | 50 | 100% | Scope entirely open; no placeholder generated | **Yes** |
| `medications` (empty list) | 46 | 92% | Treatment-rate gated: only 3 of 19 hypertensives and 1 of 4 diabetics drew treatment, matching NNMS rates (14.5% / 36.1%) | **Yes** |
| `diagnoses` (empty list) | 29 | 58% | 29 patients have neither the hypertension nor diabetes flag | **Yes** |
| `labs` (empty) | 4 | 8% | Exactly the 4 diabetic patients — HbA1c is generated only for non-diabetics (insufficient diabetic-population evidence) | **Yes** |
| `diagnosed_date` (all diagnoses) | all | 100% | No evidence-backed per-patient onset distribution exists | **Yes** |
| `medications.start_date` / `stop_date` | all | 100% | NNMS gives point-prevalence of "currently treated" only — no initiation or duration information | **Yes** |
| `blood_pressure` | **0** | 0% | Newly populated | — |
| `encounters` | **0** | 0% | Newly populated | — |

**No field is missing for an undocumented reason.** There is no partial
or accidental missingness in the batch: every absence above is either a
population-level decision affecting all records, or a per-patient
consequence of an evidence-backed conditional rule.

### Missingness correlated with other fields — worth a reviewer's attention

Two absences are **not** missing-at-random, by design:

- `labs` is empty **exactly when** `risk_factors.diabetes` is true. Any
  downstream model will see HbA1c-missingness as a perfect predictor of
  diabetes. This is a documented consequence of the M4B evidence gap,
  not a leak introduced here, but it matters for the pattern-discovery
  stage this dataset feeds.
- `medications` is empty for all non-diagnosed patients and for
  untreated diagnosed patients, so medication presence is a function of
  diagnosis plus one Bernoulli draw.

---

## 3. New-field distributions (the 50-record batch)

### Blood pressure

| Statistic | SBP (mmHg) | DBP (mmHg) | Pulse pressure |
|---|---|---|---|
| mean | 126.38 | 84.24 | 42.14 |
| SD | 15.77 | 11.29 | 10.85 |
| min | 95 | 52 | 23 |
| median | 124.5 | 83.0 | 41.5 |
| max | 160 | 118 | 69 |

Reference points: published NFHS-5 male overall SBP 123.4 ± 13.8,
DBP 80.5 ± 10.2, PP 42.9 ± 9.5. **The pulse-pressure mean matches to
within 2%.** SBP/DBP means run higher than NFHS-5's, as expected and
documented — the batch's age distribution (mean 59.8, uniform 20–89) is
far older than NFHS-5's 15+ sample, and the label truncation reweights
toward INDIAB-17's higher hypertension prevalence. **These figures must
not be read as a reproduction of NFHS-5's observed BP distribution**
(`evidence_and_assumptions.md` §1.5(b)).

| Check | Result |
|---|---|
| SBP > DBP in every record | **50/50** |
| Pulse pressure < 20 mmHg | **0** |
| Distinct systolic values | 38 / 50 |
| Distinct diastolic values | 30 / 50 |
| Raised BP (≥140/≥90) | 18 |
| Hypertension label true | 19 |
| Above source age coverage | 32 (64%) |

The 19-vs-18 gap is the single treated-and-controlled hypertensive —
exactly what the published definition predicts, and the observable proof
that treated patients are not forced to look uncontrolled.

### Cohort coverage in the batch

| Cohort | n | Note |
|---|---|---|
| Hypertension label true | 19 | 38% (population target 35.5%) |
| On antihypertensive | 3 | 16% of hypertensives (NNMS rate 14.5%) |
| Treated **and controlled** | 1 | The architecturally important case — covered |
| Diabetes label true | 4 | 8% |
| Diabetic without HbA1c | 4 / 4 | Rule holds exactly |
| Age bands represented | 9 distinct | male 20–24 … 50–54; female 25–29 … 45–49 |

**Coverage limitation of a 50-record batch.** The sample is uniform
without replacement over all 100,000 records (seed 8), **not** purposive
— so rare cohorts appear only as often as chance allows. With 3 treated
hypertensives and 4 diabetics, this batch **cannot** support any
statistical claim about those subgroups; it demonstrates that the rules
hold for the cases present. The generator-level properties are asserted
over hundreds of draws in `tests/test_m8_bp_encounters.py` instead, which
is where those claims belong.

### Encounters and timeline

| Metric | Value |
|---|---|
| Records with exactly one encounter | 50 / 50 |
| Encounter types | `synthetic_baseline_assessment` × 50 (only value in the vocabulary) |
| Measurement sets | `blood_pressure, lipid_panel, labs.HbA1c` × 46; `blood_pressure, lipid_panel` × 4 |
| Timeline events per record | 2 in all 50 |
| Timeline event types | `synthetic_record_created` × 50, `synthetic_baseline_assessment` × 50 |

The two distinct measurement sets are the 46 non-diabetic and 4 diabetic
patients — i.e. **the encounter contents vary with what was actually
measured**, rather than every patient receiving an identical history.

---

## 4. Defect surfaced in preserved data — pre-existing, not introduced

**The pilot's headline unresolved issue.** `lipid_panel`'s TC, TG and HDL
are sampled as three **independent** marginals (M4B — no joint
distribution evidence exists). Friedewald requires
`TC ≥ HDL + TG/5` for a self-consistent panel. Some triples violate it,
and LDL's documented `clip_range` floor of 30 mg/dL silently absorbs the
result.

In the 50-record batch:

| Condition | Count | Patient ids |
|---|---|---|
| **Internally impossible** — TC below the sum of its own components | **2** | `PAT_044552`, `PAT_059083` |
| LDL clipped at the floor but feasible (0 ≤ implied LDL < 30) | 2 | `PAT_081367`, `PAT_081541` |
| Triglycerides > 400 mg/dL (Friedewald not valid above this) | 0 | — |

Worked example — `PAT_044552`: TC 129.8, HDL 89.5, TG 260.1 mg/dL.
`HDL + TG/5 = 141.5 > 129.8`, so the implied LDL is **−11.7 mg/dL** and
the stored value is the 30.0 floor. The record asserts a total
cholesterol lower than the sum of its own fractions.

**This is pre-existing M4B behaviour, not introduced by M8**, and the
stored LDL does follow its documented clip rule — so M8 raises it as a
**warning** rather than promoting it to a validation error, which would
fail a large share of the dataset over a decision that is not a
validator's to make. It is now **counted** rather than invisible:
`validation/clinical_consistency.py` flags every such record, and
`run_pilot.py` tallies them into `validation_metrics.json`.

**Measured across all 100,000 records** (`full_dataset_dryrun_audit.json`):

| Condition | Count | % of dataset |
|---|---|---|
| LDL clipped at the floor but feasible | 7,548 | 7.5% |
| **Internally impossible (TC < HDL + TG/5)** | **2,283** | **2.3%** |
| Triglycerides > 400 mg/dL | 0 | 0% |
| **Total records whose LDL is the clip floor, not a derivation** | **9,831** | **9.8%** |

So roughly one record in ten carries an LDL that was clipped rather than
derived, and one in forty-four is internally contradictory. The batch's
4-and-2 counts are in line with those rates.

**Recommendation:** resolve before external *clinical* review, since a
reviewer will reasonably read "TC < HDL + TG/5" as a data error. This is
a D011-level decision; the options are (a) sample TC, then HDL and TG
conditioned so the triple stays feasible, (b) sample LDL/HDL/TG and
derive TC additively, or (c) reject-and-redraw infeasible triples.
Option (b) changes which quantity is "primary" and so needs the same
kind of explicit decision D011 itself was.

Separately, **2 records in the batch (6,466 — 6.5% — across the full
dataset) have an empty `ecg.superclasses`** — a genuine PTB-XL label
gap. Warned about, **not** guessed at, per
`docs/M7_0_ECG_READINESS_REPORT.md`. This matters for the ECG
workstream, not for this batch's clinical fields.

---

## 5. Field-by-field verdict on the task's requested scope

| Requested | Verdict |
|---|---|
| **A. Height and weight** | **Deferred.** Evidence evaluated across 6 attempts; mean weakly supported, dispersion not supported at all. BMI preserved exactly; no contradictory anthropometrics created. Hook, derivation and tests in place; one verified mean+SD table unblocks it. |
| **B. Blood pressure** | **Implemented.** Evidence located, SDs derived and externally validated, correlation derived. Conditioned on the label's own published definition — not assigned from hypertension status, and a treated patient's reading is never forced to confirm the label. |
| **C. Medical history** | **Not expanded.** No evidence supports surgeries, admissions, CV events or procedures. Referential integrity to diagnosis ids verified. Empty history is **not** represented as proof of absence. |
| **D. Diagnoses** | **Unchanged.** HTN/diabetes remain 1:1 promotions of their flags. Hyperlipidemia still deferred. No diagnosis derived from the new BP measurement — the rule for that is not approved. |
| **E. Encounters** | **Implemented minimally** as a declared structural container. No visit, admission, appointment or follow-up invented. Reversible if a reviewer prefers `null`. |
| **F. Clinical timeline** | **Extended** to index the encounter via a new `reference_id`. No onset, start/stop or follow-up date fabricated. No duplicate events. |
| **G. Medications** | **Unchanged.** Dates reviewed and justifiably still `null`. No statin or antiplatelet added. |
| **H. Family history / family tree** | **Deferred.** No relatives, kinship links, family sizes or hereditary conditions invented. No family-tree schema proposed. Blocked on an open human scope decision. |
| **I. Labs and lipids** | **Preserved** exactly, and audited — which is how the feasibility defect in §4 was found. |
| **ECG / echo boundaries** | **Preserved.** No waveform, no guessed label, no echo placeholder. |
