# Podcast Generation 🎙️

**Script:** `scripts/podcast_generator_yandex_v3.py` (API v3 gRPC)
**TTS:** Yandex SpeechKit
**Credentials:** `~/.openclaw/secrets.env` → YANDEX_API_KEY_ID, YANDEX_API_SECRET

## Голоса

| ID | Имя | Тип | Эмоции |
|----|-----|-----|--------|
| `ermil` | Ермил | мужской | neutral, good, evil |
| `alena` | Алёна | женский | neutral, good, evil |
| `filipp` | Филипп | мужской | neutral, good |
| `jane` | Джейн | женский | neutral, good, evil |
| `zahar` | Захар | мужской | neutral, good |

**Defaults:** ermil +30Hz (host1), alena +20Hz (host2), speed 1.05x

## Использование

```python
from scripts.podcast_generator_yandex_v3 import generate_podcast

script = [
    {"speaker": "host1", "text": "Привет! sil<[200]> Как дела?"},
    {"speaker": "host2", "text": "Отлично! Обсудим <[accented]> новости?"},
    {"speaker": "host1", "text": "Интересно!", "pitch_shift": 50},  # override pitch
]
generate_podcast(script, "output.mp3")
```

## TTS-разметка

| Разметка | Описание | Пример |
|----------|----------|--------|
| `+` | Ударение | `зам+ок` |
| `sil<[t]>` | Пауза (мс, макс 7000) | `слово. sil<[300]> следующее` |
| `<[size]>` | Контекстная пауза | `слово; <[medium]> дальше` |
| `**слово**` | Акцент | `Мы **должны** успеть` |
| `[[фонемы]]` | Фонетика | `[[v a sʲ ʌ]]` |

**Размеры пауз:** tiny / small / medium / large / huge

## Параметры

- **speed:** 0.1–3.0 (default 1.0, рекомендуем 1.05x)
- **pitch_shift:** -1000..+1000 Hz
- **emotion:** neutral / good / evil

## Dependencies

```bash
pip install grpcio grpcio-tools protobuf
# ffmpeg: ~/.local/bin/ffmpeg
```

## Стоимость

1 млн символов/месяц бесплатно, потом ~1₽/1k символов.
