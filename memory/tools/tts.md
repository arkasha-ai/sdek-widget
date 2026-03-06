# TTS (Text-to-Speech) 🔊

**Provider:** Edge TTS (Microsoft) — бесплатно, без API key
**Voice:** `ru-RU-DmitryNeural` (мужской) / `ru-RU-SvetlanaNeural` (женский)
**Config:** `~/.openclaw/openclaw.json` → `messages.tts`

## Правила

- Только по **явному запросу** ("расскажи голосом", "отправь голосовое")
- ❌ БЕЗ эмодзи и markdown в тексте (звучат странно)
- ✅ Чистый русский текст

## Как отправить

```python
# 1. Генерируем
tts(text="Чистый текст без эмодзи", channel="telegram")

# 2. Отправляем как voice note
message.send(channel="telegram", target="364935958", media="/tmp/voice.mp3", asVoice=True)
```
