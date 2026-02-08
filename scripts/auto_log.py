#!/usr/bin/env python3
"""
Auto-logging wrapper functions
Use these instead of direct tool calls to get automatic event logging.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from session_manager import auto_log_message, get_or_create_session
from event_helpers import log_command, log_api_call, log_file_change


def message_received(content: str, from_user: str = None, chat: str = None):
    """Log incoming message (call this when processing user message)"""
    session = get_or_create_session(chat)
    
    metadata = {}
    if from_user:
        metadata['from'] = from_user
    if chat:
        metadata['chat'] = chat
    
    auto_log_message('received', content, metadata)


def message_sent(content: str, to: str = None):
    """Log outgoing message (call this after sending reply)"""
    metadata = {}
    if to:
        metadata['to'] = to
    
    auto_log_message('sent', content, metadata)


def wrap_exec(command: str, **kwargs):
    """Wrapper for exec tool with auto-logging"""
    # Log command execution
    log_command(command, "executing")
    
    # Here you would call actual exec tool
    # For now, just log
    print(f"[AUTO-LOG] Would execute: {command}")
    
    # Log result (in real usage, capture from exec result)
    # log_command(command, "success", 0)


def wrap_file_operation(operation: str, file_path: str, details: str = None):
    """Wrapper for file operations with auto-logging"""
    log_file_change(file_path, operation, details)


def wrap_api_call(api: str, endpoint: str, **kwargs):
    """Wrapper for API calls with auto-logging"""
    log_api_call(api, endpoint, "calling")
    
    # Here you would call actual API
    # For now, just log
    print(f"[AUTO-LOG] Would call: {api}/{endpoint}")
    
    # Log result (in real usage, capture from API response)
    # log_api_call(api, endpoint, "success")


# Export shortcuts
__all__ = [
    'message_received',
    'message_sent',
    'wrap_exec',
    'wrap_file_operation',
    'wrap_api_call'
]


if __name__ == "__main__":
    # Demo
    print("Auto-logging Demo\n")
    
    # Simulate message flow
    message_received("Hey, can you help?", from_user="Denis", chat="main")
    message_sent("Sure! What do you need?", to="Denis")
    
    # Simulate operations
    wrap_file_operation("modified", "test.py", "Added logging")
    wrap_exec("git commit -m 'Update'")
    wrap_api_call("github", "/repos/arkasha-ai")
    
    print("\n✅ Auto-logging demo complete")
    
    # Show results
    from event_logger import get_recent_events
    events = get_recent_events("main", limit=5)
    print(f"\nLogged {len(events)} events in main session")
