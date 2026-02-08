# Event Log Integration Guide

How to use event logging in daily work.

---

## Quick Start

### Option 1: Manual Logging (Simple)

When starting important work:

```python
from scripts.event_helpers import task_context, log_decision

with task_context("my_task", {"context": "details"}):
    # Do work
    # Task automatically logged on completion
```

### Option 2: Auto-logging (Advanced)

When you want automatic tracking:

```python
from scripts.auto_log import message_received, message_sent
from scripts.session_manager import get_or_create_session

# At message start
message_received(user_message, from_user="Denis", chat="main")

# Do work...

# At message end
message_sent(my_reply, to="Denis")
```

---

## Integration Patterns

### Pattern 1: Task-Based Work

**Use when:** Working on specific tasks (coding, documentation, etc.)

```python
from scripts.event_helpers import task_context, log_file_change, log_decision

with task_context("implement_feature_x", {"phase": "backend"}):
    # Step 1: Make decision
    log_decision("Use PostgreSQL for better transaction support")
    
    # Step 2: Create files
    log_file_change("backend/database.py", "created", "Database connection")
    
    # Step 3: Implement
    # ... work ...
    
    # Step 4: Commit
    log_command("git commit -m 'Add database layer'", "success", 0)
    
    # Task automatically marked complete on exit
```

### Pattern 2: Conversation-Based Work

**Use when:** Responding to messages, handling requests

```python
from scripts.auto_log import message_received, message_sent
from scripts.session_manager import get_or_create_session

# Get/create session for this chat
session = get_or_create_session("backend-release")

# Log incoming message
message_received(user_text, from_user="Denis", chat="backend-release")

# Process and respond
# ... work ...

# Log outgoing message
message_sent(response_text)
```

### Pattern 3: Multi-Session Work

**Use when:** Switching between different contexts

```python
from scripts.session_manager import SessionContext

# Main work
with SessionContext("main"):
    # ... do main work ...
    pass

# Switch to Discord temporarily
with SessionContext("discord-general"):
    # ... handle Discord message ...
    pass

# Automatically returns to main
# Context switches logged automatically
```

---

## Real-World Examples

### Example 1: Implementing a Feature

```python
from scripts.event_helpers import task_context, log_decision, log_file_change

# Start task
with task_context("add_email_notifications", {"priority": "high"}):
    
    # Design decision
    log_decision("Use SendGrid for email delivery (reliable, scalable)")
    
    # Implementation
    log_file_change("notifications/email.py", "created", "Email service")
    log_file_change("config.py", "modified", "Added SendGrid config")
    
    # Testing
    log_command("pytest tests/test_email.py", "success", 0)
    
    # Deploy
    log_command("git push origin main", "success", 0)
    
# Task complete (logged automatically)
```

### Example 2: Handling Multiple Chats

```python
from scripts.auto_log import message_received, message_sent
from scripts.session_manager import get_or_create_session

# Main chat message
get_or_create_session("main")
message_received("Can you check the logs?", from_user="Denis")
# ... check logs ...
message_sent("Found the issue - database connection timeout")

# Discord interruption  
get_or_create_session("discord-general")
message_received("Quick question about deployment", from_user="teammate")
# ... answer ...
message_sent("Deploy with docker-compose up -d")

# Back to main (automatic)
get_or_create_session("main")
message_sent("Fixed the timeout issue, deploying now")
```

### Example 3: Research & Documentation

```python
from scripts.event_helpers import task_context, log_api_call

with task_context("research_semantic_search", {"goal": "find_best_library"}):
    
    # Research
    log_api_call("google", "/search?q=semantic+search+python", "success")
    log_api_call("github", "/search/repositories?q=semantic+search", "success")
    
    # Decision
    log_decision("Chose Qdrant - best balance of features and ease of use")
    
    # Documentation
    log_file_change("docs/semantic-search.md", "created", "Research findings")
    
# Task complete
```

---

## Best Practices

### DO ✅

- **Log task boundaries** - start and completion
- **Log decisions with reasoning** - future-you will thank you
- **Log file changes** - especially important ones
- **Use task_context** - automatic lifecycle tracking
- **Log errors** - helps with debugging later

### DON'T ❌

- **Don't log every trivial action** - creates noise
- **Don't log sensitive data** - passwords, tokens, etc.
- **Don't log without context** - always include relevant metadata
- **Don't forget to switch sessions** - keeps context clean

---

## Recovery Workflow

### Morning Routine

```python
from scripts.recover_session import print_recovery_report

# Check state
print_recovery_report("main")

# Resume incomplete tasks
from scripts.event_logger import get_incomplete_tasks
incomplete = get_incomplete_tasks("main")

for task in incomplete:
    task_name = task['data']['task']
    context = task['data'].get('context', 'N/A')
    print(f"TODO: Resume {task_name} - {context}")
```

### Quick Status Check

```bash
# Session overview
python3 scripts/recover_session.py

# Detailed report
python3 scripts/recover_session.py main

# Timeline view
python3 scripts/event_timeline.py main 20
```

---

## Troubleshooting

### Issue: Events not logging

**Check:**
1. Is session ID correct? `echo $OPENCLAW_SESSION`
2. Is events directory writable? `ls -la memory/events/`
3. Are imports working? `python3 -c "from scripts.event_helpers import task_context"`

### Issue: Wrong session detected

**Fix:**
```python
from scripts.event_helpers import set_session_id
set_session_id("correct-session-name")
```

### Issue: Too many events

**Solution:** Be more selective about what to log. Focus on:
- Task boundaries (start/end)
- Decisions (why, not just what)
- Important file changes
- Errors and recoveries

---

## Advanced: Custom Event Types

You can create custom event types:

```python
from scripts.event_logger import log_event
from scripts.event_helpers import get_session_id

# Custom event
log_event(get_session_id(), "deployment_started", {
    "environment": "production",
    "version": "1.2.3",
    "by": "automated_pipeline"
})

# Custom event with tags
log_event(
    get_session_id(),
    "security_alert",
    {"severity": "high", "issue": "unauthorized_access_attempt"},
    tags=["security", "urgent"]
)
```

---

## Migration from Manual Logging

If you have existing logs in markdown, you can:

1. **Keep both** - markdown for humans, events for machines
2. **Gradually adopt** - start with new work, leave old logs
3. **Distill important events** - extract key milestones to event log

No need to migrate everything - event log complements, doesn't replace.

---

## FAQ

**Q: Do I need to log every message?**  
A: No! Log important conversations and task work. Routine chat can stay in markdown logs.

**Q: How do I know which session I'm in?**  
A: `python3 scripts/session_manager.py detect`

**Q: Can I search events?**  
A: Yes! `./scripts/qdrant index-events && ./scripts/qdrant search --type event "query"`

**Q: What if I make a mistake?**  
A: Events are append-only. Just log a correction event if needed.

**Q: How much disk space?**  
A: ~100-200 bytes per event. 100 events/day = ~20KB/day = ~7MB/year. Very efficient!

---

**Start small, grow gradually. Event logging should help, not hinder!**
