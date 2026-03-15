# Qwen3-TTS — Voice Cloning

## Сервер
- URL: `http://109.194.141.123:7860`
- **Доступен только когда включён "beast" (RunPod GPU сервер)**
- Перед использованием: `curl -s --max-time 5 http://109.194.141.123:7860/voices/`

## Репо
- Оригинал: https://github.com/ValyrianTech/Qwen3-TTS_server
- Наш форк: https://github.com/arkasha-ai/Qwen3-TTS_server (с улучшениями)

## Что умею

### Генерация с клонированием голоса + эмоция
```bash
TEXT="Текст для озвучки"
ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$TEXT'))")
curl -s --max-time 60 \
  "http://109.194.141.123:7860/synthesize_speech/?text=${ENCODED}&voice=denis&emotion=happy" \
  -o /path/to/output.wav
```

### Загрузить голос с эмоцией
```bash
curl -X POST "http://109.194.141.123:7860/upload_audio/" \
  -F "audio_file_label=denis" \
  -F "emotion=happy" \
  -F "file=@voice_sample.ogg"
```

### Список голосов и эмоций
```bash
curl http://109.194.141.123:7860/voices/
```

## Голоса (сохранены на сервере)
| Голос | Эмоции |
|-------|--------|
| denis | neutral, happy, serious, angry |
| yulia | neutral |
| demo_speaker0 | neutral |

## Подкаст с голосами
Скрипт: `drafts/gen_podcast_qwen3.py`
- Генерирует реплики по очереди через API
- Склеивает через ffmpeg с паузами между репликами
- Итоговый файл: MP3

## Важно
- Голоса хранятся на сервере в `resources/{name}/{emotion}.wav`
- При перезапуске контейнера без volume — голоса слетят
- Нужно заново заливать через upload_audio после каждого рестарта
- Латентность ~30-60 сек на реплику (GPU генерация)
