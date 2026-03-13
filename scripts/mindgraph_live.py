#!/usr/bin/env python3
"""
mindgraph_live.py — Live mode watcher for MindGraph
Watches memory/ directory and auto-ingests changes into MindGraph.

Run: python3 scripts/mindgraph_live.py
Or as a service: see scripts/mindgraph_live.service
"""

import os
import re
import sys
import time
import json
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime

import pyinotify
import urllib.request
import urllib.error

# ─── Config ──────────────────────────────────────────────────────────────────

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
MEMORY_DIR = WORKSPACE / 'memory'
SCRIPTS_DIR = WORKSPACE / 'scripts'

def load_token():
    secrets = Path.home() / '.openclaw' / 'secrets.env'
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            if line.startswith('MINDGRAPH_TOKEN='):
                return line.split('=', 1)[1].strip()
    return os.environ.get('MINDGRAPH_TOKEN', '')

BASE_URL = 'http://127.0.0.1:18790'
TOKEN = load_token()
AGENT_ID = 'arkasha'

# Debounce: don't re-ingest same file more than once per N seconds
DEBOUNCE_SEC = 10
_last_processed = {}
_lock = threading.Lock()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [mindgraph-live] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(WORKSPACE / 'memory' / 'mindgraph_live.log', mode='a'),
    ]
)
log = logging.getLogger(__name__)

# ─── MindGraph API ────────────────────────────────────────────────────────────

def mg_request(endpoint, body):
    """Make a POST request to MindGraph API."""
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {TOKEN}',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        log.warning(f"MG API {endpoint} → {e.code}: {err_body[:200]}")
        return None
    except Exception as e:
        log.error(f"MG API error {endpoint}: {e}")
        return None

def mg_ingest_observation(label, content):
    return mg_request('/reality/ingest', {
        'action': 'observation',
        'agent_id': AGENT_ID,
        'label': label,
        'content': content,
    })

def mg_find_entity(label):
    result = mg_request('/retrieve', {
        'action': 'text',
        'query': label,
        'limit': 1,
    })
    if result and len(result) > 0:
        node = result[0].get('node') or result[0]
        if node.get('label', '').lower() == label.lower():
            return node
    return None

def mg_update_entity(uid, description, summary):
    return mg_request('/evolve', {
        'action': 'update',
        'uid': uid,
        'agent_id': AGENT_ID,
        'summary': summary,
        'props_patch': {'description': description},
    })

# ─── File Processors ─────────────────────────────────────────────────────────

def process_daily_log(filepath):
    """Ingest/update a daily log file."""
    path = Path(filepath)
    date_match = re.match(r'(\d{4}-\d{2}-\d{2})\.md$', path.name)
    if not date_match:
        return
    date = date_match.group(1)
    content = path.read_text(encoding='utf-8')
    if len(content.strip()) < 50:
        return

    # Use first 2500 chars for the observation
    snippet = content[:2500]
    label = f'Дневник {date}'
    result = mg_ingest_observation(label, snippet)
    if result:
        log.info(f"📅 Ingested daily log: {date}")
    else:
        log.warning(f"⚠️ Failed to ingest daily log: {date}")

def process_people_file(filepath):
    """Update a person entity from their profile file."""
    path = Path(filepath)
    name_hint = path.stem.replace('-', ' ').title()
    content = path.read_text(encoding='utf-8')
    
    # Extract name from H1 heading
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if not h1_match:
        return
    name = h1_match.group(1).strip()
    
    # Find entity in MindGraph
    entity = mg_find_entity(name)
    if entity:
        uid = entity.get('uid')
        summary = content[:200].replace('\n', ' ')
        result = mg_update_entity(uid, content[:1500], summary[:200])
        if result:
            log.info(f"👤 Updated person: {name}")
    else:
        # Create observation with the full content
        result = mg_ingest_observation(f'Профиль: {name}', content[:2000])
        if result:
            log.info(f"👤 Ingested person profile: {name}")

def process_project_file(filepath):
    """Update a project entity from its file."""
    path = Path(filepath)
    content = path.read_text(encoding='utf-8')
    
    # Extract name from H1 heading
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if not h1_match:
        return
    name = h1_match.group(1).strip()
    # Clean up — remove suffixes like " — Единый справочник"
    name = re.split(r'\s+[—–-]\s+', name)[0].strip()
    
    entity = mg_find_entity(name)
    if entity:
        uid = entity.get('uid')
        summary = content[:200].replace('\n', ' ')
        result = mg_update_entity(uid, content[:2000], summary[:200])
        if result:
            log.info(f"📦 Updated project: {name}")
    else:
        result = mg_ingest_observation(f'Проект: {name}', content[:2000])
        if result:
            log.info(f"📦 Ingested project: {name}")

def process_memory_file(filepath):
    """Process any .md file that changed."""
    path = Path(filepath)
    
    # Debounce
    with _lock:
        last = _last_processed.get(str(path), 0)
        now = time.time()
        if now - last < DEBOUNCE_SEC:
            return
        _last_processed[str(path)] = now

    # Skip non-markdown and non-existent files
    if not path.exists() or path.suffix != '.md':
        return

    rel = path.relative_to(MEMORY_DIR)
    log.info(f"🔔 Changed: {rel}")

    parts = rel.parts
    if len(parts) == 1 and re.match(r'\d{4}-\d{2}-\d{2}\.md$', parts[0]):
        process_daily_log(filepath)
    elif len(parts) == 2 and parts[0] == 'people':
        process_people_file(filepath)
    elif len(parts) == 2 and parts[0] == 'projects':
        process_project_file(filepath)
    else:
        # Generic: ingest as observation
        content = path.read_text(encoding='utf-8')
        if len(content.strip()) > 100:
            label = f'memory/{rel}'
            result = mg_ingest_observation(label, content[:2000])
            if result:
                log.info(f"📝 Ingested generic: {rel}")

# ─── inotify Handler ──────────────────────────────────────────────────────────

class MemoryEventHandler(pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
        process_memory_file(event.pathname)

    def process_IN_MOVED_TO(self, event):
        process_memory_file(event.pathname)

    def process_IN_CREATE(self, event):
        # Handle new files
        if not event.dir:
            process_memory_file(event.pathname)

# ─── Main ─────────────────────────────────────────────────────────────────────

def health_check():
    """Check if MindGraph server is up."""
    try:
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode().strip() == 'ok'
    except:
        return False

def main():
    log.info("🚀 MindGraph Live Mode starting...")
    log.info(f"📡 Server: {BASE_URL}")
    log.info(f"📁 Watching: {MEMORY_DIR}")
    
    if not TOKEN:
        log.error("❌ MINDGRAPH_TOKEN not found!")
        sys.exit(1)

    # Wait for server
    for i in range(10):
        if health_check():
            log.info("💚 MindGraph server is healthy")
            break
        log.warning(f"⏳ Waiting for MindGraph server... ({i+1}/10)")
        time.sleep(3)
    else:
        log.error("❌ MindGraph server not responding")
        sys.exit(1)

    # Set up inotify watcher
    wm = pyinotify.WatchManager()
    mask = (
        pyinotify.IN_CLOSE_WRITE |
        pyinotify.IN_MOVED_TO |
        pyinotify.IN_CREATE
    )
    
    handler = MemoryEventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    
    wm.add_watch(
        str(MEMORY_DIR),
        mask,
        rec=True,  # Watch recursively
        auto_add=True,  # Auto-watch new subdirs
    )
    
    log.info("👀 Watching for changes (recursive)...")
    
    try:
        notifier.loop()
    except KeyboardInterrupt:
        log.info("🛑 Shutting down...")
    finally:
        notifier.stop()

if __name__ == '__main__':
    main()
