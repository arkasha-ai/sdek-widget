#!/usr/bin/env python3
"""
Session Manager - Auto-detect and manage sessions
"""
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))
from event_logger import log_event
from event_helpers import set_session_id, get_session_id

# Session mapping rules
SESSION_PATTERNS = {
    'main': ['main', 'telegram:364935958'],
    'discord-general': ['discord', 'general'],
    'backend-release': ['backend', 'release'],
}


def detect_session_from_context() -> str:
    """
    Detect current session from environment/context.
    
    Tries multiple sources:
    1. OPENCLAW_SESSION env var (explicit)
    2. Current working directory
    3. Process context
    4. Default: 'main'
    """
    # 1. Check explicit env var
    if 'OPENCLAW_SESSION' in os.environ:
        return os.environ['OPENCLAW_SESSION']
    
    # 2. Check for session indicators in env
    # OpenClaw might set these (check if available)
    session_hints = [
        os.getenv('OPENCLAW_CHANNEL'),
        os.getenv('OPENCLAW_CHAT'),
        os.getenv('SESSION_ID'),
    ]
    
    for hint in session_hints:
        if hint:
            return normalize_session_id(hint)
    
    # 3. Default to main
    return 'main'


def normalize_session_id(raw_id: str) -> str:
    """Normalize session ID to canonical form"""
    raw_id = raw_id.lower().strip()
    
    # Check patterns
    for canonical, patterns in SESSION_PATTERNS.items():
        for pattern in patterns:
            if pattern in raw_id:
                return canonical
    
    # Return sanitized version
    return raw_id.replace(':', '-').replace(' ', '-')


def auto_log_message(direction: str, content: str, metadata: Optional[dict] = None):
    """
    Auto-log message in current session.
    
    Args:
        direction: 'received' or 'sent'
        content: Message content
        metadata: Optional metadata (from, to, etc.)
    """
    session = detect_session_from_context()
    
    event_type = f"message_{direction}"
    data = {
        "content": content[:200],  # Truncate long messages
        "length": len(content)
    }
    
    if metadata:
        data.update(metadata)
    
    log_event(session, event_type, data, user_triggered=(direction == 'received'))


def auto_switch_session(new_session: str, reason: str = None):
    """
    Log session switch and update context.
    
    Args:
        new_session: Target session ID
        reason: Optional reason for switch
    """
    old_session = get_session_id()
    
    if old_session != new_session:
        # Log switch in old session
        log_event(old_session, "context_switched", {
            "from": old_session,
            "to": new_session,
            "reason": reason or "Session change"
        })
        
        # Update session
        set_session_id(new_session)
        
        # Log arrival in new session
        log_event(new_session, "session_resumed", {
            "from": old_session
        })


def get_or_create_session(chat_name: str = None) -> str:
    """
    Get or create session for chat.
    Auto-switches if needed.
    
    Args:
        chat_name: Chat/channel name (optional)
    
    Returns:
        Session ID
    """
    if chat_name:
        session = normalize_session_id(chat_name)
        current = get_session_id()
        
        if session != current:
            auto_switch_session(session, f"Chat: {chat_name}")
        
        return session
    
    return detect_session_from_context()


# Convenience wrapper for common operations
class SessionContext:
    """Context manager for temporary session switch"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.prev_session = None
    
    def __enter__(self):
        self.prev_session = get_session_id()
        if self.prev_session != self.session_id:
            auto_switch_session(self.session_id, "Temporary switch")
        return self.session_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.prev_session and self.prev_session != self.session_id:
            auto_switch_session(self.prev_session, "Returning from temporary switch")


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Session management')
    parser.add_argument('action', choices=['detect', 'switch', 'log-message'])
    parser.add_argument('--session', help='Session ID')
    parser.add_argument('--direction', choices=['received', 'sent'], help='Message direction')
    parser.add_argument('--content', help='Message content')
    parser.add_argument('--reason', help='Switch reason')
    
    args = parser.parse_args()
    
    if args.action == 'detect':
        session = detect_session_from_context()
        print(f"Detected session: {session}")
    
    elif args.action == 'switch':
        if not args.session:
            print("Error: --session required")
            sys.exit(1)
        auto_switch_session(args.session, args.reason)
        print(f"Switched to: {args.session}")
    
    elif args.action == 'log-message':
        if not args.direction or not args.content:
            print("Error: --direction and --content required")
            sys.exit(1)
        auto_log_message(args.direction, args.content)
        print(f"Logged {args.direction} message")


if __name__ == "__main__":
    main()
