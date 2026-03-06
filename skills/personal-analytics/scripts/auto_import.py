#!/usr/bin/env python3
"""
Auto-import new sessions from OpenClaw transcripts
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from config import load_data, save_data
from import_existing import parse_transcript, extract_topics, detect_sentiment, detect_productivity
from collections import Counter

def get_last_import_time():
    """Get timestamp of last import."""
    data = load_data()
    return data.get('last_import', None)

def set_last_import_time(timestamp):
    """Save timestamp of last import."""
    data = load_data()
    data['last_import'] = timestamp
    save_data(data)

def import_new_sessions():
    """Import only new/modified sessions since last import."""
    sessions_dir = Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions'
    
    if not sessions_dir.exists():
        print("⚠️ Sessions directory not found")
        return
    
    last_import = get_last_import_time()
    last_import_dt = datetime.fromisoformat(last_import) if last_import else datetime(2000, 1, 1)
    
    # Find new/modified transcripts
    new_transcripts = []
    for transcript in sessions_dir.glob('*.jsonl'):
        mtime = datetime.fromtimestamp(transcript.stat().st_mtime)
        if mtime > last_import_dt:
            new_transcripts.append(transcript)
    
    if not new_transcripts:
        print("✅ No new sessions to import")
        return
    
    print(f"🔍 Found {len(new_transcripts)} new/modified transcript(s)")
    
    # Load existing data
    data = load_data()
    existing_ids = {s['id'] for s in data.get('sessions', [])}
    
    # Import new sessions
    all_new_sessions = []
    for transcript_path in new_transcripts:
        try:
            sessions = parse_transcript(transcript_path)
            # Filter out already imported sessions
            new_sessions = [s for s in sessions if s['id'] not in existing_ids]
            if new_sessions:
                all_new_sessions.extend(new_sessions)
                print(f"  ✅ {transcript_path.name}: {len(new_sessions)} new session(s)")
        except Exception as e:
            print(f"  ❌ {transcript_path.name}: {e}")
    
    if not all_new_sessions:
        print("✅ No new sessions found")
        set_last_import_time(datetime.now().isoformat())
        return
    
    # Merge with existing data
    data['sessions'] = data.get('sessions', []) + all_new_sessions
    
    # Update topic stats
    topic_counter = Counter()
    for session in all_new_sessions:
        for topic in session.get('topics', []):
            topic_counter[topic] += 1
    
    topic_stats = data.get('topic_stats', {})
    for topic, count in topic_counter.items():
        if topic in topic_stats:
            topic_stats[topic]['total_mentions'] += count
            topic_stats[topic]['last_seen'] = all_new_sessions[-1]['start']
        else:
            topic_stats[topic] = {
                'total_mentions': count,
                'last_seen': all_new_sessions[-1]['start'],
                'trend': 'new'
            }
    data['topic_stats'] = topic_stats
    
    # Update time/sentiment stats
    time_stats = data.get('time_stats', {
        'hourly_distribution': {},
        'daily_distribution': {}
    })
    
    sentiment_stats = data.get('sentiment_stats', {
        'positive': 0, 'neutral': 0, 'negative': 0, 'mixed': 0
    })
    
    for session in all_new_sessions:
        start_dt = datetime.fromisoformat(session['start'])
        hour = start_dt.hour
        day = start_dt.strftime('%A').lower()
        
        time_stats['hourly_distribution'][str(hour)] = \
            time_stats['hourly_distribution'].get(str(hour), 0) + 1
        time_stats['daily_distribution'][day] = \
            time_stats['daily_distribution'].get(day, 0) + 1
        
        sentiment = session.get('sentiment', 'neutral')
        sentiment_stats[sentiment] = sentiment_stats.get(sentiment, 0) + 1
    
    data['time_stats'] = time_stats
    data['sentiment_stats'] = sentiment_stats
    
    # Save
    save_data(data)
    set_last_import_time(datetime.now().isoformat())
    
    print(f"\n✅ Import complete! Added {len(all_new_sessions)} new session(s)")
    print(f"   Total sessions: {len(data['sessions'])}")
    print(f"   Total topics: {len(topic_stats)}")

if __name__ == '__main__':
    import_new_sessions()
