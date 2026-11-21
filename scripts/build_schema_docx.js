// Builds docs/SYSDAG_Patient_Record_Schema_v0.13.docx from schemas/patient_schema.json.
// Usage: node scripts/build_schema_docx.js schemas/patient_schema.json docs/SYSDAG_Patient_Record_Schema_v0.13.docx  (needs: npm install docx@9)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, TableLayoutType, LevelFormat, BorderStyle, Footer, PageNumber, PageOrientation,
} = require("docx");

const [, , schemaPath, outPath] = process.argv;
const S = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
const FONT = "Calibri";
const NAVY = "1F4E78";
const LIGHT = "DDEBF7";
const GREY = "F2F2F2";

// ---------- schema helpers
const deref = (n) => (n && n.$ref ? S.$defs[n.$ref.split("/").pop()] : n);

function unwrap(node) {
  // oneOf [null, X] -> X (nullable); returns {node, nullable}
  node = deref(node);
  if (node.oneOf) {
    const nonNull = node.oneOf.find((o) => !(o.type === "null"));
    const merged = { ...deref(nonNull) };
    if (node.description) merged.description = node.description + (merged.description ? " " + merged.description : "");
    return { node: merged, nullable: true };
  }
  return { node, nullable: Array.isArray(node.type) && node.type.includes("null") };
}

const TYPE_NAMES = { string: "Text", number: "Number", integer: "Integer", boolean: "Yes/No", array: "List", object: "Object" };

function typeText(node) {
  const n = deref(node);
  let types = Array.isArray(n.type) ? n.type : [n.type];
  types = types.filter((t) => t && t !== "null");
  let base = types.map((t) => TYPE_NAMES[t] || t).join(" / ") || "Object";
  if (n.$ref === undefined && node.$ref && /date/i.test(node.$ref)) base = "Date";
  if (n.pattern === "^[0-9]{4}-[0-9]{2}-[0-9]{2}$") base = "Date";
  if (n.format === "date-time") base = "Date-time";
  if (types.includes("array") && n.items) {
    const it = deref(n.items);
    base = `List of ${(TYPE_NAMES[it.type] || "Text").toLowerCase()}`;
  }
  return base;
}

const PATTERNS = {
  "^PAT_[0-9]{6}$": "PAT_ + 6 digits (e.g. PAT_000001)",
  "^PAT_[0-9]{6}_DX[0-9]{2}$": "e.g. PAT_000001_DX01",
  "^PAT_[0-9]{6}_MED[0-9]{2}$": "e.g. PAT_000001_MED01",
  "^PAT_[0-9]{6}_ENC[0-9]{2}$": "e.g. PAT_000001_ENC01",
  "^[0-9]{4}-[0-9]{2}-[0-9]{2}$": "YYYY-MM-DD",
  "^modeled_": "starts with \"modeled_\"",
};

function allowedText(node) {
  const n = deref(node);
  const src = n.items && !n.enum ? deref(n.items) : n;
  const parts = [];
  if (src.enum) parts.push(src.enum.filter((v) => v !== null).join(", "));
  if (src.const !== undefined) parts.push(String(src.const));
  if (src.pattern) parts.push(PATTERNS[src.pattern] || src.pattern);
  if (src.format === "date-time") parts.push("ISO 8601 date-time (UTC)");
  if (n.minimum !== undefined && n.maximum !== undefined) parts.push(`${n.minimum} to ${n.maximum}`);
  else if (n.minimum !== undefined) parts.push(`>= ${n.minimum}`);
  if (n.minItems === 2 && n.maxItems === 2) parts.push("[samples, leads]");
  return parts.join("; ") || "—";
}

function descText(node, required, nullable) {
  const n = deref(node);
  let d = (node.description || n.description || "").trim();
  return d || "—";
}

function addedIn(text) {
  const m = /Added(?: \(populated\))? in v([0-9]+\.[0-9]+)/.exec(text || "");
  return m ? `v${m[1]}` : null;
}

// ---------- doc helpers
const W = 9026; // A4 width minus 1" margins (DXA)
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };

function cell(text, width, opts = {}) {
  const lines = String(text).split("\n");
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: lines.map((l) => new Paragraph({
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text: l, font: opts.mono ? "Consolas" : FONT, size: opts.size || (opts.mono ? 16 : 18),
                               bold: !!opts.bold, color: opts.color })],
    })),
  });
}

function table(widths, header, rows) {
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: widths,
    layout: TableLayoutType.FIXED,
    rows: [
      new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, widths[i], { fill: NAVY, bold: true, color: "FFFFFF" })) }),
      ...rows.map((r, ri) => new TableRow({
        cantSplit: true,
        children: r.map((v, i) => cell(v, widths[i], { mono: i === 0, fill: ri % 2 ? GREY : undefined })),
      })),
    ],
  });
}

const P = (text, opts = {}) => new Paragraph({
  spacing: { after: 120 }, ...opts.para,
  children: (Array.isArray(text) ? text : [text]).map((t) => typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 22 }) : t),
});
const B = (text, bold) => new TextRun({ text, font: FONT, size: 22, bold });
const bullet = (runs) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
  children: (Array.isArray(runs) ? runs : [runs]).map((t) => typeof t === "string" ? B(t) : t) });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });

// ---------- sections
const SECTIONS = [
  ["patient_id", "Patient ID", "Unique synthetic identifier of the record."],
  ["demographics", "Demographics", "Who the patient is."],
  ["risk_factors", "Risk factors", "Lifestyle and cardiovascular risk factors."],
  ["family_history", "Family history", "Conditions in first-degree relatives (parents / siblings)."],
  ["medical_history", "Medical history", "List; one entry per chronic condition. Each entry points to a diagnosis."],
  ["diagnoses", "Diagnoses", "List; one entry per diagnosed condition (hypertension, diabetes)."],
  ["medications", "Medications", "List; one entry per treated condition. Drug class only, no drug names."],
  ["labs", "Laboratory results", "List; one entry per lab test (currently HbA1c)."],
  ["blood_pressure", "Blood pressure", "One office blood-pressure measurement."],
  ["lipid_panel", "Lipid panel", "Cholesterol test values."],
  ["lipid_interpretations", "Lipid interpretations", "List; one entry per guideline (NCEP ATP III and Lipid Association of India 2020)."],
  ["air_quality", "Air quality (environment)", "Annual average AQI of the patient's state. Not personal exposure."],
  ["encounters", "Encounters", "List; the baseline check-up at which BP and labs were measured."],
  ["ecg", "ECG", "Linked PTB-XL ECG record (metadata only, no waveform yet)."],
  ["echo", "Echocardiography", "Reserved; not modelled yet (always empty)."],
  ["clinical_timeline", "Clinical timeline", "List; every dated event in the record."],
  ["provenance", "Provenance", "How, when and from which sources the record was generated."],
  ["validation", "Validation", "Results of the automatic quality checks."],
];

const clean = (t) => (t || "").replace(/Added(?: \(populated\))? in v[0-9]+\.[0-9]+\.?\s*/g, "").replace(/\s+/g, " ").trim() || "—";

function fieldRows(objNode, prefix = "", parentAdded = "v0.7") {
  const { node } = unwrap(objNode);
  const n = node.type === "array" || (Array.isArray(node.type) && node.type.includes("array")) ? deref(node.items) : node;
  const req = new Set(n.required || []);
  const rows = [];
  for (const [k, v] of Object.entries(n.properties || {})) {
    const u = unwrap(v);
    const d = (v.description || "") + (u.node.description && v.description !== u.node.description ? " " + (u.node.description || "") : "");
    const isObj = u.node.properties;
    rows.push([prefix + k, isObj ? "Object" : typeText(v.$ref ? v : u.node), isObj ? "—" : allowedText(v.$ref ? v : u.node),
               clean(deref(v).description || v.description), addedIn(d) || parentAdded]);
    if (isObj) rows.push(...fieldRows(u.node, prefix + k + ".", addedIn(d) || parentAdded));
  }
  return rows;
}

const content = [];
content.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Synthetic Cardiovascular Patient Record")] }));
content.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Data Schema — version 0.13", font: FONT, size: 30, color: NAVY })] }));
content.push(new Paragraph({ spacing: { after: 240 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 4 } },
  children: [new TextRun({ text: "SYSDAG project  ·  21 November 2026", font: FONT, size: 20, color: "595959" })] }));

content.push(H1("1. About this document"));
content.push(P("This document describes the structure (schema) of every synthetic patient record generated in the SYSDAG project. Each record is one complete synthetic patient: demographics, risk factors, family history, diagnoses, medications, labs, vitals, environment, ECG link, timeline, provenance and validation results."));
content.push(bullet([B("All records are synthetic. ", true), B("No record describes a real patient.")]));
content.push(bullet([B("Current version: ", true), B("0.13. Records were generated at versions 0.7 to 0.13; the schema covers all of them. The frozen 100,000-patient dataset is version 0.9.")]));
content.push(bullet([B("Source of truth: ", true), B("schemas/patient_schema.json (machine-readable JSON Schema) and schemas/patient_schema.py in the repository. All 125 locally stored records validate against it.")]));

content.push(H2("Conventions"));
content.push(bullet([B("Empty value (null) ", true), B("= not modelled by the generator (e.g. height, echo).")]));
content.push(bullet([B("Empty list ", true), B("= modelled, and nothing applies (e.g. a patient with no diagnoses).")]));
content.push(bullet([B("Added in ", true), B("= the schema version that introduced the field; older records do not contain it.")]));
content.push(bullet([B("Nested fields ", true), B("are written with a dot, e.g. clinical_consistency.valid.")]));

content.push(H1("2. Record overview"));
content.push(table([2300, 1500, 5226], ["Section", "Type", "Contents"],
  SECTIONS.map(([k, label, what]) => {
    const { node } = unwrap(S.properties[k]);
    const t = (Array.isArray(node.type) ? node.type : [node.type]).includes("array") ? "List" :
              (node.properties || node.type === "object" || (Array.isArray(node.type) && node.type.includes("object"))) ? "Object" : typeText(node);
    return [k, t, `${label}: ${what}`];
  })));

content.push(H1("3. Field reference"));
const COLS = [2450, 1000, 2100, 2576, 900];
let i = 0;
for (const [k, label, what] of SECTIONS) {
  i++;
  content.push(H2(`3.${i}  ${label}  (${k})`));
  content.push(P(what, { para: { spacing: { after: 80 } } }));
  const node = S.properties[k];
  const { node: u } = unwrap(node);
  let rows;
  if (u.properties || (u.items && deref(u.items).properties)) rows = fieldRows(node, "", addedIn(node.description) || "v0.7");
  else rows = [[k, typeText(u), allowedText(u), clean(node.description || u.description), addedIn(node.description) || "v0.7"]];
  content.push(table(COLS, ["Field", "Type", "Allowed values / format", "Description", "Added in"], rows));
}

content.push(H1("4. Not yet modelled"));
content.push(P("These fields exist in the schema but are always empty, because no usable Indian evidence source has been found yet:"));
for (const t of [
  "Height and weight (demographics.height_cm, weight_kg)",
  "Date a doctor made the diagnosis (diagnoses.diagnosed_date, medical_history.event_date)",
  "Medication start and stop dates",
  "Statin and antiplatelet medicines; heart attack, stroke and procedure history",
  "Echocardiography (echo)",
  "ECG waveform (only the PTB-XL record link is stored; signal_available is false)",
]) content.push(bullet(t));

const doc = new Document({
  creator: "SYSDAG project",
  title: "Synthetic Cardiovascular Patient Record — Data Schema v0.13",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { font: FONT, size: 44, bold: true, color: NAVY },
        paragraph: { spacing: { before: 0, after: 60 }, keepNext: true } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: NAVY }, paragraph: { spacing: { before: 320, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: "2E75B6" }, paragraph: { spacing: { before: 240, after: 80 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "SYSDAG patient record schema v0.13  ·  Page ", font: FONT, size: 16, color: "808080" }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "808080" }),
    ] })] }) },
    children: content,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log("wrote", outPath); });
