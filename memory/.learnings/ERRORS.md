# ERRORS.md — Аркаша

Ошибки команд, сбои инструментов, баги интеграций.

---

## [ERR-20260207-001] gateway-cron-scheduler

**Logged**: 2026-02-07T00:00:00+03:00
**Priority**: critical
**Status**: mitigated
**Area**: infra

### Summary
Gateway cron пропустил все три напоминания про лекарства

### Error
```
Все три cron jobs (09:00, 09:20, 09:45) не сработали.
Денис спросил в 09:57 "Где напоминания????"
```

### Context
- Gateway был занят → scheduler пропустил задачи
- Жизненно критичные задачи

### Suggested Fix
Добавить cron catch-up в HEARTBEAT.md. Для критичных задач — OS-level crontab как backup.

### Metadata
- Tags: cron, medications, critical
- Related Files: HEARTBEAT.md
- Promoted To: MEMORY.md, HEARTBEAT.md

---

## [ERR-20260217-001] vllm-tool-choice

**Logged**: 2026-02-17T16:00:00+03:00
**Priority**: high
**Status**: known-limitation
**Area**: infra

### Summary
Большинство моделей через litellm крашатся с `tool_choice: "auto"`

### Error
```
litellm.BadRequestError: "auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser
```

### Context
- Затронуто: GLM-4.6, GLM-4.7, GLM-4.7-Flash, MiniMax-M2, DeepSeek-OCR-2, Qwen3-Next-80B
- Рабочие: Qwen3-235B, gpt-oss-120b, Qwen3-Coder-480B, Qwen3-Coder-Next

### Suggested Fix
Фиксить на уровне vLLM backend: `--enable-auto-tool-choice --tool-call-parser <parser>`.
Или ждать OpenClaw compat flag `supportsTools: false` per-model.

### Metadata
- Tags: vllm, litellm, tool-choice, models
- Related Files: openclaw.json

---

## [ERR-20260217-002] minimax-tool-schema

**Logged**: 2026-02-17T16:10:00+03:00
**Priority**: medium
**Status**: known-limitation
**Area**: infra

### Summary
MiniMax-M2 через native provider: ошибка валидации пустых tool schemas

### Error
```
400 Tool 0 function has invalid 'parameters' schema: {} is not of type 'array'
```

### Context
- vLLM отвергает пустые `{}` в параметрах tool schemas
- Проявляется при использовании native provider minimax

### Suggested Fix
Workaround: не использовать MiniMax для задач с tool calls до фикса на backend.

### Metadata
- Tags: minimax, vllm, tool-schema

---
