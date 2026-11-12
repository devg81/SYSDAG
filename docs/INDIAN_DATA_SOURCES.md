# Indian Population Data Sources — Research Report (M2A)

**Milestone:** M2A — Indian Population Data Research (research/documentation-only).
**Status:** Research checkpoint. No code, schema, or configuration was modified.
**Date:** 2026-09-25

This document inventories real Indian population/health datasets that could
eventually inform the demographic and cardiovascular-risk-factor generation
layer described in `docs/Claude.md` (Stage 10 — Indian Demographic
Conditioning) and the spec's Indian-demographic direction
(`docs/superpowers/specs/2026-09-19-multimodal-cardio-dataset-spec-design.md`
§4). It does **not** select a final dataset, does **not** change the schema,
and does **not** integrate anything into the pipeline. See
["What This Milestone Does Not Decide"](#what-this-milestone-does-not-decide).

---

## 1. Executive Summary

Eight Indian datasets were researched: the three mandated (ICMR-INDIAB,
ICMR-NNMS, IHDS) plus five additional candidates identified as genuinely
relevant (NFHS-5, LASI, NSS 75th Round health survey, the India State-Level
Disease Burden Initiative/GBD, and ICMR's ACS registries CREATE/STEMI-ACT).

The consistent pattern across every dataset that collects clinical/health
data: **individual-level (row-level) microdata is either restricted,
query-mediated, or request-gated — never freely downloadable** for the
health-focused sources (ICMR-INDIAB, NNMS, NFHS-5, LASI). The one exception
is the NSS 75th Round health-consumption survey, whose unit-level data is
published directly on `microdata.gov.in` with no visible application gate.
IHDS's household microdata (waves 1–2) is also freely downloadable via
ICPSR, but IHDS carries very little clinical cardiovascular data and ICPSR's
terms explicitly restrict feeding its data to LLMs — a finding directly
relevant to this project's downstream generative-model plans.

No dataset examined provides individual-level cardiovascular risk-factor
data that is both (a) freely accessible today and (b) confirmed permissive
of synthetic-data derivation. **Aggregate/published statistics are freely
available for every dataset** and are sufficient for distribution
calibration (matching age/sex/state-level prevalence), but not for
joint-distribution modeling, which would require the gated microdata.

None of the researched datasets' licensing terms were found to explicitly
address "synthetic data generation" one way or the other for the
health-survey sources — this is marked `Not verified` throughout rather than
assumed permitted, per this milestone's verification rules.

---

## 2. Project Context

From `docs/Claude.md` and `docs/superpowers/specs/2026-09-19-...-spec-design.md`:

- The project's long-term pipeline (top-level `CLAUDE.md` §4, `docs/Claude.md`
  Stage 8–10) is: validate a large synthetic cardiovascular population →
  discover patterns → **incorporate Indian demographic characteristics** →
  use a selected existing generative model → produce new synthetic patient
  fields/records.
- `docs/Claude.md` §4 is explicit: *"The project should NOT make unsupported
  claims that the synthetic dataset represents the Indian population... Do
  not invent population-level relationships simply because they appear
  medically plausible."* This research exists to find what evidence
  actually supports that layer, rather than assuming it.
- Current implementation state (M1, complete — see
  `docs/session_logs/2026-09-25_M1-foundation.md`): Schema v0.2 implemented
  as Python dataclasses in `schemas/patient_schema.py`. One synthetic patient
  (`PAT_000001`) generated with demographics + ECG metadata reused from a
  real PTB-XL record. `risk_factors`, `family_history`, `medical_history`,
  `diagnoses`, `medications`, `labs`, `encounters`, and `echo` are all
  currently `None`/unset — this is exactly the layer Indian population data
  would eventually inform, once a real generation strategy (Stage 3) exists.
- Stage 10 (`docs/Claude.md`): *"The exact conditioning mechanism is not yet
  finalized... Do not assume that a variable should be used merely because
  it is available."* This report follows that instruction — it documents
  what's available and its constraints, not a conditioning design.

---

## 3. ICMR-INDIAB Analysis

**Official name:** ICMR–INDIAB (Indian Council of Medical Research – INDIA
Diabetes) study.
**Producing organization:** ICMR, with the Madras Diabetes Research
Foundation (MDRF) as the lead research partner.
**Purpose:** Nationally-scaled, population-based surveillance of diabetes,
prediabetes, and metabolic NCD burden across India.

Sources: [Lancet Diabetes & Endocrinology overview](https://thelancet.com/journals/landia/article/PIIS2213-8587(17)30190-0/fulltext) · [MDRF Eprints](http://mdrf-eprints.in/1420/) · [PubMed 37301218](https://pubmed.ncbi.nlm.nih.gov/37301218/) · [NHRDR dataset page](https://nhrdr.icmr.org.in/datasets/icmr-indiab)

### Population, geography, sampling
- Sample size: **113,043 individuals** (79,506 rural, 33,537 urban), surveyed
  Oct 2008 – Dec 2020 across 5 phases.
- Geographic coverage: all 28 states, 2 UTs, and NCT Delhi.
- Age range: adults 20+.
- Sampling: stratified multistage design, three-level stratification by
  geography, population size, and state-level socioeconomic status, across
  four cardinal regions.
- Described in the source itself as *"the largest nationally representative
  population-based study on diabetes and metabolic NCDs undertaken in
  India"* — source-stated, not inferred.

### Variables
| Category | Detail |
|---|---|
| Demographic | age, sex, education, urban/rural, state/region |
| Diabetes | diabetes 11.4% [10.2–12.5], prediabetes 15.3% (weighted, ICMR-INDIAB-17) |
| Hypertension | 35.5% weighted prevalence |
| Obesity/BMI | generalised obesity 28.6%, abdominal obesity 39.5% |
| Lipids | dyslipidaemia 81.2%, but on a smaller sub-cohort (n≈25,647 vs. n≈107–111k for other variables) — **not measured at the same scale as diabetes/HTN/obesity** |
| Smoking/tobacco | never/current/past |
| Alcohol, physical activity | covariates; a dedicated diet sub-study exists (ICMR-INDIAB survey-21, *Nature Medicine* 2025) |
| Family history | Type 2 diabetes family history (yes/no) captured. Family history of *cardiovascular disease* specifically: `Not verified` |
| CV event/diagnosis variables (MI, stroke) | `Not verified` |

### Individual-level vs. aggregate
- **Individual-level: RESTRICTED.** Collected at individual level (one
  person per household, door-to-door), but the NHRDR platform states
  explicitly: *"Raw dataset will not be shared, only the query outcome will
  be shared."*
- **Aggregate: YES**, freely available in peer-reviewed papers with 95% CIs.
- A small "sample dataset" is available to logged-in NHRDR users; its exact
  contents/size: `Not verified`.

### Access
Hosted on ICMR's National Health Research Data Repository (NHRDR):
https://nhrdr.icmr.org.in/datasets/icmr-indiab. Six-step workflow: register
→ browse sample datasets/metadata → identify variables → build a query →
submit research question + analysis code → receive summarized output after
approval. Registration required. Application requirements beyond
registration (ethics approval, institutional proof): `Not verified`.
Contact: datacentre.hq[at]icmr[dot]gov[dot]in.

### Usage (licensing — kept separate from access, per instructions)
- Research use: implied by the platform's framing, but no explicit license
  text found — `Not verified` as a formal permission.
- Commercial use: `Not verified`.
- Redistribution: `Not verified`, but structurally constrained — raw data is
  never released even to approved researchers, so "redistributing the
  dataset" doesn't apply; whether a researcher's own query-output aggregates
  may be redistributed is also `Not verified`.
- Derived/synthetic-data generation: `Not verified` — no source addressed
  this question either way.
- Directional (not INDIAB-specific) context: a *different* ICMR institute
  (NCDIR) states in its own policy that "no primary data shall be available
  to a third party unless three years have elapsed from the date of
  publication" — cited only as directional context, not confirmed to apply
  to INDIAB. [NCDIR policy PDF](https://ncdirindia.org/Downloads/NCDIR_Policy.pdf)
- Citation: no NHRDR-stated mandatory format found; standard academic
  practice would cite the relevant phase paper (e.g., Anjana et al., *Lancet
  Diabetes Endocrinol* 2023;11:474–89).

### Freshness
Collection Nov 2008 – Dec 2020 (5 phases). Most recent major publication:
ICMR-INDIAB-17, July 2023. A diet sub-study (ICMR-INDIAB survey-21) was
published in *Nature Medicine* in 2025, indicating active ongoing analysis.
Whether new field-collection waves are planned post-2020: `Not verified`.

### Access status summary
Direct raw download: **NO**. Restricted query-mediated access to
individual-level data (summarized output only): **YES**, via NHRDR
registration + approval. Aggregate/published statistics: **YES**.

---

## 4. ICMR-NNMS (National NCD Monitoring Survey) Analysis

**Official name:** National Noncommunicable Disease Monitoring Survey
(NNMS) 2017–18.
**Producing organization:** ICMR, with ICMR-NCDIR (Bengaluru) as nodal
agency, ~10–11 implementing institutions.
**Purpose:** National estimates of NCD risk-factor indicators and
health-system preparedness, aligned to India's National NCD Monitoring
Framework (WHO-aligned, 10 targets/21 indicators). Two components:
population survey (adults 18–69, adolescents 15–17) + facility survey of
NCD-service preparedness.

Sources: [Factsheet PDF](https://www.ncdirindia.org/nnms/resources/factsheet.pdf) · [PLOS One 2021](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0246712) · [NHRDR dataset page](https://nhrdr.icmr.org.in/datasets/national-ncd-monitoring-survey-nnms-household-and-adult) · [NCDIR](https://ncdirindia.org/NCD.aspx) · [BMC Health Services Research](https://link.springer.com/article/10.1186/s12913-021-06530-0) · [BMC Public Health regional estimates](https://bmcpublichealth.biomedcentral.com/articles/10.1186/s12889-022-13466-5)

### Population, geography, sampling
- Target: 12,000 households / 600 PSUs (300 urban + 300 rural, PPS-selected
  from the 2011 Census frame). Achieved: **10,659 adults (18–69)**
  completed; ~3,000-person subsample for urine salt-intake estimation.
- Geographic: national; one source specifies 27 states with 10 implementing
  agencies — full 36-state/UT coverage `Not verified`.
- Sampling: stratified multistage cluster sampling, WHO-KISH grid for
  one-adult-per-household selection; instruments adapted from WHO STEPwise
  approach, IDSP-NCD survey, WHO Global Adult Tobacco Survey.
- Source-stated as nationally representative and *"first comprehensive fully
  digitalized national level survey."*

### Variables
| Category | Detail |
|---|---|
| Demographic | gender, age, education, occupation, marital status, SES, housing, cooking-fuel use |
| Tobacco | smoked + smokeless use, second-hand exposure |
| Alcohol | consumption pattern, frequency, quantity, heavy episodic drinking |
| Physical activity | GPAQ (workplace/home/travel/leisure) |
| Diet | fruit/vegetable servings; salt intake KAP + urine-sodium subsample |
| BMI/obesity | overweight 26.1% [24.2–28.1], obesity 6.2% [5.5–7.0] |
| Blood pressure | raised BP 28.5% [27.0–30.1] |
| Glucose/diabetes | raised fasting glucose 9.3% [8.3–10.5], capillary testing at camps |
| Lipids | `Not verified` — no source confirmed or denied lipid-profile measurement in the core adult protocol |

### Individual-level vs. aggregate
- **Individual-level: RESTRICTED.** ICMR's NHRDR portal states: *"The raw
  dataset will not be shared, only the query outcome will be shared."*
- **Aggregate: YES** — factsheet, chapter PDFs, and multiple peer-reviewed
  papers (national + regional prevalence with CIs).
- The PLOS One paper's own data-availability statement confirms no
  microdata download accompanies it either.

### Access
Aggregate reports/factsheets: direct download from
`ncdirindia.org/nnms/resources/`, no registration observed. Query-level
access to underlying data: login required at NHRDR; approval criteria/
turnaround beyond "log in": `Not verified`.

### Usage
- Research use: `Not verified` (implied by academic framing, not stated).
- Commercial use: `Not verified` — not addressed anywhere examined.
- Redistribution: `Not verified` — "raw dataset will not be shared" implies
  microdata redistribution isn't applicable since raw data itself isn't
  released.
- Derived/synthetic-data generation: `Not verified`.
- Citation: `Not verified` — no NNMS-specific citation policy located.

### Freshness
Collection Sept 2017 – July 2018. Main publication March 2021. A 2025
publication extends NNMS-style methodology to adolescents nationally,
suggesting the program is still active — but this is a methods/adolescent
paper, **not confirmation of a full second adult wave**. Whether an NNMS-2
(post-2018 adult wave) exists: `Not verified`.

### Limitations
Nationally representative per source. One respondent per household (KISH
grid) — no within-household clustering data. BP/diabetes are single-visit
field measurements (capillary glucose, camp BP), not clinical/lab diagnoses
— relevant when comparing against ICMR-INDIAB's clinically-oriented protocol.

---

## 5. IHDS (India Human Development Survey) Analysis

**Official name:** India Human Development Survey. **Producing
organizations:** NCAER (New Delhi) + University of Maryland (Sonalde Desai,
Reeve Vanneman), with University of Michigan and Indiana University
Bloomington on IHDS-3; funded by US NIH. India's only national household
panel dataset.

Sources: [NCAER project page](https://ncaer.org/project/india-human-development-survey-ihds/) · [ihds.umd.edu/data](https://ihds.umd.edu/data) · [Wikipedia](https://en.wikipedia.org/wiki/India_Human_Development_Survey) · [ICPSR 22626](https://www.icpsr.umich.edu/web/DSDR/studies/22626) · [ICPSR 36151](https://www.icpsr.umich.edu/web/DSDR/studies/36151)

### Waves
| Wave | Years | Households | Public microdata |
|---|---|---|---|
| IHDS-1 | 2004–05 | 41,554 (1,503 villages, 971 urban neighborhoods) | Yes — ICPSR 22626 |
| IHDS-2 | 2011–12 | 42,152 (re-interviews of Wave 1) | Yes — ICPSR 36151 |
| IHDS-3 | Conflicting sources: Wikipedia says 2022–23; ihds.umd.edu (possibly stale) says "in preparation"; a Feb-2026 NCAER page exists | — | **Not verified — public availability unresolved, flagged explicitly** |

### Coverage
Nationally representative, rural + urban, all major states.

### Variables
| Category | Detail |
|---|---|
| Demographic | age, sex, education, household roster, state/geography |
| Socioeconomic | income (farm/wage/nonfarm), consumption, consumer goods, debts, housing quality, social networks |
| Health-related | short-term morbidity, major morbidity, ADLs, quality of medical care, **tobacco and alcohol**, **anthropometry** (height/weight → BMI derivable), health beliefs, AIDS knowledge, fertility/reproductive health |
| Clinical biomarkers (BP, HbA1c, etc.) | No evidence found of a clinical biomarker module — `Not verified`, needs direct codebook confirmation before assuming absence or presence |

**Relevance assessment (explicitly, per instructions not to assume every
IHDS variable is useful):** demographic/socioeconomic/behavioral
(tobacco/alcohol) data is directly relevant to context conditioning;
anthropometry is relevant to a future BMI-adjacent field. Self-reported
morbidity *may* capture self-reported hypertension/diabetes/heart disease,
but this is `Not verified` from what was retrieved — do not assume IHDS
provides clinical-grade cardiovascular data; its strength is socioeconomic
and household context, not CV risk factors.

### Individual-level vs. aggregate
- **Individual/household-level microdata: YES**, publicly downloadable for
  Waves 1–2 via ICPSR — free registration (email/password), no ICPSR
  membership required. Formats: SAS/SPSS/STATA/R/ASCII+setup files.
- **Aggregate: YES**, also via NCAER publications.
- Note on confidence: direct fetches of `icpsr.umich.edu` pages returned
  HTTP 403 (bot-blocked) throughout this research pass; the facts above come
  from search-engine-cached snippets of those pages, not a direct read.
  Recommend a human re-verify by logging into ICPSR directly before relying
  on this for planning.

### Access
ICPSR study pages 22626 (Wave 1) and 36151 (Wave 2). Free registration, no
membership fee.

### Usage — important finding
General ICPSR Terms of Use (the study-specific terms page 403'd, so this is
the *general* ICPSR policy — **not confirmed identical for this specific
study**):
- Research/statistical use only — explicitly **not** for investigating
  specific individuals.
- **Redistribution barred** without a written ICPSR agreement.
- **Explicit bar on feeding ICPSR data to any LLM that retains data or
  trains on it** (ChatGPT, Copilot, Gemini named as examples), characterized
  by ICPSR as a form of "redistribution."
- Commercial use: not explicitly addressed in what was retrieved —
  `Not verified`, though the research-only framing implies restriction.
- Violations: access revocation, data-return demand, future access denial.
- Citation: required, formal citation strings exist (below).

> **This is the single most project-relevant licensing finding in this
> report.** If any future pipeline stage involves an LLM touching
> IHDS-derived data (training, few-shot conditioning, or even ad hoc
> analysis by an LLM agent), that would need separate clarification from
> ICPSR/NCAER first — it is not something to assume is fine by default.

### Citation
```
Desai, Sonalde, Vanneman, Reeve, and NCAER. India Human Development Survey
(IHDS), 2005. ICPSR [distributor], 2018-08-08. https://doi.org/10.3886/ICPSR22626.v12

Desai, Sonalde, Reeve Vanneman and NCAER. India Human Development Survey-II
(IHDS-II), 2011-12. ICPSR [distributor], 2018-08-08.

Desai et al. 2010. Human Development in India: Challenges for a Society in
Transition. Oxford University Press.
```

### Freshness
Most recent **publicly available** wave is 2011–12 — 13+ years old as of
2026. IHDS-3 release status is unresolved (see waves table). Do not assume
2011–12 distributions are current without re-checking IHDS-3's status closer
to implementation.

### Derived/synthetic data generation
`Not verified`. No source addressed whether ICPSR/IHDS terms permit
generating synthetic data derived from the microdata. Given the strict
redistribution and explicit LLM bar, do not assume this is permitted.

---

## 6. Additional Dataset Candidates

Five additional datasets were investigated and found genuinely relevant (no
padding — a sixth candidate, a standalone national WHO STEPS India survey
distinct from NNMS, was investigated and **excluded**: NNMS *is* ICMR's
national implementation of the WHO STEPS methodology, so a separate entry
would double-count the same instrument/population. State-level STEPS
surveys exist but are sub-national one-off academic studies, not a single
national dataset, so also excluded as a distinct entry).

### 6.1 National Family Health Survey (NFHS-5), 2019–21

**Producing organization:** International Institute for Population Sciences
(IIPS), Mumbai, under MoHFW, with technical assistance from ICF (DHS
Program).

Sources: [IIPS](https://iipsindia.ac.in/content/national-family-health-survey-nfhs-5-india-report) · [DHS India report](https://dhsprogram.com/pubs/pdf/FR375/FR375.pdf) · [data.gov.in factsheets](https://www.data.gov.in/resource/all-india-and-stateut-wise-factsheets-national-family-health-survey-nfhs-5-2019-2021) · [World Bank Microdata Library](https://microdata.worldbank.org/index.php/catalog/4482)

- **Contains:** population, health, nutrition; hypertension, diabetes/
  blood-glucose testing, BMI/anthropometry, tobacco/alcohol use, household
  wealth index, alongside demographics (age, sex, education, household
  composition, urban/rural, state/district).
- **Why it could help:** the strongest available source for
  **nationally- and district-representative demographic + coarse
  cardiometabolic risk-factor distributions**.
- **Population/sample:** 636,699 households; 724,115 women (15–49);
  101,839 men (15–54); all states/UTs, district-level estimates for many
  indicators.
- **Individual-level:** RESTRICTED (registration-gated). **Aggregate:** YES
  (fact sheets, state/district reports, Open Government Data India).
- **Access:** DHS Program portal registration, free, purpose must be
  declared, framed as for "legitimate academic research."
- **Usage:** Research use permitted (explicit). Commercial use:
  `Not verified`. Redistribution: restricted without permission (DHS/IPUMS-
  DHS terms). Derived/synthetic-data generation: `Not verified`. Citation
  required (standard DHS format).
- **Freshness:** Fieldwork 2019–2021, published 2021–22; NFHS-6 not yet
  confirmed published as of this research pass.
- **Representativeness:** source explicitly states national/state/district
  representativeness.
- **Limitations:** survey-based risk factors (single BP reading, non-fasting
  glucose in some rounds) — population-distribution reference, not
  clinical-grade ground truth.

### 6.2 Longitudinal Ageing Study in India (LASI), Wave 1

**Producing organizations:** IIPS Mumbai, Harvard T.H. Chan School of Public
Health, USC, NIA-funded; distributed via Gateway to Global Aging Data.

Sources: [IIPS](https://www.iipsindia.ac.in/lasi) · [Nature Aging](https://www.nature.com/articles/s43587-021-00155-y) · [Gateway to Global Aging — LASI](https://g2aging.org/?section=overviews&study=lasi) · [NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/NBK109220/)

- **Contains:** nationally representative survey of India's **45+
  population** — directly relevant given CVD risk concentrates in older age
  groups. Detailed health (self-reported + biomarker/anthropometric — BP,
  anthropometry, blood glucose/HbA1c in a sub-sample), cognitive, social,
  economic variables, state-representative.
- **Population:** Wave 1: 73,396 adults 45+, all states/UTs.
- **Individual-level:** RESTRICTED (request form + government ID required).
  **Aggregate:** YES (published Wave 1 national report).
- **Access:** IIPS data-request form, reviewed within 24–48 working hours,
  restricted to "legitimate academic research purposes." A public-access
  de-identified subset is also available via Gateway to Global Aging Data
  by request.
- **Usage:** Research use permitted (explicit). Commercial use:
  `Not verified`. Redistribution: a CC BY-NC-ND license was found associated
  with LASI-DAD published materials specifically (not confirmed as the
  blanket license for all LASI microdata); commercial re-use requires
  separate contact. Derived/synthetic-data generation: `Not verified`.
  Attribution required.
- **Freshness:** Wave 1 fielded 2017–18, published from 2020. Wave 2
  fieldwork referenced in program materials but public release/access
  status: `Not verified`.
- **Representativeness:** multiple independent sources confirm national/
  state representativeness for the 45+ population.
- **Limitations:** restricted to 45+ — must be combined with a
  general-population source (e.g., NFHS) for younger ages.

### 6.3 NSS 75th Round — Household Social Consumption: Health (2017–18)

**Producing organization:** National Statistical Office (NSO), MoSPI,
Government of India.

Sources: [MoSPI unit-level data page](http://mospi.nic.in/unit-level-data-report-nss-75th-round-july-2017-june-2018-schedule-250social-consumption-health) · [microdata.gov.in catalog](https://microdata.gov.in/NADA/index.php/catalog/152) · [PIB release](https://www.pib.gov.in/newsite/PrintRelease.aspx?relid=194918)

- **Contains:** morbidity/ailment profiles, treatment-seeking, healthcare
  out-of-pocket expenditure, maternity/childbirth care, elderly health
  status. **Socioeconomic/healthcare-access conditioning** rather than
  direct clinical risk factors — complements NFHS/LASI's clinical variables.
- **Population:** 555,115 individuals, 8,077 rural villages + 6,181 urban
  blocks nationwide, stratified multi-stage design.
- **Individual-level: YES** — unit-level data directly published, a
  meaningfully different posture from NFHS/LASI/INDIAB/NNMS. **Aggregate:**
  YES (official summary report).
- **Access:** direct download from MoSPI / `microdata.gov.in` (India's
  official NADA-based microdata catalog), mirrored on the ICSSR Data
  Repository — **no registration-gated application process identified**,
  the most directly accessible dataset researched.
- **Usage:** Government of India open unit-level data. Specific license
  terms (commercial use, redistribution, derived-data generation):
  `Not verified` — the NADA catalog page's own terms-of-use statement should
  be read directly before relying on this beyond research use. Do not
  assume open-download implies unrestricted commercial/redistribution
  rights.
- **Freshness:** fielded July 2017 – June 2018, published ~2019–2020. A
  newer NSS health-consumption round: `Not verified` as published.
- **Representativeness:** described as nationally representative by MoSPI/
  PIB; not CVD-specific.

### 6.4 India State-Level Disease Burden Initiative (GBD, India states)

**Producing organizations:** ICMR, Public Health Foundation of India (PHFI),
IHME, with MoHFW.

Sources: [IHME project page](https://www.healthdata.org/research-analysis/health-by-location/disease-burden-initiative-research-library) · [Lancet Global Health 2018](https://www.thelancet.com/journals/langlo/article/PIIS2214-109X(18)30407-8/fulltext) · [PMC6227386](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6227386/)

- **Not a primary survey** — a modeled epidemiological synthesis (GBD
  methodology) combining many underlying sources to produce state-level
  disease burden (deaths, DALYs, prevalence) for CVD (ischemic heart
  disease, stroke, rheumatic heart disease) and risk factors, by state and
  year, 1990–2016 (later GBD cycles extend further).
- **Why it could help:** a **validation/reference layer** — a generated
  synthetic population's implied state-level CVD prevalence/burden can be
  compared against these published estimates as an external plausibility
  check. Not a source of individual-level records.
- **Individual-level: NO.** **Aggregate: YES** (that's the dataset's nature).
- **Access:** direct download via the Global Health Data Exchange (GHDx)
  portal, no registration gate identified for the estimate files themselves.
- **Usage:** IHME's **Free-of-Charge Non-Commercial User Agreement** —
  explicit: research use permitted, **commercial use NOT permitted** under
  the free agreement. Redistribution/derived use governed by the same
  agreement — read in full before any reuse.
- **Freshness:** primary cited study covers 1990–2016 (published 2017–18);
  GBD is an actively maintained recurring program (later global cycles
  referenced), but whether an India-state-level update beyond 2016 has been
  published as of 2026: `Not verified`.
- **Representativeness:** not survey-methodology "representative" in the
  usual sense — validity depends on the quality of GBD's underlying input
  data and modeling. A different kind of caveat than for the survey-based
  datasets above; stated explicitly rather than calling it "representative."

### 6.5 ICMR Acute Coronary Syndrome Registries — CREATE (2001–05) and STEMI-ACT (ongoing)

**Producing organization:** ICMR (CREATE via the Cardiological Society of
India network).

Sources: [CREATE — Lancet 2008](https://pubmed.ncbi.nlm.nih.gov/18440425/) · [STEMI-ACT official site](https://stemiact.icmr.org.in/) · [JACC abstract](https://www.jacc.org/doi/10.1016/S0735-1097%2823%2902752-3)

- **Contains:** the closest thing found to **clinical CVD-event registries**
  (as opposed to population risk-factor surveys) — hospitalized acute
  coronary syndrome cases with treatment patterns and outcomes. Potentially
  informative for diagnosis/encounter/medication-pattern realism if a
  diagnosed-CVD subpopulation is later modeled.
- **Population:** CREATE: 20,937 patients (20,468 definite ACS, 60.6%
  STEMI), 89 centres across 10 regions/50 cities. STEMI-ACT: scope/sample
  size `Not verified` in this pass beyond a conference abstract.
- **Individual-level:** CREATE: **NO** (published aggregate results only, no
  public microdata identified). STEMI-ACT: **UNKNOWN** — an ICMR ePMS portal
  exists but whether it grants external-researcher access to patient-level
  data, or is an internal PI/data-collection system only, was
  `Not verified`.
- **Aggregate:** CREATE: YES (2008 Lancet paper). STEMI-ACT: partial
  (conference-abstract-level results only).
- **Access:** CREATE: no data-access mechanism found — treat as
  published-results-only, not a reusable dataset. STEMI-ACT: `Not verified`
  — would require directly contacting ICMR.
- **Usage:** `Not verified` for either — no terms-of-use/data-sharing policy
  located. Do not assume any access is available without direct
  confirmation from ICMR.
- **Freshness:** CREATE enrollment ~2001–05, published 2008 — nearly 20
  years old, care patterns have likely changed substantially. STEMI-ACT
  appears active (recent conference abstract found) but current status is
  `Not verified`.
- **Representativeness:** CREATE is multi-city but hospital-based, **not**
  population-representative (captures only patients who reached a
  participating hospital — an acknowledged limitation of clinical
  registries). No source claims national representativeness for either
  registry, unlike NFHS/LASI/NSSO.
- **Honest accessibility note:** of all eight datasets in this report, this
  is the weakest on practical accessibility — included because it is the
  only genuinely CVD-clinical (not risk-factor-survey) Indian source found,
  but should currently be treated as a citation/context source (e.g., citing
  published STEMI proportion, treatment-delay statistics), not a usable
  data input.

---

## 7. Dataset Comparison

| Dataset | Population | Geographic Coverage | Urban/Rural | Health Variables | Demographics | Individual Data | Access | Potential Project Role |
|---|---|---|---|---|---|---|---|---|
| ICMR-INDIAB | 113,043 adults 20+ | All 28 states, 2 UTs, NCT Delhi | Both | Diabetes, HTN, obesity, lipids (sub-sample), smoking | age, sex, education, region | RESTRICTED (query-mediated) | NHRDR registration + approval | Cardiometabolic risk-factor calibration |
| ICMR-NNMS | 10,659 adults 18–69 | ~27 states confirmed | Both, equal allocation | Tobacco, alcohol, physical activity, diet, BMI, BP, glucose | age, sex, education, SES | RESTRICTED (query-mediated) | NHRDR registration | NCD behavioral/risk-factor distributions |
| IHDS (Waves 1–2) | 41,554 / 42,152 households | All major states | Both | Morbidity (self-report), tobacco/alcohol, anthropometry | age, sex, education, household | **YES (public)** | ICPSR free registration | Demographic/socioeconomic context |
| NFHS-5 | 636,699 households; ~825k individuals | All states/UTs, district-level | Both | HTN, diabetes screening, BMI, tobacco/alcohol | age, sex, education, wealth index | RESTRICTED (registration) | DHS Program registration | Demographic + coarse CV risk calibration |
| LASI Wave 1 | 73,396 adults 45+ | All states/UTs | Both | BP, anthropometry, glucose/HbA1c (sub-sample) | age, sex, state | RESTRICTED (request + ID) | IIPS request form | Older-age CV/comorbidity distributions |
| NSS 75th Round | 555,115 individuals | Nationwide | Both | Morbidity, healthcare expenditure, insurance | age, sex, household | **YES (open download)** | `microdata.gov.in`, no gate found | Socioeconomic/healthcare-access context |
| GBD India State-Level | N/A (modeled) | All states | N/A | CVD burden estimates (DALYs, deaths, prevalence) | N/A | NO (aggregate by design) | GHDx, open (non-commercial terms) | Validation/reference only |
| CREATE / STEMI-ACT | 20,937 ACS patients (CREATE) | 50 cities / 10 regions | Hospital-based, not pop-representative | ACS/STEMI treatment & outcomes | age, sex (clinical cohort) | NO / UNKNOWN | None found / `Not verified` | Citation context only, not integrable today |

Roles differ rather than rank:
- **ICMR-INDIAB** → strongest cardiometabolic clinical risk-factor evidence.
- **ICMR-NNMS** → strongest NCD behavioral/risk-factor evidence.
- **NFHS-5** → strongest demographic + district-level breadth.
- **IHDS** → strongest socioeconomic/household context, weakest on clinical CV data.
- **LASI** → strongest older-age (45+) CV/comorbidity depth.
- **NSS 75th Round** → strongest healthcare-access/utilization context, and the most directly accessible microdata of the health-adjacent sources.
- **GBD India State-Level** → reference/validation only, never a generation input.
- **CREATE/STEMI-ACT** → the only clinical-event (not survey) source, but not practically usable as data today.

---

## 8. Schema-Variable Mapping

Current schema (`schemas/patient_schema.py`, Schema v0.2): `risk_factors`,
`family_history`, `medical_history`, `diagnoses`, `medications`, `labs`, and
`encounters` are all currently `Optional[dict]`/`Optional[list]` **with no
defined sub-fields** (Stage 3 work, not yet implemented). Per this
milestone's instructions, this mapping shows which *container* each dataset
variable would eventually belong under, and marks specific prospective key
names as `Potential future field` — no schema change is made here.

| Dataset variable | Our schema field | Direct / Derived | Potential use | Notes |
|---|---|---|---|---|
| Age | `demographics.age` | Direct | Already-implemented field | Already populated (currently reused from PTB-XL, not Indian data — see `docs/DECISIONS.md` D004) |
| Sex | `demographics.sex` | Direct | Already-implemented field | Encoding would need reconciling — PTB-XL uses 0=male/1=female; verify each Indian source's own encoding before merging |
| Height/weight (IHDS, LASI anthropometry) | `demographics.height_cm` / `demographics.weight_kg` | Direct | Already-implemented field | Units must be checked per source |
| BMI (NFHS, NNMS, ICMR-INDIAB) | `risk_factors` (key: `bmi`) | Derived (from height/weight) or Direct (if source reports BMI directly) | `Potential future field` | Container exists; sub-field doesn't yet |
| Hypertension (all health surveys) | `risk_factors` (key: `hypertension`) | Direct | `Potential future field` | Definitions vary by source — see §13 |
| Diabetes/glucose (ICMR-INDIAB, NNMS, NFHS, LASI) | `risk_factors` (key: `diabetes`) | Direct | `Potential future field` | Diagnostic method differs (OGTT vs. fasting vs. capillary) — see §13 |
| Dyslipidaemia/lipids (ICMR-INDIAB sub-sample) | `labs` (list of lab results) | Direct | `Potential future field` | Only ICMR-INDIAB confirmed lipid measurement, and on a sub-sample |
| Smoking/tobacco status (INDIAB, NNMS, NFHS, IHDS) | `risk_factors` (key: `smoking_status`) | Direct | `Potential future field` | — |
| Alcohol use (NNMS, IHDS) | `risk_factors` (key: `alcohol_use`) | Direct | `Potential future field` | — |
| Physical activity (NNMS, INDIAB) | `risk_factors` (key: `physical_activity`) | Direct | `Potential future field` | — |
| Family history of diabetes (ICMR-INDIAB) | `family_history` (key: `diabetes`) | Direct | `Potential future field` | Family CVD history specifically: `Not verified` present in any researched source |
| Household/socioeconomic status (IHDS, NSS, NFHS wealth index) | *(no current container)* | — | `Potential future field` | No schema field exists for socioeconomic context today — would need a new section if adopted, not decided here |
| Morbidity/self-reported conditions (IHDS, NSS) | `medical_history` | Direct (self-report, not clinical diagnosis) | `Potential future field` | Should not be conflated with clinically-confirmed `diagnoses` |
| Healthcare utilization/expenditure (NSS 75th Round) | `encounters` | Derived | `Potential future field` | Represents care-seeking behavior, not a clinical encounter record per se |
| ACS/STEMI treatment patterns (CREATE/STEMI-ACT) | `diagnoses` / `encounters` / `medications` | Derived (population-level pattern, not individual record — see §5) | `Potential future field` | Not individual-level; would inform *distribution* of a diagnosed-CVD subpopulation, not per-patient values |
| State-level CVD burden (GBD India) | *(no current field — validation use)* | N/A | Validation/reference, not a generation input | Used to check aggregate plausibility of a generated population, never mapped to a per-patient field |

No dataset variable researched maps cleanly to `echo` (echocardiography) —
none of the eight sources collect echo data. This is consistent with the
spec's own note that echo scope is an open decision
(`docs/superpowers/specs/...-spec-design.md` §7).

---

## 9. Individual vs. Aggregate Data — Why It Matters

```text
Individual-level data:
  ICMR-INDIAB    RESTRICTED (query-mediated only)
  ICMR-NNMS      RESTRICTED (query-mediated only)
  IHDS           YES (public, ICPSR, Waves 1-2)
  NFHS-5         RESTRICTED (registration-gated)
  LASI           RESTRICTED (request + ID-gated)
  NSS 75th Round YES (public, no gate found)
  GBD India      NO (aggregate by design)
  CREATE/STEMI   NO / UNKNOWN

Aggregate statistics:
  ICMR-INDIAB    YES
  ICMR-NNMS      YES
  IHDS           YES
  NFHS-5         YES
  LASI           YES
  NSS 75th Round YES
  GBD India      YES (this IS the dataset)
  CREATE/STEMI   YES (CREATE) / partial (STEMI-ACT)
```

**Why the distinction matters for this project:** aggregate statistics
(prevalence with confidence intervals, mean/SD by age-sex-state group) are
sufficient for **distribution calibration** — e.g., sampling a generated
patient's hypertension status from a state-and-age-appropriate marginal
probability. They are **not** sufficient for **joint-distribution
modeling** — e.g., correctly capturing that hypertension, diabetes, and
obesity co-occur in the same individuals at a certain rate, which requires
seeing individual records, not just each variable's separate marginal
prevalence. Of the eight sources, only **IHDS** and the **NSS 75th Round**
currently offer that individual-level access without an application/approval
step — and neither has strong direct cardiovascular clinical variables. The
datasets with the richest CV risk-factor content (ICMR-INDIAB, NNMS, NFHS,
LASI) are exactly the ones where individual-level access is gated. This
report does not claim any dataset supports joint modeling beyond what its
actual available access level permits.

---

## 10. Access and Licensing

Per instructions, access (can we obtain it) and usage/licensing (what can we
do with it once obtained) are kept as separate, explicit statements for
every dataset — see each dataset's own "Access" and "Usage" subsections in
§3–§6. Consolidated view:

| Dataset | Access mechanism | Research use | Commercial use | Redistribution | Derived/synthetic data | Citation required |
|---|---|---|---|---|---|---|
| ICMR-INDIAB | NHRDR registration + query approval | `Not verified` (implied) | `Not verified` | `Not verified` | `Not verified` | Not formally stated; academic norm applies |
| ICMR-NNMS | NHRDR registration | `Not verified` | `Not verified` | `Not verified` | `Not verified` | `Not verified` |
| IHDS | ICPSR free registration | Yes, research/statistical only | `Not verified` (implied restricted) | **Barred** without written ICPSR agreement | Not verified; **LLM data-retention/training explicitly barred** | Yes, formal citation strings provided |
| NFHS-5 | DHS Program registration | Yes (stated) | `Not verified` | Restricted without permission | `Not verified` | Yes, standard DHS format |
| LASI | IIPS request form + ID | Yes (stated) | `Not verified` | CC BY-NC-ND for LASI-DAD materials specifically; general microdata license `Not verified` | `Not verified` | Yes (attribution required) |
| NSS 75th Round | Open download, `microdata.gov.in` | Presumed via open GoI data, terms page not confirmed | `Not verified` | `Not verified` | `Not verified` | `Not verified` |
| GBD India State-Level | Open download, GHDx | Yes (explicit) | **No** (explicit, free-of-charge agreement is non-commercial) | Governed by IHME agreement | `Not verified` | Per IHME agreement |
| CREATE / STEMI-ACT | None found / `Not verified` | `Not verified` | `Not verified` | `Not verified` | `Not verified` | `Not verified` |

**No inference was made anywhere licensing terms were silent.** Where a cell
above says `Not verified`, that reflects the absence of a located affirmative
statement — it must not be read as "probably fine."

---

## 11. Data Quality / Representativeness

| Dataset | Sampling design | Nationally representative? (per source) | Known caveats |
|---|---|---|---|
| ICMR-INDIAB | Stratified multistage, 3-level stratification, 4 cardinal regions | Yes (source-stated) | Lipid measurement only on a ~25,647-person sub-cohort vs. ~107–111k for other variables |
| ICMR-NNMS | Stratified multistage cluster, PPS + WHO-KISH grid | Yes (source-stated) | Only ~27 states confirmed in one source; single-visit field measurement (capillary glucose, camp BP) |
| IHDS | Stratified national household panel | Yes (source-stated) | No confirmed clinical biomarker module; latest public wave is 13+ years old |
| NFHS-5 | Stratified multi-stage, DHS-standard methodology | Yes, including district-level (source-stated) | Self-reported/measured risk factors have standard survey limitations (single BP reading, non-fasting glucose in some rounds) |
| LASI | Stratified national panel, 45+ only | Yes for the 45+ population (multiple sources) | Not representative of the full population — only ages 45+ |
| NSS 75th Round | Stratified multi-stage (Census villages / UFS blocks) | Yes (source-stated) | General health-consumption survey, not CVD-specific |
| GBD India State-Level | N/A — modeled synthesis, not a sample survey | Not applicable in the survey-methodology sense | Validity depends on underlying input-data/model quality, a different caveat category |
| CREATE / STEMI-ACT | Multi-city hospital-based enrollment | **Not** claimed representative by any source | Captures only patients who reached a participating hospital — acknowledged clinical-registry limitation |

---

## 12. Data Freshness

| Dataset | Collection/wave years | Publication year(s) | Newer wave exists? | Actively maintained? |
|---|---|---|---|---|
| ICMR-INDIAB | 2008–2020 (5 phases) | Latest major: 2023 (ICMR-INDIAB-17); sub-study 2025 | New field-collection waves post-2020: `Not verified` | Appears active (2025 sub-study published) |
| ICMR-NNMS | 2017–18 | 2021 (main); 2025 (adolescent methods paper) | Full adult NNMS-2: `Not verified` | Program appears active; adult-wave status unclear |
| IHDS | Wave 1: 2004–05; Wave 2: 2011–12 | 2018 (ICPSR release) | IHDS-3: status conflicting/unresolved (see §5) | Unclear — flagged explicitly |
| NFHS-5 | 2019–2021 | 2021–22 | NFHS-6: not confirmed published as of this research pass | Yes, recurring DHS-aligned program |
| LASI | Wave 1: 2017–18 | From 2020 | Wave 2 fieldwork referenced; public release status `Not verified` | Appears active |
| NSS 75th Round | 2017–18 | ~2019–2020 | Newer NSS health round: `Not verified` | MoSPI runs recurring NSS rounds generally |
| GBD India State-Level | 1990–2016 (primary cited study) | 2017–2018 | Later GBD global cycles exist (2019/2021/2023 referenced); India-state-level update beyond 2016: `Not verified` | Yes, IHME's GBD is an actively maintained recurring program |
| CREATE | 2001–2005 | 2008 | STEMI-ACT is a newer, apparently-active successor effort | CREATE itself: no, it's a closed historical registry |

**This matters because the project is being developed in 2026.** IHDS's
public microdata (2011–12) is now well over a decade old; CREATE's data is
nearly 20 years old. Treat both as historical-context sources, not current
population snapshots, unless a newer wave's status is re-confirmed.

---

## 13. Dataset Compatibility Concerns

### Population/sampling overlap
- ICMR-INDIAB, NNMS, and NFHS-5 all sample the general adult Indian
  population through independent, differently-designed household surveys —
  their samples are **not the same individuals**, but they measure
  overlapping constructs (BMI, hypertension, diabetes) using **different
  instruments and protocols**. Combining their prevalence estimates as if
  they were one consistent dataset would conflate different measurement
  methods, not just different samples.
- LASI overlaps with NFHS/NNMS/INDIAB only in the 45+ age band; below that
  age it contributes nothing, so it should be treated as a
  population-*subset* enrichment, not a merge candidate for the general
  population.
- NSS 75th Round's morbidity/utilization data and NFHS's clinical screening
  data both touch "health status" but from different angles (self-reported
  healthcare-seeking behavior vs. measured clinical indicators) — not
  duplicative, but also not directly reconcilable into one variable.
- GBD India is itself a synthesis of many of the same underlying surveys
  (likely including some of NFHS/INDIAB/NNMS as inputs) — using it
  *alongside* those primary surveys for the same purpose (e.g., both as
  calibration targets) risks **double-counting the same underlying
  evidence**. Its correct use is validation of a population built from the
  primary surveys, not an independent calibration source alongside them.

### Variable-definition compatibility
| Variable | Known definitional differences found |
|---|---|
| Hypertension | Exact BP cutoff/definition not confirmed identical across ICMR-INDIAB, NNMS, and NFHS in this research pass — `Not verified` whether all three use the same threshold (e.g., ≥140/90 vs. other guideline cutoffs). Must be checked before merging. |
| Diabetes | ICMR-INDIAB and portions of NFHS/LASI use OGTT/fasting-glucose-based clinical criteria; NNMS uses single-visit capillary glucose testing at camps — **different diagnostic rigor**, not directly interchangeable. |
| BMI/obesity | Generally WHO-standard BMI cutoffs are used across Indian NCD surveys, but INDIAB reports both "generalised obesity" (BMI-based) and "abdominal obesity" (waist-based) as distinct figures — conflating the two would misrepresent prevalence. |
| Smoking/tobacco | INDIAB uses never/current/past categories; NNMS separately tracks smoked vs. smokeless tobacco — a coarser INDIAB category cannot be directly cross-walked to NNMS's finer distinction without a defined mapping. |
| Urban/rural | Multiple surveys use the Census-based urban/rural frame (2011 Census for NNMS), which should be broadly consistent — but exact classification vintage (2011 Census in older surveys vs. any updated frame in newer ones) was not independently confirmed as identical across all eight sources. |
| Age | LASI's 45+ restriction vs. general-population surveys' typically 15/18+ lower bound is a **hard boundary difference**, not just a definitional nuance — already noted above. |
| Sex/gender | PTB-XL (already in the schema via ECG data, per `docs/DECISIONS.md` D004) encodes sex as 0=male/1=female; none of the eight Indian sources' exact coding scheme was independently confirmed in this pass — `Not verified`, must check each source's codebook before any merge, not assume encodings match. |

None of these definitional differences were resolved or normalized in this
research pass — that is explicitly deferred, per instructions ("do not
normalize the definitions in code yet").

---

## 14. Potential Combination Strategy

> **PROPOSED — NOT YET IMPLEMENTED.** This is a conceptual sketch only, based
> on the evidence gathered above. No decision has been made to build this,
> and doing so is out of scope for M2A.

```text
ICMR-INDIAB
     ↓
Cardiometabolic risk-factor population distributions
(diabetes, hypertension, BMI, dyslipidaemia — aggregate calibration only,
 given restricted individual-level access)

ICMR-NNMS
     ↓
NCD behavioral risk-factor distributions
(tobacco, alcohol, physical activity, diet — aggregate calibration only)

NFHS-5
     ↓
District-level demographic + coarse cardiometabolic calibration
(broadest geographic granularity of the health-survey sources)

LASI
     ↓
Older-age (45+) comorbidity depth
(enrichment layer for the highest-CV-risk age band only)

IHDS + NSS 75th Round
     ↓
Socioeconomic/household context
(the only sources with open individual-level access, but weak on direct
 clinical CV variables — candidate for joint-distribution modeling of
 context variables specifically, not clinical risk factors)

GBD India State-Level Disease Burden Initiative
     ↓
Post-hoc validation
(compare a generated population's implied state-level CVD burden against
 published estimates — never used as a generation input directly)
```

This layering follows the pattern the dataset-comparison section already
shows: each source contributes a role, not a merge. Any actual combination
would need to resolve the compatibility concerns in §13 first (definitional
alignment, avoiding double-counting GBD's own input surveys, and confirming
licensing actually permits the intended derived use — most of which is
currently `Not verified`).

---

## 15. Proposed Dataset Roles

```text
ICMR-INDIAB
→ Cardiometabolic risk-factor / population calibration
→ Relevant variables: diabetes, hypertension, BMI, dyslipidaemia (sub-sample), smoking, family history of diabetes
→ Expected stage of use: M2/M3 generation calibration, later validation

ICMR-NNMS
→ NCD behavioral risk-factor calibration
→ Relevant variables: tobacco, alcohol, physical activity, diet, BMI, BP, glucose
→ Expected stage of use: M2/M3 generation calibration, later validation

NFHS-5
→ Demographic + district-level coarse risk-factor calibration
→ Relevant variables: age, sex, education, wealth index, hypertension, diabetes screening, BMI, tobacco/alcohol
→ Expected stage of use: M2/M3 generation calibration (broadest geographic granularity), later validation

LASI
→ Older-age (45+) comorbidity/risk-factor enrichment
→ Relevant variables: BP, anthropometry, glucose/HbA1c (sub-sample), age, state
→ Expected stage of use: M3+ generation calibration for the 45+ age band specifically

IHDS
→ Socioeconomic/household demographic context
→ Relevant variables: income, consumption, education, household composition, tobacco/alcohol (self-report)
→ Expected stage of use: M3+ context conditioning, if a socioeconomic schema section is later added (not decided here)

NSS 75th Round
→ Healthcare-access/utilization context
→ Relevant variables: healthcare expenditure, insurance coverage, care-seeking behavior
→ Expected stage of use: M3+ context conditioning / encounters modeling, if adopted

GBD India State-Level Disease Burden Initiative
→ Population-level validation/reference
→ Relevant variables: state-level CVD DALYs, deaths, prevalence estimates
→ Expected stage of use: Stage 5/6 validation, never a direct generation input

CREATE / STEMI-ACT
→ Citation/context source for diagnosed-CVD subpopulation plausibility
→ Relevant variables: STEMI proportion, treatment-delay statistics, ACS treatment patterns
→ Expected stage of use: Stage 3+ narrative/plausibility grounding only, not an integrable dataset at this time
```

These are recommendations for future consideration, not current
implementation decisions.

---

## 16. What This Milestone Does Not Decide

Per the M2A instructions, this research explicitly does **not** decide:

- Final dataset selection
- Final dataset combination
- Any schema modifications
- Generator implementation
- Distribution parameters
- Model architecture
- CardioSynth/CardioSync integration
- AWS infrastructure
- Training/fine-tuning of any model
- Final Indian demographic conditioning methodology

Those are separate, later decisions — several of them explicit human
checkpoints per `docs/Claude.md` §28.

---

## 17. Open Questions

1. Does ICMR's NHRDR query-mediated access model (ICMR-INDIAB, NNMS) permit
   a use case like "calibrate a synthetic-data generator's distributions,"
   or only ad hoc statistical queries? Not addressed by anything found.
2. Is there a second full-adult NNMS wave (NNMS-2) beyond 2017–18? Sources
   are ambiguous.
3. What is IHDS-3's actual current public-availability status? Sources
   conflict (in-preparation vs. already fielded).
4. Do ICMR-INDIAB and NNMS use the same clinical definitions/cutoffs for
   hypertension and diabetes as NFHS/LASI? Not confirmed identical.
5. Does any researched dataset's license explicitly permit generating
   *synthetic* data derived from it? Not confirmed for any of the eight —
   this is a load-bearing open question for the entire Indian-conditioning
   direction of the project, not just a detail.
6. If a future pipeline stage uses an LLM in any capacity that touches
   IHDS-derived data, does that trigger ICPSR's explicit LLM-training/
   retention bar? Needs direct clarification from ICPSR/NCAER, not
   assumption either way.
7. Does STEMI-ACT's ICMR ePMS portal grant any external-researcher access
   path, or is it internal-only? Not determined.
8. Has GBD published an India-state-level CVD burden update beyond the
   1990–2016 primary study, and if so, is it accessible under the same
   non-commercial terms?
9. What sex/gender coding does each Indian source actually use in its
   codebook, and does any of them match PTB-XL's 0=male/1=female convention
   already embedded in the current schema (`docs/DECISIONS.md` D004)?

---

## 18. Recommended Next Research Step

Before any implementation decision: **directly confirm, in writing from
ICMR (NHRDR) and ICPSR/NCAER respectively, whether synthetic-data generation
derived from their datasets (including via an LLM-based pipeline) is
permitted.** This single question gates nearly every other decision in this
report — every dataset examined left it `Not verified`, and IHDS's terms
raise it as an explicit concern rather than a silent gap. Resolving it is
cheaper and lower-risk than any further technical integration work, and
several downstream decisions (dataset selection, combination strategy,
whether individual-level access is even worth pursuing) depend on the
answer.

Secondary next steps, roughly in order of leverage:
1. Re-verify IHDS-3's actual public-availability status directly (ICPSR
   blocked automated fetches in this research pass).
2. Directly read the MoSPI/NADA terms-of-use page for the NSS 75th Round
   (the most openly accessible dataset found) rather than relying on the
   absence of a visible gate as evidence of permissive terms.
3. Confirm hypertension/diabetes definitional consistency across
   ICMR-INDIAB, NNMS, and NFHS-5 by reading their published methodology
   chapters/questionnaires directly.

---

## 19. Sources

**ICMR-INDIAB:** [Lancet Diabetes & Endocrinology overview](https://thelancet.com/journals/landia/article/PIIS2213-8587(17)30190-0/fulltext) · [MDRF Eprints](http://mdrf-eprints.in/1420/) · [PubMed 37301218](https://pubmed.ncbi.nlm.nih.gov/37301218/) · [NHRDR dataset page](https://nhrdr.icmr.org.in/datasets/icmr-indiab) · [ICMR-INDIAB-17, Lancet Diabetes & Endocrinology 2023](https://www.thelancet.com/journals/landia/article/PIIS2213-8587(23)00119-5/fulltext) · [Nature Medicine 2025 diet sub-study](https://www.nature.com/articles/s41591-025-03949-4) · [NCDIR policy PDF](https://ncdirindia.org/Downloads/NCDIR_Policy.pdf) · [DBT/ICMR draft biological data policy](https://dbtindia.gov.in/sites/default/files/Draft1-Biological_Data_Policy.pdf)

**ICMR-NNMS:** [Factsheet PDF](https://www.ncdirindia.org/nnms/resources/factsheet.pdf) · [NHRDR dataset page](https://nhrdr.icmr.org.in/datasets/national-ncd-monitoring-survey-nnms-household-and-adult) · [PLOS One 2021](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0246712) · [PMC7924800](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7924800/) · [BMC Health Services Research](https://link.springer.com/article/10.1186/s12913-021-06530-0) · [BMC Public Health regional estimates](https://bmcpublichealth.biomedcentral.com/articles/10.1186/s12889-022-13466-5) · [NCDIR NCD page](https://ncdirindia.org/NCD.aspx) · [ScienceDirect 2025 adolescent methods paper](https://www.sciencedirect.com/science/article/pii/S2215016125003796) · [PMC12337017](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12337017/)

**IHDS:** [NCAER project page](https://ncaer.org/project/india-human-development-survey-ihds/) · [ihds.umd.edu/data](https://ihds.umd.edu/data) · [Wikipedia](https://en.wikipedia.org/wiki/India_Human_Development_Survey) · [NCAER Feb 2026 page](https://ncaer.org/publication/india-human-development-survey-february-2026/) · [ICPSR 22626](https://www.icpsr.umich.edu/web/DSDR/studies/22626) · [ICPSR 36151](https://www.icpsr.umich.edu/web/DSDR/studies/36151) · [ihds.umd.edu/ihds-1-codebook-topic-index]

**NFHS-5:** [IIPS](https://iipsindia.ac.in/content/national-family-health-survey-nfhs-5-india-report) · [MoHFW/IIPS report PDF](http://rchiips.org/nfhs/NFHS-5Reports/NFHS-5_INDIA_REPORT.pdf) · [DHS India report](https://dhsprogram.com/pubs/pdf/FR375/FR375.pdf) · [data.gov.in factsheets](https://www.data.gov.in/resource/all-india-and-stateut-wise-factsheets-national-family-health-survey-nfhs-5-2019-2021) · [World Bank Microdata Library](https://microdata.worldbank.org/index.php/catalog/4482) · [DHS registration](https://dhsprogram.com/data/new-user-registration.cfm) · [DHS terms of use](https://dhsprogram.com/data/terms-of-use.cfm) · [IPUMS terms](https://www.ipums.org/about/terms) · [Wikipedia NFHS overview](https://en.wikipedia.org/wiki/National_Family_Health_Survey)

**LASI:** [IIPS](https://www.iipsindia.ac.in/lasi) · [Nature Aging cohort description](https://www.nature.com/articles/s43587-021-00155-y) · [Gateway to Global Aging — LASI](https://g2aging.org/?section=overviews&study=lasi) · [NCBI Bookshelf overview](https://www.ncbi.nlm.nih.gov/books/NBK109220/) · [IIPS LASI data](https://www.iipsindia.ac.in/content/LASI-data) · [Gateway to Global Aging downloads](https://g2aging.org/?section=lasi-downloads) · [Harmonized LASI-DAD Documentation](https://lasi-dad.org/codebooks/Harmonized%20LASI-DAD%20A.3.pdf)

**NSS 75th Round:** [MoSPI unit-level data page](http://mospi.nic.in/unit-level-data-report-nss-75th-round-july-2017-june-2018-schedule-250social-consumption-health) · [microdata.gov.in catalog](https://microdata.gov.in/NADA/index.php/catalog/152) · [ICSSR Data Repository mirror](http://icssrdataservice.in/datarepository/index.php/catalog/152/overview) · [PIB release](https://www.pib.gov.in/newsite/PrintRelease.aspx?relid=194918)

**GBD India State-Level:** [IHME project page](https://www.healthdata.org/research-analysis/health-by-location/disease-burden-initiative-research-library) · [Lancet Global Health 2018](https://www.thelancet.com/journals/langlo/article/PIIS2214-109X(18)30407-8/fulltext) · [PMC6227386](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6227386/) · [GHDx portal](https://ghdx.healthdata.org/) · [IHME data terms reference](https://ghdx.healthdata.org/ihme_data)

**CREATE / STEMI-ACT:** [CREATE — PubMed abstract](https://pubmed.ncbi.nlm.nih.gov/18440425/) · [STEMI-ACT official site](https://stemiact.icmr.org.in/) · [JACC abstract reference](https://www.jacc.org/doi/10.1016/S0735-1097%2823%2902752-3)

---

## Verification Notes

- Several official pages (ICPSR study-specific terms, ICMR-INDIAB full-text
  PDF) returned HTTP 403 to automated fetches during this research pass and
  were instead sourced from search-engine-cached snippets or adjacent
  official pages. These are flagged inline where they occur (see IHDS §5)
  and should be treated as lower-confidence-but-sourced, worth a direct
  human re-check before any access application is submitted.
- Every `Not verified` marker in this document reflects an absence of a
  located affirmative statement from a credible source, not a guess in
  either direction. Nothing in this document should be read as "probably
  yes" where it says `Not verified`.
