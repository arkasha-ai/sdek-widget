#!/usr/bin/env python3
"""
Генератор Заявок v2 — шаблонная замена с точным позиционированием run'ов.
"""

from docx import Document
from lxml import etree
from docx.oxml.ns import qn

TEMPLATE_PATH = '/home/clawdbot/.openclaw/media/inbound/file_81---2141837f-9e85-45e3-9135-f0ffbf7ac458.docx'
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def replace_across_runs(paragraph, old_text, new_text):
    """Заменить текст, который может быть разбит на несколько run'ов."""
    # Собираем все (run, t_element) пары
    pieces = []
    for run_elem in paragraph.findall('.//w:r', ns):
        for t in run_elem.findall('.//w:t', ns):
            pieces.append(t)
    
    if not pieces:
        return False
    
    # Собираем полный текст
    full = ''.join(t.text or '' for t in pieces)
    if old_text not in full:
        return False
    
    # Заменяем
    new_full = full.replace(old_text, new_text, 1)
    
    # Записываем новый текст обратно: весь текст в первый t, остальные пустые
    if pieces:
        pieces[0].text = new_full
        pieces[0].set(qn('xml:space'), 'preserve')
        for t in pieces[1:]:
            t.text = ''
    
    return True


def replace_sdt_content(body, alias, new_text):
    """Заменить содержимое SDT по alias."""
    for sdt in body.findall('.//w:sdt', ns):
        sdtPr = sdt.find('.//w:sdtPr', ns)
        if sdtPr is not None:
            a = sdtPr.find('.//w:alias', ns)
            if a is not None and a.get(qn('w:val')) == alias:
                for t in sdt.findall('.//w:t', ns):
                    t.text = new_text
                    return True
    return False


def update_property(doc, prop_type, prop_name, new_value):
    """Обновить свойство документа (app/core)."""
    for rel in doc.part.package.rels.values():
        reltype = str(rel.reltype).lower()
        if prop_type == 'app' and ('extended' in reltype or 'app' in reltype):
            ns_uri = 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
        elif prop_type == 'core' and ('core-properties' in reltype or 'metadata/core' in reltype):
            ns_uri = 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
        else:
            continue
        
        try:
            root = etree.fromstring(rel.target_part.blob)
            elem = root.find(f'{{{ns_uri}}}{prop_name}')
            if elem is not None:
                elem.text = new_value
                rel.target_part._blob = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
                return True
        except:
            pass
    return False


def generate_zavka(data, output_path):
    doc = Document(TEMPLATE_PATH)
    body = doc.element.body
    
    # === 1. SDT замены ===
    replace_sdt_content(body, "Наименование Заказчика", data.get("customer_name", ""))
    replace_sdt_content(body, "ИНН Заказчика", data.get("customer_inn", ""))
    update_property(doc, 'app', 'Company', data.get("customer_name", ""))
    update_property(doc, 'core', 'contentStatus', data.get("customer_inn", ""))
    
    # === 2. Замены в параграфах ===
    all_paras = list(body.iter(qn('w:p')))
    
    replacements = [
        ("ЗАЯВКА №4", f"ЗАЯВКА №{data.get('number', '4')}"),
        ("14/25", data.get("contract_number", "14/25")),
        ("«16» мая 2025", data.get("contract_date", "«16» мая 2025")),
        ("«05» февраля 2026", data.get("date", "«05» февраля 2026")),
        ("«5» февраля 2026", data.get("start_date", "«5» февраля 2026")),
        ("«27» февраля 2026", data.get("end_date", "«27» февраля 2026")),
        ("Шевшелева Сергея Викторовича", data.get("customer_director", "Шевшелева Сергея Викторовича")),
        ("С.В. Шевшелев", data.get("customer_director_short", "С.В. Шевшелев")),
        ("Яборова Андрея Владимировича", data.get("contractor_director", "Яборова Андрея Владимировича")),
        ("А.В. Яборов", data.get("contractor_director_short", "А.В. Яборов")),
        ("166 057", data.get("total_amount", "166 057")),
        ("166\xa0057", data.get("total_amount", "166 057")),  # С неразрывным пробелом
        ("Сто шестьдесят шесть тысяч пятьдесят семь", data.get("total_words", "Сто шестьдесят шесть тысяч пятьдесят семь")),
        ("7\xa0907,50", data.get("vat_amount", "7\xa0907,50")),
        ("7 907,50", data.get("vat_amount", "7 907,50")),
        ("49 817", data.get("payment1_amount", "49 817")),
        ("49\xa0817", data.get("payment1_amount", "49 817")),
        ("Сорок девять тысяч восемьсот семнадцать", data.get("payment1_words", "Сорок девять тысяч восемьсот семнадцать")),
        ("61 441", data.get("payment2_amount", "61 441")),
        ("61\xa0441", data.get("payment2_amount", "61 441")),
        ("Шестьдесят одна тысяча четыреста сорок один", data.get("payment2_words", "Шестьдесят одна тысяча четыреста сорок один")),
        ("3 (Три)", data.get("warranty", "3 (Три)")),
    ]
    
    for old_text, new_text in replacements:
        found = False
        for para in all_paras:
            if replace_across_runs(para, old_text, new_text):
                found = True
        if not found and old_text != new_text:
            # Only warn if we actually need to replace
            pass  # Silent for template test
    
    doc.save(output_path)
    print(f"✅ Заявка №{data.get('number', '?')} → {output_path}")
    return doc


if __name__ == "__main__":
    # Тест: те же данные что в оригинале
    data = {
        "number": "4",
        "contract_number": "14/25",
        "contract_date": "«16» мая 2025",
        "date": "«05» февраля 2026",
        "customer_name": "Общество с ограниченной ответственностью «Инплайн»",
        "customer_inn": "5906142571",
        "customer_director": "Шевшелева Сергея Викторовича",
        "customer_director_short": "С.В. Шевшелев",
        "contractor_director": "Яборова Андрея Владимировича",
        "contractor_director_short": "А.В. Яборов",
        "total_amount": "166 057",
        "total_words": "Сто шестьдесят шесть тысяч пятьдесят семь",
        "vat_amount": "7\xa0907,50",
        "start_date": "«5» февраля 2026",
        "end_date": "«27» февраля 2026",
        "payment1_amount": "49 817",
        "payment1_words": "Сорок девять тысяч восемьсот семнадцать",
        "payment2_amount": "61 441",
        "payment2_words": "Шестьдесят одна тысяча четыреста сорок один",
        "warranty": "3 (Три)",
    }
    
    output = "/home/clawdbot/.openclaw/workspace/docs/zavka4_TEMPLATE_GEN.docx"
    doc = generate_zavka(data, output)
    
    # Верификация
    body = doc.element.body
    sdts = body.findall('.//w:sdt', ns)
    numPrs = body.findall('.//w:numPr', ns)
    print(f"📊 SDT: {len(sdts)} | numPr: {len(numPrs)}")
    
    # Тест 2: Заявка №5 с другими данными
    data5 = {
        "number": "5",
        "contract_number": "14/25",
        "contract_date": "«16» мая 2025",
        "date": "«10» марта 2026",
        "customer_name": "Общество с ограниченной ответственностью «ПЛАТФОРМА»",
        "customer_inn": "5902054490",
        "customer_director": "Иванова Ивана Ивановича",
        "customer_director_short": "И.И. Иванов",
        "contractor_director": "Яборова Андрея Владимировича",
        "contractor_director_short": "А.В. Яборов",
        "total_amount": "200 000",
        "total_words": "Двести тысяч",
        "vat_amount": "9\xa0523,81",
        "start_date": "«10» марта 2026",
        "end_date": "«10» апреля 2026",
        "payment1_amount": "60 000",
        "payment1_words": "Шестьдесят тысяч",
        "payment2_amount": "74 000",
        "payment2_words": "Семьдесят четыре тысячи",
        "warranty": "6 (Шесть)",
    }
    
    output5 = "/home/clawdbot/.openclaw/workspace/docs/zavka5_EXAMPLE.docx"
    doc5 = generate_zavka(data5, output5)
    
    # Удалить Приложение №1 (Техническое задание) из заявки
    # Стратегия: удалить 4ю таблицу (ТЗ) + все параграфы после 3й таблицы до конца документа
    
    # 1) Найти все таблицы
    all_tables = doc5.tables
    
    # 2) Удалить 4ю таблицу (индекс 3) если она есть
    if len(all_tables) >= 4:
        table_to_remove = all_tables[3]
        table_to_remove._element.getparent().remove(table_to_remove._element)
        print("✅ Удалена Таблица 4 (ТЗ)")
    
    # 3) Удалить параграфы после 3й таблицы (заголовки типа "Приложение №1")
    # Найдём позицию 3й таблицы в document body
    body = doc5.element.body
    table3_elem = all_tables[2]._element if len(all_tables) >= 3 else None
    
    if table3_elem is not None:
        # Найдём индекс 3й таблицы среди всех элементов body
        table3_idx = None
        for i, child in enumerate(body):
            if child == table3_elem:
                table3_idx = i
                break
        
        # Удалить все параграфы после этого индекса
        if table3_idx is not None:
            elements_to_remove = []
            for i in range(table3_idx + 1, len(body)):
                child = body[i]
                tag = child.tag.split('}')[-1]  # извлечь имя тега
                # Удаляем параграфы и таблицы после 3й таблицы
                if tag in ('p', 'tbl'):
                    elements_to_remove.append(child)
            
            for elem in elements_to_remove:
                body.remove(elem)
            
            print(f"✅ Удалено {len(elements_to_remove)} элементов после Таблицы 3")
    
    doc5.save(output5)
    print(f"✅ Заявка №5 без ТЗ → {output5}")
