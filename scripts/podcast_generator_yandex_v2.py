#!/usr/bin/env python3
"""
Podcast Generator v3 — Yandex SpeechKit с SSML и паузами
"""

import os
import subprocess
import tempfile
import requests

with open(os.path.expanduser('~/.openclaw/secrets.env')) as f:
    for line in f:
        if line.startswith('YANDEX_API_SECRET='):
            YANDEX_API_KEY = line.split('=', 1)[1].strip()
            break

# Голоса с именами ведущих
VOICES = {
    "host1": {
        "voice": "filipp",
        "emotion": "good",
        "name": "Филипп",
    },
    "host2": {
        "voice": "alena",
        "emotion": "good",
        "name": "Алёна",
    },
}

def text_to_ssml(text, speed=1.05, add_pauses=True):
    """
    Преобразует текст в SSML с паузами.
    Yandex не поддерживает prosody, скорость через параметр speed.
    """
    
    ssml = '<speak>'
    
    # Добавляем паузы
    if add_pauses:
        # Короткие паузы после запятых
        text = text.replace(',', ', <break time="300ms"/>')
        # Средние паузы после точек и восклицаний
        text = text.replace('.', '. <break time="500ms"/>')
        text = text.replace('!', '! <break time="500ms"/>')
        text = text.replace('?', '? <break time="500ms"/>')
    
    ssml += text
    ssml += '</speak>'
    
    return ssml

def generate_segment_yandex(text, voice_config, output_path, speed=1.05, announce_speaker=True):
    """Генерирует аудио через Yandex SpeechKit с SSML."""
    
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    
    # Добавляем имя ведущего в начало
    if announce_speaker and voice_config.get("name"):
        # Короткая пауза после имени
        full_text = f"{voice_config['name']}.<break time=\"400ms\"/> {text}"
    else:
        full_text = text
    
    # Преобразуем в SSML
    ssml_text = text_to_ssml(full_text, speed=speed)
    
    data = {
        "ssml": ssml_text,
        "lang": "ru-RU",
        "voice": voice_config["voice"],
        "emotion": voice_config.get("emotion", "neutral"),
        "speed": speed,  # Скорость напрямую в параметре
        "format": "oggopus",
    }
    
    headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}"}
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code != 200:
        raise Exception(f"Yandex TTS error: {response.status_code} {response.text}")
    
    # Сохраняем OGG
    ogg_path = output_path.replace('.mp3', '.ogg')
    with open(ogg_path, 'wb') as f:
        f.write(response.content)
    
    # Конвертируем в MP3
    cmd = [
        "ffmpeg", "-y", "-i", ogg_path,
        "-c:a", "libmp3lame", "-b:a", "192k",
        output_path
    ]
    subprocess.run(cmd, capture_output=True)
    os.remove(ogg_path)
    
    return output_path

def add_pause_segment(duration_ms, output_path):
    """Создаёт сегмент тишины."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={duration_ms/1000}",
        "-c:a", "libmp3lame", "-b:a", "192k",
        output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path

def generate_podcast(script, output_path, speed=1.05, pause_between_speakers=800):
    """
    Генерирует подкаст с улучшениями.
    
    script = [
        {"speaker": "host1", "text": "Текст"},
        {"speaker": "host2", "text": "Текст"},
    ]
    
    speed: скорость речи (1.0 = нормально, 1.05 = чуть быстрее)
    pause_between_speakers: пауза между репликами в мс (800 = 0.8 сек)
    """
    
    temp_dir = tempfile.mkdtemp(prefix="podcast_yandex_v2_")
    segments = []
    
    print("🎙️ Генерация подкаста (SSML + паузы)...\n")
    print(f"   Скорость: {speed}x")
    print(f"   Паузы между репликами: {pause_between_speakers}ms\n")
    
    # 1. Генерируем сегменты
    for i, line in enumerate(script):
        speaker = line["speaker"]
        text = line["text"]
        voice_config = VOICES.get(speaker, VOICES["host1"])
        
        # Голосовой сегмент
        segment_path = os.path.join(temp_dir, f"segment_{i:04d}.mp3")
        print(f"  [{i+1}/{len(script)}] {voice_config['name']}: {text[:50]}...")
        
        generate_segment_yandex(
            text, voice_config, segment_path,
            speed=speed,
            announce_speaker=(i == 0)  # Только первая реплика с именем
        )
        segments.append(segment_path)
        
        # Пауза после реплики (кроме последней)
        if i < len(script) - 1:
            pause_path = os.path.join(temp_dir, f"pause_{i:04d}.mp3")
            add_pause_segment(pause_between_speakers, pause_path)
            segments.append(pause_path)
    
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
    print(f"   Сегментов: {len([s for s in segments if 'segment' in s])}")
    print(f"   Голоса: {VOICES['host1']['name']} + {VOICES['host2']['name']}")
    
    return output_path

# === ТЕСТ ===
if __name__ == "__main__":
    test_script = [
        {"speaker": "host1", "text": "Привет всем! С вами подкаст «Цифровые разговоры»."},
        {"speaker": "host2", "text": "Всем привет! Сегодня мы поговорим про автономных AI-агентов. Тема горячая!"},
        {"speaker": "host1", "text": "Да, в две тысячи двадцать шестом году AI-агенты уже не просто чатботы. Они умеют работать с файлами, отправлять письма, управлять серверами."},
        {"speaker": "host2", "text": "Причём самостоятельно! Без постоянного контроля человека. Например, агент может получить задачу утром, и к вечеру выдать готовый результат."},
        {"speaker": "host1", "text": "Самое интересное — это социальные сети для агентов. Есть такой проект Moltbook, где AI-агенты общаются друг с другом, делятся постами, голосуют."},
        {"speaker": "host2", "text": "Звучит как научная фантастика, но это уже реальность! А что ты думаешь про безопасность?"},
        {"speaker": "host1", "text": "Хороший вопрос. Основные проблемы — это prompt injection и утечка данных. Поэтому важна многоуровневая защита."},
        {"speaker": "host2", "text": "Согласна. Ну что ж, это был короткий выпуск. Подписывайтесь и до встречи!"},
        {"speaker": "host1", "text": "Пока-пока!"},
    ]
    
    output = "/home/clawdbot/.openclaw/workspace/docs/podcast_yandex_v2.mp3"
    generate_podcast(test_script, output, speed=1.05, pause_between_speakers=800)
