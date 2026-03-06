#!/usr/bin/env python3
"""
Podcast Generator v3 — Yandex SpeechKit API v3 gRPC edition
Поддерживает pitch_shift для управления высотой тона.
"""

import os
import subprocess
import tempfile
import grpc
import sys

# Добавляем путь к сгенерированным protobuf файлам
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/scripts'))

from yandex.cloud.ai.tts.v3 import tts_pb2, tts_service_pb2_grpc

# Загружаем API ключ
with open(os.path.expanduser('~/.openclaw/secrets.env')) as f:
    for line in f:
        if line.startswith('YANDEX_API_SECRET='):
            YANDEX_API_KEY = line.split('=', 1)[1].strip()
            break

# Голоса Yandex (конфигурация по умолчанию)
VOICES = {
    "host1": {"voice": "ermil", "emotion": "neutral", "pitch_shift": 30},   # Мужской, профессиональный
    "host2": {"voice": "alena", "emotion": "good", "pitch_shift": 20},      # Женский, приветливый
}

def generate_segment_yandex_v3(text, voice_config, output_path, speed=1.0, pitch_shift=None):
    """Генерирует аудио через Yandex SpeechKit API v3 gRPC."""
    
    # Используем pitch_shift из параметра или конфига
    final_pitch_shift = pitch_shift if pitch_shift is not None else voice_config.get("pitch_shift", 0)
    
    # Создаём gRPC канал
    channel = grpc.secure_channel(
        'tts.api.cloud.yandex.net:443',
        grpc.ssl_channel_credentials()
    )
    
    stub = tts_service_pb2_grpc.SynthesizerStub(channel)
    
    # Формируем запрос
    request = tts_pb2.UtteranceSynthesisRequest(
        text=text,
        output_audio_spec=tts_pb2.AudioFormatOptions(
            container_audio=tts_pb2.ContainerAudio(
                container_audio_type=tts_pb2.ContainerAudio.MP3
            )
        ),
        hints=[
            tts_pb2.Hints(voice=voice_config["voice"]),
            tts_pb2.Hints(speed=speed),
            tts_pb2.Hints(pitch_shift=final_pitch_shift),
        ],
        loudness_normalization_type=tts_pb2.LUFS,
        unsafe_mode=False
    )
    
    # Метаданные для авторизации
    metadata = [
        ('authorization', f'Api-Key {YANDEX_API_KEY}'),
    ]
    
    # Вызываем API (стриминг)
    audio_chunks = []
    try:
        for response in stub.UtteranceSynthesis(request, metadata=metadata):
            if response.audio_chunk:
                audio_chunks.append(response.audio_chunk.data)
    except grpc.RpcError as e:
        raise Exception(f"Yandex TTS gRPC error: {e.code()} {e.details()}")
    finally:
        channel.close()
    
    # Сохраняем в файл
    audio_data = b''.join(audio_chunks)
    with open(output_path, 'wb') as f:
        f.write(audio_data)
    
    return output_path

def generate_podcast(script, output_path, speed=1.0):
    """
    Генерирует подкаст из скрипта.
    
    script = [
        {"speaker": "host1", "text": "Текст", "pitch_shift": 50},  # pitch_shift опционально
        {"speaker": "host2", "text": "Текст"},
    ]
    """
    
    temp_dir = tempfile.mkdtemp(prefix="podcast_yandex_v3_")
    segments = []
    
    print("🎙️ Генерация подкаста через Yandex SpeechKit API v3...\n")
    
    # 1. Генерируем сегменты
    for i, line in enumerate(script):
        speaker = line["speaker"]
        text = line["text"]
        voice_config = VOICES.get(speaker, VOICES["host1"])
        
        # pitch_shift из скрипта или конфига
        pitch_shift = line.get("pitch_shift", voice_config.get("pitch_shift", 0))
        
        segment_path = os.path.join(temp_dir, f"segment_{i:04d}.mp3")
        
        print(f"  [{i+1}/{len(script)}] {speaker} ({voice_config['voice']}, pitch: {pitch_shift:+d} Hz): {text[:50]}...")
        
        generate_segment_yandex_v3(text, voice_config, segment_path, speed=speed, pitch_shift=pitch_shift)
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
    print(f"   API: v3 gRPC (с поддержкой pitch_shift)")
    
    return output_path

# === ТЕСТ ===
if __name__ == "__main__":
    test_script = [
        {"speaker": "host1", "text": "Привет! Меня зовут Филипп.", "pitch_shift": -50},  # Ниже
        {"speaker": "host2", "text": "А я Алёна! Сегодня тестируем pitch shift.", "pitch_shift": 50},  # Выше
        {"speaker": "host1", "text": "Это обычный голос без изменений.", "pitch_shift": 0},
        {"speaker": "host2", "text": "А это тоже без изменений."},
    ]
    
    output = "/tmp/podcast_v3_test.mp3"
    generate_podcast(test_script, output)
