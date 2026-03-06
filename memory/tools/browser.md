# Browser 🌐

**Profile:** `openclaw` (NOT `chrome`)
**Status:** Always available, already logged in GitHub (arkasha-ai — ЗАБЛОКИРОВАН)

**DON'T use:** `profile="chrome"` unless Denis explicitly asks to attach his Chrome tab

## Click Workaround (CLI)

`browser.act` сломан в текущей версии OpenClaw.

**Решение:** CLI команда `openclaw browser click`

```bash
# 1. Snapshot для получения refs
# 2. Кликнуть через CLI
openclaw browser click <ref> --target-id <targetId>

# Опции:
# --button left|right|middle
# --double                     (двойной клик)
# --modifiers Shift,Alt,Meta
```

**Пример:**
```bash
# Нашли кнопку ref="e42" в snapshot
exec("openclaw browser click e42 --target-id ABC123")
exec("sleep 2")
# Новый snapshot
```

**Статус:** Работает! (2026-02-09)
