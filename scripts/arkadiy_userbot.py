#!/usr/bin/env python3
"""
Arkadiy Userbot — WebSocket Bridge with media support
Text, voice (Whisper), images, documents.
"""

import asyncio
import json
import logging
import tempfile
import base64
import os
from pathlib import Path
from uuid import uuid4

import re
import websockets
import httpx
import edge_tts
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import (
    DocumentAttributeAudio, MessageMediaPhoto,
    MessageMediaDocument
)

# ─── Config ─────────────────────────────────────────────────────────────────
SESSION_FILE = Path("/home/clawdbot/.openclaw/arkadiy_session.txt")
LOG_FILE = Path("/home/clawdbot/.openclaw/workspace/memory/arkadiy_userbot.log")

API_ID = 37775362
API_HASH = "3ecd874239e793d8cc45e80d8cdad99b"

GATEWAY_WS = "ws://127.0.0.1:18789"
GATEWAY_TOKEN = "534be314efde94f86f194cde7d3b662b875798421facde70"
GATEWAY_ORIGIN = "https://clwd.jakeberrimor.com"

WHISPER_URL = "https://litellm.jakeberrimor.com/v1/audio/transcriptions"
LITELLM_KEY_FILE = Path("/home/clawdbot/.openclaw/litellm.env")
LITELLM_KEY = ""
for line in LITELLM_KEY_FILE.read_text().splitlines():
    if line.startswith("LITELLM_API_KEY="):
        LITELLM_KEY = line.split("=", 1)[1].strip()

session_string = SESSION_FILE.read_text().strip()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger(__name__)


# ─── Whisper transcription ───────────────────────────────────────────────────
async def transcribe_voice(file_path: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        with open(file_path, "rb") as f:
            resp = await client.post(
                WHISPER_URL,
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
                files={"file": ("voice.ogg", f, "audio/ogg")},
                data={"model": "openai/whisper-large-v3"}
            )
    resp.raise_for_status()
    return resp.json().get("text", "").strip()


SYSTEM_INJECT = "[Канал: Telegram userbot @narrownorn. Для файлов используй маркер [FILE:/путь] в ответе. НЕ используй message tool.]"

# ─── OpenClaw WebSocket ──────────────────────────────────────────────────────
async def openclaw_send(session_key: str, message: str, attachments: list = None) -> str:
    async with websockets.connect(
        GATEWAY_WS,
        additional_headers={"Origin": GATEWAY_ORIGIN}
    ) as ws:
        await ws.recv()  # challenge
        await ws.send(json.dumps({
            "type": "req", "id": str(uuid4()), "method": "connect",
            "params": {
                "minProtocol": 3, "maxProtocol": 3,
                "client": {"id": "webchat", "version": "1.0.0", "platform": "linux", "mode": "webchat"},
                "auth": {"token": GATEWAY_TOKEN},
                "role": "operator", "scopes": ["operator.admin"]
            }
        }))
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        if not resp.get('ok'):
            raise Exception(f"Auth failed: {resp.get('error', {}).get('message')}")

        # Prepend channel instructions to every message (works in any session state)
        full_message = SYSTEM_INJECT + "\n---\n" + message

        params = {
            "sessionKey": session_key,
            "message": full_message,
            "idempotencyKey": str(uuid4())
        }
        if attachments:
            params["attachments"] = attachments

        await ws.send(json.dumps({
            "type": "req", "id": str(uuid4()), "method": "chat.send",
            "params": params
        }))

        async for raw in ws:
            evt = json.loads(raw)
            if evt.get('event') == 'chat':
                payload = evt['payload']
                if payload.get('sessionKey') != session_key:
                    continue
                if payload.get('state') == 'final':
                    text = ""
                    for block in payload.get('message', {}).get('content', []):
                        if block.get('type') == 'text':
                            text += block.get('text', '')
                    return text or "..."

    return "Не получил ответ."


# ─── Message handler ─────────────────────────────────────────────────────────
async def handle_message(event, client):
    sender = await event.get_sender()
    uid = sender.id
    name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
    session_key = f"agent:main:webchat:user_{uid}"
    msg = event.message

    text = msg.text or msg.message or ""
    attachments = []
    prefix = ""

    # ── Voice message ──────────────────────────────────────────────────────
    is_voice = False
    if msg.media and hasattr(msg.media, 'document') and msg.media.document:
        for attr in msg.media.document.attributes:
            if isinstance(attr, DocumentAttributeAudio) and attr.voice:
                is_voice = True
                break

    if is_voice:
        log.info(f"[{uid}] Voice message received")
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            tmp_path = f.name
        try:
            await client.download_media(msg, file=tmp_path)
            transcript = await transcribe_voice(tmp_path)
            prefix = f"[Голосовое сообщение]: {transcript}"
            log.info(f"[{uid}] Transcribed: {transcript[:80]}")
        except Exception as e:
            log.error(f"Whisper error: {e}")
            prefix = "[Голосовое сообщение — не удалось расшифровать]"
        finally:
            os.unlink(tmp_path)

    # ── Photo ──────────────────────────────────────────────────────────────
    elif isinstance(msg.media, MessageMediaPhoto):
        log.info(f"[{uid}] Photo received")
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            tmp_path = f.name
        try:
            await client.download_media(msg, file=tmp_path)
            with open(tmp_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            attachments = [{"type": "image", "mimeType": "image/jpeg", "data": b64}]
            prefix = text or "[Фото]"
        except Exception as e:
            log.error(f"Photo download error: {e}")
            prefix = "[Фото — не удалось загрузить]"
        finally:
            os.unlink(tmp_path)

    # ── Document ───────────────────────────────────────────────────────────
    elif isinstance(msg.media, MessageMediaDocument) and not is_voice:
        doc = msg.media.document
        mime = getattr(doc, 'mime_type', '') or ''
        fname = ""
        for attr in doc.attributes:
            if hasattr(attr, 'file_name'):
                fname = attr.file_name
                break
        
        if mime.startswith('image/'):
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                tmp_path = f.name
            try:
                await client.download_media(msg, file=tmp_path)
                with open(tmp_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                attachments = [{"type": "image", "mimeType": mime, "data": b64}]
                prefix = text or f"[Изображение: {fname}]"
            except Exception as e:
                log.error(f"Image doc error: {e}")
                prefix = f"[Изображение {fname} — не удалось загрузить]"
            finally:
                os.unlink(tmp_path)
        elif doc.size < 200_000 and mime in ('text/plain', 'application/json', 'text/csv', 'text/markdown'):
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                tmp_path = f.name
            try:
                await client.download_media(msg, file=tmp_path)
                content = Path(tmp_path).read_text(errors='replace')[:3000]
                prefix = f"[Файл: {fname}]\n```\n{content}\n```"
                if text:
                    prefix = text + "\n\n" + prefix
            except Exception as e:
                log.error(f"File read error: {e}")
                prefix = f"[Файл {fname} — не удалось прочитать]"
            finally:
                os.unlink(tmp_path)
        else:
            prefix = text or f"[Файл: {fname} ({mime}, {doc.size//1024}KB) — слишком большой для обработки]"

    # ── Sticker / other ───────────────────────────────────────────────────
    elif msg.media and not prefix and not text:
        prefix = "[Медиа — не поддерживается]"

    # ── Plain text ─────────────────────────────────────────────────────────
    final_text = prefix or text
    if not final_text:
        return

    log.info(f"[{uid}] {name}: {final_text[:100]}")

    async with client.action(event.chat_id, 'typing'):
        try:
            reply = await asyncio.wait_for(
                openclaw_send(session_key, final_text, attachments or None),
                timeout=120
            )
        except asyncio.TimeoutError:
            reply = "Извини, запрос занял слишком много времени. Попробуй ещё раз."
        except Exception as e:
            log.error(f"OpenClaw error: {e}")
            reply = "Что-то пошло не так. Попробуй позже."

    # ── Check for FILE: markers in reply ──────────────────────────────────
    file_matches = re.findall(r'\[FILE:\s*([^\]]+)\]', reply)
    clean_reply = re.sub(r'\[FILE:\s*[^\]]+\]', '', reply).strip()

    # ── Send text reply ────────────────────────────────────────────────────
    if clean_reply:
        await event.reply(clean_reply)

    # ── Send any files referenced by AI ───────────────────────────────────
    for fpath in file_matches:
        fpath = fpath.strip()
        if Path(fpath).exists():
            await client.send_file(event.chat_id, fpath, reply_to=event.id)
            log.info(f"→ [{uid}] sent file: {fpath}")
        else:
            await event.reply(f"(Файл не найден: {fpath})")

    # ── Voice response if user sent voice ─────────────────────────────────
    if is_voice and clean_reply:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            voice_path = f.name
        try:
            communicate = edge_tts.Communicate(clean_reply, voice="ru-RU-DmitryNeural")
            await communicate.save(voice_path)
            await client.send_file(
                event.chat_id, voice_path,
                voice_note=True, reply_to=event.id
            )
            log.info(f"→ [{uid}] sent voice reply")
        except Exception as e:
            log.error(f"TTS error: {e}")
        finally:
            os.unlink(voice_path)

    log.info(f"→ [{uid}] {(clean_reply or '[files]')[:80]}")


# ─── Main ────────────────────────────────────────────────────────────────────
async def main():
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    log.info(f"Userbot started: {me.first_name} @{me.username} (id:{me.id})")

    seen_ids: set[int] = set()

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def on_dm(event):
        mid = event.message.id
        if mid in seen_ids:
            log.warning(f"[dedup] Skipping duplicate message_id={mid}")
            return
        seen_ids.add(mid)
        if len(seen_ids) > 1000:
            seen_ids.clear()
        await handle_message(event, client)

    log.info("Userbot running (text + voice + photo + docs)")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
