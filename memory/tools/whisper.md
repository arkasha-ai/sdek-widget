# Whisper (Speech Recognition) 🎤

**Endpoint:** `https://litellm.jakeberrimor.com`
**Model:** `openai/whisper-large-v3`
**Config:** `~/.openclaw/litellm.env`

## Использование (curl)

```bash
source ~/.openclaw/litellm.env
curl -X POST "${LITELLM_BASE_URL}/v1/audio/transcriptions" \
  -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  -F "file=@/path/to/audio.ogg" \
  -F "model=${WHISPER_MODEL}"
```

**Статус:** OpenClaw автоматически распознаёт голосовые из Telegram через этот endpoint.
