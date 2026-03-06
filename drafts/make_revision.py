#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Создание отформатированного акта инвентаризации"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ─── Поля страницы ───────────────────────────────────────────────────────────
section = doc.sections[0]
section.left_margin   = Cm(3)
section.right_margin  = Cm(2)
section.top_margin    = Cm(2)
section.bottom_margin = Cm(2)

# ─── Базовый стиль Normal ────────────────────────────────────────────────────
normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'
normal.font.size = Pt(12)

def set_font(run, bold=False, size=12, color=None):
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color

def para(text, align=WD_ALIGN_PARAGRAPH.LEFT, bold=False,
         size=12, space_before=0, space_after=6, color=None, line_spacing=1.5):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after  = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing      = line_spacing
    if text:
        run = p.add_run(text)
        set_font(run, bold=bold, size=size, color=color)
    return p

def add_horizontal_line(paragraph):
    """Добавить горизонтальную линию под абзацем"""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pBdr.append(bottom)
    pPr.append(pBdr)

def set_cell_background(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def set_row_height(row, height_cm):
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    trHeight = OxmlElement('w:trHeight')
    trHeight.set(qn('w:val'), str(int(Cm(height_cm).pt * 20)))
    trHeight.set(qn('w:hRule'), 'exact')
    trPr.append(trHeight)

def set_table_border(table):
    """Рамка вокруг всей таблицы + внутренние линии"""
    tbl = table._tbl
    tblPr = tbl.find(qn('w:tblPr'))
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement('w:tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '6')
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), '000000')
        tblBorders.append(el)
    tblPr.append(tblBorders)

def cell_para(cell, text, align=WD_ALIGN_PARAGRAPH.LEFT, bold=False, size=11, color=None):
    cell.paragraphs[0].clear()
    p = cell.paragraphs[0]
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(1)
    pf.space_after  = Pt(1)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing      = 1.0
    if text:
        run = p.add_run(text)
        set_font(run, bold=bold, size=size, color=color)
    return p

# ═══════════════════════════════════════════════════════════════════════════════
#  ШАПКА ДОКУМЕНТА
# ═══════════════════════════════════════════════════════════════════════════════

# Название организации
p_org = para('ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ КАМЫЗИН А.Н.',
             align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=12, space_after=2)

# ИНН / ОГРН placeholder
p_req = para('ИНН: _____________  |  ОГРНИП: _____________  |  г. Москва',
             align=WD_ALIGN_PARAGRAPH.CENTER, size=11, space_after=2)

# Разделитель
add_horizontal_line(p_req)
para('', space_after=4)

# Блок «УТВЕРЖДАЮ»
p_approve = doc.add_paragraph()
p_approve.alignment = WD_ALIGN_PARAGRAPH.RIGHT
p_approve.paragraph_format.space_after = Pt(4)
run = p_approve.add_run('УТВЕРЖДАЮ\nИндивидуальный предприниматель\nКамызин А.Н.\n\n«____» ____________ 2026 г.    _______________')
set_font(run, size=11)

para('', space_after=4)

# Название документа
para('АКТ ИНВЕНТАРИЗАЦИИ', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14, space_after=4)

# Реквизиты
p_num = doc.add_paragraph()
p_num.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_num.paragraph_format.space_after = Pt(4)
r1 = p_num.add_run('№ _______ от «04» марта 2026 г.')
set_font(r1, size=12)

# Место и период
para('г. Москва', align=WD_ALIGN_PARAGRAPH.LEFT, size=12, space_after=2)

# ─── ОСНОВАНИЕ ───────────────────────────────────────────────────────────────
para('ОСНОВАНИЕ ДЛЯ ПРОВЕДЕНИЯ ИНВЕНТАРИЗАЦИИ', bold=True, size=12, space_before=6, space_after=2)
p_base = para('Приказ № _______ от «____» ____________ 2026 г. о проведении инвентаризации.',
              size=12, space_after=2)
para('Период проведения инвентаризации: с «____» ____________ 2026 г. по «04» марта 2026 г.',
     size=12, space_after=6)

# ─── ОТВЕТСТВЕННЫЕ ЛИЦА ──────────────────────────────────────────────────────
para('СОСТАВ ИНВЕНТАРИЗАЦИОННОЙ КОМИССИИ:', bold=True, size=12, space_before=4, space_after=2)

resp_table = doc.add_table(rows=4, cols=4)
resp_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(resp_table)

hdr = ['Должность', 'ФИО', 'Подпись', 'Дата']
for j, h in enumerate(hdr):
    cell_para(resp_table.rows[0].cells[j], h, bold=True,
              align=WD_ALIGN_PARAGRAPH.CENTER,
              color=RGBColor(0xFF, 0xFF, 0xFF))
    set_cell_background(resp_table.rows[0].cells[j], '2F4F8F')
set_row_height(resp_table.rows[0], 0.9)

roles = ['Председатель комиссии', 'Член комиссии', 'Материально ответственное лицо']
for i, role in enumerate(roles, start=1):
    cell_para(resp_table.rows[i].cells[0], role, size=11)
    for j in range(1, 4):
        cell_para(resp_table.rows[i].cells[j], '', size=11)
    set_row_height(resp_table.rows[i], 0.85)

# Ширина колонок
widths = [Cm(5.5), Cm(5.5), Cm(3.0), Cm(3.0)]
for row in resp_table.rows:
    for j, cell in enumerate(row.cells):
        cell.width = widths[j]

para('', space_after=6)

# ═══════════════════════════════════════════════════════════════════════════════
#  ОСНОВНАЯ ТАБЛИЦА
# ═══════════════════════════════════════════════════════════════════════════════
para('ПЕРЕЧЕНЬ ИНВЕНТАРИЗИРУЕМЫХ ОБЪЕКТОВ:', bold=True, size=12, space_before=4, space_after=4)

# Заголовки
col_headers = ['№\nп/п', 'Наименование\nимущества', 'Ед.\nизм.', 'По учёту\n(кол-во)', 'Факт.\nналичие', 'Откло-\nнение', 'Цена\nруб.', 'Стоимость\nруб.', 'Комментарий']
col_widths = [Cm(1.0), Cm(5.0), Cm(1.5), Cm(1.8), Cm(1.8), Cm(1.8), Cm(2.2), Cm(2.7), Cm(3.2)]

EMPTY_ROWS = 8

main_table = doc.add_table(rows=2 + EMPTY_ROWS + 1, cols=len(col_headers))
main_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(main_table)

# Строка заголовков
for j, h in enumerate(col_headers):
    cell_para(main_table.rows[0].cells[j], h, bold=True,
              align=WD_ALIGN_PARAGRAPH.CENTER,
              color=RGBColor(0xFF, 0xFF, 0xFF))
    set_cell_background(main_table.rows[0].cells[j], '2F4F8F')
set_row_height(main_table.rows[0], 1.2)

# Нумерация
num_row = main_table.rows[1]
for j in range(len(col_headers)):
    cell_para(num_row.cells[j], str(j + 1),
              align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
    set_cell_background(num_row.cells[j], 'D9E1F2')
set_row_height(num_row, 0.6)

# Пустые строки данных
for i in range(EMPTY_ROWS):
    row = main_table.rows[2 + i]
    cell_para(row.cells[0], str(i + 1), align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
    for j in range(1, len(col_headers)):
        cell_para(row.cells[j], '', size=11)
    set_row_height(row, 0.75)
    # Чётные строки слегка подсвечены
    if i % 2 == 1:
        for cell in row.cells:
            set_cell_background(cell, 'F2F2F2')

# Итоговая строка
total_row = main_table.rows[2 + EMPTY_ROWS]
cell_para(total_row.cells[0], 'Итого', bold=True,
          align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
# Merge первые 7 ячеек для «Итого»
for idx in range(1, 7):
    cell_para(total_row.cells[idx], '', size=11)
cell_para(total_row.cells[7], '0,00', bold=True,
          align=WD_ALIGN_PARAGRAPH.RIGHT, size=11)
cell_para(total_row.cells[8], '', size=11)
for cell in total_row.cells:
    set_cell_background(cell, 'FFE699')
set_row_height(total_row, 0.85)

# Ширины
for row in main_table.rows:
    for j, cell in enumerate(row.cells):
        cell.width = col_widths[j]

para('', space_after=6)

# ═══════════════════════════════════════════════════════════════════════════════
#  ИТОГИ ИНВЕНТАРИЗАЦИИ
# ═══════════════════════════════════════════════════════════════════════════════
para('ИТОГИ ИНВЕНТАРИЗАЦИИ', bold=True, size=13, space_before=6, space_after=4,
     align=WD_ALIGN_PARAGRAPH.CENTER)

results = [
    ('Наименование показателя', 'По учёту', 'Фактически', 'Отклонение'),
    ('Общее количество позиций (шт.)', '', '', ''),
    ('Итоговая стоимость (руб.)', '', '', ''),
    ('Излишки (руб.)', '', '', ''),
    ('Недостача (руб.)', '', '', ''),
]

res_table = doc.add_table(rows=len(results), cols=4)
res_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(res_table)
r_widths = [Cm(7.0), Cm(3.0), Cm(3.0), Cm(3.0)]

for i, row_data in enumerate(results):
    for j, val in enumerate(row_data):
        a = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else WD_ALIGN_PARAGRAPH.LEFT
        b = (i == 0)
        c = RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else None
        cell_para(res_table.rows[i].cells[j], val, bold=b, align=a, size=11, color=c)
        if i == 0:
            set_cell_background(res_table.rows[i].cells[j], '2F4F8F')
        elif i % 2 == 0:
            set_cell_background(res_table.rows[i].cells[j], 'F2F2F2')
    set_row_height(res_table.rows[i], 0.8)

for row in res_table.rows:
    for j, cell in enumerate(row.cells):
        cell.width = r_widths[j]

para('', space_after=6)

# ─── СООТВЕТСТВИЕ УЧЁТНЫМ ДАННЫМ ─────────────────────────────────────────────
para('О СООТВЕТСТВИИ ФАКТИЧЕСКОГО НАЛИЧИЯ УЧЁТНЫМ ДАННЫМ:', bold=True,
     size=12, space_before=4, space_after=2)
para('По результатам инвентаризации установлено:', size=12, space_after=2)

conform_items = [
    '☐  Фактическое наличие имущества соответствует данным бухгалтерского учёта.',
    '☐  Выявлены излишки. Акт об излишках № _______ от «____» ____________ 2026 г.',
    '☐  Выявлена недостача. Акт о недостаче № _______ от «____» ____________ 2026 г.',
]
for item in conform_items:
    para(item, size=12, space_before=1, space_after=1)

para('', space_after=6)

# ═══════════════════════════════════════════════════════════════════════════════
#  БЛОК ПОДПИСЕЙ
# ═══════════════════════════════════════════════════════════════════════════════
para('ПОДПИСИ УЧАСТНИКОВ ИНВЕНТАРИЗАЦИИ', bold=True, size=13,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_before=6, space_after=4)

sign_headers = ['Должность', 'ФИО', 'Подпись', 'Дата подписания']
sign_roles   = [
    'Председатель комиссии',
    'Член комиссии',
    'Материально ответственное лицо',
    'Бухгалтер',
]
sign_widths = [Cm(5.5), Cm(5.0), Cm(2.8), Cm(3.7)]

sign_table = doc.add_table(rows=1 + len(sign_roles), cols=4)
sign_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(sign_table)

for j, h in enumerate(sign_headers):
    cell_para(sign_table.rows[0].cells[j], h, bold=True,
              align=WD_ALIGN_PARAGRAPH.CENTER,
              color=RGBColor(0xFF, 0xFF, 0xFF))
    set_cell_background(sign_table.rows[0].cells[j], '2F4F8F')
set_row_height(sign_table.rows[0], 0.9)

for i, role in enumerate(sign_roles, start=1):
    cell_para(sign_table.rows[i].cells[0], role, size=11)
    for j in range(1, 4):
        cell_para(sign_table.rows[i].cells[j], '', size=11)
    set_row_height(sign_table.rows[i], 0.9)

for row in sign_table.rows:
    for j, cell in enumerate(row.cells):
        cell.width = sign_widths[j]

para('', space_after=6)

# ─── МЕСТО ДЛЯ ПЕЧАТИ ────────────────────────────────────────────────────────
p_seal = doc.add_paragraph()
p_seal.paragraph_format.space_after = Pt(2)
r = p_seal.add_run('М.П.  (место для печати организации)')
set_font(r, size=11)

para('', space_after=6)

# ═══════════════════════════════════════════════════════════════════════════════
#  БЛОК ЗАМЕЧАНИЙ ПРОВЕРЯЮЩИХ
# ═══════════════════════════════════════════════════════════════════════════════
para('ЗАМЕЧАНИЯ ПРОВЕРЯЮЩИХ', bold=True, size=12, space_before=6, space_after=2)

remarks_table = doc.add_table(rows=4, cols=3)
remarks_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(remarks_table)

rem_headers = ['Проверяющий (ФИО, должность)', 'Замечание', 'Подпись и дата']
rem_widths  = [Cm(6.0), Cm(7.0), Cm(4.0)]
for j, h in enumerate(rem_headers):
    cell_para(remarks_table.rows[0].cells[j], h, bold=True,
              align=WD_ALIGN_PARAGRAPH.CENTER,
              color=RGBColor(0xFF, 0xFF, 0xFF))
    set_cell_background(remarks_table.rows[0].cells[j], '2F4F8F')
set_row_height(remarks_table.rows[0], 0.85)

for i in range(1, 4):
    for j in range(3):
        cell_para(remarks_table.rows[i].cells[j], '', size=11)
    set_row_height(remarks_table.rows[i], 0.85)

for row in remarks_table.rows:
    for j, cell in enumerate(row.cells):
        cell.width = rem_widths[j]

para('', space_after=6)

# ═══════════════════════════════════════════════════════════════════════════════
#  ПРИМЕЧАНИЯ
# ═══════════════════════════════════════════════════════════════════════════════
para('ПРИМЕЧАНИЯ', bold=True, size=12, space_before=4, space_after=2)

notes_table = doc.add_table(rows=4, cols=1)
notes_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(notes_table)
cell_para(notes_table.rows[0].cells[0], 'Текст примечания:', bold=True, size=11)
set_cell_background(notes_table.rows[0].cells[0], 'D9E1F2')
for i in range(1, 4):
    cell_para(notes_table.rows[i].cells[0], '', size=11)
    set_row_height(notes_table.rows[i], 0.85)
for row in notes_table.rows:
    row.cells[0].width = Cm(17.0)

para('', space_after=4)

# Финальная сноска
p_footer = doc.add_paragraph()
p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_footer.paragraph_format.space_before = Pt(10)
add_horizontal_line(p_footer)
r = p_footer.add_run('Акт составлен в ___ экземплярах. Дата составления: «04» марта 2026 г.')
set_font(r, size=11)

# ─── СОХРАНЕНИЕ ──────────────────────────────────────────────────────────────
out_path = '/home/clawdbot/.openclaw/workspace/drafts/акт_инвентаризации_оформленный.docx'
doc.save(out_path)
print(f'OK: {out_path}')
