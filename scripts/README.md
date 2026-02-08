# Scripts Directory

Utility scripts for automation and integrations.

---

## 📧 Email & Notifications

### imap_idle_listener_v2.py

**Purpose:** Event-driven email monitoring using IMAP IDLE protocol.

**What it does:**
- Maintains persistent IMAP IDLE connections to all email accounts
- Instantly triggers OpenClaw webhook on new mail (<1 sec latency)
- Tracks UIDs to avoid duplicate notifications
- Auto-reconnects with exponential backoff

**Accounts monitored:**
- dparmeev@luminesfox.com
- spam@jakeberrimor.com
- contact@jakeberrimor.com
- contact@luminesfox.com

**Usage:**
```bash
# Run in foreground (for debugging)
python3 -u ~/.openclaw/workspace/scripts/imap_idle_listener_v2.py

# Run in background (PTY mode via OpenClaw exec)
cd ~/.openclaw/workspace && python3 -u scripts/imap_idle_listener_v2.py
```

**Dependencies:**
```bash
pip3 install imapclient --user --break-system-packages
```

**Tech details:**
- Library: `imapclient` (proper IDLE protocol implementation)
- Keep-alive: IDLE refresh every 15 min
- Timeout: `idle_check(timeout=300)` = 5 min
- Reconnect: exponential backoff (5s → 300s max)

**Configuration:** Credentials in `~/.openclaw/secrets.env`

**See also:** [IMAP IDLE skill](../skills/imap-idle/SKILL.md)

---

## 🔍 Search & Indexing

### qdrant_indexer.py

**Purpose:** Semantic search over emails and memory files using Qdrant vector database.

**What it does:**
- Indexes emails from Himalaya accounts
- Indexes memory files (MEMORY.md + memory/*.md)
- Semantic search using embeddings (Qwen3-Embedding-0.6B)
- Returns relevant snippets with metadata and similarity scores

**Usage:**
```bash
# Index all emails (first 50 per account)
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py index-emails

# Index memory files
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py index-memory

# Search
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py search "your query here"
```

**Accounts indexed:**
- dparmeev, spam, contact, contact-lumines

**Output:** JSON with score, metadata (subject/from/date or file path), and text snippet

**Configuration:**
- Qdrant URL/API key: `secrets.env`
- LiteLLM API key: `secrets.env`
- Embedding model: Qwen3-Embedding-0.6B (via LiteLLM)
- Collection: `arkasha`

**Tech details:**
- ID generation: MD5 hash (account:email_id or file_path)
- Vector dimension: 1024 (Qwen embedding size)
- Distance metric: Cosine similarity

---

## 🦞 Social & Integrations

### moltbook.py

**Purpose:** Interact with Moltbook API (social network for AI agents).

**What it does:**
- Read feed (following, recommended, trending)
- Create posts and comments
- Upvote/downvote content
- Follow/unfollow users
- Search posts semantically

**Usage:**
```bash
# View feed
python3 ~/.openclaw/workspace/scripts/moltbook.py feed --type following --limit 10

# Create post
python3 ~/.openclaw/workspace/scripts/moltbook.py post "Your content here"

# Comment on post
python3 ~/.openclaw/workspace/scripts/moltbook.py comment <post_id> "Your comment"

# Upvote
python3 ~/.openclaw/workspace/scripts/moltbook.py upvote <post_id>

# Search
python3 ~/.openclaw/workspace/scripts/moltbook.py search "query"
```

**Profile:** https://moltbook.com/u/Arkasha

**Configuration:**
- Credentials: `~/.config/moltbook/credentials.json`
- API key stored in file after initial claim

**Use cases:**
- Learn from other agents' solutions
- Share experiences and insights
- Discover new tools and approaches
- Build reputation in AI agent community

---

## 🎥 Media Processing

### youtube_transcript.py

**Purpose:** Download and extract clean text transcripts from YouTube videos.

**What it does:**
- Downloads auto-generated subtitles from YouTube
- Converts to clean text (removes timestamps, formatting)
- Supports multiple languages (defaults to Russian, falls back to English)

**Usage:**
```bash
python3 ~/.openclaw/workspace/scripts/youtube_transcript.py <youtube_url> [language]
```

**Examples:**
```bash
# Default (Russian with English fallback)
python3 youtube_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Specific language
python3 youtube_transcript.py "https://youtu.be/dQw4w9WgXcQ" en
```

**Supported formats:**
- youtube.com/watch?v=...
- youtu.be/...
- youtube.com/shorts/...
- youtube.com/embed/...

**Dependencies:**
- `yt-dlp` installed at `~/.local/bin/yt-dlp`

**Tech details:**
- Uses yt-dlp subtitles extraction
- No video download (subtitles only)
- Fast and bandwidth-efficient

---

## 📊 Event Logging

### event_logger.py

**Purpose:** Multi-session structured event logging for fast state recovery.

**What it does:**
- Logs events to per-session streams (JSONL format)
- Tracks tasks, actions, decisions, state changes
- Enables fast recovery: "where did I stop?" without reading full history
- Isolates parallel sessions (main, Discord, isolated)

**Usage:**
```bash
# Log an event
python3 ~/.openclaw/workspace/scripts/event_logger.py log main task_started '{"task": "xyz"}'

# Get session state
python3 ~/.openclaw/workspace/scripts/event_logger.py state main

# Find incomplete tasks
python3 ~/.openclaw/workspace/scripts/event_logger.py incomplete main

# List all sessions
python3 ~/.openclaw/workspace/scripts/event_logger.py sessions
```

**Event types:**
- Task management: task_started, task_completed, task_failed
- Actions: file_created, code_committed, command_executed
- Decisions: decision_made, approach_changed
- Communication: message_received, message_sent

**Storage:** `memory/events/<session>.jsonl` (one file per session)

**Python API:** Import helpers for easy logging
```python
from event_helpers import task_context, log_decision, log_file_change

with task_context("my_task"):
    # Work automatically logged
    log_file_change("file.py", "modified")
```

**Recovery:** Fast session state reconstruction
```bash
# Show recovery report
python3 ~/.openclaw/workspace/scripts/recover_session.py main

# List all sessions
python3 ~/.openclaw/workspace/scripts/recover_session.py
```

**Visualization:** Timeline view
```bash
python3 ~/.openclaw/workspace/scripts/event_timeline.py main 20
```

**See also:** [memory/events/README.md](../memory/events/README.md) for detailed documentation

---

### event_helpers.py

**Purpose:** Python decorators and helpers for easy event logging.

**Features:**
- `@log_task(name)` decorator - auto-log task lifecycle
- `@log_decision(reasoning)` decorator - log decisions
- `task_context(name)` context manager - automatic task tracking
- Quick shortcuts: log_file_change, log_command, log_api_call

**See:** event_logger.py section above for usage

---

### recover_session.py

**Purpose:** Session recovery helper with actionable recommendations.

**Features:**
- Session state summary (events, active tasks, last activity)
- Time-aware analysis (events today, last hour)
- Incomplete task detection with context
- Actionable recommendations

**Usage:** See event_logger.py section above

---

### event_timeline.py

**Purpose:** Visual timeline of session events.

**Features:**
- Chronological event display with icons
- Hour separators for readability
- Event type highlighting
- Configurable limit

**Usage:** See event_logger.py section above

---

## 🔄 Project Management

### update_logera_tasks.py

**Purpose:** Sync and update tasks for Logera project (Deniss's pet project).

**What it does:**
- [To be documented - need to analyze usage]

**Usage:**
```bash
python3 ~/.openclaw/workspace/scripts/update_logera_tasks.py
```

---

## 📝 Best Practices

**When adding new scripts:**

1. **Add shebang:** `#!/usr/bin/env python3` for executables
2. **Make executable:** `chmod +x script.py`
3. **Add docstring:** Module-level description
4. **Document here:** Add entry to this README
5. **Configuration:** Use `secrets.env` for credentials
6. **Error handling:** Graceful failures with clear messages
7. **Logging:** Use print/logging for debugging

**Naming conventions:**
- Descriptive names: `imap_idle_listener.py` not `listener.py`
- Underscores for multi-word: `qdrant_indexer.py`
- Version suffix if needed: `_v2.py`

**Dependencies:**
- Document required packages
- Use `--user --break-system-packages` for pip installs
- Keep dependencies minimal

---

## 🗄️ Archive

Old/deprecated scripts moved to `../archive/scripts-cleanup-YYYY-MM-DD/`:
- Multiple TickTick API experiments (replaced by standalone CLI)
- Old IMAP listener v1 (replaced by v2)
- GitHub notifier polling (replaced by email notifications)

Nothing is deleted - check archive if you need to recover old code.

---

**Last updated:** 2026-02-08
