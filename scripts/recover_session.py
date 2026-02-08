#!/usr/bin/env python3
"""
Session Recovery Helper
Fast state recovery and context reconstruction.
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from event_logger import (
    get_session_state,
    get_incomplete_tasks,
    get_recent_events,
    list_sessions
)

def format_time_ago(timestamp_str: str) -> str:
    """Format timestamp as 'X minutes/hours ago'"""
    try:
        ts = datetime.fromisoformat(timestamp_str)
        now = datetime.now(ts.tzinfo)
        delta = now - ts
        
        if delta.total_seconds() < 60:
            return "just now"
        elif delta.total_seconds() < 3600:
            mins = int(delta.total_seconds() / 60)
            return f"{mins}m ago"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            days = int(delta.total_seconds() / 86400)
            return f"{days}d ago"
    except:
        return "unknown"


def recover_session(session_id: str, verbose: bool = False):
    """
    Recover session state and provide actionable summary.
    
    Returns:
        dict with recovery info
    """
    state = get_session_state(session_id)
    incomplete = get_incomplete_tasks(session_id)
    recent = get_recent_events(session_id, limit=20)
    
    # Analyze recent events
    events_today = []
    events_last_hour = []
    now = datetime.now()
    
    for event in recent:
        try:
            ts = datetime.fromisoformat(event['timestamp'])
            delta = now - ts.replace(tzinfo=None)
            
            if delta.total_seconds() < 86400:  # Today
                events_today.append(event)
            if delta.total_seconds() < 3600:  # Last hour
                events_last_hour.append(event)
        except:
            pass
    
    # Build recovery summary
    recovery = {
        "session_id": session_id,
        "total_events": state['event_count'],
        "active_tasks": state['active_tasks'],
        "last_action": state['last_action'],
        "last_event": state['last_event'],
        "incomplete_tasks": incomplete,
        "events_today": len(events_today),
        "events_last_hour": len(events_last_hour),
        "recent_events": recent[:10]
    }
    
    return recovery


def print_recovery_report(session_id: str):
    """Print human-readable recovery report"""
    recovery = recover_session(session_id)
    
    print("=" * 70)
    print(f"SESSION RECOVERY: {session_id}")
    print("=" * 70)
    
    # Basic stats
    print(f"\n📊 Stats:")
    print(f"   Total events: {recovery['total_events']}")
    print(f"   Events today: {recovery['events_today']}")
    print(f"   Events last hour: {recovery['events_last_hour']}")
    
    # Last activity
    if recovery['last_event']:
        ts = recovery['last_event'].get('timestamp', '')
        time_ago = format_time_ago(ts)
        print(f"\n⏱️  Last activity: {time_ago}")
        print(f"   {recovery['last_action']}")
    
    # Active/incomplete tasks
    if recovery['active_tasks']:
        print(f"\n⚠️  Active tasks ({len(recovery['active_tasks'])}):")
        for task in recovery['active_tasks']:
            print(f"   • {task}")
        
        # Show task details
        print(f"\n📋 Task details:")
        for task_event in recovery['incomplete_tasks']:
            task_name = task_event['data'].get('task')
            context = task_event['data'].get('context', 'N/A')
            started = format_time_ago(task_event['timestamp'])
            print(f"\n   {task_name}:")
            print(f"      Started: {started}")
            print(f"      Context: {context}")
    else:
        print(f"\n✅ No active tasks - clean state")
    
    # Recent activity summary
    if recovery['recent_events']:
        print(f"\n📝 Recent activity (last 10 events):")
        for event in recovery['recent_events']:
            ts = event['timestamp'][11:19]  # HH:MM:SS
            etype = event['type']
            
            # Extract relevant data
            data = event.get('data', {})
            detail = (
                data.get('task') or 
                data.get('file') or 
                data.get('command', '')[:30] or
                str(data)[:30]
            )
            
            print(f"   {ts} | {etype:20s} | {detail}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if recovery['active_tasks']:
        print(f"   → Resume incomplete work")
    if recovery['events_last_hour'] > 0:
        print(f"   → Check recent events for context")
    if recovery['total_events'] == 0:
        print(f"   → Fresh session - no prior state")
    else:
        print(f"   → Use get_recent_events() for detailed context")
    
    print("\n" + "=" * 70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Session recovery helper')
    parser.add_argument('session', nargs='?', help='Session ID (default: list all)')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not args.session:
        # List all sessions
        sessions = list_sessions()
        print("Available sessions:")
        for session in sessions:
            state = get_session_state(session)
            print(f"  • {session:20s} ({state['event_count']} events, {len(state['active_tasks'])} active)")
        sys.exit(0)
    
    if args.json:
        import json
        recovery = recover_session(args.session, args.verbose)
        print(json.dumps(recovery, indent=2, ensure_ascii=False))
    else:
        print_recovery_report(args.session)


if __name__ == "__main__":
    main()
