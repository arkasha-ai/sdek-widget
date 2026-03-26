# ERRORS

## [ERR-20260321-001] litellm-anthropic-oauth-headers
**Logged**: 2026-03-21T01:41:00Z
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
Anthropic OAuth tokens (sk-ant-oat*) rejected by API with "Request not allowed" when used via LiteLLM proxy

### Error
```
litellm.APIConnectionError: AnthropicException - {"error": {"type": "forbidden", "message": "Request not allowed"}}
```

### Context
- LiteLLM добавлял только `anthropic-beta: oauth-2025-04-20`
- Anthropic требует также `anthropic-beta: claude-code-20250219`, `user-agent: claude-cli/2.1.75`, `x-app: cli`
- Без этих заголовков OAuth токен работает только в официальных клиентах (OpenClaw, Claude Code)

### Suggested Fix
Добавить в `litellm/llms/anthropic/common_utils.py` в `optionally_handle_anthropic_oauth()`:
```python
headers["anthropic-beta"] = _merge_beta_headers(headers.get("anthropic-beta"), "claude-code-20250219")
headers.setdefault("user-agent", "claude-cli/2.1.75")
headers.setdefault("x-app", "cli")
```

### Metadata
- Reproducible: yes
- Related Files: litellm/llms/anthropic/common_utils.py
- See Also: LRN-20260321-001

### Resolution
- **Resolved**: 2026-03-21T01:40:00Z
- **Commit**: 2ace808fc4 (topitip/litellm)
- **Notes**: Патч запушен, Dokploy ребилд запущен

---

## [ERR-20260325-001] disk-full-enospc-cascade

**Logged**: 2026-03-25T16:44:00Z
**Priority**: critical
**Status**: resolved
**Area**: infra

### Summary
Диск заполнен на 100% (33 МБ свободно из 79 ГБ) → каскадные сбои: cron jobs падают с ENOSPC, MiniMax-M2.7 зацикливается и спамит чат, файлы отправляются в неправильные топики.

### Error
```
Error: ENOSPC: no space left on device, write
```

### Context
- `/tmp/` содержал 23 ГБ мусора: ~15 старых workspace-backup-*.tar.gz, litellm репозитории, portfolio-frontend
- `.cache/pip` — 4.4 ГБ кэша
- `.cache/whisper/large-v3-turbo.pt` — 1.6 ГБ (локальная модель, не используется)
- Paperclip cron и znaem-ai cron падали с ENOSPC
- Модель MiniMax-M2.7 при невозможности записать сессию зацикливалась на одном ответе

### Suggested Fix
1. Добавить мониторинг диска в HEARTBEAT.md (алерт при >85%)
2. Настроить автоочистку /tmp/ от старых бэкапов
3. Периодически чистить pip cache (`pip cache purge`)

### Metadata
- Reproducible: yes
- Related Files: HEARTBEAT.md
- Tags: disk, enospc, monitoring, cascade-failure

### Resolution
- **Resolved**: 2026-03-25T16:43:00Z
- **Notes**: Удалены /tmp/workspace-backup-*.tar.gz, /tmp/litellm*, /tmp/portfolio-frontend-new, .cache/pip, .cache/whisper. Освобождено ~27 ГБ (33 МБ → 28 ГБ свободно)
