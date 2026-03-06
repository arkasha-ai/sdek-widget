#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Договор купли-продажи материальных и нематериальных активов — полная версия"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT

doc = Document()

# ─── Поля страницы ────────────────────────────────────────────────────────────
section = doc.sections[0]
section.left_margin   = Cm(3)
section.right_margin  = Cm(1.5)
section.top_margin    = Cm(2)
section.bottom_margin = Cm(2)

# ─── Колонтитул с номером страницы ───────────────────────────────────────────
def add_page_number_footer(section):
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.clear()
    run = fp.add_run('Договор купли-продажи активов № 02/26  |  стр. ')
    run.font.name = 'Times New Roman'
    run.font.size = Pt(10)
    # Поле PAGE
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = ' PAGE '
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    r = OxmlElement('w:r')
    rpr = OxmlElement('w:rPr')
    fn = OxmlElement('w:rFonts')
    fn.set(qn('w:ascii'), 'Times New Roman')
    fn.set(qn('w:hAnsi'), 'Times New Roman')
    rpr.append(fn)
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '20'); rpr.append(sz)
    r.append(rpr); r.append(fldChar1); r.append(instrText); r.append(fldChar2)
    fp._p.append(r)

add_page_number_footer(section)

# ─── Хелперы ──────────────────────────────────────────────────────────────────
TNR = 'Times New Roman'

def set_font(run, bold=False, italic=False, size=14, color=None, underline=False):
    run.font.name = TNR
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.underline = underline
    if color:
        run.font.color.rgb = color

def para(text='', align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, italic=False,
         size=14, sb=0, sa=6, color=None, line_spacing=1.5, underline=False,
         first_indent=None):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(sb)
    pf.space_after  = Pt(sa)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line_spacing
    if first_indent is not None:
        pf.first_line_indent = Cm(first_indent)
    if text:
        run = p.add_run(text)
        set_font(run, bold=bold, italic=italic, size=size, color=color, underline=underline)
    return p

def heading(text, level=1, numbered=''):
    sizes = {1: 14, 2: 14, 3: 14}
    p = para(f'{numbered}{text}' if numbered else text,
             align=WD_ALIGN_PARAGRAPH.LEFT,
             bold=True, size=sizes.get(level, 14), sb=10, sa=4)
    return p

def bullet(text, bold_prefix='', rest='', indent=1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after  = Pt(3)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.5
    pf.left_indent  = Cm(indent)
    pf.first_line_indent = Cm(-0.5)
    r0 = p.add_run('• ')
    set_font(r0, size=14)
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        set_font(rb, bold=True, size=14)
    if rest:
        rr = p.add_run(rest)
        set_font(rr, size=14)
    elif text:
        rr = p.add_run(text)
        set_font(rr, size=14)
    return p

def numbered_item(num, text, bold_prefix='', rest=''):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(2)
    pf.space_after  = Pt(2)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.5
    pf.first_line_indent = Cm(1.25)
    r0 = p.add_run(f'{num}  ')
    set_font(r0, bold=True, size=14)
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        set_font(rb, bold=True, size=14)
    if rest:
        rr = p.add_run(rest)
        set_font(rr, size=14)
    elif text:
        rr = p.add_run(text)
        set_font(rr, size=14)
    return p

def hr():
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(4)
    pf.space_after  = Pt(4)
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '4472C4')
    pBdr.append(bottom)
    p._p.get_or_add_pPr().append(pBdr)
    return p

def set_table_border(table, color='000000', sz='6'):
    tbl = table._tbl
    tblPr = tbl.find(qn('w:tblPr'))
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement('w:tblBorders')
    for side in ('top','left','bottom','right','insideH','insideV'):
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), sz)
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), color)
        tblBorders.append(el)
    tblPr.append(tblBorders)

def set_cell_bg(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def set_row_h(row, h_cm):
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    trHeight = OxmlElement('w:trHeight')
    trHeight.set(qn('w:val'), str(int(Cm(h_cm).pt * 20)))
    trHeight.set(qn('w:hRule'), 'exact')
    trPr.append(trHeight)

def cell_p(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT,
           size=12, color=None, sb=1, sa=1):
    for p in cell.paragraphs:
        p._element.getparent().remove(p._element)
    p = cell.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(sb)
    pf.space_after  = Pt(sa)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.2
    if text:
        r = p.add_run(text)
        set_font(r, bold=bold, size=size, color=color)
    return p

def page_break():
    p = doc.add_paragraph()
    r = p.add_run()
    r.add_break(docx_break_type())

def docx_break_type():
    from docx.oxml.ns import nsmap
    from docx.enum.text import WD_BREAK
    return WD_BREAK.PAGE

def add_page_break():
    p = doc.add_paragraph()
    run = p.add_run()
    run.add_break(WD_BREAK.PAGE)

from docx.enum.text import WD_BREAK

# ══════════════════════════════════════════════════════════════════════════════
#  ТИТУЛЬНЫЙ БЛОК
# ══════════════════════════════════════════════════════════════════════════════

para('ДОГОВОР КУПЛИ-ПРОДАЖИ', align=WD_ALIGN_PARAGRAPH.CENTER,
     bold=True, size=16, sb=0, sa=2)
para('материальных и нематериальных активов № 02/26',
     align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14, sb=0, sa=10)

# Город / дата
city_table = doc.add_table(rows=1, cols=2)
city_table.alignment = WD_TABLE_ALIGNMENT.LEFT
city_table.style = 'Table Grid'
set_table_border(city_table, color='FFFFFF', sz='0')
cell_p(city_table.rows[0].cells[0], 'г. Москва', bold=False, size=14,
       align=WD_ALIGN_PARAGRAPH.LEFT)
cell_p(city_table.rows[0].cells[1], '«__» февраля 2026 г.',
       align=WD_ALIGN_PARAGRAPH.RIGHT, size=14)
city_table.rows[0].cells[0].width = Cm(9)
city_table.rows[0].cells[1].width = Cm(9)

para('', sb=0, sa=6)

# Стороны
p_parties = doc.add_paragraph()
p_parties.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p_parties.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
p_parties.paragraph_format.line_spacing = 1.5
p_parties.paragraph_format.space_after = Pt(6)
r1 = p_parties.add_run('Камызин Александр Николаевич')
set_font(r1, bold=True, size=14)
r2 = p_parties.add_run(', именуемый в дальнейшем ')
set_font(r2, size=14)
r3 = p_parties.add_run('«Продавец»')
set_font(r3, bold=True, size=14)
r4 = p_parties.add_run(', с одной стороны, и ', )
set_font(r4, size=14)
r5 = p_parties.add_run('___________________________________________________')
set_font(r5, size=14)
r6 = p_parties.add_run(', именуемый в дальнейшем ')
set_font(r6, size=14)
r7 = p_parties.add_run('«Покупатель»')
set_font(r7, bold=True, size=14)
r8 = p_parties.add_run(', с другой стороны, совместно именуемые ')
set_font(r8, size=14)
r9 = p_parties.add_run('«Стороны»')
set_font(r9, bold=True, size=14)
r10 = p_parties.add_run(', заключили настоящий Договор о нижеследующем:')
set_font(r10, size=14)

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  СОДЕРЖАНИЕ
# ══════════════════════════════════════════════════════════════════════════════

para('СОДЕРЖАНИЕ', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14, sb=8, sa=4)

toc_items = [
    ('1.', 'Определения и термины'),
    ('2.', 'Предмет договора'),
    ('3.', 'Описание активов'),
    ('4.', 'Заверения об обстоятельствах'),
    ('5.', 'Цена договора и порядок расчётов'),
    ('6.', 'Обязательства Сторон'),
    ('7.', 'Переход права собственности. Порядок приёмки-передачи'),
    ('8.', 'Ответственность Сторон. Неустойка'),
    ('9.', 'Форс-мажорные обстоятельства'),
    ('10.', 'Конфиденциальность'),
    ('11.', 'Порядок расторжения договора'),
    ('12.', 'Применимое законодательство. Разрешение споров'),
    ('13.', 'Сохранение силы договора'),
    ('14.', 'Таблица ключевых дат и сроков'),
    ('15.', 'Заключительные положения'),
    ('Приложение № 1', 'Акт приёма-передачи активов'),
    ('Приложение № 2', 'Акт инвентаризации активов'),
    ('Приложение № 3', 'Расписка о получении денежных средств'),
    ('Реквизиты', 'Реквизиты и подписи Сторон'),
]

toc_table = doc.add_table(rows=len(toc_items), cols=2)
toc_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(toc_table, color='D9D9D9', sz='4')
for i, (num, title) in enumerate(toc_items):
    cell_p(toc_table.rows[i].cells[0], num, bold=True, size=13, align=WD_ALIGN_PARAGRAPH.LEFT)
    cell_p(toc_table.rows[i].cells[1], title, size=13, align=WD_ALIGN_PARAGRAPH.LEFT)
    if i % 2 == 0:
        set_cell_bg(toc_table.rows[i].cells[0], 'EBF3FB')
        set_cell_bg(toc_table.rows[i].cells[1], 'EBF3FB')
    set_row_h(toc_table.rows[i], 0.72)
    toc_table.rows[i].cells[0].width = Cm(3.5)
    toc_table.rows[i].cells[1].width = Cm(14.0)

hr()
add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 1. ОПРЕДЕЛЕНИЯ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 1. ОПРЕДЕЛЕНИЯ И ТЕРМИНЫ', 1)
para('В настоящем Договоре используются следующие понятия:', size=14, first_indent=1.25)

defs = [
    ('Активы', '— совокупность материальных и нематериальных объектов, передаваемых Покупателю по настоящему Договору, включая оборудование, технику, мебель, интерьер и аккаунты социальных сетей.'),
    ('Акт приёмки-передачи', '— документ, подтверждающий фактическую передачу Активов от Продавца Покупателю (Приложение № 1).'),
    ('Акт инвентаризации', '— перечень передаваемых Активов с указанием количества, состояния и стоимости (Приложение № 2).'),
    ('Цена договора', '— общая сумма вознаграждения Продавца за передачу Активов, указанная в разделе 5 настоящего Договора.'),
    ('Интеллектуальная собственность', '— исключительные права на результаты интеллектуальной деятельности и средства индивидуализации, передаваемые в составе Активов.'),
    ('Форс-мажор', '— обстоятельства непреодолимой силы, предусмотренные разделом 9 настоящего Договора.'),
]

def_table = doc.add_table(rows=len(defs), cols=2)
def_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(def_table, color='4472C4', sz='4')
for i, (term, definition) in enumerate(defs):
    cell_p(def_table.rows[i].cells[0], term, bold=True, size=13, align=WD_ALIGN_PARAGRAPH.LEFT)
    cell_p(def_table.rows[i].cells[1], definition, size=13, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    set_cell_bg(def_table.rows[i].cells[0], 'D6E4F0')
    set_row_h(def_table.rows[i], 0.9)
    def_table.rows[i].cells[0].width = Cm(5.5)
    def_table.rows[i].cells[1].width = Cm(12.0)

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 2. ПРЕДМЕТ ДОГОВОРА
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 2. ПРЕДМЕТ ДОГОВОРА', 1)

numbered_item('2.1.', '',
    bold_prefix='Продавец обязуется передать ',
    rest='в собственность Покупателя комплекс материальных и нематериальных Активов, а Покупатель обязуется принять и оплатить их в порядке и сроки, установленные настоящим Договором.')

numbered_item('2.2.', '',
    bold_prefix='Состав Активов: ',
    rest='Активы представляют собой совокупность оборудования, техники, мебели и интерьера, а также аккаунтов социальных сетей, принадлежащих Продавцу на праве собственности.')

numbered_item('2.3.', '',
    rest='Продажа материальных активов (оборудования), в том числе используемых по фактическому местонахождению, осуществляется одновременно с передачей исключительных прав на результаты интеллектуальной деятельности и средства индивидуализации (интеллектуальную собственность). Передача регулируется гл. 30 ГК РФ (купля-продажа) и гл. 69–72 ГК РФ (интеллектуальные права).')

numbered_item('2.4.', '',
    rest='Продавец не несёт ответственности за скрытые недостатки, выявленные после подписания Акта приёмки-передачи, если они не были сообщены Продавцом умышленно.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 3. ОПИСАНИЕ АКТИВОВ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 3. ОПИСАНИЕ АКТИВОВ', 1)

numbered_item('3.1.', '',
    bold_prefix='Адрес местонахождения Активов: ',
    rest='__________________________________________________________')

numbered_item('3.2.', '',
    rest='Полный перечень имущества, имущественных прав, результатов интеллектуальной деятельности и средств индивидуализации содержится в ')
p32 = doc.paragraphs[-1]
rb = p32.add_run('Акте инвентаризации (Приложение № 2)')
set_font(rb, bold=True, size=14)
rc = p32.add_run(', являющемся неотъемлемой частью настоящего Договора.')
set_font(rc, size=14)

numbered_item('3.3.', '',
    rest='Покупатель обязуется принять и оплатить Активы в порядке и сроки, установленные настоящим Договором.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 4. ЗАВЕРЕНИЯ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 4. ЗАВЕРЕНИЯ ОБ ОБСТОЯТЕЛЬСТВАХ', 1)
para('Продавец заверяет Покупателя в следующем:', size=14, first_indent=1.25)

bullet('всё имущество и имущественные права, перечисленные в Акте инвентаризации, принадлежат Продавцу на законных основаниях; он имеет все необходимые права для распоряжения ими;')
bullet('ничего из перечисленного в Акте инвентаризации не находится в залоге у третьих лиц и не является предметом сделок с третьими лицами;')
bullet('с момента подписания настоящего Договора Продавец прекращает любые переговоры о продаже Активов третьим лицам;')
bullet('логины и пароли от аккаунтов социальных сетей, указанные в Акте инвентаризации, достоверны и не будут изменены Продавцом после заключения Договора;')
bullet('Активы не обременены правами третьих лиц, не находятся под арестом или иным ограничением.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 5. ЦЕНА И РАСЧЁТЫ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 5. ЦЕНА ДОГОВОРА И ПОРЯДОК РАСЧЁТОВ', 1)

numbered_item('5.1.', '',
    bold_prefix='Цена договора: ',
    rest='Общая стоимость Активов составляет __________________ (_____________________) рублей 00 копеек.')

numbered_item('5.2.', '',
    bold_prefix='Валюта расчётов: ',
    rest='Расчёты осуществляются в рублях Российской Федерации (RUB).')

numbered_item('5.3.', '',
    bold_prefix='Порядок оплаты: ',
    rest='Покупатель производит оплату Продавцу в течение ')
p53 = doc.paragraphs[-1]
rb = p53.add_run('3 (трёх) календарных дней')
set_font(rb, bold=True, size=14)
rc = p53.add_run(' с момента подписания настоящего Договора.')
set_font(rc, size=14)

numbered_item('5.4.', '',
    bold_prefix='Форма оплаты: ',
    rest='наличными денежными средствами, если иное не согласовано Сторонами в письменной форме.')

numbered_item('5.5.', '',
    rest='В день получения денежных средств Продавец передаёт Покупателю расписку о получении оплаты по форме Приложения № 3.')

numbered_item('5.6.', '',
    rest='Обязательство Покупателя по оплате считается исполненным с момента передачи денежных средств Продавцу и получения расписки.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 6. ОБЯЗАТЕЛЬСТВА СТОРОН
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 6. ОБЯЗАТЕЛЬСТВА СТОРОН', 1)

heading('6.1. Продавец обязуется:', 2)
bullet('Обеспечить фактическую передачу Покупателю всех Активов, перечисленных в Акте инвентаризации, в срок, установленный п. 7.2 настоящего Договора.')
bullet('Не изменять логины и пароли от аккаунтов социальных сетей с момента подписания Договора до момента передачи Активов.')
bullet('В день расчётов передать Покупателю оригинал расписки о получении денежных средств.')
bullet('Уведомить Покупателя об известных ему недостатках Активов до подписания Акта приёмки-передачи.')
bullet('Оказывать содействие Покупателю в согласовании даты и времени встречи для проверки Активов.')

heading('6.2. Покупатель обязуется:', 2)
bullet('Произвести оплату в размере и сроки, установленные разделом 5 настоящего Договора.')
bullet('Согласовать с Продавцом дату и время встречи по адресу, указанному в п. 3.1, для совместной проверки наличия, качества и комплектности Активов.')
bullet('Принять Активы по Акту приёмки-передачи в согласованные сроки.')
bullet('Не предъявлять претензий по недостаткам, которые могли быть обнаружены при надлежащей проверке в момент приёмки.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 7. ПЕРЕХОД ПРАВА СОБСТВЕННОСТИ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 7. ПЕРЕХОД ПРАВА СОБСТВЕННОСТИ. ПОРЯДОК ПРИЁМКИ-ПЕРЕДАЧИ', 1)

numbered_item('7.1.', '',
    rest='Активы считаются переданными Покупателю в момент подписания обеими Сторонами Акта приёмки-передачи (Приложение № 1).')

numbered_item('7.2.', '',
    bold_prefix='Сроки передачи: ',
    rest='Акт приёмки-передачи подписывается не позднее ')
p72 = doc.paragraphs[-1]
rb = p72.add_run('3 (трёх) календарных дней')
set_font(rb, bold=True, size=14)
rc = p72.add_run(' с даты подписания настоящего Договора.')
set_font(rc, size=14)

numbered_item('7.3.', '',
    rest='До подписания Акта приёмки-передачи Стороны проводят совместную проверку наличия, качества и комплектности Активов по адресу, указанному в п. 3.1.')

numbered_item('7.4.', '',
    rest='С момента подписания Акта приёмки-передачи на Покупателя переходит риск случайной гибели или повреждения Активов (ст. 459 ГК РФ).')

numbered_item('7.5.', '',
    rest='Все расходы, связанные с передачей и транспортировкой Активов, несёт _________________________ (по договорённости Сторон).')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 8. ОТВЕТСТВЕННОСТЬ. НЕУСТОЙКА
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 8. ОТВЕТСТВЕННОСТЬ СТОРОН. НЕУСТОЙКА', 1)

numbered_item('8.1.', '',
    rest='Стороны несут ответственность за неисполнение или ненадлежащее исполнение своих обязательств в соответствии с действующим законодательством РФ и настоящим Договором.')

numbered_item('8.2.', '',
    bold_prefix='Ответственность Продавца: ',
    rest='В случае нарушения Продавцом сроков передачи Активов (п. 7.2) Продавец уплачивает Покупателю неустойку в размере ')
p82 = doc.paragraphs[-1]
rb = p82.add_run('0,1% от цены Договора за каждый день просрочки')
set_font(rb, bold=True, size=14)
rc = p82.add_run(', но не более 10% от цены Договора.')
set_font(rc, size=14)

numbered_item('8.3.', '',
    bold_prefix='Ответственность Покупателя: ',
    rest='В случае нарушения Покупателем сроков оплаты (п. 5.3) Покупатель уплачивает Продавцу неустойку в размере ')
p83 = doc.paragraphs[-1]
rb = p83.add_run('0,1% от суммы задолженности за каждый день просрочки')
set_font(rb, bold=True, size=14)
rc = p83.add_run(', но не более 10% от цены Договора.')
set_font(rc, size=14)

numbered_item('8.4.', '',
    bold_prefix='Порядок расчёта неустойки: ',
    rest='Неустойка рассчитывается со дня, следующего за последним днём срока исполнения обязательства, по день фактического исполнения включительно. Уплата неустойки не освобождает Сторону от исполнения обязательства.')

numbered_item('8.5.', '',
    rest='Сторона вправе требовать возмещения убытков в части, не покрытой неустойкой (ст. 394 ГК РФ).')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 9. ФОРС-МАЖОР
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 9. ФОРС-МАЖОРНЫЕ ОБСТОЯТЕЛЬСТВА', 1)

numbered_item('9.1.', '',
    rest='Стороны освобождаются от ответственности за частичное или полное неисполнение обязательств, если такое неисполнение стало следствием обстоятельств непреодолимой силы (форс-мажора): стихийных бедствий, военных действий, решений государственных органов, делающих исполнение Договора невозможным.')

numbered_item('9.2.', '',
    rest='Сторона, для которой наступили форс-мажорные обстоятельства, обязана уведомить другую Сторону в письменной форме не позднее ')
p92 = doc.paragraphs[-1]
rb = p92.add_run('5 (пяти) рабочих дней')
set_font(rb, bold=True, size=14)
rc = p92.add_run(' с момента их наступления.')
set_font(rc, size=14)

numbered_item('9.3.', '',
    rest='Если форс-мажорные обстоятельства продолжаются более 30 (тридцати) календарных дней, каждая из Сторон вправе расторгнуть Договор в одностороннем порядке без уплаты штрафных санкций.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 10. КОНФИДЕНЦИАЛЬНОСТЬ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 10. КОНФИДЕНЦИАЛЬНОСТЬ', 1)

numbered_item('10.1.', '',
    rest='Стороны обязуются сохранять конфиденциальность условий настоящего Договора, а также любой информации, полученной в ходе его исполнения, и не раскрывать её третьим лицам без письменного согласия другой Стороны.')

numbered_item('10.2.', '',
    rest='Обязательство о конфиденциальности действует в течение ')
p102 = doc.paragraphs[-1]
rb = p102.add_run('3 (трёх) лет')
set_font(rb, bold=True, size=14)
rc = p102.add_run(' после исполнения Договора.')
set_font(rc, size=14)

numbered_item('10.3.', '',
    rest='Обязательство о конфиденциальности не распространяется на сведения, ставшие общедоступными не по вине Сторон, а также на случаи раскрытия информации по требованию уполномоченных государственных органов.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 11. РАСТОРЖЕНИЕ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 11. ПОРЯДОК РАСТОРЖЕНИЯ ДОГОВОРА', 1)

numbered_item('11.1.', '',
    rest='Договор может быть расторгнут по соглашению Сторон в любое время до момента полного исполнения обязательств.')

numbered_item('11.2.', '',
    rest='Продавец вправе расторгнуть Договор в одностороннем порядке при просрочке оплаты Покупателем более 5 (пяти) рабочих дней, уведомив об этом Покупателя за 3 (три) рабочих дня.')

numbered_item('11.3.', '',
    rest='Покупатель вправе расторгнуть Договор в одностороннем порядке при существенном нарушении Продавцом условий о составе или состоянии Активов, уведомив об этом Продавца за 3 (три) рабочих дня.')

numbered_item('11.4.', '',
    rest='При расторжении Договора по вине одной из Сторон виновная Сторона возмещает другой стороне документально подтверждённые убытки.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 12. ЗАКОНОДАТЕЛЬСТВО. СПОРЫ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 12. ПРИМЕНИМОЕ ЗАКОНОДАТЕЛЬСТВО. РАЗРЕШЕНИЕ СПОРОВ', 1)

numbered_item('12.1.', '',
    rest='Настоящий Договор регулируется и толкуется в соответствии с законодательством Российской Федерации, в том числе: ГК РФ (гл. 30 — купля-продажа, гл. 69–72 — интеллектуальная собственность).')

numbered_item('12.2.', '',
    rest='Все споры Стороны урегулируют путём переговоров. Срок рассмотрения претензии — 10 (десять) рабочих дней с даты её получения.')

numbered_item('12.3.', '',
    rest='При невозможности урегулирования спора путём переговоров он передаётся в суд общей юрисдикции по месту нахождения ответчика в порядке, предусмотренном действующим процессуальным законодательством РФ.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 13. СОХРАНЕНИЕ СИЛЫ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 13. СОХРАНЕНИЕ СИЛЫ ДОГОВОРА', 1)

numbered_item('13.1.', '',
    rest='Если какое-либо положение настоящего Договора будет признано недействительным, это не влечёт недействительности Договора в целом. Стороны обязуются заменить недействительное положение допустимым, максимально соответствующим первоначальному намерению Сторон.')

numbered_item('13.2.', '',
    rest='Все изменения и дополнения к настоящему Договору действительны только при условии их оформления в письменной форме и подписания уполномоченными представителями обеих Сторон.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 14. ТАБЛИЦА КЛЮЧЕВЫХ ДАТ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 14. ТАБЛИЦА КЛЮЧЕВЫХ ДАТ И СРОКОВ', 1)

dates_rows = [
    ('Событие / Действие', 'Ответственная сторона', 'Срок', 'Дата (факт)'),
    ('Подписание Договора', 'Обе Стороны', 'День подписания', ''),
    ('Оплата по Договору (п. 5.3)', 'Покупатель', 'В течение 3 кал. дней', ''),
    ('Совместная проверка Активов (п. 7.3)', 'Обе Стороны', 'До подписания Акта', ''),
    ('Подписание Акта приёмки-передачи (п. 7.2)', 'Обе Стороны', 'Не позднее 3 кал. дней', ''),
    ('Передача расписки (п. 5.5)', 'Продавец', 'В день оплаты', ''),
    ('Уведомление о форс-мажоре (п. 9.2)', 'Пострадавшая Сторона', 'В течение 5 раб. дней', ''),
    ('Рассмотрение претензии (п. 12.2)', 'Получатель претензии', 'В течение 10 раб. дней', ''),
]

dt_table = doc.add_table(rows=len(dates_rows), cols=4)
dt_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(dt_table, color='4472C4', sz='6')
dt_widths = [Cm(6.5), Cm(4.0), Cm(3.5), Cm(3.5)]

for i, row_data in enumerate(dates_rows):
    for j, val in enumerate(row_data):
        a = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else WD_ALIGN_PARAGRAPH.LEFT
        b = (i == 0)
        c = RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else None
        cell_p(dt_table.rows[i].cells[j], val, bold=b, align=a, size=12, color=c)
        if i == 0:
            set_cell_bg(dt_table.rows[i].cells[j], '2F5496')
        elif i % 2 == 0:
            set_cell_bg(dt_table.rows[i].cells[j], 'EBF3FB')
    set_row_h(dt_table.rows[i], 0.8)
    for j, cell in enumerate(dt_table.rows[i].cells):
        cell.width = dt_widths[j]

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ 15. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ
# ══════════════════════════════════════════════════════════════════════════════

heading('Раздел 15. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ', 1)

numbered_item('15.1.', '',
    rest='Настоящий Договор составлен в 2 (двух) экземплярах, имеющих одинаковую юридическую силу, — по одному для каждой из Сторон.')

numbered_item('15.2.', '',
    rest='Договор вступает в силу с момента его подписания уполномоченными представителями обеих Сторон.')

numbered_item('15.3.', '',
    rest='Все уведомления и претензии по Договору направляются в письменной форме по контактным данным Сторон, указанным в разделе «Реквизиты и подписи».')

p_annex = doc.add_paragraph()
p_annex.paragraph_format.space_before = Pt(8)
p_annex.paragraph_format.space_after  = Pt(4)
p_annex.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
p_annex.paragraph_format.line_spacing = 1.5
r_b = p_annex.add_run('Неотъемлемые приложения к настоящему Договору:')
set_font(r_b, bold=True, size=14)

bullet('Приложение № 1 — Акт приёмки-передачи материальных и нематериальных активов.')
bullet('Приложение № 2 — Акт инвентаризации активов.')
bullet('Приложение № 3 — Расписка о получении денежных средств.')

hr()

# ══════════════════════════════════════════════════════════════════════════════
#  РЕКВИЗИТЫ
# ══════════════════════════════════════════════════════════════════════════════

add_page_break()
para('РЕКВИЗИТЫ И ПОДПИСИ СТОРОН', align=WD_ALIGN_PARAGRAPH.CENTER,
     bold=True, size=14, sb=0, sa=8)

req_table = doc.add_table(rows=7, cols=2)
req_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(req_table, color='4472C4', sz='6')

# Заголовок
cell_p(req_table.rows[0].cells[0], 'ПРОДАВЕЦ', bold=True, size=13,
       align=WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0xFF, 0xFF, 0xFF))
cell_p(req_table.rows[0].cells[1], 'ПОКУПАТЕЛЬ', bold=True, size=13,
       align=WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0xFF, 0xFF, 0xFF))
set_cell_bg(req_table.rows[0].cells[0], '2F5496')
set_cell_bg(req_table.rows[0].cells[1], '2F5496')
set_row_h(req_table.rows[0], 0.9)

# Данные
rows_data = [
    ('ФИО:', 'Камызин Александр Николаевич', 'ФИО: ____________________________'),
    ('Паспорт:', 'Серия 4521 № 722029\nВыдан ГУ МВД России по г. Москве 11.03.2022 г.\nКод подразделения: 770-068', 'Серия _____ № ________\nВыдан ______________________________\n_______________________________'),
    ('Адрес регистрации:', 'Самарская обл., р-н Волжский,\nпгт Петра Дубрава, ул. 60 лет Октября, д. 10, кв. 19', '____________________________________\n____________________________________'),
    ('Телефон:', '____________________________', '____________________________'),
    ('Email:', '____________________________', '____________________________'),
    ('Подпись:', '_______________  /  Камызин А.Н.', '_______________  /  ________________'),
]

for i, (label, val_s, val_b) in enumerate(rows_data, start=1):
    cell_p(req_table.rows[i].cells[0],
           f'{label}\n{val_s}', size=12, align=WD_ALIGN_PARAGRAPH.LEFT)
    cell_p(req_table.rows[i].cells[1],
           f'{label}\n{val_b}', size=12, align=WD_ALIGN_PARAGRAPH.LEFT)
    if i == len(rows_data):
        set_cell_bg(req_table.rows[i].cells[0], 'EBF3FB')
        set_cell_bg(req_table.rows[i].cells[1], 'EBF3FB')
    set_row_h(req_table.rows[i], 1.3)

for row in req_table.rows:
    row.cells[0].width = Cm(8.75)
    row.cells[1].width = Cm(8.75)

para('', sb=4, sa=4)
para('Дата подписания: «____» _____________ 2026 г.', size=14, align=WD_ALIGN_PARAGRAPH.LEFT)
para('М.П.  (место для печати — при наличии)', size=12, align=WD_ALIGN_PARAGRAPH.LEFT)

# ══════════════════════════════════════════════════════════════════════════════
#  ПРИЛОЖЕНИЕ № 1 — АКТ ПРИЁМКИ-ПЕРЕДАЧИ
# ══════════════════════════════════════════════════════════════════════════════

add_page_break()

para('Приложение № 1', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('к Договору купли-продажи', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('материальных и нематериальных активов № 02/26', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('от «__» февраля 2026 г.', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=10)

para('АКТ ПРИЁМКИ-ПЕРЕДАЧИ', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=16, sa=2)
para('материальных и нематериальных активов', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14, sa=8)

act_city = doc.add_table(rows=1, cols=2)
act_city.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(act_city, color='FFFFFF', sz='0')
cell_p(act_city.rows[0].cells[0], 'г. Москва', size=14)
cell_p(act_city.rows[0].cells[1], '«__» ________________ 2026 г.', size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
act_city.rows[0].cells[0].width = Cm(9)
act_city.rows[0].cells[1].width = Cm(9)

para('', sa=6)

p_a1 = doc.add_paragraph()
p_a1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p_a1.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
p_a1.paragraph_format.line_spacing = 1.5
p_a1.paragraph_format.space_after = Pt(6)
for t, b in [('Камызин Александр Николаевич', True), (', именуемый в дальнейшем ', False),
             ('«Продавец»', True), (', с одной стороны, и ', False),
             ('__________________________________________', False),
             (', именуемый в дальнейшем ', False), ('«Покупатель»', True),
             (', с другой стороны, совместно именуемые ', False), ('«Стороны»', True),
             (', составили настоящий Акт о нижеследующем:', False)]:
    r = p_a1.add_run(t); set_font(r, bold=b, size=14)

numbered_item('1.', '',
    rest='Стороны проверили наличие, качество и комплектность имущества, имущественных прав и иных объектов, перечисленных в Акте инвентаризации. Замечаний не выявлено, Покупатель претензий не имеет.')

numbered_item('2.', '',
    rest='Продавец передал, а Покупатель принял Активы по Договору в полном объёме.')

numbered_item('3.', '',
    rest='С момента подписания настоящего Акта на Покупателя переходит риск случайной гибели или случайного повреждения имущества, переданного в составе Активов (ст. 459 ГК РФ).')

numbered_item('4.', '',
    rest='Настоящий Акт составлен в 2 (двух) экземплярах, имеющих равную юридическую силу, по одному для каждой из Сторон.')

para('', sa=6)

# Подписи к Акту
act_sign = doc.add_table(rows=4, cols=2)
act_sign.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(act_sign, color='4472C4', sz='6')
cell_p(act_sign.rows[0].cells[0], 'ПРОДАВЕЦ', bold=True, size=13,
       align=WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0xFF, 0xFF, 0xFF))
cell_p(act_sign.rows[0].cells[1], 'ПОКУПАТЕЛЬ', bold=True, size=13,
       align=WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0xFF, 0xFF, 0xFF))
set_cell_bg(act_sign.rows[0].cells[0], '2F5496')
set_cell_bg(act_sign.rows[0].cells[1], '2F5496')

act_sign_rows = [
    ('Камызин Александр Николаевич', '____________________________________'),
    ('_______________  /  Камызин А.Н.', '_______________  /  ________________'),
    ('Дата: «__» _____________ 2026 г.', 'Дата: «__» _____________ 2026 г.'),
]
for i, (ls, rs) in enumerate(act_sign_rows, start=1):
    cell_p(act_sign.rows[i].cells[0], ls, size=12)
    cell_p(act_sign.rows[i].cells[1], rs, size=12)
    set_row_h(act_sign.rows[i], 0.9)
for row in act_sign.rows:
    row.cells[0].width = Cm(8.75)
    row.cells[1].width = Cm(8.75)

# ══════════════════════════════════════════════════════════════════════════════
#  ПРИЛОЖЕНИЕ № 2 — АКТ ИНВЕНТАРИЗАЦИИ
# ══════════════════════════════════════════════════════════════════════════════

add_page_break()

para('Приложение № 2', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('к Договору купли-продажи', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('материальных и нематериальных активов № 02/26', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('от «__» февраля 2026 г.', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=10)

para('АКТ ИНВЕНТАРИЗАЦИИ', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=16, sa=2)
para('материальных и нематериальных активов', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14, sa=8)

# Таблица инвентаризации
inv_headers = ['№\nп/п', 'Наименование актива', 'Категория', 'Кол-во\n(шт.)', 'Состояние', 'Стоимость\n(руб.)', 'Примечание']
inv_widths  = [Cm(1.0), Cm(5.0), Cm(2.8), Cm(1.5), Cm(2.2), Cm(2.5), Cm(2.5)]
EMPTY = 10

inv_table = doc.add_table(rows=2 + EMPTY + 1, cols=len(inv_headers))
inv_table.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(inv_table, color='4472C4', sz='6')

for j, h in enumerate(inv_headers):
    cell_p(inv_table.rows[0].cells[j], h, bold=True,
           align=WD_ALIGN_PARAGRAPH.CENTER,
           color=RGBColor(0xFF, 0xFF, 0xFF), size=12)
    set_cell_bg(inv_table.rows[0].cells[j], '2F5496')
set_row_h(inv_table.rows[0], 1.0)

for j in range(len(inv_headers)):
    cell_p(inv_table.rows[1].cells[j], str(j + 1),
           align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
    set_cell_bg(inv_table.rows[1].cells[j], 'D6E4F0')
set_row_h(inv_table.rows[1], 0.55)

for i in range(EMPTY):
    row = inv_table.rows[2 + i]
    cell_p(row.cells[0], str(i + 1), align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
    for j in range(1, len(inv_headers)):
        cell_p(row.cells[j], '', size=12)
    set_row_h(row, 0.75)
    if i % 2 == 1:
        for cell in row.cells:
            set_cell_bg(cell, 'F2F7FB')

# Итого
total_row_inv = inv_table.rows[2 + EMPTY]
cell_p(total_row_inv.cells[0], 'Итого', bold=True,
       align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
for j in range(1, len(inv_headers) - 2):
    cell_p(total_row_inv.cells[j], '', size=12)
cell_p(total_row_inv.cells[5], '0,00', bold=True,
       align=WD_ALIGN_PARAGRAPH.RIGHT, size=12)
cell_p(total_row_inv.cells[6], '', size=12)
for cell in total_row_inv.cells:
    set_cell_bg(cell, 'FFE699')
set_row_h(total_row_inv, 0.8)

for row in inv_table.rows:
    for j, cell in enumerate(row.cells):
        cell.width = inv_widths[j]

para('', sa=8)

# Подписи к Приложению 2
inv_sign = doc.add_table(rows=3, cols=2)
inv_sign.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(inv_sign, color='4472C4', sz='6')
cell_p(inv_sign.rows[0].cells[0], 'Продавец', bold=True, size=13,
       align=WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0xFF, 0xFF, 0xFF))
cell_p(inv_sign.rows[0].cells[1], 'Покупатель', bold=True, size=13,
       align=WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0xFF, 0xFF, 0xFF))
set_cell_bg(inv_sign.rows[0].cells[0], '2F5496')
set_cell_bg(inv_sign.rows[0].cells[1], '2F5496')
for i, (ls, rs) in enumerate([
    ('_______________  /  Камызин А.Н.', '_______________  /  ________________'),
    ('Дата: «__» _____________ 2026 г.', 'Дата: «__» _____________ 2026 г.'),
], start=1):
    cell_p(inv_sign.rows[i].cells[0], ls, size=12)
    cell_p(inv_sign.rows[i].cells[1], rs, size=12)
    set_row_h(inv_sign.rows[i], 0.9)
for row in inv_sign.rows:
    row.cells[0].width = Cm(8.75)
    row.cells[1].width = Cm(8.75)

# ══════════════════════════════════════════════════════════════════════════════
#  ПРИЛОЖЕНИЕ № 3 — РАСПИСКА
# ══════════════════════════════════════════════════════════════════════════════

add_page_break()

para('Приложение № 3', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('к Договору купли-продажи', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('материальных и нематериальных активов № 02/26', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=2)
para('от «__» февраля 2026 г.', align=WD_ALIGN_PARAGRAPH.RIGHT, size=12, sa=10)

para('РАСПИСКА', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=16, sa=2)
para('о получении денежных средств', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14, sa=10)

rcpt_city = doc.add_table(rows=1, cols=2)
rcpt_city.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(rcpt_city, color='FFFFFF', sz='0')
cell_p(rcpt_city.rows[0].cells[0], 'г. Москва', size=14)
cell_p(rcpt_city.rows[0].cells[1], '«__» ________________ 2026 г.', size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
rcpt_city.rows[0].cells[0].width = Cm(9)
rcpt_city.rows[0].cells[1].width = Cm(9)

para('', sa=6)

rcpt_box = doc.add_table(rows=1, cols=1)
rcpt_box.alignment = WD_TABLE_ALIGNMENT.LEFT
set_table_border(rcpt_box, color='4472C4', sz='6')
set_cell_bg(rcpt_box.rows[0].cells[0], 'EBF3FB')

rcpt_text = (
    'Я, Камызин Александр Николаевич, паспорт серия 4521 № 722029, '
    'выдан ГУ МВД России по г. Москве 11.03.2022 г., получил от '
    '__________________________________________'
    ' денежные средства в размере '
    '________________ (____________________________) рублей '
    'в качестве полной оплаты по Договору купли-продажи материальных и нематериальных активов № 02/26 '
    'от «__» февраля 2026 г.\n\n'
    'Претензий по оплате не имею. Обязательства Покупателя по оплате считаю исполненными в полном объёме.'
)
cell_p(rcpt_box.rows[0].cells[0], rcpt_text, size=14, align=WD_ALIGN_PARAGRAPH.JUSTIFY, sb=6, sa=6)
rcpt_box.rows[0].cells[0].width = Cm(17.5)

para('', sa=10)

para('Подпись Продавца: _______________  /  Камызин А.Н.', size=14)
para('Дата: «__» _____________ 2026 г.', size=14)
para('', sa=4)
para('Свидетель (при наличии): _______________  /  _________________________', size=14)
para('ФИО: ________________________________  Телефон: _____________________', size=14)

# ─── СОХРАНЕНИЕ ───────────────────────────────────────────────────────────────
import docx as _d
out = '/home/clawdbot/.openclaw/workspace/drafts/ДКП_активы_оформленный.docx'
doc.save(out)
print(f'OK: {out}')
