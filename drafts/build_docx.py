#!/usr/bin/env python3
"""Build znaemai_content_v3.docx from markdown articles."""

import re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

CONTENT_DIR = Path(__file__).parent / "content"
OUTPUT = Path(__file__).parent / "znaemai_content_v3.docx"

HABR_FILES = [f"habr_v2_{i}.md" for i in range(1, 6)]
VCRU_FILES = [f"vcru_v2_{i}.md" for i in range(1, 6)]


def parse_md(filepath: Path) -> list[tuple[str, str, int]]:
    """Parse markdown into list of (type, text, heading_level).
    type: 'h1', 'h2', 'h3', 'para', 'code', 'hr', 'table'
    """
    lines = filepath.read_text(encoding="utf-8").splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Code block
        if line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(("code", "\n".join(code_lines), 0))
            i += 1
            continue

        # Headings
        if line.startswith("### "):
            blocks.append(("h3", line[4:].strip(), 3))
            i += 1
            continue
        if line.startswith("## "):
            blocks.append(("h2", line[3:].strip(), 2))
            i += 1
            continue
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip(), 1))
            i += 1
            continue

        # HR
        if line.strip() in ("---", "***", "___"):
            blocks.append(("hr", "", 0))
            i += 1
            continue

        # Table (skip table lines, just add as text)
        if line.strip().startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|[\s\-|]+\|$", lines[i].strip()):
                    table_lines.append(lines[i].strip())
                i += 1
            for tl in table_lines:
                cells = [c.strip() for c in tl.split("|") if c.strip()]
                blocks.append(("para", " | ".join(cells), 0))
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Regular paragraph
        blocks.append(("para", line.strip(), 0))
        i += 1

    return blocks


def clean_md_formatting(text: str) -> list[tuple[str, bool, bool]]:
    """Parse inline markdown into segments: (text, bold, italic)."""
    segments = []
    # Handle bold+italic, bold, italic
    pattern = re.compile(r"(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|([^*`]+))")
    for m in pattern.finditer(text):
        if m.group(2):  # bold+italic
            segments.append((m.group(2), True, True))
        elif m.group(3):  # bold
            segments.append((m.group(3), True, False))
        elif m.group(4):  # italic
            segments.append((m.group(4), False, True))
        elif m.group(5):  # code
            segments.append((m.group(5), False, False))  # treat inline code as normal
        elif m.group(6):
            segments.append((m.group(6), False, False))
    return segments if segments else [(text, False, False)]


def add_formatted_paragraph(doc, text: str, style=None):
    """Add a paragraph with inline markdown formatting."""
    p = doc.add_paragraph(style=style)
    segments = clean_md_formatting(text)
    for seg_text, bold, italic in segments:
        run = p.add_run(seg_text)
        run.bold = bold
        run.italic = italic
    return p


def add_article(doc, filepath: Path):
    """Add one article to the document."""
    blocks = parse_md(filepath)
    for btype, text, level in blocks:
        if btype == "h1":
            doc.add_heading(text, level=1)
        elif btype == "h2":
            doc.add_heading(text, level=2)
        elif btype == "h3":
            doc.add_heading(text, level=3)
        elif btype == "code":
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.font.name = "Courier New"
            run.font.size = Pt(9)
        elif btype == "hr":
            pass  # skip horizontal rules
        elif btype == "para":
            # Handle list items
            if text.startswith("- "):
                add_formatted_paragraph(doc, text[2:], style="List Bullet")
            elif re.match(r"^\d+\.\s", text):
                clean = re.sub(r"^\d+\.\s", "", text)
                add_formatted_paragraph(doc, clean, style="List Number")
            else:
                add_formatted_paragraph(doc, text)


def main():
    doc = Document()

    # Title page
    title = doc.add_heading("ZnaemAI — Контент v3", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    subtitle = doc.add_paragraph("10 статей для Хабра и vc.ru")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    doc.add_paragraph()

    # HABR section
    doc.add_page_break()
    section_title = doc.add_heading("ХАБР — 5 статей", level=0)
    doc.add_paragraph()

    for fname in HABR_FILES:
        fpath = CONTENT_DIR / fname
        if fpath.exists():
            add_article(doc, fpath)
            doc.add_page_break()

    # VC.RU section
    section_title = doc.add_heading("VC.RU — 5 статей", level=0)
    doc.add_paragraph()

    for fname in VCRU_FILES:
        fpath = CONTENT_DIR / fname
        if fpath.exists():
            add_article(doc, fpath)
            doc.add_page_break()

    doc.save(str(OUTPUT))
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
