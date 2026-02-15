# Runbook: Daily Workspace Backup

## 1. Goal + Success Metric
**Goal:** Backup workspace to GitHub/Gitea daily at 03:00 AM.
**Success:** Fresh commit pushed every 24h, no data loss.

## 2. Inputs/Outputs + Storage
**Inputs:**
- Cron schedule: 03:00 daily (Europe/Moscow)
- Source: `/home/clawdbot/.openclaw/workspace/`
- Script: `/home/clawdbot/.openclaw/workspace/backup/backup.sh`

**Outputs:**
- Git commits to Gitea: `https://git.jakeberrimor.com/Arkasha/workspace-backup`
- Logs: Cron run history
- **Note:** Migrated from GitHub (arkasha-ai account suspended) on 2026-02-15

**State:**
- Job ID: `4ad0614f-1b38-4ed6-9642-cb7fa8926201`
- Session: main (NOT isolated sub-agent)

## 3. Guardrails (NEVER DO)
- ❌ Never backup secrets (API keys, tokens) — use .gitignore
- ❌ Never force-push (preserve history)
- ❌ Never delete remote branches
- ❌ Never commit large binary files (>10MB)

## 4. Failure Modes + Detection
**Failure modes:**
- Script fails (exit code != 0)
- Git auth fails (SSH key expired)
- Network down (Gitea unreachable)
- Disk full (can't write commit)

**Detection:**
```bash
# Check last run
cron action=runs jobId=4ad0614f-1b38-4ed6-9642-cb7fa8926201

# Manual test
cd ~/.openclaw/workspace/backup && ./backup.sh
```

**Alerts:**
- If `lastStatus != "ok"` for >24h → investigate immediately
- Weekly: verify last commit timestamp on Gitea

## 5. Rollback / Kill Switch
**Emergency disable:**
```bash
cron action=update jobId=4ad0614f-1b38-4ed6-9642-cb7fa8926201 patch='{"enabled":false}'
```

**Rollback data:**
```bash
# Restore from Gitea (requires credentials in ~/.git-credentials)
git clone https://git.jakeberrimor.com/Arkasha/workspace-backup /tmp/restore
# Cherry-pick commits or full restore
```

**Credentials:**
- Stored in `~/.git-credentials` (git credential helper)
- Format: `https://USERNAME:PASSWORD@git.jakeberrimor.com`
- Permissions: 600 (read/write owner only)

**Re-enable:**
```bash
cron action=update jobId=4ad0614f-1b38-4ed6-9642-cb7fa8926201 patch='{"enabled":true}'
```

## 6. Rate Limits
**Limits:**
- Git push: No API limit (self-hosted Gitea)
- Disk space: Monitor `/home/clawdbot/.openclaw/workspace/` size

**Anti-spam:**
- Runs once daily (03:00 AM)
- No retries on failure (wait for next day)

## 7. Monitoring
**Daily check (heartbeat):**
```bash
# Verify last commit is recent
cd ~/.openclaw/workspace/backup
git log -1 --format="%ct %s"
# Should be within last 27h
```

**Weekly audit:**
- Check Gitea repo: https://git.jakeberrimor.com/Arkasha/workspace-backup
- Verify commit history (7 commits in 7 days)
- Check .gitignore covers all secrets

## 8. Ownership
**Human:** Denis (@JakeBerrimor)
**Agent:** Arkasha (main agent)
**Created:** 2026-02-05
**Last reviewed:** 2026-02-15
**Migration:** GitHub → Gitea (2026-02-15 22:26)
**Gitea repo created:** 2026-02-15 via API
**Credentials:** Configured git credential helper
