# Runbook: Morning Briefing

## 1. Goal + Success Metric
**Goal:** Send daily morning briefing at 08:00 with weather, reminders, and motivation.
**Success:** Denis receives relevant info before his day starts.

## 2. Inputs/Outputs + Storage
**Inputs:**
- Cron schedule: 08:00 daily (Europe/Moscow)
- Weather API: via `weather` skill (Penza)
- Memory: medications reminder (09:00 upcoming)

**Outputs:**
- Telegram message to 364935958
- Session: main (NOT isolated sub-agent)

**State:**
- Job ID: `48292459-29b8-4a2b-b7ae-e7a071a78e4e`
- Last run: check via `cron action=runs`

## 3. Guardrails (NEVER DO)
- ❌ Never send at wrong time (respect timezone)
- ❌ Never skip medication reminder mention
- ❌ Never send empty/failed weather data without fallback
- ❌ Never spam if weather API fails

## 4. Failure Modes + Detection
**Failure modes:**
- Weather API timeout → Use fallback "Погода недоступна"
- Cron disabled → No briefing sent
- Wrong timezone → Fires at wrong time

**Detection:**
```bash
# Check last run
cron action=runs jobId=48292459-29b8-4a2b-b7ae-e7a071a78e4e

# Test weather skill manually
weather --location Penza
```

**Alerts:**
- If `lastStatus != "ok"` → check logs
- If Denis reports missing briefing → verify job enabled

## 5. Rollback / Kill Switch
**Emergency disable:**
```bash
cron action=update jobId=48292459-29b8-4a2b-b7ae-e7a071a78e4e patch='{"enabled":false}'
```

**Manual trigger:**
```bash
cron action=run jobId=48292459-29b8-4a2b-b7ae-e7a071a78e4e runMode=force
```

**Re-enable:**
```bash
cron action=update jobId=48292459-29b8-4a2b-b7ae-e7a071a78e4e patch='{"enabled":true}'
```

## 6. Rate Limits
**Limits:**
- Weather API: ~100 requests/day (we use 1/day — safe)
- Telegram: ~30 messages/second (we send 1/day — safe)

**Anti-spam:**
- Fixed schedule (08:00 once daily)
- No retries on failure

## 7. Monitoring
**Daily check (heartbeat):**
```python
# Verify briefing sent today
runs = cron.runs(jobId="48292459-29b8-4a2b-b7ae-e7a071a78e4e")
last_run = runs[-1]
if last_run.status != "ok":
    alert("Morning briefing failed!")
```

**Weekly audit:**
- Review 7 days of briefings (should be 7 successful runs)
- Check weather skill still working
- Update briefing text if needed (seasonal changes, new habits)

## 8. Ownership
**Human:** Denis (@JakeBerrimor)
**Agent:** Arkasha (main agent)
**Created:** 2026-02-05
**Last reviewed:** 2026-02-15
