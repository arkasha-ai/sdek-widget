# FEATURE REQUESTS

## [FEAT-20260321-001] mindgraph-auto-prefetch
**Logged**: 2026-03-21T01:41:00Z
**Priority**: medium
**Status**: pending
**Area**: infra

### Requested Capability
Автоматический pre-fetch из MindGraph при каждом входящем сообщении — чтобы не полагаться на поведение модели

### User Context
Денис заметил что MindGraph не используется несмотря на инструкции. Нужен механический способ гарантировать что граф опрашивается.

### Complexity Estimate
medium

### Suggested Implementation
OpenClaw webhook/hook, который на каждое сообщение извлекает именованные сущности и делает POST /retrieve, инжектируя результат как system message

### Metadata
- Frequency: first_time
- Related Features: MindGraph skill
