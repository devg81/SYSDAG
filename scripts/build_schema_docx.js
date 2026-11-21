// Builds docs/SYSDAG_Patient_Record_Schema_v0.13.docx: the attribute list of a patient record,
// read from schemas/patient_schema.json.
// Usage: node scripts/build_schema_docx.js schemas/patient_schema.json docs/SYSDAG_Patient_Record_Schema_v0.13.docx  (needs: npm install docx@9)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, BorderStyle, TableLayoutType, VerticalAlign,
} = require("docx");

const [, , schemaPath, outPath] = process.argv;
const S = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
const FONT = "Calibri";
const NAVY = "1F4E78";

const deref = (n) => (n && n.$ref ? S.$defs[n.$ref.split("/").pop()] : n);

// Resolve a top-level property to the object whose properties are its attributes.
function objectOf(node) {
  node = deref(node);
  if (node.oneOf) node = deref(node.oneOf.find((o) => o.type !== "null"));
  if (node.items) node = deref(node.items);
  return node.properties ? node : null;
}

function isList(node) {
  const t = deref(node).type;
  return t === "array" || (Array.isArray(t) && t.includes("array"));
}

// Attribute names, nested objects written as parent {child, child}.
function attrs(obj) {
  return Object.entries(obj.properties).map(([k, v]) => {
    const inner = objectOf(v);
    return inner ? `${k} {${attrs(inner).join(", ")}}` : k;
  });
}

const W = 9026; // A4 minus 1" margins, DXA
const COLS = [600, 2700, 5726];
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };

function cell(text, width, opts = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders,
    verticalAlign: VerticalAlign.CENTER,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text, font: FONT, size: 20, bold: !!opts.bold, color: opts.color })],
    })],
  });
}

const rows = [];
let n = 0;
for (const [key, node] of Object.entries(S.properties)) {
  n++;
  const obj = objectOf(node);
  const name = key + (isList(node) ? " [ ]" : "");
  const list = obj ? attrs(obj).join(", ")
    : key === "patient_id" ? "Unique synthetic ID (e.g. PAT_000001)"
    : key === "echo" ? "Reserved (not modelled yet)" : "—";
  rows.push(new TableRow({
    cantSplit: true,
    children: [
      cell(String(n), COLS[0], { center: true, fill: n % 2 ? undefined : "F2F2F2" }),
      cell(name, COLS[1], { bold: true, fill: n % 2 ? undefined : "F2F2F2" }),
      cell(list, COLS[2], { fill: n % 2 ? undefined : "F2F2F2" }),
    ],
  }));
}

const doc = new Document({
  creator: "SYSDAG project",
  title: "Synthetic Patient Record - Attribute List (Schema v0.13)",
  styles: { default: { document: { run: { font: FONT, size: 22 } } } },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    children: [
      new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Synthetic Cardiovascular Patient Record", font: FONT, size: 36, bold: true, color: NAVY })] }),
      new Paragraph({ spacing: { after: 240 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 4 } },
        children: [new TextRun({ text: "Attribute list  ·  Schema v0.13  ·  SYSDAG project", font: FONT, size: 24, color: "595959" })] }),
      new Table({
        width: { size: W, type: WidthType.DXA },
        columnWidths: COLS,
        layout: TableLayoutType.FIXED,
        rows: [
          new TableRow({ tableHeader: true, children: ["No.", "Section", "Attributes"].map((h, i) =>
            cell(h, COLS[i], { bold: true, color: "FFFFFF", fill: NAVY, center: i === 0 })) }),
          ...rows,
        ],
      }),
      new Paragraph({ spacing: { before: 200 }, children: [new TextRun({ text: "[ ] = list (one entry per item, e.g. one per diagnosis).  All records are synthetic.", font: FONT, size: 18, italics: true, color: "595959" })] }),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log("wrote", outPath); });
