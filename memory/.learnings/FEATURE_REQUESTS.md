# FEATURE_REQUESTS.md — Аркаша

Возможности которых не хватает. Фиксировать когда Денис просит что-то чего нет.

---

## [FR-20260217-001] openclaw-model-compat-flag

**Logged**: 2026-02-17T00:00:00+03:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
Нужен флаг `supportsTools: false` per-model в OpenClaw конфиге

### Details
Сейчас нет способа отключить tool calls для конкретной модели. Модели на vLLM без `--enable-auto-tool-choice` крашатся.

### Suggested Action
Открыть issue в openclaw/openclaw или ждать обновления.

### Metadata
- Tags: openclaw, models, vllm
- Related: ERR-20260217-001

---
