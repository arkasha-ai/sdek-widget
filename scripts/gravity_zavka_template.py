#!/usr/bin/env python3
"""
Генератор ЗАЯВОК для Gravity Group по шаблону
Использование: python3 gravity_zavka_template.py
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime

def number_to_russian_words(num):
    """
    Конвертация числа в слова на русском языке
    Поддерживает числа от 0 до 999 999 999
    """
    if num == 0:
        return "ноль"
    
    ones = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
    teens = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", 
             "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
    tens = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", 
            "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
    hundreds = ["", "сто", "двести", "триста", "четыреста", "пятьсот", 
                "шестьсот", "семьсот", "восемьсот", "девятьсот"]
    
    thousands = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
    
    def convert_hundreds(n):
        """Конвертация чисел от 0 до 999"""
        if n == 0:
            return ""
        elif n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        else:
            h = hundreds[n // 100]
            remainder = n % 100
            if remainder == 0:
                return h
            elif remainder < 10:
                return h + " " + ones[remainder]
            elif remainder < 20:
                return h + " " + teens[remainder - 10]
            else:
                return h + " " + tens[remainder // 10] + (" " + ones[remainder % 10] if remainder % 10 != 0 else "")
    
    def get_thousand_form(n):
        """Правильная форма слова 'тысяча'"""
        if n % 10 == 1 and n % 100 != 11:
            return "тысяча"
        elif n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]:
            return "тысячи"
        else:
            return "тысяч"
    
    num = int(num)
    if num == 0:
        return "ноль"
    
    result = []
    
    # Миллионы
    millions = num // 1000000
    if millions > 0:
        result.append(convert_hundreds(millions))
        if millions % 10 == 1 and millions % 100 != 11:
            result.append("миллион")
        elif millions % 10 in [2, 3, 4] and millions % 100 not in [12, 13, 14]:
            result.append("миллиона")
        else:
            result.append("миллионов")
    
    # Тысячи
    thousands_num = (num % 1000000) // 1000
    if thousands_num > 0:
        # Для тысяч используем женский род (одна, две)
        if thousands_num < 10:
            result.append(thousands[thousands_num])
        elif thousands_num < 20:
            result.append(teens[thousands_num - 10])
        elif thousands_num < 100:
            t = tens[thousands_num // 10]
            o = thousands[thousands_num % 10] if thousands_num % 10 != 0 else ""
            result.append(t + (" " + o if o else ""))
        else:
            h = hundreds[thousands_num // 100]
            remainder = thousands_num % 100
            if remainder == 0:
                result.append(h)
            elif remainder < 10:
                result.append(h + " " + thousands[remainder])
            elif remainder < 20:
                result.append(h + " " + teens[remainder - 10])
            else:
                t = tens[remainder // 10]
                o = thousands[remainder % 10] if remainder % 10 != 0 else ""
                result.append(h + " " + t + (" " + o if o else ""))
        
        result.append(get_thousand_form(thousands_num))
    
    # Единицы
    ones_num = num % 1000
    if ones_num > 0:
        result.append(convert_hundreds(ones_num))
    
    return " ".join(result)

def set_cell_border(cell, **kwargs):
    """
    Установка границ ячейки таблицы
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()

    # Список сторон границ
    for edge in ('top', 'left', 'bottom', 'right'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            
            element = OxmlElement(tag)
            for key in ["sz", "val", "color", "space"]:
                if key in edge_data:
                    element.set(qn('w:{}'.format(key)), str(edge_data[key]))
            
            tcPr.append(element)

def money_to_words(amount):
    """
    Конвертация суммы в слова (русский язык)
    Пример: 147450 -> "Сто сорок семь тысяч четыреста пятьдесят"
    """
    rubles = int(amount)
    kopeks = int(round((amount - rubles) * 100))
    
    rubles_words = number_to_russian_words(rubles).capitalize()
    
    return f"{rubles_words} рублей, {kopeks:02d} копеек"

def create_zavka_document(data):
    """
    Создание документа ЗАЯВКИ
    
    data = {
        'zavka_number': '4',
        'contract_number': '14/25',
        'contract_date': '16.05.2025',
        'zavka_date': '05.02.2026',
        'cost_total': 166057.50,
        'cost_vat_percent': 5,  # Или None если без НДС
        'work_start': '05.02.2026',
        'work_end': '27.02.2026',
        'payment_30_percent': 49817.25,
        'payment_37_percent': 61441.28,
        'warranty_months': 3,
        'customer_name': 'ООО "Инплайн"',
        'customer_inn': '5902054490',
        'customer_director': 'Шевшелев Сергей Викторович',
        'customer_director_short': 'С.В. Шевшелев',
        'works': [
            {'category': 'Разработка мобильной версии приложения (Приложение №1 к Заявке)', 'items': [
                {'specialist': 'Дизайнер', 'hours': 8.0},
                {'specialist': 'Веб разработчик', 'hours': 23.0},
                {'specialist': 'Специалист по тестированию', 'hours': 10.0}
            ]}
        ],
        'appendix': 'Техническое задание'  # Или детали приложения
    }
    """
    
    doc = Document()
    
    # === ЗАГОЛОВОК ===
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(f"ЗАЯВКА №{data['zavka_number']} к Договору {data['contract_number']} от «{data['contract_date']}» г.")
    run.font.size = Pt(14)
    run.font.bold = True
    
    # Дата заявки
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = date_para.add_run(f"Дата Заявки: «{data['zavka_date']}» г.")
    run.font.size = Pt(12)
    
    doc.add_paragraph()  # Пустая строка
    
    # === ТАБЛИЦА СТОРОН ===
    table_parties = doc.add_table(rows=2, cols=2)
    table_parties.style = 'Table Grid'
    
    # Заголовки
    cell = table_parties.rows[0].cells[0]
    cell.text = "Заказчик"
    cell.paragraphs[0].runs[0].font.bold = True
    
    cell = table_parties.rows[0].cells[1]
    customer_text = (
        f"{data['customer_name']}\n"
        f"ИНН {data['customer_inn']}\n"
        f"в лице директора {data['customer_director']}\n"
        f"действующего на основании Устава"
    )
    cell.text = customer_text
    
    # Исполнитель
    cell = table_parties.rows[1].cells[0]
    cell.text = "Исполнитель"
    cell.paragraphs[0].runs[0].font.bold = True
    
    cell = table_parties.rows[1].cells[1]
    executor_text = (
        "Общество с ограниченной ответственностью «Гравити Групп»\n"
        "ИНН 5908999996\n"
        "в лице Директора Яборова Андрея Владимировича, действующего на основании Устава"
    )
    cell.text = executor_text
    
    doc.add_paragraph()
    
    # === ОСНОВНОЙ ТЕКСТ ===
    intro = doc.add_paragraph("согласовали следующий условия выполнения работ по Заявке к Договору:")
    
    doc.add_paragraph()
    
    # Стоимость
    cost_text = f"Предварительная стоимость работ по Заявке составляет {data['cost_total']:,.2f} ({money_to_words(data['cost_total'])})"
    if data.get('cost_vat_percent'):
        vat_amount = data['cost_total'] * data['cost_vat_percent'] / (100 + data['cost_vat_percent'])
        cost_text += f", в т.ч. НДС {data['cost_vat_percent']}% - {vat_amount:,.2f} рублей"
    cost_text += "."
    
    para = doc.add_paragraph(cost_text)
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    # Сроки
    para = doc.add_paragraph("Сроки выполнения Заявки:")
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    para = doc.add_paragraph(f"Дата начала выполнения работ: «{data['work_start']}» г.")
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    para = doc.add_paragraph(f"Дата окончания выполнения работ: «{data['work_end']}» г.")
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    # Порядок оплаты
    para = doc.add_paragraph("Порядок оплаты работ по Заявке:")
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    para = doc.add_paragraph(
        f"30% планируемой стоимости работ в размере {data['payment_30_percent']:,.2f} "
        f"({money_to_words(data['payment_30_percent'])}) оплачиваются в течение 2 (Двух) "
        f"рабочих с момента подписания Заявки."
    )
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    para = doc.add_paragraph(
        f"37% планируемой стоимости работ в размере {data['payment_37_percent']:,.2f} "
        f"({money_to_words(data['payment_37_percent'])}) оплачиваются в течение 30 (Тридцати) "
        f"рабочих с момента подписания Заявки, но не позже даты подписания Акта по Заявке."
    )
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    para = doc.add_paragraph(
        "Оплата оставшейся части общей стоимости работ, рассчитанной на основании фактических "
        "трудозатрат Исполнителя, и указанных в Акте по производится в течение 5 (Пяти) рабочих "
        "дней со дня подписания Акта по Заявке. По согласованию с Исполнителем оплата оставшейся "
        "части общей стоимости выполненных работ может быть отсрочена до 20 (Двадцати) рабочих "
        "дней после подписания Акта сдачи-приемки работ."
    )
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    # Гарантия
    warranty_word = number_to_russian_words(data['warranty_months']).capitalize()
    para = doc.add_paragraph(
        f"Срок гарантии на выполненные работы Исполнителем составляет {data['warranty_months']} "
        f"({warranty_word}) месяца."
    )
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    # Доп условие
    para = doc.add_paragraph(
        "Если для выполнения Заявки потребуются проработка предметной области, разработка 3D моделей, "
        "то для выполнения работ со стороны Исполнителя привлекается аналитик, разработчик, "
        "трудозатраты будут отражены в Акте по Заявке."
    )
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    # Приоритет
    para = doc.add_paragraph(
        "Положения Заявки имеют приоритет над условиями Договора. В остальном, что не предусмотрено "
        "Заявкой, Стороны руководствуются условиями Договора."
    )
    para.paragraph_format.first_line_indent = Cm(1.25)
    
    doc.add_paragraph()
    
    # === ТАБЛИЦА РАБОТ ===
    para = doc.add_paragraph("Приложение №1")
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.runs[0]
    run.font.bold = True
    
    para = doc.add_paragraph(f"к Заявке №{data['zavka_number']} от «{data['zavka_date']}» г.")
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    para = doc.add_paragraph(f"по Договору №{data['contract_number']} от «{data['contract_date']}» г.")
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph()
    
    # Подсчёт количества строк для таблицы работ
    total_rows = 1  # Заголовок
    for work_cat in data['works']:
        total_rows += 1  # Строка категории
        total_rows += len(work_cat['items'])  # Строки специалистов
    
    table_works = doc.add_table(rows=total_rows, cols=3)
    table_works.style = 'Table Grid'
    
    # Заголовок таблицы
    headers = ['№', 'Наименование и описание работ', 'Оценка трудоёмкости в часах']
    for i, header in enumerate(headers):
        cell = table_works.rows[0].cells[i]
        cell.text = header
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Заполнение работ
    row_idx = 1
    for work_cat in data['works']:
        # Категория работ
        cell = table_works.rows[row_idx].cells[1]
        cell.text = work_cat['category']
        cell.paragraphs[0].runs[0].font.bold = True
        row_idx += 1
        
        # Специалисты
        for item in work_cat['items']:
            table_works.rows[row_idx].cells[1].text = item['specialist']
            table_works.rows[row_idx].cells[2].text = f"{item['hours']:.2f}"
            row_idx += 1
    
    doc.add_paragraph()
    
    # === ТАБЛИЦА ПОДПИСЕЙ ===
    table_signs = doc.add_table(rows=4, cols=2)
    table_signs.style = 'Table Grid'
    
    # Заголовки
    cell = table_signs.rows[0].cells[0]
    cell.text = "ЗАКАЗЧИК"
    cell.paragraphs[0].runs[0].font.bold = True
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    cell = table_signs.rows[0].cells[1]
    cell.text = "ИСПОЛНИТЕЛЬ"
    cell.paragraphs[0].runs[0].font.bold = True
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Названия организаций
    table_signs.rows[1].cells[0].text = ""
    table_signs.rows[1].cells[1].text = "Общество с ограниченной ответственностью «Гравити Групп»"
    
    # Должности и ФИО
    cell = table_signs.rows[2].cells[0]
    cell.text = (
        f"Генеральный директор {data['customer_name']}\n"
        f"{data['customer_director']}\n\n"
        f"(на основании Устава)"
    )
    
    cell = table_signs.rows[2].cells[1]
    cell.text = (
        "Директор ООО «ГРАВИТИ ГРУПП»\n"
        "Яборов Андрей Владимирович\n"
        "(на основании Устава)"
    )
    
    # Строка подписей
    cell = table_signs.rows[3].cells[0]
    cell.text = f"_____________________ / {data['customer_director_short']}"
    
    cell = table_signs.rows[3].cells[1]
    cell.text = "_________________________ / А.В. Яборов"
    
    return doc

# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===
if __name__ == "__main__":
    # Пример данных для заявки
    example_data = {
        'zavka_number': '4',
        'contract_number': '14/25',
        'contract_date': '16 мая 2025',
        'zavka_date': '05 февраля 2026',
        'cost_total': 166057.50,
        'cost_vat_percent': 5,
        'work_start': '5 февраля 2026',
        'work_end': '27 февраля 2026',
        'payment_30_percent': 49817.25,
        'payment_37_percent': 61441.28,
        'warranty_months': 3,
        'customer_name': 'ООО "Инплайн"',
        'customer_inn': '5902054490',
        'customer_director': 'Шевшелев Сергей Викторович',
        'customer_director_short': 'С.В. Шевшелев',
        'works': [
            {'category': 'Разработка мобильной версии приложения (Приложение №1 к Заявке)', 'items': [
                {'specialist': 'Дизайнер', 'hours': 8.0},
                {'specialist': 'Веб разработчик', 'hours': 23.0},
                {'specialist': 'Специалист по тестированию', 'hours': 10.0}
            ]}
        ],
        'appendix': 'Техническое задание'
    }
    
    # Генерация документа
    doc = create_zavka_document(example_data)
    
    # Сохранение
    output_path = "/home/clawdbot/.openclaw/workspace/docs/gravity_zavka_template_example.docx"
    doc.save(output_path)
    
    print(f"✅ Шаблон заявки создан: {output_path}")
    print("\n📋 Пример использования:")
    print("```python")
    print("from gravity_zavka_template import create_zavka_document")
    print("")
    print("data = {")
    print("    'zavka_number': '5',")
    print("    'contract_number': '14/25',")
    print("    # ... остальные поля")
    print("}")
    print("")
    print("doc = create_zavka_document(data)")
    print("doc.save('zavka_5.docx')")
    print("```")
