#!/usr/bin/env bash
# Dokploy API helper script
# Usage:
#   ./dokploy-api.sh GET project.all
#   ./dokploy-api.sh POST application.deploy '{"applicationId":"xxx"}'
#   ./dokploy-api.sh GET application.one applicationId=xxx
#
# Requires: DOKPLOY_API_URL and DOKPLOY_API_KEY in ~/.openclaw/secrets.env

set -euo pipefail

# Load secrets
SECRETS_FILE="${HOME}/.openclaw/secrets.env"
if [[ -f "$SECRETS_FILE" ]]; then
  source "$SECRETS_FILE"
else
  echo "ERROR: $SECRETS_FILE not found" >&2
  exit 1
fi

if [[ -z "${DOKPLOY_API_URL:-}" ]] || [[ -z "${DOKPLOY_API_KEY:-}" ]]; then
  echo "ERROR: DOKPLOY_API_URL and DOKPLOY_API_KEY must be set" >&2
  exit 1
fi

METHOD="${1:?Usage: dokploy-api.sh METHOD ENDPOINT [BODY_OR_PARAMS]}"
ENDPOINT="${2:?Usage: dokploy-api.sh METHOD ENDPOINT [BODY_OR_PARAMS]}"
EXTRA="${3:-}"

API="${DOKPLOY_API_URL}/api"

if [[ "$METHOD" == "GET" ]]; then
  URL="${API}/${ENDPOINT}"
  if [[ -n "$EXTRA" ]]; then
    URL="${URL}?${EXTRA}"
  fi
  curl -s -H "x-api-key: $DOKPLOY_API_KEY" "$URL" | jq .
elif [[ "$METHOD" == "POST" ]]; then
  if [[ -n "$EXTRA" ]]; then
    curl -s -X POST \
      -H "x-api-key: $DOKPLOY_API_KEY" \
      -H "Content-Type: application/json" \
      "${API}/${ENDPOINT}" \
      -d "$EXTRA" | jq .
  else
    curl -s -X POST \
      -H "x-api-key: $DOKPLOY_API_KEY" \
      -H "Content-Type: application/json" \
      "${API}/${ENDPOINT}" | jq .
  fi
else
  echo "ERROR: Unknown method $METHOD. Use GET or POST." >&2
  exit 1
fi
