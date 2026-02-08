#!/usr/bin/env python3
"""
Event Logger - Multi-Session Event Log System
Structured event logging for fast state recovery across parallel sessions.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

EVENTS_DIR = Path.home() / ".openclaw" / "workspace" / "memory" / "events"

# Ensure events directory exists
EVENTS_DIR.mkdir(parents=True, exist_ok=True)


def get_session_file(session_id: str) -> Path:
    """Get event log file path for session"""
    return EVENTS_DIR / f"{session_id}.jsonl"


def log_event(
    session_id: str,
    event_type: str,
    data: Dict[str, Any],
    tags: Optional[List[str]] = None,
    user_triggered: bool = False
) -> Dict[str, Any]:
    """
    Log an event to session stream.
    
    Args:
        session_id: Session identifier (e.g., "main", "discord-general")
        event_type: Event type (task_started, file_modified, etc.)
        data: Event-specific data
        tags: Optional tags for filtering
        user_triggered: True if triggered by user action
    
    Returns:
        The logged event with timestamp
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "type": event_type,
        "data": data
    }
    
    if tags:
        event["tags"] = tags
    
    if user_triggered:
        event["user_triggered"] = True
    
    # Append to session log
    log_file = get_session_file(session_id)
    with open(log_file, 'a') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
    
    return event


def get_recent_events(
    session_id: str,
    limit: int = 20,
    event_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recent events from session.
    
    Args:
        session_id: Session identifier
        limit: Maximum number of events to return
        event_type: Optional filter by event type
    
    Returns:
        List of recent events (newest first)
    """
    log_file = get_session_file(session_id)
    
    if not log_file.exists():
        return []
    
    events = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if event_type is None or event.get('type') == event_type:
                    events.append(event)
            except json.JSONDecodeError:
                continue
    
    # Return last N events, newest first
    return list(reversed(events[-limit:]))


def get_incomplete_tasks(session_id: str) -> List[Dict[str, Any]]:
    """
    Find tasks that were started but not completed.
    
    Returns:
        List of incomplete tasks with their start events
    """
    log_file = get_session_file(session_id)
    
    if not log_file.exists():
        return []
    
    started_tasks = {}  # task_id -> event
    completed_tasks = set()
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                event_type = event.get('type')
                task_id = event.get('data', {}).get('task')
                
                if event_type == 'task_started' and task_id:
                    started_tasks[task_id] = event
                elif event_type in ('task_completed', 'task_failed') and task_id:
                    completed_tasks.add(task_id)
            except json.JSONDecodeError:
                continue
    
    # Return tasks that were started but not completed
    incomplete = []
    for task_id, event in started_tasks.items():
        if task_id not in completed_tasks:
            incomplete.append(event)
    
    return incomplete


def get_session_state(session_id: str) -> Dict[str, Any]:
    """
    Get current state of session based on event log.
    
    Returns:
        Dictionary with:
        - active_tasks: List of incomplete tasks
        - last_event: Most recent event
        - last_action: Description of last action
        - event_count: Total events in session
    """
    log_file = get_session_file(session_id)
    
    if not log_file.exists():
        return {
            "active_tasks": [],
            "last_event": None,
            "last_action": "No events yet",
            "event_count": 0
        }
    
    # Count events
    event_count = 0
    last_event = None
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                event_count += 1
                last_event = event
            except json.JSONDecodeError:
                continue
    
    # Get incomplete tasks
    active_tasks = get_incomplete_tasks(session_id)
    
    # Format last action
    last_action = "Unknown"
    if last_event:
        event_type = last_event.get('type', 'unknown')
        data = last_event.get('data', {})
        
        if event_type == 'task_started':
            last_action = f"Started: {data.get('task', 'unknown')}"
        elif event_type == 'task_completed':
            last_action = f"Completed: {data.get('task', 'unknown')}"
        elif event_type == 'code_committed':
            last_action = f"Committed: {data.get('message', 'unknown')}"
        elif event_type == 'file_modified':
            last_action = f"Modified: {data.get('file', 'unknown')}"
        else:
            last_action = f"{event_type}: {str(data)[:50]}"
    
    return {
        "active_tasks": [t['data'].get('task') for t in active_tasks],
        "last_event": last_event,
        "last_action": last_action,
        "event_count": event_count
    }


def list_sessions() -> List[str]:
    """List all session IDs that have event logs"""
    if not EVENTS_DIR.exists():
        return []
    
    sessions = []
    for log_file in EVENTS_DIR.glob("*.jsonl"):
        sessions.append(log_file.stem)
    
    return sorted(sessions)


# CLI interface
def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  event_logger.py log <session> <type> <json_data>")
        print("  event_logger.py recent <session> [limit]")
        print("  event_logger.py state <session>")
        print("  event_logger.py incomplete <session>")
        print("  event_logger.py sessions")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "log":
        session = sys.argv[2]
        event_type = sys.argv[3]
        data = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        
        event = log_event(session, event_type, data)
        print(json.dumps(event, indent=2))
    
    elif command == "recent":
        session = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        
        events = get_recent_events(session, limit)
        print(json.dumps(events, indent=2, ensure_ascii=False))
    
    elif command == "state":
        session = sys.argv[2]
        
        state = get_session_state(session)
        print(json.dumps(state, indent=2, ensure_ascii=False))
    
    elif command == "incomplete":
        session = sys.argv[2]
        
        tasks = get_incomplete_tasks(session)
        print(json.dumps(tasks, indent=2, ensure_ascii=False))
    
    elif command == "sessions":
        sessions = list_sessions()
        print(json.dumps(sessions, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
