#!/bin/bash
# Usage: watch_deploy.sh <application_id> <chat_id> [thread_id]
# Example: watch_deploy.sh 2I301SWysYj46deXZK8lD telegram:-1003831241406 1

source ~/.openclaw/secrets.env

APP_ID="${1}"
CHAT_ID="${2}"
THREAD_ID="${3:-}"
DELAY=20  # секунд между проверками
MAX_WAIT=600  # максимум 10 минут

elapsed=0

while [ $elapsed -lt $MAX_WAIT ]; do
  STATUS=$(curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
    "$DOKPLOY_API_URL/api/deployment.all?applicationId=$APP_ID" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['status'])" 2>/dev/null)

  if [ "$STATUS" = "done" ]; then
    MSG="✅ Задеплоилось — https://znaemai.ru"
    break
  elif [ "$STATUS" = "error" ]; then
    MSG="❌ Деплой упал — смотри Dokploy"
    break
  fi

  sleep $DELAY
  elapsed=$((elapsed + DELAY))
done

if [ $elapsed -ge $MAX_WAIT ]; then
  MSG="⚠️ Деплой завис (>10 мин) — проверь вручную"
fi

# Отправить в группу через OpenClaw
openclaw message send \
  --channel telegram \
  --to "$CHAT_ID" \
  ${THREAD_ID:+--thread-id "$THREAD_ID"} \
  --text "$MSG"
