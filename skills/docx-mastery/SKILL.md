---
name: docx-mastery
description: "Create, edit, and analyze DOCX files with python-docx. Tracked changes, comments, formatting, templates. Use when: (1) creating Word documents, (2) editing existing DOCX, (3) generating reports/contracts, (4) extracting text from DOCX, (5) Gravity document templates. Triggers on: docx, word, документ, отчёт, заявка, контракт, шаблон."
---

# DOCX Mastery

> Create and edit Word documents programmatically with python-docx.

## Quick Decision

| Task | Approach |
|------|----------|
| Create new DOCX | python-docx (see below) |
| Read/extract text | `pandoc file.docx -o output.md` or python-docx |
| Edit existing DOCX | python-docx load + modify + save |
| Tracked changes | OOXML XML manipulation (advanced) |
| Convert formats | `pandoc` or `pdf2docx` |

## Creating Documents

```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

# Styles
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(12)

# Title
doc.add_heading('Title', level=0)

# Paragraph with formatting
p = doc.add_paragraph()
run = p.add_run('Bold text')
run.bold = True
run.font.size = Pt(14)

# Table
table = doc.add_table(rows=2, cols=3, style='Table Grid')
table.cell(0, 0).text = 'Header 1'

# Page break
doc.add_page_break()

# Save
doc.save('output.docx')
```

## Key Patterns

### Heading Hierarchy
```python
doc.add_heading('Chapter', level=1)    # H1
doc.add_heading('Section', level=2)    # H2
doc.add_heading('Subsection', level=3) # H3
```

### Tables with Merged Cells
```python
table = doc.add_table(rows=3, cols=4, style='Table Grid')
# Merge cells
a = table.cell(0, 0)
b = table.cell(0, 3)
a.merge(b)  # Merge first row across all columns
```

### Images
```python
doc.add_picture('image.png', width=Inches(4))
# Or with specific dimensions
doc.add_picture('logo.png', width=Cm(5), height=Cm(3))
```

### Page Setup
```python
from docx.shared import Cm
section = doc.sections[0]
section.page_width = Cm(21)    # A4
section.page_height = Cm(29.7)
section.left_margin = Cm(2)
section.right_margin = Cm(1.5)
section.top_margin = Cm(2)
section.bottom_margin = Cm(2)
```

### Numbered/Bullet Lists
```python
doc.add_paragraph('First item', style='List Number')
doc.add_paragraph('Second item', style='List Number')
doc.add_paragraph('Bullet point', style='List Bullet')
```

## Reading Documents

```python
doc = Document('input.docx')

# All text
for para in doc.paragraphs:
    print(para.text)

# Tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text)
```

## Common Pitfalls

1. **Encoding:** python-docx handles UTF-8 natively, no special handling for Cyrillic
2. **Styles:** Always set font on style level, not per-paragraph
3. **Tables:** Set column widths explicitly, auto-width is unpredictable
4. **Images:** Use Inches() or Cm() for sizing, never raw numbers
5. **Existing docs:** Load with `Document('file.docx')`, modify, save to NEW file
