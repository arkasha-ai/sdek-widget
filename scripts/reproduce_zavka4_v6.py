#!/usr/bin/env python3
"""
Заявка №4 v6 — КЛОНИРОВАНИЕ НА БАЗЕ ОРИГИНАЛА
Подход: открываем оригинал → очищаем body → заполняем заново.
Это сохраняет ВСЕ стили, тему, docDefaults, header/footer.
"""

import copy
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsdecls

ORIG_PATH = '/home/clawdbot/.openclaw/media/inbound/file_81---2141837f-9e85-45e3-9135-f0ffbf7ac458.docx'
PURPLE = '5F497A'
NBSP = '\xa0'

# ==============================================================
# Открываем оригинал и КЛОНИРУЕМ элементы
# Подход: deep copy каждого элемента body из оригинала
# ==============================================================

orig = Document(ORIG_PATH)

# Сохраняем порядок элементов оригинала
orig_body = orig.element.body
orig_elements = list(orig_body)

# Создаём новый документ НА БАЗЕ оригинала (сохраняя стили и тему)
# Простейший способ: скопировать оригинал и модифицировать
doc = Document(ORIG_PATH)

# Удаляем ВСЁ содержимое body (кроме sectPr)
body = doc.element.body
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
sectPr = body.find('.//w:sectPr', ns)

# Сохраняем sectPr
sectPr_copy = copy.deepcopy(sectPr) if sectPr is not None else None

# Удаляем все дочерние элементы
for child in list(body):
    body.remove(child)

# Возвращаем sectPr
if sectPr_copy is not None:
    body.append(sectPr_copy)

# Теперь вставляем элементы ПЕРЕД sectPr, копируя из оригинала
def insert_before_sectPr(element):
    """Вставляет элемент перед sectPr."""
    sectPr = body.find('.//w:sectPr', ns)
    if sectPr is not None:
        sectPr.addprevious(element)
    else:
        body.append(element)

# ==============================================================
# Клонируем ВСЕ элементы из оригинала (deep copy)
# ==============================================================
for elem in orig_elements:
    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    if tag != 'sectPr':
        cloned = copy.deepcopy(elem)
        insert_before_sectPr(cloned)

# === СОХРАНЕНИЕ ===
output = "/home/clawdbot/.openclaw/workspace/docs/zavka4_v6_CLONED.docx"
doc.save(output)

print(f"✅ v6 создан (клон оригинала): {output}")
print("\nПодход: deep copy всех элементов из оригинала")
print("Сохранены: стили, тема, docDefaults, header/footer, ВСЁ")
