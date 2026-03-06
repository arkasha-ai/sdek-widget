#!/usr/bin/env python3
"""
Podcast Generator v1 — генерация подкастов с двумя ведущими.
Использует Edge TTS для озвучки и ffmpeg для сборки.
"""

import asyncio
import json
import os
import tempfile
import subprocess

# Голоса
VOICES = {
    "host1": "ru-RU-DmitryNeural",    # Мужской — основной ведущий
    "host2": "ru-RU-SvetlanaNeural",   # Женский — со-ведущая
    # Английские альтернативы:
    # "host1": "en-US-AndrewMultilingualNeural",  # Warm, Confident
    # "host2": "en-US-EmmaMultilingualNeural",     # Cheerful, Conversational
}

async def generate_segment(text, voice, output_path, rate="+0%"):
    """Генерирует аудио-сегмент через Edge TTS."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path

async def generate_podcast(script, output_path, lang="ru"):
    """
    Генерирует подкаст из скрипта.
    
    script = [
        {"speaker": "host1", "text": "Привет! Добро пожаловать в наш подкаст!"},
        {"speaker": "host2", "text": "Да, сегодня мы обсудим..."},
        ...
    ]
    """
    
    temp_dir = tempfile.mkdtemp(prefix="podcast_")
    segments = []
    
    # 1. Генерируем каждый сегмент
    for i, line in enumerate(script):
        speaker = line["speaker"]
        text = line["text"]
        voice = VOICES.get(speaker, VOICES["host1"])
        
        segment_path = os.path.join(temp_dir, f"segment_{i:04d}.mp3")
        print(f"  [{i+1}/{len(script)}] {speaker}: {text[:50]}...")
        await generate_segment(text, voice, segment_path)
        segments.append(segment_path)
    
    # 2. Создаём файл-список для ffmpeg
    list_path = os.path.join(temp_dir, "segments.txt")
    with open(list_path, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
    
    # 3. Склеиваем через ffmpeg
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
    
    # 4. Получаем длительность
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", output_path],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
    
    # 5. Чистим temp
    for seg in segments:
        os.remove(seg)
    os.remove(list_path)
    os.rmdir(temp_dir)
    
    print(f"\n✅ Подкаст готов: {output_path}")
    print(f"   Длительность: {int(duration//60)}:{int(duration%60):02d}")
    print(f"   Сегментов: {len(segments)}")
    
    return output_path


# === ТЕСТ ===
if __name__ == "__main__":
    # Мини-подкаст про AI-агентов
    test_script = [
        {"speaker": "host1", "text": "Привет всем! С вами подкаст «Цифровые разговоры». Я Дмитрий."},
        {"speaker": "host2", "text": "А я Светлана! Сегодня мы поговорим про автономных AI-агентов. Тема горячая!"},
        {"speaker": "host1", "text": "Да, в две тысячи двадцать шестом году AI-агенты уже не просто чатботы. Они умеют работать с файлами, отправлять письма, управлять серверами."},
        {"speaker": "host2", "text": "Причём самостоятельно! Без постоянного контроля человека. Например, агент может получить задачу утром, и к вечеру выдать готовый результат."},
        {"speaker": "host1", "text": "Самое интересное — это социальные сети для агентов. Есть такой проект Moltbook, где AI-агенты общаются друг с другом, делятся постами, голосуют."},
        {"speaker": "host2", "text": "Звучит как научная фантастика, но это уже реальность! А что ты думаешь про безопасность?"},
        {"speaker": "host1", "text": "Хороший вопрос. Основные проблемы — это prompt injection и утечка данных. Поэтому важна многоуровневая защита."},
        {"speaker": "host2", "text": "Согласна. Ну что ж, это был короткий выпуск. Подписывайтесь и до встречи!"},
        {"speaker": "host1", "text": "Пока-пока!"},
    ]
    
    output = "/home/clawdbot/.openclaw/workspace/docs/test_podcast.mp3"
    asyncio.run(generate_podcast(test_script, output))
