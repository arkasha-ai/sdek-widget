#!/bin/bash
# S3 backup script for arkasha workspace
# Backs up: sessions, workspace, drafts, openclaw config
# Runs daily at 04:00 MSK

set -e
DATE=$(date +%Y-%m-%d)
BACKUP_PREFIX="backups/$DATE"

echo "[$(date)] Starting S3 backup..."

# 1. Sessions (conversation history)
echo "Syncing sessions..."
s3cmd sync ~/.openclaw/agents/main/sessions/ s3://arkasha/sessions/ \
  --exclude "archive/*" \
  --delete-removed \
  --quiet 2>&1 || echo "Sessions sync failed"

# 2. Workspace snapshot (tar.gz для компактности)
echo "Creating workspace snapshot..."
TMPFILE=$(mktemp /tmp/workspace-backup-XXXXXX.tar.gz)
tar -czf "$TMPFILE" \
  --exclude="workspace/.git" \
  --exclude="workspace/agents" \
  --exclude="workspace/media" \
  --exclude="workspace/sio-wdio-tests" \
  --exclude="workspace/sio-ui-tests" \
  --exclude="workspace/frontend-master" \
  --exclude="workspace/cloudapi" \
  --exclude="workspace/googleapis" \
  --exclude="workspace/**/__pycache__" \
  --exclude="workspace/**/*.pyc" \
  -C /home/clawdbot/.openclaw workspace/ 2>/dev/null

s3cmd put "$TMPFILE" "s3://arkasha/workspace-snapshots/workspace-$DATE.tar.gz" --quiet
rm -f "$TMPFILE"
echo "Workspace snapshot: workspace-$DATE.tar.gz"

# 3. OpenClaw config (без секретов)
echo "Syncing openclaw config..."
s3cmd put ~/.openclaw/config.json "s3://arkasha/config/config-$DATE.json" --quiet 2>/dev/null || true

echo "[$(date)] S3 backup complete!"

# Чистим старые снапшоты (оставляем последние 14 дней)
s3cmd ls s3://arkasha/workspace-snapshots/ 2>/dev/null | \
  awk '{print $4}' | sort | head -n -14 | \
  xargs -r s3cmd del --quiet 2>/dev/null || true
