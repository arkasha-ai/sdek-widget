#!/usr/bin/env python3
"""
Тест всех голосов Yandex SpeechKit
"""

import os
import requests
import subprocess

with open(os.path.expanduser('~/.openclaw/secrets.env')) as f:
    for line in f:
        if line.startswith('YANDEX_API_SECRET='):
            YANDEX_API_KEY = line.split('=', 1)[1].strip()
            break

# Все доступные голоса Yandex
VOICES = {
    "alena": {"gender": "female", "desc": "Приветливый женский"},
    "filipp": {"gender": "male", "desc": "Дружелюбный мужской"},
    "ermil": {"gender": "male", "desc": "Нейтральный мужской"},
    "jane": {"gender": "female", "desc": "Нейтральный женский"},
    "madirus": {"gender": "male", "desc": "Драматичный мужской"},
    "zahar": {"gender": "male", "desc": "Мужской с характером"},
    "omazh": {"gender": "female", "desc": "Женский приветливый"},
}

EMOTIONS = ["neutral", "good", "evil"]
SPEEDS = [0.8, 1.0, 1.2]

def generate_test(voice, emotion, speed, text, output_path):
    """Генерирует тестовый образец."""
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": voice,
        "emotion": emotion,
        "speed": speed,
        "format": "oggopus",
    }
    
    headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}"}
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code != 200:
        return None
    
    ogg_path = output_path.replace('.mp3', '.ogg')
    with open(ogg_path, 'wb') as f:
        f.write(response.content)
    
    cmd = ["ffmpeg", "-y", "-i", ogg_path, "-c:a", "libmp3lame", "-b:a", "192k", output_path]
    subprocess.run(cmd, capture_output=True)
    os.remove(ogg_path)
    
    return output_path

# Тест всех голосов
text = "Привет! Это тестовый голос для подкаста. Звучит хорошо?"

print("🎙️ Тестирую все голоса Yandex...\n")

results = []
for voice, info in VOICES.items():
    for emotion in ["neutral", "good"]:
        output = f"/tmp/yandex_test_{voice}_{emotion}.mp3"
        print(f"  {voice} ({info['desc']}) — эмоция: {emotion}")
        
        result = generate_test(voice, emotion, 1.0, text, output)
        if result:
            results.append({
                "voice": voice,
                "emotion": emotion,
                "desc": info['desc'],
                "file": output
            })

print(f"\n✅ Сгенерировано {len(results)} образцов")
print("\nСлушай их и выбери лучший!")

# Создаём плейлист
playlist = "/tmp/yandex_voices_playlist.txt"
with open(playlist, "w") as f:
    for r in results:
        f.write(f"# {r['voice']} - {r['desc']} ({r['emotion']})\n")
        f.write(f"file '{r['file']}'\n")

# Склеиваем всё в один файл для удобства
output_all = "/home/clawdbot/.openclaw/workspace/docs/yandex_all_voices.mp3"
cmd = [
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", playlist,
    "-c:a", "libmp3lame", "-b:a", "192k",
    output_all
]
subprocess.run(cmd, capture_output=True)

print(f"\n🎧 Все голоса в одном файле: {output_all}")
print("\nВ файле:")
for r in results:
    print(f"  - {r['voice']} ({r['emotion']}): {r['desc']}")
