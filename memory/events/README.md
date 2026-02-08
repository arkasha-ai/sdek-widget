# Event Log System 🎯

Multi-session structured event logging for fast state recovery.

---

## Overview

**Problem:** Agent "Babysitting Tax" - spending tokens to remember context after restart.

**Solution:** Structured event log per session → deterministic state recovery.

**Key Features:**
- ✅ Session isolation (parallel contexts don't interfere)
- ✅ Fast recovery (read last N events, not full history)
- ✅ Queryable (find incomplete tasks, recent actions)
- ✅ Human + Machine readable (JSONL format)

---

## Architecture

```
memory/events/
├── main.jsonl              # Main session events
├── discord-general.jsonl   # Discord session events
├── isolated-XXX.jsonl      # Isolated sessions
└── README.md              # This file
```

**Each session = independent event stream**

---

## Event Format

```json
{
  "timestamp": "2026-02-08T03:47:00+03:00",
  "session_id": "main",
  "type": "task_started",
  "data": {
    "task": "semantic_search_improvements",
    "context": "Add filters to qdrant_indexer"
  }
}
```

**Base fields:**
- `timestamp` - ISO-8601 format
- `session_id` - Session identifier
- `type` - Event type (see below)
- `data` - Event-specific data (flexible)

**Optional fields:**
- `tags` - List of tags for filtering
- `user_triggered` - Boolean (user action vs automated)

---

## Event Types

### Task Management
- `task_started` - Started a task
- `task_completed` - Task finished successfully
- `task_failed` - Task failed
- `task_paused` - Task paused (context switch)
- `task_resumed` - Resumed paused task

### Actions
- `file_created` / `file_modified` / `file_deleted`
- `code_committed` - Git commit
- `command_executed` - Important shell command
- `api_called` - External API call

### Decisions
- `decision_made` - Important decision with reasoning
- `approach_changed` - Changed approach to task

### Communication
- `message_received` - Message from user
- `message_sent` - Reply sent
- `notification_sent` - Notification delivered

### State Changes
- `context_switched` - Switched between sessions
- `error_occurred` - Error happened
- `recovery_attempted` - Recovery action

---

## Usage

### CLI Interface

**Log an event:**
```bash
python3 scripts/event_logger.py log main task_started '{"task": "xyz"}'
```

**Get recent events:**
```bash
python3 scripts/event_logger.py recent main 20
```

**Get session state:**
```bash
python3 scripts/event_logger.py state main
```

**Find incomplete tasks:**
```bash
python3 scripts/event_logger.py incomplete main
```

**List all sessions:**
```bash
python3 scripts/event_logger.py sessions
```

### Python API

```python
from event_logger import log_event, get_session_state, get_incomplete_tasks

# Log event
log_event("main", "task_started", {
    "task": "event_log_implementation",
    "context": "Building the system"
})

# Get current state
state = get_session_state("main")
print(f"Active tasks: {state['active_tasks']}")
print(f"Last action: {state['last_action']}")

# Find incomplete tasks
incomplete = get_incomplete_tasks("main")
for task in incomplete:
    print(f"TODO: {task['data']['task']}")
```

---

## Recovery Workflow

### On Session Start

```python
from event_logger import get_session_state, get_incomplete_tasks

# 1. Get session state
state = get_session_state("main")

# 2. Check for incomplete tasks
if state['active_tasks']:
    print(f"⚠️ Resume: {', '.join(state['active_tasks'])}")

# 3. Get recent context
recent = get_recent_events("main", limit=10)
# Review what happened before restart
```

### During Work

```python
# Log important events as you work
log_event("main", "task_started", {"task": "xyz"})

# ... do work ...

log_event("main", "file_modified", {
    "file": "scripts/something.py",
    "change": "added function"
})

# ... more work ...

log_event("main", "task_completed", {
    "task": "xyz",
    "outcome": "success"
})
```

---

## Integration with Existing System

**Event logs complement, not replace:**

### Markdown Logs (keep!)
- **Purpose:** Human-readable context
- **Audience:** Humans (Denis, future review)
- **Content:** Conversations, decisions, reasoning
- **Location:** `memory/YYYY-MM-DD.md`

### Event Logs (new!)
- **Purpose:** Machine state recovery
- **Audience:** Agent (fast bootstrap)
- **Content:** Structured actions, tasks, state changes
- **Location:** `memory/events/<session>.jsonl`

### MEMORY.md (keep!)
- **Purpose:** Long-term curated wisdom
- **Audience:** Both (reference material)
- **Content:** Decisions, lessons, configurations
- **Location:** `MEMORY.md` (workspace root)

**Use all three together!**

---

## Advantages

### vs Full Markdown Logs

**Before (markdown only):**
```
Read 30KB daily log → LLM extracts "where I stopped" → costs tokens
```

**After (event log):**
```
Read last 20 events (2KB) → instant state → no LLM needed
```

### vs Single Global Log

**Problem:** All sessions mixed → hard to isolate context

**Solution:** Per-session logs → clean isolation

### vs In-Memory State

**Problem:** Lost on restart

**Solution:** Persistent event stream → rebuild state deterministically

---

## Storage Details

**Format:** JSONL (JSON Lines)
- One event per line
- Append-only
- Grep-able, parseable
- No locking needed

**Retention:** Keep forever
- Old events compress well
- Disk is cheap, context is valuable
- Can archive old sessions if needed

**Size:** ~100-200 bytes per event
- Medium logging (50-100 events/day)
- ~5-10 KB per day per session
- ~150-300 KB per month per session

---

## Best Practices

### What to Log

**✅ DO log:**
- Task boundaries (started/completed)
- Important decisions
- File changes
- Git commits
- Errors and recovery

**❌ DON'T log:**
- Every LLM call (too noisy)
- Routine heartbeats (unless important)
- Trivial actions

### When to Log

**Manually:** Semantic events (tasks, decisions)
**Automatically:** Infrastructure events (files, commands)

### Session Naming

**Good:** `main`, `discord-general`, `isolated-reminder-YYYYMMDD`
**Bad:** `agent:main:main` (too verbose), `temp123` (unclear)

---

## Future Enhancements

**Could add:**
- Global index for cross-session queries
- Semantic search over events (via Qdrant)
- Timeline visualization
- Event replay debugging
- SQLite backend (if querying becomes critical)

**For now:** Keep it simple - JSONL works great!

---

## Example Session

```bash
# Start task
python3 scripts/event_logger.py log main task_started \
  '{"task": "github_profile_upgrade", "context": "Improve README"}'

# Log progress
python3 scripts/event_logger.py log main file_modified \
  '{"file": "README.md", "change": "added badges"}'

python3 scripts/event_logger.py log main code_committed \
  '{"message": "Add badges and stats", "commit": "abc123"}'

# Complete task
python3 scripts/event_logger.py log main task_completed \
  '{"task": "github_profile_upgrade", "outcome": "success"}'

# Check state
python3 scripts/event_logger.py state main
# → active_tasks: [], last_action: "Completed: github_profile_upgrade"
```

---

## Comparison with SiriusOS

**SiriusOS Immortal Event Log:**
- Cryptographic attestations (signed events)
- State machine reconstitution
- Single-agent focus

**Our Multi-Session Event Log:**
- Session isolation (parallel contexts)
- Simpler (no crypto overhead for now)
- Hybrid approach (events + markdown)

**Both solve the "Babysitting Tax"!**

---

**Created:** 2026-02-08  
**Inspired by:** [@Sirius's post on Moltbook](https://moltbook.com/u/Sirius)  
**Status:** ✅ Production ready (Phase A & B complete)  

**Integration:** See [INTEGRATION.md](INTEGRATION.md) for practical usage guide

**Quick links:**
- [Integration Guide](INTEGRATION.md) - How to use in daily work
- [Event Logger API](../../scripts/event_logger.py) - Core functions
- [Event Helpers](../../scripts/event_helpers.py) - Decorators & shortcuts
- [Session Manager](../../scripts/session_manager.py) - Auto-detection
- [Recovery Tool](../../scripts/recover_session.py) - State reconstruction
