#!/usr/bin/env python3
"""Convert CSV files to formatted Excel workbooks.

Usage:
    python csv_to_excel.py input.csv output.xlsx
    python csv_to_excel.py file1.csv file2.csv --output combined.xlsx
    python csv_to_excel.py file1.csv file2.csv --output report.xlsx --sheet-names "Sheet1" "Sheet2"
"""

import csv
import sys
import argparse
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter


def detect_encoding(filepath):
    """Try common encodings."""
    for enc in ["utf-8", "utf-8-sig", "cp1251", "cp1252", "latin1"]:
        try:
            with open(filepath, encoding=enc) as f:
                f.read(1024)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def add_csv_to_sheet(ws, csv_path, encoding=None):
    """Load CSV data into worksheet with formatting."""
    if not encoding:
        encoding = detect_encoding(csv_path)
    
    with open(csv_path, encoding=encoding) as f:
        reader = csv.reader(f)
        for ri, row in enumerate(reader, 1):
            for ci, val in enumerate(row, 1):
                ws.cell(row=ri, column=ci, value=val)
    
    # Format header
    header_fill = PatternFill("solid", fgColor="4472C4")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    
    max_col = ws.max_column
    max_row = ws.max_row
    
    for col in range(1, max_col + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Borders + auto-width
    col_widths = {}
    for row in ws.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
        for cell in row:
            cell.border = border
            col = cell.column
            val_len = len(str(cell.value or ""))
            # Rough width for Cyrillic (wider chars)
            w = val_len * 1.2 + 2
            col_widths[col] = max(col_widths.get(col, 8), min(w, 50))
    
    for col, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width
    
    # Freeze header
    ws.freeze_panes = "A2"


def main():
    parser = argparse.ArgumentParser(description="CSV to Excel converter")
    parser.add_argument("files", nargs="+", help="CSV file(s)")
    parser.add_argument("--output", "-o", help="Output XLSX path")
    parser.add_argument("--sheet-names", nargs="*", help="Custom sheet names")
    args = parser.parse_args()
    
    files = [Path(f) for f in args.files]
    
    if len(files) == 1 and not args.output:
        output = files[0].with_suffix(".xlsx")
    elif args.output:
        output = Path(args.output)
    else:
        output = Path("combined.xlsx")
    
    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet
    
    for i, csv_path in enumerate(files):
        if args.sheet_names and i < len(args.sheet_names):
            name = args.sheet_names[i][:31]
        else:
            name = csv_path.stem[:31]
        
        ws = wb.create_sheet(title=name)
        add_csv_to_sheet(ws, csv_path)
        print(f"  Added: {name} ({ws.max_row} rows)")
    
    wb.save(str(output))
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
