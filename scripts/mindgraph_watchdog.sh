#!/bin/bash
# Watchdog для MindGraph сервера
if ! curl -sf http://127.0.0.1:18790/health > /dev/null 2>&1; then
    echo "$(date) MindGraph down, restarting..." >> /tmp/mindgraph-watchdog.log
    cd /home/clawdbot/.openclaw/workspace/skills/mindgraph-rs && bash start.sh
fi
