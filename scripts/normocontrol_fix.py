#!/usr/bin/env python3
"""
Нормоконтроль: 31911111.62.01.11.000.005.П2.2
Пояснительная записка к техническому проекту — ЭОС, Этап 2
Исправления в режиме рецензирования (tracked changes).
"""
import copy
import shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC  = Path("/home/clawdbot/.openclaw/media/inbound/Тестовое_задание_для_кандидата_2023---6e285ce6-d842-449b-bb12-f6367feaddad.docx")
DEST = Path("/home/clawdbot/.openclaw/workspace/drafts/31911111.62.01.11.000.005.П2.2_норм.docx")
DEST.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(SRC, DEST)

AUTHOR = "Нормоконтроль"
DATE   = "2026-03-20T11:00:00Z"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

_cid = [1]
def cid():
    v = _cid[0]; _cid[0] += 1; return str(v)


# ── XML helpers ──────────────────────────────────────────────────────────────

def _del_elem(rpr, text: str):
    d = OxmlElement("w:del")
    d.set(qn("w:id"), cid()); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
    r = OxmlElement("w:r")
    if rpr is not None: r.append(copy.deepcopy(rpr))
    dt = OxmlElement("w:delText"); dt.set(XML_SPACE, "preserve"); dt.text = text
    r.append(dt); d.append(r)
    return d

def _ins_elem(rpr, text: str):
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), cid()); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = OxmlElement("w:r")
    if rpr is not None: r.append(copy.deepcopy(rpr))
    t = OxmlElement("w:t"); t.set(XML_SPACE, "preserve"); t.text = text
    r.append(t); ins.append(r)
    return ins

def _plain_run(rpr, text: str):
    r = OxmlElement("w:r")
    if rpr is not None: r.append(copy.deepcopy(rpr))
    t = OxmlElement("w:t"); t.set(XML_SPACE, "preserve"); t.text = text
    r.append(t)
    return r


def track_replace(para, old: str, new: str) -> bool:
    """Replace `old` → `new` inside paragraph with tracked change markup."""
    p = para._p
    # collect all direct w:r elements (not inside existing w:ins/w:del)
    runs = [r for r in p if r.tag == qn("w:r")]
    for r in runs:
        t_el = r.find(qn("w:t"))
        if t_el is None or not t_el.text:
            continue
        orig = t_el.text
        if old not in orig:
            continue
        idx    = orig.index(old)
        before = orig[:idx]
        after  = orig[idx + len(old):]
        rpr    = r.find(qn("w:rPr"))

        # shrink original run to 'before'
        t_el.text = before
        if before:
            t_el.set(XML_SPACE, "preserve")

        anchor = r
        d = _del_elem(rpr, old);  anchor.addnext(d);   anchor = d
        ins = _ins_elem(rpr, new); anchor.addnext(ins); anchor = ins
        if after:
            ar = _plain_run(rpr, after); anchor.addnext(ar)

        return True
    return False


def track_style_change(para, new_style_val: str):
    """
    Change paragraph style and record old style in w:pPrChange.
    `new_style_val` is the w:styleId value (e.g. 'Normal', '-', '-1').
    """
    p = para._p
    pPr = p.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p.insert(0, pPr)

    # remember old style
    old_pStyle = pPr.find(qn("w:pStyle"))
    old_val = old_pStyle.get(qn("w:val")) if old_pStyle is not None else "Normal"

    # set new style
    if old_pStyle is None:
        old_pStyle = OxmlElement("w:pStyle")
        pPr.insert(0, old_pStyle)
    old_pStyle.set(qn("w:val"), new_style_val)

    # build pPrChange
    pPrChange = pPr.find(qn("w:pPrChange"))
    if pPrChange is None:
        pPrChange = OxmlElement("w:pPrChange")
        pPrChange.set(qn("w:id"), cid())
        pPrChange.set(qn("w:author"), AUTHOR)
        pPrChange.set(qn("w:date"), DATE)
        inner = OxmlElement("w:pPr")
        inner_style = OxmlElement("w:pStyle")
        inner_style.set(qn("w:val"), old_val)
        inner.append(inner_style)
        pPrChange.append(inner)
        pPr.append(pPrChange)


def track_append_text(para, text: str):
    """Insert text at the end of paragraph as w:ins."""
    p = para._p
    # try to grab rPr from last run
    runs = [r for r in p if r.tag == qn("w:r")]
    rpr  = runs[-1].find(qn("w:rPr")) if runs else None
    ins  = _ins_elem(rpr, text)
    p.append(ins)


def track_cell_replace(cell, old: str, new: str) -> bool:
    """Replace text inside a table cell (iterates cell paragraphs)."""
    for para in cell.paragraphs:
        if track_replace(para, old, new):
            return True
    return False


def add_comment_run(para, comment_text: str):
    """
    Append a visually distinct annotation run in [[ ]] brackets as w:ins,
    styled with red highlight — a lightweight substitute for a full review comment.
    """
    p = para._p
    # Build the comment as an inserted run with rPr highlight=red
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), cid()); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    hl  = OxmlElement("w:highlight"); hl.set(qn("w:val"), "yellow")
    rpr.append(hl); r.append(rpr)
    t = OxmlElement("w:t"); t.set(XML_SPACE, "preserve")
    t.text = f" [[ЗАМЕЧАНИЕ: {comment_text}]]"
    r.append(t); ins.append(r)
    p.append(ins)


# ═══════════════════════════════════════════════════════════════════════════
doc = Document(str(DEST))
paras = doc.paragraphs
# ═══════════════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────────
# 1. АННОТАЦИЯ: стиль заголовка Normal → Заголовки частей документа
# ──────────────────────────────────────────────────────────────────
ann_heading = paras[2]
if ann_heading.text.strip() == "Аннотация":
    track_style_change(ann_heading, "- ")   # styleId 'Заголовки частей документа' varies; apply style name via python-docx
    ann_heading.style = doc.styles["Заголовки частей документа"]

# Текст аннотации: character-style 'Текст документа Знак' → para-style 'Гост-абзац'
for idx in (3, 4):
    p = paras[idx]
    if p.style.name == "Текст документа Знак":
        track_style_change(p, "- ")
        p.style = doc.styles["Гост-абзац"]

# ──────────────────────────────────────────────────────────────────
# 2. ЛИСТА УТВЕРЖДЕНИЯ (Table 1 — второй лист, верхний колонтитул)
# ──────────────────────────────────────────────────────────────────
if len(doc.tables) > 1:
    tbl1 = doc.tables[1]
    # Row 5 (index 5): неверная дата контракта и номер
    for cell in tbl1.rows[5].cells:
        track_cell_replace(cell, "19 января 2023 г.", "09 января 2023 г.")
        track_cell_replace(cell, "01/ОК-2021", "01/ОК-2023")
    # Row 6 (index 6): "Этап 132" → "Этап 2"
    for cell in tbl1.rows[6].cells:
        track_cell_replace(cell, "132", "2")
    # Row 12 (index 12): год "2020" → "2023"
    for cell in tbl1.rows[12].cells:
        track_cell_replace(cell, "2020", "2023")

# ──────────────────────────────────────────────────────────────────
# 3. 1.2 — предложение неполное: добавить "осуществляется"
# ──────────────────────────────────────────────────────────────────
p52 = paras[52]
track_replace(p52,
    "Выполнение работ по развитию Системы на основании Контракта",
    "Работы по развитию Системы выполняются на основании Контракта")

# ──────────────────────────────────────────────────────────────────
# 4. 1.3 — Заказчик: ошибки падежа и регистра
# ──────────────────────────────────────────────────────────────────
p55 = paras[55]
# "Общество с ограниченными ответственностью" → "общество с ограниченной ответственностью"
track_replace(p55, "Общество с ограниченными ответственностью",
                    "общество с ограниченной ответственностью")

# ──────────────────────────────────────────────────────────────────
# 5. 1.5.1 — Система предназначен (несогласование), аббревиатуры
# ──────────────────────────────────────────────────────────────────
p62 = paras[62]
track_replace(p62, "предназначен для", "предназначена для")
track_replace(p62, "адм-ции образной организации",
                    "администрации образовательной организации")

# ──────────────────────────────────────────────────────────────────
# 6. 1.5.2 — "являются создание" → "является создание"; запятая → точка
# ──────────────────────────────────────────────────────────────────
p64 = paras[64]
track_replace(p64, "являются создание", "является создание")
# Последний символ ";" → "."
full64 = p64.text
if full64.rstrip().endswith(";"):
    track_replace(p64, full64.rstrip()[-1], ".")

# ──────────────────────────────────────────────────────────────────
# 7. 1.5.2 — грубая грамматическая ошибка: падежи и двоеточие
# ──────────────────────────────────────────────────────────────────
p65 = paras[65]
track_replace(p65,
    "задача повышение информирование участники образовательный процесса за счет",
    "задача: повышение информированности участников образовательного процесса за счёт")

# ──────────────────────────────────────────────────────────────────
# 8. 3.4.3 — "по средством" → "посредством"
# ──────────────────────────────────────────────────────────────────
p81 = paras[81]
track_replace(p81, "по средством", "посредством")

# ──────────────────────────────────────────────────────────────────
# 9. 3.4.3 — "должен быть эргономичным" (требование в тексте ТП)
# ──────────────────────────────────────────────────────────────────
p89 = paras[89]
track_replace(p89, "должен быть эргономичным", "является эргономичным")

# ──────────────────────────────────────────────────────────────────
# 10. 3.5 — несогласование рода: "модернизирован Мобильное приложение"
# ──────────────────────────────────────────────────────────────────
p96 = paras[96]
track_replace(p96, "модернизирован Мобильное", "модернизировано мобильное")

# ──────────────────────────────────────────────────────────────────
# 11. 3.5 — отсутствие точки в конце предложений
# ──────────────────────────────────────────────────────────────────
p97 = paras[97]
if not p97.text.rstrip().endswith((".", ":", ";")):
    track_append_text(p97, ".")

p98 = paras[98]
# "демо версия" → "демо-версия"
track_replace(p98, "демо версия", "демо-версия")
if not p98.text.rstrip().endswith((".", ":", ";")):
    track_append_text(p98, ".")

# ──────────────────────────────────────────────────────────────────
# 12. Список п.100-102: "не доступным" → "недоступным"
# ──────────────────────────────────────────────────────────────────
p102 = paras[102]
track_replace(p102, "становится не доступным", "становится недоступным")

# ──────────────────────────────────────────────────────────────────
# 13. п.103: отсутствие точки после "мобильного приложения"
# ──────────────────────────────────────────────────────────────────
p103 = paras[103]
if not p103.text.rstrip().endswith((".", ":", ";")):
    track_append_text(p103, ".")

# ──────────────────────────────────────────────────────────────────
# 14. п.104: сломанная перекрёстная ссылка — отметить замечанием
# ──────────────────────────────────────────────────────────────────
p104 = paras[104]
add_comment_run(p104,
    "Сломанная перекрёстная ссылка «Ошибка! Источник ссылки не найден.» — "
    "необходимо восстановить ссылку на рисунок с формой авторизации "
    "(предположительно Рисунок 1)")

# ──────────────────────────────────────────────────────────────────
# 15. Названия рисунков: нумерация и оформление
# ──────────────────────────────────────────────────────────────────
# [107]: "Рисунок  – Модальное окно" → "Рисунок 2 – Модальное окно"
p107 = paras[107]
track_replace(p107, "Рисунок  –", "Рисунок 2 –")

# [109]: "Рис. 2." — неверный формат подписи; должно быть удалено
# (является дублем либо должно быть: "Рисунок 1 – Форма авторизации демо-версии")
p109 = paras[109]
track_replace(p109, "Рис. 2.", "Рисунок 1 – Форма авторизации для демо-версии мобильного приложения")
add_comment_run(p109,
    "Подпись рисунка оформлена неверно: «Рис. 2.» — по ГОСТ 2.105 следует "
    "«Рисунок N – Наименование». Уточните наименование и номер.")

# Элементы списка: прописная → строчная буква в начале
p114 = paras[114]
track_replace(p114, "Раздел «Календарь»", "раздел «Календарь»")

p117 = paras[117]
track_replace(p117, "Раздел «Уведомления»", "раздел «Уведомления»")

p121 = paras[121]
track_replace(p121, "Раздел «Библиотека»", "раздел «Библиотека»")

# ──────────────────────────────────────────────────────────────────
# 16. [120]: раздел «Журналы — нет закрывающей кавычки и точки с запятой
# ──────────────────────────────────────────────────────────────────
p120 = paras[120]
track_replace(p120, "раздел «Журналы", "раздел «Журналы»;")

# ──────────────────────────────────────────────────────────────────
# 17. [125]: "Рисунок  Разделы" → "Рисунок 3 – Разделы"
# ──────────────────────────────────────────────────────────────────
p125 = paras[125]
track_replace(p125, "Рисунок  Разделы", "Рисунок 3 – Разделы")

# ──────────────────────────────────────────────────────────────────
# 18. [127]: номер рисунка и замена кавычек
# ──────────────────────────────────────────────────────────────────
p127 = paras[127]
track_replace(p127, "Рисунок  –", "Рисунок 4 –")
track_replace(p127, '"Учитель"', '«Учитель»')

# ──────────────────────────────────────────────────────────────────
# 19. [128]: некорректная ссылка и кавычки
# ──────────────────────────────────────────────────────────────────
p128 = paras[128]
track_replace(p128,
    "На рисунках 1 – Рисунок 4 – Разделы демо-версии мобильного приложения для роли \"Учитель\" настоящего документа представле",
    "На рисунках 1–4 настоящего документа представле")
# Дополнительно — кавычки (если вариант с полным текстом не сработал — ловим отдельно)
track_replace(p128, '"Учитель"', '«Учитель»')

# ──────────────────────────────────────────────────────────────────
# 20. [130]: отсутствие точки в конце
# ──────────────────────────────────────────────────────────────────
p130 = paras[130]
if not p130.text.rstrip().endswith((".", ":", ";")):
    track_append_text(p130, ".")

# ──────────────────────────────────────────────────────────────────
# 21. [116]: "раздел «Личный кабинет»" — нет знака препинания
# ──────────────────────────────────────────────────────────────────
p116 = paras[116]
if not p116.text.rstrip().endswith((".", ":", ";")):
    add_comment_run(p116,
        "Отсутствует знак препинания в конце элемента списка (ожидается «;»)")

# ──────────────────────────────────────────────────────────────────
# 22. [112]: "раздел «Дневник»" — нет точки с запятой
# ──────────────────────────────────────────────────────────────────
p112 = paras[112]
if not p112.text.rstrip().endswith((".", ":", ";")):
    track_append_text(p112, ";")

# ──────────────────────────────────────────────────────────────────
# 23. [122]: "раздел «Личный кабинет»;" — уже есть ";"? Проверить
# ──────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────
# Save
# ──────────────────────────────────────────────────────────────────
doc.save(str(DEST))
print(f"Сохранено: {DEST}")
print(f"Всего отметок рецензии: {_cid[0] - 1}")
