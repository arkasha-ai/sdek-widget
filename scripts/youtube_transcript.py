#!/usr/bin/env python3
"""
YouTube Transcript Extractor
Получает транскрипцию видео с YouTube используя автоматические субтитры
"""
import subprocess
import sys
import re
import os
import tempfile


def extract_video_id(url):
    """Извлечь video ID из YouTube URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\?/]+)',
        r'youtube\.com/shorts/([^&\?/]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url  # Может быть уже ID


def get_transcript(video_url, lang='ru'):
    """Получить транскрипцию видео"""
    video_id = extract_video_id(video_url)
    
    # Создать временную директорию
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'transcript.srt')
        
        # Скачать субтитры
        cmd = [
            os.path.expanduser('~/.local/bin/yt-dlp'),
            '--skip-download',
            '--write-auto-sub',
            '--sub-lang', lang,
            '--sub-format', 'srt',
            '--convert-subs', 'srt',
            '-o', output_path,
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Найти файл с субтитрами
        srt_file = None
        for file in os.listdir(tmpdir):
            if file.endswith('.srt'):
                srt_file = os.path.join(tmpdir, file)
                break
        
        if not srt_file or not os.path.exists(srt_file):
            # Попробовать английский, если русского нет
            if lang == 'ru':
                return get_transcript(video_url, lang='en')
            raise Exception(f"Субтитры не найдены. Вывод yt-dlp:\n{result.stderr}")
        
        # Прочитать и очистить субтитры
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Удалить номера строк и тайминги из SRT формата
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            # Пропустить пустые строки, номера и тайминги
            if not line or line.isdigit() or '-->' in line:
                continue
            # Удалить HTML теги
            line = re.sub(r'<[^>]+>', '', line)
            if line:
                lines.append(line)
        
        return ' '.join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: youtube_transcript.py <youtube_url> [lang]")
        sys.exit(1)
    
    url = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else 'ru'
    
    try:
        transcript = get_transcript(url, lang)
        print(transcript)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
