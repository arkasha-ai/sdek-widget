#!/usr/bin/env python3
"""
Import existing OpenClaw sessions into Personal Analytics
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter
import re

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config, load_data, save_data

def extract_topics(text):
    """Extract topics from text using keyword matching."""
    # Common topic keywords
    topics = []
    text_lower = text.lower()
    
    # Technical topics
    tech_keywords = {
        'python': 'Python',
        'docker': 'Docker',
        'kubernetes': 'Kubernetes',
        'typescript': 'TypeScript',
        'javascript': 'JavaScript',
        'react': 'React',
        'github': 'GitHub',
        'git': 'Git',
        'api': 'API',
        'database': 'Database',
        'sql': 'SQL',
        'redis': 'Redis',
        'nginx': 'Nginx',
        'heartbeat': 'Heartbeat',
        'cron': 'Cron',
        'telegram': 'Telegram',
        'skill': 'Skills',
        'agent': 'Agents',
        'openclaw': 'OpenClaw',
        'gateway': 'Gateway',
        'browser': 'Browser',
        'task': 'Tasks',
        'analytics': 'Analytics',
        'лекарства': 'Medication',
        'напоминание': 'Reminders',
        'здоровье': 'Health',
    }
    
    for keyword, topic in tech_keywords.items():
        if keyword in text_lower:
            topics.append(topic)
    
    return list(set(topics))  # Remove duplicates

def detect_sentiment(text):
    """Simple sentiment detection."""
    text_lower = text.lower()
    
    positive_words = ['отлично', 'хорошо', 'спасибо', '👍', '✅', 'perfect', 'great', 'good', 'thanks']
    negative_words = ['проблема', 'ошибка', 'не работает', 'сломан', '⚠️', '❌', 'bug', 'error', 'broken', 'failed']
    
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    if pos_count > neg_count * 1.5:
        return 'positive'
    elif neg_count > pos_count * 1.5:
        return 'negative'
    elif pos_count > 0 and neg_count > 0:
        return 'mixed'
    return 'neutral'

def detect_productivity(text):
    """Detect productivity markers."""
    text_lower = text.lower()
    
    markers = {
        'task_completed': ['исправил', 'готово', 'сделано', 'done', 'fixed', 'completed', 'resolved'],
        'decision_made': ['решил', 'выбрал', 'decided', 'chose'],
        'problem_solved': ['решил проблему', 'solved', 'figured out'],
    }
    
    score = 0
    for marker_type, keywords in markers.items():
        if any(kw in text_lower for kw in keywords):
            score += 0.3
    
    return min(score, 1.0)

def parse_transcript(jsonl_path):
    """Parse a JSONL transcript file. One file = one session with real timestamps."""
    session_start = None
    session_end = None
    all_messages = []
    session_id = jsonl_path.stem  # filename without extension

    with open(jsonl_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = entry.get('timestamp')

                # Use first entry timestamp as session start
                if ts and session_start is None:
                    session_start = ts

                # Track last timestamp as session end
                if ts:
                    session_end = ts

                # Collect text from messages
                if entry.get('type') == 'message':
                    msg = entry.get('message', {})
                    content_items = msg.get('content', [])
                    text = ''
                    for item in content_items:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text += item.get('text', '')
                        elif isinstance(item, str):
                            text += item
                    if text.strip():
                        all_messages.append(text)

            except json.JSONDecodeError:
                continue

    if not session_start or not all_messages:
        return []

    # Parse timestamps for duration
    try:
        start_dt = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(session_end.replace('Z', '+00:00'))
        duration_seconds = max(60, int((end_dt - start_dt).total_seconds()))
    except Exception:
        duration_seconds = 300  # default 5 min

    all_text = ' '.join(all_messages)

    session_data = {
        'id': session_id,
        'start': session_start,
        'end': session_end,
        'duration_seconds': duration_seconds,
        'channel': 'telegram',
        'topics': extract_topics(all_text)[:5],
        'sentiment': detect_sentiment(all_text),
        'productivity_score': detect_productivity(all_text),
        'tasks_completed': 1 if detect_productivity(all_text) > 0.5 else 0,
    }

    return [session_data]

def import_sessions():
    """Import existing sessions."""
    # Find JSONL transcripts in agents/main/sessions
    sessions_dir = Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions'
    
    # Also check workspace root
    workspace = Path.home() / '.openclaw' / 'workspace'
    
    transcripts = []
    if sessions_dir.exists():
        transcripts.extend(list(sessions_dir.glob('*.jsonl')))
    transcripts.extend(list(workspace.glob('*.jsonl')))
    
    if not transcripts:
        print("⚠️ No transcripts found")
        return
    
    print(f"🔍 Found {len(transcripts)} transcript(s)")
    
    # Load existing data
    data = load_data()
    existing_count = len(data.get('sessions', []))
    
    # Import each transcript
    all_sessions = []
    for transcript_path in transcripts:
        print(f"📄 Importing: {transcript_path.name}")
        try:
            sessions = parse_transcript(transcript_path)
            all_sessions.extend(sessions)
            print(f"  ✅ Extracted {len(sessions)} session(s)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    if not all_sessions:
        print("⚠️ No sessions extracted")
        return
    
    # Merge with existing data
    data['sessions'] = data.get('sessions', []) + all_sessions
    
    # Update topic stats
    topic_counter = Counter()
    for session in all_sessions:
        for topic in session.get('topics', []):
            topic_counter[topic] += 1
    
    topic_stats = data.get('topic_stats', {})
    for topic, count in topic_counter.items():
        if topic in topic_stats:
            topic_stats[topic]['total_mentions'] += count
        else:
            topic_stats[topic] = {
                'total_mentions': count,
                'last_seen': all_sessions[-1]['start'],
                'trend': 'new'
            }
    data['topic_stats'] = topic_stats
    
    # Update time stats
    time_stats = data.get('time_stats', {
        'hourly_distribution': {},
        'daily_distribution': {}
    })
    
    for session in all_sessions:
        start_dt = datetime.fromisoformat(session['start'])
        hour = start_dt.hour
        day = start_dt.strftime('%A').lower()
        
        time_stats['hourly_distribution'][str(hour)] = \
            time_stats['hourly_distribution'].get(str(hour), 0) + 1
        time_stats['daily_distribution'][day] = \
            time_stats['daily_distribution'].get(day, 0) + 1
    
    data['time_stats'] = time_stats
    
    # Update sentiment stats
    sentiment_stats = data.get('sentiment_stats', {
        'positive': 0,
        'neutral': 0,
        'negative': 0,
        'mixed': 0
    })
    
    for session in all_sessions:
        sentiment = session.get('sentiment', 'neutral')
        sentiment_stats[sentiment] = sentiment_stats.get(sentiment, 0) + 1
    
    data['sentiment_stats'] = sentiment_stats
    
    # Save data
    save_data(data)
    
    print(f"\n✅ Import complete!")
    print(f"   Sessions: {existing_count} → {len(data['sessions'])}")
    print(f"   Topics: {len(topic_stats)}")
    print(f"   New sessions: {len(all_sessions)}")

if __name__ == '__main__':
    import_sessions()
