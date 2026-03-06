#!/usr/bin/env python3
"""
Генератор Заявок на базе шаблона file_81.
Подход: открываем оригинал → заменяем данные → сохраняем.
Все SDT, numPr, стили, тема — сохраняются автоматически.
"""

import copy
import sys
import json
from docx import Document
from lxml import etree
from docx.oxml.ns import qn

TEMPLATE_PATH = '/home/clawdbot/.openclaw/media/inbound/file_81---2141837f-9e85-45e3-9135-f0ffbf7ac458.docx'

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def replace_sdt_text(doc_element, alias, new_text):
    """Заменить текст в SDT (Structured Document Tag) по alias."""
    for sdt in doc_element.findall('.//w:sdt', ns):
        sdtPr = sdt.find('.//w:sdtPr', ns)
        if sdtPr is not None:
            a = sdtPr.find('.//w:alias', ns)
            if a is not None and a.get(qn('w:val')) == alias:
                sdtContent = sdt.find('.//w:sdtContent', ns)
                if sdtContent is not None:
                    for run in sdtContent.findall('.//w:r', ns):
                        for t in run.findall('.//w:t', ns):
                            t.text = new_text
                            return True
    return False


def replace_run_text(para_element, old_text, new_text):
    """Заменить текст в run'ах параграфа."""
    full_text = ''.join(t.text or '' for t in para_element.findall('.//w:t', ns))
    if old_text in full_text:
        # Simple case: text in a single run
        for t in para_element.findall('.//w:t', ns):
            if t.text and old_text in t.text:
                t.text = t.text.replace(old_text, new_text)
                return True
    return False


def replace_in_body(body, old_text, new_text):
    """Заменить текст по всему body — работает через split runs."""
    count = 0
    # First try simple single-run replacement
    for t in body.findall('.//w:t', ns):
        if t.text and old_text in t.text:
            t.text = t.text.replace(old_text, new_text)
            count += 1
    if count > 0:
        return count
    
    # Cross-run replacement: find paragraphs containing the text
    for para in body.iter(qn('w:p')):
        runs = para.findall('.//w:r', ns)
        if not runs:
            continue
        
        # Build full text with run mapping
        full = ''
        run_map = []  # [(run_idx, char_idx_in_run)]
        for ri, run in enumerate(runs):
            for t in run.findall('.//w:t', ns):
                if t.text:
                    for ci, ch in enumerate(t.text):
                        run_map.append((ri, t, ci))
                        full += ch
        
        idx = full.find(old_text)
        if idx == -1:
            continue
        
        # Found! Now replace across runs
        end_idx = idx + len(old_text)
        
        # Collect affected runs
        affected_runs = set()
        for i in range(idx, end_idx):
            affected_runs.add(run_map[i][0])
        
        # Put new_text in the first affected run's text element, clear the rest
        first_done = False
        for i in range(idx, end_idx):
            ri, t_elem, ci = run_map[i]
            if not first_done:
                # Replace in first position
                t_elem.text = t_elem.text[:ci] + new_text + t_elem.text[ci + 1:]
                first_done = True
                first_ri = ri
                first_t = t_elem
                first_ci = ci
            else:
                # Remove character (set to empty if last char)
                if t_elem.text:
                    t_elem.text = t_elem.text[:ci] + t_elem.text[ci + 1:]
        
        count += 1
    
    return count


def replace_app_property(doc, prop_name, new_value):
    """Заменить свойство в app.xml (Company и т.д.)."""
    for rel in doc.part.package.rels.values():
        if 'extended' in str(rel.reltype).lower() or 'app' in str(rel.reltype).lower():
            try:
                blob = rel.target_part.blob
                root = etree.fromstring(blob)
                ep_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
                elem = root.find(f'{{{ep_ns}}}{prop_name}')
                if elem is not None:
                    elem.text = new_value
                    rel.target_part._blob = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
                    return True
            except Exception as e:
                print(f"Warning: Could not update app property {prop_name}: {e}")
    return False


def replace_core_property(doc, prop_name, new_value):
    """Заменить core property (contentStatus = ИНН Заказчика через data binding)."""
    for rel in doc.part.package.rels.values():
        if 'core-properties' in str(rel.reltype).lower() or 'metadata/core' in str(rel.reltype).lower():
            try:
                blob = rel.target_part.blob
                root = etree.fromstring(blob)
                # contentStatus is in cp namespace
                cp_ns = 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
                elem = root.find(f'{{{cp_ns}}}{prop_name}')
                if elem is not None:
                    elem.text = new_value
                    rel.target_part._blob = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
                    return True
            except Exception as e:
                print(f"Warning: Could not update core property {prop_name}: {e}")
    return False


def generate_zavka(data, output_path):
    """
    Генерирует Заявку на базе шаблона.
    
    data = {
        "number": "4",                    # Номер заявки
        "contract_number": "14/25",       # Номер договора
        "contract_date": "«16» мая 2025", # Дата договора
        "date": "«05» февраля 2026",      # Дата заявки
        
        "customer_name": "Общество с ограниченной ответственностью «Инплайн»",
        "customer_inn": "5906142571",
        "customer_director": "Шевшелева Сергея Викторовича",
        "customer_director_short": "С.В. Шевшелев",
        "customer_position": "Генеральный директор",
        "customer_org_short": "ООО «Инплайн»",
        
        "contractor_name": "Общество с ограниченной ответственностью «Гравити Групп»",
        "contractor_inn": "5908999996",
        "contractor_director": "Яборова Андрея Владимировича",
        "contractor_director_short": "А.В. Яборов",
        "contractor_position": "Директор",
        "contractor_org_short": "ООО «ГРАВИТИ ГРУПП»",
        
        "total_amount": "166 057",
        "total_words": "Сто шестьдесят шесть тысяч пятьдесят семь",
        "total_kopecks": "50",
        "vat_percent": "5",
        "vat_amount": "7 907,50",
        
        "start_date": "«5» февраля 2026",
        "end_date": "«27» февраля 2026",
        "warranty_months": "3 (Три)",
        
        "payments": [
            {"percent": "30", "amount": "49 817", "words": "Сорок девять тысяч восемьсот семнадцать", "kopecks": "25", "days": "2 (Двух)", "condition": "с момента подписания Заявки"},
            {"percent": "37", "amount": "61 441", "words": "Шестьдесят одна тысяча четыреста сорок один", "kopecks": "28", "days": "30 (Тридцати)", "condition": "с момента подписания Заявки, но не позже даты подписания Акта по Заявке"},
        ],
        
        "works": [
            {"name": "Разработка мобильной версии приложения (Приложение №1 к Заявке)", "is_category": True},
            {"name": "Дизайнер", "hours": "8,00"},
            {"name": "Веб разработчик", "hours": "23,00"},
            {"name": "Специалист по тестированию", "hours": "10,00"},
            {"name": "Руководитель проекта", "hours": "7,00"},
            {"name": "Аналитик", "hours": "1,00"},
        ],
    }
    """
    
    doc = Document(TEMPLATE_PATH)
    body = doc.element.body
    
    # 1. SDT замены (привязаны к свойствам документа)
    # Название заказчика → Company property
    replace_sdt_text(body, "Наименование Заказчика", data["customer_name"])
    replace_app_property(doc, "Company", data["customer_name"])
    
    # ИНН заказчика → contentStatus core property
    replace_sdt_text(body, "ИНН Заказчика", data["customer_inn"])
    replace_core_property(doc, "contentStatus", data["customer_inn"])
    
    # 2. Текстовые замены в body
    replacements = {
        "ЗАЯВКА №4": f"ЗАЯВКА №{data['number']}",
        "14/25": data["contract_number"],
        "«16» мая 2025": data["contract_date"],
        "«05» февраля 2026": data["date"],
        "Шевшелева Сергея Викторовича": data["customer_director"],
        "С.В. Шевшелев": data["customer_director_short"],
        "Яборова Андрея Владимировича": data["contractor_director"],
        "А.В. Яборов": data["contractor_director_short"],
        "166 057": data["total_amount"],
        "Сто шестьдесят шесть тысяч пятьдесят семь": data["total_words"],
        "«5» февраля 2026": data["start_date"],
        "«27» февраля 2026": data["end_date"],
    }
    
    for old, new in replacements.items():
        count = replace_in_body(body, old, new)
        if count == 0:
            print(f"⚠️  Не найдено: '{old}'")
    
    # 3. Сохранение
    doc.save(output_path)
    print(f"✅ Заявка №{data['number']} сохранена: {output_path}")


# === ТЕСТ: Генерируем ту же Заявку №4 ===
if __name__ == "__main__":
    test_data = {
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
        
        "total_amount": "166\xa0057",
        "total_words": "Сто шестьдесят шесть тысяч пятьдесят семь",
        
        "start_date": "«5» февраля 2026",
        "end_date": "«27» февраля 2026",
    }
    
    output = "/home/clawdbot/.openclaw/workspace/docs/zavka4_GENERATED.docx"
    generate_zavka(test_data, output)
    
    # Верификация
    doc = Document(output)
    body = doc.element.body
    sdts = body.findall('.//w:sdt', ns)
    print(f"\n📊 Верификация: {len(sdts)} SDT")
    
    for sdt in sdts:
        sdtPr = sdt.find('.//w:sdtPr', ns)
        alias = ""
        if sdtPr is not None:
            a = sdtPr.find('.//w:alias', ns)
            if a is not None:
                alias = a.get(qn('w:val'), '')
        sdtContent = sdt.find('.//w:sdtContent', ns)
        text = ''.join(sdtContent.itertext()).strip()[:50] if sdtContent is not None else ""
        print(f"  SDT '{alias}': '{text}'")
    
    # Check numbering preserved
    numPr_count = len(body.findall('.//w:numPr', ns))
    print(f"  numPr elements: {numPr_count}")
