# Memory Directory 🧠

Structured memory system for persistent context and knowledge.

---

## 📂 Structure

```
memory/
├── YYYY-MM-DD.md        # Daily logs (raw, append-only)
├── projects/            # Project-specific notes
│   ├── logera.md
│   └── logera-collabora-migration.md
└── state/               # Runtime state (JSON)
    ├── heartbeat-state.json
    └── github-notifications-state.json
```

---

## 📅 Daily Logs (YYYY-MM-DD.md)

**Purpose:** Raw chronological logs of what happened each day.

**Content:**
- Conversations and decisions
- Actions taken and results
- Problems encountered and solutions
- Learning moments
- Important context for future reference

**Style:**
- Append-only (never edit past entries)
- Timestamped when helpful
- Markdown formatting (headers, lists, code blocks)
- Include links to relevant files/commits when applicable

**When to create:** Automatically at first event of the day

**Retention:** Keep indefinitely (review monthly, archive if needed)

**Example structure:**
```markdown
# 2026-02-08

## Morning (03:00-09:00)

### Backup Completed
- Daily backup ran successfully at 03:00
- Pushed to GitHub: arkasha-ai/arkasha-workspace-backup
- Commit: 50eceee

### Phase 1 & 2: Workspace Organization
- Cleaned up old scripts (6 ticktick files → archive)
- Created comprehensive documentation
- See: README.md, scripts/README.md

## Notes
- Learned: Always check for hardcoded paths when moving files
- TODO: Review memory files next week
```

---

## 📁 Projects (projects/)

**Purpose:** Long-term notes for specific projects.

**Content:**
- Project overview and goals
- Technical specifications
- Implementation plans
- Migration guides
- Lessons learned specific to the project

**When to create:** When project spans multiple days/weeks

**Current projects:**
- **logera.md** - Logera project overview and context
- **logera-collabora-migration.md** - ONLYOFFICE → Collabora migration plan

**Naming:** `project-name.md` or `project-name-specific-topic.md`

**Lifecycle:**
1. Create when project starts
2. Update throughout development
3. Keep after completion (valuable reference)
4. Archive if outdated/deprecated

---

## 📊 State (state/)

**Purpose:** Runtime state for automation and tracking.

**Content:** JSON files with temporal state data

**Current state files:**
- **heartbeat-state.json** - Last check timestamps for heartbeat tasks
- **github-notifications-state.json** - Last processed notification ID

**Format example:**
```json
{
  "lastMoltbookCheck": 1770497220,
  "lastMemoryReview": null
}
```

**Rules:**
- Machine-generated (scripts update these)
- Not committed to git (excluded in .gitignore)
- Can be deleted safely (will reset tracking)
- Use Unix timestamps (milliseconds) for dates

---

## 🔄 Memory Workflow

### Daily Routine

1. **Log as you go**
   - Append to today's `YYYY-MM-DD.md`
   - Include context: what, why, outcome
   - Link to relevant files/commits

2. **Update project notes**
   - When project decisions made
   - When implementation details change
   - When learning something project-specific

3. **Update MEMORY.md (workspace root)**
   - Significant insights worth long-term retention
   - Decisions with important reasoning
   - Lessons learned from mistakes

### Periodic Review (Heartbeat)

**Every few days:**
1. Read last 3-5 daily logs
2. Identify patterns and insights
3. Update `../MEMORY.md` with distilled knowledge
4. Remove outdated info from MEMORY.md

**What to promote to MEMORY.md:**
- Important decisions and their reasoning
- System configurations that worked
- Security lessons and fixes
- Workflow improvements
- Recurring patterns

**What to keep in daily logs:**
- Raw conversations
- Debugging sessions
- Temporary context
- Daily routine tasks

---

## 🗃️ Archiving

**When to archive daily logs:**
- After 3+ months (if no longer relevant)
- Create `archive/YYYY-MM/` for old months
- Keep compressed archive for reference

**When to archive project notes:**
- Project completed and no longer maintained
- Create `archive/projects/` for old projects
- Keep README explaining what was archived

**Never delete:**
- Archive instead of deleting
- Disk is cheap, context is valuable
- Future-you might need it

---

## 🔍 Search & Discovery

**Finding information:**

1. **Recent context:** Check last 2-3 daily logs
2. **Project context:** Check `projects/*.md`
3. **Long-term wisdom:** Check `../MEMORY.md`
4. **Semantic search:** Use `qdrant_indexer.py search "query"`

**Semantic search example:**
```bash
cd ~/.openclaw/workspace
python3 scripts/qdrant_indexer.py index-memory
python3 scripts/qdrant_indexer.py search "GitHub authentication setup"
```

---

## 📝 Best Practices

### Writing Daily Logs

**Do:**
- ✅ Write while context is fresh
- ✅ Include reasoning behind decisions
- ✅ Link to relevant files/commits
- ✅ Use markdown formatting
- ✅ Timestamp important events

**Don't:**
- ❌ Wait until end of day (context lost)
- ❌ Write vague summaries ("fixed bug")
- ❌ Include sensitive credentials (use secrets.env)
- ❌ Edit past entries (append corrections instead)

### Managing Projects

**When to split project notes:**
- Main file getting too large (>1000 lines)
- Distinct sub-topics emerge
- Migration/refactoring plans

**Keep project notes focused:**
- Specific to the project
- Technical depth appropriate
- Updated with actual implementation
- Include links to code/docs

---

## 🎯 Memory Goals

**Short-term (daily logs):**
- Capture what happened today
- Preserve context for tomorrow
- Quick reference for recent work

**Medium-term (project notes):**
- Understand project state
- Document technical decisions
- Guide implementation work

**Long-term (MEMORY.md):**
- Wisdom and lessons learned
- Important decisions with reasoning
- System knowledge worth keeping forever

**The memory pyramid:**
```
       MEMORY.md (curated wisdom)
            ↑
      projects/*.md (focused knowledge)
            ↑
   YYYY-MM-DD.md (raw daily logs)
            ↑
        experience
```

---

**Last updated:** 2026-02-08 03:16 MSK  
**Maintained by:** Arkasha ⚡
