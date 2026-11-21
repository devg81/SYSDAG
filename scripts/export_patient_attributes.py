"""Patient-wise attribute sheet: everything one synthetic patient record contains.

Builds docs/PATIENT_ATTRIBUTES.xlsx from the latest review samples
(review_samples_v013/, schema v0.13 -- the same record structure used for the
full generated population):

  * "All Attributes"  -- one row per attribute (age, sex, AQI, BP, diagnoses ...),
                          grouped by section, one column per patient, plus
                          "what it means" and "how it is decided".
  * one "PAT_xxxxxx" sheet per patient -- a readable patient card.

Usage:
    python scripts/export_patient_attributes.py [samples_dir] [output.xlsx]
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
NOT_MODELLED = "Not recorded (not modelled yet)"


# ---------------------------------------------------------------- helpers
def yn(v):
    return "-" if v is None else ("Yes" if v else "No")


def dx(r, code):
    return next((d for d in r.get("diagnoses") or [] if d["code"] == code), None)


def med(r, cls):
    return next((m for m in r.get("medications") or [] if m["drug_class"] == cls), None)


def lab(r, analyte):
    return next((l for l in r.get("labs") or [] if l["analyte"] == analyte), None)


def interp(r, definition):
    return next((i for i in r.get("lipid_interpretations") or [] if i["definition"] == definition), None)


def g(obj, key, default="-"):
    if obj is None:
        return default
    v = obj.get(key)
    return default if v is None else v


def join(xs):
    return ", ".join(map(str, xs)) if xs else "None"


def diag_rows(code, label):
    return [
        ("Diagnosis history", f"{label} - diagnosed?", "", lambda r: yn(dx(r, code) is not None),
         f"Has the patient got {label.lower()}? Copied from the risk-factor flag (never decided separately)."),
        ("Diagnosis history", f"{label} - age at onset", "years", lambda r: g(dx(r, code), "age_at_onset_years"),
         "Modelled age when the condition started, from the Indian age-prevalence curve. Always <= current age."),
        ("Diagnosis history", f"{label} - onset date", "date", lambda r: g(dx(r, code), "onset_date"),
         "Assessment date minus (age - onset age)."),
        ("Diagnosis history", f"{label} - date diagnosed by doctor", "date",
         lambda r: NOT_MODELLED if dx(r, code) else "-",
         "Not modelled: about half of Indian cases are undiagnosed, no evidence for diagnosis timing."),
        ("Diagnosis history", f"{label} - onset confidence", "", lambda r: g(dx(r, code), "onset_confidence"),
         "Onset is modelled, not observed, so confidence is low."),
    ]


def med_rows(cls, label, cond):
    return [
        ("Medications", f"{label} medicine", "",
         lambda r: (f"Yes ({g(med(r, cls), 'current_status')})" if med(r, cls) else
                    ("No (untreated)" if dx(r, cond) else "No (no diagnosis)")),
         f"Only given if the patient has {cond}; then drawn from the ICMR-NNMS national treatment rate "
         f"({'14.5%' if cls == 'antihypertensive' else '36.1%'}). Drug class only, no drug names."),
        ("Medications", f"{label} - start / stop date", "date",
         lambda r: NOT_MODELLED if med(r, cls) else "-", "No per-patient evidence for when treatment starts."),
    ]


def timeline_text(r):
    names = {d["diagnosis_id"]: d["code"] for d in r.get("diagnoses") or []}
    out = []
    for t in sorted(r.get("clinical_timeline") or [], key=lambda t: t["date"]):
        ev = t["event_type"].replace("_", " ")
        if t.get("reference_id") in names:
            ev += f" ({names[t['reference_id']]})"
        out.append(f"{t['date']}: {ev}")
    return "\n".join(out)


def aqi_value(r):
    a = r.get("air_quality") or {}
    return a.get("aqi") if a.get("aqi") is not None else f"Not available ({a.get('unavailable_reason')})"


ECG_CLASSES = {"NORM": "Normal", "MI": "Myocardial infarction", "STTC": "ST/T change",
               "CD": "Conduction disturbance", "HYP": "Hypertrophy"}

# (section, attribute, unit, extractor(record) -> value, what it means / how decided)
ROWS = [
    # --- identity
    ("Patient identity", "Patient ID", "", lambda r: r["patient_id"], "Synthetic ID. Not a real patient."),
    ("Patient identity", "Record type", "", lambda r: "Synthetic (not a real patient)", "Every record is generated."),
    ("Patient identity", "Schema version", "", lambda r: r["provenance"]["schema_version"], "Version of the record format."),
    # --- demographics
    ("Demographics", "Age", "years", lambda r: r["demographics"]["age"], "Uniform 20-89 years."),
    ("Demographics", "Sex", "", lambda r: {0: "Male", 1: "Female"}.get(r["demographics"]["sex"], "-"),
     "From Census of India 2011 national sex ratio."),
    ("Demographics", "State", "", lambda r: r["demographics"]["state"], "From Census 2011 state population share."),
    ("Demographics", "Urban / Rural", "", lambda r: r["demographics"]["urban_rural"].title(),
     "From Census 2011 urban share of that state."),
    ("Demographics", "Height", "cm", lambda r: r["demographics"]["height_cm"] or NOT_MODELLED,
     "No Indian national height data (mean + spread) found."),
    ("Demographics", "Weight", "kg", lambda r: r["demographics"]["weight_kg"] or NOT_MODELLED,
     "Needs height first."),
    # --- environment
    ("Environment (air quality)", "AQI (state annual average)", "AQI", aqi_value,
     "2023 CPCB average AQI of the patient's STATE. Not the patient's own exposure."),
    ("Environment (air quality)", "AQI category", "", lambda r: g(r.get("air_quality"), "category"),
     "CPCB scale: Good / Satisfactory / Moderate / Poor / Very Poor / Severe."),
    ("Environment (air quality)", "AQI year", "", lambda r: g(r.get("air_quality"), "reference_year"), ""),
    ("Environment (air quality)", "Monitoring stations / cities in state", "",
     lambda r: (f"{g(r.get('air_quality'), 'stations')} stations / {g(r.get('air_quality'), 'cities')} cities"
                if g(r.get("air_quality"), "aqi", None) is not None else "-"),
     "Mostly urban stations, so rural patients may differ."),
    # --- risk factors
    ("Lifestyle & risk factors", "BMI", "kg/m²", lambda r: r["risk_factors"]["bmi"],
     "Drawn by sex from Indian survey BMI categories."),
    ("Lifestyle & risk factors", "Smoking status", "", lambda r: r["risk_factors"]["smoking_status"].title(),
     "Drawn by sex (never / current)."),
    ("Lifestyle & risk factors", "Hypertension (high BP)", "", lambda r: yn(r["risk_factors"]["hypertension"]),
     "Chance depends on age and sex (NFHS-5 under 45, LASI 45+)."),
    ("Lifestyle & risk factors", "Diabetes", "", lambda r: yn(r["risk_factors"]["diabetes"]),
     "Chance depends on age (ICMR-NNMS under 45, LASI 45+)."),
    ("Lifestyle & risk factors", "Hyperlipidemia (high cholesterol)", "",
     lambda r: yn(r["risk_factors"]["hyperlipidemia"]),
     "Decided from the patient's own lipid test (NCEP ATP III rule)."),
    # --- family history
    ("Family history", "Diabetes in parent / sibling", "", lambda r: yn(g(r.get("family_history"), "diabetes", None)),
     "LASI survey rates; more likely if the patient is diabetic."),
    ("Family history", "Heart disease or stroke in parent / sibling", "",
     lambda r: yn(g(r.get("family_history"), "cardiovascular_disease", None)), "LASI survey rates."),
    ("Family history", "How family history was decided", "",
     lambda r: {"lasi_observed_45_plus": "LASI observed rate (age 45+)",
                "parent_simulation_calibrated": "Modelled from parents' ages (age 20-44)"}.get(
         g(r.get("family_history"), "derivation"), g(r.get("family_history"), "derivation")), ""),
    # --- vitals
    ("Vitals (health check)", "Blood pressure - systolic", "mmHg",
     lambda r: g(r.get("blood_pressure"), "systolic_mm_hg"), "NFHS-5 by age and sex; kept consistent with hypertension yes/no."),
    ("Vitals (health check)", "Blood pressure - diastolic", "mmHg",
     lambda r: g(r.get("blood_pressure"), "diastolic_mm_hg"), ""),
    ("Vitals (health check)", "BP measured on", "date", lambda r: g(r.get("blood_pressure"), "measured_at"), ""),
    ("Vitals (health check)", "BP confidence", "", lambda r: g(r.get("blood_pressure"), "confidence"),
     "Low if the patient is older than the survey's age range (extrapolated)."),
    # --- labs
    ("Lab results", "HbA1c (blood sugar, 3-month)", "%", lambda r: g(lab(r, "HbA1c"), "value"),
     "ICMR-INDIAB; depends on diabetes yes/no, age and sex."),
    ("Lab results", "HbA1c confidence", "", lambda r: g(lab(r, "HbA1c"), "confidence"),
     "Low for untreated diabetics (borrowed distribution)."),
    ("Lab results", "Total cholesterol", "mg/dL", lambda r: g(r.get("lipid_panel"), "total_cholesterol_mg_dl"),
     "Drawn jointly with TG and HDL (ICMR-INDIAB)."),
    ("Lab results", "LDL (bad cholesterol)", "mg/dL", lambda r: g(r.get("lipid_panel"), "ldl_mg_dl"),
     "Calculated with the Friedewald formula from TC, HDL, TG."),
    ("Lab results", "HDL (good cholesterol)", "mg/dL", lambda r: g(r.get("lipid_panel"), "hdl_mg_dl"), ""),
    ("Lab results", "Triglycerides", "mg/dL", lambda r: g(r.get("lipid_panel"), "triglycerides_mg_dl"), ""),
    ("Lab results", "Lab date", "date", lambda r: g(lab(r, "HbA1c"), "measured_at"), ""),
    # --- lipid interpretation
    ("Cholesterol interpretation", "Dyslipidemia (NCEP ATP III)", "",
     lambda r: yn(g(interp(r, "NCEP_ATP_III"), "dyslipidemia", None)), "Rule applied to the lipid values."),
    ("Cholesterol interpretation", "Abnormal parts (NCEP ATP III)", "",
     lambda r: join(g(interp(r, "NCEP_ATP_III"), "components_abnormal", [])), ""),
    ("Cholesterol interpretation", "Dyslipidemia (Lipid Association of India)", "",
     lambda r: yn(g(interp(r, "LAI_2020"), "dyslipidemia", None)), "Indian guideline (LAI 2020)."),
    ("Cholesterol interpretation", "Heart-risk category (LAI)", "",
     lambda r: str(g(interp(r, "LAI_2020"), "risk_category")).replace("_", " ").title(),
     "Rule-based from age, smoking, BP, low HDL, diabetes. May under-estimate."),
    ("Cholesterol interpretation", "LDL target (LAI)", "mg/dL", lambda r: g(interp(r, "LAI_2020"), "ldl_goal_mg_dl"), ""),
    ("Cholesterol interpretation", "LDL above target?", "", lambda r: yn(g(interp(r, "LAI_2020"), "ldl_above_goal", None)), ""),
    ("Cholesterol interpretation", "Risk factors counted (LAI)", "",
     lambda r: join([x.replace("_", " ") for x in g(interp(r, "LAI_2020"), "risk_factors_counted", [])]), ""),
    # --- diagnosis history
    *diag_rows("hypertension", "Hypertension"),
    *diag_rows("diabetes", "Diabetes"),
    # --- medical history
    ("Medical history", "Past / chronic conditions", "",
     lambda r: join([f"{m['description'].title()} ({m['category'].replace('_', ' ')})"
                     for m in r.get("medical_history") or []]),
     "Points to the diagnoses above (not decided separately)."),
    ("Medical history", "Heart attack / stroke / procedures", "", lambda r: NOT_MODELLED,
     "Reserved in the format; no evidence source yet."),
    # --- medications
    *med_rows("antihypertensive", "BP-lowering (antihypertensive)", "hypertension"),
    *med_rows("antidiabetic", "Sugar-lowering (antidiabetic)", "diabetes"),
    ("Medications", "Statin / aspirin", "", lambda r: NOT_MODELLED, "No Indian treatment-rate evidence."),
    # --- ECG / echo
    ("ECG", "ECG findings", "",
     lambda r: join([f"{c} - {ECG_CLASSES.get(c, c)}" for c in g(r.get("ecg"), "superclasses", [])]) if g(r.get("ecg"), "superclasses", []) else "No label",
     "Linked real PTB-XL ECG record (labels only)."),
    ("ECG", "ECG record ID (PTB-XL)", "", lambda r: g(r.get("ecg"), "ecg_id"), ""),
    ("ECG", "ECG format", "",
     lambda r: f"12-lead, {g(r.get('ecg'), 'sampling_hz')} Hz, {g(r.get('ecg'), 'signal_shape', ['-'])[0]} samples", ""),
    ("ECG", "ECG waveform attached?", "", lambda r: yn(g(r.get("ecg"), "signal_available", None)),
     "Metadata only for now; generated waveforms are a later milestone."),
    ("Echo", "Echocardiography", "", lambda r: r.get("echo") or NOT_MODELLED, "No usable source yet."),
    # --- encounters / timeline
    ("Visits & timeline", "Visits (encounters)", "",
     lambda r: join([f"{e['date']}: {e['encounter_type'].replace('_', ' ')}" for e in r.get("encounters") or []]),
     "One baseline check-up holding BP + labs. Not a real hospital visit."),
    ("Visits & timeline", "Measured at that visit", "",
     lambda r: join([{"blood_pressure": "Blood pressure", "lipid_panel": "Lipid panel",
                      "labs.HbA1c": "HbA1c"}.get(m, m)
                     for m in (r.get("encounters") or [{}])[0].get("recorded_measurements", [])]), ""),
    ("Visits & timeline", "Clinical timeline", "", timeline_text, "All dated events, oldest first."),
    # --- quality
    ("Record quality", "Structure valid?", "", lambda r: yn(r["validation"]["validated"]), "Checked by the structural validator."),
    ("Record quality", "Clinically consistent?", "",
     lambda r: yn(r["validation"].get("clinical_consistency", {}).get("valid")),
     "e.g. diabetic has diabetic-range HbA1c, BP matches hypertension flag."),
    ("Record quality", "Warnings", "",
     lambda r: join(r["validation"].get("clinical_consistency", {}).get("warnings", [])), ""),
    ("Record quality", "Generated on", "", lambda r: r["provenance"]["generated_at"][:10], ""),
    ("Record quality", "Random seed", "", lambda r: r["provenance"]["random_seed"], "Re-running with this seed gives the same patient."),
    ("Record quality", "Data sources used", "", lambda r: "\n".join(r["provenance"]["source_datasets"]), ""),
]


def summary(r):
    d = r["demographics"]
    sex = {0: "male", 1: "female"}.get(d["sex"], "")
    conds = [x["code"] for x in r.get("diagnoses") or []]
    return (f"{r['patient_id']} - {round(d['age'])}-year-old {sex}, {d['urban_rural']} {d['state']}; "
            f"conditions: {', '.join(conds) if conds else 'none'} (SYNTHETIC)")


# ---------------------------------------------------------------- styling
HEAD = PatternFill("solid", fgColor="1F4E78")
SECTION = PatternFill("solid", fgColor="DDEBF7")
WHITE_BOLD = Font(bold=True, color="FFFFFF")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def write_table(ws, header, groups, widths, title=None):
    """groups: list of (section, [row values]) -- a coloured section header row precedes each group."""
    row = 1
    if title:
        ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=13)
        row = 3
    for c, h in enumerate(header, 1):
        cell = ws.cell(row=row, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEAD, WHITE_BOLD, WRAP, BOX
    ws.freeze_panes = ws.cell(row=row + 1, column=2)
    for section, rows in groups:
        row += 1
        for c in range(1, len(header) + 1):
            ws.cell(row=row, column=c).fill = SECTION
            ws.cell(row=row, column=c).border = BOX
        ws.cell(row=row, column=1, value=section).font = Font(bold=True)
        for vals in rows:
            row += 1
            for c, v in enumerate(vals, 1):
                cell = ws.cell(row=row, column=c, value=v)
                cell.alignment, cell.border = WRAP, BOX
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def grouped(rows):
    out = []
    for r in rows:
        if not out or out[-1][0] != r[0]:
            out.append((r[0], []))
        out[-1][1].append(r[1:])
    return out


def main(samples_dir: Path, out_path: Path):
    records = [json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(samples_dir / "*.json")))]
    records.sort(key=lambda r: r["patient_id"])
    wb = Workbook()

    # Sheet 1: all attributes, patients side by side
    ws = wb.active
    ws.title = "All Attributes"
    table = []
    for sec, attr, unit, fn, note in ROWS:
        table.append((sec, attr, unit, *[fn(r) for r in records], note))
    header = ["Attribute", "Unit", *[r["patient_id"] for r in records], "What it means / how it is decided"]
    write_table(ws, header, grouped(table), [40, 9, *[26] * len(records), 60],
                title=f"What one synthetic patient record contains - {len(ROWS)} attributes, "
                      f"{len(records)} example patients (schema v{records[0]['provenance']['schema_version']})")
    ws.cell(row=2, column=1, value="All patients are SYNTHETIC. The full generated population uses this same record "
                                   "structure.").font = Font(italic=True)

    # One card per patient
    for r in records:
        ws = wb.create_sheet(r["patient_id"])
        rows = [(sec, attr, fn(r), unit, note) for sec, attr, unit, fn, note in ROWS]
        write_table(ws, ["Attribute", "Value", "Unit", "What it means / how it is decided"],
                    grouped(rows), [40, 34, 9, 60], title=summary(r))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"wrote {out_path} | patients={len(records)} attributes={len(ROWS)} sections={len(grouped(table))}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(Path(a[0]) if a else ROOT / "review_samples_v013",
         Path(a[1]) if len(a) > 1 else ROOT / "docs/PATIENT_ATTRIBUTES.xlsx")
