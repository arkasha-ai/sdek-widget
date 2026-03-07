#!/bin/bash
# Deploy profile files to Docker container on i9-4090-beast
set -e

CONTAINER=logera-app-front
BASE_DIR=/app/src/routes/profile

FILES=(
  "+layout.svelte"
  "+page.svelte"
  "voice/+page.svelte"
  "ai-settings/+page.svelte"
  "security/+page.svelte"
  "notifications/+page.svelte"
  "usage/+page.svelte"
  "organization/+page.svelte"
  "billing/+page.svelte"
)

SRC_DIR=/tmp/logera-profile

for f in "${FILES[@]}"; do
  echo "Deploying $f..."
  docker exec -i $CONTAINER sh -c "cat > $BASE_DIR/$f" < "$SRC_DIR/$f"
done

echo "All files deployed!"
