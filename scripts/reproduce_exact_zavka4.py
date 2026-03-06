#!/usr/bin/env python3
"""
Точное воспроизведение Заявки №4 с ТЗ
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_table_borders_colored(table, color_hex='5F497A', inside_only=False):
    """Установка цветных границ таблицы"""
    tbl = table._element
    tblPr = tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)
    
    tblBorders = OxmlElement('w:tblBorders')
    
    if inside_only:
        borders_to_set = ['insideH', 'insideV']
    else:
        borders_to_set = ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']
    
    for border_name in borders_to_set:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), color_hex)
        tblBorders.append(border)
    
    old_borders = tblPr.find(qn('w:tblBorders'))
    if old_borders is not None:
        tblPr.remove(old_borders)
    
    tblPr.append(tblBorders)

def set_cell_shading(cell, color_hex):
    """Установка фонового цвета ячейки"""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color_hex)
    cell._element.get_or_add_tcPr().append(shading_elm)

# === СОЗДАНИЕ ДОКУМЕНТА ===
doc = Document()

# Margins
section = doc.sections[0]
section.top_margin = Cm(2.0)
section.bottom_margin = Cm(2.0)
section.left_margin = Cm(3.0)
section.right_margin = Cm(1.5)

# === ЗАГОЛОВОК ===
def add_para(text, bold=False, with_indent=False):
    """Добавить параграф с форматированием"""
    para = doc.add_paragraph()
    if with_indent:
        para.paragraph_format.left_indent = Pt(28.35)
        para.paragraph_format.first_line_indent = Pt(-28.35)
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(6)
    para.paragraph_format.line_spacing = 1.2
    para.style = 'Normal'
    run = para.add_run(text)
    run.font.name = 'Calibri'
    run.font.bold = bold
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0, 0, 0)
    return para

add_para("ЗАЯВКА №4 к Договору 14/25 от «16» мая 2025 г.", bold=True, with_indent=True)
add_para("Дата Заявки: «05» февраля 2026 г.", bold=True, with_indent=True)

# === ТАБЛИЦА 1: СТОРОНЫ ===
table1 = doc.add_table(rows=2, cols=2)
table1.style = 'Normal Table'
set_table_borders_colored(table1, inside_only=True)
table1.columns[0].width = Cm(4.25)
table1.columns[1].width = Cm(12.26)

# Заказчик
cell = table1.rows[0].cells[0]
para = cell.paragraphs[0]
para.paragraph_format.space_before = Pt(6)
para.paragraph_format.space_after = Pt(6)
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Заказчик")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0, 0, 0)

cell = table1.rows[0].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.space_before = Pt(6)
para.paragraph_format.space_after = Pt(6)
para.paragraph_format.line_spacing = 1.2
run = para.add_run("ИНН \nв лице директора Шевшелева Сергея Викторовича\nдействующего на основании Устава")
run.font.name = 'Calibri'
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0, 0, 0)

# Исполнитель
cell = table1.rows[1].cells[0]
para = cell.paragraphs[0]
para.paragraph_format.space_before = Pt(6)
para.paragraph_format.space_after = Pt(6)
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Исполнитель")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0, 0, 0)

cell = table1.rows[1].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.space_before = Pt(6)
para.paragraph_format.space_after = Pt(6)
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Общество с ограниченной ответственностью «Гравити Групп»\nИНН 5908999996\nв лице Директора Яборова Андрея Владимировича, действующего на основании Устава")
run.font.name = 'Calibri'
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0, 0, 0)

# === ОСНОВНОЙ ТЕКСТ ===
add_para("согласовали следующий условия выполнения работ по Заявке к Договору:")
add_para("Предварительная стоимость работ по Заявке составляет 166 057 (Сто шестьдесят шесть тысяч пятьдесят семь) рублей 50 копеек, в т.ч. НДС 5% - 7 907,95 рублей.", with_indent=True)
add_para("Сроки выполнения Заявки:", with_indent=True)
add_para("Дата начала выполнения работ: «5» февраля 2026 г.", with_indent=True)
add_para("Дата окончания выполнения работ: «27» февраля 2026 г.", with_indent=True)
add_para("Порядок оплаты работ по Заявке:", with_indent=True)
add_para("30% планируемой стоимости работ в размере 49 817 (Сорок девять тысяч восемьсот семнадцать) рублей 25 копеек оплачиваются в течение 2 (Двух) рабочих с момента подписания Заявки.", with_indent=True)
add_para("37% планируемой стоимости работ в размере 61 441 (Шестьдесят одна тысяча четыреста сорок один) рубль 28 копеек оплачиваются в течение 30 (Тридцати) рабочих с момента подписания Заявки, но не позже даты подписания Акта по Заявке.", with_indent=True)
add_para("Оплата оставшейся части общей стоимости работ, рассчитанной на основании фактических трудозатрат Исполнителя, и указанных в Акте по производится в течение 5 (Пяти) рабочих дней со дня подписания Акта по Заявке. По согласованию с Исполнителем оплата оставшейся части общей стоимости выполненных работ может быть отсрочена до 20 (Двадцати) рабочих дней после подписания Акта сдачи-приемки работ.", with_indent=True)
add_para("Срок гарантии на выполненные работы Исполнителем составляет 3 (Три) месяца.", with_indent=True)
add_para("Если для выполнения Заявки потребуются проработка предметной области, разработка 3D моделей, то для выполнения работ со стороны Исполнителя привлекается аналитик, разработчик, трудозатраты будут отражены в Акте по Заявке.", with_indent=True)
add_para("Положения Заявки имеют приоритет над условиями Договора. В остальном, что не предусмотрено Заявкой, Стороны руководствуются условиями Договора.", with_indent=True)

# === ТАБЛИЦА 2: РАБОТЫ ===
table2 = doc.add_table(rows=7, cols=3)
table2.style = 'Normal Table'
set_table_borders_colored(table2, inside_only=True)
table2.columns[0].width = Cm(1.25)
table2.columns[1].width = Cm(11.00)
table2.columns[2].width = Cm(3.86)

# Заголовок
headers = ['№', 'Наименование и описание работ', 'Оценка трудоёмкости в часах']
for i, header in enumerate(headers):
    cell = table2.rows[0].cells[i]
    para = cell.paragraphs[0]
    para.paragraph_format.left_indent = Pt(5.40)
    para.paragraph_format.first_line_indent = Pt(-5.40)
    para.paragraph_format.line_spacing = 1.2
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run(header)
    run.font.name = 'Calibri'
    run.font.bold = True
    run.font.size = Pt(12)

# Категория
cell = table2.rows[1].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Разработка мобильной версии приложения (Приложение №1 к Заявке)")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)

# Специалисты
specialists = [
    ("Дизайнер", "8,00"),
    ("Веб разработчик", "23,00"),
    ("Специалист по тестированию", "10,00"),
    ("Руководитель проекта", "7,00"),
    ("Аналитик", "1,00")
]

for idx, (name, hours) in enumerate(specialists, start=2):
    cell = table2.rows[idx].cells[1]
    para = cell.paragraphs[0]
    para.paragraph_format.line_spacing = 1.2
    run = para.add_run(name)
    run.font.name = 'Calibri'
    run.font.size = Pt(12)
    
    cell = table2.rows[idx].cells[2]
    para = cell.paragraphs[0]
    para.paragraph_format.line_spacing = 1.2
    run = para.add_run(hours)
    run.font.name = 'Calibri'
    run.font.size = Pt(12)

# === ТАБЛИЦА 3: ПОДПИСИ ===
table3 = doc.add_table(rows=4, cols=2)
table3.style = 'Normal Table'
set_table_borders_colored(table3, inside_only=True)
table3.columns[0].width = Cm(8.24)
table3.columns[1].width = Cm(8.24)

# Заголовки
cell = table3.rows[0].cells[0]
set_cell_shading(cell, '5F497A')
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
para.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = para.add_run("ЗАКАЗЧИК")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(255, 255, 255)

cell = table3.rows[0].cells[1]
set_cell_shading(cell, '5F497A')
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
para.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = para.add_run("ИСПОЛНИТЕЛЬ")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(255, 255, 255)

# Организации
cell = table3.rows[1].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Общество с ограниченной ответственностью «Гравити Групп»\n")
run.font.name = 'Calibri'
run.font.size = Pt(12)

# Должности
cell = table3.rows[2].cells[0]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Генеральный директор ООО «Инплайн»\nШевшелев Сергей Викторович\n\n(на основании Устава)")
run.font.name = 'Calibri'
run.font.size = Pt(12)

cell = table3.rows[2].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Директор ООО «ГРАВИТИ ГРУПП»\nЯборов Андрей Владимирович\n(на основании Устава)")
run.font.name = 'Calibri'
run.font.size = Pt(12)

# Подписи
cell = table3.rows[3].cells[0]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("\n_____________________ / С.В. Шевшелев")
run.font.name = 'Calibri'
run.font.size = Pt(12)

cell = table3.rows[3].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("\n_________________________ / А.В. Яборов")
run.font.name = 'Calibri'
run.font.size = Pt(12)

# === ТАБЛИЦА 4: ТЗ ===
table4 = doc.add_table(rows=4, cols=2)
table4.style = 'Normal Table'
set_table_borders_colored(table4, inside_only=True)

# Строка 1
cell = table4.rows[0].cells[0]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Добавление новых типов банок и моделей")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)

cell = table4.rows[0].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Требуется добавить 3 вида новых банок и конвертировать модели в поддерживаемый формат: \n1. Банки с горлом 38мм\n1.1 100 мл\n1.2 150 мл\n1.3 155 мл\n")
run.font.name = 'Calibri'
run.font.size = Pt(12)

# Строка 2
cell = table4.rows[1].cells[0]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Добавление предпросмотра капсул")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)

cell = table4.rows[1].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Требуется добавить предпросмотр капсул в этапе выбора МЖК/ТЖК/Таблеток\n1. Реализовать функционал создания изображения из модели капсулы\n2. Отобразить изображение для каждой капсулы")
run.font.name = 'Calibri'
run.font.size = Pt(12)

# Строка 3
cell = table4.rows[2].cells[0]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Обновление логики расчетов для физики банок")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)

cell = table4.rows[2].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Требуется добавить поддержку логики расчета для новых размеров банок\n1. Требуется подогнать физические ограничения и максимальный уровень насыпки под каждый размер новых моделей")
run.font.name = 'Calibri'
run.font.size = Pt(12)

# Строка 4
cell = table4.rows[3].cells[0]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Мобильная версия")
run.font.name = 'Calibri'
run.font.bold = True
run.font.size = Pt(12)

cell = table4.rows[3].cells[1]
para = cell.paragraphs[0]
para.paragraph_format.line_spacing = 1.2
run = para.add_run("Требуется разработать дизайн мобильной версии и интегрировать его в конфигуратор")
run.font.name = 'Calibri'
run.font.size = Pt(12)

# === СОХРАНЕНИЕ ===
output_path = "/home/clawdbot/.openclaw/workspace/docs/zavka4_reproduced_EXACT.docx"
doc.save(output_path)

print(f"✅ Документ создан: {output_path}")
print("\n📋 ВОСПРОИЗВЕДЕНО:")
print("  ✅ Заявка №4 к Договору 14/25")
print("  ✅ Margins: 3см слева, 1.5см справа")
print("  ✅ Висячие строки: 28.35pt / -28.35pt")
print("  ✅ Calibri 12pt + line_spacing 1.2")
print("  ✅ Цветные границы #5F497A")
print("  ✅ 4 таблицы:")
print("     1. Стороны (заказчик без названия компании)")
print("     2. Работы (5 специалистов)")
print("     3. Подписи (белый текст на фиолетовом)")
print("     4. Техническое задание (4 задачи)")
