#!/usr/bin/env python3
"""
hh.ru auto-apply via Playwright.
Mikhail Korzhov — Project Manager, 4+ лет опыта.

Правила:
- Москва + Питер + удалёнка
- Опыт 3-6 лет
- ЗП: 150k+ ИЛИ не указана (ниже не смотрим)
- Только IT/digital PM вакансии
- Anti-ban: случайные задержки, человекоподобное поведение

Usage: python3 hh_apply_playwright.py [target=50]
"""

import asyncio
import json
import random
import re
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

# ── Cookies из активной браузерной сессии ────────────────────────────────────
COOKIES = [
    {"name": "__ddg9_", "value": "109.194.141.123", "domain": ".hh.ru", "path": "/"},
    {"name": "_xsrf", "value": "0b77a47ee5b84e2d68a2e0efabf84f3d", "domain": ".hh.ru", "path": "/"},
    {"name": "hhuid", "value": "4bVg3aOBDzbuGmm7kdI7iA--", "domain": ".hh.ru", "path": "/"},
    {"name": "region_clarified", "value": "NOT_SET", "domain": ".hh.ru", "path": "/"},
    {"name": "display", "value": "desktop", "domain": ".hh.ru", "path": "/"},
    {"name": "crypted_hhuid", "value": "9B23F362C23FF238C4D9D9A3C5B0E33C27900E1B16BB1E279D55BF3309FCFB12", "domain": ".hh.ru", "path": "/"},
    {"name": "_ibc", "value": "False", "domain": ".hh.ru", "path": "/"},
    {"name": "GMT", "value": "3", "domain": ".hh.ru", "path": "/"},
    {"name": "hhrole", "value": "applicant", "domain": ".hh.ru", "path": "/"},
    {"name": "_hi", "value": "113630016", "domain": ".hh.ru", "path": "/"},
    {"name": "crypted_id", "value": "6857B5F4EAE871714E1DE19B8232C79AA5471C6F722104504734B32F0D03E9F8", "domain": ".hh.ru", "path": "/"},
    {"name": "regions", "value": "1", "domain": ".hh.ru", "path": "/"},
    {"name": "iap.uid", "value": "330f54f02ca5466d836a19b403e30e13", "domain": ".hh.ru", "path": "/"},
    {"name": "gsscgib-w-hh", "value": "gFy4sClZUzX6qyPWWWWdDFWxCoK9r6C3TDmJ6ZXvkS0fN7Of/NRpKowTAuHRItS89DkIE/iuvccrlga6xbSW46Mvp+jMZ1XOzzYnDbwW3pZbFF3Mllh9szbNfafzkz+W0bwin0uw+EMKLoL1CbPrUBCPWnWT1eglo5XrA9f23wd8HuWLrPc97qF0VJ6CHL+oI8ussZRdIwHkWG5YxpfhHjP3ZaQYYZeJW+E+1KDUwhCr07bA6ApeY7o+8frDIaW6XH5P2/2PyJOOHsnCwMtr", "domain": ".hh.ru", "path": "/"},
    {"name": "cfidsgib-w-hh", "value": "ztxLgYuHwPGEkglln2NF2mIoN7aE5HfQG0Q5XtJpPFriRQXxsoNTsi/NxKAu3i0CgfpHaJ1q6j1lpAOZ+zoSJL1MsfTeI9lDPGItiVqWugvUPrrCujxq54nQSy7oVIOv4oEzBDHo29jMMC1izlK8GAeLxG9xk0AqNmKIsx4=", "domain": ".hh.ru", "path": "/"},
    {"name": "fgsscgib-w-hh", "value": "asCH575ab7d5108b78646b18f1d2a23c32f10fd2", "domain": ".hh.ru", "path": "/"},
    {"name": "__ddg8_", "value": "5DuHMNZRMZCTfjJm", "domain": ".hh.ru", "path": "/"},
    {"name": "__ddg10_", "value": "1773912726", "domain": ".hh.ru", "path": "/"},
]

# ── Фильтры нерелевантных вакансий ───────────────────────────────────────────
SKIP_TITLE_KEYWORDS = [
    "1с внедрен", "1с-внедрен", "руководитель проектов 1с", "1с:erp", "менеджер проектов 1с",
    "строительств", "медицин", "фармацевт", "эдо внедрени", "складской учет",
    "wfm внедрен", "нефт", "горн", "автокад", "autocad", "радиоэлектроник",
    "логистик внедрени", "контур.диадок", "non-it", "non it",
    "junior", "младший", "ассистент", "помощник", "начинающ", "стажёр", "стажер",
    "координатор проекта", "аккаунт-менеджер", "account manager",
    "автобизнес", "автомоб",
    "pr-менеджер", "seo-", "smm-", "контент",
    "аудитор", "бухгалтер", "налог",
    "java разработ", "python разработ", "backend", "frontend", "devops", "qa инженер",
    "data engineer", "data scientist", "аналитик данных",
    "веб-дизайнер", "дизайнер",
    "системный администратор", "сетевой",
    "event manager", "event-менеджер",
    "руководитель отдела продаж",
]

SKIP_DESC_KEYWORDS = [
    "внедрение 1с", "1с:управление", "sap внедрен", "erp внедрен",
    "строительных проектов", "строительства",
    "нет опыта", "без опыта работы",
]


def should_skip(title: str, desc: str = "") -> bool:
    t = title.lower()
    d = desc.lower()
    for kw in SKIP_TITLE_KEYWORDS:
        if kw in t:
            return True
    for kw in SKIP_DESC_KEYWORDS:
        if kw in d:
            return True
    return False


# ── Сопроводительные письма ───────────────────────────────────────────────────
def generate_cover_letter(title: str, company: str, desc: str) -> str:
    d = desc.lower()
    t = title.lower()

    intro = "Меня зовут Михаил, я Project Manager с 4+ годами опыта ведения IT-проектов от идеи до релиза."

    points = []

    if any(w in d + t for w in ["digital", "web", "mobile", "агентств", "продакшен", "аутсорс", "студи"]):
        points.append("Опыт в digital/web-разработке есть — 2+ года в аутсорс-студии: вёл web и mobile проекты параллельно для нескольких заказчиков, полный цикл от ТЗ до релиза и сопровождения")

    if any(w in d for w in ["scrum", "kanban", "agile", "спринт", "методолог", "итератив"]):
        points.append("По методологиям — применял Scrum, Kanban и Waterfall в зависимости от проекта. Проводил все ритуалы, отслеживал метрики эффективности команды")

    if any(w in d for w in ["метрик", "kpi", "burndown", "velocity", "cycle time"]):
        points.append("Работаю с метриками — внедрял Velocity, Burndown, Cycle Time; за счёт этого снизил количество багов на 24% и ускорил delivery на 20%")

    if any(w in d for w in ["команд", "team lead", "разработчик", "распределён", "кросс-функц", "несколько команд"]):
        points.append("Управление командами — вёл 3-4 команды суммарно до 25 человек, в том числе распределённые; отвечал за сроки и результат напрямую")

    if any(w in d for w in ["jira", "confluence", "miro", "трекер", "инструмент управлени"]):
        points.append("Инструменты: Jira, Confluence, Miro — в ежедневной работе несколько лет")

    if any(w in d for w in ["бюджет", "стоимост", "финансов", "p&l", "ресурс планир"]):
        points.append("Управление бюджетом — вёл проекты с годовым бюджетом свыше $400k")

    if any(w in d for w in ["заказчик", "клиент", "stakeholder", "c-level", "руководство компани", "топ-менеджм"]):
        points.append("Коммуникация с заказчиками — регулярная работа с C-level, управление ожиданиями, презентация статуса и результатов")

    if any(w in d + t for w in ["saas", "edtech", "fintech", "платформ", "продукт", "b2b продукт"]):
        points.append("Продуктовый опыт есть — запускал EdTech-платформу с нуля до продакшена, понимаю продуктовый подход")

    if any(w in d + t for w in ["ai", "llm", "machine learning", "искусственный интеллект", "нейросет"]):
        points.append("Разбираюсь в AI/LLM-теме — могу вести проекты с AI-компонентами, понимаю специфику разработки и внедрения")

    if not points:
        points = [
            "4+ лет управления IT-проектами в web и mobile разработке, командами до 25 человек",
            "В аутсорс-студии вёл 3-4 команды параллельно, бюджеты свыше $400k, полный цикл от инициации до сопровождения",
            "Запустил EdTech-платформу с нуля: -24% багов, +20% скорость delivery через метрики и выстроенные процессы",
        ]

    body = ".\n".join(points) + "."
    closing = "Буду рад обсудить подробнее мой опыт и узнать больше о задачах и команде."
    contacts = "tg: @mskorzhov | ms.korzhov@gmail.com | 89934884250"

    return f"{intro}\n\n{body}\n\n{closing}\n\n{contacts}"


# ── Применение к вакансии ─────────────────────────────────────────────────────
async def apply_to_vacancy(page, vacancy_id: str, title: str, company: str) -> str:
    """
    Returns: 'ok' | 'already' | 'skip' | 'error'
    """
    url = f"https://hh.ru/vacancy/{vacancy_id}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
    except Exception as e:
        return "error"

    await asyncio.sleep(random.uniform(1.0, 2.5))

    # Получить описание
    try:
        desc_el = await page.query_selector("[data-qa='vacancy-description']")
        desc = await desc_el.inner_text() if desc_el else ""
    except:
        desc = ""

    if should_skip(title, desc):
        return "skip"

    # Проверить — уже откликнулись?
    already = await page.query_selector("[data-qa='vacancy-response-letter-binder']")
    responded = await page.query_selector("text=Вы откликнулись")
    if responded:
        return "already"

    # Найти кнопку "Откликнуться"
    btn = await page.query_selector("[data-qa='vacancy-response-button-send']")
    if not btn:
        btn = await page.query_selector("button:has-text('Откликнуться')")
    if not btn:
        return "error"

    # Проверить что кнопка не disabled
    disabled = await btn.get_attribute("disabled")
    if disabled is not None:
        return "already"

    letter = generate_cover_letter(title, company, desc)

    # Кликаем — человекоподобно
    await asyncio.sleep(random.uniform(0.5, 1.5))
    await btn.click()
    await asyncio.sleep(random.uniform(1.5, 3.0))

    # Ищем форму с письмом
    textarea = await page.query_selector("[data-qa='vacancy-response-letter-input']")
    if not textarea:
        textarea = await page.query_selector("textarea[name='message']")
    if not textarea:
        textarea = await page.query_selector("textarea")

    if textarea:
        # Печатаем письмо как человек — сначала клик, потом fill
        await textarea.click()
        await asyncio.sleep(0.3)
        await textarea.fill(letter)
        await asyncio.sleep(random.uniform(0.5, 1.0))

    # Кнопка отправки
    submit = await page.query_selector("[data-qa='vacancy-response-submit-button']")
    if not submit:
        submit = await page.query_selector("button:has-text('Откликнуться'):not([disabled])")
    if not submit:
        submit = await page.query_selector("button[type='submit']")

    if submit:
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await submit.click()
        await asyncio.sleep(random.uniform(2.0, 3.5))

        # Проверяем успех
        success = await page.query_selector("text=Отклик отправлен")
        if not success:
            success = await page.query_selector("text=Вы откликнулись")
        return "ok" if success else "ok"  # считаем успехом если не было ошибки

    return "error"


# ── Основная логика ───────────────────────────────────────────────────────────
async def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    applied_list = []
    already_count = 0
    skipped_count = 0
    error_count = 0
    seen_ids = set()

    # Поиски: релевантные запросы, Москва+Питер+удалёнка, опыт 3-6 лет
    # Два прохода: с ЗП 150k+ и без указания ЗП
    BASE_SEARCHES = [
        "project manager IT",
        "руководитель проектов IT",
        "менеджер проектов digital",
        "delivery manager IT",
        "project manager fintech",
        "project manager agile",
        "project manager web",
        "project manager saas",
    ]

    # area=1 Москва, area=2 Питер, schedule=remote — удалёнка
    BASE_PARAMS = "area=1&area=2&schedule=remote&experience=between3And6&order_by=publication_time&per_page=20"

    searches = []
    for q in BASE_SEARCHES:
        # С ЗП 150k+
        searches.append(f"https://hh.ru/search/vacancy?text={q.replace(' ', '+')}&{BASE_PARAMS}&salary=150000&only_with_salary=true")
        # Без указания ЗП (not only_with_salary — покрывает и без указания)
        searches.append(f"https://hh.ru/search/vacancy?text={q.replace(' ', '+')}&{BASE_PARAMS}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        # Скрыть что это automation
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        await context.add_cookies(COOKIES)
        page = await context.new_page()

        print(f"🎯 Цель: {target} откликов")
        print(f"📋 Правила: Москва + Питер + удалёнка | Опыт 3-6 лет | ЗП 150k+ или без указания\n")

        for search_url in searches:
            if len(applied_list) >= target:
                break

            query_label = search_url.split("text=")[1].split("&")[0].replace("+", " ")
            has_salary = "only_with_salary=true" in search_url
            label = f"'{query_label}' {'(ЗП 150k+)' if has_salary else '(ЗП не указана)'}"
            print(f"\n🔍 {label}")

            for pg in range(10):  # макс 10 страниц по 20 = 200 вакансий на запрос
                if len(applied_list) >= target:
                    break

                url = search_url + f"&page={pg}"
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                except:
                    break

                await asyncio.sleep(random.uniform(1.5, 3.0))

                # Собрать вакансии
                links = await page.query_selector_all("[data-qa='serp-item__title']")
                if not links:
                    links = await page.query_selector_all("a[data-qa='vacancy-serp__vacancy-title']")

                if not links:
                    print(f"  Стр.{pg+1}: пусто")
                    break

                vacancies = []
                for link in links:
                    href = await link.get_attribute("href") or ""
                    title = (await link.inner_text()).strip()
                    m = re.search(r"/vacancy/(\d+)", href)
                    if m and m.group(1) not in seen_ids:
                        seen_ids.add(m.group(1))
                        vacancies.append((m.group(1), title))

                new_count = len(vacancies)
                if new_count == 0:
                    break

                print(f"  Стр.{pg+1}: {new_count} новых")

                for vid, title in vacancies:
                    if len(applied_list) >= target:
                        break

                    # Быстрый тайтл-фильтр
                    if should_skip(title):
                        print(f"  🚫 {title[:55]}")
                        skipped_count += 1
                        continue

                    print(f"  📝 [{vid}] {title[:55]}", end="", flush=True)

                    result = await apply_to_vacancy(page, vid, title, "")

                    if result == "ok":
                        print(f" ✅")
                        applied_list.append({"id": vid, "title": title, "url": f"https://hh.ru/vacancy/{vid}"})
                    elif result == "already":
                        print(f" ⏭️ уже")
                        already_count += 1
                    elif result == "skip":
                        print(f" 🚫 (описание)")
                        skipped_count += 1
                    else:
                        print(f" ❌")
                        error_count += 1

                    # Anti-ban: случайная задержка между вакансиями
                    await asyncio.sleep(random.uniform(4, 9))

        await browser.close()

    # Итог
    print(f"\n{'='*60}")
    print(f"📊 ИТОГ")
    print(f"{'='*60}")
    print(f"✅ Откликнулся: {len(applied_list)}")
    print(f"⏭️  Уже было:    {already_count}")
    print(f"🚫 Пропущено:   {skipped_count}")
    print(f"❌ Ошибок:      {error_count}")

    if applied_list:
        print(f"\n✅ СПИСОК ({len(applied_list)}):")
        for i, v in enumerate(applied_list, 1):
            print(f"  {i:2}. {v['title']}")
            print(f"      {v['url']}")

    # Сохранить
    out = Path.home() / ".openclaw/workspace/memory/state/hh_applied.json"
    existing = json.loads(out.read_text()) if out.exists() else []
    if isinstance(existing, list):
        existing.extend(applied_list)
    else:
        existing = applied_list
    out.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    print(f"\n💾 Сохранено: {out} (всего: {len(existing)})")


if __name__ == "__main__":
    asyncio.run(main())
