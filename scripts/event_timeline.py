#!/usr/bin/env python3
"""Event Timeline Visualizer"""
import sys
sys.path.insert(0, '/home/clawdbot/.openclaw/workspace/scripts')
from event_logger import get_recent_events
from datetime import datetime

def timeline(session_id: str, limit: int = 20):
    """Show visual timeline of events"""
    events = get_recent_events(session_id, limit)
    
    if not events:
        print(f"No events in session: {session_id}")
        return
    
    print(f"\n📅 Timeline: {session_id} (last {len(events)} events)\n")
    print("─" * 70)
    
    prev_hour = None
    for event in reversed(events):  # Oldest first
        ts = datetime.fromisoformat(event['timestamp'])
        time_str = ts.strftime("%H:%M:%S")
        hour = ts.hour
        
        # Hour separator
        if prev_hour is not None and hour != prev_hour:
            print("─" * 70)
        prev_hour = hour
        
        # Event icon
        etype = event['type']
        icons = {
            'task_started': '🟢',
            'task_completed': '✅',
            'task_failed': '❌',
            'task_paused': '⏸️',
            'file_created': '📄',
            'file_modified': '✏️',
            'code_committed': '💾',
            'decision_made': '🎯',
            'message_received': '📨',
            'message_sent': '📤',
        }
        icon = icons.get(etype, '▪️')
        
        # Extract detail
        data = event.get('data', {})
        detail = (
            data.get('task') or 
            data.get('file') or 
            data.get('decision', '')[:40] or
            str(data)[:40]
        )
        
        print(f"{time_str} {icon} {etype:20s} │ {detail}")
    
    print("─" * 70 + "\n")

if __name__ == "__main__":
    session = sys.argv[1] if len(sys.argv) > 1 else "main"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    timeline(session, limit)
