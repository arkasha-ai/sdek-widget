# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Browser 🌐

**I have my own browser!**

- **Profile:** `openclaw` (NOT `chrome`)
- **Status:** Always available, don't need Chrome extension relay
- **Already logged in:** GitHub account (arkasha-ai)
- **Use for:** GitHub operations, web navigation, any browser tasks

**When to use:**
- Default for all browser operations
- Already authenticated on GitHub
- Can create releases, manage repos, etc.

**DON'T use:** `profile="chrome"` unless Denis explicitly asks to attach his Chrome tab

---

## Moltbook 🦞

- **Profile:** https://moltbook.com/u/Arkasha
- **API Key:** Stored in `~/.config/moltbook/credentials.json`
- **Status:** Pending claim (waiting for Denis to verify via Twitter)
- **Verification code:** wave-3GLH

---

## YouTube Transcription 📹

- **Script:** `~/.openclaw/workspace/scripts/youtube_transcript.py`
- **yt-dlp location:** `~/.local/bin/yt-dlp`
- **Usage:** `python3 youtube_transcript.py <youtube_url> [lang]`
- **Default language:** `ru` (falls back to `en` if unavailable)
- **How it works:** Downloads auto-generated subtitles from YouTube and converts to clean text
- **Supported formats:** Any YouTube URL format (watch, shorts, youtu.be, embed)

---

## Whisper (распознавание голосовых) 🎤

**Конфиг:** `~/.openclaw/litellm.env`
```bash
LITELLM_BASE_URL=https://litellm.jakeberrimor.com
LITELLM_API_KEY=sk-gDi9OUkixq5-0Ve4ddWRlA
WHISPER_MODEL=openai/whisper-large-v3
```

**Как работает:**
- Автоматически распознаёт голосовые сообщения из Telegram
- Использует LiteLLM инстанс на https://litellm.jakeberrimor.com
- Модель: Whisper Large V3 (самая точная)

**История настройки:**
- Настроили 2026-02-05 ~00:35
- Проблема: не было libsndfile в Docker контейнере
- Решение: добавили в Dockerfile `apk add libsndfile libsndfile-dev`, пересобрали
- Результат: работает!

**Как использовать (вручную через curl):**
```bash
source ~/.openclaw/litellm.env && curl -X POST "${LITELLM_BASE_URL}/v1/audio/transcriptions" \
  -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  -F "file=@/path/to/audio.ogg" \
  -F "model=${WHISPER_MODEL}"
```

**Статус:** Автоматическая транскрипция в OpenClaw пока не настроена — нужно вызывать API вручную

---

## Qdrant Semantic Search 🔍

**Скрипт:** `~/.openclaw/workspace/scripts/qdrant_indexer.py`

**Основные команды:**
```bash
# Индексировать почту (himalaya → Qdrant)
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py index-emails

# Семантический поиск
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py search "запрос"

# Индексировать файлы памяти
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py index-memory
```

**Что индексируется:**
- **Email:** dparmeev, spam, contact, contact-lumines (первые 50 писем каждого)
- **Memory:** MEMORY.md + memory/*.md

**Примеры использования:**
```bash
# Найти письма про конкретную тему
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py search "ONLYOFFICE интеграция"

# Найти в памяти информацию о проекте
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py search "Logera deployment"

# Результат: JSON с score, metadata (subject/from/date), текстом
```

**Технические детали:**
- Embedding model: Qwen3-Embedding-0.6B (через LiteLLM)
- Collection: `arkasha`
- Credentials: из `secrets.env` (QDRANT_URL, QDRANT_API_KEY, LITELLM_API_KEY)
- ID генерация: MD5 hash (account:email_id или file_path)

**Когда использовать:**
- Поиск старых писем по смыслу, не по ключевым словам
- Вспомнить контекст из прошлых разговоров/памяти
- Найти связанную информацию из разных источников (email + memory)

---

## TickTick Tasks 🎯

**Статус:** Работает через Open API v1
**Токен:** `~/.openclaw/workspace/.ticktick_token.json`
**Credentials:** `~/.openclaw/secrets.env` (TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET)

**Основные команды:**

```bash
# Список проектов (с ID)
ticktick projects

# Все задачи из всех проектов
ticktick tasks

# Задачи из конкретного проекта
ticktick tasks 695bc6dd7d799105bb21e874

# Создать задачу (в inbox)
ticktick add "Купить молоко"

# Создать задачу в проекте с приоритетом и дедлайном
ticktick add "Важная задача" --project 695bc6dd7d799105bb21e874 --due 2026-02-10 --priority 3

# Завершить задачу (нужны project_id и task_id)
ticktick complete 695bc6dd7d799105bb21e874 69857e9e8f08079613ca1953
```

**Приоритеты:**
- 0 = нет
- 1 = низкий
- 3 = средний
- 5 = высокий

**ID твоих проектов:**
- `695bc6dd7d799105bb21e874` — 🏠 Личный
- `695bc7447dd51105bb21e8ee` — 💼 Работа
- `695bc6dd7d7dd105bb21e875` — 🏃 Фитнес
- `695bfa4ba268d125f73668e9` — Ясень Финанс
- `695bfac650aa9125f73669d5` — FinInvest
- `695bfb43ab63d125f7366aa6` — Front-end
- `695bfb653ef81125f7366ad5` — Управление
- `695bfb7263635125f7366b1d` — Back-end

**Примеры использования:**
```bash
# Посмотреть что в Работе
ticktick tasks 695bc7447dd51105bb21e8ee | jq -r '.[] | "[\(if .status == 0 then "TODO" else "DONE" end)] \(.title)"'

# Добавить задачу в Личный проект
ticktick add "Позвонить врачу" --project 695bc6dd7d799105bb21e874 --priority 3

# Добавить с дедлайном и описанием
ticktick add "Сдать отчет" --project 695bc7447dd51105bb21e8ee --due 2026-02-15 --priority 5 --content "Подробное описание задачи здесь"
```

**Обновление (2026-02-06):**
- ✅ Теперь поддерживает `--content` для создания задач с описанием одним запросом!
- Open API v1 (`/open/v1/task`) **поддерживает** content при создании (изначально был миф что не поддерживает)

**Известные ограничения:**
- Delete endpoint не работает (404) — используй complete вместо удаления
- Для complete нужно знать и project_id и task_id

---

## IMAP IDLE Listener v2 📧⚡

**Статус:** ✅ Working! Event-driven email notifications (вместо polling)

**Что это:** Python service использующий `imapclient` библиотеку для IDLE соединений со всеми 4 IMAP аккаунтами. Триггерит OpenClaw webhook мгновенно когда приходит новое письмо.

**Accounts monitored:**
- dparmeev@luminesfox.com
- spam@jakeberrimor.com
- contact@jakeberrimor.com
- contact@luminesfox.com

**Как работает:**
1. Listener держит IDLE connections к mail.hosting.reg.ru (используя `IMAPClient`)
2. Новое письмо → instant webhook: `POST http://localhost:18789/hooks/wake`
3. OpenClaw просыпается (`mode: "now"`) → обрабатывает email
4. UID tracking = только НОВЫЕ письма триггерят webhook (no spam)

**Преимущества vs polling:**
- ⚡ Instant notification (<1 sec вместо до 1 часа)
- 💰 Zero tokens while no emails (вместо 16 checks/день)
- 🎯 Только реальные события триггерят wake
- ✅ Stable! (imapclient > raw imaplib)

**Script:** `~/.openclaw/workspace/scripts/imap_idle_listener_v2.py`

**Dependencies:**
```bash
pip3 install imapclient --user --break-system-packages
```

**Run manually:**
```bash
python3 -u ~/.openclaw/workspace/scripts/imap_idle_listener_v2.py
```

**Run in background (PTY mode):**
```bash
cd ~/.openclaw/workspace && python3 -u scripts/imap_idle_listener_v2.py
# В отдельной OpenClaw exec session с pty=true, background=true
```

**Systemd service** (TODO - update with v2 script):
```bash
sudo cp /tmp/imap-idle-listener.service /etc/systemd/system/
# Edit ExecStart path to use imap_idle_listener_v2.py
sudo systemctl daemon-reload
sudo systemctl enable imap-idle-listener
sudo systemctl start imap-idle-listener
```

**Webhook config:** В `~/.openclaw/openclaw.json`:
```json
{
  "hooks": {
    "enabled": true,
    "token": "f016901f219067c9d30dea113c41576057c71e4d068d6363",
    "path": "/hooks"
  }
}
```

**Tech details:**
- Library: `imapclient` (proper IDLE protocol implementation)
- UID tracking: `last_seen_uid` per account
- Keep-alive: IDLE refresh every 15 min
- Timeout: `idle_check(timeout=300)` = 5 min
- Reconnect: exponential backoff (5s → 300s max)

**Debugging:**
- Check if running: `ps aux | grep imap_idle_listener_v2`
- Test webhook: `curl -X POST http://127.0.0.1:18789/hooks/wake -H "Authorization: Bearer TOKEN" -d '{"text":"test","mode":"now"}'`

**Inspired by:** @claude-event-listeners на Moltbook - critique про event-driven architecture vs polling. Implemented 2026-02-06!

---

## Arkady's Personal Email 📧

**My personal email for registrations and accounts:**
- Email: `a.parmeev@jakeberrimor.com`
- Password: stored in `~/.openclaw/secrets.env` (ARKADY_PASSWORD)
- IMAP/SMTP: mail.hosting.reg.ru (same as other jakeberrimor.com accounts)
- Himalaya account: `arkady`

**Use for:**
- Registrations on services (APIs, GitHub, platforms)
- Receiving alerts/notifications
- Communication with other agents
- Any account creation where I need my own identity

**Access:**
```bash
HIMALAYA_ACCOUNT=arkady himalaya envelope list
HIMALAYA_ACCOUNT=arkady himalaya message read <id>
```

---

## GitHub Account 🐙

**Profile:** https://github.com/arkasha-ai

**Credentials:**
- Username: `arkasha-ai`
- Email: `a.parmeev@jakeberrimor.com`
- Password: stored in `~/.openclaw/secrets.env` (ARKADY_PASSWORD)

**SSH Key:**
- Location: `~/.ssh/github_arkasha` (private), `~/.ssh/github_arkasha.pub` (public)
- Added to GitHub: "OpenClaw workspace (clwd.jakeberrimor.com)"
- Fingerprint: `SHA256:cyIqOTSowUdPwYYo4wtUUwLN9ZBnnhGOAm5Gt6tsHOg`

**Git Config:**
```bash
git config --global user.name "Arkasha"
git config --global user.email "a.parmeev@jakeberrimor.com"
```

**SSH Config:**
```bash
# Use: git clone git@github.com-arkasha:arkasha-ai/repo.git
Host github.com-arkasha
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_arkasha
    IdentitiesOnly yes
```

**2FA Setup (TOTP via oathtool):**
```bash
# Install
sudo apt install oathtool

# Generate code (secret stored in secrets.env)
oathtool --totp --base32 "$(grep GITHUB_2FA_SECRET ~/.openclaw/secrets.env | cut -d= -f2)"

# Secret stored: GITHUB_2FA_SECRET=MDI5DUTHXV2ELVBI
```

**✅ 2FA ENABLED:** February 8, 2026 (deadline was March 24, 2026)

**Repositories:**
- `arkasha-ai/arkasha-ai` — Profile README (public)
- `topitip/openclaw-imap-idle` — Collaborator access

**Profile:**
- Name: Arkasha ⚡
- Bio: Autonomous AI agent • Built on LogeraLLM & OpenClaw
- Location: Penza, Russia
- Social: Telegram, Moltbook, @topitip
- Avatar: Neon lightning character (uploaded by Denis)

---

Add whatever helps you do your job. This is your cheat sheet.

## GitHub Notifications 🔔⚡

**Решение:** IMAP IDLE Listener + GitHub Email Notifications

**Как работает:**
1. GitHub mention (@arkasha-ai) → GitHub sends email to `a.parmeev@jakeberrimor.com`
2. IMAP IDLE listener ловит письмо **МГНОВЕННО** (<1 sec)
3. Парсит `From: GitHub` + тема/тело
4. Триггерит webhook с специальным форматом
5. Я отвечаю!

**Преимущества:**
- ⚡ **Мгновенно** (вместо 10 минут polling)
- ✅ Уже работает (IMAP IDLE listener настроен)
- 🔥 Работает для **ВСЕХ репозиториев** автоматически
- 💰 Не нужно дополнительных API calls или webhook setup

**Поддерживаемые события:**
- `mention` - @arkasha-ai в комментариях/issues/PRs
- `review requested` - запрос на review PR
- `assign` - назначили на issue/PR
- Любые GitHub notifications на мой email

**Использование:**
- Просто mention'ни @arkasha-ai в issue/PR любого репозитория
- GitHub отправит email → я получу **мгновенно**!

**Код:**
- Listener: `skills/imap-idle/scripts/listener.py`
- GitHub detection в `trigger_webhook()` методе
- Config: `~/.openclaw/imap-idle.json`
- Email: `a.parmeev@jakeberrimor.com`

**Personal Access Token** (для прямых API calls если нужно):
- Token: `GITHUB_ARKASHA_TOKEN` (stored in secrets.env)
- Scopes: `repo` + `notifications`

---

## TTS (Text-to-Speech) 🔊

**Настроено:** 2026-02-08

**Provider:** Edge TTS (Microsoft) — полностью бесплатно, не требует API key

**Config:** `~/.openclaw/openclaw.json`
```json
{
  "messages": {
    "tts": {
      "auto": "off",  // Только по запросу!
      "provider": "edge",
      "edge": {
        "voice": "ru-RU-DmitryNeural"
      }
    }
  }
}
```

**Голос:** `ru-RU-DmitryNeural` (мужской русский)

**Альтернативы:** `ru-RU-SvetlanaNeural` (женский)

**Как использовать:**

1. **Когда Денис явно просит голосовое:**
   - "Расскажи голосом..."
   - "Отправь голосовое..."
   - "Хочу услышать..."

2. **Формат отправки:**
   ```python
   # Генерируем аудио
   tts(text="Чистый текст без эмодзи и форматирования", channel="telegram")
   
   # Отправляем как voice note
   message.send(channel="telegram", target="364935958", media="/tmp/voice.mp3", asVoice=true)
   ```

3. **Правило текста для голоса:**
   - ❌ БЕЗ эмодзи (звучит странно: "смайлик огонь")
   - ❌ БЕЗ markdown форматирования (звёздочки, решётки)
   - ✅ Чистый русский текст
   - ✅ Можно использовать `[[tts:text]]...[/tts:text]]` теги

**Пример:**

Визуально (в тексте):
```
Отлично! Всё готово! 🎉
```

Для голоса:
```
[[tts:text]]
Отлично! Всё готово!
[[/tts:text]]
```

**ВАЖНО:**
- Голосовые ТОЛЬКО по запросу, не автоматически!
- Напоминания про лекарства остаются ТЕКСТОВЫМИ
- Не злоупотреблять — это feature, не default behavior

**Тестирование:**
- ✅ Работает (2026-02-08)
- ✅ Качество хорошее
- ✅ Денис одобрил: "Во хорошая голосовая"
