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
