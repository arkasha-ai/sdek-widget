# Excel Styles Reference

## Color Palette (Professional)

| Use | Color Code | Description |
|-----|-----------|-------------|
| Header bg | 4472C4 | Blue |
| Header text | FFFFFF | White |
| Success | C6EFCE | Light green |
| Warning | FFEB9C | Light yellow |
| Error | FFC7CE | Light red |
| Alternating | F2F2F2 | Light gray |
| Accent | ED7D31 | Orange |

## Font Presets

```python
header_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
body_font = Font(name="Calibri", size=10)
title_font = Font(name="Calibri", bold=True, size=14)
link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")
```

## Alignment Presets

```python
center = Alignment(horizontal="center", vertical="center", wrap_text=True)
left_wrap = Alignment(horizontal="left", vertical="top", wrap_text=True)
right_num = Alignment(horizontal="right", vertical="center")
```

## Dashboard Layout

```
Row 1-2:   Title + date range (merged cells)
Row 3:     KPI cards (merged 3-col blocks)
Row 5-20:  Main chart
Row 22-35: Detail table
Row 37+:   Notes / appendix
```

## Print Setup

```python
ws.page_setup.orientation = "landscape"
ws.page_setup.paperSize = ws.PAPERSIZE_A4
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0  # Auto pages
ws.print_area = "A1:G50"
ws.print_title_rows = "1:1"  # Repeat header
```
