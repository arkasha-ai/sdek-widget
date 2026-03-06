#!/usr/bin/env python3
"""
Process userbot queue: read pending messages, spawn sub-agents, write responses.
Called by OpenClaw on wake event USERBOT_QUEUE.
"""

import json
import sys
import time
from pathlib import Path

QUEUE_FILE = Path("/home/clawdbot/.openclaw/workspace/memory/userbot_queue.jsonl")
RESPONSES_DIR = Path("/home/clawdbot/.openclaw/workspace/memory/userbot_responses")
RESPONSES_DIR.mkdir(exist_ok=True)

def read_pending():
    if not QUEUE_FILE.exists():
        return []
    entries = []
    lines = QUEUE_FILE.read_text().splitlines()
    for line in lines:
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            if e.get("status") == "pending":
                entries.append(e)
        except:
            pass
    return entries

def mark_processing(msg_id: str):
    if not QUEUE_FILE.exists():
        return
    lines = QUEUE_FILE.read_text().splitlines()
    new_lines = []
    for line in lines:
        try:
            e = json.loads(line)
            if e.get("id") == msg_id:
                e["status"] = "processing"
            new_lines.append(json.dumps(e, ensure_ascii=False))
        except:
            new_lines.append(line)
    QUEUE_FILE.write_text("\n".join(new_lines) + "\n")

def write_response(msg_id: str, text: str):
    resp_file = RESPONSES_DIR / f"{msg_id}.txt"
    resp_file.write_text(text)

pending = read_pending()
if not pending:
    print("No pending messages")
    sys.exit(0)

print(f"Found {len(pending)} pending messages")
for entry in pending:
    print(f"MSG: {entry['id']} from {entry['sender_name']} ({entry['username']}): {entry['text'][:80]}")
    mark_processing(entry['id'])
