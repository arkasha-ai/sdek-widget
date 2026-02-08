#!/usr/bin/env python3
"""
Advanced Event Visualization
Task graphs, heatmaps, and session comparisons.
"""
import sys
import os
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from event_logger import get_recent_events, list_sessions, get_session_state


def task_dependency_graph(session_id: str, limit: int = 50):
    """Show task dependencies and relationships"""
    events = get_recent_events(session_id, limit)
    
    tasks = {}
    current_task = None
    
    for event in reversed(events):
        etype = event['type']
        data = event.get('data', {})
        
        if etype == 'task_started':
            task = data.get('task')
            if task:
                current_task = task
                tasks[task] = {
                    'started': event['timestamp'],
                    'files': [],
                    'decisions': [],
                    'commands': [],
                    'status': 'in_progress'
                }
        
        elif etype == 'task_completed' and current_task:
            task = data.get('task')
            if task in tasks:
                tasks[task]['status'] = 'completed'
                tasks[task]['completed'] = event['timestamp']
        
        elif current_task and current_task in tasks:
            if etype == 'file_modified' or etype == 'file_created':
                tasks[current_task]['files'].append(data.get('file'))
            elif etype == 'decision_made':
                tasks[current_task]['decisions'].append(data.get('decision'))
            elif etype == 'command_executed':
                tasks[current_task]['commands'].append(data.get('command'))
    
    # Visualize
    print(f"\n📊 Task Dependency Graph: {session_id}\n")
    print("─" * 70)
    
    for task, info in tasks.items():
        status_icon = "✅" if info['status'] == 'completed' else "⚠️"
        print(f"\n{status_icon} {task}")
        
        if 'started' in info:
            ts = info['started'][11:19]
            print(f"   ├─ Started: {ts}")
        
        if 'completed' in info:
            ts = info['completed'][11:19]
            print(f"   ├─ Completed: {ts}")
        
        if info['files']:
            print(f"   ├─ Files ({len(info['files'])}):")
            for f in info['files'][:3]:
                print(f"   │  • {f}")
            if len(info['files']) > 3:
                print(f"   │  • ... +{len(info['files']) - 3} more")
        
        if info['decisions']:
            print(f"   ├─ Decisions ({len(info['decisions'])}):")
            for d in info['decisions'][:2]:
                print(f"   │  • {d[:50]}")
        
        if info['commands']:
            print(f"   └─ Commands ({len(info['commands'])}):")
            for c in info['commands'][:2]:
                print(f"      • {c[:50]}")
    
    print("\n" + "─" * 70)


def activity_heatmap(session_id: str, days: int = 7):
    """Show activity heatmap over time"""
    events = get_recent_events(session_id, limit=1000)
    
    # Group by hour
    hourly_counts = defaultdict(int)
    daily_counts = defaultdict(int)
    
    for event in events:
        try:
            ts = datetime.fromisoformat(event['timestamp'])
            hour_key = ts.strftime("%Y-%m-%d %H:00")
            day_key = ts.strftime("%Y-%m-%d")
            
            hourly_counts[hour_key] += 1
            daily_counts[day_key] += 1
        except:
            pass
    
    print(f"\n🔥 Activity Heatmap: {session_id}\n")
    print("─" * 70)
    
    # Daily summary
    print("\nDaily Activity:")
    for day in sorted(daily_counts.keys(), reverse=True)[:days]:
        count = daily_counts[day]
        bar = "█" * min(count // 2, 30)
        print(f"  {day}  {bar} {count}")
    
    # Hourly pattern (last 24h)
    print("\nHourly Pattern (Last 24h):")
    now = datetime.now()
    
    for i in range(24):
        hour = (now - timedelta(hours=23-i)).strftime("%Y-%m-%d %H:00")
        count = hourly_counts.get(hour, 0)
        
        if count > 0:
            bar = "▓" * min(count, 20)
            hour_label = hour.split()[1][:5]
            print(f"  {hour_label}  {bar} {count}")
    
    print("\n" + "─" * 70)


def session_comparison(sessions: list = None):
    """Compare multiple sessions side-by-side"""
    if not sessions:
        sessions = list_sessions()[:5]  # Top 5
    
    print(f"\n📈 Session Comparison\n")
    print("─" * 70)
    
    stats = []
    for session in sessions:
        state = get_session_state(session)
        events = get_recent_events(session, limit=100)
        
        # Analyze event types
        type_counts = defaultdict(int)
        for event in events:
            type_counts[event['type']] += 1
        
        stats.append({
            'session': session,
            'events': state['event_count'],
            'active_tasks': len(state['active_tasks']),
            'top_types': sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        })
    
    # Table header
    print(f"{'Session':<20} {'Events':<10} {'Active':<10} {'Top Activity'}")
    print("─" * 70)
    
    for s in stats:
        top_activity = ", ".join([f"{t[0]}({t[1]})" for t in s['top_types'][:2]])
        print(f"{s['session']:<20} {s['events']:<10} {s['active_tasks']:<10} {top_activity}")
    
    print("─" * 70)


def event_type_breakdown(session_id: str):
    """Show breakdown of event types"""
    events = get_recent_events(session_id, limit=1000)
    
    type_counts = defaultdict(int)
    for event in events:
        type_counts[event['type']] += 1
    
    total = sum(type_counts.values())
    
    print(f"\n📊 Event Type Breakdown: {session_id}\n")
    print("─" * 70)
    
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    
    for etype, count in sorted_types:
        percentage = (count / total * 100) if total > 0 else 0
        bar = "█" * int(percentage / 2)
        print(f"  {etype:<25} {bar:<25} {count:>4} ({percentage:>5.1f}%)")
    
    print("─" * 70)
    print(f"  Total: {total} events")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced event visualization')
    parser.add_argument('action', choices=['graph', 'heatmap', 'compare', 'breakdown'])
    parser.add_argument('--session', default='main', help='Session ID')
    parser.add_argument('--limit', type=int, default=50, help='Event limit')
    parser.add_argument('--days', type=int, default=7, help='Days for heatmap')
    parser.add_argument('--sessions', nargs='+', help='Sessions to compare')
    
    args = parser.parse_args()
    
    if args.action == 'graph':
        task_dependency_graph(args.session, args.limit)
    
    elif args.action == 'heatmap':
        activity_heatmap(args.session, args.days)
    
    elif args.action == 'compare':
        session_comparison(args.sessions)
    
    elif args.action == 'breakdown':
        event_type_breakdown(args.session)


if __name__ == "__main__":
    main()
