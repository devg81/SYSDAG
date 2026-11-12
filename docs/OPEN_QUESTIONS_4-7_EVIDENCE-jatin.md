# v0.10 open questions 4–7: evidence search results -jatin

**Author:** -jatin, 2026-11-12. Research only: **no generator change was made.**
Source questions: `docs/V010_CHANGE_REPORT.md` §Open questions 4–7.

## Summary

| Q | Topic | Result | Change made |
|---|---|---|---|
| 4 | Onset curves (INDIAB-17 by age) | INDIAB-17 age table not reachable (Lancet, paywalled). Found LASI and NFHS-4/SAGE hypertension prevalence by age × sex (35+/45+). **The early-onset skew is a model assumption, not a data-source problem.** | None |
| 5 | BP at 55+ (LASI means by age) | The LASI India Report (Table 9.1 / Fig 9.1) has them, but the PDF is >10 MB and could not be fetched. No secondary source quotes the means. | None (download needs approval) |
| 6 | Indian lipid correlation matrix; urban/rural lipids | **None found** (CARRS, INDIAB, regional studies report prevalences and means only). Urban/rural TC gap exists only in INDIAB phase I (4 regions). | None |
| 7 | HbA1c in untreated / undiagnosed diabetes | LASI (Lancet Glob Health 2025, DBS HbA1c, 45+): **45.7%** of diagnosed diabetics have HbA1c <7%. No HbA1c distribution for undiagnosed people is published. | None |

**New, more important finding: hypertension and diabetes flags have no age gradient.**
See the last section. It needs a human decision.

## Q4: onset curves
- **Why the skew happens:** onset is drawn from the CDF P(a)/P(A) on [20, A]. The
  NFHS-5 BP curve gives P(20) ≈ 8.5%, so for a 65-year-old hypertensive with
  P(65) ≈ 45%, about 19% of onsets fall at ~20. Every Indian age curve (NFHS-5,
  INDIAB-17, LASI) has non-zero prevalence in the 20s, so **swapping in INDIAB-17
  would not remove the skew.** The real cause is assumption (1) in
  `onset_model` (prevalence ≈ cumulative incidence, no remission or measurement
  noise in young single-visit BP readings).
- **Found (tier A, observed):** Mohanty et al., BMC Public Health 2022;22:1524,
  Table 2. Predicted hypertension prevalence (%, ≥140/90 or on treatment):

  | Age | NFHS-4/SAGE M | F | LASI W1 M | F |
  |---|---|---|---|---|
  | 35–39 | 23.37 | 17.61 | – | – |
  | 40–44 | 29.17 | 23.66 | – | – |
  | 45–49 | 31.23 | 29.37 | 32.12 | 28.21 |
  | 50–54 | 30.51 | 37.61 | 36.87 | 38.65 |
  | 55–59 | 34.21 | 42.29 | 38.44 | 41.88 |
  | 60–64 | 37.21 | 43.50 | 44.40 | 48.06 |
  | 65–69 | 38.81 | 50.71 | 48.36 | 53.88 |
  | 70+ | 46.59 | 51.43 | 46.96 | 60.14 |

- **Not done:** an evidence-free fix to the young end (for example, inventing an
  incidence curve). Options for a human: accept and disclose (current state);
  start the curve at a later "zero-prevalence" age (an assumption); or use an
  incidence-based model if an Indian incidence cohort is found.

## Q5: BP above 55
- The LASI Wave 1 India Report (2020), Table 9.1 and Figure 9.1, gives mean SBP/DBP
  by age and sex for 45+. The PDF (`citizenshealth.in/.../LASI_India_Report_2020.pdf`)
  exceeds the fetch limit, and the fact-sheet hosts refused connections.
- **Next step:** with approval, download the report PDF (~10+ MB, IIPS/LASI, public)
  to a scratch folder and extract Table 9.1. That would replace the SBP
  extrapolation above 54/49 (D022) with observed means.

## Q6: lipid correlations and conditioning
- No Indian population study publishing pairwise TC/TG/HDL/LDL correlations was
  found. Searched INDIAB, CARRS (16,287 urban adults; reports prevalence and assay
  methods only), and regional studies. The D022 calibrated latent correlations stay.
- The urban/rural TC gap (~13 mg/dL) is from ICMR-INDIAB phase I (4 regions,
  n=2,042). Adopting it would mix a regional study into the national INDIAB-17
  calibration and require re-solving the joint model, so it is **not adopted**
  (project rule: do not blend non-identical studies without a decision).

## Q7: HbA1c in untreated / undiagnosed diabetes
- Sekher et al., Lancet Glob Health 2025;13(9):e1543–52 (LASI, DBS HbA1c, ages 45+):
  45.7% (95% CI 44.3–47.2) of previously diagnosed diabetics had HbA1c <7%; 43.0%
  among all diabetics. No mean, SD or category distribution is reported for any
  subgroup.
- The generator uses INDIAB-13's 36.3% (self-reported diabetics, 20+). LASI's 45.7%
  is a different population (45+) and assay (DBS), so it is recorded as a
  cross-check and **not blended**.
- Undiagnosed diabetics keep the borrowed distribution, tagged confidence low.
  No source was found that improves it.

## Key finding: no age gradient in hypertension or diabetes (needs a decision)
Measured on 20,000 generated records (current generator, seeds 43–20042):

| Age | HTN generated M / F | LASI M / F | Diabetes generated M / F |
|---|---|---|---|
| 20–34 | 34.3 / 36.4 | – | 10.8 / 12.7 |
| 35–44 | 35.7 / 35.5 | – | 11.2 / 11.0 |
| 45–49 | 34.8 / 34.4 | 32.1 / 28.2 | 11.5 / 11.8 |
| 55–59 | 33.9 / 38.1 | 38.4 / 41.9 | 14.4 / 11.7 |
| 65–69 | 37.1 / 34.0 | 48.4 / 53.9 | 12.3 / 13.5 |
| 70–89 | 35.9 / 35.7 | 47.0 / 60.1 | 11.0 / 12.4 |

- `risk_factors.hypertension` / `diabetes` are unconditioned national Bernoulli
  draws (35.5% / 11.4%, INDIAB-17). This was a deliberate M2C/M2D decision (D006),
  made because no INDIAB-17 age table was available. The result is that young
  adults are too often hypertensive and older adults not often enough.
- The repo **already holds an age × sex hypertension curve** (the NFHS-5 BP model
  the onset model reads). LASI and NFHS-4/SAGE above add observed 35+/45+ points.
  LASI also has diabetes by age.
- **Option:** age × sex-condition both flags, calibrated so the national marginal
  under the generator's age distribution still equals INDIAB-17's 35.5% / 11.4%.
  This would be a v0.13 generator change. It would also shift BP, medications,
  onset, HbA1c and the D024 risk tiers (all depend on the two flags). The D023
  hyperlipidemia flag would not change, because it comes from lipids. It revisits
  D006, so it is the user's decision.

## Sources
- Mohanty P et al. BMC Public Health 2022;22:1524 (PMC9364494): https://link.springer.com/article/10.1186/s12889-022-13949-5
- Sekher TV et al. Lancet Glob Health 2025 (PMC12397963), via Europe PMC: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12397963/fullTextXML
- ICMR-INDIAB-17, Lancet Diabetes Endocrinol 2023;11(7):474–89: https://www.thelancet.com/journals/landia/article/PIIS2213-8587(23)00163-8/abstract
- LASI Wave 1 India Report 2020 (not readable here): https://www.citizenshealth.in/wp-content/uploads/2021/02/LASI_India_Report_2020.pdf
- CARRS dyslipidaemia (NMJI 2020): https://nmji.in/prevalence-of-dyslipidaemia-and-factors-associated-with-dyslipidaemia-among-south-asian-adults-the-center-for-cardiometabolic-risk-reduction-in-south-asia-cohort-study/
