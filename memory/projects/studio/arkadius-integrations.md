# Аркадиус — Интеграции каналов

> Исследование: апрель 2026  
> Цель: выбрать каналы для подключения ИИ-ассистента Аркадиус

---

## Оглавление

1. [MAX Bot API](#1-max-bot-api)
2. [VK Bot API](#2-vk-bot-api)
3. [LiveKit Agents SDK (голосовые звонки)](#3-livekit-agents-sdk)
4. [Российская SIP-телефония](#4-российская-sip-телефония)
5. [Сравнительная таблица](#5-сравнительная-таблица)
6. [Рекомендации](#6-рекомендации)

---

## 1. MAX Bot API

**Сайт:** https://dev.max.ru/docs  
**API Endpoint:** `https://platform-api.max.ru`

### Описание

MAX (бывший ТамТам от Mail.ru Group) — российский мессенджер. Платформа для партнёров позволяет создавать чат-боты, мини-приложения и каналы.

### Ограничения доступа

- Только для **юридических лиц и ИП — резидентов РФ**
- Требуется верификация организации на платформе MAX для партнёров
- Один аккаунт = максимум **5 ботов**
- Бот проходит **модерацию** перед публикацией

### Подключение бота

Поддерживаются два режима (нельзя использовать одновременно):

| Режим | Применение |
|-------|-----------|
| **Webhook** | Production: сервер получает события через POST-запросы |
| **Long Polling** | Разработка/тестирование: бот сам опрашивает сервер |

**Лимит API:** 30 запросов в секунду (rps) на `platform-api.max.ru`

**Передача токена:** через заголовок `Authorization: <token>` (через query-параметры больше **не поддерживается**)

### Python SDK

**Библиотека:** `maxapi`  
**GitHub:** https://github.com/max-messenger/max-botapi-python  
**PyPI:** https://pypi.org/project/maxapi/  
**Лицензия:** MIT  
**Статус:** неофициальная, но **верифицирована командой MAX**

```bash
# Установка из PyPI
pip install maxapi

# Установка из GitHub (версия, проверенная командой MAX)
pip install git+https://github.com/max-messenger/max-botapi-python.git

# Webhook-зависимости
pip install maxapi[webhook]
```

### Поддержка голосовых сообщений

Явно не документирована в открытом доступе. MAX как мессенджер поддерживает голосовые сообщения на уровне интерфейса, но API ботов — только текст и файлы.  
**Вывод: голосовые сообщения через Bot API не поддерживаются нативно.**

### Примеры кода

#### Long Polling (разработка)

```python
import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated

logging.basicConfig(level=logging.INFO)

bot = Bot('ВАШ_ТОКЕН')
dp = Dispatcher()

# Обработчик нажатия кнопки "Начать"
@dp.bot_started()
async def bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='Привет! Отправь мне /start'
    )

# Обработчик команды /start
@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    await event.message.answer("Пример чат-бота для MAX")

async def main():
    # Если есть webhook-подписки — удалить перед polling
    await bot.delete_webhook()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
```

#### Webhook (production)

```python
import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import Command, MessageCreated

logging.basicConfig(level=logging.INFO)

bot = Bot('ВАШ_ТОКЕН')
dp = Dispatcher()

@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    await event.message.answer("Привет из вебхука!")

async def main():
    await dp.handle_webhook(
        bot=bot,
        host='localhost',
        port=8080,
    )

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 2. VK Bot API

**Документация:** https://dev.vk.com/ru/api/bots/getting-started  
**API Endpoint:** `https://api.vk.com/method/`

### Описание

VK (ВКонтакте) — крупнейшая российская социальная сеть. Боты создаются от имени **групп/сообществ**, не личных аккаунтов.

### Подключение бота

| Режим | Описание |
|-------|---------|
| **Callback API (Webhook)** | VK отправляет события на ваш сервер. Нужен публичный HTTPS URL. Ответ `{"type":"confirmation",...}` при верификации. |
| **Bots Long Poll API** | Бот периодически опрашивает сервер VK на события. Подходит для разработки. |

**Как получить токен:**  
1. Создать сообщество VK  
2. Управление → Работа с API → Ключи доступа → Создать ключ  
3. Включить разрешения: `messages`, `photos`, `docs` и т.д.

**Лимиты:**
- Стандартные лимиты VK API: ~3 запроса в секунду на метод
- `messages.send` — не более 20 сообщений в секунду одному пользователю

### Python SDK

#### vkbottle (рекомендуется)

**GitHub:** https://github.com/vkbottle/vkbottle  
**PyPI:** https://pypi.org/project/vkbottle/  
**Лицензия:** MIT  
**Статус:** активно поддерживается (2024), async-first

```bash
pip install vkbottle
```

#### vk_api (классический)

**Документация:** https://vk-api.readthedocs.io  
**PyPI:** https://pypi.org/project/vk-api/  
**Модуль:** `VkBotLongPoll` для ботов

```bash
pip install vk-api
```

### Поддержка голосовых сообщений

**Да, частично:**
- Бот **может принимать** голосовые сообщения (они приходят как вложение типа `audio_message`)
- Бот **может отправлять** аудио-файлы (загрузка через `docs.getMessagesUploadServer`)
- Отправить именно "голосовое сообщение" (с видеодорожкой) боту сложнее — нужна загрузка в формате `.ogg`

### Примеры кода

#### vkbottle — Long Polling

```python
from vkbottle.bot import Bot, Message

bot = Bot("GroupToken")

@bot.on.message()
async def handler(message: Message) -> str:
    return "Привет! Чем могу помочь?"

# Обработка голосового сообщения
@bot.on.message()
async def voice_handler(message: Message):
    if message.attachments:
        for att in message.attachments:
            if att.type.value == "audio_message":
                ogg_url = att.audio_message.link_ogg
                # Скачать и обработать голос
                await message.answer(f"Получил голосовое: {ogg_url}")
                return
    return "Отправь голосовое или текст"

bot.run_forever()
```

#### vk_api — Long Polling

```python
import vk_api
from vk_api.longpoll import VkBotLongPoll, VkBotEventType

vk_session = vk_api.VkApi(token="GroupToken")
longpoll = VkBotLongPoll(vk_session, group_id=123456789)
vk = vk_session.get_api()

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.object.message
        text = msg.get("text", "")
        peer_id = msg["peer_id"]
        
        # Проверка голосового сообщения
        attachments = msg.get("attachments", [])
        for att in attachments:
            if att["type"] == "audio_message":
                ogg_url = att["audio_message"]["link_ogg"]
                # Обработать голос...
        
        vk.messages.send(
            peer_id=peer_id,
            message=f"Ты написал: {text}",
            random_id=0
        )
```

#### Webhook (Callback API) через FastAPI

```python
from fastapi import FastAPI, Request
import vk_api

app = FastAPI()
vk_session = vk_api.VkApi(token="GroupToken")
vk = vk_session.get_api()

CONFIRMATION_TOKEN = "ВАШ_CONFIRMATION_TOKEN"

@app.post("/vk-webhook")
async def vk_webhook(request: Request):
    data = await request.json()
    
    if data["type"] == "confirmation":
        return CONFIRMATION_TOKEN
    
    if data["type"] == "message_new":
        msg = data["object"]["message"]
        vk.messages.send(
            peer_id=msg["peer_id"],
            message="Получил через webhook!",
            random_id=0
        )
    
    return "ok"
```

---

## 3. LiveKit Agents SDK

**Документация:** https://docs.livekit.io/agents/  
**GitHub:** https://github.com/livekit/agents  
**Лицензия:** Apache 2.0

### Описание

LiveKit — open-source платформа для realtime голоса, видео и AI-агентов. Agents SDK позволяет строить голосовых ИИ-ассистентов с полноценным STT-LLM-TTS пайплайном.

### Ключевые возможности

- **Голос:** STT → LLM → TTS пайплайн в реальном времени
- **WebRTC:** надёжная передача даже при плохом интернете
- **Телефония:** нативная поддержка SIP (входящие и исходящие звонки)
- **Мультимодальность:** голос, текст, видео, screen share
- **Multi-agent handoff:** передача звонка между агентами
- **Интеграции:** OpenAI, Anthropic, Deepgram, ElevenLabs, Azure, Silero VAD и др.

### Требования

- Python >= 3.10 (или Node.js >= 20)
- Аккаунт LiveKit Cloud (бесплатный) или self-hosted сервер

### Установка

```bash
pip install livekit-agents

# Плагины (выбрать нужные)
pip install livekit-plugins-openai
pip install livekit-plugins-deepgram      # STT
pip install livekit-plugins-elevenlabs    # TTS
pip install livekit-plugins-silero        # VAD (определение речи)
pip install livekit-plugins-noise-cancellation
```

### Как работает

1. Агент запускается и регистрируется на LiveKit сервере
2. Ждёт dispatch-запроса (новая комната / новый звонок)
3. Подключается к комнате как участник
4. Обрабатывает аудио через STT → LLM → TTS

### SIP / Телефония

LiveKit поддерживает:
- **Входящие звонки** через SIP Inbound Trunk (любой SIP-провайдер)
- **Исходящие звонки** через SIP Outbound Trunk
- **LiveKit Phone Numbers** (США, через LiveKit Cloud)
- Интеграция с **любым российским SIP-провайдером** (Sipuni, Mango Office и др.) через SIP trunk

Поддерживаемые протоколы: SIP over UDP/TCP/TLS, DTMF, RTP

### Пример кода: голосовой агент

```python
import asyncio
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, deepgram, silero

async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "Вы — Аркадий, дружелюбный голосовой ассистент. "
            "Общайтесь на русском языке. "
            "Отвечайте кратко и по делу."
        ),
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=deepgram.STT(language="ru"),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(voice="alloy"),
        chat_ctx=initial_ctx,
    )

    assistant.start(ctx.room)

    await asyncio.sleep(1)
    await assistant.say("Привет! Я Аркадий. Чем могу помочь?", allow_interruptions=True)

    await assistant.wait_until_done()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
```

### Запуск

```bash
# Создать .env файл с ключами
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=...
DEEPGRAM_API_KEY=...

# Запустить агента
python agent.py dev
```

---

## 4. Российская SIP-телефония

### 4.1 Sipuni

**Сайт:** https://sipuni.com  
**Документация API:** https://doc.sipuni.com/articles/636--api/

#### Возможности API

| Метод | Описание |
|-------|---------|
| HTTP Events (Webhook) | Sipuni отправляет события о звонках на ваш URL |
| WebSocket Events | Подписка на события через WebSocket |
| REST API | Управление: инициация звонков, SMS, статистика |
| Генерация ключа | Через личный кабинет: Настройки → API |

#### Webhook — события звонков

Настройка: Личный кабинет → Настройки → API → События на АТС → указать URL

**Параметры webhook-события:**

```
event     - тип события (1=начало, 2=ответ, 3=конец, 4=перевод)
call_id   - уникальный ID звонка
src_num   - номер звонящего
src_type  - 1=внешний, 2=внутренний
dst_num   - номер назначения
dst_type  - 1=внешний, 2=внутренний
timestamp - Unix timestamp (UTC)
```

**Ответ вашего сервера:**
```json
{"success": true}
```

#### Пример обработки webhook (Python + FastAPI)

```python
from fastapi import FastAPI, Request
import hashlib
import requests

app = FastAPI()

SIPUNI_API_KEY = "ваш_ключ_api"
SIPUNI_USER_ID = "ID_кабинета"

@app.post("/sipuni-webhook")
async def sipuni_webhook(request: Request):
    data = await request.form()
    
    event_type = data.get("event")
    call_id = data.get("call_id")
    src_num = data.get("src_num")
    dst_num = data.get("dst_num")
    
    print(f"Событие {event_type}: {src_num} -> {dst_num}, ID: {call_id}")
    
    # event=1 — начало звонка, можно инициировать ИИ-обработку
    if event_type == "1":
        # Запустить обработку через LiveKit
        pass
    
    return {"success": True}


def make_call(caller_num: str, callee_num: str):
    """Инициировать исходящий звонок через Sipuni API"""
    import time
    ts = str(int(time.time()))
    
    sign_str = f"{SIPUNI_USER_ID}{callee_num}{caller_num}{ts}{SIPUNI_API_KEY}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    
    response = requests.get(
        "https://sipuni.com/api/call/request",
        params={
            "user": SIPUNI_USER_ID,
            "caller": caller_num,   # номер АТС
            "callee": callee_num,   # кому звонить
            "tree": "0",            # 0 = без схемы
            "timestamp": ts,
            "sign": sign,
        }
    )
    return response.json()
```

#### Python SDK

Официального SDK нет. Работа через `requests` / `httpx` напрямую.

---

### 4.2 Mango Office

**Сайт:** https://www.mango-office.ru  
**Документация API:** https://www.mango-office.ru/support/api/

#### Виды API

| API | Описание |
|-----|---------|
| API Виртуальной АТС | Основной: управление звонками, уведомления, перевод |
| API Коллтрекинга | Данные о звонках для аналитики/CRM |
| API Манго Диалоги | Мультиканальный чат: Telegram, WhatsApp, Email, VK, виджет |
| API Контакт-центра | Обращения, статусы агентов, кампании обзвона |
| API Сервер-клиент | Дополнительный: для случаев когда основной API недоступен |

#### Особенности

- REST API + Webhooks
- **Манго Диалоги** — интересная возможность: единый API для множества каналов
- Подробная документация в PDF: https://static.mango-office.ru/project-im/Support/Mango_Dialogi/Manual_API_Mango_Dialogi.pdf

#### Пример: webhook на входящий звонок

```python
from fastapi import FastAPI, Request
import hashlib
import json

app = FastAPI()
MANGO_API_KEY = "ваш_api_key"
MANGO_API_SALT = "ваш_salt"

@app.post("/mango-webhook")
async def mango_webhook(request: Request):
    data = await request.form()
    
    json_str = data.get("json")
    sign = data.get("sign")
    
    # Верификация подписи
    expected_sign = hashlib.sha256(
        (MANGO_API_KEY + json_str + MANGO_API_SALT).encode()
    ).hexdigest()
    
    if sign != expected_sign:
        return {"error": "Invalid signature"}, 403
    
    event = json.loads(json_str)
    event_type = event.get("event", {}).get("type")
    
    print(f"Mango событие: {event_type}")
    
    return "OK"
```

#### Python SDK

Официального SDK нет. Работа через REST API с `requests`.

---

### 4.3 МТТ (Межрегиональный ТранзитТелеком)

**Сайт:** https://www.mtt.ru  
**Продукт для ботов:** МТТ VoiceBox (голосовой бот)

#### Особенности

- **VoiceBox** — готовый конструктор голосовых ботов + API для разработчиков
- REST API для управления голосовыми сценариями
- SIP-транки для интеграции с собственной телефонией
- Интеграции с CRM: Bitrix24, AmoCRM, retailCRM, МойСклад

#### Применение для Аркадиуса

МТТ лучше подходит как **SIP-провайдер** (SIP trunk), а не как платформа для ботов. VoiceBox — собственный конструктор, не предназначен для интеграции с внешними LLM.

**Схема интеграции:**
```
МТТ (SIP trunk) → LiveKit SIP Trunk → LiveKit Room → Аркадиус (LLM агент)
```

---

## 5. Сравнительная таблица

| Параметр | MAX | VK | LiveKit | Sipuni | Mango Office |
|----------|-----|----|---------|--------|-------------|
| **Тип** | Мессенджер | Соцсеть | WebRTC платформа | АТС/СИП | АТС/СИП |
| **Webhook** | ✅ | ✅ | ✅ (SIP trunk) | ✅ | ✅ |
| **Long Poll** | ✅ (dev only) | ✅ | — | — | — |
| **Python SDK** | ✅ `maxapi` | ✅ `vkbottle`, `vk_api` | ✅ `livekit-agents` | ❌ REST | ❌ REST |
| **Голосовые сообщения** | ❌ | Частично (receive) | ✅ Полностью | ✅ (SIP звонки) | ✅ (SIP звонки) |
| **Аудио-звонки** | ❌ | ❌ | ✅ WebRTC + SIP | ✅ | ✅ |
| **Ограничения** | РФ юрлица, 5 ботов, 30 rps | ~3 rps, сообщество | Python 3.10+, облако | Без SDK | Без SDK |
| **Простота начала** | Средняя | Высокая | Средняя | Средняя | Средняя |
| **Стоимость** | Бесплатно | Бесплатно | Бесплатно (cloud по трафику) | По тарифу | По тарифу |

---

## 6. Рекомендации

### Для текстового чат-бота

**VK** — проще всего начать:
- Хорошая документация
- Два отличных Python SDK (`vkbottle`, `vk_api`)
- Нет требований к юрлицу
- Огромная аудитория

**MAX** — если нужен охват именно MAX-аудитории:
- Нужно быть юрлицом/ИП
- Хорошая библиотека `maxapi`
- Меньше пользователей чем у VK

### Для голосового ИИ-ассистента

**LiveKit Agents** — лучший выбор:
- Профессиональный STT-LLM-TTS пайплайн
- Нативная SIP-поддержка (звонки по телефону)
- Open Source
- Работает с любым LLM (OpenAI, Anthropic, Yandex SpeechKit и др.)

**Связка с телефонией:**
```
Пользователь звонит → Sipuni/Mango Office (SIP trunk) 
                    → LiveKit SIP Inbound Trunk 
                    → LiveKit Room 
                    → Аркадиус Agent (Python) 
                    → LLM (GPT-4o / Claude / etc.)
```

**Sipuni vs Mango Office для SIP trunk:**

| | Sipuni | Mango Office |
|--|--------|-------------|
| Документация | Базовая, есть Telegram-поддержка | Подробнее, есть PDF |
| Webhook | ✅ HTTP + WebSocket | ✅ REST + Webhook |
| API простота | Средняя (MD5 подпись) | Средняя (SHA256 подпись) |
| Известность | Меньше | Больше |
| Рекомендация | Для старта (проще тарифы) | Если нужен контакт-центр |

### Итоговый стек для Аркадиуса

```
Текстовые каналы:
  - VK → vkbottle + FastAPI
  - MAX → maxapi + FastAPI (при наличии юрлица)

Голосовые звонки:
  - LiveKit Agents SDK (Python)
  - SIP trunk: Sipuni или Mango Office
  - STT: Yandex SpeechKit / Deepgram (русский язык!)
  - TTS: Yandex SpeechKit / ElevenLabs

Инфраструктура:
  - LiveKit Cloud (бесплатный старт) или self-hosted
  - FastAPI для webhook-эндпоинтов
```

> **Важно для русского языка:** LiveKit поддерживает Yandex SpeechKit для STT/TTS через плагины — это ключевое преимущество для русскоязычного голосового ассистента.

---

*Документ создан: 2026-04-04*  
*Обновить при изменении API или появлении новых библиотек*
