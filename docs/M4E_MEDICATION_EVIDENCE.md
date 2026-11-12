# M4E-0 — Medication Evidence Audit

**Status:** COMPLETE. Research-only findings below; no code changed by
this document.

**Method:** reused this project's existing evidence base first
(`docs/M4_CLINICAL_EVIDENCE.md` §4, already covering NLEM 2022 and
NNMS treatment rates) and dispatched two parallel research passes to
verify those figures against primary/near-primary sources and fill the
specific gaps this milestone asks about (statins, antiplatelets,
adherence, discontinuation, duration). No hospital/clinic dataset was
adopted — every hospital/registry-derived figure found (UNICORN study,
multicentric diabetes-discontinuation study) is explicitly excluded
below, per this project's standing rule against non-representative
clinical cohorts (the same rule already applied to CREATE/STEMI-ACT/NHFR).

## Evidence table

| Parameter | Current status | Source | Population | Year | Evidence strength | What it actually supports | What it does NOT support | Potential generator use | Limitations |
|---|---|---|---|---|---|---|---|---|---|
| Antihypertensive treatment rate | **SUPPORTED** | ICMR-NNMS 2017-18 hypertension care cascade ([PMC10156594](https://pmc.ncbi.nlm.nih.gov/articles/PMC10156594/)) | National, 300 rural/300 urban clusters, n=3,017 hypertensive of 10,593 measured, ages 18-69 | 2017-18 fieldwork | **SUPPORTED** (national, population-representative survey) | The fraction of diagnosed hypertensives currently on treatment: **14.5%** (95% CI 12.7-16.5) | Which specific drug/class a treated patient receives; treatment duration; adherence | Bernoulli(0.145), gated on `diagnoses` containing `code="hypertension"` | Point-prevalence of "currently treated" at survey time, not a longitudinal/duration figure. A sex-stratified split exists (M10.9%/F18.8%) — **not adopted**, see below. |
| Antidiabetic treatment rate | **SUPPORTED** | ICMR-NNMS 2017-18 diabetes care cascade ([PMC8964146](https://pmc.ncbi.nlm.nih.gov/articles/PMC8964146/)) | National, same survey design, n=904 diabetic of 9,721 surveyed | 2017-18 fieldwork | **SUPPORTED** | The fraction of diagnosed diabetics currently on treatment: **36.1%** | Which specific drug/class; duration; adherence | Bernoulli(0.361), gated on `diagnoses` containing `code="diabetes"` | Same point-prevalence caveat as above. A sex split of the *treatment-given-aware* sub-rate exists (M82.6%/F74.5%) — **not adopted**, different quantity (conditional on awareness, not on diagnosis) and would need its own conditioning chain this project doesn't have (no `aware` variable exists). |
| Antihypertensive drug class/name | **PARTIALLY SUPPORTED, secondary-source only** | NLEM 2022 (23rd list), via secondary coverage (medicaldialogues.in, businesstoday.in, a hospital drug-utilization study) — primary MoHFW/CDSCO PDF inaccessible across 3 independent mirror attempts (2 research passes) | National essential-medicines list | 2022 | **PARTIALLY SUPPORTED** — availability confirmed via secondary sources, not primary-verified | That amlodipine (CCB), enalapril, and ramipril (ACE-i) are essential medicines in India; that atenolol and methyldopa were *removed* in the 2022 revision | **Which fraction of treated hypertensives receive which class** — no class-share distribution exists anywhere researched | None this milestone — see M4E-1 | NLEM = availability/essential-medicine status, not prescribing prevalence (this milestone's own explicit warning) |
| Antidiabetic drug class/name | **PARTIALLY SUPPORTED, secondary-source only** | Same NLEM 2022 secondary sources; prior project finding (metformin, teneligliptin, insulin glargine) | National | 2022 | **PARTIALLY SUPPORTED** | That these drugs are essential medicines | Class-share distribution among treated diabetics | None this milestone | Same NLEM-≠-prevalence caveat |
| Statin / lipid-lowering treatment rate | **NOT SUPPORTED at population level** | Only found: UNICORN study, 99.19% statin prescription rate — **hospital/clinic cohort of already-treated dyslipidemia patients**, not a population survey | Non-representative clinical cohort | — | **NOT SUPPORTED** | Nothing usable for population generation | Population-level statin treatment rate | None | Explicitly excluded — same non-representativeness class this project already excludes for CREATE/STEMI-ACT/NHFR. Doubly blocked regardless: hyperlipidemia's own diagnosis is deferred (D015), so there is no diagnosis to gate a statin against even if a rate existed. |
| Antiplatelet therapy (aspirin/clopidogrel) | **NOT SUPPORTED** | No Indian population-level prevalence/treatment-rate figure found; all retrieved sources were international trial/guideline discussions | — | — | **NOT SUPPORTED** | Nothing | Population-level antiplatelet prevalence/indication | None | Also architecturally blocked: antiplatelet indication is typically a prior CVD event or primary-prevention-in-high-risk-patient decision — this project generates neither CVD events nor a primary-prevention risk score (both deferred, M4-0/M4D) |
| Antihypertensive/antidiabetic adherence | **NOT SUPPORTED — conflicting, non-reconcilable** | NFHS-4 secondary analysis ([PMC9731078](https://pmc.ncbi.nlm.nih.gov/articles/PMC9731078/)): 26.78% antihypertensive adherence. A systematic review/meta-analysis of heterogeneous small studies: pooled 15.8% | NFHS-4: ages 15-49 only (narrower than this project's 20-89 scope); meta-analysis: heterogeneous small non-national studies | 2015-16 / pooled | **NOT SUPPORTED** | Nothing directly usable | Nothing | None | Two real but materially conflicting, non-identical-population figures — per this project's "don't blend non-identical studies" rule, neither is used. Documented as a genuine conflict, not silently resolved; does not affect generation since adherence is not generated regardless of which figure might be "right." |
| Statin-specific adherence/discontinuation | **NOT SUPPORTED** | None found | — | — | **NOT SUPPORTED** | — | — | — |
| Diabetes treatment discontinuation | **NOT SUPPORTED for population generation** | A multicentric study across 11 diabetes-care centers in Northern India | Clinic-based, regional (Northern India only) | — | **NOT SUPPORTED** (non-representative, regional) | — | Population-level discontinuation rate | None | Same clinic-cohort exclusion rule |
| Treatment duration (any class) | **NOT SUPPORTED** | None found | — | — | **NOT SUPPORTED** | — | — | — | — |

## Answering this milestone's 9 questions per parameter

For **antihypertensive/antidiabetic treatment rate** (the two SUPPORTED
rows): (1) yes, Indian population-level evidence exists; (2) national
survey respondents, ages 18-69 (NNMS); (3) 2017-18 fieldwork; (4)
national; (5) hypertension/diabetes specifically; (6) national,
NOT age-stratified in the cited figure, sex-stratified data exists but
is deliberately not used (see below); (7) reports **treatment rate**
(the "currently on treatment" fraction) — not medication class,
specific drug, adherence, discontinuation, or duration; (8) yes, this
project's general-population target (D008) matches NNMS's own general
adult sampling frame reasonably well (same source class already used
for `hypertension`/`diabetes` risk-factor prevalence itself); (9) the
only real assumption required is treating "currently on treatment" as
equivalent to `current_status="active"` for a generated `Medication`
record — a direct, non-inventive mapping of what the survey actually
measured.

For every other row: NOT SUPPORTED or PARTIALLY SUPPORTED at the
availability (not prevalence) level — answered inline in the table.

## The sex-stratified hypertension-treatment finding

This research pass found that ICMR-NNMS's hypertension care cascade
**is** sex-stratified (treatment: M10.9%/F18.8%) — more granular than
this project's existing note in `docs/M4_CLINICAL_EVIDENCE.md` §4, which
said the overall awareness/treatment/control figures were "explicitly
not sex-varying." That earlier note was imprecise (the *headline*
national figures are sex-pooled; a sex breakdown exists in the same
paper and simply wasn't extracted previously) — corrected here for the
record. **Not adopted for generation**: `risk_factors.hypertension`
itself is generated as an unconditioned, sex-independent national
marginal, a settled M2D-audited decision ("confirmed correct... not an
oversight"). Conditioning only the *downstream treatment rate* on sex,
while the *diagnosis* it depends on remains sex-unconditioned, would
introduce an inconsistent asymmetry not present anywhere else in this
project's architecture. The national marginal (14.5%) is used instead.
This is a documented engineering choice, not evidence being discarded
silently.

## Conclusion

Only **antihypertensive** and **antidiabetic** treatment can be
defensibly generated this milestone, and only at the **existence/class
level** (treated: yes/no, with a coarse therapeutic-category label) —
not at the specific-drug-name level. Statins and antiplatelets are not
generated at all. No specific drug name is ever generated for any
class — NLEM confirms *availability*, never *prescribing share*, and
this milestone explicitly warns against conflating the two.
