#!/usr/bin/env python3
"""Генерация примеров голосов Yandex SpeechKit"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/scripts'))

import grpc
from yandex.cloud.ai.tts.v3 import tts_pb2, tts_service_pb2_grpc

with open(os.path.expanduser('~/.openclaw/secrets.env')) as f:
    for line in f:
        if line.startswith('YANDEX_API_SECRET='):
            YANDEX_API_KEY = line.split('=', 1)[1].strip()
            break

SAMPLE_TEXT = "Привет! Это профессиональная озвучка от Яндекс. Готов озвучить ваш текст."

VOICES = [
    ("ermil",   "neutral", "Мужской - Эрмил"),
    ("filipp",  "neutral", "Мужской - Филипп"),
    ("zahar",   "good",    "Мужской - Захар"),
    ("alena",   "good",    "Женский - Алёна"),
    ("jane",    "good",    "Женский - Джейн"),
    ("oksana",  "good",    "Женский - Оксана"),
]

def generate(text, voice, emotion, output_path):
    channel = grpc.secure_channel('tts.api.cloud.yandex.net:443', grpc.ssl_channel_credentials())
    stub = tts_service_pb2_grpc.SynthesizerStub(channel)
    hints = [tts_pb2.Hints(voice=voice), tts_pb2.Hints(speed=1.0)]
    request = tts_pb2.UtteranceSynthesisRequest(
        text=text,
        output_audio_spec=tts_pb2.AudioFormatOptions(
            container_audio=tts_pb2.ContainerAudio(
                container_audio_type=tts_pb2.ContainerAudio.MP3
            )
        ),
        hints=hints,
        loudness_normalization_type=tts_pb2.LUFS,
    )
    metadata = [('authorization', f'Api-Key {YANDEX_API_KEY}')]
    chunks = []
    for resp in stub.UtteranceSynthesis(request, metadata=metadata):
        if resp.audio_chunk:
            chunks.append(resp.audio_chunk.data)
    channel.close()
    with open(output_path, 'wb') as f:
        f.write(b''.join(chunks))

for voice, emotion, label in VOICES:
    path = f"/home/clawdbot/.openclaw/workspace/drafts/sample_{voice}.mp3"
    try:
        generate(SAMPLE_TEXT, voice, emotion, path)
        print(f"OK: {label} -> {path}")
    except Exception as e:
        print(f"ERR: {label}: {e}")
