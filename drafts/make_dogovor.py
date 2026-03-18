#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy
from lxml import etree

doc = Document()

# ── Page margins ────────────────────────────────────────────────
section = doc.sections[0]
section.page_width  = Cm(21)
section.page_height = Cm(29.7)
section.left_margin   = Cm(2.5)
section.right_margin  = Cm(2)
section.top_margin    = Cm(2)
section.bottom_margin = Cm(2)

# ── Color palette ───────────────────────────────────────────────
NAVY   = RGBColor(0x1a, 0x27, 0x44)
BLUE   = RGBColor(0x25, 0x63, 0xeb)
BLUE_L = RGBColor(0xdb, 0xe4, 0xfe)
AMBER  = RGBColor(0xf5, 0x9e, 0x0b)
AMB_L  = RGBColor(0xfe, 0xf3, 0xc7)
GREEN  = RGBColor(0x05, 0x96, 0x69)
GRN_L  = RGBColor(0xd1, 0xfa, 0xe5)
RED    = RGBColor(0xdc, 0x26, 0x26)
RED_L  = RGBColor(0xfe, 0xe2, 0xe2)
GRAY9  = RGBColor(0x11, 0x18, 0x27)
GRAY6  = RGBColor(0x4b, 0x55, 0x63)
GRAY4  = RGBColor(0x9c, 0xa3, 0xaf)
WHITE  = RGBColor(0xff, 0xff, 0xff)
GRAY1  = RGBColor(0xf3, 0xf4, 0xf6)
GRAY2  = RGBColor(0xe5, 0xe7, 0xeb)

# ── Helpers ─────────────────────────────────────────────────────
def set_cell_bg(cell, color: RGBColor):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    hex_color = f'{color[0]:02X}{color[1]:02X}{color[2]:02X}'
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  hex_color)
    tcPr.append(shd)

def set_cell_border(cell, top=None, bottom=None, left=None, right=None):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        if val:
            el = OxmlElement(f'w:{side}')
            el.set(qn('w:val'),   val.get('val', 'single'))
            el.set(qn('w:sz'),    val.get('sz', '4'))
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), val.get('color', 'auto'))
            tcBorders.append(el)
    tcPr.append(tcBorders)

def clear_numbering(p):
    """Remove any inherited list/numbering from a paragraph."""
    pPr = p._p.get_or_add_pPr()
    numPr = pPr.find(qn('w:numPr'))
    if numPr is not None:
        pPr.remove(numPr)

def cell_para(cell, text, bold=False, italic=False, size=10,
              color=None, align=WD_ALIGN_PARAGRAPH.LEFT,
              space_before=0, space_after=0):
    # Clear existing paragraphs then add
    tc = cell._tc
    for p in tc.findall(qn('w:p')):
        tc.remove(p)
    p = cell.add_paragraph(style='Normal')
    clear_numbering(p)
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    run = p.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.size  = Pt(size)
    run.font.color.rgb = color or GRAY9
    return p

def add_para(text, bold=False, size=10.5, color=None,
             align=WD_ALIGN_PARAGRAPH.LEFT,
             space_before=2, space_after=2, italic=False):
    p = doc.add_paragraph(style='Normal')
    clear_numbering(p)
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    run = p.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.size  = Pt(size)
    run.font.color.rgb = color or GRAY9
    return p

def add_section_title(num_text, title_text, icon=''):
    p = doc.add_paragraph(style='Normal')
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(6)
    # colored bar: use a shaded 1×1 table as a visual divider
    # Section label
    r1 = p.add_run(f'{icon}  {num_text}  ')
    r1.font.size  = Pt(8)
    r1.font.color.rgb = GRAY4
    r1.bold = True
    r2 = p.add_run(title_text)
    r2.font.size = Pt(13)
    r2.font.color.rgb = NAVY
    r2.bold = True
    return p

def add_clause(num, text, indent=True):
    p = doc.add_paragraph(style='Normal')
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)
    if indent:
        p.paragraph_format.left_indent = Cm(0.5)
    rn = p.add_run(f'{num}  ')
    rn.bold = True
    rn.font.size  = Pt(10)
    rn.font.color.rgb = BLUE
    rt = p.add_run(text)
    rt.font.size  = Pt(10)
    rt.font.color.rgb = GRAY6
    return p

def add_highlight(text, title=None, bg=BLUE_L, border_color=BLUE, icon=''):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = tbl.cell(0, 0)
    set_cell_bg(cell, bg)
    hex_border = f'{border_color[0]:02X}{border_color[1]:02X}{border_color[2]:02X}'
    set_cell_border(cell,
        left={'val':'single','sz':'18','color': hex_border},
        top={'val':'none','sz':'0','color':'auto'},
        bottom={'val':'none','sz':'0','color':'auto'},
        right={'val':'none','sz':'0','color':'auto'},
    )
    tc = cell._tc
    for p_el in tc.findall(qn('w:p')):
        tc.remove(p_el)
    if title:
        p1 = cell.add_paragraph(style='Normal')
        p1.paragraph_format.space_before = Pt(4)
        p1.paragraph_format.space_after  = Pt(2)
        p1.paragraph_format.left_indent  = Cm(0.3)
        r = p1.add_run(f'{icon} {title}')
        r.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = GRAY9
    p2 = cell.add_paragraph(style='Normal')
    clear_numbering(p2)
    p2.paragraph_format.space_before = Pt(1)
    p2.paragraph_format.space_after  = Pt(5)
    p2.paragraph_format.left_indent  = Cm(0.3)
    r2 = p2.add_run(text)
    r2.font.size  = Pt(10)
    r2.font.color.rgb = GRAY6
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

def make_table(headers, rows, col_widths=None):
    n_cols = len(headers)
    tbl = doc.add_table(rows=1 + len(rows), cols=n_cols)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Header row
    hdr = tbl.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_bg(cell, NAVY)
        cell_para(cell, h, bold=True, size=9, color=WHITE)

    # Data rows
    for ri, row_data in enumerate(rows):
        row = tbl.rows[ri + 1]
        bg = GRAY1 if ri % 2 == 0 else WHITE
        for ci, val in enumerate(row_data):
            cell = row.cells[ci]
            set_cell_bg(cell, bg)
            is_bold = ci == 0
            cell_para(cell, val, bold=is_bold, size=9.5, color=GRAY6 if not is_bold else GRAY9)

    # Column widths
    if col_widths:
        for ci, w in enumerate(col_widths):
            for row in tbl.rows:
                row.cells[ci].width = Cm(w)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return tbl

def add_bullet(text, color=BLUE):
    p = doc.add_paragraph(style='Normal')
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after  = Pt(1)
    p.paragraph_format.left_indent  = Cm(0.5)
    rb = p.add_run('◆  ')
    rb.font.size  = Pt(7)
    rb.font.color.rgb = color
    rt = p.add_run(text)
    rt.font.size  = Pt(10)
    rt.font.color.rgb = GRAY6
    return p

def page_break():
    doc.add_page_break()

def thin_line():
    p = doc.add_paragraph(style='Normal')
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'),   'single')
    bottom.set(qn('w:sz'),    '4')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'E5E7EB')
    pBdr.append(bottom)
    pPr.append(pBdr)

# ══════════════════════════════════════════════════════════════
#  COVER PAGE
# ══════════════════════════════════════════════════════════════
cover_tbl = doc.add_table(rows=1, cols=1)
cover_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
c = cover_tbl.cell(0, 0)
set_cell_bg(c, NAVY)
c.width = Cm(16)
tc = c._tc
for p_el in tc.findall(qn('w:p')):
    tc.remove(p_el)

# Badge
pb = c.add_paragraph(style='Normal')
pb.paragraph_format.space_before = Pt(30)
pb.paragraph_format.space_after  = Pt(6)
pb.paragraph_format.left_indent  = Cm(1)
rb = pb.add_run('СУБАРЕНДА НЕЖИЛОГО ПОМЕЩЕНИЯ')
rb.font.size = Pt(8)
rb.font.color.rgb = RGBColor(0x9c, 0xa3, 0xaf)
rb.bold = True

# Title
pt = c.add_paragraph(style='Normal')
pt.paragraph_format.space_before = Pt(4)
pt.paragraph_format.space_after  = Pt(4)
pt.paragraph_format.left_indent  = Cm(1)
rt = pt.add_run('Договор субаренды')
rt.font.size = Pt(26)
rt.font.color.rgb = WHITE
rt.bold = True

# Subtitle
ps = c.add_paragraph(style='Normal')
ps.paragraph_format.space_before = Pt(2)
ps.paragraph_format.space_after  = Pt(24)
ps.paragraph_format.left_indent  = Cm(1)
rs = ps.add_run('нежилого помещения  ·  пекарня')
rs.font.size = Pt(12)
rs.font.color.rgb = RGBColor(0x9c, 0xa3, 0xaf)

# Meta line
meta_items = [
    ('ДОГОВОР №', '_______'),
    ('ДАТА', '«___» ________ 2025 г.'),
    ('ПЛОЩАДЬ', '___ кв.м'),
    ('СРОК', '11 месяцев'),
    ('ПЕРИОД', '01.11.2025 — 01.10.2026'),
]
for label, val in meta_items:
    pm = c.add_paragraph(style='Normal')
    pm.paragraph_format.space_before = Pt(3)
    pm.paragraph_format.space_after  = Pt(1)
    pm.paragraph_format.left_indent  = Cm(1)
    rl = pm.add_run(f'{label}:  ')
    rl.font.size = Pt(8)
    rl.font.color.rgb = RGBColor(0x6b, 0x72, 0x80)
    rv = pm.add_run(val)
    rv.font.size = Pt(10)
    rv.font.color.rgb = WHITE
    rv.bold = True

pb2 = c.add_paragraph(style='Normal')
pb2.paragraph_format.space_before = Pt(20)
pb2.paragraph_format.space_after  = Pt(16)
pb2.paragraph_format.left_indent  = Cm(1)
rb2 = pb2.add_run('г. Москва')
rb2.font.size = Pt(9)
rb2.font.color.rgb = RGBColor(0x6b, 0x72, 0x80)

doc.add_paragraph().paragraph_format.space_after = Pt(8)

# ══════════════════════════════════════════════════════════════
#  KEY TERMS SUMMARY (4-column table)
# ══════════════════════════════════════════════════════════════
add_para('КЛЮЧЕВЫЕ УСЛОВИЯ ДОГОВОРА', bold=True, size=8, color=GRAY4, space_before=10, space_after=6)

kv_tbl = doc.add_table(rows=1, cols=4)
kv_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
kv_data = [
    ('Аренда до конца 2025', '360 000 ₽/мес', 'авансом, до 1-го числа', BLUE_L, BLUE),
    ('Аренда с 2026 года', '378 000 ₽/мес', '+ коммунальные услуги', AMB_L, AMBER),
    ('Обеспечит. платёж', '378 000 ₽', 'в день подписания', GRN_L, GREEN),
    ('Пеня за просрочку', '1% в день', 'от суммы долга по аренде', RED_L, RED),
]
for i, (label, val, sub, bg, acc) in enumerate(kv_data):
    cell = kv_tbl.cell(0, i)
    set_cell_bg(cell, bg)
    tc2 = cell._tc
    for p_el in tc2.findall(qn('w:p')):
        tc2.remove(p_el)
    pl = cell.add_paragraph(style='Normal')
    pl.paragraph_format.space_before = Pt(6)
    pl.paragraph_format.space_after  = Pt(2)
    pl.paragraph_format.left_indent  = Cm(0.2)
    rl2 = pl.add_run(label.upper())
    rl2.font.size = Pt(7.5)
    rl2.font.color.rgb = acc
    rl2.bold = True
    pv = cell.add_paragraph(style='Normal')
    pv.paragraph_format.left_indent  = Cm(0.2)
    pv.paragraph_format.space_after  = Pt(1)
    rv2 = pv.add_run(val)
    rv2.font.size = Pt(12)
    rv2.font.color.rgb = GRAY9
    rv2.bold = True
    ps2 = cell.add_paragraph(style='Normal')
    ps2.paragraph_format.left_indent  = Cm(0.2)
    ps2.paragraph_format.space_after  = Pt(6)
    rs2 = ps2.add_run(sub)
    rs2.font.size = Pt(8.5)
    rs2.font.color.rgb = GRAY4

doc.add_paragraph().paragraph_format.space_after = Pt(6)

# ══════════════════════════════════════════════════════════════
#  PARTIES
# ══════════════════════════════════════════════════════════════
add_para('СТОРОНЫ ДОГОВОРА', bold=True, size=8, color=GRAY4, space_before=8, space_after=6)

pt_tbl = doc.add_table(rows=1, cols=3)
pt_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

def fill_party(cell, role, role_color, name, details, bg):
    set_cell_bg(cell, bg)
    tc3 = cell._tc
    for p_el in tc3.findall(qn('w:p')):
        tc3.remove(p_el)
    pr = cell.add_paragraph(style='Normal')
    pr.paragraph_format.space_before = Pt(8)
    pr.paragraph_format.space_after  = Pt(4)
    pr.paragraph_format.left_indent  = Cm(0.3)
    rr = pr.add_run(role)
    rr.font.size = Pt(8.5)
    rr.font.color.rgb = role_color
    rr.bold = True
    pn = cell.add_paragraph(style='Normal')
    pn.paragraph_format.space_after  = Pt(4)
    pn.paragraph_format.left_indent  = Cm(0.3)
    rn2 = pn.add_run(name)
    rn2.font.size = Pt(11)
    rn2.font.color.rgb = GRAY9
    rn2.bold = True
    for line in details:
        pd = cell.add_paragraph(style='Normal')
        pd.paragraph_format.space_after  = Pt(1)
        pd.paragraph_format.left_indent  = Cm(0.3)
        rd = pd.add_run(line)
        rd.font.size = Pt(9)
        rd.font.color.rgb = GRAY6
    cell.add_paragraph(style='Normal').paragraph_format.space_after = Pt(8)

fill_party(pt_tbl.cell(0,0), 'АРЕНДАТОР', BLUE,
    'ООО «Перспектива М»',
    ['ОГРН: ___________', 'ИНН: _________',
     'Ген. директор:', 'Гусман Рустем Гусманович'],
    BLUE_L)

# Divider cell
dc = pt_tbl.cell(0,1)
set_cell_bg(dc, WHITE)
tc4 = dc._tc
for p_el in tc4.findall(qn('w:p')):
    tc4.remove(p_el)
pd2 = dc.add_paragraph(style='Normal')
pd2.alignment = WD_ALIGN_PARAGRAPH.CENTER
pd2.paragraph_format.space_before = Pt(30)
rd2 = pd2.add_run('⇄')
rd2.font.size = Pt(18)
rd2.font.color.rgb = GRAY4

fill_party(pt_tbl.cell(0,2), 'СУБАРЕНДАТОР', AMBER,
    'ИП _______________',
    ['ИНН: _______', 'ОГРНИП: _______________',
     'Действует от своего имени', ''],
    AMB_L)

doc.add_paragraph().paragraph_format.space_after = Pt(4)

thin_line()

# ══════════════════════════════════════════════════════════════
#  SECTION 1: ПРЕДМЕТ
# ══════════════════════════════════════════════════════════════
add_section_title('РАЗДЕЛ 1', 'Предмет договора', '🏠')

add_clause('1.1', 'Арендатор передаёт Субарендатору во временное владение и пользование нежилое помещение площадью ___ кв.м по Акту приёма-передачи.')
add_clause('1.2', 'Назначение помещения: размещение пекарни. Иное использование — только с письменного согласия Арендатора.')

add_highlight(
    '01.11.2025 — начало срока  |  Передача помещения: в течение 3 рабочих дней после подписания\n01.10.2026 — окончание срока (11 месяцев, включительно)',
    title='Сроки субаренды',
    bg=GRN_L, border_color=GREEN, icon='📅'
)

add_clause('1.7', 'Арендатор гарантирует: помещение не заложено, не арестовано, не обременено правами третьих лиц.')

thin_line()

# ══════════════════════════════════════════════════════════════
#  SECTION 2: ПЕРЕДАЧА
# ══════════════════════════════════════════════════════════════
add_section_title('РАЗДЕЛ 2', 'Порядок передачи помещения', '🔑')

add_clause('2.1', 'Помещение передаётся в течение 3 рабочих дней с момента подписания договора. Помещение должно быть чистым и освобождённым от имущества Арендатора.')
add_clause('2.2', 'В последний день срока Субарендатор возвращает помещение в исходном состоянии (нормальный износ допускается).')

add_highlight(
    'При задержке более 5 календарных дней: Арендатор вправе переместить имущество Субарендатора на склад ответственного хранения.\nСтоимость хранения: 36 000 ₽ за каждый кв.м в месяц.\nПо истечении 2 месяцев — имущество переходит в собственность Арендатора.',
    title='Просрочка освобождения помещения',
    bg=AMB_L, border_color=AMBER, icon='⚠️'
)

add_clause('2.6', 'Все неотделимые улучшения переходят в собственность Арендатора без компенсации.')

thin_line()

# ══════════════════════════════════════════════════════════════
#  SECTION 3: ПРАВА И ОБЯЗАННОСТИ (two-column table)
# ══════════════════════════════════════════════════════════════
add_section_title('РАЗДЕЛ 3', 'Права и обязанности сторон', '📋')

ro_tbl = doc.add_table(rows=1, cols=2)
ro_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

def fill_ro(cell, title, title_color, items, bg, bullet_color):
    set_cell_bg(cell, bg)
    tc5 = cell._tc
    for p_el in tc5.findall(qn('w:p')):
        tc5.remove(p_el)
    ph = cell.add_paragraph(style='Normal')
    ph.paragraph_format.space_before = Pt(8)
    ph.paragraph_format.space_after  = Pt(6)
    ph.paragraph_format.left_indent  = Cm(0.3)
    rh = ph.add_run(title)
    rh.font.size = Pt(8.5)
    rh.font.color.rgb = title_color
    rh.bold = True
    for item in items:
        pi = cell.add_paragraph(style='Normal')
        pi.paragraph_format.space_before = Pt(2)
        pi.paragraph_format.space_after  = Pt(2)
        pi.paragraph_format.left_indent  = Cm(0.5)
        rb3 = pi.add_run('◆  ')
        rb3.font.size  = Pt(6)
        rb3.font.color.rgb = bullet_color
        ri = pi.add_run(item)
        ri.font.size  = Pt(9.5)
        ri.font.color.rgb = GRAY6
    cell.add_paragraph(style='Normal').paragraph_format.space_after = Pt(6)

fill_ro(ro_tbl.cell(0,0), 'АРЕНДАТОР ОБЯЗАН', BLUE,
    ['Передать помещение по Акту в срок',
     'Обеспечить круглосуточный доступ',
     'Принять помещение при возврате',
     'Предоставить правоустанавливающие документы по запросу',
     'Уведомлять об изменении реквизитов (в течение 3 дней)',
     'Проводить капитальный ремонт за свой счёт'],
    BLUE_L, BLUE)

fill_ro(ro_tbl.cell(0,1), 'СУБАРЕНДАТОР ОБЯЗАН', AMBER,
    ['Принять помещение по Акту в срок',
     'Своевременно вносить арендную плату',
     'Использовать помещение только как пекарню',
     'Поддерживать чистоту и порядок',
     'Самостоятельно получать все лицензии и разрешения',
     'Не хранить опасные вещества',
     'Соблюдать пожарную и санитарную безопасность',
     'Не передавать помещение в субаренду третьим лицам',
     'Не использовать адрес как юридический адрес ЮЛ'],
    AMB_L, AMBER)

doc.add_paragraph().paragraph_format.space_after = Pt(4)

ro_tbl2 = doc.add_table(rows=1, cols=2)
ro_tbl2.alignment = WD_TABLE_ALIGNMENT.LEFT

fill_ro(ro_tbl2.cell(0,0), 'АРЕНДАТОР ВПРАВЕ', GREEN,
    ['Входить для проверки (без вмешательства в деятельность)',
     'Запрашивать документы о деятельности Субарендатора',
     'Приостанавливать коммунальные услуги при задолженности',
     'Привлекать управляющие организации'],
    GRN_L, GREEN)

fill_ro(ro_tbl2.cell(0,1), 'СУБАРЕНДАТОР ВПРАВЕ', GREEN,
    ['Вести хозяйственную деятельность (пекарня)',
     'Проводить ремонт с письменного согласия Арендатора',
     'Размещать рекламу с письменного согласия',
     'Вывезти отделимые улучшения с согласия Арендатора',
     'Преимущественное право на продление договора'],
    GRN_L, GREEN)

doc.add_paragraph().paragraph_format.space_after = Pt(4)
thin_line()

# ══════════════════════════════════════════════════════════════
#  SECTION 4: ПЛАТЕЖИ
# ══════════════════════════════════════════════════════════════
add_section_title('РАЗДЕЛ 4', 'Платежи и расчёты', '💳')

make_table(
    ['Платёж', 'Период', 'Сумма', 'Срок оплаты'],
    [
        ('Аренда (постоянная)', 'до конца 2025 г.', '360 000 ₽/мес', 'до 1-го числа, авансом'),
        ('Аренда (постоянная)', 'с января 2026 г.', '378 000 ₽/мес', 'до 1-го числа, авансом'),
        ('Аренда (переменная)', 'ежемесячно', 'по счёту (коммуналка)', 'в течение 3 банк. дней'),
        ('Обеспечительный платёж', 'разовый', '378 000 ₽', 'в день подписания'),
        ('Аренда за 1-й месяц', 'разовый', '360 000 ₽', 'в день подписания'),
    ],
    col_widths=[4.5, 3.5, 3.5, 4.5]
)

add_highlight(
    'Аренда за 1-й месяц: 360 000 ₽ + Обеспечительный платёж: 378 000 ₽ = Итого: 738 000 ₽',
    title='Итого к оплате в день подписания договора',
    bg=AMB_L, border_color=AMBER, icon='📌'
)

add_clause('4.1.3', 'Арендатор вправе ежегодно индексировать постоянную часть арендной платы в одностороннем порядке, направив уведомление за 30 дней (без доп. соглашения).')

thin_line()

# ══════════════════════════════════════════════════════════════
#  SECTION 5: ОБЕСПЕЧИТЕЛЬНЫЙ ПЛАТЁЖ
# ══════════════════════════════════════════════════════════════
add_section_title('РАЗДЕЛ 5', 'Обеспечительный платёж', '🔒')

make_table(
    ['Сценарий', 'Что происходит с платежом'],
    [
        ('Нормальное окончание договора', 'Возвращается в течение 30 дней после возврата помещения'),
        ('Досрочный выход по инициативе Субарендатора', 'Удерживается полностью (не возвращается)'),
        ('Расторжение за нарушения Субарендатора', 'Удерживается полностью'),
        ('Задолженность по платежам', 'Зачитывается в счёт долга; остаток должен быть восстановлен'),
    ],
    col_widths=[8, 8]
)

add_highlight(
    'Пеня за каждый день просрочки пополнения: 1% от суммы ежемесячной аренды.\nПри просрочке более 7 дней — Арендатор вправе расторгнуть договор.',
    title='Просрочка пополнения обеспечительного платежа',
    bg=RED_L, border_color=RED, icon='⚠️'
)

thin_line()

# ══════════════════════════════════════════════════════════════
#  SECTION 6: ОТВЕТСТВЕННОСТЬ
# ══════════════════════════════════════════════════════════════
add_section_title('РАЗДЕЛ 6', 'Ответственность сторон', '⚖️')

make_table(
    ['Нарушение', 'Ответственная сторона', 'Санкция'],
    [
        ('Просрочка арендной платы', 'Субарендатор', '1% в день от просроченной суммы'),
        ('Непередача помещения в срок', 'Арендатор', 'Возмещение убытков'),
        ('Непринятие помещения в срок', 'Субарендатор', 'Возмещение убытков'),
        ('Просрочка возврата помещения', 'Субарендатор', 'Аренда за всё время просрочки + пеня'),
        ('Повреждение имущества', 'Субарендатор', 'Полное возмещение + возможно расторжение'),
        ('Уклонение Арендатора от приёмки', 'Арендатор', '1% в день от суммы ежемесячной аренды'),
    ],
    col_widths=[6.5, 4, 5.5]
)

thin_line()

# ══════════════════════════════════════════════════════════════
#  SECTION 7: РАСТОРЖЕНИЕ
# ══════════════════════════════════════════════════════════════
add_section_title('РАЗДЕЛ 7', 'Расторжение договора', '🔔')

rt_tbl = doc.add_table(rows=1, cols=2)
rt_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

fill_ro(rt_tbl.cell(0,0), 'АРЕНДАТОР МОЖЕТ РАСТОРГНУТЬ, ЕСЛИ:', RED,
    ['Субарендатор использует помещение не по назначению',
     'Два раза подряд просрочена арендная плата',
     'Существенно ухудшено помещение',
     '2+ нарушений п.3.3 за 6 месяцев подряд',
     '',
     'Уведомление → расторжение через 15 дней'],
    RED_L, RED)

fill_ro(rt_tbl.cell(0,1), 'СУБАРЕНДАТОР МОЖЕТ РАСТОРГНУТЬ:', BLUE,
    ['В любое время с уведомлением за 2 месяца',
     'Письменное уведомление по адресу Арендатора',
     '',
     '⚠ При досрочном выходе: обеспечительный',
     '  платёж (378 000 ₽) НЕ ВОЗВРАЩАЕТСЯ'],
    BLUE_L, BLUE)

doc.add_paragraph().paragraph_format.space_after = Pt(4)
thin_line()

# ══════════════════════════════════════════════════════════════
#  SECTIONS 8–9: ФОРС-МАЖОР / ЗАКЛЮЧИТЕЛЬНЫЕ
# ══════════════════════════════════════════════════════════════
add_section_title('РАЗДЕЛЫ 8–9', 'Форс-мажор и заключительные положения', '🌪️')

fz_tbl = doc.add_table(rows=1, cols=2)
fz_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

fill_ro(fz_tbl.cell(0,0), 'ФОРС-МАЖОР', BLUE,
    ['Стороны освобождаются от ответственности при',
     'обстоятельствах, которые нельзя предвидеть.',
     'Уведомить другую сторону в течение 3 дней.',
     '',
     '⚠ COVID-19 НЕ признаётся форс-мажором',
     '  по данному договору.'],
    BLUE_L, BLUE)

fill_ro(fz_tbl.cell(0,1), 'ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ', GREEN,
    ['Претензионный порядок обязателен; срок ответа — 15 дней',
     'Споры — Арбитражный суд г. Москвы',
     'Уведомления: заказное письмо, email, под расписку',
     'Договор составлен в 2 экземплярах',
     'Все изменения — только доп. соглашением'],
    GRN_L, GREEN)

doc.add_paragraph().paragraph_format.space_after = Pt(4)
thin_line()

# ══════════════════════════════════════════════════════════════
#  SIGNATURES
# ══════════════════════════════════════════════════════════════
page_break()

add_para('АДРЕСА, РЕКВИЗИТЫ И ПОДПИСИ СТОРОН', bold=True, size=9, color=GRAY4, space_before=6, space_after=12)

sig_tbl = doc.add_table(rows=1, cols=2)
sig_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

def fill_sig(cell, role, name, fields):
    set_cell_bg(cell, GRAY1)
    tc6 = cell._tc
    for p_el in tc6.findall(qn('w:p')):
        tc6.remove(p_el)
    pr = cell.add_paragraph(style='Normal')
    pr.paragraph_format.space_before = Pt(10)
    pr.paragraph_format.space_after  = Pt(4)
    pr.paragraph_format.left_indent  = Cm(0.5)
    rr2 = pr.add_run(role)
    rr2.font.size = Pt(8)
    rr2.font.color.rgb = GRAY4
    rr2.bold = True
    pn2 = cell.add_paragraph(style='Normal')
    pn2.paragraph_format.space_after  = Pt(14)
    pn2.paragraph_format.left_indent  = Cm(0.5)
    rn3 = pn2.add_run(name)
    rn3.font.size = Pt(12)
    rn3.font.color.rgb = NAVY
    rn3.bold = True
    for label in fields:
        pl2 = cell.add_paragraph(style='Normal')
        pl2.paragraph_format.space_before = Pt(3)
        pl2.paragraph_format.space_after  = Pt(1)
        pl2.paragraph_format.left_indent  = Cm(0.5)
        rl3 = pl2.add_run(label + ':')
        rl3.font.size  = Pt(8)
        rl3.font.color.rgb = GRAY4
        pv2 = cell.add_paragraph(style='Normal')
        pv2.paragraph_format.space_before = Pt(1)
        pv2.paragraph_format.space_after  = Pt(8)
        pv2.paragraph_format.left_indent  = Cm(0.5)
        # underline placeholder
        pPr = pv2._p.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'),   'single')
        bottom.set(qn('w:sz'),    '4')
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), 'D1D5DB')
        pBdr.append(bottom)
        pPr.append(pBdr)
        rv3 = pv2.add_run(' ')
        rv3.font.size = Pt(12)
    # Signature line
    psig = cell.add_paragraph(style='Normal')
    psig.paragraph_format.space_before = Pt(20)
    psig.paragraph_format.space_after  = Pt(4)
    psig.paragraph_format.left_indent  = Cm(0.5)
    rsig = psig.add_run('Подпись: _________________________')
    rsig.font.size = Pt(10)
    rsig.font.color.rgb = GRAY6
    cell.add_paragraph(style='Normal').paragraph_format.space_after = Pt(10)

fill_sig(sig_tbl.cell(0,0), 'АРЕНДАТОР', 'ООО «Перспектива М»',
    ['Юридический адрес', 'ИНН / ОГРН', 'Расчётный счёт', 'Банк / БИК'])

fill_sig(sig_tbl.cell(0,1), 'СУБАРЕНДАТОР', 'ИП _______________',
    ['Адрес регистрации', 'ИНН / ОГРНИП', 'Расчётный счёт', 'Банк / БИК'])

# ── Save ────────────────────────────────────────────────────────
out = '/home/clawdbot/.openclaw/workspace/drafts/Договор_субаренды_LEGAL_DESIGN.docx'
doc.save(out)
print(f'Saved: {out}')
