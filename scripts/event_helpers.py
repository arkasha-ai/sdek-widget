#!/usr/bin/env python3
"""
Event Logging Helpers
Decorators and context managers for easy event logging.
"""
import functools
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Dict, Any

# Import core logger
import sys
sys.path.insert(0, os.path.dirname(__file__))
from event_logger import log_event

# Get current session from environment (default: main)
CURRENT_SESSION = os.getenv('OPENCLAW_SESSION', 'main')


def get_session_id() -> str:
    """Get current session ID (from env or default)"""
    return CURRENT_SESSION


def set_session_id(session_id: str):
    """Set current session ID"""
    global CURRENT_SESSION
    CURRENT_SESSION = session_id
    os.environ['OPENCLAW_SESSION'] = session_id


def log_task(task_name: str = None):
    """
    Decorator: Auto-log task start/completion.
    
    Usage:
        @log_task("my_task")
        def do_something():
            ...
    """
    def decorator(func):
        task = task_name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            session = get_session_id()
            
            # Log task start
            log_event(session, "task_started", {
                "task": task,
                "function": func.__name__
            })
            
            try:
                result = func(*args, **kwargs)
                
                # Log task completion
                log_event(session, "task_completed", {
                    "task": task,
                    "outcome": "success"
                })
                
                return result
            
            except Exception as e:
                # Log task failure
                log_event(session, "task_failed", {
                    "task": task,
                    "error": str(e)
                })
                raise
        
        return wrapper
    return decorator


def log_decision(reasoning: str = None):
    """
    Decorator: Log important decisions.
    
    Usage:
        @log_decision("Chose approach X because Y")
        def decide_approach():
            return "approach_x"
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            session = get_session_id()
            log_event(session, "decision_made", {
                "decision": result,
                "function": func.__name__,
                "reasoning": reasoning or "See function implementation"
            })
            
            return result
        return wrapper
    return decorator


@contextmanager
def task_context(task_name: str, context: Optional[Dict[str, Any]] = None):
    """
    Context manager: Auto-log task lifecycle.
    
    Usage:
        with task_context("my_task", {"step": 1}):
            do_work()
    """
    session = get_session_id()
    
    # Start
    log_event(session, "task_started", {
        "task": task_name,
        **(context or {})
    })
    
    try:
        yield
        
        # Success
        log_event(session, "task_completed", {
            "task": task_name,
            "outcome": "success"
        })
    
    except Exception as e:
        # Failure
        log_event(session, "task_failed", {
            "task": task_name,
            "error": str(e)
        })
        raise


def quick_log(event_type: str, data: Dict[str, Any], session: str = None):
    """Quick event logging shortcut"""
    session = session or get_session_id()
    return log_event(session, event_type, data)


def log_file_change(file_path: str, change_type: str = "modified", details: str = None):
    """Log file change event"""
    session = get_session_id()
    log_event(session, f"file_{change_type}", {
        "file": file_path,
        "details": details
    })


def log_command(command: str, result: str = None, exit_code: int = None):
    """Log command execution"""
    session = get_session_id()
    log_event(session, "command_executed", {
        "command": command,
        "result": result,
        "exit_code": exit_code
    })


def log_api_call(api: str, endpoint: str, status: str = "success"):
    """Log API call"""
    session = get_session_id()
    log_event(session, "api_called", {
        "api": api,
        "endpoint": endpoint,
        "status": status
    })


# Example usage
if __name__ == "__main__":
    print("Event Helpers Demo\n")
    
    # Example 1: Task decorator
    @log_task("demo_task")
    def example_task():
        print("Doing work...")
        return "done"
    
    example_task()
    
    # Example 2: Context manager
    with task_context("demo_context", {"phase": "testing"}):
        print("Work inside context...")
    
    # Example 3: Quick shortcuts
    log_file_change("test.py", "modified", "Added function")
    log_command("git commit", "success", 0)
    log_api_call("github", "/repos/arkasha-ai", "success")
    
    print("\n✅ Demo complete! Check memory/events/main.jsonl")
