---
name: pptx-mastery
description: "Create PowerPoint presentations with python-pptx. Slides, layouts, charts, images, speaker notes. Use when: (1) creating presentations, (2) generating pitch decks, (3) KP/proposals, (4) slide decks from data. Triggers on: pptx, powerpoint, presentation, slides, deck, КП, презентация."
---

# PPTX Mastery

> Create professional PowerPoint presentations with python-pptx. No PowerPoint installation needed.

## Quick Start

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

prs = Presentation()
prs.slide_width = Cm(33.867)   # 16:9 widescreen
prs.slide_height = Cm(19.05)

# Title slide
layout = prs.slide_layouts[0]  # Title Slide
slide = prs.slides.add_slide(layout)
slide.shapes.title.text = "Project Name"
slide.placeholders[1].text = "Subtitle or date"

# Content slide
layout = prs.slide_layouts[1]  # Title and Content
slide = prs.slides.add_slide(layout)
slide.shapes.title.text = "Key Points"
body = slide.placeholders[1]
tf = body.text_frame
tf.text = "First point"
p = tf.add_paragraph()
p.text = "Second point"
p.level = 1  # Sub-bullet

prs.save("presentation.pptx")
```

## Slide Layouts (Standard)

| Index | Name | Use |
|-------|------|-----|
| 0 | Title Slide | First slide |
| 1 | Title and Content | Body slides |
| 2 | Section Header | Section dividers |
| 5 | Title Only | Custom layouts |
| 6 | Blank | Full custom |

## Key Patterns

### Custom Text Box
```python
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

layout = prs.slide_layouts[6]  # Blank
slide = prs.slides.add_slide(layout)

txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1))
tf = txBox.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Custom styled text"
p.font.size = Pt(24)
p.font.bold = True
p.font.color.rgb = RGBColor(0x44, 0x72, 0xC4)
p.alignment = PP_ALIGN.CENTER
```

### Images
```python
slide.shapes.add_picture("image.png", Inches(1), Inches(2), width=Inches(4))
```

### Tables
```python
rows, cols = 4, 3
table_shape = slide.shapes.add_table(rows, cols, Inches(1), Inches(2), Inches(8), Inches(3))
table = table_shape.table

# Headers
for i, header in enumerate(["Name", "Value", "Status"]):
    cell = table.cell(0, i)
    cell.text = header
    for para in cell.text_frame.paragraphs:
        para.font.bold = True
        para.font.size = Pt(12)

# Data
table.cell(1, 0).text = "Item A"
table.cell(1, 1).text = "100"
```

### Charts
```python
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = CategoryChartData()
chart_data.categories = ['Q1', 'Q2', 'Q3', 'Q4']
chart_data.add_series('Revenue', (100, 150, 130, 200))

chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(1), Inches(2), Inches(8), Inches(4),
    chart_data
).chart
chart.has_legend = False
```

### Speaker Notes
```python
notes_slide = slide.notes_slide
notes_slide.notes_text_frame.text = "Speaker notes here"
```

### Background Color
```python
background = slide.background
fill = background.fill
fill.solid()
fill.fore_color.rgb = RGBColor(0x1A, 0x1A, 0x2E)  # Dark blue
```

## Presentation Templates

For reusable templates, see `references/pptx-templates.md`.

## Common Pitfalls

1. **Slide size:** Set BEFORE adding slides (16:9 = 33.867cm x 19.05cm)
2. **Layouts:** Index depends on template, always check `prs.slide_layouts`
3. **Fonts:** Set on paragraph.font, not on text_frame
4. **Images:** Use absolute paths or verify relative paths
5. **Tables:** Cell text must be string, use `str()` for numbers
