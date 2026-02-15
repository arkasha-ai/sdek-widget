# Runbook: Medications Reminder (Sub-agent)

## 1. Goal + Success Metric
**Goal:** Remind Denis to take medications at 09:00 daily with escalating urgency.
**Success:** Denis confirms medication taken within 45 minutes (by 09:45).

## 2. Inputs/Outputs + Storage
**Inputs:**
- Cron schedule: 09:00, 09:20, 09:45 (Europe/Moscow)
- Target: telegram:364935958

**Outputs:**
- Telegram messages (announce mode, isolated sub-agent)
- Logs: `/home/clawdbot/.openclaw/cron/runs/` (job run history)

**State:**
- Cron jobs config: `/home/clawdbot/.openclaw/cron/jobs.json`
- IDs: `df3b7638` (09:00), `5eaf605e` (09:20), `fe16b478` (09:45)

## 3. Guardrails (NEVER DO)
- ❌ Never skip a reminder (even if "already reminded today")
- ❌ Never send to wrong channel/person
- ❌ Never disable job without explicit human request
- ❌ Never change schedule without confirmation

## 4. Failure Modes + Detection
**Failure modes:**
- Cron disabled → No reminders sent
- Telegram channel down → Message fails
- Sub-agent timeout → No announcement
- Wrong timezone → Wrong time

**Detection:**
```bash
# Check cron status
cron action=status

# Check last runs
cron action=runs jobId=df3b7638-16b3-406f-928a-a90d7df2c6ae

# Verify next run time
cron action=list | grep "Лекарства"
```

**Alerts:**
- If `lastStatus != "ok"` → check logs immediately
- If `consecutiveErrors > 0` → investigate

## 5. Rollback / Kill Switch
**Emergency disable:**
```bash
cron action=update jobId=df3b7638-16b3-406f-928a-a90d7df2c6ae patch='{"enabled":false}'
cron action=update jobId=5eaf605e-6e95-4440-a93a-bc2f3c2a4df0 patch='{"enabled":false}'
cron action=update jobId=fe16b478-95df-40fc-a39d-bfe16cb11d89 patch='{"enabled":false}'
```

**Re-enable:**
```bash
cron action=update jobId=<id> patch='{"enabled":true}'
```

**Test without sending:**
- Use `dryRun` mode (not implemented yet — feature request?)

## 6. Rate Limits
**Limits:**
- Telegram: ~30 messages/second (we send 3/day max — safe)
- Sub-agent spawn: 8 concurrent max (we use 1 at a time — safe)

**Anti-spam:**
- Fixed schedule (09:00, 09:20, 09:45) — no risk of runaway loop
- Escalation capped at 3 attempts
- No retries if delivery fails (bestEffort=true)

## 7. Monitoring
**Daily check (heartbeat):**
```python
# Check if all 3 jobs are enabled and last run was successful
jobs = ["df3b7638", "5eaf605e", "fe16b478"]
for job_id in jobs:
    runs = cron.runs(jobId=job_id)
    if runs[-1].status != "ok":
        alert(f"Medication reminder {job_id} failed!")
```

**Weekly audit:**
- Review cron run history (are all 3 jobs firing daily?)
- Check consecutiveErrors counter
- Verify timezone still correct (Europe/Moscow)

## 8. Ownership
**Human:** Denis (@JakeBerrimor)
**Agent:** Arkasha (main agent)
**Sub-agent:** Isolated session (spawned by cron)
**Created:** 2026-02-05
**Last reviewed:** 2026-02-15
