"""Export every attribute of the generated synthetic patient data into ONE Excel file.

Reads all generated patient records present on this machine:
  * review_samples_v09 .. review_samples_v013   (5 patients x 5 schema versions)
  * validation/pilot_50_records/output/patient_records_50.json   (50 records, v0.8)
  * validation/pilot_50_records/input/original_records/*.json    (same 50, v0.7)
and the 100K full-dataset audit (docs/M9_FIELD_COMPLETENESS_AUDIT.json).

The frozen 100K dataset itself (outputs/m9/100k_patients_v09/) is gitignored and
not required: its per-field completeness comes from the audit JSON.

Usage:
    python scripts/export_data_attributes.py [output.xlsx]
Default output: docs/GENERATED_DATA_ATTRIBUTES.xlsx
"""

from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from schemas import patient_schema as S  # noqa: E402

VERSION_ORDER = ["0.7", "0.8", "0.9", "0.10", "0.11", "0.12", "0.13"]

# How each attribute is produced. Keys are generic paths (list items as "[]").
# (section, description, unit, how_generated, allowed_values)
ATTR = {
    "patient_id": ("Patient metadata", "Synthetic patient identifier (PAT_NNNNNN). Never a real patient ID.", "", "Structural (sequence)", "PAT_ + 6 digits"),
    "demographics.age": ("Demographics", "Age in years (2 decimals from v0.10).", "years", "Sampled (uniform 20-89, configs/indian_population.yaml)", "20-89"),
    "demographics.sex": ("Demographics", "Sex, PTB-XL encoding.", "", "Sampled (Census 2011 national marginal)", "0 = male, 1 = female"),
    "demographics.height_cm": ("Demographics", "Height. NOT MODELLED: no Indian national mean+SD of adult height by sex located.", "cm", "Not modelled (always null)", ""),
    "demographics.weight_kg": ("Demographics", "Weight. NOT MODELLED (derivable from BMI once height exists).", "kg", "Not modelled (always null)", ""),
    "demographics.state": ("Demographics", "Indian state / UT of residence.", "", "Sampled (Census 2011 state population share)", "Indian states/UTs"),
    "demographics.urban_rural": ("Demographics", "Urban or rural residence.", "", "Sampled (Census 2011 urban share by state)", "urban, rural"),
    "risk_factors.bmi": ("Risk factors", "Body-mass index.", "kg/m^2", "Sampled (by sex, Indian survey category rates)", ""),
    "risk_factors.smoking_status": ("Risk factors", "Smoking status.", "", "Sampled (by sex)", ", ".join(sorted(S.SMOKING_STATUSES))),
    "risk_factors.hypertension": ("Risk factors", "Hypertension flag. v0.13: age x sex prevalence curve (NFHS-5 <45 / LASI 45+); earlier: flat national rate.", "", "Sampled (Bernoulli on age x sex curve)", "true, false"),
    "risk_factors.diabetes": ("Risk factors", "Diabetes flag. v0.13: age prevalence curve (ICMR-NNMS <45 / LASI 45+); earlier: flat national rate.", "", "Sampled (Bernoulli on age curve)", "true, false"),
    "risk_factors.hyperlipidemia": ("Risk factors", "Hyperlipidemia flag. v0.11+: DERIVED = NCEP_ATP_III dyslipidemia verdict of own lipid panel (D023); before v0.11 an independent draw.", "", "Derived (from lipid_panel, v0.11+)", "true, false"),
    "family_history": ("Family history", "Family-history block. null in v0.7/v0.8 (not yet modelled).", "", "Container", ""),
    "family_history.diabetes": ("Family history", "Diabetes in a first-degree relative.", "", "Sampled (LASI Wave 1; conditional on own diabetes via OR 3.80)", "true, false"),
    "family_history.cardiovascular_disease": ("Family history", "Heart disease or stroke in a first-degree relative.", "", "Sampled (LASI Wave 1)", "true, false"),
    "family_history.derivation": ("Family history", "How family history was produced: LASI observed (45+) or model-derived parent simulation (20-44).", "", "Metadata", "lasi_observed_45_plus, model_derived_*"),
    "medical_history": ("Medical history", "List of medical-history entries (references to diagnoses).", "", "Container", ""),
    "medical_history[].category": ("Medical history", "Entry category; only chronic_condition is generated.", "", "Derived (from diagnoses)", ", ".join(sorted(S.MEDICAL_HISTORY_CATEGORIES))),
    "medical_history[].description": ("Medical history", "Condition name, mirrors the referenced diagnosis code.", "", "Derived (from diagnoses)", ", ".join(sorted(S.DIAGNOSIS_CODES))),
    "medical_history[].diagnosis_id": ("Medical history", "Reference to diagnoses[].diagnosis_id.", "", "Reference", "PAT_NNNNNN_DXnn"),
    "medical_history[].event_date": ("Medical history", "Mirrors diagnosed_date (not modelled, null).", "date", "Not modelled (always null)", ""),
    "diagnoses": ("Diagnoses", "List of diagnoses: 1:1 promotion of hypertension/diabetes risk-factor flags (D015).", "", "Container", ""),
    "diagnoses[].diagnosis_id": ("Diagnoses", "Diagnosis ID.", "", "Structural", "PAT_NNNNNN_DXnn"),
    "diagnoses[].code": ("Diagnoses", "Condition (plain text, not ICD).", "", "Derived (from risk_factors flag)", ", ".join(sorted(S.DIAGNOSIS_CODES))),
    "diagnoses[].diagnosed_date": ("Diagnoses", "Date of diagnosis. NOT MODELLED (about half of cases are undiagnosed).", "date", "Not modelled (always null)", ""),
    "diagnoses[].source": ("Diagnoses", "Provenance tag.", "", "Metadata", "derived_from_risk_factors"),
    "diagnoses[].age_at_onset_years": ("Diagnoses", "Modelled age at onset (v0.10+), inverse-CDF on prevalence-by-age curve; always <= age.", "years", "Modelled (low confidence)", "<= demographics.age"),
    "diagnoses[].onset_date": ("Diagnoses", "Modelled onset date = assessment date - (age - onset age).", "date", "Derived (from age_at_onset_years)", "ISO 8601"),
    "diagnoses[].onset_derivation": ("Diagnoses", "Which onset curve was used.", "", "Metadata", "modeled_from_age_prevalence_curve_*"),
    "diagnoses[].onset_confidence": ("Diagnoses", "Confidence of modelled onset.", "", "Metadata", "low"),
    "medications": ("Medications", "List of medications (drug class only), gated on ICMR-NNMS treatment rates (14.5% / 36.1%).", "", "Container", ""),
    "medications[].medication_id": ("Medications", "Medication ID.", "", "Structural", "PAT_NNNNNN_MEDnn"),
    "medications[].drug_class": ("Medications", "Therapeutic class; no drug names generated.", "", "Derived (diagnosis + NNMS Bernoulli)", ", ".join(sorted(S.MEDICATION_DRUG_CLASSES))),
    "medications[].diagnosis_id": ("Medications", "Reference to the treated diagnosis.", "", "Reference", "PAT_NNNNNN_DXnn"),
    "medications[].current_status": ("Medications", "Status; only 'active' is produced.", "", "Structural", ", ".join(sorted(S.MEDICATION_STATUSES))),
    "medications[].start_date": ("Medications", "Start date. NOT MODELLED.", "date", "Not modelled (always null)", ""),
    "medications[].stop_date": ("Medications", "Stop date. NOT MODELLED.", "date", "Not modelled (always null)", ""),
    "medications[].source": ("Medications", "Provenance tag.", "", "Metadata", "derived_from_diagnosis_treatment_rate"),
    "labs": ("Labs", "List of lab results (HbA1c for every patient from v0.10; only non-diabetics before).", "", "Container", ""),
    "labs[].analyte": ("Labs", "Analyte name.", "", "Structural", ", ".join(S.ANALYTE_UNITS)),
    "labs[].unit": ("Labs", "Unit of the value.", "", "Structural", "; ".join(f"{k}={v}" for k, v in S.ANALYTE_UNITS.items())),
    "labs[].value": ("Labs", "Lab value. HbA1c conditional on diabetes label (ICMR-INDIAB-12 / -13).", "% (HbA1c)", "Sampled (conditional on diabetes, age, sex)", ""),
    "labs[].measured_at": ("Labs", "Measurement date (= baseline assessment date).", "date", "Structural", "ISO 8601"),
    "labs[].derivation": ("Labs", "Which distribution produced the value (v0.10+).", "", "Metadata", ""),
    "labs[].confidence": ("Labs", "Confidence of the value's distribution (v0.10+).", "", "Metadata", "moderate, low"),
    "blood_pressure.systolic_mm_hg": ("Blood pressure", "Systolic BP, conditional on hypertension label (NFHS-5 age-band x sex truncated normal).", "mmHg", "Sampled (conditional on hypertension)", ""),
    "blood_pressure.diastolic_mm_hg": ("Blood pressure", "Diastolic BP (SBP/DBP r = 0.7255).", "mmHg", "Sampled (conditional on hypertension)", ""),
    "blood_pressure.measured_at": ("Blood pressure", "Measurement date (= baseline assessment).", "date", "Structural", "ISO 8601"),
    "blood_pressure.age_band_source": ("Blood pressure", "NFHS-5 age band / extrapolation used.", "", "Metadata", ""),
    "blood_pressure.extrapolated_beyond_source_age_range": ("Blood pressure", "True when age exceeds NFHS-5 coverage (men >54, women >49).", "", "Metadata", "true, false"),
    "blood_pressure.source": ("Blood pressure", "Provenance tag.", "", "Metadata", "derived_conditional_on_hypertension_label"),
    "blood_pressure.confidence": ("Blood pressure", "'low' iff extrapolated, else 'moderate' (v0.10+).", "", "Metadata", "moderate, low"),
    "air_quality.aqi": ("Air quality", "2023 CPCB annual mean AQI of the patient's STATE (not personal exposure). null for 9 states/UTs.", "AQI", "Lookup (by state)", ""),
    "air_quality.category": ("Air quality", "CPCB National AQI category.", "", "Derived (from aqi)", ", ".join(S.AQI_CATEGORIES)),
    "air_quality.reference_year": ("Air quality", "Year of AQI data.", "", "Lookup", "2023"),
    "air_quality.stations": ("Air quality", "Number of monitoring stations in state.", "", "Lookup", ""),
    "air_quality.cities": ("Air quality", "Number of cities with stations.", "", "Lookup", ""),
    "air_quality.unavailable_reason": ("Air quality", "Why AQI is null (if it is).", "", "Lookup", ""),
    "air_quality.geographic_resolution": ("Air quality", "Resolution of the lookup.", "", "Metadata", "state"),
    "air_quality.monitoring_bias": ("Air quality", "Bias flag: state mean is urban-station weighted.", "", "Metadata", "state_mean_is_urban_station_weighted"),
    "air_quality.source": ("Air quality", "Data source.", "", "Metadata", ""),
    "encounters": ("Encounters", "List of encounters (null in v0.7).", "", "Container", ""),
    "encounters[].encounter_id": ("Encounters", "Encounter ID.", "", "Structural", "PAT_NNNNNN_ENCnn"),
    "encounters[].encounter_type": ("Encounters", "Only a structural baseline container; NOT a real healthcare visit.", "", "Structural", ", ".join(sorted(S.ENCOUNTER_TYPES))),
    "encounters[].date": ("Encounters", "Encounter date.", "date", "Structural", "ISO 8601"),
    "encounters[].patient_id": ("Encounters", "Owning patient.", "", "Reference", ""),
    "encounters[].recorded_measurements": ("Encounters", "Fields this encounter anchors (by reference).", "", "Structural", "blood_pressure, lipid_panel, labs.HbA1c"),
    "encounters[].source": ("Encounters", "Provenance tag.", "", "Metadata", "synthetic_structural_container"),
    "lipid_panel.ldl_mg_dl": ("Lipid panel", "LDL cholesterol, DERIVED via Friedewald (never sampled, never clamped from v0.10).", "mg/dL", "Derived (Friedewald)", ""),
    "lipid_panel.hdl_mg_dl": ("Lipid panel", "HDL cholesterol (joint trivariate normal from v0.10).", "mg/dL", "Sampled (joint TC/ln TG/HDL)", ""),
    "lipid_panel.triglycerides_mg_dl": ("Lipid panel", "Triglycerides (TG > 400 rejected and redrawn).", "mg/dL", "Sampled (joint TC/ln TG/HDL)", ""),
    "lipid_panel.total_cholesterol_mg_dl": ("Lipid panel", "Total cholesterol.", "mg/dL", "Sampled (joint TC/ln TG/HDL)", ""),
    "lipid_interpretations[].definition": ("Lipid interpretations", "Guideline used for the interpretation.", "", "Structural", "NCEP_ATP_III, LAI_2020"),
    "lipid_interpretations[].dyslipidemia": ("Lipid interpretations", "Dyslipidemia verdict computed from the panel.", "", "Derived (from lipid_panel)", "true, false"),
    "lipid_interpretations[].components_abnormal": ("Lipid interpretations", "Which lipid components are abnormal.", "", "Derived (from lipid_panel)", ", ".join(sorted(S.LIPID_COMPONENTS))),
    "lipid_interpretations[].source_citation": ("Lipid interpretations", "Citation for thresholds.", "", "Metadata", ""),
    "lipid_interpretations[].risk_category": ("Lipid interpretations", "LAI_2020 only (v0.12+): rule-based risk tier from modelled factors; can only under-estimate.", "", "Derived (rule-based)", ", ".join(sorted(S.LAI_RISK_CATEGORIES))),
    "lipid_interpretations[].ldl_goal_mg_dl": ("Lipid interpretations", "LAI_2020 only: LDL goal for the risk tier.", "mg/dL", "Derived (rule-based)", ""),
    "lipid_interpretations[].ldl_above_goal": ("Lipid interpretations", "LAI_2020 only: LDL above goal.", "", "Derived (rule-based)", "true, false"),
    "lipid_interpretations[].risk_factors_counted": ("Lipid interpretations", "LAI_2020 only: modelled risk factors counted.", "", "Derived (rule-based)", "age, current_smoking, hypertension, low_hdl, diabetes"),
    "lipid_interpretations[].risk_derivation": ("Lipid interpretations", "LAI_2020 only: derivation tag.", "", "Metadata", "rule_based_lai_modelled_factors_only"),
    "ecg.source": ("ECG", "ECG source dataset. Metadata only; no waveform attached (D003).", "", "Sampled (PTB-XL record pool)", "PTB-XL"),
    "ecg.ecg_id": ("ECG", "PTB-XL ecg_id of the linked record.", "", "Sampled (PTB-XL)", ""),
    "ecg.superclasses": ("ECG", "PTB-XL diagnostic superclasses.", "", "From PTB-XL", "NORM, MI, STTC, CD, HYP"),
    "ecg.strat_fold": ("ECG", "PTB-XL stratified fold.", "", "From PTB-XL", "1-10"),
    "ecg.sampling_hz": ("ECG", "Signal sampling rate.", "Hz", "From PTB-XL", "100"),
    "ecg.signal_shape": ("ECG", "Signal shape (samples x leads).", "", "From PTB-XL", "1000 x 12"),
    "ecg.filename": ("ECG", "PTB-XL record path.", "", "From PTB-XL", ""),
    "ecg.signal_available": ("ECG", "Whether a waveform is attached.", "", "Structural", "false (always, so far)"),
    "echo": ("Echo", "Echocardiography. NOT MODELLED (no usable source yet).", "", "Not modelled (always null)", ""),
    "clinical_timeline[].event_type": ("Clinical timeline", "Timeline event type.", "", "Structural", ", ".join(sorted(S.TIMELINE_EVENT_TYPES))),
    "clinical_timeline[].date": ("Clinical timeline", "Event date.", "date", "Structural", "ISO 8601"),
    "clinical_timeline[].reference_id": ("Clinical timeline", "ID of encounter/diagnosis the event indexes (v0.8+).", "", "Reference", ""),
    "provenance.schema_version": ("Provenance", "Schema version of the record.", "", "Metadata", ", ".join(VERSION_ORDER)),
    "provenance.generated_at": ("Provenance", "Generation timestamp (UTC).", "datetime", "Metadata", "ISO 8601"),
    "provenance.generator": ("Provenance", "Full description of how every field was generated (long text).", "", "Metadata", ""),
    "provenance.random_seed": ("Provenance", "Random seed for this record.", "", "Metadata", ""),
    "provenance.source_datasets": ("Provenance", "Source datasets that influenced generation.", "", "Metadata", ""),
    "validation.validated": ("Validation", "Passed structural validation.", "", "Validator output", "true, false"),
    "validation.validation_version": ("Validation", "Validator version.", "", "Validator output", ""),
    "validation.errors": ("Validation", "Structural validation errors.", "", "Validator output", ""),
    "validation.clinical_consistency.valid": ("Validation", "Passed clinical-consistency checks (v0.10+ stored in record).", "", "Validator output", "true, false"),
    "validation.clinical_consistency.errors": ("Validation", "Clinical-consistency errors.", "", "Validator output", ""),
    "validation.clinical_consistency.warnings": ("Validation", "Clinical-consistency warnings.", "", "Validator output", ""),
}

# List-of-dict fields flattened by a natural key instead of an index.
LIST_KEYS = {
    "labs": "analyte",
    "diagnoses": "code",
    "medical_history": "description",
    "medications": "drug_class",
    "lipid_interpretations": "definition",
}


def load_records() -> list[tuple[str, str, dict]]:
    """Return (dataset_label, source_file, record) for every generated record."""
    out = []
    for d in sorted(glob.glob(str(ROOT / "review_samples_v0*"))):
        for f in sorted(glob.glob(f"{d}/*.json")):
            out.append((Path(d).name, str(Path(f).relative_to(ROOT)), json.loads(Path(f).read_text(encoding="utf-8"))))
    pilot_out = ROOT / "validation/pilot_50_records/output/patient_records_50.json"
    if pilot_out.exists():
        for r in json.loads(pilot_out.read_text(encoding="utf-8")):
            out.append(("pilot_50_v08_output", str(pilot_out.relative_to(ROOT)), r))
    for f in sorted(glob.glob(str(ROOT / "validation/pilot_50_records/input/original_records/*.json"))):
        out.append(("pilot_50_v07_input", str(Path(f).relative_to(ROOT)), json.loads(Path(f).read_text(encoding="utf-8"))))
    order = {v: i for i, v in enumerate(VERSION_ORDER)}
    out.sort(key=lambda t: (-order.get(t[2]["provenance"]["schema_version"], -1), t[0], t[2]["patient_id"]))
    return out


def scalar(v):
    if isinstance(v, list):
        return "; ".join(json.dumps(x) if isinstance(x, (dict, list)) else str(x) for x in v)
    return v


def flatten(o, prefix="", row=None):
    """Flatten a record into {column: value}; lists of dicts keyed by LIST_KEYS or index."""
    row = {} if row is None else row
    if isinstance(o, dict):
        for k, v in o.items():
            flatten(v, f"{prefix}.{k}" if prefix else k, row)
    elif isinstance(o, list) and any(isinstance(i, dict) for i in o):
        row[f"{prefix}.count"] = len(o)
        key = LIST_KEYS.get(prefix)
        for i, item in enumerate(o):
            tag = item.get(key) if key and isinstance(item, dict) and item.get(key) else str(i)
            flatten(item, f"{prefix}[{tag}]", row)
    elif isinstance(o, list):
        if o == [] and prefix in LIST_KEYS | {"encounters": 0, "clinical_timeline": 0}:
            row[f"{prefix}.count"] = 0
        else:
            row[prefix] = scalar(o)
    else:
        row[prefix] = o
    return row


def generic_walk(o, path, hit):
    """Collect (generic_path -> list of leaf values) with list items collapsed to []."""
    if isinstance(o, dict):
        for k, v in o.items():
            generic_walk(v, f"{path}.{k}" if path else k, hit)
    elif isinstance(o, list) and any(isinstance(i, (dict, list)) for i in o):
        for i in o:
            generic_walk(i, path + "[]", hit)
    else:
        hit[path].append(o)


def type_name(values):
    kinds = set()
    for v in values:
        if v is None:
            continue
        if isinstance(v, bool):
            kinds.add("boolean")
        elif isinstance(v, int):
            kinds.add("integer")
        elif isinstance(v, float):
            kinds.add("number")
        elif isinstance(v, list):
            kinds.add("list")
        else:
            kinds.add("string")
    if kinds == {"integer", "number"}:
        return "number"
    return " / ".join(sorted(kinds)) or "null"


def observed_summary(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return "all null"
    nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if nums and len(nums) == len(vals) and len(set(nums)) > 6:
        return f"min {round(min(nums), 2)} | max {round(max(nums), 2)} | mean {round(sum(nums) / len(nums), 2)}"
    flat = []
    for v in vals:
        flat.extend(v if isinstance(v, list) else [v])
    distinct = sorted({str(v) for v in flat})
    if not distinct:
        return "empty list"
    if len(distinct) > 12 or any(len(d) > 120 for d in distinct):
        long = any(len(d) > 120 for d in distinct)
        return f"{len(distinct)} distinct values" + (" (long text)" if long else f", e.g. {', '.join(distinct[:5])}")
    return ", ".join(distinct)


HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def write_sheet(ws, header, rows, widths=None, wrap_cols=()):
    ws.append(header)
    for c in ws[1]:
        c.fill, c.font = HEADER_FILL, HEADER_FONT
        c.alignment = Alignment(vertical="top", wrap_text=True)
    for r in rows:
        ws.append([scalar(v) for v in r])
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions
    for i, h in enumerate(header, 1):
        w = (widths or {}).get(h) or min(60, max(10, len(str(h)) + 2))
        ws.column_dimensions[get_column_letter(i)].width = w
    for col in wrap_cols:
        idx = header.index(col) + 1
        for row in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")


def main(out_path: Path):
    records = load_records()

    # ---- per-version generic attribute stats
    hits_by_version: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    hits_all = defaultdict(list)
    present_records = defaultdict(int)
    nonnull_records = defaultdict(int)
    for _, _, r in records:
        h = defaultdict(list)
        generic_walk(r, "", h)
        v = r["provenance"]["schema_version"]
        for p, vals in h.items():
            hits_by_version[v][p].extend(vals)
            hits_all[p].extend(vals)
            present_records[p] += 1
            if any(x is not None for x in vals):
                nonnull_records[p] += 1

    # canonical attribute order: schema/ATTR order, then any extra observed paths
    paths = list(ATTR) + sorted(p for p in hits_all if p not in ATTR)
    # Drop container rows whose leaves are already listed (they only appear when null/empty)
    versions = [v for v in VERSION_ORDER if v in hits_by_version]

    dict_rows = []
    for p in paths:
        sec, desc, unit, how, allowed = ATTR.get(p, ("(unlisted)", "", "", "", ""))
        vals = hits_all.get(p, [])
        if how == "Container":
            # Top-level block: summarise per record (populated / empty list / null) across all versions.
            tops = [r.get(p, "__absent__") for _, _, r in records]
            populated = sum(1 for t in tops if t not in (None, [], "__absent__"))
            empty = sum(1 for t in tops if t == [])
            null = sum(1 for t in tops if t is None)
            in_versions = [v for v in versions if any(r["provenance"]["schema_version"] == v and p in r
                                                       for _, _, r in records)]
            kind = "list" if p in LIST_KEYS or p in ("encounters", "clinical_timeline") else "object"
            dict_rows.append([sec, p, kind, unit, how, desc, allowed,
                              f"populated in {populated} | empty list in {empty} | null in {null} records",
                              populated, populated + empty + null, len(records), ", ".join(in_versions)])
            continue
        in_versions = [v for v in versions if p in hits_by_version[v]]
        dict_rows.append([
            sec, p, type_name(vals), unit, how, desc, allowed,
            observed_summary(vals) if vals else "(not observed)",
            nonnull_records.get(p, 0), present_records.get(p, 0), len(records),
            ", ".join(in_versions),
        ])

    # ---- flattened records
    flat_rows, cols = [], []
    seen = set()
    for label, src, r in records:
        row = {"dataset": label, "source_file": src, **flatten(r)}
        flat_rows.append(row)
        for k in row:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    # order columns: dataset/source first, then by top-level section order of the record
    section_order = ["dataset", "source_file", "patient_id", "provenance.schema_version", "demographics", "risk_factors",
                     "family_history", "medical_history", "diagnoses", "medications", "labs", "blood_pressure",
                     "air_quality", "encounters", "lipid_panel", "lipid_interpretations", "ecg", "echo",
                     "clinical_timeline", "validation", "provenance"]

    first_seen = {c: i for i, c in enumerate(cols)}

    def col_key(c):
        for i, s in enumerate(section_order):
            if c == s or c.startswith(s + ".") or c.startswith(s + "["):
                return (i, first_seen[c])
        return (len(section_order), first_seen[c])

    cols.sort(key=col_key)

    # ---- column dictionary for the flat sheet
    def generic_of(c):
        import re
        g = re.sub(r"\[[^\]]*\]", "[]", c)
        return g

    # ---- 100K completeness audit
    audit_rows = []
    audit_path = ROOT / "docs/M9_FIELD_COMPLETENESS_AUDIT.json"
    audit_note = ""
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit_note = f"{audit.get('n_records')} records from {audit.get('source_dir')}"
        for f, s in audit["fields"].items():
            audit_rows.append([f, s.get("valid"), s.get("valid_pct"), s.get("null"), s.get("null_pct"),
                               s.get("invalid"), s.get("invalid_pct"), "; ".join(map(str, s.get("invalid_examples", [])))])

    manifest_path = ROOT / "client_review_package_v09/04_dataset_manifest/dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    # ---- workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    counts = defaultdict(int)
    for label, _, r in records:
        counts[(label, r["provenance"]["schema_version"])] += 1
    lines = [
        ["SYSDAG — attributes of all generated synthetic patient data"],
        ["ALL RECORDS ARE SYNTHETIC. None represent real patients."],
        [f"Current schema: v{S.SCHEMA_VERSION} (schemas/patient_schema.py). Regenerate: python scripts/export_data_attributes.py"],
        [],
        ["Sheet", "Contents"],
        ["Attribute_Dictionary", "One row per attribute (all schema versions): section, type, unit, how generated, description, allowed values, values observed in the local records, counts, versions it appears in."],
        ["Records_Flat", f"Every generated record on this machine ({len(records)} rows), one column per attribute. List fields are keyed by name, e.g. labs[HbA1c].value, diagnoses[diabetes].onset_date."],
        ["Column_Index", "Every Records_Flat column mapped back to its Attribute_Dictionary attribute."],
        ["100K_Field_Completeness", f"Per-field valid/null/invalid counts from the full-scale audit ({audit_note or 'not found'})."],
        ["Version_History", "Which schema version added or changed what."],
        [],
        ["Dataset", "Schema version", "Records"],
        *[[k[0], k[1], n] for k, n in sorted(counts.items(), key=lambda kv: (VERSION_ORDER.index(kv[0][1]), kv[0][0]))],
        ["TOTAL", "", len(records)],
        [],
        ["Frozen full-scale dataset (NOT on this machine, gitignored)"],
        ["name", manifest.get("dataset_name", "sysdag_m9_100k_v09")],
        ["patient_count", manifest.get("patient_count", 100000)],
        ["schema_version", manifest.get("schema_version", "0.9")],
        ["location", "outputs/m9/100k_patients_v09/ (regenerate from code + seed + config)"],
        ["structural validation", json.dumps(manifest.get("validation_status", {}))],
        ["clinical validation", json.dumps({k: v for k, v in manifest.get("clinical_validation_status", {}).items() if k != "checks_performed"})],
        [],
        ["Notes"],
        ["- The 5 review patients (PAT_000001/11/13/15/95) appear once per schema version v0.9..v0.13 so attribute changes across versions can be compared."],
        ["- 'Not modelled (always null)' attributes exist in the schema but are deliberately left empty (no usable evidence): height, weight, echo, diagnosed_date, medication dates."],
        ["- ECG is metadata only (a linked PTB-XL record); no waveform is attached."],
        ["- The 100K completeness sheet comes from the v0.8 100K audit (outputs/m8/100k_patients_v08): it predates family_history/air_quality population (v0.9)."],
    ]
    for l in lines:
        ws.append(l)
    for r in (1, 5, 12):
        for c in ws[r]:
            c.font = Font(bold=True, size=13 if r == 1 else 11)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 110
    ws.column_dimensions["C"].width = 10

    write_sheet(
        wb.create_sheet("Attribute_Dictionary"),
        ["Section", "Attribute", "Data type", "Unit", "How generated", "Description", "Allowed values / vocabulary",
         "Observed in local records", "Records non-null", "Records present", "Total records", "Schema versions present"],
        dict_rows,
        widths={"Section": 18, "Attribute": 46, "Data type": 12, "Unit": 10, "How generated": 34, "Description": 60,
                "Allowed values / vocabulary": 40, "Observed in local records": 50, "Schema versions present": 30},
        wrap_cols=("Description", "Observed in local records", "Allowed values / vocabulary", "How generated"),
    )

    ws = wb.create_sheet("Records_Flat")
    write_sheet(ws, cols, [[row.get(c) for c in cols] for row in flat_rows],
                widths={c: (40 if c == "provenance.generator" else 22) for c in cols})
    ws.freeze_panes = "D2"

    col_rows = []
    for c in cols:
        g = generic_of(c)
        base = g[:-len(".count")] if g.endswith(".count") else g
        sec, desc, unit, how, _ = ATTR.get(base, ATTR.get(g, ("", "", "", "", "")))
        if g.endswith(".count"):
            desc = f"Number of items in {base}"
            how = "Computed by export"
        if c in ("dataset", "source_file"):
            sec, desc = "Export", "Which local dataset / file the record came from"
        col_rows.append([c, base, sec, unit, how, desc])
    write_sheet(wb.create_sheet("Column_Index"),
                ["Records_Flat column", "Attribute", "Section", "Unit", "How generated", "Description"], col_rows,
                widths={"Records_Flat column": 50, "Attribute": 46, "Section": 18, "How generated": 34, "Description": 70},
                wrap_cols=("Description",))

    write_sheet(wb.create_sheet("100K_Field_Completeness"),
                ["Field", "Valid", "Valid %", "Null", "Null %", "Invalid", "Invalid %", "Invalid examples"], audit_rows,
                widths={"Field": 50, "Invalid examples": 50})

    write_sheet(wb.create_sheet("Version_History"), ["Schema version", "Change"], [
        ["0.7", "M5 100K baseline: demographics, risk factors, lipids, HbA1c (non-diabetics), diagnoses, medical history, medications, ECG metadata."],
        ["0.8", "M8: blood_pressure, encounters (baseline container), clinical_timeline reference_id."],
        ["0.9", "D019 lipid reject-and-redraw; D020 family_history populated (LASI); D021 air_quality (CPCB state AQI). Frozen 100K dataset."],
        ["0.10", "D022: joint lipid model (no LDL clamp); HbA1c for every patient + derivation/confidence; BP confidence + SBP trend extrapolation; modelled onset age/date on diagnoses; condition_onset_modeled timeline event."],
        ["0.11", "D023: risk_factors.hyperlipidemia derived from own lipid panel (NCEP_ATP_III)."],
        ["0.12", "D024: LAI_2020 interpretation gains rule-based risk_category / ldl_goal_mg_dl / ldl_above_goal / risk_factors_counted / risk_derivation."],
        ["0.13", "D027: hypertension from age x sex curve, diabetes from age curve (NFHS-5 / ICMR-NNMS / LASI)."],
    ], widths={"Schema version": 16, "Change": 140}, wrap_cols=("Change",))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"wrote {out_path} | records={len(records)} attributes={len(dict_rows)} flat_columns={len(cols)} audit_fields={len(audit_rows)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs/GENERATED_DATA_ATTRIBUTES.xlsx")
