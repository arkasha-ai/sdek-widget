#!/usr/bin/env python3
"""
Advanced Event Search
Cross-session queries, pattern detection, and semantic search.
"""
import sys
import os
import json
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from event_logger import get_recent_events, list_sessions


def cross_session_search(query: str, sessions: list = None, limit_per_session: int = 50):
    """Search across multiple sessions"""
    if not sessions:
        sessions = list_sessions()
    
    results = []
    
    for session in sessions:
        events = get_recent_events(session, limit_per_session)
        
        for event in events:
            # Search in event type and data
            match = False
            
            if query.lower() in event['type'].lower():
                match = True
            
            data_str = json.dumps(event.get('data', {})).lower()
            if query.lower() in data_str:
                match = True
            
            if match:
                results.append({
                    'session': session,
                    'event': event
                })
    
    return results


def pattern_detection(session_id: str = None, pattern_type: str = 'all'):
    """Detect patterns in events"""
    sessions = [session_id] if session_id else list_sessions()
    
    patterns = {
        'frequent_errors': defaultdict(int),
        'task_chains': [],
        'time_patterns': defaultdict(list),
        'rapid_switches': []
    }
    
    for session in sessions:
        events = get_recent_events(session, limit=200)
        
        prev_event = None
        task_chain = []
        
        for event in events:
            etype = event['type']
            ts = datetime.fromisoformat(event['timestamp'])
            hour = ts.hour
            
            # Error patterns
            if 'error' in etype or 'failed' in etype:
                error_detail = event.get('data', {}).get('error', 'unknown')
                patterns['frequent_errors'][error_detail] += 1
            
            # Task chains
            if etype == 'task_started':
                task = event['data'].get('task')
                task_chain.append(task)
            elif etype == 'task_completed' and task_chain:
                patterns['task_chains'].append(list(task_chain))
                task_chain = []
            
            # Time patterns
            patterns['time_patterns'][hour].append(etype)
            
            # Rapid context switches
            if prev_event and etype == 'context_switched':
                time_diff = (ts - datetime.fromisoformat(prev_event['timestamp'])).total_seconds()
                if time_diff < 60:  # Less than 1 minute
                    patterns['rapid_switches'].append({
                        'session': session,
                        'time': ts.isoformat(),
                        'interval': time_diff
                    })
            
            prev_event = event
    
    return patterns


def semantic_event_search(query: str, limit: int = 10):
    """Search events using semantic similarity (via Qdrant)"""
    try:
        # Import qdrant indexer for semantic search
        from qdrant_indexer import search
        
        # Search with event type filter
        results = search(query, limit=limit, filter_type='event')
        return results
    
    except Exception as e:
        print(f"Semantic search not available: {e}", file=sys.stderr)
        print("Run: ./scripts/qdrant index-events", file=sys.stderr)
        return []


def time_range_search(session_id: str, start_time: str, end_time: str):
    """Search events within time range"""
    events = get_recent_events(session_id, limit=1000)
    
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)
    
    filtered = []
    for event in events:
        try:
            ts = datetime.fromisoformat(event['timestamp'])
            if start_dt <= ts <= end_dt:
                filtered.append(event)
        except:
            pass
    
    return filtered


def find_related_events(event_id: str, session_id: str, context_window: int = 5):
    """Find events related to a specific event"""
    events = get_recent_events(session_id, limit=200)
    
    # Find target event
    target_idx = None
    for i, event in enumerate(events):
        if event['timestamp'] == event_id:
            target_idx = i
            break
    
    if target_idx is None:
        return []
    
    # Get surrounding events
    start_idx = max(0, target_idx - context_window)
    end_idx = min(len(events), target_idx + context_window + 1)
    
    return events[start_idx:end_idx]


def visualize_search_results(results: list, max_results: int = 10):
    """Pretty print search results"""
    print(f"\n🔍 Search Results ({len(results)} found, showing {min(len(results), max_results)})\n")
    print("─" * 70)
    
    for i, result in enumerate(results[:max_results]):
        session = result.get('session', 'unknown')
        event = result.get('event', result)  # Handle both formats
        
        ts = event.get('timestamp', '')[:19]
        etype = event.get('type', 'unknown')
        data = event.get('data', {})
        
        # Extract key info
        key_info = (
            data.get('task') or 
            data.get('file') or 
            data.get('decision', '')[:40] or
            str(data)[:40]
        )
        
        print(f"{i+1}. [{session}] {ts}")
        print(f"   Type: {etype}")
        print(f"   Data: {key_info}")
        
        if 'score' in result:
            print(f"   Score: {result['score']:.2f}")
        
        print()
    
    if len(results) > max_results:
        print(f"... and {len(results) - max_results} more results")
    
    print("─" * 70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced event search')
    parser.add_argument('action', choices=['search', 'patterns', 'semantic', 'time-range'])
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('--session', help='Session ID')
    parser.add_argument('--sessions', nargs='+', help='Multiple sessions')
    parser.add_argument('--limit', type=int, default=10, help='Result limit')
    parser.add_argument('--start', help='Start time (ISO format)')
    parser.add_argument('--end', help='End time (ISO format)')
    parser.add_argument('--pattern-type', default='all', help='Pattern type')
    
    args = parser.parse_args()
    
    if args.action == 'search':
        if not args.query:
            print("Error: query required")
            sys.exit(1)
        
        results = cross_session_search(args.query, args.sessions)
        visualize_search_results(results, args.limit)
    
    elif args.action == 'patterns':
        patterns = pattern_detection(args.session, args.pattern_type)
        
        print("\n🔍 Pattern Detection\n")
        print("─" * 70)
        
        if patterns['frequent_errors']:
            print("\n❌ Frequent Errors:")
            for error, count in sorted(patterns['frequent_errors'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   • {error[:50]} ({count}x)")
        
        if patterns['task_chains']:
            print("\n🔗 Task Chains (recent):")
            for chain in patterns['task_chains'][-5:]:
                print(f"   • {' → '.join(chain)}")
        
        if patterns['time_patterns']:
            print("\n⏰ Hourly Activity:")
            hourly_counts = {h: len(events) for h, events in patterns['time_patterns'].items()}
            for hour in sorted(hourly_counts.keys()):
                count = hourly_counts[hour]
                bar = "█" * min(count // 2, 20)
                print(f"   {hour:02d}:00  {bar} {count}")
        
        if patterns['rapid_switches']:
            print(f"\n⚡ Rapid Context Switches ({len(patterns['rapid_switches'])}):")
            for switch in patterns['rapid_switches'][-3:]:
                print(f"   • {switch['time'][11:19]} ({switch['interval']:.1f}s)")
        
        print("\n" + "─" * 70)
    
    elif args.action == 'semantic':
        if not args.query:
            print("Error: query required")
            sys.exit(1)
        
        results = semantic_event_search(args.query, args.limit)
        if results:
            visualize_search_results(results, args.limit)
        else:
            print("No results or semantic search not available")
    
    elif args.action == 'time-range':
        if not args.session or not args.start or not args.end:
            print("Error: --session, --start, and --end required")
            sys.exit(1)
        
        results = time_range_search(args.session, args.start, args.end)
        visualize_search_results([{'session': args.session, 'event': e} for e in results], args.limit)


if __name__ == "__main__":
    main()
