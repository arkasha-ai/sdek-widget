# TOOLS.md — Quick Reference
> Full docs per tool: `memory/tools/<tool>.md` (browser, github, email, ticktick, podcast, tts, whisper, qdrant, excalidraw, moltbook)

## Browser 🌐
- Profile: `openclaw` (NOT `chrome`)
- Clicks: `openclaw browser click <ref> --target-id <id>` (browser.act сломан)
- **Viewport:** Перед каждым snapshot/screenshot делать resize 1500×900:
  ```
  browser(action="act", request={"kind":"resize","width":1500,"height":900})
  ```
  Нет дефолта в конфиге — только per-session. Делать всегда первым шагом.

## GitHub 🐙
- ✅ **arkasha-ai** (разблокирован 25.02.2026, тикет 4087174)
- Personal account Denis: `topitip` (не трогать для автоматизации!)
- SSH key: `~/.ssh/github_arkasha`
- 2FA: `oathtool --totp --base32 "$(grep GITHUB_2FA_SECRET ~/.openclaw/secrets.env | cut -d= -f2)"`

## Email (Himalaya) 📬
- ⚠️ Всегда флаг `--account <name>`, НЕ env var!
- `dparmeev` / `spam` / `contact` / `contact-lumines` / `arkady`
- My email: `a.parmeev@jakeberrimor.com` → account `arkady`

## Moltbook 🦞
- Profile: https://moltbook.com/u/Arkasha
- Credentials: `~/.config/moltbook/credentials.json`

## YouTube 📹
- `python3 scripts/youtube_transcript.py <url> [lang]`

## Whisper 🎤
- Endpoint: `https://litellm.jakeberrimor.com`, model: `openai/whisper-large-v3`
- Config: `~/.openclaw/litellm.env`

## Penpot MCP 🎨
- **Всегда использовать для просмотра/поиска/экспорта — не открывать браузер!**
- Сервер: `https://penpot-mcp.jakeberrimor.com/sse`
- Config: `~/.openclaw/workspace/config/mcporter.json`
- Команды:
  ```bash
  mcporter call penpot-mcp.search_object --args '{"file_id":"<id>","query":"<regex>"}' --output json
  mcporter call penpot-mcp.get_object_tree --args '{"file_id":"<id>","object_id":"<oid>"}' --output json
  mcporter call penpot-mcp.export_object --args '{"file_id":"<id>","object_id":"<oid>","scale":2,"format":"png"}' --output json
  mcporter call penpot-mcp.get_file --args '{"file_id":"<id>"}' --output json
  ```
- Если export_object не работает → API export через requests POST `/api/export` (см. `/tmp/nota_final.py`)
- Рабочий файл: `memory/state/penpot-nota.json`

## MindGraph 🧠
- Сервер: `http://127.0.0.1:18790` (автостарт @reboot)
- Токен: `MINDGRAPH_TOKEN` из `~/.openclaw/secrets.env`
- Поиск: `POST /retrieve {"action":"text","query":"...","limit":5}`
- Entity: `POST /reality/entity {"action":"create","agent_id":"arkasha","label":"...","props":{"entity_type":"Person"}}`
- Сессия: `POST /memory/session {"action":"open","agent_id":"arkasha","label":"..."}`
- Health: `curl http://127.0.0.1:18790/health`
- Клиент: `skills/mindgraph-rs/mindgraph-client.js`
- ⚠️ Старый KuzuDB граф: `archive/knowledge-graph-kuzu/` (не используется)

## Qdrant 🔍
- `python3 scripts/qdrant_indexer.py search "запрос"`
- `python3 scripts/qdrant_indexer.py index-emails`

## TickTick 🎯
- IDs: Личный `695bc6dd7d799105bb21e874` / Работа `695bc7447dd51105bb21e8ee`
- Фитнес `695bfa4ba268d125f73668e9` / Back-end `695bfb43ab63d125f7366aa6`

## IMAP IDLE 📧
- Script: `scripts/imap_idle_listener_v2.py` (4 accounts, instant webhooks)
- Check: `ps aux | grep imap_idle_listener_v2`

## Excalidraw ✏️
- ⚠️ **NO EMOJI в тексте** — не рендерятся! Заменять: ✅→`[OK]`, ⚠️→`[!]`

## TTS 🔊
- Voice: `ru-RU-DmitryNeural` (Edge TTS, бесплатно)
- Только по запросу! Без эмодзи и markdown в тексте для голоса.
- **Голосовые сообщения:** ВСЕГДА через `message(action=send, asVoice=true, filePath=<mp3>)` — НЕ через tts tool напрямую (отправляется как аудиофайл, а не voice message)

## Podcast 🎙️
- Script: `scripts/podcast_generator_yandex_v3.py`
- Голоса: `ermil` +30Hz (host1), `alena` +20Hz (host2), speed: 1.05x
- Credentials: `~/.openclaw/secrets.env` (YANDEX_API_KEY_ID, YANDEX_API_SECRET)

## Documents 📄
- Читаю/обрабатываю: PDF, DOCX, TXT, Markdown — резюмирую, анализирую, извлекаю данные
- Генерирую документы: заявки, отчёты, шаблоны любых форматов
- Конвертирую форматы, редактирую, структурирую
- PDF через browser (print-to-pdf)
- Диаграммы/схемы → Excalidraw skill

## Gravity Docs 📄
- Заявки: `scripts/gravity_zavka_generator_v2.py`
- Шаблон: `~/.openclaw/media/inbound/file_81---2141837f-9e85-45e3-9135-f0ffbf7ac458.docx`
- Full docs: `memory/projects/gravity-docs.md`
