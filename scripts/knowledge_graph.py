#!/usr/bin/env python3
"""
Knowledge Graph for Аркаша — backed by KuzuDB (embedded graph DB).

Commands:
  python3 knowledge_graph.py build              — index all memory/*.md files (incremental)
  python3 knowledge_graph.py build --full       — full rebuild (ignore hashes)
  python3 knowledge_graph.py build-sessions     — index user messages from JSONL sessions
  python3 knowledge_graph.py query "Денис"      — find everything related to entity
  python3 knowledge_graph.py status             — graph statistics
"""

import sys
import os
import hashlib
import json
import subprocess
import importlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Bootstrap: ensure kuzu is installed
# ---------------------------------------------------------------------------

def ensure_deps():
    missing = []
    for pkg in ["kuzu", "numpy", "pandas", "instructor", "openai"]:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[bootstrap] Installing {' '.join(missing)}...", file=sys.stderr)
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", *missing,
            "--break-system-packages", "-q"
        ])
        importlib.invalidate_caches()

ensure_deps()
import kuzu  # noqa: E402

# ---------------------------------------------------------------------------
# Entity normalization — aliases → canonical names
# ---------------------------------------------------------------------------

KNOWN_ENTITIES: dict[str, str] = {
    # Аркаша (agent)
    "Аркаша":          "Аркаша ⚡",
    "Аркадий":         "Аркаша ⚡",
    "Arkasha":         "Аркаша ⚡",
    "Аркадий Пармеев": "Аркаша ⚡",
    "Arkady":          "Аркаша ⚡",
    # Денис
    "Denis":           "Денис Пармеев",
    "Denis Parmeev":   "Денис Пармеев",
    "Денис Пармеев":   "Денис Пармеев",
    # Прочие известные
    "OpenClaw":        "OpenClaw",
    "ClawHub":         "ClawHub",
    # Gravity
    "Gravity":              "Gravity Group",
    "IT Gravity-group":     "Gravity Group",
    "Gravity (IT Gravity-group)": "Gravity Group",
    "ООО «Гравити Групп»": "Gravity Group",
    "Gravity Telegram Group": "Gravity Group",
}

# ---------------------------------------------------------------------------
# Known Telegram chats (ID -> (canonical_name, entity_type))
# ---------------------------------------------------------------------------

KNOWN_CHATS: dict[str, tuple[str, str]] = {
    "-4958457563":      ("Gravity LLM", "Organization"),
    "-1003676744192":   ("Gravity LLM", "Organization"),
    "-5112704488":      ("Оценки Аркаша", "Organization"),
    "-5226768769":      ("Афигеваем от ассистентов", "Organization"),
    "364935958":        ("Денис Пармеев", "Person"),
}

# ---------------------------------------------------------------------------
# Noise filter — names that must NEVER be typed as Person
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# pymorphy3: module-level MorphAnalyzer (initialize once — expensive)
# ---------------------------------------------------------------------------

try:
    import pymorphy3 as _pymorphy3
    _morph = _pymorphy3.MorphAnalyzer()
except ImportError:
    _morph = None  # type: ignore


def normalize_nominative(name: str) -> str:
    """Normalize Russian name to nominative case. Skip Latin words.

    Strategy:
    - First word: look for Name-tagged parses; detect gender.
    - Subsequent words (surnames): use gender from the first name to
      disambiguate via gender agreement.
    - If a word is already in sing+nomn (matching gender) → keep as-is.
    - If pymorphy3 has no singular parses for a word → it doesn't know it →
      keep as-is (conservative).
    """
    if _morph is None:
        return name

    parts = name.strip().split()
    result = []
    detected_gender = None  # 'masc' / 'femn' from first Name word
    prev_was_name = False

    for part in parts:
        # Латиница — пропустить
        if not any('\u0400' <= c <= '\u04ff' for c in part):
            result.append(part)
            prev_was_name = False
            continue

        parses = _morph.parse(part)

        if not prev_was_name:
            # --- First name (имя) ---
            name_parses = [p for p in parses if 'Name' in p.tag]
            if name_parses:
                best = name_parses[0]
                # Extract gender
                for g in ('masc', 'femn'):
                    if g in best.tag:
                        detected_gender = g
                        break
                if 'nomn' in best.tag and 'sing' in best.tag:
                    result.append(part)
                else:
                    nomn = best.inflect({'nomn'})
                    result.append(_inflected_word(part, nomn))
                prev_was_name = True
            else:
                # Not a known name — keep as-is
                result.append(part)
                prev_was_name = False
        else:
            # --- Surname (фамилия) after a name ---
            sing_parses = [p for p in parses if 'sing' in p.tag]

            if not sing_parses:
                # pymorphy3 has no singular forms → doesn't know this word
                # (e.g. "Пармеев" parsed only as plural) → keep as-is
                result.append(part)
                continue

            # Check if word is already nomn in matching gender
            if detected_gender:
                nomn_gender = [p for p in sing_parses
                               if 'nomn' in p.tag and detected_gender in p.tag]
                if nomn_gender:
                    result.append(part)
                    continue

                # Not nomn yet → find parse with matching gender and inflect
                gendered = [p for p in sing_parses if detected_gender in p.tag]
                if gendered:
                    nomn = gendered[0].inflect({'nomn'})
                    result.append(_inflected_word(part, nomn))
                    continue

            # Fallback: check any sing,nomn parse
            any_nomn = [p for p in sing_parses if 'nomn' in p.tag]
            if any_nomn:
                result.append(part)
            else:
                nomn = sing_parses[0].inflect({'nomn'})
                result.append(_inflected_word(part, nomn))

    return ' '.join(result)


def _inflected_word(original: str, inflected) -> str:
    """Apply inflected form preserving capitalization and normalizing ё→е."""
    if inflected is None:
        return original
    word = inflected.word
    if original[0].isupper():
        word = word[0].upper() + word[1:]
    return word.replace('ё', 'е').replace('Ё', 'Е')


import re as _re

# ---------------------------------------------------------------------------
# Transliteration: Latin ↔ Cyrillic for person name deduplication
# ---------------------------------------------------------------------------

_LAT_TO_CYR: dict[str, str] = {
    'a': 'а', 'b': 'б', 'v': 'в', 'g': 'г', 'd': 'д', 'e': 'е',
    'yo': 'ё', 'zh': 'ж', 'z': 'з', 'i': 'и', 'y': 'й', 'k': 'к',
    'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р',
    's': 'с', 't': 'т', 'u': 'у', 'f': 'ф', 'kh': 'х', 'ts': 'ц',
    'ch': 'ч', 'sh': 'ш', 'shch': 'щ', 'ia': 'я', 'yu': 'ю',
    'ya': 'я', 'iu': 'ю', 'j': 'й', 'x': 'кс', 'w': 'в', 'h': 'х',
    'ey': 'ей', 'iy': 'ий', 'ay': 'ай',
}

# Build reverse map: Cyrillic → Latin (for lookup)
_CYR_TO_LAT: dict[str, str] = {}
for _lat, _cyr in _LAT_TO_CYR.items():
    if _cyr not in _CYR_TO_LAT or len(_lat) < len(_CYR_TO_LAT[_cyr]):
        _CYR_TO_LAT[_cyr] = _lat

# Known transliteration pairs: Latin name → Cyrillic canonical
_TRANSLIT_MAP: dict[str, str] = {
    "Timofey": "Тимофей",
    "Shutov": "Шутов",
    "Shutova": "Шутова",
    "Ksenia": "Ксения",
    "Kseniya": "Ксения",
    "Denis": "Денис",
    "Parmeev": "Пармеев",
    "Arkady": "Аркадий",
    "Arkasha": "Аркаша",
    "Alexey": "Алексей",
    "Aleksey": "Алексей",
    "Alexander": "Александр",
    "Aleksandr": "Александр",
    "Andrey": "Андрей",
    "Dmitry": "Дмитрий",
    "Dmitriy": "Дмитрий",
    "Evgeny": "Евгений",
    "Evgeniy": "Евгений",
    "Igor": "Игорь",
    "Ivan": "Иван",
    "Kirill": "Кирилл",
    "Konstantin": "Константин",
    "Maksim": "Максим",
    "Maxim": "Максим",
    "Mikhail": "Михаил",
    "Nikita": "Никита",
    "Nikolay": "Николай",
    "Oleg": "Олег",
    "Pavel": "Павел",
    "Roman": "Роман",
    "Ruslan": "Руслан",
    "Sergey": "Сергей",
    "Sergei": "Сергей",
    "Stanislav": "Станислав",
    "Svetlana": "Светлана",
    "Tatiana": "Татьяна",
    "Tatyana": "Татьяна",
    "Timur": "Тимур",
    "Vadim": "Вадим",
    "Valentin": "Валентин",
    "Viktor": "Виктор",
    "Vladimir": "Владимир",
    "Vladislav": "Владислав",
    "Vyacheslav": "Вячеслав",
    "Yaroslav": "Ярослав",
    "Yuri": "Юрий",
    "Yuriy": "Юрий",
    "Elena": "Елена",
    "Maria": "Мария",
    "Natalia": "Наталья",
    "Natalya": "Наталья",
    "Olga": "Ольга",
    "Anna": "Анна",
    "Irina": "Ирина",
    "Ekaterina": "Екатерина",
    "Anastasia": "Анастасия",
}

# Build case-insensitive lookup
_TRANSLIT_MAP_LOWER: dict[str, str] = {k.lower(): v for k, v in _TRANSLIT_MAP.items()}


def _transliterate_word_to_cyrillic(word: str) -> str | None:
    """Try to transliterate a single Latin word to Cyrillic using the known map."""
    lower = word.lower()
    if lower in _TRANSLIT_MAP_LOWER:
        return _TRANSLIT_MAP_LOWER[lower]
    return None


def transliterate_name_to_cyrillic(name: str) -> str | None:
    """
    Try to transliterate a full Latin name to Cyrillic.
    Returns the Cyrillic version if ALL parts can be transliterated, else None.
    """
    parts = name.strip().split()
    if not parts:
        return None
    # Only try if name is all Latin
    if any('\u0400' <= c <= '\u04ff' for c in name):
        return None  # already has Cyrillic
    
    result = []
    for part in parts:
        cyr = _transliterate_word_to_cyrillic(part)
        if cyr is None:
            return None  # can't transliterate all parts
        result.append(cyr)
    return ' '.join(result)


def is_nickname(name: str) -> bool:
    """Returns True if name looks like a username/nickname, not a real person name."""
    # Содержит цифры
    if any(c.isdigit() for c in name):
        return True
    # Содержит _ или - (типично для username)
    if '_' in name or '-' in name:
        return True
    # CamelCase без пробела (одно слово, смешанный регистр, >4 символов)
    if ' ' not in name and len(name) > 4 and name != name.lower() and name != name.upper():
        return True
    return False


# ---------------------------------------------------------------------------

NOISE_PERSONS: set[str] = {
    # Yandex SpeechKit TTS voices
    "Alena", "alena", "Алёна", "Алена",
    "Ermil", "ermil", "Эрмил",
    "Filipp", "filipp", "Филипп",
    "Jane", "Джейн",
    "Zahar", "Захар",
    "Omazh", "Oksana",
    "Alyss", "Nick",
    # Edge TTS
    "DmitryNeural", "SvetlanaNeural", "DariyaNeural",
    # Common system/model names that leak in
    "Qwen", "Claude", "GPT", "LLaMA", "Mistral",
    "whisper", "Whisper",
    # File/path patterns (extra safety)
    "AGENTS.md", "SOUL.md", "USER.md", "MEMORY.md", "TOOLS.md",
    # Fictional / test characters from design docs
    "Chapos Joe", "Joe Chapos",
    # Test/placeholder names
    "Иван Иванов", "Иванов Иван", "Петр Петров", "Петров Петр",
    "John Doe", "Jane Doe", "Test User",
}

# ---------------------------------------------------------------------------
# Post-processing noise filter — regex patterns for garbage entities
# ---------------------------------------------------------------------------

_NOISE_ENTITY_PATTERNS: list[_re.Pattern] = [
    # UUIDs (full and short hex hashes)
    _re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'),
    _re.compile(r'^[0-9a-fA-F]{12,}$'),
    # Git commit hashes (6-8 hex chars, standalone)
    _re.compile(r'^[0-9a-f]{6,8}$'),
    # IP addresses (v4)
    _re.compile(r'\b(\d{1,3}\.){2,3}\d{1,3}(/\d+)?\b'),
    # Timestamps / time patterns (07:02, 09:00 — основное, etc.)
    _re.compile(r'^\d{1,2}:\d{2}'),
    # Dates (2024-01-15, 15.01.2024, etc.)
    _re.compile(r'^\d{4}-\d{2}-\d{2}'),
    _re.compile(r'^\d{1,2}\.\d{1,2}\.\d{2,4}'),
    # Version strings (v2026.2.17, v2.3.1)
    _re.compile(r'^v?\d+\.\d+\.\d+'),
    # Money / numeric amounts with units (994 часа, 6.05M₽, 2,624,000 ₽, 8 спринтов)
    _re.compile(r'^[\d,.\s]+\s*(₽|руб|час|спринт|дн|нед|мес|год|min|hour|day|week|month|sprint|container)', _re.IGNORECASE),
    _re.compile(r'[\d,.\s]*[MKМКк]?₽'),
    _re.compile(r'^\d[\d,.\s]*/\s*[\d,.\s]+'),  # "994 часа / 2,624,000 ₽"
    # File paths and filenames (*.md, *.py, *.json, *.env, *.yaml, *.xlsx, *.docx, etc.)
    _re.compile(r'\.\w{1,5}$'),  # ends with .ext
    _re.compile(r'^[./~]'),  # starts with path separator
    _re.compile(r'/'),  # contains path separator (scripts/foo.py, memory/projects/*.md)
    _re.compile(r'^[A-Z_]+\.\w+$'),  # AGENTS.md, SOUL.md
    _re.compile(r'^[a-z_]\w*\.\w+$'),  # lowercase_file.ext (config.json, secrets.env)
    # Telegram bot handles
    _re.compile(r'^@\w+Bot$', _re.IGNORECASE),
    # Pure numbers (with optional minus)
    _re.compile(r'^-?\d[\d,.\s]*$'),
    # URLs and domains
    _re.compile(r'^https?://'),
    _re.compile(r'^[\w-]+\.[\w.-]+\.\w{2,}$'),  # domain.example.com
    _re.compile(r'\.com$|\.ru$|\.space$|\.dev$|\.io$|\.ai$'),  # common TLDs
    # Telegram-style numeric IDs (bare chat IDs not in KNOWN_CHATS)
    _re.compile(r'^-?\d{7,}$'),
    # Email addresses
    _re.compile(r'@[\w.-]+\.\w{2,}$'),
    # Glob patterns (memory/people/*.md)
    _re.compile(r'\*'),
    # Telegram channel references (telegram:364935958)
    _re.compile(r'^telegram:\d+$'),
    # Telegram chat ID mentions in text
    _re.compile(r'Telegram chat ID', _re.IGNORECASE),
    # Sub-agent IDs (Sub-agent 8cf55346)
    _re.compile(r'^Sub-agent\s+[0-9a-f]+$', _re.IGNORECASE),
    # Strings starting with "file_" (file_72, file_73...)
    _re.compile(r'^file_\d+$'),
    # "enabled: true" style config fragments
    _re.compile(r'^\w+:\s*(true|false|null|\d+)$', _re.IGNORECASE),
    # Code fragments: function calls, brackets, operators
    _re.compile(r'[(){}\[\]]'),
    _re.compile(r'^(chat_id|chat not found)'),
    # Memory/config path patterns without leading dot/slash
    _re.compile(r'^memory/'),
    _re.compile(r'^scripts/'),
    _re.compile(r'^drafts/'),
    _re.compile(r'^skills/'),
    # Hardware specs as standalone entities
    _re.compile(r'^\d+\s*[GT]B$', _re.IGNORECASE),
    # Python snake_case function/method names with verb prefixes
    _re.compile(r'^(get|set|put|post|delete|patch|create|update|remove|find|fetch|send|receive|handle|process|parse|build|make|init|start|stop|run|exec|load|save|dump|log|print|check|validate|verify|test|mock|assert|ensure|compute|calculate|convert|transform|format|render|display|show|hide|open|close|read|write|add|insert|append|push|pop|pull|merge|split|join|connect|disconnect|subscribe|unsubscribe|listen|emit|dispatch|trigger|fire|raise|throw|catch|retry|reset|clear|clean|flush|purge|sync|async|wait|sleep|poll|watch|observe|monitor|track|record|replay|restore|recover|backup|archive|compress|decompress|encrypt|decrypt|sign|verify|authorize|authenticate|register|login|logout|index|search|query|filter|sort|group|aggregate|reduce|map|scan|collect|stream|pipe|chain|wrap|unwrap|lock|unlock|acquire|release|allocate|free|manage|configure|setup|teardown|destroy|kill|abort|cancel|schedule|enqueue|dequeue|publish|consume|produce|forward|redirect|route|proxy|cache|invalidate|refresh|reload|restart|reboot|shutdown|suspend|resume|pause|continue|skip|ignore|suppress|mute|unmute|enable|disable|activate|deactivate|toggle|switch|swap|rotate|shift|move|copy|clone|duplicate|rename|replace|substitute|override|overwrite|extend|implement|inherit|compose|decorate|annotate|tag|label|mark|flag|pin|unpin|star|unstar|like|unlike|follow|unfollow|block|unblock|ban|unban|accept|reject|approve|deny|grant|revoke|assign|unassign|delegate|escalate|notify|alert|warn|inform|report|announce|broadcast|multicast|unicast)_[a-z][a-z_]*$'),
    # CLI command strings (openclaw ...)
    _re.compile(r'^openclaw\s+\w+', _re.IGNORECASE),
    # Stdout/log output patterns: "N entities, N relations", "STATUS_OK" style
    _re.compile(r'^\d+\s+entit', _re.IGNORECASE),
    _re.compile(r'^[A-Z_]+_OK$'),
    # Tomato varieties (Помидор ...)
    _re.compile(r'^Помидор\s+', _re.IGNORECASE),
    # ONLYOFFICE API method patterns (API Verb...)
    _re.compile(r'^API\s+(Create|Get|Set|Delete|Update|Remove|Insert|Add|Replace|Search|Find|Open|Close|Save|Load|Print|Export|Import|Merge|Split|Copy|Move|Rename|Format|Style|Bold|Italic|Underline|Strikeout|Numbering|Paragraph|Table|Chart|Image|Shape|Document|Worksheet|Slide|Presentation)\w*', _re.IGNORECASE),
]

# Additional exact-match noise set for entities that regex alone can't catch cleanly
_NOISE_ENTITY_EXACT: set[str] = {
    # Generic words that aren't real entities
    "Decision", "Technology", "Event", "Principle", "Idea",
    "LLM", "ASR", "NER", "QA", "HSM", "NC", "UAC", "OOM", "FSD",
    "ВЫВОД", "cron", "backup", "web", "db", "asr", "skills", "scripts",
    "Header", "Sidebar", "HomePage", "Browser", "Podcast", "Excel",
    "Markdown", "Sentiment", "S3", "DXF", "JSONL", "JWT", "SIEM",
    "WOPI", "desktop", "iOS", "nodes", "xlsx", "iOS Node",
    # Role titles / job positions (not persons, not orgs)
    "Backend Lead", "Backend API", "QA",
    "Backend Senior", "ML-инженер", "Frontend", "DevOps",
    "Backend", "Senior", "Junior", "Middle", "Team Lead", "Tech Lead",
    "PM", "RP", "Analyst", "Executor", "Ispolnitel",
    "AI Engineer", "Engineering Team Lead",
    # Telegram groups (not real organizations)
    "Остров Аркаша", "Оценки Аркаша", "Тестирование Аркадий",
    "Афигеваем от ассистентов", "Тестирование Аркадия",
    # Generic concepts too vague to be useful
    "здоровье", "раскрой", "sonnet", "opus", "arkasha",
    "Кэширование", "Напоминания", "Карточки контента",
    "Внешние API", "Внутренние API", "приватные данные",
    "обработчик ошибок", "самообучение STT", "scene detection",
    "image AI", "Cron jobs", "cron jobs", "system crontab",
    # Noise from specific files
    "Alena", "Ermil", "ermil", "alena",
    "discrete deaths and births",
    "kelexine",
    "Babysitting Tax", "Compression Tax", "Trade Hold",
    # Too-generic single words that aren't real entities
    "Auth", "API", "Data", "CLI", "SSO", "MFA", "STT", "VAD",
    "Email", "RBAC", "TOTP", "SDT", "XLSX", "AMQP",
    "Organization", "Identifier",
    # Section headers / meta-text from AGENTS.md etc
    "Session Start", "Task Flow", "Memory Structure", "Workspace",
    "Heartbeats", "Голосовые сообщения", "Граф знаний",
    "При каждом сообщении от Дениса", "Triggers → Rules",
    "Guest in someone's life",
    # Delivery modes / config values
    "delivery.mode=announce",
    # Stdout/log noise
    "HEARTBEAT_OK", "Cron статус", "Context usage",
    # Internal code classes/objects (not real technologies)
    "SessionContext", "SpeakerProfile", "Transcript", "FsNode", "fsApi", "fsStore",
    "numPr",
    # User flow steps / TickTick generic tasks (not real projects)
    "Корзина", "Оформление заказа", "Регистрация и авторизация",
    "Поиск товаров", "Переход между ключевыми разделами",
    "Проверка статуса заказа", "Поиск и каталог",
    "прогресс-индикатор в корзине",
    "Управление", "Документация", "Личный", "Работа", "Фитнес", "Заявка",
    # Log entries / status messages / TODOs
    "Показать результаты Денису",
    "Ожидается ответ от Дениса о приёме лекарств",
    "Попытки отправки через Telegram бот не удались из-за технических проблем",
    "Система автоматически доставит напоминания по установленным каналам",
    "Разобраться с блокировкой GitHub аккаунта arkasha-ai",
    "Объяснение задержек SyncVoice",
    "Почему перевод звучит не мгновенно",
    "Токен embeddings протух",
    "Честно", "Вывод", "Субагент", "память",
    "credentials", "cleanup", "indexer", "diarization",
    "media_prep", "nlp_adapter", "speaker_linking", "syncvoice",
    "memory_search", "index-memory", "index-sessions",
    # Generic standalone identifiers
    "main",
    # Voice names leaked as technology
    "ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural",
    # Too-generic project names
    "Systems", "Back-end", "Front-end",
    # Misc noise
    "Calibri", "Embla",
    "Адаптация", "Организм", "Логирование",
    "Продуктивное окружение", "Разговор о жизни",
    "Дефолтная модель сессии", "личка владельцу",
    "Шаблонная замена", "External content", "Documents",
    "Meet", "Teams", "Vue", "Svelte", "Vite", "WebSocket", "TypeScript",
    "aiopg", "Rust 2024",
}

def _is_noise_entity(name: str, etype: str) -> bool:
    """Returns True if the entity name matches a known noise pattern."""
    name_stripped = name.strip()
    if not name_stripped:
        return True
    # Exact-match noise set
    if name_stripped in _NOISE_ENTITY_EXACT:
        return True
    # Whitelist: known real entities that would be false-positived by regex
    _ENTITY_WHITELIST = {
        'Next.js', 'Vue.js', 'Node.js', 'Three.js', 'D3.js', 'Nuxt.js',
        'Express.js', 'Nest.js', 'Deno.js', 'Bun.js', 'Ember.js',
        'OAuth 2.0', 'OAuth2', 'TLS 1.3', 'HTTP/2', 'HTTP/3',
        'ГОСТ 34.10-2012', 'ГОСТ 34.11-2012',
        'SQLAlchemy 2.0.47', 'Python 3.13',
        'Qwen3-235B', 'Qwen3-Coder-480B',
        # Real technologies with snake_case-like names
        'docker-compose', 'class-variance-authority',
        'shadcn-vue', 'shadcn-svelte', 'lucide-vue-next',
        'html-to-docx', 'python-docx', 'python-jose',
        'pdfjs-dist', 'reka-ui', 'docx-preview',
        'pre-mortem-analyst',
    }
    if name_stripped in _ENTITY_WHITELIST:
        return False
    # Check regex patterns
    for pat in _NOISE_ENTITY_PATTERNS:
        if pat.search(name_stripped):
            return True
    # Very short entities (1-2 chars) are almost always garbage
    if len(name_stripped) <= 2:
        return True
    # Entities that are too long (>80 chars) are usually descriptions, not entities
    if len(name_stripped) > 80:
        return True
    # Nonsense phrases for Technology / Idea
    if etype in ("Technology", "Idea") and len(name_stripped.split()) >= 2:
        _non_tech_words = {'клики', 'нажатия', 'штуки', 'вещи', 'дела', 'итого', 'всего'}
        words = set(name_stripped.lower().split())
        if words & _non_tech_words:
            return True
    # Idea entities: filter out descriptive phrases that look like section headers
    # (contain ✅, 🎉, —, or are suspiciously long with colons)
    if etype == "Idea":
        if any(ch in name_stripped for ch in ('✅', '🎉', '❌', '⚠️', '📊', '📬', '🔒', '🤖')):
            return True
        # "Foo — Bar" style headers
        if ' — ' in name_stripped and len(name_stripped) > 30:
            return True
        # Log/status entries: sentences with verbs indicating status/action
        _idea_noise_words = {
            'ожидается', 'попытки', 'система', 'автоматически', 'доставит',
            'показать', 'разобраться', 'не удались', 'крах', 'объяснение',
        }
        lower = name_stripped.lower()
        if any(w in lower for w in _idea_noise_words):
            return True
        # Stdout-like output: "N entities, N relations" etc.
        if _re.match(r'^\d+\s+\w+,\s+\d+\s+\w+$', name_stripped):
            return True

    # Organizations: filter job titles and Telegram groups
    if etype == "Organization":
        _job_title_patterns = [
            _re.compile(r'^(Backend|Frontend|DevOps|QA|PM|RP|ML|AI|Data|Full.?Stack|Senior|Junior|Middle|Lead|Head|Chief|Director|Manager|Engineer|Developer|Architect|Designer|Analyst|Tester|Admin|Coordinator|Specialist|Consultant|Intern)\b', _re.IGNORECASE),
            _re.compile(r'(инженер|разработчик|архитектор|тестировщик|аналитик|менеджер|руководитель|директор|специалист|координатор|консультант|стажёр|стажер)$', _re.IGNORECASE),
        ]
        for pat in _job_title_patterns:
            if pat.search(name_stripped):
                return True
        # Telegram groups with Аркаш/Аркадий in name
        if _re.search(r'(Аркаш|Аркадий|ассистент)', name_stripped, _re.IGNORECASE):
            return True

    # Projects: filter user-flow steps, generic task names, tomato varieties
    if etype == "Project":
        _generic_project_names = {
            'корзина', 'оформление заказа', 'регистрация и авторизация',
            'поиск товаров', 'переход между ключевыми разделами',
            'проверка статуса заказа', 'управление', 'документация',
            'личный', 'работа', 'фитнес', 'заявка', 'поиск и каталог',
            'каталог и поиск', 'сортировка и фильтрация',
            'регистрация', 'авторизация', 'восстановление пароля',
            'выбор доставки', 'выбор оплаты',
        }
        if name_stripped.lower() in _generic_project_names:
            return True
        # Tomato varieties from TickTick
        if name_stripped.lower().startswith('помидор'):
            return True

    # Technologies: filter internal code objects (PascalCase single words that aren't known tech)
    if etype == "Technology":
        # snake_case names (likely function/variable names)
        if _re.match(r'^[a-z][a-z0-9]*(_[a-z0-9]+)+$', name_stripped):
            return True
        # camelCase names (likely JS/code objects)
        if _re.match(r'^[a-z][a-zA-Z0-9]+$', name_stripped) and any(c.isupper() for c in name_stripped):
            return True

    # Identifiers: filter git commit hashes and negative telegram IDs
    if etype == "Identifier":
        # Short hex hashes (git commits)
        if _re.match(r'^[0-9a-f]{6,8}$', name_stripped):
            return True
        # Telegram-style negative IDs not in KNOWN_CHATS
        if _re.match(r'^-\d{7,}$', name_stripped):
            return True
        # "main" or other generic identifiers
        if name_stripped in ('main', 'master', 'dev', 'staging', 'production'):
            return True

    return False

# ---------------------------------------------------------------------------
# Type specificity order (index 0 = most specific)
# ---------------------------------------------------------------------------

TYPE_SPECIFICITY: list[str] = [
    "Person",
    "Organization",
    "Project",
    "Technology",
    "Account",
    "Decision",
    "Event",
    "Principle",
    "Idea",
    "Identifier",
]

# ---------------------------------------------------------------------------
# Pydantic models for structured LLM extraction
# ---------------------------------------------------------------------------

class Relation(BaseModel):
    target: str
    rel_type: Literal["PARTICIPATED_IN", "MADE_DECISION", "RELATED_TO", "CAUSED", "MENTIONED"]

class Entity(BaseModel):
    name: str
    type: Literal[
        "Person", "Project", "Organization", "Technology", "Account",
        "Decision", "Event", "Principle", "Idea",
        "Identifier",
    ]
    relations: list[Relation] = []

class ExtractedEntities(BaseModel):
    entities: list[Entity]

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------

WORKSPACE = Path.home() / ".openclaw/workspace"
SECRETS_FILE = Path.home() / ".openclaw/secrets.env"
DB_PATH = WORKSPACE / "memory/graph/kuzu_db"
HASHES_PATH = WORKSPACE / "memory/graph/file_hashes.json"
SESSIONS_DIR = Path.home() / ".openclaw/agents/main/sessions"

MEMORY_DIRS = [
    WORKSPACE / "memory",
    WORKSPACE / "memory/people",
    WORKSPACE / "memory/projects",
    WORKSPACE / "memory/rules",
    WORKSPACE / "memory/tools",
    WORKSPACE / "memory/events",
    WORKSPACE / "memory/ideas",
    WORKSPACE / "memory/issues",
]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

VALID_NODE_TYPES = {
    "Person",
    "Project",
    "Organization",
    "Technology",
    "Account",
    "Decision",
    "Event",
    "Principle",
    "Idea",
    "Identifier",
}
VALID_REL_TYPES = {"PARTICIPATED_IN", "MADE_DECISION", "RELATED_TO", "CAUSED", "MENTIONED"}

# ---------------------------------------------------------------------------
# Load secrets
# ---------------------------------------------------------------------------

def load_secrets() -> dict:
    secrets = {}
    if not SECRETS_FILE.exists():
        return secrets
    for line in SECRETS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        secrets[key.strip()] = value.strip()
    return secrets

# ---------------------------------------------------------------------------
# Incremental rebuild: MD5 hashes
# ---------------------------------------------------------------------------

def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()

def load_hashes() -> dict:
    return json.loads(HASHES_PATH.read_text()) if HASHES_PATH.exists() else {}

def save_hashes(hashes: dict) -> None:
    HASHES_PATH.parent.mkdir(parents=True, exist_ok=True)
    HASHES_PATH.write_text(json.dumps(hashes, indent=2))

# ---------------------------------------------------------------------------
# Dynamic entity limit based on file size
# ---------------------------------------------------------------------------

def entity_limit(text_len: int) -> int:
    return min(10 + text_len // 2000, 20)

# ---------------------------------------------------------------------------
# KuzuDB helpers
# ---------------------------------------------------------------------------

def open_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = kuzu.Database(str(DB_PATH))
    conn = kuzu.Connection(db)
    return db, conn


def init_schema_v2(conn):
    """
    Pragmatic schema: single Entity node table with 'type' property.
    Rel tables per relationship type, all pointing Entity→Entity.
    """
    try:
        conn.execute(
            "CREATE NODE TABLE IF NOT EXISTS Entity "
            "(name STRING PRIMARY KEY, type STRING, source STRING)"
        )
    except Exception as e:
        print(f"[schema] Entity: {e}", file=sys.stderr)

    for rel_type in VALID_REL_TYPES:
        try:
            conn.execute(
                f"CREATE REL TABLE IF NOT EXISTS {rel_type} "
                f"(FROM Entity TO Entity, source STRING)"
            )
        except Exception as e:
            print(f"[schema] {rel_type}: {e}", file=sys.stderr)


def normalize_entity(name: str, etype: str) -> tuple[str, str] | None:
    """
    Apply name normalization and noise filtering.
    Returns (canonical_name, etype) or None if the entity should be discarded.
    """
    name = name.strip()
    if not name:
        return None

    # Telegram chat ID → canonical name + type
    if name in KNOWN_CHATS:
        return KNOWN_CHATS[name]

    # Числовые ID (chat IDs без маппинга) → Technology (технический идентификатор)
    if _re.match(r'^-?\d+$', name):
        return name, "Identifier"

    # Post-processing noise filter (UUIDs, IPs, timestamps, money, file paths, etc.)
    if _is_noise_entity(name, etype):
        return None

    canonical = KNOWN_ENTITIES.get(name, name)

    if etype == "Person" and (canonical in NOISE_PERSONS or name in NOISE_PERSONS):
        return None

    resolved_type = etype if etype in VALID_NODE_TYPES else "Idea"

    # Level 1.5: transliteration — Latin Person names → Cyrillic canonical
    if resolved_type == "Person":
        cyr_name = transliterate_name_to_cyrillic(canonical)
        if cyr_name:
            canonical = cyr_name

    # Level 2: pymorphy3 — приводим к именительному падежу (Person и Organization, только кириллица)
    if resolved_type in ("Person", "Organization"):
        if any('\u0400' <= c <= '\u04ff' for c in canonical):
            canonical = normalize_nominative(canonical)

    # Level 3: детекция никнеймов — переклассифицировать Person → Account
    if resolved_type == "Person" and is_nickname(canonical):
        resolved_type = "Account"

    return canonical, resolved_type


def upsert_entity(conn, name: str, etype: str, source: str = ""):
    """
    Insert entity if not exists. If exists — update type only if new type is more specific.
    Deduplication: no duplicates by name.
    """
    result = normalize_entity(name, etype)
    if result is None:
        return

    name, etype = result
    name_esc = name.replace("'", "\\'")
    source_esc = source.replace("'", "\\'")

    # Check if entity already exists
    try:
        res = conn.execute(f"MATCH (e:Entity {{name: '{name_esc}'}}) RETURN e.type, e.source")
        df = res.get_as_df()
        if not df.empty:
            # Entity exists — update type only if new type is more specific
            current_type = df["e.type"].iloc[0]
            current_spec = TYPE_SPECIFICITY.index(current_type) if current_type in TYPE_SPECIFICITY else len(TYPE_SPECIFICITY)
            new_spec = TYPE_SPECIFICITY.index(etype) if etype in TYPE_SPECIFICITY else len(TYPE_SPECIFICITY)
            if new_spec < current_spec:
                conn.execute(f"MATCH (e:Entity {{name: '{name_esc}'}}) SET e.type = '{etype}'")
            # Update source if was empty
            current_source = df["e.source"].iloc[0] or ""
            if not current_source and source_esc:
                conn.execute(f"MATCH (e:Entity {{name: '{name_esc}'}}) SET e.source = '{source_esc}'")
            return
    except Exception:
        pass

    # Entity doesn't exist — create it
    try:
        conn.execute(
            f"CREATE (e:Entity {{name: '{name_esc}', type: '{etype}', source: '{source_esc}'}})"
        )
    except Exception:
        # Last resort: try MERGE (handles race conditions)
        try:
            conn.execute(
                f"MERGE (e:Entity {{name: '{name_esc}'}}) "
                f"ON CREATE SET e.type = '{etype}', e.source = '{source_esc}'"
            )
        except Exception:
            pass


def upsert_relation(conn, src: str, dst: str, rel_type: str, source: str = ""):
    if rel_type not in VALID_REL_TYPES:
        rel_type = "RELATED_TO"
    # Normalize names through same pipeline as entities
    src_raw = KNOWN_ENTITIES.get(src.strip(), src.strip())
    dst_raw = KNOWN_ENTITIES.get(dst.strip(), dst.strip())
    # Apply transliteration for relation endpoints too
    src_cyr = transliterate_name_to_cyrillic(src_raw)
    dst_cyr = transliterate_name_to_cyrillic(dst_raw)
    src = (src_cyr or src_raw).replace("'", "\\'")
    dst = (dst_cyr or dst_raw).replace("'", "\\'")
    source_esc = source.replace("'", "\\'")
    try:
        # Дедупликация: не создавать ребро если уже существует
        res = conn.execute(
            f"MATCH (a:Entity {{name: '{src}'}})-[r:{rel_type}]->(b:Entity {{name: '{dst}'}}) "
            f"RETURN count(r)"
        )
        if res.get_next()[0] > 0:
            return
        conn.execute(
            f"MATCH (a:Entity {{name: '{src}'}}), (b:Entity {{name: '{dst}'}}) "
            f"CREATE (a)-[:{rel_type} {{source: '{source_esc}'}}]->(b)"
        )
    except Exception as e:
        print(f"[rel] {src} -{rel_type}-> {dst}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Instructor-based extraction
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT_TEMPLATE = """Act like an expert information-extraction analyst specializing in entity recognition and relationship mapping for messy technical + Russian-language text.

Your goal is to extract the TOP {limit} most important entities from the provided text and map the strongest relationships between them. You must NOT summarize the text; you only output structured extraction.

Critical fixes (must enforce):
- Roles/titles without a proper human name are NEVER Person and must be skipped.
  Examples to SKIP: Backend Senior, Backend Lead, DevOps, Frontend, QA, RP, PM, Team Lead, Analyst, Executor, Ispolnitel.
- A Person requires a real human name (e.g., "Timofey Shutov", "Ksenia Shutova") -- a role alone never qualifies.
- If the text contains a role next to a real name (e.g., "QA -- Ksenia Shutova"), extract ONLY the Person; the role is skipped.

Task (follow in order):
1) Read the full text and identify all candidate named entities.
2) Classify each candidate into exactly one ENTITY TYPE using the rules below.
3) Filter to the TOP {limit} entities by importance:
 - Centrality: appears often, or many other entities connect to it
 - Specificity: proper names > generic terms
 - Decision/event linkage: entities tied to Decisions or Events rank higher
4) Extract directed RELATIONS between the selected entities (only strong, defensible links).
5) Run a self-check: remove misclassified items (roles, files, folders, domains, IPs).

ENTITY TYPES (strict):
- Person: real human with a full proper name. NOT roles. NOT AI models. NOT usernames.
- Organization: company/team/community.
- Project: specific named product/system. NOT scripts. NOT config files.
- Technology: language/framework/tool/protocol/AI model/script/algorithm.
- Account: ONLY human username, email, or @handle of a real person. NOT domains. NOT filenames. NOT config files.
- Identifier: technical ID — Telegram chat ID (-4958457563), UUID, numeric ID. NOT a name, NOT a username.
- Decision: concrete decision made (quoted or clearly stated).
- Principle: rule/agreement/value phrased as a norm.
- Idea: hypothesis/plan/intent not yet decided.
- Event: something that happened (release, incident, operation, bug found).

Hard exclusions — NEVER extract these as entities of ANY type:
- UUIDs (e.g. 5eaf605e-6e95-4440-a93a-bc2f3c2a4df0) — SKIP entirely
- Hex hashes (e.g. 695bc6dd7d799105bb21e874) — SKIP entirely
- IP addresses (e.g. 80.87.197.0, 192.168.1.1) — SKIP entirely
- Timestamps / time references (e.g. "07:02 крах", "09:00 — основное", "09:20 — повторное") — SKIP entirely
- Money amounts / numeric metrics (e.g. "994 часа / 2,624,000 ₽", "6.05M₽", "8 спринтов") — SKIP entirely
- File paths and filenames (e.g. AUDIT_zavka4_problems.md, .integrity.baseline, secrets.env) — SKIP entirely
- Telegram bot handles (e.g. @LisaToyBot) — SKIP entirely
- Pure numbers or numeric IDs — SKIP entirely
- URLs and domains — SKIP entirely
- Config file names like AGENTS.md, SOUL.md, USER.md — SKIP entirely
- Nonsense phrases that are not real technology names (e.g. "CLI клики") — SKIP entirely

Type-specific rules:
- Filenames (*.md, *.py, *.json, *.env), folder paths, domains, IPs: NEVER Account. SKIP them.
- Telegram chat IDs (e.g. -4958457563) → Identifier (NOT Account, NOT Technology, NOT skip).
- WRONG: "Backend lead" (skip), "Opus/Claude/Qwen" (Technology), "qdrant_indexer.py" (skip), "clwd.jakeberrimor.com" (skip), "secrets.env" (skip).
- Idea must be a genuine hypothesis, plan, or concept — NOT a UUID, NOT a number, NOT a timestamp, NOT a file path.
- Technology must be a real technology, framework, language, tool, or protocol — NOT a config filename, NOT a random phrase.

RELATIONS -- STRICT rules (follow precisely):
- Person PARTICIPATED_IN Event — person actively took part in an event
- Person MADE_DECISION Decision — person explicitly made a decision
- Project RELATED_TO Organization — project belongs to or is associated with org
- Technology RELATED_TO Project — tech is used in a project
- Event CAUSED Event — one event directly caused another
- MENTIONED — USE SPARINGLY! Only when an entity is passively name-dropped in text but NOT an active participant. 
  DO NOT create MENTIONED if a stronger relation type applies.
  DO NOT create bidirectional MENTIONED (A MENTIONED B and B MENTIONED A).
  Maximum 2-3 MENTIONED relations per file. Prefer RELATED_TO or PARTICIPATED_IN instead.
  If unsure between MENTIONED and RELATED_TO, choose RELATED_TO.

Note: Text may be in Russian. Entity names should be extracted as-is (keep Russian names in Russian).
CRITICAL: All entity names must be in NOMINATIVE case (именительный падеж / именительный падеж).
Examples: "Тимофея Шутова" → "Тимофей Шутов", "Ксении Шутовой" → "Ксения Шутова", "Саши" → "Саша".

Take a deep breath and work on this problem step-by-step.

Text:
"""



DEBUG_MODE = False
DEBUG_LOG = Path("/tmp/kg-debug.log")


# ---------------------------------------------------------------------------
# Graph context for LLM prompt (deduplication helper)
# ---------------------------------------------------------------------------

def get_graph_context(conn, text: str) -> str:
    """Ищет в графе сущности чьи имена встречаются в тексте. Возвращает строку для промпта."""
    parts = []

    # Известные чаты — всегда добавляем если chat ID встречается в тексте
    chat_hints = []
    for chat_id, (name, etype) in KNOWN_CHATS.items():
        if chat_id in text:
            chat_hints.append(f"  {chat_id} = [{etype}] {name}")
    if chat_hints:
        parts.append("Known Telegram chats (use name, not ID):\n" + "\n".join(chat_hints))

    # Уже существующие ноды в графе
    try:
        res = conn.execute("MATCH (e:Entity) RETURN e.name, e.type ORDER BY e.type, e.name")
        existing = []
        while res.has_next():
            row = res.get_next()
            name, etype = row[0], row[1]
            if len(name) >= 3 and name.lower() in text.lower():
                existing.append(f"  [{etype}] {name}")
        if existing:
            parts.append("Already in graph (USE THESE EXACT NAMES, do not create variants):\n" + "\n".join(existing[:30]))
    except Exception:
        pass

    return "\n\n".join(parts) + "\n\n" if parts else ""


def call_litellm(text: str, secrets: dict, limit: int = 10, source: str = "", graph_context: str = "") -> list:
    """Extract entities from text using instructor + pydantic. Returns list of Entity objects."""
    import instructor
    from openai import OpenAI

    base_url = secrets.get("LITELLM_BASE_URL") or secrets.get("LITELLM_URL", "https://litellm.jakeberrimor.com")
    api_key = secrets.get("LITELLM_API_KEY", "")

    client = instructor.from_openai(
        OpenAI(base_url=base_url.rstrip("/") + "/v1", api_key=api_key),
        mode=instructor.Mode.JSON,
    )

    text_chunk = text[:10000]
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(limit=limit) + graph_context + text_chunk

    try:
        result = client.chat.completions.create(
            model="GLM-4.7",
            response_model=ExtractedEntities,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=65536,
        )
        if DEBUG_MODE:
            with open(DEBUG_LOG, "a") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"FILE: {source}\n")
                f.write(f"TEXT (first 300 chars): {text_chunk[:300]}\n")
                f.write(f"ENTITIES:\n")
                for ent in result.entities:
                    f.write(f"  [{ent.type}] {ent.name}\n")
                    for rel in ent.relations:
                        f.write(f"    --[{rel.rel_type}]--> {rel.target}\n")
        return result.entities
    except Exception as e:
        print(f"[llm] Extraction failed: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Build command (incremental by default, --full for complete rebuild)
# ---------------------------------------------------------------------------

def cmd_build(full: bool = False):
    secrets = load_secrets()
    db, conn = open_db()
    init_schema_v2(conn)

    # Load existing file hashes
    hashes = {} if full else load_hashes()
    if full:
        print("[build] Full rebuild — ignoring cached hashes", file=sys.stderr)
        # Clear existing data for a truly clean rebuild
        try:
            conn.execute("MATCH (e:Entity) DETACH DELETE e")
            print("[build] Cleared all existing entities and relations", file=sys.stderr)
        except Exception as e:
            print(f"[build] Warning: could not clear DB: {e}", file=sys.stderr)

    # Collect all .md files
    md_files = []
    for d in MEMORY_DIRS:
        if d.exists() and d.is_dir():
            md_files.extend(d.glob("*.md"))
    for f in WORKSPACE.glob("*.md"):
        md_files.append(f)

    # Deduplicate and sort
    md_files = list({str(f): f for f in md_files}.values())
    md_files.sort()

    # Blacklist: skip test-validation files (contain fake test users like "Иван Иванов")
    FILE_BLACKLIST_PATTERNS = ["test-validation-", "test-validation_", "logera-design-notes"]
    before_filter = len(md_files)
    md_files = [f for f in md_files if not any(pat in f.name for pat in FILE_BLACKLIST_PATTERNS)]
    blacklisted = before_filter - len(md_files)
    if blacklisted:
        print(f"[build] Blacklisted {blacklisted} test-validation files", file=sys.stderr)

    # Filter to only changed files (incremental)
    changed_files = []
    skipped = 0
    for f in md_files:
        try:
            h = file_hash(f)
        except Exception:
            h = ""
        if not full and hashes.get(str(f)) == h:
            skipped += 1
        else:
            changed_files.append((f, h))

    print(f"[build] Found {len(md_files)} files: {len(changed_files)} changed, {skipped} unchanged (skipped)", file=sys.stderr)

    if not changed_files:
        print("[build] Nothing to do — all files up to date. Use --full to rebuild everything.", file=sys.stderr)
        conn.close()
        return

    total_entities = 0
    total_relations = 0

    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Собираем graph_context ДО запуска потоков — KuzuDB не потокобезопасен для чтения
    # одновременно с записью, поэтому контекст собирается заранее как строка
    file_contexts: dict[str, str] = {}
    for f, h in changed_files:
        try:
            text_preview = f.read_text(errors="replace")[:10000]
            file_contexts[str(f)] = get_graph_context(conn, text_preview)
        except Exception:
            file_contexts[str(f)] = ""

    def process_file(args):
        i, fpath, fhash = args
        stat = fpath.stat()
        if stat.st_size > MAX_FILE_SIZE:
            return i, fpath, fhash, None, "too large"
        text = fpath.read_text(errors="replace")
        if len(text.strip()) < 50:
            return i, fpath, fhash, None, "too short"
        rel_name = str(fpath.relative_to(WORKSPACE))
        limit = entity_limit(len(text))
        graph_context = file_contexts.get(str(fpath), "")
        entities = call_litellm(text, secrets, limit=limit, source=rel_name, graph_context=graph_context)
        return i, fpath, fhash, entities, rel_name

    WORKERS = 5
    results = []

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(process_file, (i, f, h)): i
            for i, (f, h) in enumerate(changed_files, 1)
        }
        for future in as_completed(futures):
            i, fpath, fhash, entities, rel_name = future.result()
            results.append((i, fpath, fhash, entities, rel_name))
            status = f"→ {len(entities)} entities" if entities else f"→ skip ({rel_name})"
            print(f"[build] [{i}/{len(changed_files)}] {fpath.name}: {status}", file=sys.stderr)

    # Write to graph sequentially (sorted by original order)
    results.sort(key=lambda x: x[0])
    new_hashes = dict(hashes)  # start from existing hashes

    for i, fpath, fhash, entities, rel_name in results:
        # Always update hash (even if skipped by size/length — avoids re-checking next time)
        if fhash:
            new_hashes[str(fpath)] = fhash

        if not entities or not isinstance(rel_name, str):
            continue
        for ent in entities:
            if not ent.name.strip():
                continue
            upsert_entity(conn, ent.name, ent.type, rel_name)
            total_entities += 1
            for rel in ent.relations:
                if not rel.target.strip():
                    continue
                upsert_entity(conn, rel.target, "Idea", rel_name)
                upsert_relation(conn, ent.name, rel.target, rel.rel_type, rel_name)
                total_relations += 1

    save_hashes(new_hashes)
    print(f"\n[build] Done. Entities written: {total_entities}, relations: {total_relations}", file=sys.stderr)
    print(f"[build] Hashes saved: {len(new_hashes)} files tracked ({HASHES_PATH})", file=sys.stderr)
    conn.close()


# ---------------------------------------------------------------------------
# Build-sessions command: index user messages from JSONL session files
# ---------------------------------------------------------------------------

def cmd_build_sessions():
    """
    Read JSONL session files, extract user messages (type=message, role=user),
    and index entities for messages longer than 100 characters.
    """
    secrets = load_secrets()
    db, conn = open_db()
    init_schema_v2(conn)

    if not SESSIONS_DIR.exists():
        print(f"[build-sessions] Sessions directory not found: {SESSIONS_DIR}", file=sys.stderr)
        conn.close()
        return

    jsonl_files = sorted(SESSIONS_DIR.glob("*.jsonl"))
    print(f"[build-sessions] Found {len(jsonl_files)} JSONL session files", file=sys.stderr)

    # Collect qualifying messages
    messages = []
    for jf in jsonl_files:
        try:
            for line in jf.read_text(errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Filter: type=message, role=user
                if obj.get("type") != "message" and obj.get("role") != "user":
                    # Try alternate structure
                    if not (obj.get("role") == "user"):
                        continue
                content = obj.get("content", "")
                if isinstance(content, list):
                    # Handle content blocks (e.g. [{type: text, text: "..."}])
                    content = " ".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in content
                    )
                if not isinstance(content, str):
                    content = str(content)
                if len(content) > 100:
                    source = f"sessions/{jf.name}"
                    messages.append((content, source))
        except Exception as e:
            print(f"[build-sessions] Error reading {jf.name}: {e}", file=sys.stderr)

    print(f"[build-sessions] Qualifying messages (>100 chars, role=user): {len(messages)}", file=sys.stderr)

    if not messages:
        print("[build-sessions] No messages to process.", file=sys.stderr)
        conn.close()
        return

    total_entities = 0
    total_relations = 0

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def process_message(args):
        i, text, source = args
        limit = entity_limit(len(text))
        entities = call_litellm(text, secrets, limit=limit, source=rel_name)
        return i, text, source, entities

    WORKERS = 5
    results = []

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(process_message, (i, text, source)): i
            for i, (text, source) in enumerate(messages, 1)
        }
        for future in as_completed(futures):
            i, text, source, entities = future.result()
            results.append((i, text, source, entities))
            preview = text[:60].replace("\n", " ")
            status = f"→ {len(entities)} entities" if entities else "→ skip (no entities)"
            print(f"[build-sessions] [{i}/{len(messages)}] \"{preview}...\": {status}", file=sys.stderr)

    results.sort(key=lambda x: x[0])

    for i, text, source, entities in results:
        if not entities:
            continue
        for ent in entities:
            if not ent.name.strip():
                continue
            upsert_entity(conn, ent.name, ent.type, source)
            total_entities += 1
            for rel in ent.relations:
                if not rel.target.strip():
                    continue
                upsert_entity(conn, rel.target, "Idea", source)
                upsert_relation(conn, ent.name, rel.target, rel.rel_type, source)
                total_relations += 1

    print(f"\n[build-sessions] Done. Entities written: {total_entities}, relations: {total_relations}", file=sys.stderr)
    conn.close()


# ---------------------------------------------------------------------------
# Query command
# ---------------------------------------------------------------------------

def cmd_query(search_term: str):
    db, conn = open_db()
    init_schema_v2(conn)

    term_esc = search_term.strip().replace("'", "\\'")

    print(f"\n=== Query: '{search_term}' ===\n")

    # 1. Direct entity match
    try:
        result = conn.execute(
            f"MATCH (e:Entity) WHERE e.name CONTAINS '{term_esc}' RETURN e.name, e.type, e.source"
        )
        rows = result.get_as_df()
        if not rows.empty:
            print("📌 Entities matching:")
            for _, row in rows.iterrows():
                print(f"  [{row['e.type']}] {row['e.name']}  (from: {row['e.source']})")
        else:
            print("No direct entity matches found.")
    except Exception as e:
        print(f"Entity query error: {e}")

    # 2. Relations (outgoing + incoming) per rel type
    outgoing_rows = []
    incoming_rows = []
    for rel_type in VALID_REL_TYPES:
        try:
            result = conn.execute(
                f"MATCH (a:Entity)-[:{rel_type}]->(b:Entity) "
                f"WHERE a.name CONTAINS '{term_esc}' "
                f"RETURN a.name, b.name, b.type LIMIT 20"
            )
            df = result.get_as_df()
            if not df.empty:
                for _, row in df.iterrows():
                    outgoing_rows.append((row["a.name"], rel_type, row["b.type"], row["b.name"]))
        except Exception:
            pass

        try:
            result = conn.execute(
                f"MATCH (a:Entity)-[:{rel_type}]->(b:Entity) "
                f"WHERE b.name CONTAINS '{term_esc}' "
                f"RETURN a.name, a.type, b.name LIMIT 20"
            )
            df = result.get_as_df()
            if not df.empty:
                for _, row in df.iterrows():
                    incoming_rows.append((row["a.name"], row["a.type"], rel_type, row["b.name"]))
        except Exception:
            pass

    if outgoing_rows:
        print("\n🔗 Outgoing relations:")
        for src, rel, btype, dst in outgoing_rows:
            print(f"  {src} --[{rel}]--> [{btype}] {dst}")

    if incoming_rows:
        print("\n⬅️  Incoming relations:")
        for src, atype, rel, dst in incoming_rows:
            print(f"  [{atype}] {src} --[{rel}]--> {dst}")

    conn.close()


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------

def cmd_status():
    db, conn = open_db()
    init_schema_v2(conn)

    print("=== Knowledge Graph Status ===\n")
    print(f"DB path: {DB_PATH}")

    # Hashes info
    hashes = load_hashes()
    print(f"Tracked files (hashes): {len(hashes)}  ({HASHES_PATH})")

    # Count entities
    try:
        result = conn.execute("MATCH (e:Entity) RETURN e.type, count(*) AS cnt ORDER BY cnt DESC")
        df = result.get_as_df()
        if df.empty:
            print("\nEntities: 0 (graph is empty — run `build` first)")
        else:
            total = df["cnt"].sum()
            print(f"\nEntities total: {total}")
            print("  By type:")
            for _, row in df.iterrows():
                print(f"    {row['e.type']:<15} {row['cnt']}")
    except Exception as e:
        print(f"Entity count error: {e}")

    # Count relations per type
    rel_totals = 0
    print("\nRelations:")
    for rel_type in VALID_REL_TYPES:
        try:
            result = conn.execute(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS cnt")
            df = result.get_as_df()
            cnt = int(df["cnt"].iloc[0]) if not df.empty else 0
            print(f"  {rel_type:<20} {cnt}")
            rel_totals += cnt
        except Exception as e:
            print(f"  {rel_type:<20} error: {e}")

    print(f"\nRelations total: {rel_totals}")

    # DB size on disk
    db_root = DB_PATH.parent
    try:
        db_size = sum(f.stat().st_size for f in db_root.rglob("*") if f.is_file())
    except Exception:
        db_size = 0
    print(f"\nDB size on disk: {db_size / 1024:.1f} KB ({db_root})")

    conn.close()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "build":
        global DEBUG_MODE
        full = "--full" in sys.argv
        if "--debug" in sys.argv:
            DEBUG_MODE = True
            DEBUG_LOG.write_text("")
            print(f"[debug] Debug mode ON → {DEBUG_LOG}", file=sys.stderr)
        cmd_build(full=full)
    elif cmd == "build-sessions":
        cmd_build_sessions()
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Usage: python3 knowledge_graph.py query <search_term>")
            sys.exit(1)
        cmd_query(sys.argv[2])
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Unknown command: {cmd}")
        print("Available: build [--full] | build-sessions | query <term> | status")
        sys.exit(1)


if __name__ == "__main__":
    main()
