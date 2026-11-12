# M4C — Hyperlipidemia Semantic Audit + Option B Resolution

**Status:** COMPLETE. Resolves the human checkpoint raised in
`docs/M4C_CONSISTENCY_AUDIT.md` ("Finding:
`risk_factors.hyperlipidemia` vs. `lipid_interpretations` disagree
substantially").

## 1. Original M4C finding

Measured on the existing 100-patient M4B output:
`risk_factors.hyperlipidemia` (M2C, unconditioned `Bernoulli(0.812)`)
agrees with the NCEP-based `lipid_interpretations` entry only 73/100
times, and with the LAI-based entry only 77/100 times. Classified in
`docs/M4C_CONSISTENCY_AUDIT.md` as **E — architecture issue**, not
fixed, recorded as a human checkpoint.

**Human decision (this milestone):** OPTION B — keep both as distinct
variables. This document performs the required semantic audit before
implementing that decision, per this milestone's own instruction not
to assume compatibility from general medical knowledge.

## 2. Semantic audit

Traced `risk_factors.hyperlipidemia` through every layer, oldest to
newest, without assuming its meaning:

**A. Evidence source.** ICMR-INDIAB-17 (Anjana et al., *Lancet Diabetes
& Endocrinology*, 2023), headline dyslipidaemia figure, cited via
`docs/INDIAN_DATA_SOURCES.md` (M2A). `configs/indian_population.yaml`
lines 448-468.

**B. Population represented.** A ~25,647-person sub-cohort of
ICMR-INDIAB-17's ~113,043-person national sample (dyslipidaemia was not
measured on the full cohort) — a **national marginal**, not
individual-level, not age/sex-stratified.

**C. Definition/cutoff used by that evidence.** "Dyslipidaemia
(composite)" — the config explicitly flags that the exact
component-level cutoffs were **not independently re-verified** for this
specific sub-cohort figure (`configs/indian_population.yaml` line 455).
This is evidence_tier **PARTIALLY SUPPORTED**, the weakest tier of any
of the five original M2C risk factors (`docs/session_logs/
2026-09-25_M2C-indian-conditioning.md` line 32).

**D. Intended representation.** Every M2A/M2B/M2C document
(`docs/INDIAN_GENERATION_STRATEGY.md` §4/§6/§14,
`docs/session_logs/2026-09-25_M2C-indian-conditioning.md`) lists
`hyperlipidemia` in the same breath, same table row, same generation
step, and same statistical-validation table as `hypertension` and
`diabetes` — all three explicitly called **"risk factors"**
(`docs/INDIAN_GENERATION_STRATEGY.md` line 44: "five risk factors
(BMI, smoking status, hypertension, diabetes, dyslipidemia)"). Nothing
in M2A/M2B/M2C ever frames it as a claim about an individual
measurement — `lipid_panel`/`lipid_interpretations` did not exist until
two milestones later (M4A/M4B). It was designed and built as a
**population-prevalence risk-factor attribute**, structurally identical
in role to `hypertension`/`diabetes`.

**E. How it is actually generated.**
`generation/indian_population.py:106-107`:
```python
def sample_hyperlipidemia(rng, config) -> bool:
    return _sample_bernoulli(rng, config, "hyperlipidemia")
```
Identical in form to `sample_hypertension`/`sample_diabetes` — an
unconditioned `Bernoulli(p)` draw from the config's single national
marginal `p=0.812`.

**F. Statistically conditioned on anything?** No. Confirmed
unconditioned in the config comment
(`configs/indian_population.yaml` line 294: "Hypertension, diabetes,
hyperlipidemia are unconditioned national marginals") and in
`generate_indian_attributes()`'s own dependency-order docstring
(`generation/indian_population.py` line 202: "hypertension/diabetes/
hyperlipidemia/lipid panel components are unconditioned marginals").

**G. Ever derived from LDL/HDL/TG/TC?** No — confirmed by reading
`sample_hyperlipidemia()` itself (E, above) and by the empirical 73-77%
disagreement measured in M4C-0 (if it were derived, agreement would be
100%).

**H. Did D011/D012 establish raw lipid values as primary?** Yes, for
**lipid_panel → lipid_interpretations** specifically. D011 also
contains a stronger, more general clause: "LDL and hyperlipidemia must
never be independently generated as unrelated random variables" —
**this is the one real tension found by this audit** (§3, below).

**I. Does existing documentation already distinguish "risk factor" from
"measurement-derived interpretation"?** Yes, and more clearly than
D011's own broad clause suggests. `docs/M4_CLINICAL_ARCHITECTURE.md`'s
own dependency table (line 56-57) already classifies
`risk_factors.hyperlipidemia` ↔ `lipid_interpretations` as **its own
separate row** ("NONE — independently generated", "E — architecture
issue") distinct from the `lipid_panel` ↔ `lipid_interpretations` row
("Computed, not sampled", "B — hard rule"). Even more tellingly, the
same document's future-`diagnoses` design (line 49, line 195) already
plans to derive a future `diagnoses.hyperlipidemia` entry from the
**lipid raw-value chain** ("two-hop chain: raw LDL → interpretation
label → diagnosis entry"), not from `risk_factors.hyperlipidemia` — the
project's own forward design already implicitly treats these as two
variables serving two different downstream purposes, in exactly the
shape Option B now makes explicit.

**J. Would keeping both variables violate any existing decision?**
Partially — see §3.

## 3. Semantic conclusion

**PARTIALLY CONFIRMED.**

The **historical M2C semantics** of `risk_factors.hyperlipidemia`
(population-prevalence risk-factor attribute, ICMR-INDIAB-sourced,
unconditioned marginal, structurally identical in role to
`hypertension`/`diabetes`) are **fully compatible** with Option B — no
part of the original M2C design ever claimed or required this field to
be a per-patient derivation from lipid measurements, because lipid
measurements didn't exist yet when it was built.

The tension is narrower and more recent: **D011's own text** contains
one general clause — "LDL and hyperlipidemia must never be
independently generated as unrelated random variables" — that, read
literally and out of context, conflicts with Option B. Tracing this
clause to its origin (`docs/M4_CLINICAL_ARCHITECTURE.md` §2, written
during M3.5/M4-0B, *before* M4B's implementation), it appears
immediately after a discussion specifically about **LDL's own raw
value and its own derived interpretation** ("generate the raw value
first; derive interpretations afterward... the single most important
consequence of Decision 2 [is making] the 'LDL=85, hyperlipidemia=true
under a definition where 85 doesn't qualify' contradiction structurally
impossible"). In context, "hyperlipidemia" in that sentence was being
used loosely as shorthand for "the derived dyslipidemia
interpretation," at a time before `lipid_interpretations` existed as a
named field and before anyone had noticed that `risk_factors.
hyperlipidemia` (an M2C field with its own, older, separate meaning)
would still exist alongside it. **This was never actually implemented
the strict way the sentence reads**: M4B (D013) implemented
`lipid_interpretations` as computed-from-raw-values exactly as
required, but left `sample_hyperlipidemia()` untouched — a fully
independent Bernoulli, exactly as M2C built it. D013 does not mention
reconciling it. No commit or decision ever redefined `risk_factors.
hyperlipidemia`'s meaning or generation logic. The 73-77% disagreement
was not a bug introduced by an implementation shortcut; it is what the
field was always going to produce once a second, independent
lipid-measurement pathway was added next to it.

**Conclusion: Option B is compatible with everything actually built and
with the field's original, documented intent. Only D011's own wording
is imprecise** and needs a scoping clarification (§4) so a future
developer cannot misread it as requiring exactly the reconciliation
Option B declines to do.

## 4. The contract

**`risk_factors.hyperlipidemia`** — population/background risk-factor
attribute. An unconditioned `Bernoulli(0.812)` draw from
ICMR-INDIAB-17's national dyslipidaemia marginal (evidence_tier
PARTIALLY SUPPORTED). Same role, same generation pattern, same
evidentiary status class as `risk_factors.hypertension`/`diabetes`. It
is a statement about the synthetic population's calibrated background
prevalence, not a claim about any individual patient's own lipid
measurement.

**`lipid_panel`** — synthetic measured lipid values (TC, TG, HDL
sampled; LDL derived via Friedewald). A statement about this specific
patient's individual measurement.

**`lipid_interpretations`** — deterministic classifications computed
from this patient's own `lipid_panel`, per explicitly named definitions
(NCEP_ATP_III, LAI_2020). Always internally consistent with
`lipid_panel` by construction (D011/D012/D013), because it is a pure
function of it.

**`risk_factors.hyperlipidemia` MUST NOT be described, documented, or
implemented as a deterministic copy, summary, or precursor of
`lipid_interpretations`.** `lipid_interpretations` MUST NOT be adjusted
to force agreement with `risk_factors.hyperlipidemia`. Disagreement
between the two is expected, not an error.

| Relationship | Status |
|---|---|
| `lipid_panel` ↔ `lipid_interpretations` | **HARD CONSISTENCY** — pure function, must always match, validated as an error if it doesn't (unchanged) |
| `risk_factors.hyperlipidemia` ↔ `lipid_interpretations` | **EXPECTED SEMANTIC DIFFERENCE** — two independently-evidenced variables about different things (population marginal vs. individual measurement-derived label); disagreement carries no validation meaning |

## 5. D011 scoping clarification

D011's clause "LDL and hyperlipidemia must never be independently
generated as unrelated random variables" is clarified (not reversed) to
apply only to **the raw LDL value and its own derived
`lipid_interpretations` entry** — the pair D011's Decision 2 was
actually about, and the pair D012/D013 actually implemented as a pure
function. It does not apply to, and was never implemented as applying
to, the separate M2C-era `risk_factors.hyperlipidemia` field. Recorded
formally as `docs/DECISIONS.md` D014 (append-only per this project's
decision-log convention — D011's own text is not edited).

## 6. Implementation changes

1. `docs/DECISIONS.md` — new **D014** records the human decision, this
   audit's conclusion, and the D011 scoping clarification.
2. `docs/PROJECT_STATE.md` — the "Human Decisions Required" entry for
   this question is marked resolved; "Next Action" updated.
3. `validation/clinical_consistency.py` — the existing
   `hyperlipidemia_vs_lipid_interpretations_intentionally_not_compared`
   check (already never treated disagreement as an error, per the
   original M4C design) now has its docstring/comment updated to cite
   D014 as the authoritative contract, so a future developer sees the
   *why*, not just the *what*.
4. `tests/test_m4c_clinical_consistency.py` — three new/extended cases
   confirming both agreement and both directions of disagreement are
   valid: (A) hyperlipidemia=true, both interpretations=true; (B)
   hyperlipidemia=false, an interpretation=true; (C) hyperlipidemia=true,
   both interpretations=false (already covered by the existing
   non-reconciliation test, re-verified here explicitly against the new
   contract language).

**No generation, distribution, schema, or lipid-derivation code
changes.** `sample_hyperlipidemia()`, `sample_lipid_panel()`,
`derive_lipid_interpretations()` are byte-for-byte unchanged.

## 7. Tests and validation results

See the session log for full figures: full suite 58/58 passing
(55 existing + 3 new), 10-patient and 100-patient real-pipeline
validation both PASS with 0 errors, 0 warnings, lipid panel ↔
interpretation consistency still enforced as a hard rule, and the
hyperlipidemia/interpretation disagreement confirmed to never appear in
`errors` for either patients where it agrees or disagrees.

## 8. Remaining limitations

- `risk_factors.hyperlipidemia`'s own evidence tier (PARTIALLY
  SUPPORTED, reduced-coverage sub-cohort) is unchanged by this
  resolution — it was never in question here, only the field's
  relationship to `lipid_interpretations`.
- The future `diagnoses.hyperlipidemia` design
  (`docs/M4_CLINICAL_ARCHITECTURE.md`) should source from the lipid
  raw-value chain (`lipid_interpretations`), not from `risk_factors.
  hyperlipidemia` — already the documented design, reaffirmed rather
  than changed here. This is a note for the future M4D milestone, not
  an action taken now.
- No new human checkpoint remains from this specific question.
