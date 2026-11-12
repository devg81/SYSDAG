"""
generate_report.py

Reads eval_<CLASS>/metrics_summary.txt and the 3 PNG plots for each class,
then produces SynDataGen_Evaluation_Report.docx

Run from D:/SynGen/:
    python generate_report.py

Output: D:/SynGen/SynDataGen_Evaluation_Report.docx

Install dependency first:
    pip install python-docx
"""

import os
import re
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── CONFIG ────────────────────────────────────────────────────────────
BASE_DIR = r"D:/SynGen"
CLASSES  = ["NORM", "MI", "STTC", "CD", "HYP"]
OUT_FILE = os.path.join(BASE_DIR, "SynDataGen_Evaluation_Report.docx")

CLASS_LABELS = {
    "NORM": "NORM — Normal Sinus Rhythm",
    "MI"  : "MI — Myocardial Infarction",
    "STTC": "STTC — ST/T Change",
    "CD"  : "CD — Conduction Disturbance",
    "HYP" : "HYP — Hypertrophy",
}

METRIC_EXPLANATIONS = {
    "Variance (diversity/mode collapse)":
        "Higher value means the model produced diverse outputs. Low variance means all generated ECGs look the same (mode collapse — bad).",
    "Mean Difference":
        "Difference between the average amplitude of real vs synthetic ECGs. Closer to 0 is better.",
    "Std Difference":
        "Difference in signal spread between real and synthetic. Closer to 0 means the synthetic data has the same variability as real data.",
    "KS Statistic (mean)":
        "Kolmogorov-Smirnov test across all 12 leads. Lower value means the synthetic amplitude distribution closely matches the real one. Below 0.1 is excellent.",
    "KL Divergence (mean)":
        "Measures how different the synthetic distribution is from the real distribution. Lower is better. Near 0 means near-identical distributions.",
    "MSE (waveform shape)":
        "Mean Squared Error between the average real waveform and average synthetic waveform. Lower means the generated ECG shape matches real ECG shape.",
}

# ── HELPERS ───────────────────────────────────────────────────────────

def parse_summary(cls):
    path = os.path.join(BASE_DIR, f"eval_{cls}", "metrics_summary.txt")
    if not os.path.exists(path):
        return {}
    metrics = {}
    with open(path, "r") as f:
        for line in f:
            match = re.match(r"^(.+?):\s+([\d.]+)", line)
            if match:
                metrics[match.group(1).strip()] = float(match.group(2))
    return metrics


def set_cell_bg(cell, hex_color):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def add_heading(doc, text, level=1, color="1B6CA8"):
    p   = doc.add_heading(text, level=level)
    run = p.runs[0]
    run.font.color.rgb = RGBColor.from_string(color)
    run.font.name      = "Calibri"
    return p


def add_body(doc, text, bold=False, size=11, color="000000"):
    p   = doc.add_paragraph()
    run = p.add_run(text)
    run.bold           = bold
    run.font.size      = Pt(size)
    run.font.name      = "Calibri"
    run.font.color.rgb = RGBColor.from_string(color)
    return p


def add_metric_table(doc, metrics):
    headers      = ["Metric", "Value", "What it means"]
    col_widths   = [Cm(6), Cm(2.5), Cm(8.5)]
    header_color = "1B6CA8"
    row_colors   = ["EBF4FB", "FFFFFF"]

    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style     = "Table Grid"

    # header row
    hdr_cells = table.rows[0].cells
    for i, (cell, txt) in enumerate(zip(hdr_cells, headers)):
        cell.width = col_widths[i]
        set_cell_bg(cell, header_color)
        p   = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(txt)
        run.bold           = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        run.font.size      = Pt(10)
        run.font.name      = "Calibri"

    # data rows
    for idx, (key, explanation) in enumerate(METRIC_EXPLANATIONS.items()):
        value = f"{metrics[key]:.4f}" if key in metrics else "N/A"
        fill  = row_colors[idx % 2]
        row   = table.add_row()
        data  = [key, value, explanation]
        aligns = [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT]
        for i, (cell, txt) in enumerate(zip(row.cells, data)):
            cell.width = col_widths[i]
            set_cell_bg(cell, fill)
            p   = cell.paragraphs[0]
            p.alignment = aligns[i]
            run = p.add_run(txt)
            run.font.size      = Pt(9)
            run.font.name      = "Calibri"
            run.font.color.rgb = RGBColor(0, 0, 0)

    doc.add_paragraph()


def add_image(doc, cls, filename, caption, width=Inches(6)):
    img_path = os.path.join(BASE_DIR, f"eval_{cls}", filename)
    if os.path.exists(img_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(img_path, width=width)

        cap = doc.add_paragraph(caption)
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.runs[0].italic         = True
        cap.runs[0].font.size      = Pt(9)
        cap.runs[0].font.color.rgb = RGBColor(100, 100, 100)
        cap.runs[0].font.name      = "Calibri"
    else:
        add_body(doc, f"[Image not found: {filename} — run evaluate_all.py first]",
                 bold=True, color="CC0000")
    doc.add_paragraph()


# ── BUILD DOCUMENT ────────────────────────────────────────────────────

doc = Document()

# page margins
for section in doc.sections:
    section.top_margin    = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin   = Cm(2.5)
    section.right_margin  = Cm(2.5)

# ── TITLE PAGE ────────────────────────────────────────────────────────
doc.add_paragraph()
doc.add_paragraph()

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
t = title.add_run("SynDataGen")
t.bold           = True
t.font.size      = Pt(32)
t.font.name      = "Calibri"
t.font.color.rgb = RGBColor.from_string("1B6CA8")

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
s = sub.add_run("Synthetic ECG Evaluation Report")
s.bold      = True
s.font.size = Pt(20)
s.font.name = "Calibri"

doc.add_paragraph()

authors = doc.add_paragraph()
authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
a = authors.add_run("Janaki Rajvir & Shelja Solanki")
a.font.size      = Pt(13)
a.font.name      = "Calibri"
a.font.color.rgb = RGBColor(80, 80, 80)

inst = doc.add_paragraph()
inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
i = inst.add_run("Adani University  |  Supervised by Dr. Vaishali Chourey")
i.font.size      = Pt(11)
i.font.name      = "Calibri"
i.font.color.rgb = RGBColor(120, 120, 120)

date_p = doc.add_paragraph()
date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
d = date_p.add_run(datetime.now().strftime("%B %Y"))
d.font.size      = Pt(11)
d.font.name      = "Calibri"
d.font.color.rgb = RGBColor(150, 150, 150)

doc.add_page_break()

# ── INTRO ─────────────────────────────────────────────────────────────
add_heading(doc, "About This Report", level=1)
add_body(doc,
    "This report presents the evaluation results of the SynDataGen generative model, "
    "which produces synthetic 12-lead ECG waveforms for five cardiovascular diagnostic "
    "classes: NORM (Normal), MI (Myocardial Infarction), STTC (ST/T Change), "
    "CD (Conduction Disturbance), and HYP (Hypertrophy). Each class has its own trained "
    "generator. The synthetic ECGs are evaluated against real ECGs from the PTB-XL dataset "
    "using statistical and visual metrics."
)
add_body(doc,
    "For each class, this report shows: (1) a sample generated ECG, (2) a beat shape "
    "comparison between real and synthetic signals on Lead II, (3) amplitude distribution "
    "comparison across all 12 leads, and (4) a metrics table with plain-English explanations."
)
doc.add_paragraph()

# ── ONE SECTION PER CLASS ─────────────────────────────────────────────
for i, cls in enumerate(CLASSES):
    if i > 0:
        doc.add_page_break()

    metrics = parse_summary(cls)

    add_heading(doc, CLASS_LABELS[cls], level=1)
    doc.add_paragraph()

    # metrics table
    add_heading(doc, "Evaluation Metrics", level=2)
    add_metric_table(doc, metrics)

    # sample ECG
    add_heading(doc, "Sample Generated ECG (12 Leads)", level=2)
    add_image(doc, cls, "generated_ecg_sample.png",
              f"Figure: One synthetic {cls} ECG — all 12 leads stacked")

    # beat overlay
    add_heading(doc, "Beat Shape Comparison — Lead II", level=2)
    add_body(doc,
        "Each faint line is one individual beat. The thick line is the average beat shape. "
        "Left = Real. Right = Synthetic.")
    add_image(doc, cls, "beat_overlay_lead_II.png",
              f"Figure: Real vs Synthetic beat overlay — Lead II ({cls})")

    # amplitude distribution
    add_heading(doc, "Amplitude Distribution — All 12 Leads", level=2)
    add_body(doc,
        "Grey = Real ECG amplitude. Light grey = Synthetic ECG amplitude. "
        "Closer the overlap, better the match.")
    add_image(doc, cls, "amplitude_distribution.png",
              f"Figure: Amplitude distribution — Real vs Synthetic ({cls})",
              width=Inches(6.2))

# ── SAVE ──────────────────────────────────────────────────────────────
doc.save(OUT_FILE)
print(f"\nReport saved → {OUT_FILE}")