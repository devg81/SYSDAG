# 2026-11-12 — M9: progress review + teammate status message reconciliation (Q&A) -jatin

**Session owner:** -jatin. Everything in this log (progress review, D014
explanation, D023 reversal, `review_samples_v011/`, the `-jatin` tags) was done
in Jatin's session.

## Request
User asked for an overall progress check and an explanation of project
context, and asked what a teammate's status message ("Where we stand /
Kept out of GitHub / Steps left", 13 steps) is asking them to do. The
user also shared the latest v0.10 sample-record report for reference.

## What was done
Read-only. Read `docs/PROJECT_STATE.md` (M9, M6, Human Decisions Required,
Next Action, Last Updated), `docs/ROADMAP.md`, `docs/DECISIONS.md`
(D018–D022), `docs/session_logs/2026-11-12_M9-v010-review-fixes.md`,
`docs/V010_CHANGE_REPORT.md` (open questions). No code, configs, schemas
or datasets touched.

## Finding: the teammate's message is stale against the repo
| Teammate says | Repo says (source) |
|---|---|
| 100K frozen at schema v0.8 | Re-frozen at **v0.9** on 2026-11-10, `outputs/m9/100k_patients_v09/`, 0 errors (PROJECT_STATE M9) |
| Family history + AQI planned, not built; needs sign-off | **Approved and built**: D020 (family history), D021 (AQI), both in the v0.9 freeze |
| D019 lipid fix not applied | **Applied** in the v0.9 freeze; then superseded by the D022 joint lipid model (v0.10, not yet frozen) |
| SSSD-ECG leading candidate, no model chosen | **D018 (2026-10-21): inherited per-class GAN selected; SSSD-ECG rejected** (weights licence unresolvable) |
| Steps 1–5 before ECG | Done, except the v0.10 open decisions + an optional v0.10 100K regeneration (~2 h) |

The message matches the repo state of ~2026-10-30 (and the Sept-27 ECG
view). Its "Kept out of GitHub" section is accurate. Steps 7–13 remain
valid, with step 6 already answered by D018 unless the team reopens it.

## Actual open items for the user (from PROJECT_STATE / V010 report)
1. v0.10 open questions, chiefly #1: reverse D014 and derive
   `risk_factors.hyperlipidemia` from the lipid panel?
2. Approve (or not) a v0.10 100K regeneration (~2 h local) and re-freeze.
3. Confirm D018 (GAN) with the teammate, or reopen ECG model selection.
4. Then start ECG integration (M7) in stages 10 → 100K.

## Files changed
- `docs/session_logs/2026-11-12_M9-progress-review-teammate-message.md` (this file)

## Commands / tests
None run beyond reading docs and `git log`.

## Datasets
None generated or modified.

## Decisions taken
None.

## Follow-up: D014 explained (Q&A, read-only)
User asked for an explanation of D014 (open question #1 in
`docs/V010_CHANGE_REPORT.md`). Read D014 in `docs/DECISIONS.md`,
`generation/indian_population.py` (draw order), and grepped all uses of
`risk_factors.hyperlipidemia`.

Findings:
- The flag is an independent `Bernoulli(0.812)` (INDIAB-17 marginal),
  drawn before and separately from the lipid panel; D014 (2026-09-26,
  human-directed) kept it deliberately unreconciled with
  `lipid_interpretations`.
- Only consumers: `integration/build_patient.py` (copies it into the
  record), `integration/validate_population.py` and
  `integration/analyze_m3_population.py` (prevalence checks). No
  diagnosis, medication, BP or timeline logic reads it, so a reversal
  has a small blast radius.
- Concrete sample example: `review_samples_v010/htn_dm_untreated_PAT_000095.json`
  has `hyperlipidemia: true` while both NCEP and LAI say dyslipidemia
  false (panel 143.2 / 70.4 / 45.8 / 83.3). The other 4 samples agree.
- Reversal side-effect to handle: removing the Bernoulli draw from the
  main RNG stream would shift every later field (lipid child seeds,
  treatment, BP, family history, onset) for the same seed, unless a
  placeholder draw is kept.

No decision taken; awaiting the user.

## Follow-up 2: D014 reversed → D023, applied to the 5 review samples
User: "Yes, reverse D014 on 5 datasets provided" (the 5 v0.10 review samples).

Changes:
- `generation/indian_population.py`: new `derive_hyperlipidemia()`; the
  Bernoulli draw is kept as a discarded placeholder (RNG alignment); the flag
  is derived after `derive_lipid_interpretations()`; docstrings updated.
- `configs/indian_population.yaml`: `risk_factors.hyperlipidemia.derivation`
  (method `derived_from_lipid_interpretations`, definition `NCEP_ATP_III`);
  `p: 0.812` kept as the statistical target.
- `schemas/patient_schema.py`: SCHEMA_VERSION 0.10 → 0.11, docstring.
- `integration/build_patient.py`: provenance text states the flag is derived.
- `validation/clinical_consistency.py`: hard check
  `hyperlipidemia_derived_from_lipid_interpretations` replaces
  `..._intentionally_not_compared`.
- Tests: version asserts → 0.11 (m4a, m8, v010); 4 D014 tests in
  `test_m4c_clinical_consistency.py` replaced with 4 D023 tests (agreement,
  both mismatch directions rejected, NCEP-not-LAI); m4d/m4e tests renamed to
  the new check; m4b comment.
- New `integration/rederive_review_samples.py`: upgrades stored records
  without PTB-XL/pandas, asserting RNG alignment field by field first.
- New `review_samples_v011/` (5 JSON + README); `docs/DECISIONS.md` D023;
  `docs/V010_CHANGE_REPORT.md` Q1 marked resolved; `docs/PROJECT_STATE.md`.

Environment: this machine's Python 3.14 had no pandas/scipy/wfdb/pytest.
Installed pandas 3.1.1, scipy, wfdb and pytest via pip (torch not installed).
pandas then failed to import ("An Application Control policy has blocked this
file", a Windows security policy, deliberately not changed). The PTB-XL CSVs
(`syngen/SynGen/SynGen/dataset/`) are also absent here (gitignored). So
`build_patient()` and **pytest could not run**. Only `py_compile` on the changed
modules and tests passed.

Checks run (`python integration/rederive_review_samples.py review_samples_v010
review_samples_v011` + a scratchpad comparison script):
- 5/5 samples structurally valid, clinically consistent, 0 warnings, D023
  check performed. Leaf diff vs v0.10: only provenance (3 fields) and, for
  PAT_000095 only, `risk_factors.hyperlipidemia` true → false.
- The old v0.10 PAT_000095 now FAILS the new validator (expected).
- 5,000 seeds, new generator vs HEAD generator: 0 records with any non-flag
  difference; flag == NCEP 5,000/5,000; prevalence 80.86%; 30.96% of flags
  changed.

Datasets: `review_samples_v011/` (5 records, seeds 43/53/55/57/137, config
`configs/indian_population.yaml` at this commit). The frozen 100K is untouched (v0.9).

Open: run `pytest tests` where PTB-XL exists; v0.10 open questions 2–4;
approve the v0.11 100K regeneration; `diagnoses.hyperlipidemia` still deferred.

## Follow-up 3: authorship tags + teammate message (-jatin)
User asked to mark everything created or updated this session with `-jatin`
and to draft a hand-off message for the teammate.
- Renamed this log to `...-teammate-message-jatin.md` and tagged its heading.
- Tagged: D023 heading + author line (`docs/DECISIONS.md`), the latest
  `docs/PROJECT_STATE.md` "Last Updated" entry, `docs/V010_CHANGE_REPORT.md`
  Q1, `review_samples_v011/README.md`, the D023 comments/docstrings in
  `configs/indian_population.yaml`, `schemas/patient_schema.py`,
  `generation/indian_population.py`, `validation/clinical_consistency.py`,
  `tests/test_m4c_clinical_consistency.py`, and the new script's docstring.
- NOT tagged on purpose: the 5 sample JSON records (an extra key would break
  the schema loader/validators, and records must not carry a person's name)
  and the provenance text that `build_patient()` writes into every record.
  Already-pushed commit messages were not rewritten.
- Hand-off message drafted in chat (not committed).

## Follow-up 4: open questions 2/3/9 + heavy-work location (-jatin)
User: "now let's move ahead and do the other things". I asked 4 questions, and the user answered:
- Q2 TG > 400: keep rejecting → **D025**.
- Q3 LAI tiers: simple risk rule → **D024**, schema v0.12.
- Q9 old pilot: rebuild at v0.12 → **D026**.
- Heavy work: "we will do this on AWS" → **D026** plus an AWS plan.

Evidence (web):
- LAI diabetic dyslipidaemia consensus (ScienceDirect S1933287422003002) and
  LAI 2023 Consensus IV (S1933287424000060), for goals and the diabetes split.
- LAI 2016 Part 1 risk-factor list, via secondary snippets.
- NLA framework, for the 0–1 / 2 / ≥3 split.
- The LAI full texts were blocked (LWW 402, lipidjournal 403). Confidence is recorded in D024.

Changes:
- `configs/indian_population.yaml`: `LAI_2020.risk_tiers`.
- `generation/indian_population.py`: `derive_lai_risk()`, attached to the
  LAI interpretation; no RNG.
- `schemas/patient_schema.py`: v0.12; 5 optional LipidInterpretation fields;
  `LAI_RISK_CATEGORIES`.
- `integration/build_patient.py`: passes the fields; provenance clause.
- `validation/clinical_consistency.py`: `lai_risk_tier_consistency`.
- `integration/rederive_review_samples.py`: provenance edit list; compares base
  interpretation keys only.
- New `tests/test_v012_lai_risk.py` (12 tests); version asserts → 0.12.
- New `validation/pilot_50_records/rebuild_v012.py` and `tests/test_pilot_v012.py`
  (skip until run).
- New `docs/AWS_RUN_PLAN-jatin.md`.
- New `review_samples_v012/`.
- `docs/DECISIONS.md` D024–D026; `docs/V010_CHANGE_REPORT.md` Q2/3/8/9 marked;
  PROJECT_STATE.

Results:
- `pytest tests/test_v012_lai_risk.py`: 12 passed.
- `test_pilot_v012.py`: 3 skipped (no output yet).
- 5 samples: all valid, 0 warnings; tiers hand-checked against the rule.
- 5,000 seeds vs the v0.11 generator: 0 non-tier differences. Tiers: low 30.8 /
  moderate 33.9 / high 27.1 / very high 8.2%; diabetics 67.2% very high; LDL above
  personal goal 70.6%.

Not run: the full `pytest tests` (needs PTB-XL + pandas), the pilot rebuild, any
scaling, and AWS (plan only, awaiting go-ahead). Open: v0.10 questions 4–7.

Datasets: `review_samples_v012/` (5 records, seeds 43/53/55/57/137). Nothing else generated.

## Follow-up 5: v0.10 open questions 4–7 researched (-jatin)
User: "Do questions 4–7 first". Web research only (WebSearch/WebFetch; PMC pages
were bot-blocked, so the Europe PMC full-text API was used).
- Q4: INDIAB-17 age table paywalled. Found Mohanty et al. BMC Public Health
  2022 Table 2 (LASI + NFHS-4/SAGE HTN by age × sex). The skew is model-driven
  (P(20) ≈ 8.5%).
- Q5: LASI India Report Table 9.1 has mean BP by age; PDF >10 MB, not fetched.
  Fact-sheet hosts refused connections.
- Q6: no Indian lipid correlation matrix; urban/rural gap not adopted (regional study).
- Q7: Sekher et al. Lancet Glob Health 2025: 45.7% of diagnosed diabetics have
  HbA1c <7% (45+, DBS). No undiagnosed distribution published.
- Check (20,000 generated records): HTN/DM flat with age; HTN 34–37% in every band
  vs LASI 28→60%.
- Output: `docs/OPEN_QUESTIONS_4-7_EVIDENCE-jatin.md`; V010 report Q4–7 annotated;
  PROJECT_STATE. No code change; no tests needed beyond the existing suite.
- Open decisions: (a) age × sex-condition HTN/DM (revisits D006, v0.13);
  (b) approve downloading the LASI India Report PDF for Q5.

## Follow-up 6: age gradient research → D027, schema v0.13 (-jatin)
User: "before applying anything do a thorough research and if found a positive
correlation you've a green light ... to add an age gradient".

Research (Europe PMC full text where PMC was bot-blocked):
- NNMS (Mathur 2022, Table 2): DM 2.2 / 7.8 / 21.8% at 18–29 / 30–49 / 50–69;
  adjusted OR 2.77 and 8.89.
- LASI (Sekher 2025, Table 1): DM 14.7 → 23.4% from 45–49 to 70–74, 21.2% at 75+.
- NFHS-4/5 (Rana 2024, Tables 1–2): DM and HTN rise in every 5-year band.
- LASI and NFHS-4/SAGE HTN by age × sex (Mohanty 2022, Table 2).
- NFHS-5 mean BP by age (PLOS ONE 2025).
- Conclusion: a positive correlation for both conditions in all sources → green
  light applied.

Changes:
- config: `hypertension.age_sex_curve`, `diabetes.age_curve` (sources inline);
  onset_model repointed; old limitations marked superseded.
- generation: `hypertension_prevalence()`, `diabetes_prevalence()`,
  `expected_prevalence_uniform_age()`; samplers take age (and sex); family
  history uses the age-specific DM prevalence; onset uses the same curves;
  dead `_diabetes_prevalence_at` removed.
- validators: `integration/validate_population.py` and
  `integration/audit_field_completeness.py` target the expected marginals;
  `integration/sampler_check.py` updated.
- schema v0.13; build_patient provenance.
- `validation/clinical_consistency.py`: D024 LAI check now warns (not crashes)
  on a panel with missing HDL/LDL (bug found by the stubbed full-suite run).
- tests: new `tests/test_v013_age_gradient.py` (8); `test_m9_family_history`
  draws DM at the age-specific rate; version asserts → 0.13.
- new `integration/regenerate_review_samples.py` (real `build_patient`, optional
  ECG reuse by seed); `review_samples_v013/`; DECISIONS D027; AWS plan → v0.13.

Results:
- `pytest tests/test_v013_age_gradient.py tests/test_v012_lai_risk.py`: 20 passed.
- Full suite with a scratch stub for `ingestion.ptbxl_source` (pytest plugin
  in the scratchpad, not committed), ignoring `test_ingestion_caching.py`:
  197 passed, 5 skipped, 1 failed (`test_existing_fields_unchanged_for_reference_patient`:
  ECG id 11035 vs 11314, caused by the stub's fake ECG; all demographic
  assertions in it passed).
- `integration/sampler_check.py`: HTN 35.92% (expected 35.64), DM 14.94% (15.27).
- 20,000 seeds: bands within ~2 points of sources; FH DM 45+ 13.95% (14.33),
  CVD 45+ 11.90% (11.61); treated HTN 14.2% (14.5), DM 36.1% (36.1); median
  onset (now 60–69) HTN 39.2, DM 42.9; LAI tiers low 34.0 / mod 27.3 / high
  27.0 / very high 11.8%.
- Samples: all 5 valid, 0 warnings; flags unchanged; only onset changed.

Datasets: `review_samples_v013/` (5 records). Nothing else generated; the frozen
100K is still v0.9.

## Commits (-jatin)
`465976d` (log), `7a0121e` (log), `c01d9f1` (D023 code + tests), `6cfa039`
(v0.11 samples), `4fd1112` (D023 docs). The tag/rename commit is recorded in
the final reply.
