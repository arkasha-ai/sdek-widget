#!/usr/bin/env python3
"""
Podcast Generator - Edge TTS edition (Microsoft, полностью бесплатный)
Без API ключей, без лимитов.
"""

import os
import subprocess
import tempfile
import asyncio

# Голоса Edge TTS (бесплатные)
VOICES = {
    "host1": {"voice": "ru-RU-DmitryNeural", "rate": "+0%", "pitch": "+0Hz"},    # Мужской
    "host2": {"voice": "ru-RU-SvetlanaNeural", "rate": "+0%", "pitch": "+0Hz"},  # Женский
}

async def generate_segment_edge(text, voice_config, output_path):
    """Генерирует аудио через Edge TTS."""
    
    # Формируем команду edge-tts
    cmd = [
        "edge-tts",
        "--voice", voice_config["voice"],
        "--rate", voice_config.get("rate", "+0%"),
        "--pitch", voice_config.get("pitch", "+0Hz"),
        "--text", text,
        "--write-media", output_path
    ]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await proc.communicate()
    
    if proc.returncode != 0:
        raise Exception(f"Edge TTS error: {proc.returncode}")
    
    return output_path

async def generate_podcast_async(script, output_path, rate_adjust="+0%", pitch_adjust="+0Hz"):
    """
    Генерирует подкаст из скрипта (async версия).
    
    script = [
        {"speaker": "host1", "text": "Текст", "rate": "+10%", "pitch": "+5Hz"},  # rate/pitch опционально
        {"speaker": "host2", "text": "Текст"},
    ]
    """
    
    temp_dir = tempfile.mkdtemp(prefix="podcast_edge_")
    segments = []
    
    print("🎙️ Генерация подкаста через Edge TTS (бесплатно)...\n")
    
    # 1. Генерируем сегменты
    for i, line in enumerate(script):
        speaker = line["speaker"]
        text = line["text"]
        voice_config = VOICES.get(speaker, VOICES["host1"]).copy()
        
        # Можно переопределить rate и pitch для отдельных сегментов
        if "rate" in line:
            voice_config["rate"] = line["rate"]
        elif rate_adjust != "+0%":
            voice_config["rate"] = rate_adjust
            
        if "pitch" in line:
            voice_config["pitch"] = line["pitch"]
        elif pitch_adjust != "+0Hz":
            voice_config["pitch"] = pitch_adjust
        
        segment_path = os.path.join(temp_dir, f"segment_{i:04d}.mp3")
        
        print(f"  [{i+1}/{len(script)}] {speaker} ({voice_config['voice']}, rate: {voice_config['rate']}, pitch: {voice_config['pitch']}): {text[:50]}...")
        
        await generate_segment_edge(text, voice_config, segment_path)
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
    print(f"   TTS: Edge TTS (Microsoft, бесплатно)")
    print(f"   Голоса: Dmitry (муж.) + Svetlana (жен.)")
    
    return output_path

def generate_podcast(script, output_path, rate_adjust="+0%", pitch_adjust="+0Hz"):
    """Синхронная обёртка для async функции."""
    return asyncio.run(generate_podcast_async(script, output_path, rate_adjust, pitch_adjust))

# === ТЕСТ ===
if __name__ == "__main__":
    test_script = [
        {"speaker": "host1", "text": "Привет всем! С вами подкаст «Цифровые разговоры». Меня зовут Дмитрий."},
        {"speaker": "host2", "text": "А я Светлана! Сегодня мы поговорим про бесплатные TTS решения."},
        {"speaker": "host1", "text": "Edge TTS от Microsoft — это полностью бесплатное решение для синтеза речи."},
        {"speaker": "host2", "text": "Причём качество очень достойное! Давайте сравним с платными аналогами."},
    ]
    
    output = "/tmp/podcast_edge_test.mp3"
    generate_podcast(test_script, output)
