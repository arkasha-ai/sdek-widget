# Runbooks - Automation Documentation

Inspired by [JakeBot's AgentOps runbook template](https://moltbook.com) - each critical automation has a runbook covering:

1. Goal + success metric
2. Inputs/outputs + storage
3. Guardrails (never do)
4. Failure modes + detection
5. Rollback / kill switch
6. Rate limits
7. Monitoring
8. Ownership

## Active Runbooks

### Critical (24/7)
- [medications-reminder.md](medications-reminder.md) - 09:00 daily medication reminders (3 escalations)

### Important (Daily)
- [daily-backup.md](daily-backup.md) - 03:00 workspace backup to Gitea
- [morning-briefing.md](morning-briefing.md) - 08:00 weather + reminders

## Why Runbooks?

From JakeBot's post:
> "This turns 'cool demo' into something you can operate safely and hand off to Future You."

When Denis asks "что случилось с лекарствами?" or "почему backup не сработал?" — я читаю runbook и сразу знаю:
- Где посмотреть логи
- Какие failure modes возможны
- Как быстро починить
- Как отключить если нужно

**Template** for new automations: Copy structure from existing runbook, fill in details, commit to Gitea.

---

**Created:** 2026-02-15
**Based on:** Moltbook discussion (Rouken's "Vespers", JakeBot's template)
