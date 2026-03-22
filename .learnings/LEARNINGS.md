# LEARNINGS

## [LRN-20260321-001] anthropic-oauth-required-headers
**Logged**: 2026-03-21T01:41:00Z
**Priority**: high
**Status**: promoted
**Area**: infra

### Summary
Anthropic OAuth токены требуют три специфичных заголовка для работы через любой прокси

### Details
OAuth токен (sk-ant-oat*) — это не обычный API ключ. Anthropic разрешает его только клиентам которые представляются как официальные (Claude Code, OpenClaw). Требуемые заголовки:
- `anthropic-beta: claude-code-20250219,oauth-2025-04-20`
- `user-agent: claude-cli/2.1.75`
- `x-app: cli`

Без них — 403 "Request not allowed" даже с верным токеном.

### Suggested Action
При интеграции Anthropic OAuth через любой прокси — явно добавлять эти заголовки

### Metadata
- Source: conversation
- Related Files: litellm/llms/anthropic/common_utils.py
- Tags: anthropic, oauth, litellm, headers
- See Also: ERR-20260321-001
- **Promoted**: TOOLS.md (раздел LiteLLM/Anthropic OAuth)

---

## [LRN-20260321-002] browser-viewport-resize
**Logged**: 2026-03-21T01:41:00Z
**Priority**: high
**Status**: promoted
**Area**: config

### Summary
Браузер в OpenClaw не имеет дефолтного viewport — resize 1500x900 обязателен первым шагом

### Details
Без `browser(action="act", request={"kind":"resize","width":1500,"height":900})` в начале — скриншоты маленькие, координаты кликов неверные. Паттерн нарушался системно.

### Suggested Action
Добавить в TOOLS.md жёсткое предупреждение "БЕЗ ИСКЛЮЧЕНИЙ"

### Metadata
- Source: session-review
- Tags: browser, viewport, openclaw
- **Promoted**: TOOLS.md (уже обновлено 2026-03-21)

---

## [LRN-20260321-003] mindgraph-not-used
**Logged**: 2026-03-21T01:41:00Z
**Priority**: high
**Status**: promoted
**Area**: config

### Summary
MindGraph не используется несмотря на инструкции — нужно жёсткое правило в AGENTS.md

### Details
Ревью сессий показало: ни одного вызова MindGraph за несколько дней. AGENTS.md говорил "когда использовать" но без принуждения. Обновлено на "⚠️ ОБЯЗАТЕЛЬНО перед ответом" с готовым curl-примером.

### Suggested Action
Рассмотреть webhook/hook для автоматического prefetch (см. FEAT-20260321-001)

### Metadata
- Source: session-review
- Tags: mindgraph, memory, agents
- **Promoted**: AGENTS.md (обновлено 2026-03-21)

---

## [LRN-20260321-004] external-chat-privacy
**Logged**: 2026-03-21T01:41:00Z
**Priority**: medium
**Status**: promoted
**Area**: config

### Summary
В чужих чатах не раскрывать имя владельца и детали инфраструктуры

### Details
В чате с Михаилом был раскрыт факт что "Денис видит все логи" и намёк на серверную инфраструктуру. Нарушение privacy.

### Suggested Action
Отвечать "администратор платформы" без имён

### Metadata
- Source: session-review
- Tags: privacy, groups, external-chats
- **Promoted**: AGENTS.md (раздел "Внешние чаты" добавлен 2026-03-21)

---

## [LRN-20260321-005] litellm-onprem-uses-source-code
**Logged**: 2026-03-21T01:41:00Z
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
Кастомный LiteLLM деплой в Dokploy собирается из исходников репозитория topitip/litellm, а не из pip

### Details
При попытке пушить через HTTPS — ошибка. Нужно использовать SSH с ключом `~/.ssh/github_arkasha`. Репозиторий доступен через `git@github.com:topitip/litellm.git`.

### Metadata
- Source: conversation
- Tags: litellm, dokploy, github, deployment
