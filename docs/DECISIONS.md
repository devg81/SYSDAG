# Architectural Decisions

Format: Decision / Reason / Alternatives considered / Consequences.
Newest entries at the top. Do not revisit a decision without new evidence.

---

## D027 — Hypertension by age × sex and diabetes by age, from observed Indian surveys; supersedes D006's flat marginals for these two; schema v0.12 → v0.13 (human-approved 2026-11-12, conditional on research) -jatin

**Author:** -jatin.

**Approval.** The user asked for thorough research first, giving a green light only if a positive age correlation was found. It was found in every national source:
- **Diabetes:** ICMR-NNMS 2.2% / 7.8% / 21.8% at 18–29 / 30–49 / 50–69, adjusted OR 2.77 and 8.89 (Mathur et al., Front Public Health 2022). NFHS-5 rises monotonically in 5-year bands. LASI rises from 14.7% at 45–49 to 23.4% at 70–74 (Sekher et al., Lancet Glob Health 2025). ICMR-INDIAB reports an increasing trend with age.
- **Hypertension:** NFHS-5 rises from ~4–5% at 15–19 to 31–41% at 45–54 (Rana et al., PLOS ONE 2024). LASI rises from 28–32% at 45–49 to 47–60% at 70+ (Mohanty et al., BMC Public Health 2022).

**Decision.**
- `risk_factors.hypertension` is drawn from `P(HTN | age, sex)`: NFHS-5 measured BP for ages <45 (band values read off the project's existing NFHS-5 BP model), LASI W1 for 45+.
- `risk_factors.diabetes` is drawn from `P(DM | age)`: NNMS for <45, LASI for 45+. It is not sex-conditioned, because sources show no consistent sex difference.
- Both curves are piecewise-linear between band midpoints and flat outside. Each still uses exactly one `rng.random()`.
- The onset model now uses the same curves.
- Family history (D020) conditions on the age-specific diabetes prevalence, so its marginal stays calibrated at every age.
- Population validators now target the curves' expected marginal under the generator's uniform(20,89) age and sex mix (`expected_prevalence_uniform_age`): HTN 35.6%, DM 15.3%. They no longer target INDIAB-17's 35.5% / 11.4%, which describe India's younger real age structure. INDIAB-17 stays in config as a reference.

**Why not keep INDIAB-17's marginals by rescaling the curves?** The generator's ages are uniform 20–89 (D007), much older than India's real adult population. Rescaling would make every age-specific rate wrong to force a national number that belongs to a different age structure. A census-weighted calibration is impossible because no usable Indian age structure is available (D007).

**Validation (20,000 seeds).** Overall HTN 35.0% (expected 35.6%), DM 15.5% (expected 15.3%). Every age band matches its source within ~2 points (for example HTN women 65–69: 53.7% vs LASI 53.9%; DM 75+: 21.2% vs LASI 21.2%). Family history: diabetes 45+ 13.95% (LASI 14.33%), CVD 45+ 11.90% (11.61%). Treatment: HTN 14.2% (14.5%), DM 36.1% (36.1%). LAI tiers: low 34.0 / moderate 27.3 / high 27.0 / very high 11.8%.

**Limitations.**
- Source definitions differ (measured BP vs BP-or-treatment; FBG vs HbA1c vs INDIAB-17's OGTT), and the sources join at ~42–47.
- Band-midpoint and open-band placements (LASI 70+ at 75, 75+ at 80) are engineering choices.
- The onset early-skew remains (median HTN onset for people now 60–69 is 39). That is a model assumption, documented in `docs/OPEN_QUESTIONS_4-7_EVIDENCE-jatin.md`.

**Consequences.**
- Records change for patients whose draw crosses the new threshold, and BP, medications, HbA1c, family history, onset and LAI tier follow.
- The 5 review samples were regenerated with the real `build_patient()` (`integration/regenerate_review_samples.py`, ECG metadata reused by seed). All 5 keep their flags; only onset ages and tags changed.
- Full test suite run locally with a scratch PTB-XL stub: 197 passed. The only failure is the stub's fake ECG id. `test_ingestion_caching.py` was not run (it needs real PTB-XL).
- Frozen 100K stays v0.9. The v0.13 regeneration is part of the AWS plan (D026).

---

## D026 — Rebuild the 50-record pilot at v0.12; run heavy work (pilot, 100K, later ECG) on AWS (human-approved 2026-11-12) -jatin

**Author:** -jatin.

**Decision.** (1) The stale v0.8 pilot (`validation/pilot_50_records/`, a v0.7→v0.8 migration) is rebuilt, not retired. The same 50 IDs are regenerated fresh at the current schema by `validation/pilot_50_records/rebuild_v012.py`, gated by `tests/test_pilot_v012.py`. The v0.8 files stay as the historical artifact; their migration tests are retired once the rebuild passes. (2) Work that needs PTB-XL, pandas or the GAN checkpoints runs on AWS, per `docs/AWS_RUN_PLAN-jatin.md`: phase 1 is one CPU `c7i.2xlarge` for ~3 h, estimated under US$5; phase 2 (ECG) is estimated only after the M7 code exists.

**Reason.** The local machine cannot run `build_patient()`: no PTB-XL CSVs, and Windows Application Control blocks pandas. The user chose AWS over the teammate's machine.

**Alternatives considered.** Retire the pilot as historical, or delete it (not chosen). Teammate's machine (not chosen). Fix this laptop (blocked by a security policy that should not be changed).

**Consequences.** Nothing has been launched yet. Launching an instance and the 100K run each still need explicit go-ahead (§15). AWS credentials stay out of the repo.

---

## D025 — Lipid panels with TG > 400 mg/dL stay rejected and redrawn (human-approved 2026-11-12) -jatin

**Author:** -jatin.

**Decision.** Keep the D022 behaviour: a panel whose TG exceeds 400 mg/dL (where Friedewald LDL is invalid) is rejected and redrawn whole. LDL is never null.

**Reason.** It is the simplest option, already validated, and keeps every downstream rule (interpretations, the D023 flag, the D024 tier) free of null-LDL handling.

**Alternatives considered.** Emit LDL = null with a reason, as a real lab would. That keeps the high-TG tail but needs null handling everywhere.

**Consequences.** The generated TG distribution is truncated at 400 (about 0.6% of real-world panels exceed it). This is documented in provenance, and closes v0.10 open question 2.

---

## D024 — Rule-based LAI risk tier and LDL goal on the LAI_2020 interpretation; schema v0.11 → v0.12 (human-approved 2026-11-12) -jatin

**Author:** -jatin.

**Decision (user chose "simple risk rule").** The LAI_2020 lipid interpretation gains `risk_category` (low / moderate / high / very_high), `ldl_goal_mg_dl`, `ldl_above_goal`, `risk_factors_counted` and `risk_derivation`. They are computed by `derive_lai_risk()` from modelled factors only, with no RNG. Major risk factors counted: age (men ≥45, women ≥55), current smoking, hypertension, and low HDL (men <40, women <50). Rule: diabetes + ≥2 risk factors → very high (goal <50); diabetes + 0–1 → high (<70); non-diabetic ≥3 → high (<70); exactly 2 → moderate (<100); 0–1 → low (<100). The clinical validator recomputes the tier (`lai_risk_tier_consistency`) and rejects tier fields on any other definition. Config: `lipid_definitions.LAI_2020.risk_tiers`.

**Evidence and confidence.**
- Diabetes split and goals: LAI diabetic dyslipidaemia consensus (J Clin Lipidol 2022) and LAI 2023 Consensus IV.
- Risk-factor list and the non-diabetic 0–1 / 2 / ≥3 split: LAI 2016 Part 1, as reported by secondary sources. The LAI full texts returned 402/403, so this split is verified against the NLA framework LAI adapted, not LAI's own table.
- Confidence: moderate for the rule, **low for a patient's category.**

**Not modelled (each can only under-count risk).** Established ASCVD, so "extreme" is never assigned. Premature family CAD: `family_history.cardiovascular_disease` is any-age, so it is deliberately not used. Target-organ damage, CKD, familial hypercholesterolaemia, Lp(a), and smokeless tobacco.

**Alternatives considered.** Screening cutoff only (recommended, not chosen). Counting family history (rejected: wrong definition).

**Consequences.**
- On 5,000 seeds: low 30.8% / moderate 33.9% / high 27.1% / very high 8.2%. Diabetics are 67% very high and 33% high. LDL is at or above the personal goal in 70.6%. These are **generated patterns, not externally validated**.
- 0 records differ from the v0.11 generator in any other field.
- The LAI `dyslipidemia` screening flag (LDL ≥100) is unchanged.
- `review_samples_v012/` re-derived, all 5 valid.
- The frozen 100K stays v0.9.
- Closes v0.10 open question 3.

---

## D023 — Reverse D014: `risk_factors.hyperlipidemia` derived from the lipid panel (NCEP ATP III); schema v0.10 → v0.11 (human-approved 2026-11-12) -jatin

**Author:** -jatin (decision taken and applied in Jatin's session, 2026-11-12).

**Decision (human-directed).** `risk_factors.hyperlipidemia` is no longer an independent `Bernoulli(0.812)` draw. It now equals `lipid_interpretations[NCEP_ATP_III].dyslipidemia`, computed from the patient's own panel (`generation/indian_population.py` `derive_hyperlipidemia()`, config `risk_factors.hyperlipidemia.derivation`). The old Bernoulli draw is still made once and discarded, so every later field keeps its random numbers for the same seed. `validation/clinical_consistency.py` replaces the D014 "intentionally not compared" check with a hard rule, `hyperlipidemia_derived_from_lipid_interpretations`, so the chain is now panel → interpretation → flag.

**Reason.** D014 kept the two fields apart because the flag predated the panel and the old independent-marginal lipid sampler could not produce the 81.2% target from the numbers. The D022 joint lipid model now gives NCEP dyslipidaemia of 80.9% (5,000 records), so deriving the flag keeps the prevalence and removes a ~31% contradiction rate (for example, v0.10 PAT_000095 had flag true with a fully normal panel). An external reviewer flagged the contradiction.

**Why NCEP, not LAI.** INDIAB-17's 81.2% is NCEP-based, so NCEP reproduces it. LAI_2020's lower LDL cutoff would give about 90%.

**Alternatives considered.** Keep D014 (documented disagreement, rejected by the user). Derive from LAI_2020 (overshoots the source prevalence). Drop the placeholder draw (shifts treatment, BP, family history and onset for every seed, for no benefit).

**Consequences.**
- Schema v0.11: no structural change, but the bump marks the field's changed meaning. v0.10 records fail the new hard rule wherever they disagree, which is intended.
- Verified on 5,000 seeds against the v0.10 generator (HEAD `7a0121e`): 0 records differ in any field except the flag; flag == NCEP 5,000/5,000; prevalence 80.86%; 30.96% of flags changed value.
- The five review samples were re-derived into `review_samples_v011/` (only PAT_000095 changed: true → false).
- `configs/indian_population.yaml`'s `distribution.p: 0.812` stays as the statistical validator's target. At 100K scale, 80.9% vs 81.2% may fail an exact binomial test (z ≈ 2.4). That is a calibration note to record when v0.11 is generated at scale, not a structural defect.
- Does **not** add a `diagnoses.hyperlipidemia` entry or statins. That M4D/D015/D016 question stays open, although NCEP is now the natural candidate definition.
- Frozen 100K stays v0.9. A v0.11 regeneration (~2 h) needs approval.
- D014 is superseded, not edited (append-only log).

---

## D022 — Review fixes: joint lipid model (no LDL clamp), HbA1c for diabetics, BP SBP-trend extrapolation, modeled onset; schema v0.9 → v0.10 (requested by human review 2026-11-12)

**Decision.** (1) TC/ln(TG)/HDL drawn jointly from a trivariate normal: means solved from the INDIAB-17 category rates, SDs from ICMR-INDIAB phase I (PMC4016101), latent correlations (0.45, -0.40, 0.40) calibrated to INDIAB-17 dyslipidaemia 81.2% / LDL>=130 20.9% and the phase-I LDL SD. LDL stays Friedewald with **no clamp**: panels with LDL<30, TG>400 or out-of-range TC/HDL are rejected whole. (2) Diabetic HbA1c: log-normal with P(<7%)=36.3% (INDIAB-13) and SD 2.2; observed for treated, borrowed (confidence low) for untreated. (3) BP above NFHS-5 coverage: mean SBP on NFHS-5's own linear trend, DBP/SDs held; `confidence` field. (4) Modeled onset age/date per diagnosis from prevalence-by-age curves (NFHS-5 BP model; LASI diabetes), tagged modeled; diagnosed_date stays null. (5) Age rounded to 2 dp; empty-value convention documented (None = not modeled, [] = none).

**Reason.** Reviewer found implausible lipid triples, a silent LDL=30 clamp (7.3% of records), frozen BP/pulse pressure above age 54/49, no glycaemic marker for diabetics, and no longitudinal dimension.

**Alternatives considered.** Sample LDL and derive TC (breaks the derived-LDL contract); copula over the old uniform marginals (needed TC-TG r=0.8 to fit); LDL=null when TG>400 (open); Synthea for longitudinal (strategic, not chosen); deriving hyperlipidemia from the panel (reverses D014 -- left for human decision).

**Consequences.** v0.10 records differ from v0.9 in lipids/HbA1c/BP; demographics and risk-factor flags unchanged for the same seed. Lipids/HbA1c now use child RNG streams. Frozen 100K remains v0.9 until a regeneration is approved. Full evidence: `docs/V010_CHANGE_REPORT.md`, `docs/V010_REVIEW_COHORT_CHECKS.json`.

---

## D021 — Air quality: 2023 CPCB state annual-mean AQI as a deterministic lookup, urban bias flagged per record; schema v0.8 → v0.9 (human-approved)

**Date:** 2026-11-10

**Decision (human-directed, implementing
`docs/Further_Steps_for_patient-Record_complete.txt` §3.3):** new
optional `Patient.air_quality` (`AirQuality` dataclass: `aqi`,
`category`, `reference_year`, `stations`, `cities`,
`unavailable_reason`, `geographic_resolution="state"`,
`monitoring_bias="state_mean_is_urban_station_weighted"`, `source`),
filled by `generation/indian_population.py` `derive_air_quality()` as a
**lookup by `demographics.state`** (no rng consumed, so no other field
moves). Values in `configs/indian_population.yaml`
`environment.air_quality`, rebuilt by `ingestion/cpcb_state_aqi.py`.
`SCHEMA_VERSION` 0.8 → 0.9 (covers D020's populated family_history
too). India's CPCB National AQI scale and categories, not US EPA.

* **Source:** CPCB CAAQMS hourly station AQI, via
  github.com/Vonter/india-cpcb-aqi (ODbL-1.0, CPCB attribution),
  `data/cpcb-aqi.parquet` @ commit 954db3a. Covers 2017-2023; 2023 is
  the latest full year (519 stations, 29 states/UTs).
* **Aggregation:** station mean of 2023 hourly AQI (stations with ≥50%
  of hours reporting: 448 of 519) → city mean → equal-weight mean over
  the state's cities, so one dense metro (Mumbai: ~40 stations) does
  not stand in for its whole state.
* **Census-2011 mapping:** Telangana pooled into "Andhra Pradesh",
  "Odisha" → "Orissa".
* **Nine states/UTs get `aqi: null` with a reason** (Jharkhand and
  Manipur: stations present but none ≥50% coverage; Goa, Puducherry,
  Nagaland, A&N, Dadra & Nagar Haveli, Daman & Diu, Lakshadweep: no
  station), ~3.4% of the population. No neighbour value is borrowed.

**Reason:** the approach was already analysed and recommended (§3.3);
the owner approved implementation. State is the finest geography the
schema has, so the station/city data is collapsed to it rather than
inventing a city/district field (§3.4).

**Verification:** Delhi computes to 212.3 against the officially
reported 2023 daily-average AQI of 204 (CAQM, from CPCB data): +4%,
from averaging hourly values rather than CPCB's daily index. Script
reproduces every config value. 1,000-record v0.9 pilot
(`outputs/m9/pilot_1000_v09/`): 1000/1000 structurally valid and
clinically consistent, 0 errors, only pre-existing warning kinds;
22 null AQI, all with reasons. 174/174 tests (17 new).

**Limitations (all in config and provenance):** urban-biased and
applied unchanged to rural patients (69% of records), flagged per
record; state resolution only; one reference year, not exposure
history; 8 states rest on a single station (count stored per record);
hourly-mean method differs slightly from the official daily AQI.

**Alternatives considered:** city/district field (needs its own
population source, §3.4); rural adjustment factor (no source for one);
borrowing neighbour states for unmonitored ones (invents data); data
from CPCB's CCR portal directly (same data, registration/bulk-export
friction; the ODbL republication is reproducible by commit).

**Consequences:** `validation/structural.py` checks AQI range,
category-vs-value under CPCB breakpoints, and null-with-reason;
`validate_patient` gained `expected_schema_version` so the historical
v0.7→v0.8 migration (`TARGET_SCHEMA_VERSION` pinned to "0.8") still
validates. The frozen 100K v0.8 dataset is untouched; it will fail
v0.9 structural validation by version only. The bundled re-freeze
(D019 + D020 + D021) ran the same day: `outputs/m9/100k_patients_v09/`,
100,000/100,000 valid, manifest `outputs/m9/dataset_manifest.json`.

---

## D020 — Family history: LASI observed for 45+, calibrated parent simulation for 20-44, diabetes family history conditioned on the patient's diabetes (human-approved)

**Date:** 2026-11-10

**Decision (human-directed, approaches "2 + 3" of the family-history
options discussion):** `family_history` is now generated for every
patient as `{diabetes, cardiovascular_disease, derivation}`
(`generation/indian_population.py` `sample_family_history()`, config
`risk_factors.family_history`). CVD = heart disease or stroke in a
first-degree relative, not hypertension. Supersedes D004's "leave null"
for this field.

* **Ages 45+** (`derivation: lasi_observed_45_plus`): LASI Wave 1
  observed marginals, diabetes 14.33% (PMC11005278 Table 1), CVD 11.61%
  (PMC11659756 Table 1).
* **Ages 20-44** (`derivation: parent_simulation_calibrated`):
  P = 1−(1−k·p_mother)(1−k·p_father), where p_parent is LASI's
  self-reported prevalence for the parent's age band × sex (LASI India
  Report 2020 Table 7.5 diabetes; Table 7.3 heart disease and stroke,
  bands 45-59 / 60+), parent age = patient age + 25 (mother) / + 30
  (father). One factor k per condition (diabetes 0.524, CVD 0.766) is
  solved so the same model reproduces the observed 45+ figure (both
  parents 60+), which also makes age 44→45 continuous.
* **Diabetes family history** is conditional on the patient's own
  diabetes label via LASI's crude OR 3.80 (PMC11005278 Table 1: 27.8%
  vs 9.2% diabetes with vs without family history), solved on the 2×2
  table so the age-specific marginal is preserved. CVD family history
  is a marginal draw (no patient-level CVD label exists).
* Drawn last in the rng order, after BP, so every earlier field is
  byte-identical for the same seed.

**Reason:** a dedicated source search (2026-11-10) found no national
family-history prevalence for ages 20-44: LASI is 45+ by design;
ICMR-INDIAB Phase I collected it but its full report publishes no
prevalence (checked); NNMS and NFHS-4/5 report none (NFHS authors
state it was not collected); PURE-India none found. CARRS
(PMC9453056: urban Delhi/Chennai/Karachi, 20+, excluding people with
their own cardiometabolic disease) has real figures (diabetes 22.2%,
heart disease 7.1%, stroke 1.9%) but is urban, partly Pakistani and
selected, so under D010's no-silent-blending rule it is a cross-check,
not a source. The verified OR 3.80 replaces the strategy doc's
unsourced "~3.13".

**Why k is needed:** uncalibrated, the parent model gives 26.4%
(diabetes) / 15.0% (CVD) at 45+ against LASI's observed 14.33% /
11.61%: the parents of 45+ respondents were diagnosed in an earlier,
lower-awareness era and many died undiagnosed. k absorbs that era/
recall/underdiagnosis gap and is ASSUMED age-invariant.

**Verification:** 50,000-draw check: 45+ diabetes 14.40% / CVD 11.33%
(targets 14.33 / 11.61); 20-44 average 12.23% / 8.88%, under the CARRS
urban reference 22.2% / 9.0%; by age 20-29: 10.4 / 5.7, 30-34: 11.9 /
9.3, 35-44: 14.3 / 11.9 (step-shaped because LASI gives only two
parent bands). 1,000-record pilot (`outputs/m9/pilot_1000_family_
history/`): 1000/1000 structurally valid and clinically consistent,
0 errors, only pre-existing warning kinds; family-history-positive
patients 24.4% diabetic vs 8.9% negative (LASI: 27.8% / 9.2%).
157/157 tests (12 new).

**Assumptions (all disclosed in config and provenance):** parental age
gaps are engineering values, not sourced; siblings ignored; parents
independent; k age-invariant; OR measured at 45+ assumed to hold at
20-44; heart disease and stroke combined assuming independence; LASI
self-report used throughout (matches self-reported family history, so
no separate underdiagnosis correction).

**Alternatives considered:** 45+ only with null below 45 (rejected by
the owner: ~36% of records empty, and an age split that would distort
pattern discovery); LASI carried flat into 20-44 (overestimates young
adults); STEPS state surveys blended (D010 objection, and 21-23%
conflicts with LASI); ICMR-INDIAB microdata request (best fix, outside
the timeline, still open).

**Consequences:** the frozen 100K v0.8 dataset is NOT regenerated by
this decision; it still has `family_history: null`. Re-freezing (bundled
with D019 and, if approved, AQI) is a separate decision.
`validation/clinical_consistency.py` now checks family-history shape
and that the derivation tag matches the age tier.

---

## D019 — Lipid panel sampling: reject-and-redraw infeasible TC/HDL/TG triples (human-approved, Decision Brief item 1, Option 4)

**Date:** 2026-10-29

**Decision (human-directed):** `generation/indian_population.py`'s
`sample_lipid_panel()` now rejects and redraws any TC/TG/HDL triple
where the implied Friedewald LDL (`TC − HDL − TG/5`) is negative —
i.e. `TC < HDL + TG/5`, a physical impossibility — up to 1000 attempts
per patient (measured feasibility rate ~97.72% per draw, so this
converges in ~1 attempt on average; the attempt cap is a safety net,
never observed to bind). Each retry redraws TC, TG, and HDL from
their exact same evidence-backed category-then-uniform marginals
(`docs/M4B_GENERATION_DESIGN.md` A2) — no new correlation, joint
distribution, or clinical assumption is introduced; infeasible
combinations are simply excluded rather than accepted and silently
clipped. This is Option 4 of the four presented in
`docs/M8_DECISION_BRIEF.md` Decision 1, approved by the project owner
over the alternatives (leave as-is; constrain sampling order;
redefine the primary quantity).

**Reason:** `docs/M8_FULL_DATASET_VALIDATION_REPORT.md` measured 2,283
of 100,000 records (2.28%) as internally impossible under this exact
rule, with the LDL clip floor (30 mg/dL) silently absorbing the
contradiction rather than surfacing it — flagged as a validator
WARNING since M8 but never fixed, pending this human decision. Option
4 was this project's own stated recommendation (`docs/
M8_DECISION_BRIEF.md` Decision 1): smallest code change, preserves
every existing marginal's evidence basis exactly.

**Verification:** a fresh 200,000-draw check
(`np.random.default_rng(42)`, alternating sex) found **0 infeasible
triples** (was ~2.28%) and a secondary effect on the separate,
smaller clip-floor population (physiologically plausible low LDL
rounding up to 30 mg/dL floor, not an impossibility): 7.72% (was
9.83%) — expected, since removing the most extreme negative-raw draws
also removes some of the near-floor ones, though this population is
NOT what D019 targeted and remains a documented, unresolved
limitation. 142/142 pre-existing tests still pass unchanged; one new
regression test added (`tests/test_m4b_clinical_generation.py::
test_no_infeasible_lipid_triples_at_scale`, 20,000-draw check, asserts
zero infeasible triples). `validation/clinical_consistency.py`'s
existing `lipid_panel_internal_feasibility` check is unchanged in
logic (kept as a regression guard and as the correct check for any
pre-D019 dataset re-validated later) — only its comment was updated to
cite this decision.

**Alternatives considered:** see `docs/M8_DECISION_BRIEF.md` Decision
1 options 1-3 (leave as-is; constrain sampling order so TC is drawn
first and HDL/TG conditioned to stay feasible; redefine which quantity
is primary) — all rejected by the project owner in favor of Option 4.

**Consequences:**
- Freshly generated records (any new dataset, not yet re-run at full
  scale this session) will have 0% internally-impossible lipid panels.
- **Existing frozen datasets are NOT retroactively changed** —
  `outputs/m5/100k_patients/` (v0.7) and `outputs/m8/100k_patients_v08/`
  (v0.8) both still contain the pre-D019 2.28%/9.83% rates, per this
  project's standing rule against silently modifying frozen artifacts.
  A new dataset version/re-generation would be required to produce a
  D019-corrected full-scale dataset — not done in this session: no 100K
  regeneration was requested or run, per `CLAUDE.md` §15's
  expensive-operation gate.
- The 9.83%→7.72% clip-floor rate is a known, now-slightly-smaller but
  still-open limitation, unaffected by D019 and not addressed by it.

---

## D018 — ECG model selection (M6/M7 checkpoint): inherited per-class GAN selected; SSSD-ECG and CardioSynth/CardioSync rejected

**Date:** 2026-10-21

**Decision:** Ship the existing inherited per-class GAN
(`syngen/SynGen/SynGen/checkpoints/generator_{CD,HYP,MI,NORM,STTC}.pt`)
as the ECG-waveform generator for the patient-generation pipeline.
SSSD-ECG and CardioSynth/CardioSync are both rejected as candidates for
this project, at this time.

**Reason:**
- **CardioSynth/CardioSync** — already found not viable in M6 research:
  the only real GitHub match is an unlicensed single-lead demo scaffold,
  not 12-lead/PTB-XL compatible (`docs/M6_ECG_MODEL_SELECTION.md`).
- **SSSD-ECG** — code is MIT-licensed (confirmed), but the separate
  pretrained-weight checkpoint is a distinct artifact hosted on an
  unlisted/private Figshare share link with no license stated anywhere
  reachable: two automated fetch attempts returned HTTP 403
  (`docs/M6_SSDD_ECG_COMPATIBILITY.md`, `docs/
  M6_MODEL_SELECTION_DECISION_BRIEF.md`), and the item's DOI
  (`10.6084/m9.figshare.21922875`) does not resolve on `doi.org` —
  consistent with an item that was never published/registered publicly.
  A human (project owner) opened the share link directly and confirmed
  it streams only the raw `.pkl` file with no accompanying metadata or
  license. Under default copyright rules, an unstated license on a
  distinct artifact (the weights) is "all rights reserved," not
  permissive-by-assumption — a code license (MIT) does not extend to a
  separately-authored, separately-hosted weights file. This project is
  building a commercial, doctor-facing SaaS product; shipping synthetic
  output generated by an unlicensed third-party pretrained model is an
  unacceptable, avoidable legal risk given a known-good alternative
  already exists.
- The inherited GAN is the project's **own** asset (already in the
  repository, no external licensing question), already held-out
  re-validated against real, never-trained-on PTB-XL data (M5.5,
  `docs/M8_ECG_HELDOUT_PILOT_REPORT.md`), and requires zero additional
  training, fine-tuning, or legal clearance.

**Alternatives considered:**
- *Assume the SSSD-ECG weights are permissively licensed and proceed
  anyway.* Rejected — explicitly discussed and declined by the project
  owner (2026-10-21): the risk is to a paid product, not an internal
  experiment, and a known-good zero-risk alternative already exists, so
  there is no upside that justifies the exposure.
- *Wait for a human to request explicit permission from the SSSD-ECG
  authors.* Not pursued — would consume timeline the 4-5 week schedule
  does not have, for a model that would only be an upgrade (patient-level
  conditioning), not a capability gap the GAN leaves unfilled.
- *Train a new ECG generative model from scratch.* Rejected per
  CLAUDE.md §12 — not justified when a working, validated, in-repo model
  already exists.

**Consequences:**
- ECG waveforms attached to synthetic patient records will be
  **diagnosis-class-conditioned only** (CD/HYP/MI/NORM/STTC — whichever
  PTB-XL superclass a patient's diagnoses map to), **not** conditioned on
  the patient's demographics, Indian-population characteristics, age, or
  sex — the GAN's 5 generators share no weights and take no conditioning
  vector beyond class. This limitation must be disclosed in product/
  provenance metadata, not overclaimed as personalized or
  Indian-specific ECG realism.
- Stage 4/M6/M7 ECG integration can now proceed (previously blocked
  pending this exact model-selection checkpoint).
- SSSD-ECG may be revisited later **only** if a human obtains and
  confirms an explicit, acceptable license directly from the authors or
  the Figshare item is later published with clear terms — not by
  re-attempting the same blocked automated checks.

---

## D017 — M8: blood pressure implemented as a label-conditional measurement; encounters as a declared structural container; height/weight still deferred; Schema v0.7 → v0.8

**Date:** 2026-10-20

**Decision:** `SCHEMA_VERSION` bumped `0.7` → `0.8`. New `BloodPressure`
and `Encounter` dataclasses; `TimelineEvent` gains
`reference_id: Optional[str]`; `Patient.blood_pressure` added and
`Patient.encounters` retyped `Optional[list[Any]]` →
`Optional[list[Encounter]]`. New vocabularies
`ENCOUNTER_TYPES = {"synthetic_baseline_assessment"}` and
`TIMELINE_EVENT_TYPES = {"synthetic_record_created",
"synthetic_baseline_assessment"}`.

**1. Blood pressure — the hypertension domain's label-only status ends,
but the LABEL stays primary.** D011 explicitly carved hypertension out
of its raw-value-primary architecture on the grounds that "hypertension
has no BP-distribution evidence yet", and
`docs/M4_CLINICAL_ARCHITECTURE.md` §1 recorded "BP continuous
distribution NEVER RESEARCHED — NOT SUPPORTED". M8's research pass
located it:

- Mean SBP/DBP by five-year age band × sex, NFHS-5 (101,839 men /
  724,115 women, 15+), via PLOS ONE 2025
  doi:10.1371/journal.pone.0332226 — this project's **first**
  age-conditioned cardiovascular evidence at national scope.
- Per-band SDs **derived** as `(CI_high − CI_low)/(2×1.96)×√n` from that
  paper's own mean/CI/n, then **externally validated**: recombined into a
  total SD they give male SBP 13.69 / DBP 10.24 mmHg against the
  independently published 13.8 / 10.2 (PMC11068163) — 0.8% and 0.4%.
- SBP/DBP correlation r = 0.7255 **derived** from
  `Var(PP) = Var(S) + Var(D) − 2r·SD_S·SD_D` using the SD(SBP)/SD(DBP)/
  SD(PP) triple PMC11068163 publishes together.

Architecture: **label → value**, the reversed direction D011 already
approved for HbA1c, NOT the lipid value → label pattern. The hypertension
label remains this project's evidence-primary variable (INDIAB-17
marginal); BP is drawn from the age-band × sex bivariate normal
restricted to the region the label's **own published definition**
implies (SBP≥140 and/or DBP≥90 and/or on antihypertensive). BP is never
used to re-derive hypertension and introduces no new prevalence claim.

The case that decides whether this is honest: a **treated** hypertensive
already satisfies the definition through medication, so the measurement
is left **unconstrained** — a treated patient may be controlled. Forcing
a raised reading there would be inventing a measurement to confirm an
existing label, and is the specific failure this design refuses.

**2. Encounters — a declared structural container, not a healthcare
visit.** Exactly one `synthetic_baseline_assessment` per record, naming
the single synthetic measurement cross-section (blood pressure, lipid
panel, HbA1c) that already shared one date and until now had no owner —
`docs/CLINICAL_RECORD_DESIGN.md` §H's
`Encounter --reference_id--> (nothing yet)`. No visit, admission,
appointment, physician, procedure or follow-up is generated, and no new
date is created (the encounter takes the record's existing
`labs.measured_at`). A care-seeking/utilization model stays deferred:
NSS 75th Round measures healthcare *expenditure behaviour*, not clinical
encounters, and `docs/INDIAN_GENERATION_STRATEGY.md` already classifies
it "E — Not Used".

**3. Height/weight — still NOT generated.** A national mean **and SD** of
Indian adult height by sex was searched for 6 times (3 in M4-0, 3 in M8)
and never located. The mean alone is insufficient: without a dispersion
figure the distribution's shape would be invented — the identical
objection M2D-2 used to **reject** a peaked within-BMI-category
distribution. Applying a weaker standard to height than to BMI was
declined. BMI remains the evidence-primary anthropometric.
`sample_height_cm()` exists as a tested no-op that **raises** if the
config ever gains height evidence while it still returns `None`, so the
gap cannot rot silently; `derive_weight_kg()` is implemented and tested
now.

**4. Family history — still null, and this is NOT an evidence decision.**
`docs/M4F_FINAL_CLINICAL_AUDIT.md` classifies the scope choice (LASI 45+
diabetes-family-history 14.33% for part of the population vs. none)
"**C — requires explicit human decision**". M8 did not make it. No
relatives, kinship links, family sizes or hereditary conditions were
invented, and no family-tree schema is proposed.

**5. One explicit engineering assumption: a 20 mmHg pulse-pressure
floor.** The only shaping parameter in the BP design that is neither read
off nor derived. Measured over 20,000 draws: independent SBP/DBP gave
pulse pressure < 20 mmHg in **10.70%** of records; adding the derived
correlation cut it to **1.98%**; the floor takes it to **0%**. A PP under
20 mmHg at these absolute levels indicates cardiogenic shock or severe
aortic stenosis, not a general-population finding. 20 sits ~2.4 SD below
the published Indian mean PP (42.9 ± 9.5). Deliberately asymmetric — no
upper cap — because wide PP is genuinely expected in older hypertensives.
Declared as tier B, with both distributions reported.

**Reason:** the evidence for BP existed and was simply not yet located,
so the honest response to finding it was to implement the measurement —
but only in the direction the evidence supports. Encounters and the
timeline reference were the smallest additions that let the record
describe its own dated structure without asserting care that never
happened. Height/weight and family history were the two places where
populating the field would have required inventing a distribution or
pre-empting a human decision, so both were left alone.

**Alternatives considered:**
- *Generate BP independently of the hypertension label* — rejected: the
  resulting raised-BP fraction (~20–22% from NFHS-5's own distribution)
  contradicts INDIAB-17's 35.5% label prevalence, producing records whose
  measurement and label disagree.
- *Assign BP from hypertension status* (e.g. a fixed hypertensive band) —
  rejected: that is the "invent a measurement that confirms the label"
  error, and it destroys within-group variance.
- *Sample SBP and DBP independently* — implemented first, then
  **discarded on measurement**: 10.70% of records had a clinically absurd
  pulse pressure. Independence was not a harmless simplification.
- *Truncated marginals or rejection sampling* — rejected for the joint
  integer-grid PMF: rejection needs a bail-out whose bias is silent
  exactly where it bites (the raised region sits ~2.6 SD out for women
  aged 20–24), and post-hoc rounding can push a value back across the
  threshold it was truncated against (measured: 1.7% label-rule
  violations before the rounding-safe fix).
- *Generate height from the ~165/152 cm secondary-source means with an
  assumed SD* — rejected, see §3.
- *Populate family_history from the LASI 45+ figure* — not rejected,
  **not mine to decide** (§4).

**Consequences:**
- `integration/migrate_v07_to_v08.py` is the reusable migration:
  idempotent, dry-runnable, pure, all-or-nothing, and it **replays each
  record's own recorded seed** to generate BP — verifying every
  pre-existing field matches before accepting the new one, so migration
  and fresh generation agree and the replay doubles as a provenance
  audit. BP is drawn **last** in `generate_indian_attributes()` precisely
  so every pre-existing field stays byte-identical for the same seed.
- Dry-run over all 100,000 records: **100,000/100,000 clean, 0 failures**,
  68.3 s (0.683 ms/record). The seed-replay audit passed for every
  record.
- 50-record pilot at `validation/pilot_50_records/`: 50/50 validated,
  179 tests passing (142 project + 37 pilot gates).
- **Known limitation, material:** NFHS-5 covers men to 54 and women to
  49, so **52.7%** of the dataset's BP values use the oldest band held
  constant (conservative — it understates BP in the elderly rather than
  inventing a trend). Flagged per record via
  `blood_pressure.extrapolated_beyond_source_age_range`. Closing it needs
  a verified age-banded mean+SD table from LASI Wave 1 (45+).
- **The generated BP marginal is NOT NFHS-5's marginal** and must not be
  validated against it: it is NFHS-5's per-band shape reweighted to agree
  with INDIAB-17's prevalence. Unavoidable given two disagreeing sources,
  and the reason the label stays primary.
- **Pre-existing defect surfaced, not introduced:** `lipid_panel`'s
  independent TC/TG/HDL marginals produce triples violating
  `TC ≥ HDL + TG/5`, which LDL's clip floor absorbs — **2,283 records
  (2.3%) are internally impossible** and **9,831 (9.8%)** carry an LDL
  that is the clip floor rather than a derivation. Now counted as a
  validator warning rather than invisible. Resolving it is a D011-level
  decision and is **not** made here; the smallest evidence-neutral option
  is to reject and redraw infeasible triples.
- Three pre-existing tests that asserted the pre-M8 state were updated
  (schema version; `encounters` leaving the unimplemented-domains list),
  and a replacement test added so no coverage was lost.
- Full-scale migration **not run**. Recommended only after the lipid
  decision above, since re-migration would invalidate review already done
  against the output.

---

## D016 — M4E: Medications implemented at drug-class level only (antihypertensive/antidiabetic), gated on NNMS treatment rates; statin/antiplatelet deferred; Schema v0.6 → v0.7

**Date:** 2026-09-27

**Decision:** `Patient.medications` (`Optional[list[Any]]` →
`Optional[list[Medication]]`) is populated for every patient.
`SCHEMA_VERSION` bumped `0.6` → `0.7`. New `Medication` dataclass
(`medication_id`, `drug_class`, `diagnosis_id`, `current_status="active"`,
`start_date=None`, `stop_date=None`, `source="derived_from_diagnosis_
treatment_rate"`). New vocabularies `MEDICATION_DRUG_CLASSES =
{"antihypertensive", "antidiabetic"}`, `MEDICATION_STATUSES = {"active",
"discontinued"}` (only `"active"` is ever produced).

`generation.indian_population.sample_medication_treatment()` draws one
Bernoulli per diagnosable condition present, from ICMR-NNMS 2017-18's
national treatment-rate cascades (antihypertensive 14.5%, antidiabetic
36.1%) — the same survey already used for `risk_factors.hypertension`/
`bmi`/`smoking_status`. `generation.clinical_history.derive_medications()`
constructs `Medication` records deterministically from that
already-resolved outcome, referencing the corresponding `Diagnosis` by
id — never a second independent generator.

**Only drug class, never a specific drug name, is generated.** NLEM
2022 confirms certain drugs (amlodipine, enalapril/ramipril, metformin,
teneligliptin, insulin glargine) are essential medicines, but no Indian
source reports what fraction of treated patients receive which specific
drug or even which pharmacological subclass (ACE-i vs. CCB vs. ARB) —
generating one would invent a distribution NLEM's mere availability
listing cannot supply. `drug_class` therefore stops at the coarse
therapeutic category NNMS itself measured ("antihypertensive"/
"antidiabetic"), not a finer pharmacological subclass.

**Statin and antiplatelet medications are not generated at all.** No
Indian population-level treatment-rate evidence exists for either (the
only statin figure found, the UNICORN study's 99.19%, is a hospital
cohort of already-treated patients, excluded per this project's
standing non-representative-cohort rule). Statins are additionally
blocked by D015's hyperlipidemia-diagnosis deferral — there is no
diagnosis to gate a statin against even if a rate existed. Antiplatelet
therapy has no diagnosis to gate against either (its usual indication,
a prior CVD event or a primary-prevention risk score, is not generated
by this project).

**`start_date`/`stop_date` are always `None`.** No per-patient
medication-initiation-date distribution exists (same conclusion as
`Diagnosis.diagnosed_date`, D015). `current_status` is always
`"active"` — a direct mapping of what NNMS's cross-sectional design
actually measured (point-prevalence of "currently treated"), not an
invented assumption; no discontinuation-rate evidence exists to
generate `"discontinued"` records.

**Reason:** implements `docs/CLINICAL_RECORD_DESIGN.md` §F's already-
designed dependency chain (`diagnosis → drug class → medication →
dates`) truncated at exactly the point the evidence stops, per this
milestone's own explicit instruction ("if only class-level treatment
evidence exists, stop at class level rather than inventing drug-name
prevalence"). The schema change is additive/backward-compatible
(`medications` was `None` for every patient ever generated, M1-M4D) and
follows the exact precedent of D006/D012/D015.

**Alternatives considered:** Generate specific drug names by sampling
uniformly among NLEM-listed candidates per class. Rejected — a uniform
distribution across drugs with no real share evidence is itself an
invented claim, exactly what this milestone forbids. Condition the
treatment-rate Bernoulli on sex (a real, more granular NNMS figure was
found: hypertension treatment M10.9%/F18.8%). Rejected — `risk_factors.
hypertension` itself is generated as a sex-unconditioned national
marginal (M2D, confirmed correct); conditioning only the downstream
treatment rate on sex while the diagnosis it depends on remains
sex-unconditioned would introduce an inconsistent asymmetry not present
anywhere else in this project's architecture. Documented in
`docs/M4E_MEDICATION_EVIDENCE.md`, not adopted. Generate statin
medications from `lipid_interpretations` presence alone, ignoring the
missing treatment-rate evidence. Rejected — would invent a treatment
probability with no source.

**Consequences:** `configs/indian_population.yaml` gains a
`medications` top-level key (`antihypertensive_treatment_rate`,
`antidiabetic_treatment_rate`), same full traceability metadata as every
existing parameter. `generation/indian_population.py` gains
`sample_medication_treatment()`, wired into `generate_indian_attributes()`
strictly after HbA1c (additive at the end of the existing draw sequence
— preserves every previously-generated field's determinism).
`generation/clinical_history.py` gains `derive_medications()`.
`validation/structural.py` gained `MEDICATION_DRUG_CLASSES`/
`MEDICATION_STATUSES` membership + duplicate-`medication_id` checks.
`validation/clinical_consistency.py` gained
`medication_diagnosis_consistency` (orphan-reference, drug_class↔
diagnosis-code mapping, active/stop_date, start/stop ordering,
one-medication-per-diagnosis checks) and dropped `medications` from its
"unimplemented domains" list. Verified: 0 differences in demographics/
risk_factors/lipid_panel/lipid_interpretations/labs/diagnoses/
medical_history vs. the M4D baseline at n=100 (700/700 field
comparisons exact); observed treatment rates (5/34 hypertension,
14.7%; 3/9 diabetes, 33.3%) statistically indistinguishable from the
cited rates (exact binomial p=1.000 both). 103/103 tests passing (25
new).

---

## D015 — M4D: Diagnoses/medical_history implemented as a 1:1 promotion of risk_factors, hyperlipidemia's diagnosis deferred; Schema v0.5 → v0.6

**Date:** 2026-09-26

**Decision:** `Patient.diagnoses` (`Optional[list[Any]]` → `Optional[
list[Diagnosis]]`) and `Patient.medical_history` (`Optional[dict[str,
Any]]` → `Optional[list[MedicalHistoryEntry]]`) are populated for every
patient. `SCHEMA_VERSION` bumped `0.5` → `0.6`. New dataclasses
`Diagnosis` (`diagnosis_id`, `code`, `diagnosed_date=None`,
`source="derived_from_risk_factors"`) and `MedicalHistoryEntry`
(`category`, `description`, `diagnosis_id`, `event_date`). New
controlled vocabularies `DIAGNOSIS_CODES = {"hypertension", "diabetes"}`
and `MEDICAL_HISTORY_CATEGORIES = {"diagnosis", "cv_event", "procedure",
"chronic_condition"}` (only `chronic_condition` is ever produced).

`generation/clinical_history.py`'s `derive_diagnoses()`/
`derive_medical_history()` are pure, deterministic, RNG-free functions:
diagnoses are a 1:1 promotion of the already-generated `hypertension`/
`diabetes` risk_factors flags (no new prevalence, no independent
re-sampling); medical_history entries reference those diagnoses by id
rather than re-deriving them from risk_factors directly.

**`hyperlipidemia`'s diagnosis is deliberately deferred** — the future
`diagnoses.hyperlipidemia` entry was already committed, in the prior
milestone's PROJECT_STATE.md note, to source from `lipid_interpretations`
rather than `risk_factors.hyperlipidemia` (per D014 and
`docs/M4_CLINICAL_ARCHITECTURE.md`'s two-hop-chain design). But
`lipid_interpretations` holds two coexisting, sometimes-disagreeing
definitions (NCEP_ATP_III, LAI_2020) by deliberate human decision
(D011) — collapsing them into one diagnosis boolean would silently make
exactly the canonical-definition choice D011 declined to make. Deferred
rather than resolved unilaterally, per this milestone's own "choice
between incompatible clinical interpretations" STOP condition.

`diagnosed_date`/`event_date` are always `None` — no per-patient
onset-date evidence exists (`docs/M4_CLINICAL_EVIDENCE.md` §7); only
population rates by age band (LASI, 45+ only) were found, not an
onset-date distribution to sample from.

**Reason:** implements `docs/CLINICAL_RECORD_DESIGN.md` §D/§E's
already-designed relationship (hypertension/diabetes → diagnosis is
"reformatting already-evidence-backed data, not inventing new
prevalence") as the minimum schema change required. The schema change
itself is additive/backward-compatible (both fields were `None` for
every patient ever generated, M1-M4C) and follows the exact precedent
of D006/D012 (retype an untyped placeholder into a real dataclass,
proceed autonomously, record the decision) — not the kind of
"significant restructuring" `CLAUDE.md` §28 reserves for a mandatory
human checkpoint.

**Alternatives considered:** Pick one lipid definition (e.g. NCEP_ATP_III)
as canonical for the hyperlipidemia diagnosis. Rejected — recreates
exactly the "pick one guideline body as more correct" choice D011's
human decision explicitly declined to make; would need its own human
sign-off, not made here. Generate both NCEP- and LAI-based hyperlipidemia
diagnosis entries side by side. Considered, deferred rather than
rejected outright — a reasonable future option, but adds complexity
this milestone's scope doesn't require given hypertension/diabetes
alone already satisfy M4D's stated objective. Derive `diagnoses.
hyperlipidemia` from `risk_factors.hyperlipidemia` instead. Rejected —
D014 already established that field as a population/background
attribute, not a per-patient diagnosis source.

**Consequences:** `integration/build_patient.py` calls
`derive_diagnoses()`/`derive_medical_history()` after risk_factors are
generated; `validation/structural.py` gained `DIAGNOSIS_CODES`/
`MEDICAL_HISTORY_CATEGORIES` membership checks; `validation/
clinical_consistency.py` gained `diagnosis_risk_factor_consistency`/
`medical_history_diagnosis_consistency` hard-rule checks and dropped
`diagnoses`/`medical_history` from its "unimplemented domains" list.
Verified: 0 differences in demographics/risk_factors/lipid_panel/
lipid_interpretations/labs vs. the M4C baseline at n=100 (a pre-existing,
unrelated `ecg.superclasses` list-*order* non-determinism was observed,
traced to reused `syngen` code's `set()`→`list()` conversion, not to
this milestone's changes). 78/78 tests passing (20 new).

---

## D014 — M4C: `risk_factors.hyperlipidemia` and `lipid_interpretations` are distinct, intentionally non-agreeing variables (Option B)

**Date:** 2026-09-26

**Decision (human-directed):** `risk_factors.hyperlipidemia` and
`lipid_interpretations` are kept as two permanently distinct fields,
not reconciled:

- `risk_factors.hyperlipidemia` — population/background risk-factor
  attribute. Unconditioned `Bernoulli(0.812)` from ICMR-INDIAB-17's
  national dyslipidaemia marginal. Same role and evidentiary class as
  `risk_factors.hypertension`/`diabetes`. A statement about the
  synthetic population's calibrated background prevalence.
- `lipid_interpretations` — deterministic classifications computed from
  this patient's own `lipid_panel` values, per named definitions
  (NCEP_ATP_III, LAI_2020).

Disagreement between them is expected and carries no validation
meaning. `lipid_panel` ↔ `lipid_interpretations` remains a **hard**
consistency requirement (unchanged, D011/D012/D013) — only the
`risk_factors.hyperlipidemia` ↔ `lipid_interpretations` relationship is
exempted.

**Scoping clarification of D011:** D011's clause "LDL and hyperlipidemia
must never be independently generated as unrelated random variables" is
clarified — not reversed — to apply only to the raw LDL value and its
own derived `lipid_interpretations` entry (the pair D011's Decision 2
was actually about, and the only pair D012/D013 actually implemented as
a pure function). It never applied to, and was never implemented as
applying to, the separate M2C-era `risk_factors.hyperlipidemia` field.
D011's own text is left unedited, per this project's append-only
decision-log convention (see D004's own "must be superseded, not
silently overwritten" precedent) — this entry is the authoritative
scoping note going forward.

**Reason:** A full semantic audit (`docs/M4C_HYPERLIPIDEMIA_RESOLUTION.md`)
traced `risk_factors.hyperlipidemia` to its M2C origin and found it was
always designed and built as a population-prevalence risk-factor
attribute (same generation pattern as hypertension/diabetes,
documented since M2A/M2B/M2C), never as a per-patient claim derived
from lipid measurements — `lipid_panel` didn't exist for two more
milestones. The empirically-measured 73-77% disagreement
(`docs/M4C_CONSISTENCY_AUDIT.md`) is not a bug: it is the expected
result of two independently-evidenced variables describing related but
distinct facts. D011's broad "never independently generated" wording
was written before `lipid_interpretations` existed as a named field and
was never actually implemented that strictly — M4B (D013) left
`sample_hyperlipidemia()` fully independent and D013 never claimed
otherwise.

**Alternatives considered:** Deprecate `risk_factors.hyperlipidemia` in
favor of `lipid_interpretations` (rejected by human decision — would
discard a distinct, separately-evidenced population attribute).
Retrofit `risk_factors.hyperlipidemia` to be derived from
`lipid_interpretations`, changing M2C generation behavior (rejected —
Option B explicitly keeps both; also would be a generation-behavior
change this milestone's own restrictions forbid making unilaterally).

**Consequences:** `validation/clinical_consistency.py`'s existing
`hyperlipidemia_vs_lipid_interpretations_intentionally_not_compared`
check (already never treated disagreement as an error) gets its
docstring updated to cite this decision. No schema, generation,
distribution, or lipid-derivation code changes.
`docs/M4_CLINICAL_ARCHITECTURE.md`'s future `diagnoses.hyperlipidemia`
design (sourced from the lipid raw-value chain, not from
`risk_factors.hyperlipidemia`) is reaffirmed, unchanged, for the future
M4D milestone.

---

## D013 — M4B: lipid/HbA1c generation logic (Friedewald-derived LDL, computed interpretations, diabetes-conditional HbA1c)

**Date:** 2026-09-26

**Decision:** Implemented the generation logic approved by D011/D012.

1. **Lipid panel:** total cholesterol, triglycerides, and HDL are each
   sampled via category-then-uniform draws from their own
   ICMR-INDIAB-17 national marginal rates (same engineering pattern
   already used for BMI). **LDL is not independently sampled** — it is
   **derived via the Friedewald equation** (`LDL = TC − HDL − TG/5`),
   the same formula ICMR-INDIAB-17 itself used to compute LDL from its
   directly-measured components. This was chosen over independent
   sampling of all four components after a quantified check: assuming
   full independence at the four components' own cited marginal rates
   implies an 86.5% composite dyslipidemia rate, materially higher than
   the actual cited 81.2% — evidence that the components are really
   correlated, and that independent sampling would systematically
   overstate the composite rate. Using Friedewald is not an invented
   correlation; it is the source's own calculation method.
2. **Lipid interpretations:** computed (never sampled) for both
   already-approved definitions (NCEP_ATP_III, LAI_2020) from the same
   generated raw values, per D011.
3. **HbA1c:** generated only for non-diabetic (NGT) patients, using
   ICMR-INDIAB-12's age×sex-conditioned trend (5.16%→5.49% across the
   age range, with a sex-specific decade slope); **not generated for
   diabetic patients** (thin, non-representative 4-state evidence only)
   — `labs` stays `None` for them, the same precedent as
   `family_history` (D004). Conditional on the already-generated
   `diabetes` label, never the reverse (D011's HbA1c finding).

Full evidence audit and every engineering-vs-evidence classification:
`docs/M4B_GENERATION_DESIGN.md`.

**Reason:** implements the M4-0/M4-0A/M4-0B evidence and architecture
work as the smallest defensible generation logic, reusing this project's
existing category-then-uniform pattern rather than inventing a new one,
and using a real clinical formula (Friedewald) rather than either (a)
inventing a correlation or (b) accepting a known, quantified independence-
inflation bias without any mitigation.

**Alternatives considered:** Independently sample all four lipid
components. Rejected — quantified to overstate the composite prevalence
relative to real evidence (86.5% vs. 81.2%), for no simplicity benefit
over Friedewald (which is arguably simpler, since it's one less
category-then-uniform draw to configure). Condition HbA1c on both sex
and urban/rural simultaneously. Rejected — would require an interaction
assumption neither source paper reports; sex alone is architecturally
consistent with how BMI/smoking are already conditioned elsewhere, and
urban/rural's effect size is small (0.08 vs. 0.10 %/decade) relative to
sex's (0.06 vs. 0.10).

**Consequences:** `configs/indian_population.yaml` gains `lipid_panel`,
`lipid_definitions`, and `hba1c` entries under `risk_factors`, each with
the same full traceability metadata as every existing parameter.
`generation/indian_population.py` gains `sample_lipid_panel()`,
`derive_lipid_interpretations()`, `sample_hba1c()`, plumbed into
`generate_indian_attributes()` and `integration/build_patient.py`.
Verified: a regenerated 10-patient sample shows **0 differences** in
demographics/risk_factors vs. the M4A baseline (full backward
determinism preserved — this milestone only *adds* new populated
fields, changes nothing existing). At n=100: NCEP composite dyslipidemia
observed at 84.0% (binomial p=0.52 vs. cited 81.2% — not statistically
distinguishable at this sample size, though the residual
independence-inflation limitation is real and documented, not hidden);
LAI composite 88.0% (p=1.00 vs. cited 87.3%). 6/100 patients hit the LDL
floor-clip safeguard; 0 hit the ceiling. 42/42 tests passing (11 new in
M4B on top of M4A's 31).

---

## D012 — M4A: implement `LipidPanel`/`LipidInterpretation`/`Lab` schema (Schema v0.4 → v0.5)

**Date:** 2026-09-26

**Decision:** `SCHEMA_VERSION` bumped `0.4` → `0.5`. Three additive
dataclasses added to `schemas/patient_schema.py`:
- `LipidPanel` — raw/continuous LDL, HDL, triglycerides, total
  cholesterol (mg/dL, field-name unit suffixes matching the existing
  `Demographics.height_cm`/`weight_kg` convention).
- `LipidInterpretation` — a derived label (`dyslipidemia: bool`) tagged
  by which `definition` (free-text, e.g. `"NCEP_ATP_III"`, `"LAI_2020"`)
  produced it, plus `components_abnormal` (from the new closed
  `LIPID_COMPONENTS` vocabulary) and a `source_citation` string.
- `Lab` — a generic, reusable single-measurement structure (`analyte`,
  `unit`, `value`, `measured_at`), used directly for HbA1c rather than a
  dedicated `HbA1cRecord` type.

`Patient` gains `lipid_panel: Optional[LipidPanel]`,
`lipid_interpretations: Optional[list[LipidInterpretation]]`, and
`labs` is now typed `Optional[list[Lab]]` (previously untyped
`Optional[list[Any]]` since M1). All new/retyped fields default to
`None` — no existing construction call breaks.
`validation/structural.py` gained matching structural (not clinical)
checks: lipid values within an outer physiological sanity range
(0-500 mg/dL — not a clinical threshold, see below), lipid
interpretations reference a non-empty `definition` and only
`LIPID_COMPONENTS`-vocabulary component names, and lab entries' `unit`
matches the new `ANALYTE_UNITS` reference table when the analyte is
known.

**Reason:** implements `docs/DECISIONS.md` D011's human-approved
architecture (raw lipid values primary, multiple tagged derived
interpretations, HbA1c via existing/generic Lab infrastructure) as the
minimum schema change required, per M4A's explicit scope. `labs` being
retyped from `Any` to `Lab` closes a placeholder gap open since M1 —
`docs/CLINICAL_RECORD_DESIGN.md` §G had already proposed exactly this
shape (`analyte`/`value`/`unit`/`measured_at`), so this is a direct,
non-speculative implementation of prior design work, not a new
invention.

**Deliberate scope limits (per M4A's explicit instructions, not
oversights):**
- No generation logic — every new field is populated with real data by
  nothing yet; all patients generated under this schema still have
  `lipid_panel`/`lipid_interpretations`/`labs` as `null`.
- No clinical-value validation (e.g. "LDL=132 → dyslipidemia=true") —
  deferred to the milestone where derivation logic actually exists;
  M4A's validation is structural only (ranges, units, vocabulary
  membership).
- `lipid_interpretations` is a **sibling** field to `lipid_panel` on
  `Patient`, not nested inside `LipidPanel` as
  `docs/M4_CLINICAL_ARCHITECTURE.md`'s illustrative pseudocode sketched
  — matches M4A's own Step 3/Step 5 examples, which present them as
  parallel structures; this is a refinement of that document's
  illustrative sketch, not a departure from D011's substance (raw
  primary, derived tagged-by-definition, multiple coexisting are all
  preserved).
- No BP/hypertension, family-history, medications, ECG, or Echo changes
  — explicitly out of scope per M4A's instructions.

**Alternatives considered:** A dedicated `HbA1cRecord` dataclass instead
of reusing `Lab`. Rejected — `Lab`'s generic shape represents HbA1c
cleanly with no information loss, and a dedicated type per analyte would
duplicate structure for every future lab (glucose, etc.) this project
adds, contradicting M4A's explicit "prefer reuse" instruction.

**Consequences:** Existing M1-M3.5 generated JSON files on disk are
unaffected (confirmed: no code anywhere in this repository deserializes
JSON back into a `Patient` object — every consumer reads plain dicts —
so there is nothing for the new optional fields to break). A regenerated
10-patient sample under this schema was diffed against the original
M2C 10-patient baseline: **0 differences in demographics or
risk_factors** — full backward determinism preserved. 31/31 tests
passing (11 new).

---

## D011 — Clinical variable architecture: raw value primary, derived interpretation secondary (where evidence supports it)

**Date:** 2026-09-26

**Decision (human-directed, M4-0B):**
1. **Dyslipidemia:** the continuous lipid measurement (LDL, and by the
   same logic HDL/triglycerides/total cholesterol) is the **primary**
   generated/stored value. Multiple documented clinical definitions
   (NCEP/ATP III, Lipid Association of India, and any future one) each
   derive their own categorical label **from** that value, tagged by
   which definition produced it. No single threshold is adopted as
   universal medical truth — resolving the M4-0A conflict (81.2% vs.
   87.3% dyslipidemia prevalence, NCEP LDL≥130 vs. LAI LDL≥100) by
   preserving both interpretations rather than picking a winner.
2. **LDL generation architecture:** generate the raw value first; derive
   interpretations afterward via a pure function over stored definition
   thresholds. LDL and hyperlipidemia must never be independently
   generated as unrelated random variables (the exact failure mode
   `docs/DECISIONS.md` D004 already warned against for a different
   field pair).
3. **Project-wide principle:** apply
   `raw/continuous value → derived interpretation` wherever the evidence
   genuinely supports it (labs is the clear case); do **not** force it
   where it doesn't (hypertension has no BP-distribution evidence yet;
   HbA1c's evidence actually supports the *reverse* direction — see
   below).

**Reason:** M4-0A's research found the dyslipidemia conflict was not a
contradiction but a definitional difference (different LDL cutoffs,
otherwise-identical component definitions) — preserving the raw value
and multiple tagged interpretations is the architecture that actually
fits what the evidence showed, rather than arbitrarily preferring one
guideline body.

**Refinement discovered while applying the decision (not a
contradiction, an application detail):** HbA1c does not fit the general
principle in the same direction as lipids. This project's diabetes label
is already its most evidence-backed variable (a national-marginal
Bernoulli directly from ICMR-INDIAB-17's own FPG/OGTT-based definition).
HbA1c's own distribution evidence (ICMR-INDIAB-12) is conditional on
diabetes status (a strong NGT-population trend; thin diabetic-population
data), not an independent primary quantity diabetes status should be
re-derived from. Architecture: diabetes label (already generated) →
HbA1c value generated conditionally on it — the reverse of the lipid
pattern, and exactly the kind of case Decision 3's own "must not force
this pattern where evidence doesn't support it" clause anticipated. This
does not reopen or contradict the human decision; it's a documented
instance of applying it correctly.

**Alternatives considered:** Pick one lipid definition as canonical
(rejected by explicit human decision — see M4-0A's finding that neither
guideline body's cutoff is "more correct," they answer different
questions). Keep LDL and hyperlipidemia as independently-generated
variables (rejected — recreates the exact inconsistency problem D004
already established this project avoids).

**Consequences:** `docs/M4_CLINICAL_ARCHITECTURE.md` is the full design
(schema audit, per-domain classification, consistency rules, dependency
graph, validation architecture). No schema change is made by this
decision — implementation is future M4 work, using this decision as its
already-satisfied human-checkpoint (`docs/M4_CLINICAL_ARCHITECTURE.md`
§8 marks the lipid/HbA1c schema additions "READY FOR M4 IMPLEMENTATION"
on this basis, not requiring a second sign-off). Hypertension remains
label-only pending BP-distribution research this project has not yet
conducted — explicitly not addressed by this decision.

---

## D010 — M3.5 candidate-improvement dispositions: urban/rural BMI (deferred), ECG-ID reuse (deferred to Stage 4), state boundaries (preserved)

**Date:** 2026-09-26

**Decision:** Three of M3's four candidate improvements are **not
implemented**, each for a distinct, documented reason — this entry
records the investigation outcome so it isn't silently re-litigated.

**1. Urban/rural-conditioned BMI — DEFERRED, requires a project-level
methodology decision.** M2C-0's own research found NNMS reports BMI
category prevalence by sex (men/women) **and separately** by urban/rural
(urban/rural), from the same national paper — but not as a single joint
sex×urban/rural×BMI table. There is no evidence-supported way to combine
"P(overweight|male)=23.3%, P(overweight|female)=29.3%" with
"P(overweight|urban)=42.5%, P(overweight|rural)=18.0%" into one
generation rule for a specific (sex, urban_rural) pair without inventing a
combination method (e.g., assuming independence and multiplying odds) —
that would be an engineering assumption presented as if it were sourced
evidence, which this project does not do silently. **Not implemented.**
Revisit only after an explicit decision on acceptable combination
methodology, or if a genuine joint table is located.

**2. ECG-ID reuse across synthetic patients — DEFERRED until Stage 4.**
Investigated `schemas/patient_schema.py`, `ingestion/ptbxl_source.py`,
`integration/build_patient.py`: `ecg_id` is purely an inherited PTB-XL
source-record identifier (metadata-only, `docs/DECISIONS.md` D003) — not
a synthetic-ECG identifier, since no synthetic ECG yet exists
(`signal_available` is always `False`). Whether multiple synthetic
patients may legitimately share a source ECG record depends entirely on
a not-yet-made Stage 4 design decision (will ECG signals be
newly-synthesized-per-patient, or reused-as-a-conditioning-template, or
something else?). Changing the current independent-per-patient sampling
to a without-replacement scheme would also be a real architecture change
(stateful, order-dependent generation vs. today's clean
per-patient-independent-of-batch-order determinism) — not a small tweak.
**Not implemented.** Explicitly flagged for human awareness: this is a
real, measured issue (30 duplicate `ecg_id`s at n=1,000) that will need a
decision before Stage 4, not indefinitely.

**3. Census 2011 state/UT boundaries — PRESERVED, no change.** M2D found
the 35-entry table uses 2011-vintage administrative boundaries
(Telangana, J&K, Daman-Diu/Dadra-Nagar-Haveli predate later
reorganizations). No current-boundary Census-quality replacement source
was located in M2C, M2D, or this session's research. Per the default
position this milestone was given ("preserve Census 2011 representation
unless evidence indicates a necessary correction"): changing boundaries
without a proper current-boundary source would require inventing a
population split (e.g. guessing Telangana's share of undivided Andhra
Pradesh's 2011 figure) — that would REDUCE fidelity to the cited source,
not improve it. **Not changed.** No new dataset introduced, per this
milestone's restriction.

**Consequences:** `docs/M3_5_CANDIDATE_IMPROVEMENTS.md` records the full
audit (all four candidates, including the one that WAS implemented,
D009). None of these three deferrals change
`configs/indian_population.yaml`'s distribution values or the synthetic
population's target definition (D008).

---

## D009 — Cache PTB-XL CSV/label-map parsing at process level (performance fix, zero content change)

**Date:** 2026-09-26

**Decision:** `ingestion/ptbxl_source.py`'s `pick_ecg_id()` and
`load_ptbxl_record()` now read `ptbxl_database.csv` and build the
SCP-to-superclass label map **once per process** (via
`functools.lru_cache`) instead of once per patient.

**Reason:** M3 measured 1,000-patient generation taking 37 minutes and
attributed it (imprecisely) to "I/O-bound" behavior. M3.5 profiled it
properly before touching anything (`integration/profile_generation.py`)
and found the actual bottleneck is **CPU-bound**: `build_label_map()`
(reused from syngen, unmodified) runs `ast.literal_eval` over all
~21,837 `scp_codes` values on every call — measured at ~4.9s per call —
and was being called fresh for every single patient, alongside 3 more
redundant CSV reads per patient (raw `pd.read_csv` alone measured at only
~0.2s, confirming file I/O itself was never the real cost). Caching the
parsed result (same inputs always produce the same label map — this is a
pure function of file contents) eliminates the redundant work without
changing what it returns.

**Alternatives considered:** Rewrite `build_label_map()`'s internal
parsing to be faster (e.g., vectorized instead of per-row
`ast.literal_eval`). Rejected — that would mean modifying syngen's
reused function itself (`docs/DECISIONS.md` D002's "reuse before rebuild"
principle), a larger and riskier change than caching its *result* in our
own adapter file, for no additional benefit at our current scale.

**Verification:** Regenerated the identical 1,000-patient population
(`outputs/m3_5/1000_patients/`, same seeds) and diffed against M3's
baseline (`outputs/m3/1000_patients/`) — **0 differences in demographics
or risk_factors, 0 real ECG content differences** (only the
already-documented, pre-existing ECG-superclass-list ordering noise from
Python's `set()` iteration, unrelated to this change). Added
`tests/test_ingestion_caching.py` (4 tests) confirming the cache
correctly distinguishes different `scp_threshold` values (the one thing
that could silently break if the cache key were wrong) rather than just
trusting it worked.

**Consequences:** 1,000-patient generation: 37 min → 20.4s (~110x).
Full test suite: 265s → 11s (~24x, since pytest shares one process across
all tests). 100,000-patient generation is now projected at minutes, not
~67 hours — removing the single largest measured blocker to scaling.
No generated content changed. `integration/profile_generation.py` is kept
in the repo as a reusable diagnostic, not a one-off script.

---

## D008 — Target population: the synthetic population represents the GENERAL Indian population

**Date:** 2026-09-26

**Decision:** The synthetic population this project generates represents
the **general Indian population**, not a cardiovascular-disease-only
population, not a hospital population, not a cardiology-clinic
population, not a high-risk cardiovascular cohort, and not an Indian CVD
patient registry. This is a project-level decision, resolving the open
question M2D-6 surfaced (`docs/session_logs/2026-09-25_M2D-calibration-quality-gate.md`
§3/§11) and recorded in `configs/indian_population.yaml`'s
`population.target_population_ambiguity_M2D6` field. It applies to all
future generation and validation work unless explicitly changed later.

**Scope clarification (not itself a new decision, restating an existing
one so it isn't lost next to this one):** "general population" here means
the general **adult** Indian population, ages 20-89 — the age-scoping
already decided in M1/M2C (`docs/DECISIONS.md` D004,
`configs/indian_population.yaml`'s `demographics.age`), which is a
separate, still-standing decision from this one. This decision does not
extend the target to include children (ages 0-19); it resolves *which
adult population* — general vs. clinical/CVD-specific — not *which age
range*.

**Reason:** M2D found the generator was implicitly stitching together
three different source populations (Census 2011's general population,
NNMS's surveyed adults 18-69, ICMR-INDIAB's surveyed adults 20+) without
any project document stating which one was actually the target. Per
M2D's own instruction ("record the ambiguity as a decision/question
rather than inventing an answer"), M2D surfaced this rather than
resolving it. This decision is that resolution, made explicitly at the
project level rather than inferred from implementation details.

**What this decision does NOT claim:** combining Census 2011 (2011,
general population, all ages), NNMS (2017-18, adults 18-69), and
ICMR-INDIAB-17 (2008-2020 fieldwork/2023 publication, adults 20+) does
**not** produce one single, internally consistent *observed* population.
These three sources remain exactly what `configs/indian_population.yaml`
already documents them as: **different pieces of evidence, from different
years/samples/age-ranges, each informing a different component** of one
*assembled, synthetic* general-population target:
- Census 2011 → demographic backbone (sex, state, urban_rural) for the
  general population.
- ICMR-NNMS 2017-18 → behavioral/metabolic risk-factor evidence (BMI,
  smoking) for the general adult population, with an acknowledged
  extrapolation gap for ages 70-89 (NNMS sampled only up to 69).
- ICMR-INDIAB-17 (2023) → cardiometabolic risk-factor evidence
  (hypertension, diabetes, hyperlipidemia) for the general adult
  population, whose 20+ sampled range matches this project's 20-89 scope
  well.

None of the existing per-parameter `evidence_tier` classifications in
`configs/indian_population.yaml` (A/B/C/D/E, per M2D-12) change as a
result of this decision — they already correctly described each
parameter's evidence status; this decision only settles *what the
assembled whole is meant to represent*, not the evidentiary status of any
individual piece.

**Alternatives considered (all explicitly rejected as the target):**
1. A cardiovascular-disease-only population. Rejected — no dataset
   examined (M2A/M2C/M2D) actually supports generating a population
   pre-conditioned on having CVD; ICMR-INDIAB/NNMS are population risk-
   factor surveys, not disease registries.
2. A hospital or cardiology-clinic population. Rejected — would require a
   clinical-encounter dataset (e.g. CREATE/STEMI-ACT, both found in M2A
   to be practically inaccessible and non-representative even where
   accessible — hospital-based, not population-based).
3. A high-risk cardiovascular cohort. Rejected — would require
   deliberately skewing demographic/risk-factor sampling toward high-risk
   strata, which none of the current evidence sources are structured to
   support without inventing a selection mechanism.
4. Leaving the target undefined (M2D's status quo). Rejected — M2D's own
   recommendation was to resolve this before scaling, precisely because
   leaving it undefined gets more expensive to fix the more patients are
   generated under an ambiguous assumption.

**Consequences:**
- No generator code changes result from this decision (per explicit
  instruction) — `generation/indian_population.py`,
  `configs/indian_population.yaml`'s actual distribution values, and
  `integration/build_patient.py` are unchanged.
- `docs/PROJECT_STATE.md` now states the target population explicitly, so
  future sessions don't have to re-derive or re-litigate it.
- Future work that would change this (e.g. later deciding to also build a
  CVD-conditioned or clinical sub-population as an additional, separate
  product) would be a new decision, not a silent reinterpretation of this
  one.

---

## D007 — M2D: keep `age ~ uniform(20, 89)` despite locating a better-sourced (but still too coarse) alternative

**Date:** 2026-09-25

**Decision:** Age remains generated as `uniform(20, 89)`, unchanged from
M2C. A better-provenanced whole-population age figure was found during
M2D's research pass (India's Registrar General population projections
based on Census 2011, via dataforindia.com: 0-14 24%, 15-59 65%, 60+ 11%,
current as of ~2026) — explicitly NOT adopted.

**Reason:** Converting the "15-59"/"60+" bands into our 20-89 adult range
requires assuming uniform population density within the 45-year-wide
15-59 band to extract a 20-59 sub-slice — a real population pyramid is not
flat across 45 years. This was quantified, not just asserted: the naive
reconstruction implies a 20-59 / 60-89 split of 84%/16%, versus
`uniform(20,89)`'s 57%/43% split — a large swing that would
**under-represent the 60-89 age band, exactly where cardiovascular risk
concentrates**, based on an assumption already known to be false.
Replacing an honestly-flat default with a wrong-shaped reconstruction
would be a worse error, not an improvement, for a project whose whole
point is cardiovascular risk modeling.

**Alternatives considered:**
1. Adopt the two-tier RGI-projection-derived split anyway, accepting the
   within-band-uniformity approximation. Rejected — quantified impact
   above shows this isn't a minor simplification, it's a materially wrong
   shape in exactly the dimension that matters most for this project.
2. Pursue India's Sample Registration System (SRS) Statistical Report
   2020 — the single most promising still-unresolved lead (official
   Registrar General of India source, likely has real age-band tables).
   Not adopted this session because the fetch failed on an SSL
   certificate error (a tooling/access problem, not a content problem) —
   worth a follow-up attempt via a different access method, not abandoned
   as a dead end.
3. Pursue NFHS-5's full India Report Table 3.1 (population by age/sex/
   residence) — attempted twice (M2C, M2D), both times the 600+ page PDF
   exceeded practical fetch limits. Same status as #2 — a real candidate,
   not yet accessible with the tools available this session.

**Consequences:** `configs/indian_population.yaml`'s `demographics.age`
block now documents this full reasoning (6 total research attempts across
M2C+M2D) so a future session doesn't have to re-derive it from scratch,
and specifically names SRS/NFHS-5 as the two leads worth retrying with a
different fetch method before concluding no age evidence exists at all.

---

## D006 — M2C: formalize `risk_factors` as a typed schema field; supersede D004's demographics placeholder with Indian-conditioned generation

**Date:** 2026-09-25

**Decision:** `Patient.risk_factors` changes from `Optional[dict[str, Any]]`
to a new typed `RiskFactors` dataclass (`bmi`, `smoking_status`,
`hypertension`, `diabetes`, `hyperlipidemia` — all `Optional`).
`SCHEMA_VERSION` bumped `0.3` → `0.4`. `integration/build_patient.py` now
generates `demographics.age/sex/state/urban_rural` and all of
`risk_factors` from `configs/indian_population.yaml` via the new
`generation/indian_population.py` calibration layer, **superseding** D004's
PTB-XL-reused-demographics placeholder as that decision itself said it
should be, when Stage 3 arrived. `demographics.height_cm`/`weight_kg`
remain `None` — out of M2C's strict scope. `family_history` remains
untouched (`None`) — no Indian evidence source exists (unchanged from
D004).

**Reason:** M2C (`docs/PROJECT_STATE.md`) required BMI/smoking_status/
hypertension/diabetes/hyperlipidemia to be present on every generated
patient with defined structure, which an untyped dict could technically
hold but without the presence/type guarantees `validation/structural.py`
needs to check them meaningfully (matches the same reasoning D005 used for
`state`/`urban_rural`). This was anticipated as REQUIRED in
`docs/INDIAN_GENERATION_STRATEGY.md` §15's schema gap analysis.

**Alternatives considered:** Keep `risk_factors` as an untyped dict and
just populate specific keys at generation time. Rejected — loses the type/
presence guarantees that make structural validation (and the M2C test
suite's presence checks) meaningful, for no real savings given the fields
were already fully enumerated in the strategy doc.

**Consequences:**
- `outputs/test/PAT_000001.json` and any patient generated before this
  decision have `risk_factors: null` under the old schema shape — not
  regenerated as part of this decision, since M1's original ECG-anchored
  patient is a historical artifact, not a live output.
- Every M2C-generated patient's `provenance.generator` field states
  explicitly which values are Indian-evidence-conditioned vs. not modeled,
  so a reviewer doesn't have to guess from the schema shape alone.
- See `docs/session_logs/2026-09-25_M2C-indian-conditioning.md` for the
  full M2C-0 evidence-verification results behind every value in
  `configs/indian_population.yaml`, and for which parameters are SUPPORTED
  vs. PARTIALLY SUPPORTED vs. NOT SUPPORTED.

---

## D005 — Adopt `state` and `urban_rural` as first-class Demographics fields

**Date:** 2026-09-25

**Decision:** `Demographics` gains two new `Optional[str]` fields —
`state` (Indian state/UT name) and `urban_rural` (`"urban"`/`"rural"`) —
implemented in `schemas/patient_schema.py`. `SCHEMA_VERSION` bumped
`0.2` → `0.3`. `validation/structural.py` gained one check: if
`urban_rural` is set, it must be `"urban"` or `"rural"`.

**Reason:** Resolves the two explicitly `OPEN` schema questions from
`docs/INDIAN_GENERATION_STRATEGY.md` (M2B) §15/§17 — the user directed
that both be adopted as first-class fields rather than deferred, overriding
M2B's more conservative recommendation (which had classified `urban_rural`
as USEFUL-but-not-required and `region`/`state` as a weaker, lower-priority
case). This is the human checkpoint M2B's schema gap analysis said was
required before either field could be added (`CLAUDE.md` §28).

**Scope of this change — deliberately narrow:** only the schema fields
were added. The "configurable, evidence-backed distributions" used to
*generate* values for these fields (M2C-2's `configs/indian_population.yaml`
state/urban-rural population shares, and M2C-3's sampling logic in a future
`generation/` module) are **not implemented by this decision** — those
still need cited Indian population figures (e.g., from NFHS-5, the primary
source M2B recommended for geographic/urban-rural calibration) verified
before being encoded, per the project's "verify, don't guess" rule
(`CLAUDE.md` §14, `docs/INDIAN_DATA_SOURCES.md`'s verification standard).
Every patient generated so far (including the regenerated `PAT_000001`)
has both fields as `null` — that's correct and expected until M2C-2/M2C-3
exist, not a bug.

**Alternatives considered:** Defer both fields per M2B's original
recommendation, revisiting only `urban_rural` first given its
stronger evidence base (§4 of the strategy doc). Superseded by explicit
user direction to adopt both now.

**Consequences:**
- `docs/INDIAN_GENERATION_STRATEGY.md` §15/§17/§18 should be read alongside
  this entry — its "OPEN"/"USEFUL, not required" framing for these two
  fields is now resolved by this decision, though the document itself was
  left as the historical record of the analysis rather than rewritten.
- The next concrete step for these fields is M2C-0 (verify exact source
  figures) and M2C-2 (encode them in `configs/indian_population.yaml`) —
  not yet started.
- `validated: true` on a patient with `state`/`urban_rural` both `null`
  remains structurally valid — these fields are optional at the schema
  level; only their *value* (if set) is validated.

---

## D004 — Demographics for the first synthetic patient are reused from the linked PTB-XL record, not independently randomized

**Date:** 2026-09-25

**Decision:** For M1, `age`/`sex`/`height`/`weight` are read directly from the same
PTB-XL row that supplies the ECG metadata (via `ingestion/ptbxl_source.py`),
instead of being drawn from an independent random distribution.

**Reason:** `docs/Claude.md` §9 (patient record philosophy) warns against
"producing records where clinically related fields are generated
independently without considering their relationships." Demographics and ECG
are clinically linked; sourcing both from the same real record keeps the one
patient record internally coherent for M1 without inventing a demographic
model prematurely (that is Stage 3's job). Age values `> 89` are clipped to
`89`, matching the known PTB-XL anonymization-age finding already recorded in
the top-level `CLAUDE.md` §2. The real PTB-XL `patient_id` is intentionally
**not** copied anywhere into the synthetic record (`CLAUDE.md` §10/§31) — only
the field *values* (age, sex, height, weight) are reused.

**Alternatives considered:** Independently sample age/sex now and connect ECG
separately. Rejected for M1 because it produces exactly the kind of
independently-generated, clinically-incoherent field pair the spec warns
against, for no benefit — Stage 3 is the right place to build a real
demographic generator.

**Consequences:** `provenance.generator` on the M1 patient explicitly says
demographics are "reused from the linked PTB-XL record's fields," not
generated. This must be superseded, not silently overwritten, when Stage 3
implements real synthetic demographic generation.

---

## D003 — ECG integration for M1 is metadata-only; signal generation stays deferred to Stage 4

**Date:** 2026-09-25

**Decision:** `ingestion/ptbxl_source.py` reuses `syngen`'s `build_label_map()`
(diagnostic-superclass mapping) and pulls one real record's metadata
(`ecg_id`, superclasses, `strat_fold`, filename, sampling rate, signal shape).
It does **not** load the actual `.dat`/`.hea` waveform via `wfdb`, and does
**not** invoke the trained GAN checkpoints to synthesize a signal.
`ECGRecord.signal_available` is `False` on every M1 patient.

**Reason:** `docs/Claude.md`'s milestone table separates "one structurally
valid patient" (Stage 2 / M1) from ECG signal integration (Stage 4 / M4/M8).
M1's checklist item "existing reusable ECG functionality connected where
practical" is satisfied by reusing the existing SCP-to-superclass mapping
logic and PTB-XL metadata — pulling in `wfdb` signal loading or the trained
GAN now would front-load Stage 4 work and risk the exact "generator-specific
logic leaking into ingestion" problem `CLAUDE.md` §4 warns against.

**Alternatives considered:** Load the real waveform now via `wfdb.rdrecord`
(available — see D002) and attach it as `signal_available=True`. Rejected as
scope creep past M1; revisit at Stage 4 when the milestone explicitly calls
for ECG signal integration.

**Consequences:** `ECGRecord` carries a `signal_available` flag so Stage 4 can
distinguish "metadata only" patients from ones with an attached waveform
without a schema change.

---

## D002 — Use the Anaconda Python interpreter for this project; add `wfdb` to it

**Date:** 2026-09-25

**Decision:** Development/test commands in this repo run under
`C:\Users\devg8\anaconda3\python.exe`, which already has `pandas`, `numpy`,
`torch`, and `pytest`. `wfdb` (not previously installed) was added to that
environment via `pip install wfdb` so that `syngen`'s `gan_pytorch.py` (which
imports `wfdb` at module level) can be imported directly instead of
re-implementing its PTB-XL loading logic.

**Reason:** The default `python` on PATH (`C:\Python314\python.exe`, 3.14.6)
has almost no packages installed (only `lxml`, `python-docx`). Reinstalling
the whole scientific stack there would duplicate an environment that already
exists and works. Installing `wfdb` is a small, reversible, non-expensive
local operation (`CLAUDE.md` §15 allows "small local tests and inference
runs"), and is required to reuse (not reimplement) `build_label_map()` per
the "reuse before rebuild" principle — `gan_pytorch.py` cannot be imported at
all without `wfdb` present, even though M1 only calls the pandas-only parts
of it (see D003).

**Alternatives considered:**
1. Reimplement `build_label_map()`'s CSV-parsing logic standalone, avoiding
   the `wfdb` dependency for M1. Rejected — this is exactly the duplicated
   logic `CLAUDE.md` §3/§18 says to avoid; the existing function already
   takes paths as parameters and needs no adaptation.
2. Install the scientific stack fresh under `C:\Python314`. Rejected —
   redundant with the working Anaconda environment and slower.

**Consequences:** Anyone running this repo's Python code must use the
Anaconda interpreter (or an environment with the same packages) until a
project-wide `requirements.txt`/environment file is formalized. A
minimal `requirements.txt` was added at the repo root recording the
packages actually required (see repo root).

---

## D001 — Repository structure: adopt Candidate A (flat, root-level)

**Date:** 2026-09-25

**Decision:** Use Candidate A from the spec
(`docs/superpowers/specs/2026-09-19-multimodal-cardio-dataset-spec-design.md`
§4.1) — flat, root-level `schemas/`, `ingestion/`, `integration/`,
`validation/`, `export/`, `generation/`, `tests/`, `configs/`, `experiments/`,
`docs/` — as the working repository structure, rather than Candidate B's
`src/`-nested layout.

**Reason:** The spec's §4.4 resolution point says to "pick the structure that
requires the least forced adaptation of working code" once the original
codebase was audited. The audit (`docs/syngen-codebase-analysis.md`, done
2026-09-22) found `syngen/SynGen/SynGen/` is a **flat collection of
standalone scripts** with no `src/`-style package nesting anywhere. Candidate
A's flat top-level modules are the closer fit — reused/adapted `syngen` code
can sit under `ingestion/` or `generation/` without an extra layer of
nesting. Candidate C (`ml/`) is structure-neutral per the audit and needs no
change either way; it continues to host model-agnostic training/eval
contracts alongside whichever generator concretely implements them under
`generation/`.

**Alternatives considered:** Candidate B (`src/`-nested, with a top-level
`data/` directory) from the Master Project Plan. Rejected for now because it
would require restructuring `syngen`'s flat scripts into a package layout
before anything could be reused, which is exactly the "forced adaptation"
the resolution rule says to avoid. Not deleted as an option — if a strong
reason to nest under `src/` shows up later, this decision should be revisited
here, not silently overridden.

**Consequences:** M1's new code (`schemas/`, `ingestion/`, `integration/`,
`validation/`) is created directly at the repo root, matching this
structure. `docs/superpowers/specs/...spec-design.md` §4 should eventually be
updated to record this resolution too (not done yet — the spec doc itself
says the day-to-day operating docs are what stay current turn-to-turn).
