#!/bin/bash
# Auto-commit identity files to track drift
# Run from heartbeat or manually
cd ~/.openclaw/workspace

# Check if any identity files changed
if git diff --quiet SOUL.md AGENTS.md IDENTITY.md MEMORY.md 2>/dev/null; then
    exit 0  # No changes
fi

git add SOUL.md AGENTS.md IDENTITY.md MEMORY.md
git commit -m "identity snapshot: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null
echo "Identity snapshot committed"
