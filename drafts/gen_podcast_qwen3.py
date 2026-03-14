#!/usr/bin/env python3
"""Генерация подкаста через Qwen3 TTS API"""
import urllib.parse
import urllib.request
import subprocess
import os

API = "http://109.194.141.123:7860"
OUT = "/home/clawdbot/.openclaw/workspace/drafts"

SCRIPT = [
    ("denis",  "Юлия, привет! Сегодня мы поговорим о родительстве. Ты уже давно в этой роли — с чего всё началось?"),
    ("yulia",  "Привет, Денис! Ну, когда родился первый ребёнок, я думала что всё знаю. Оказалось — не знаю вообще ничего. Это было честное открытие!"),
    ("denis",  "Да, мне кажется это универсальная история. Все книжки, советы — и всё равно первые месяцы как в тумане."),
    ("yulia",  "Именно! И самое главное что я поняла — не надо бояться ошибаться. Дети не такие хрупкие, как мы думаем. Они очень живучие."),
    ("denis",  "А что тебе помогало не сойти с ума в трудные моменты? Лично мне — юмор. Если не смеяться, то плакать."),
    ("yulia",  "Юмор — это да. И ещё поддержка партнёра. Когда понимаешь что вы команда, а не каждый сам по себе — становится намного легче."),
    ("denis",  "Золотые слова. Я думаю самое ценное в родительстве — это не вырастить идеального ребёнка, а вырасти самому."),
    ("yulia",  "Подписываюсь под каждым словом. Дети — лучшие учителя в жизни. Спасибо за разговор, Денис!"),
    ("denis",  "И тебе спасибо, Юлия! До следующего выпуска!"),
]

def synthesize(text, voice, out_path):
    encoded = urllib.parse.quote(text)
    url = f"{API}/synthesize_speech/?text={encoded}&voice={voice}&speed=1.0"
    urllib.request.urlretrieve(url, out_path)
    print(f"  OK: {voice}: {text[:50]}...")

# Генерируем каждую реплику
segments = []
for i, (voice, text) in enumerate(SCRIPT):
    path = f"{OUT}/podcast_seg_{i:02d}_{voice}.wav"
    synthesize(text, voice, path)
    segments.append(path)

# Создаём файл со списком для ffmpeg (с паузами)
silence_path = f"{OUT}/podcast_silence.wav"
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi",
    "-i", "anullsrc=r=24000:cl=mono",
    "-t", "0.7",
    "-acodec", "pcm_s16le",
    silence_path
], check=True, capture_output=True)

# Строим список с паузами между репликами
concat_list = f"{OUT}/podcast_concat.txt"
with open(concat_list, "w") as f:
    for i, seg in enumerate(segments):
        f.write(f"file '{seg}'\n")
        if i < len(segments) - 1:
            f.write(f"file '{silence_path}'\n")

# Склеиваем
output = f"{OUT}/podcast_roditelstvo.mp3"
subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", concat_list,
    "-acodec", "libmp3lame", "-q:a", "2",
    output
], check=True, capture_output=True)

print(f"\nГотово! {output}")
