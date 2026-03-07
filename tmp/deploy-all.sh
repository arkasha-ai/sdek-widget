#!/bin/bash
# Deploys all profile files to docker container
set -e
DIR=/home/clawdbot/.openclaw/workspace/tmp/logera-profile
CONTAINER=logera-app-front
BASE=/app/src/routes/profile

FILES=(
  "+page.svelte:+page.svelte"
  "voice/+page.svelte:voice/+page.svelte"
  "ai-settings/+page.svelte:ai-settings/+page.svelte"
  "security/+page.svelte:security/+page.svelte"
  "notifications/+page.svelte:notifications/+page.svelte"
  "usage/+page.svelte:usage/+page.svelte"
  "organization/+page.svelte:organization/+page.svelte"
  "billing/+page.svelte:billing/+page.svelte"
)

for entry in "${FILES[@]}"; do
  src="${entry%%:*}"
  dst="${entry##*:}"
  b64=$(base64 -w0 "$DIR/$src")
  echo "$b64" | base64 -d | docker exec -i $CONTAINER sh -c "cat > $BASE/$dst"
  echo "Deployed $dst"
done

echo "All done!"
