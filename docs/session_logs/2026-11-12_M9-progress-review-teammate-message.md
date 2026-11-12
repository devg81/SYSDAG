# 2026-11-12 — M9: progress review + teammate status message reconciliation (Q&A)

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

## Commit
First push: `465976d`; second: `7a0121e`. Third recorded in the final reply.
