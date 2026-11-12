# M9 — Population & Environmental Data Enrichment: Audit + Design Proposal

**Status:** M9-1 audit COMPLETE; design PROPOSED, nothing implemented beyond read-only tooling and
config prose corrections. **No dataset generated or modified.** Date: 2026-10-29.

Machine-readable audit: `docs/M9_FIELD_COMPLETENESS_AUDIT.json`
(tool: `integration/audit_field_completeness.py`, test: `tests/test_m9_field_audit.py`).
Audited: frozen v0.8, `outputs/m8/100k_patients_v08/` (100,000 records), read-only.

---

## 1. Field-completeness audit (actual data, n = 100,000)

| Field | Valid | Null | Invalid | Generation / source | Note |
|---|---|---|---|---|---|
| demographics.age | 100% | 0 | 0 | uniform(20,89), engineering default (D007) | KS p=0.886 vs config |
| demographics.sex | 100% | 0 | 0 | Census 2011 marginal | chi² p=0.919 |
| demographics.state | 100% | 0 | 0 | Census 2011, 2011 boundaries | chi² p=0.055 |
| demographics.urban_rural | 100% | 0 | 0 | Census 2011 marginal, **independent of state** | see §2.1 |
| demographics.height_cm / weight_kg | 0 | 100% | 0 | not generated (no mean+SD) | unchanged |
| risk_factors.bmi | 100% | 0 | 0 | NNMS sex-conditional category + uniform | p=0.26/0.41 |
| risk_factors.smoking_status | 100% | 0 | 0 | NNMS sex-conditional; `former` never produced | p=0.20/0.81 |
| risk_factors.hypertension/diabetes/hyperlipidemia | 100% | 0 | 0 | INDIAB unconditioned Bernoulli | 35.40% / 11.46% / 81.23% |
| family_history | 0 | **100%** | 0 | not generated | see §4 |
| labs.HbA1c | 88.54% | 11.46% | 0 | only non-diabetics, by design | 0 rule violations |
| blood_pressure.systolic/diastolic | 100% | 0 | 0 | NFHS-5 joint grid PMF, label-conditional | 0 region violations |
| blood_pressure.measured_at | 100% | 0 | 0 | **one value for all records: 2026-09-26** (generation date) | see §5 |
| heart rate, resp. rate, temperature, SpO2 | — | — | — | **do not exist** in schema/generator/validators | not proposed |
| AQI / any environmental field | — | — | — | **does not exist** anywhere | see §5 |

Age coverage of evidence: 20-44: 36,127 · 45-69: 36,441 · 70-89: 27,432 (beyond NNMS 18-69 coverage).
BP extrapolated beyond NFHS-5 age coverage: 52,684 (flag verified correct for all records).

## 2. Statistical / implementation concerns found

1. **State × urban/rural independence produces implausible combinations.** Generated urban share
   is ~31% in every state, e.g. Delhi 29.9%, Chandigarh 32.9%, Bihar 30.7%. Census 2011
   (MHA Lok Sabha table): Chandigarh 97.25% urban, Bihar 11.3% urban. ~970 of ~1,387 Delhi
   records are "rural". Already a documented limitation (config `urban_rural`, D010), now
   quantified. Material for any location-based linkage (AQI).
2. **Isolated diastolic hypertension dominates the untreated-hypertensive BP region in young
   patients.** Share of the `raised` region with SBP<140 & DBP≥90 (after the floor): women
   20-24 87.3%, men 20-24 60.6%, falling to ~34% at the oldest bands. Mean SBP of untreated
   hypertensives = 140.02. Root cause: hypertension is a flat 35.5% at every age (no
   age-stratified INDIAB table) while NFHS-5 young-adult BP is low, so the label forces draws
   into the nearest tail (DBP). No external IDH-share figure was verified; flagged for review,
   not changed.
3. **Pulse-pressure floor (20 mmHg):** removes 0.0–3.6% of probability mass per
   (sex, band, region) cell (max: women 45-49 normotensive 3.64%). Because it truncates and
   renormalises, there is no pile-up at 20 (counts at PP=20..25: 445, 554, 683, 804, 942, 1106).
   Behaviour matches its documentation; no change recommended or made. Remains open decision #4.
4. **Treated hypertensives** (`unconstrained`, n=5,211): 71.8% below 140/90. No BP-control-rate
   evidence exists in the project to check this against — unverified, not a defect claim.
5. **Stale config prose (FIXED, prose only):** `risk_factors.blood_pressure.transformation`
   steps (3)/(4), `limitations (b)` and `evidence_tier` described the superseded first M8 sampler
   (independent truncated normals, "correlation NOT modelled"). The code uses a joint grid with
   r=0.7255. Corrected 2026-10-29; no parameter changed.
6. **Provenance self-contradiction (frozen, not changed):** each v0.8 record's
   `provenance.generator` says family_history is unpopulated because of "no Indian evidence
   source (D004)" and later "an open human scope decision, not an evidence gap".
7. **Frozen v0.8 is no longer reproducible from the current working tree.** D019 (lipid
   reject-and-redraw, applied 2026-10-29 by another session) changes the 2.28% impossible-panel
   records: a 2,000-record `--compare-source` check gives 1,952 exact matches and 48 seed-replay
   mismatches, all lipid/HbA1c on exactly those records. Expected consequence of D019, but the
   v0.8 manifest should record that reproducing it requires the pre-D019 code state.

## 3. Evidence reviewed (verified this pass)

| Source | Claim it supports | Verified how |
|---|---|---|
| Ahmed W, BMC Public Health 2024, doi:10.1186/s12889-024-18146-0 (PMC11005278, CC BY 4.0), LASI W1 2017-18 | FH diabetes (father/mother/sibling) **14.33% weighted** (8,822/58,612), 45+; parental 9.28%, sibling 6.81%; self-reported diabetes 27.8% with FH vs 9.2% without; overall 11.9%; outcome = self-reported diagnosis | full text, Table 1 |
| Ahmed, Dixit & Halli, Front. Cardiovasc. Med. 2024, doi:10.3389/fcvm.2024.1386378 (PMC11659756, CC BY), LASI W1 | **FH of CVD (heart disease/stroke, 1st-degree) 11.61% weighted** (6,360/58,673), 45+; self-reported CVD 9.2% with FH vs 4.8% without | full text, Tables 1-2 — **supersedes the "CVD FH not supported" status** |
| Muhammad, Irshad & Rajan, SSM Pop Health 2022, doi:10.1016/j.ssmph.2022.101175, LASI 60+ | FH hypertension 19.48%, FH diabetes 14.69% (n=31,464, 60+) | abstract only — weighting/definitions not verified |
| CPCB National AQI (launched 17 Oct 2014; via ies.gov.in Arthapedia) | 6 bands 0-50…401-500; 8 pollutants; AQI only if ≥3 pollutants incl. PM2.5 or PM10; sub-index needs ≥16 h | secondary government page; primary CPCB PDF not fetched (NIUA mirror refused connection) |
| data.gov.in "Real time AQI from various locations" | live instrument data, unreviewed, no API | page 403 to fetch; search snippet only; **licence not confirmed** |
| Urban Emissions compilation of CPCB daily bulletins 2015-2023 | city-day AQI + category + dominant pollutant; 22 cities (2015) → 271 (2023) | page fetched; **no licence stated** |
| GODL-India | royalty-free commercial use with attribution (applies to data.gov.in datasets) | secondary (OSM wiki); gazette PDF not fetched |

## 4. Family history — design proposal (requires approval)

Problem: `family_history` null for 100%. Evidence now exists **for ages 45+ only**, self-reported,
from LASI (a different survey from INDIAB, which supplies our diabetes/hypertension labels).

Candidate schema (additive, v0.9): `family_history: {cvd: bool|null, diabetes: bool|null,
hypertension: null, relation_detail: null, source: str, coverage_note: str}`; explicit `null` for
age < 45 (no evidence) — never `false`.

Candidate generation, per category:
- **FH CVD (45+):** Bernoulli(0.1161). The dataset has no CVD outcome field, so no generated
  association is lost. Cleanest candidate.
- **FH diabetes (45+), two options:**
  (a) independent Bernoulli(0.1433) — erases the observed ~3× association with diabetes;
  (b) conditional on our diabetes label via Bayes from LASI's own figures:
  P(FH|D)=0.1433·0.278/0.1187=**0.336**, P(FH|¬D)=0.1433·0.722/0.8813=**0.117**
  (check: implied P(D)=11.87% ≈ LASI's reported 11.9%). Engineering assumption: transfers an
  association measured on *self-reported diagnosed* diabetes onto INDIAB's *OGTT-defined* label.
- **FH hypertension:** NOT ready — abstract-level, 60+ only. Keep null.
- Age shape caveat: LASI's weighted 45+ figures reflect a real age pyramid; ours is uniform 45-89.

Validation: binomial vs cited rates in 45+; null-rate = share <45 exactly; for (b) recover
P(D|FH)≈0.278 / P(D|¬FH)≈0.092 within sampling error.
Effort: small (one sampler appended at end of draw order, as BP was).

## 5. AQI — feasibility assessment (recommend: keep unavailable for now)

AQI is a property of a place and time, not a person. The current dataset has **neither a
city/district nor a real observation date** (every measurement date = 2026-09-26, the generation
date), and urban/rural is independent of state (§2.1). Any AQI attached today would be
manufactured precision. Minimum prerequisites, each an approval item:
1. A synthetic **district/city** assignment (needs a Census 2011 district/town population table and
   state×urban/rural joint shares — new data download).
2. A defined **exposure window** semantics (e.g. "annual mean for calendar year Y"), since record
   dates are synthetic.
3. A **licensed source**: CPCB bulletin archive / CCR portal, licence unconfirmed; the Urban
   Emissions compilation states no licence. Coverage 22→271 cities: rural residents (~69%) and
   most districts have no monitor.

Minimum schema if approved (v0.9+): `environment.aqi: {value: int|null, category: CPCB band|null,
scale: "CPCB_NAQI_2014", geography_ref, geography_level: "city"|"state", exposure_period,
source_id, provenance_status: "observed"|"unavailable", unavailable_reason}`. Records without a
monitored city must carry `provenance_status="unavailable"`, never an imputed value.

## 6. Decisions requiring human approval

1. Family history: populate FH-CVD for 45+ (Bernoulli 11.61%)? FH-diabetes for 45+: option (a) or (b)?
2. Whether to add a synthetic district/city field (prerequisite for AQI) and download Census district tables.
3. AQI source + licence (requires a human to confirm CPCB/data.gov.in terms for commercial use).
4. Whether to age-condition hypertension (would address §2.2) — needs a new evidence search (NFHS-5 age-band prevalence).
5. Whether to replace independent urban/rural with Census state×urban/rural shares (D010 revisit).
6. Carried forward unchanged: PP floor (#4), encounters container (#3), hyperlipidemia diagnosis.

## 7. Recommended sequence

M9-2 (after approval of item 1): FH v0.9 pilot on 10 → 100 → 1,000 fresh records in
`outputs/m9/`, never touching `outputs/m5` or `outputs/m8`. AQI stays `unavailable` until items 2-3
are resolved.
