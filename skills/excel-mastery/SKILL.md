---
name: excel-mastery
description: "Create and edit Excel files with openpyxl. Charts, formatting, dashboards, multi-sheet workbooks. Use when: (1) creating spreadsheets, (2) generating reports in XLSX, (3) data tables with formatting, (4) charts and dashboards, (5) CSV to Excel conversion. Triggers on: excel, xlsx, таблица, spreadsheet, dashboard, chart, отчёт в excel."
---

# Excel Mastery

> Create professional Excel workbooks with openpyxl. No Excel installation needed.

## Quick Start

```python
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "Report"

# Header row
headers = ["Name", "Value", "Status"]
for col, h in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=11)
    cell.fill = PatternFill("solid", fgColor="4472C4")
    cell.alignment = Alignment(horizontal="center")

# Data
data = [("Item A", 100, "OK"), ("Item B", 250, "Warning"), ("Item C", 50, "Critical")]
for ri, row in enumerate(data, 2):
    for ci, val in enumerate(row, 1):
        ws.cell(row=ri, column=ci, value=val)

# Auto-width columns
for col in range(1, len(headers) + 1):
    ws.column_dimensions[get_column_letter(col)].width = 15

# Freeze header
ws.freeze_panes = "A2"

# Borders
thin = Side(style="thin")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
for row in ws.iter_rows(min_row=1, max_row=len(data)+1, max_col=len(headers)):
    for cell in row:
        cell.border = border

wb.save("report.xlsx")
```

## Key Patterns

### Multiple Sheets
```python
ws2 = wb.create_sheet("Summary")
ws3 = wb.create_sheet("Raw Data")
```

### Charts
```python
chart = BarChart()
chart.title = "Sales by Month"
chart.y_axis.title = "Revenue"
chart.x_axis.title = "Month"

data_ref = Reference(ws, min_col=2, min_row=1, max_row=13)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=13)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
chart.style = 10
ws.add_chart(chart, "E2")
```

### Conditional Formatting
```python
from openpyxl.formatting.rule import CellIsRule

red_fill = PatternFill("solid", fgColor="FFC7CE")
green_fill = PatternFill("solid", fgColor="C6EFCE")

ws.conditional_formatting.add("C2:C100",
    CellIsRule(operator="equal", formula=['"Critical"'], fill=red_fill))
ws.conditional_formatting.add("C2:C100",
    CellIsRule(operator="equal", formula=['"OK"'], fill=green_fill))
```

### Formulas
```python
ws["D2"] = "=SUM(B2:B100)"
ws["D3"] = "=AVERAGE(B2:B100)"
ws["D4"] = '=COUNTIF(C2:C100,"OK")'
```

### Number Formats
```python
cell.number_format = '#,##0.00'      # 1,234.56
cell.number_format = '0.0%'          # 85.5%
cell.number_format = 'DD.MM.YYYY'    # 25.03.2026
cell.number_format = '#,##0 "руб."'  # 1,234 руб.
```

### CSV to Excel
```python
import csv
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
with open("data.csv", encoding="utf-8") as f:
    for row in csv.reader(f):
        ws.append(row)
wb.save("data.xlsx")
```

## Styling Reference

See `references/excel-styles.md` for complete styling guide.

## Common Pitfalls

1. **Column width:** Set explicitly, auto-width doesn't exist in openpyxl
2. **Formulas:** Use English function names (SUM, not СУММ)
3. **Dates:** Use Python datetime objects, not strings
4. **Large files:** Use `write_only=True` mode for 100K+ rows
5. **Encoding:** openpyxl handles UTF-8 natively, Cyrillic works
