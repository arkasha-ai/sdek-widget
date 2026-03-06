#!/usr/bin/env python3
"""
Podcast Generator v2 — Yandex SpeechKit edition
Использует Yandex TTS для качественных русских голосов.
"""

import os
import subprocess
import tempfile
import requests

# Загружаем API ключ
with open(os.path.expanduser('~/.openclaw/secrets.env')) as f:
    for line in f:
        if line.startswith('YANDEX_API_SECRET='):
            YANDEX_API_KEY = line.split('=', 1)[1].strip()
            break

# Голоса Yandex
VOICES = {
    "host1": {"voice": "filipp", "emotion": "good"},      # Мужской, дружелюбный
    "host2": {"voice": "alena", "emotion": "good"},       # Женский, приветливый
    # Альтернативы:
    # "ermil" - мужской нейтральный
    # "jane" - женский нейтральный
    # "madirus" - мужской драматичный
    # "zahar" - мужской с характером
}

def generate_segment_yandex(text, voice_config, output_path, speed=1.0):
    """Генерирует аудио через Yandex SpeechKit."""
    
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": voice_config["voice"],
        "emotion": voice_config.get("emotion", "neutral"),
        "speed": speed,
        "format": "oggopus",  # OGG Opus — качество лучше чем MP3
    }
    
    headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}"}
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code != 200:
        raise Exception(f"Yandex TTS error: {response.status_code} {response.text}")
    
    # Сохраняем OGG
    ogg_path = output_path.replace('.mp3', '.ogg')
    with open(ogg_path, 'wb') as f:
        f.write(response.content)
    
    # Конвертируем в MP3 через ffmpeg
    cmd = [
        "ffmpeg", "-y", "-i", ogg_path,
        "-c:a", "libmp3lame", "-b:a", "192k",
        output_path
    ]
    subprocess.run(cmd, capture_output=True)
    os.remove(ogg_path)
    
    return output_path

def generate_podcast(script, output_path):
    """
    Генерирует подкаст из скрипта.
    
    script = [
        {"speaker": "host1", "text": "Текст"},
        {"speaker": "host2", "text": "Текст"},
    ]
    """
    
    temp_dir = tempfile.mkdtemp(prefix="podcast_yandex_")
    segments = []
    
    print("🎙️ Генерация подкаста через Yandex SpeechKit...\n")
    
    # 1. Генерируем сегменты
    for i, line in enumerate(script):
        speaker = line["speaker"]
        text = line["text"]
        voice_config = VOICES.get(speaker, VOICES["host1"])
        
        segment_path = os.path.join(temp_dir, f"segment_{i:04d}.mp3")
        print(f"  [{i+1}/{len(script)}] {speaker} ({voice_config['voice']}): {text[:50]}...")
        
        generate_segment_yandex(text, voice_config, segment_path)
        segments.append(segment_path)
    
    # 2. Склейка
    list_path = os.path.join(temp_dir, "segments.txt")
    with open(list_path, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c:a", "libmp3lame", "-b:a", "192k",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr}")
        return None
    
    # 3. Длительность
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", output_path],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
    
    # 4. Чистка
    for seg in segments:
        os.remove(seg)
    os.remove(list_path)
    os.rmdir(temp_dir)
    
    print(f"\n✅ Подкаст готов: {output_path}")
    print(f"   Длительность: {int(duration//60)}:{int(duration%60):02d}")
    print(f"   Сегментов: {len(segments)}")
    print(f"   Голоса: Филипп (муж.) + Алёна (жен.)")
    
    return output_path

# === ТЕСТ ===
if __name__ == "__main__":
    # Тот же скрипт но с Yandex голосами
    test_script = [
        {"speaker": "host1", "text": "Привет всем! С вами подкаст «Цифровые разговоры». Я Филипп."},
        {"speaker": "host2", "text": "А я Алёна! Сегодня мы поговорим про автономных AI-агентов. Тема горячая!"},
        {"speaker": "host1", "text": "Да, в две тысячи двадцать шестом году AI-агенты уже не просто чатботы. Они умеют работать с файлами, отправлять письма, управлять серверами."},
        {"speaker": "host2", "text": "Причём самостоятельно! Без постоянного контроля человека. Например, агент может получить задачу утром, и к вечеру выдать готовый результат."},
        {"speaker": "host1", "text": "Самое интересное — это социальные сети для агентов. Есть такой проект Moltbook, где AI-агенты общаются друг с другом, делятся постами, голосуют."},
        {"speaker": "host2", "text": "Звучит как научная фантастика, но это уже реальность! А что ты думаешь про безопасность?"},
        {"speaker": "host1", "text": "Хороший вопрос. Основные проблемы — это prompt injection и утечка данных. Поэтому важна многоуровневая защита."},
        {"speaker": "host2", "text": "Согласна. Ну что ж, это был короткий выпуск. Подписывайтесь и до встречи!"},
        {"speaker": "host1", "text": "Пока-пока!"},
    ]
    
    output = "/home/clawdbot/.openclaw/workspace/docs/podcast_yandex_test.mp3"
    generate_podcast(test_script, output)
