#!/usr/bin/env python3
"""
hh.ru auto-apply script for Mikhail Korzhov (Project Manager)
Uses browser session cookies to apply to vacancies with unique cover letters.
"""

import requests
import json
import time
import random
import re
import sys
from pathlib import Path

# ── Auth ──────────────────────────────────────────────────────────────────────
COOKIES = {
    "__ddg9_": "109.194.141.123",
    "_xsrf": "0b77a47ee5b84e2d68a2e0efabf84f3d",
    "hhuid": "4bVg3aOBDzbuGmm7kdI7iA--",
    "region_clarified": "NOT_SET",
    "display": "desktop",
    "crypted_hhuid": "9B23F362C23FF238C4D9D9A3C5B0E33C27900E1B16BB1E279D55BF3309FCFB12",
    "_ibc": "False",
    "GMT": "3",
    "hhrole": "applicant",
    "_hi": "113630016",
    "crypted_id": "6857B5F4EAE871714E1DE19B8232C79AA5471C6F722104504734B32F0D03E9F8",
    "regions": "1",
    "iap.uid": "330f54f02ca5466d836a19b403e30e13",
    "uxs_uid": "6f0b7780-2359-11f1-9a37-df9305babeb5",
    "domain_sid": "Z-GNvrYhZFfIMO85o2ihH%3A1773900244943",
    "gsscgib-w-hh": "Qb++mL5jLzTaLwPRnkZI4J9ZmDrIIFcx7UjdXlvTPZ3Y3GaLT1r/aMiXQuFsGkCv/CY0cAqVhBgw9/SxAPF1whOxPrHBPnp8TPl5XHdrNjbEYHLBWGHZG+oXW2rmsmujCave5speO90llP8T6IxGPVRuwiPL4tjIkgpaMsiM1gKxKRUoNnKblwgaPztiKwUZeeS8+vH4nsva//SPVkhsOW4/vPYcePK2DvlOVcDtKSdTqBUTqbiVymzcJnrALEDKdzz1mPqhmXTVOtmzwyMI",
    "cfidsgib-w-hh": "HA1RFXDXvKeGZxj+gsq24PkbVRzRLG8iNwtEQOO8/di++6g3RhCmCd3C5vfVMteTzhMAsn3I1IrcX83HMfSijDq56iGOGdycaJJ3TjvvqPj5IgYTdfmq5qF1WDzdd/c3NzHiHA6tjZbvnvbcWBA5spKMw5u0EbylGLinwlA=",
    "fgsscgib-w-hh": "QjDe57183278f7d251f6c3b31f108653c69f05a1",
    "__ddg8_": "m5nj3jlBW7qfagXD",
    "__ddg10_": "1773902953",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "X-Xsrftoken": "0b77a47ee5b84e2d68a2e0efabf84f3d",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://hh.ru/",
    "Origin": "https://hh.ru",
}

RESUME_ID = "85bac3b7ff09d1a6fa0039ed1f656e665a6f44"

# ── Candidate profile ─────────────────────────────────────────────────────────
PROFILE = """
Михаил Коржов, Project Manager, 4+ года опыта.
- Аутсорс-студия 2+ года: 3-4 команды параллельно, до 25 человек, web+mobile (PHP/React/JS/Kotlin/Swift), 
  Scrum/Kanban/Waterfall, бюджеты $400k+, полный цикл от инициации до релиза и сопровождения
- EdTech запуск платформы с нуля: метрики Velocity/Burndown/Cycle Time, -24% багов, +20% delivery speed
- Инструменты: Jira, Confluence, Miro
- Контакты: tg: @mskorzhov | ms.korzhov@gmail.com | 89934884250
- Готов к офису в Москве
"""

# ── Skip keywords ─────────────────────────────────────────────────────────────
SKIP_KEYWORDS = [
    "1С", "строительств", "медицин", "фармацевт", "ЭДО внедрени",
    "Битрикс24 внедрени", "SAP", "логистик внедрени", "нефт", "горн",
    "складск", "WFM внедрен", "банковск процесс"
]

def should_skip(title: str, description: str = "") -> bool:
    text = (title + " " + description).lower()
    for kw in SKIP_KEYWORDS:
        if kw.lower() in text:
            return True
    return False

def generate_cover_letter(vacancy_name: str, company_name: str, requirements: str, salary: str) -> str:
    """Generate a unique cover letter based on vacancy requirements."""
    
    # Parse key requirements to address
    req_lower = requirements.lower()
    
    intro = f"Меня зовут Михаил, я Project Manager с 4+ годами опыта ведения IT-проектов от идеи до релиза."
    
    # Build specific matching
    specific = []
    
    if any(w in req_lower for w in ["digital", "web", "mobile", "агентств", "продакшен", "студи"]):
        specific.append("Опыт в digital/web-разработке есть — 2+ года в аутсорс-студии: вёл web и mobile проекты параллельно для разных заказчиков, полный цикл от ТЗ до релиза")
    
    if any(w in req_lower for w in ["scrum", "kanban", "agile", "спринт", "metodolog"]):
        specific.append("По методологиям подхожу — применял Scrum, Kanban и Waterfall в зависимости от проекта, проводил все скрам-ритуалы, поддерживал метрики эффективности команды")
    
    if any(w in req_lower for w in ["метрик", "kpi", "burndown", "velocity", "аналитик"]):
        specific.append("Умею работать с метриками — внедрял Velocity, Burndown Chart, Cycle Time; за счёт этого снизил количество багов на 24% и ускорил delivery на 20%")
    
    if any(w in req_lower for w in ["команд", "team", "разработчик", "распределён"]):
        specific.append("Управление командами — вёл 3-4 команды суммарно до 25 человек, в том числе распределённые, отвечал за сроки и результат напрямую")
    
    if any(w in req_lower for w in ["jira", "confluence", "miro", "трекер", "инструмент"]):
        specific.append("Инструменты: Jira, Confluence, Miro — в ежедневной работе несколько лет")
    
    if any(w in req_lower for w in ["бюджет", "стоимост", "ресурс", "400"]):
        specific.append("Управление бюджетом — вёл проекты с годовым бюджетом свыше $400k")
    
    if any(w in req_lower for w in ["stakeholder", "заказчик", "клиент", "c-level", "руководств"]):
        specific.append("Работа с заказчиками — регулярно общался с C-level, управлял ожиданиями, презентовал статус и результаты")
    
    if any(w in req_lower for w in ["saas", "продукт", "product"]):
        specific.append("Есть продуктовый опыт — запускал web-платформу в EdTech с нуля до продакшена, понимаю продуктовый подход")
    
    if any(w in req_lower for w in ["риск", "risk"]):
        specific.append("Управление рисками — составлял реестры рисков, своевременно эскалировал и принимал решения")
    
    # Default if no specific matches
    if not specific:
        specific = [
            "4+ лет управления IT-проектами в web и mobile разработке, командами до 25 человек",
            "Запускал платформу с нуля в EdTech: метрики, процессы, результат — -24% багов, +20% скорость delivery"
        ]
    
    specific_text = ".\n".join(specific) + "."
    
    closing = "Можем подробнее обсудить мой опыт и проекты, а также буду рад узнать подробнее о задачах и компании."
    contacts = "tg: @mskorzhov | ms.korzhov@gmail.com | 89934884250"
    
    return f"{intro}\n\n{specific_text}\n\n{closing}\n\n{contacts}"


def search_vacancies(page: int = 0, per_page: int = 20, text: str = "project manager") -> dict:
    """Search vacancies via hh.ru API."""
    params = {
        "text": text,
        "area": "1",  # Moscow
        "salary": "150000",
        "only_with_salary": "true",
        "order_by": "salary_desc",
        "schedule": ["remote", "fullDay"],
        "experience": "between3And6",
        "professional_role": "107",
        "per_page": per_page,
        "page": page,
    }
    
    resp = requests.get(
        "https://api.hh.ru/vacancies",
        params=params,
        headers=HEADERS,
        cookies=COOKIES,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def get_vacancy_details(vacancy_id: str) -> dict:
    """Get full vacancy info."""
    resp = requests.get(
        f"https://api.hh.ru/vacancies/{vacancy_id}",
        headers=HEADERS,
        cookies=COOKIES,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def apply_to_vacancy(vacancy_id: str, cover_letter: str) -> bool:
    """Apply to a vacancy."""
    data = {
        "vacancy_id": vacancy_id,
        "resume_id": RESUME_ID,
        "message": cover_letter,
    }
    
    resp = requests.post(
        "https://api.hh.ru/negotiations",
        json=data,
        headers={**HEADERS, "Content-Type": "application/json"},
        cookies=COOKIES,
        timeout=15
    )
    
    if resp.status_code == 201:
        return True
    elif resp.status_code == 403:
        print(f"  ⚠️  403 — уже откликнулся или требует токен")
        return False
    elif resp.status_code == 400:
        err = resp.json()
        print(f"  ⚠️  400 — {err.get('description', err)}")
        return False
    else:
        print(f"  ⚠️  {resp.status_code} — {resp.text[:200]}")
        return False


def extract_requirements(vacancy: dict) -> str:
    """Extract requirements text from vacancy."""
    desc = vacancy.get("description", "")
    # Strip HTML
    clean = re.sub(r'<[^>]+>', ' ', desc)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:2000]


def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    applied = []
    skipped = []
    errors = []
    
    searches = [
        "project manager",
        "руководитель проектов",
        "менеджер проектов IT",
        "project lead",
    ]
    
    seen_ids = set()
    
    print(f"🎯 Цель: {target} откликов\n")
    
    for search_text in searches:
        if len(applied) >= target:
            break
            
        print(f"\n🔍 Поиск: '{search_text}'")
        
        for page in range(5):
            if len(applied) >= target:
                break
            
            try:
                data = search_vacancies(page=page, text=search_text)
            except Exception as e:
                print(f"  ❌ Ошибка поиска: {e}")
                break
            
            items = data.get("items", [])
            if not items:
                break
            
            print(f"  Страница {page+1}: {len(items)} вакансий")
            
            for item in items:
                if len(applied) >= target:
                    break
                
                vid = item["id"]
                if vid in seen_ids:
                    continue
                seen_ids.add(vid)
                
                title = item.get("name", "")
                company = item.get("employer", {}).get("name", "")
                salary = item.get("salary", {})
                salary_str = ""
                if salary:
                    fr = salary.get("from", "")
                    to = salary.get("to", "")
                    cur = salary.get("currency", "RUR")
                    salary_str = f"{fr or ''}-{to or ''} {cur}".strip("-")
                
                # Check already applied
                already = item.get("relations", [])
                if "negotiation" in str(already):
                    print(f"  ⏭️  [{vid}] {title} — уже откликнулся")
                    skipped.append({"id": vid, "reason": "already"})
                    continue
                
                # Skip unsuitable
                if should_skip(title):
                    print(f"  🚫 [{vid}] {title} — пропускаю (не подходит)")
                    skipped.append({"id": vid, "reason": "unsuitable", "title": title})
                    continue
                
                # Get details
                try:
                    details = get_vacancy_details(vid)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  ❌ [{vid}] Ошибка деталей: {e}")
                    continue
                
                requirements = extract_requirements(details)
                
                if should_skip(title, requirements):
                    print(f"  🚫 [{vid}] {title} — пропускаю (по описанию)")
                    skipped.append({"id": vid, "reason": "unsuitable", "title": title})
                    continue
                
                # Generate cover letter
                letter = generate_cover_letter(title, company, requirements, salary_str)
                
                print(f"  📝 [{vid}] {title} | {company} | {salary_str}")
                
                # Apply
                success = apply_to_vacancy(vid, letter)
                
                if success:
                    print(f"  ✅ Отклик отправлен!")
                    applied.append({
                        "id": vid,
                        "title": title,
                        "company": company,
                        "salary": salary_str,
                    })
                else:
                    errors.append({"id": vid, "title": title})
                
                # Delay to avoid rate limiting
                time.sleep(random.uniform(2, 4))
    
    # Report
    print(f"\n{'='*60}")
    print(f"📊 ИТОГ")
    print(f"{'='*60}")
    print(f"✅ Откликнулся: {len(applied)}")
    print(f"🚫 Пропущено: {len(skipped)}")
    print(f"❌ Ошибок: {len(errors)}")
    print()
    
    if applied:
        print("✅ ОТКЛИКИ:")
        for i, v in enumerate(applied, 1):
            print(f"  {i}. {v['company']} — {v['title']} | {v['salary']}")
    
    # Save results
    result_path = Path.home() / ".openclaw/workspace/memory/state/hh_applied.json"
    with open(result_path, "w") as f:
        json.dump({"applied": applied, "skipped": skipped, "errors": errors}, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Результаты сохранены в {result_path}")
    return len(applied)


if __name__ == "__main__":
    main()
