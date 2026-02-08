#!/usr/bin/env python3
"""
GitHub Notifications Monitor for OpenClaw
Checks GitHub notifications API for mentions and new issues/PRs
"""
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Config
SECRETS_FILE = Path.home() / ".openclaw" / "secrets.env"
STATE_FILE = Path.home() / ".openclaw" / "workspace" / "memory" / "github-notifications-state.json"
WEBHOOK_URL = "http://127.0.0.1:18789/hooks/wake"

def load_token():
    """Load GitHub token from secrets.env"""
    token = None
    if SECRETS_FILE.exists():
        with open(SECRETS_FILE) as f:
            for line in f:
                if line.startswith("GITHUB_ARKASHA_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break
    if not token:
        raise ValueError("GITHUB_ARKASHA_TOKEN not found in secrets.env")
    return token

def load_state():
    """Load last processed notification timestamp"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_check": None, "processed_ids": []}

def save_state(state):
    """Save state to file"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def fetch_notifications(token):
    """Fetch notifications from GitHub API"""
    import urllib.request
    import urllib.error
    
    url = "https://api.github.com/notifications?per_page=50"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"GitHub API error: {e.code} {e.reason}")
        return []

def trigger_webhook(message):
    """Trigger OpenClaw webhook"""
    import urllib.request
    
    # Load webhook token
    webhook_token = None
    config_file = Path.home() / ".openclaw" / "openclaw.json"
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
            webhook_token = config.get("hooks", {}).get("token")
    
    if not webhook_token:
        print("Webhook token not found, skipping webhook")
        return
    
    payload = json.dumps({
        "text": message,
        "mode": "now"
    }).encode()
    
    headers = {
        "Authorization": f"Bearer {webhook_token}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(WEBHOOK_URL, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"Webhook triggered: {response.status}")
    except Exception as e:
        print(f"Webhook error: {e}")

def process_notifications(notifications, state):
    """Process new notifications and trigger webhook"""
    processed_ids = set(state.get("processed_ids", []))
    new_count = 0
    
    for notif in notifications:
        notif_id = notif["id"]
        if notif_id in processed_ids:
            continue
        
        # Extract info
        reason = notif["reason"]  # mention, review_requested, etc.
        repo = notif["repository"]["full_name"]
        subject_type = notif["subject"]["type"]  # Issue, PullRequest, etc.
        subject_title = notif["subject"]["title"]
        subject_url = notif["subject"]["url"]
        html_url = notif["subject"].get("html_url", subject_url)
        updated_at = notif["updated_at"]
        
        # Build message
        if reason == "mention":
            icon = "💬"
            action = "упомянули"
        elif reason == "review_requested":
            icon = "👀"
            action = "запросили review"
        elif reason == "assign":
            icon = "📌"
            action = "назначили"
        else:
            icon = "🔔"
            action = f"уведомление ({reason})"
        
        type_name = {"Issue": "issue", "PullRequest": "PR"}.get(subject_type, subject_type.lower())
        
        message = f"{icon} GitHub: тебя {action} в {repo}\n{type_name}: {subject_title}\n{html_url}"
        
        print(f"New notification: {notif_id} - {reason} - {repo}")
        trigger_webhook(message)
        
        processed_ids.add(notif_id)
        new_count += 1
    
    # Keep only last 200 processed IDs (prevent unbounded growth)
    state["processed_ids"] = list(processed_ids)[-200:]
    state["last_check"] = datetime.utcnow().isoformat()
    
    return new_count

def main():
    try:
        token = load_token()
        state = load_state()
        
        notifications = fetch_notifications(token)
        print(f"Fetched {len(notifications)} notifications")
        
        if notifications:
            new_count = process_notifications(notifications, state)
            print(f"Processed {new_count} new notifications")
        
        save_state(state)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
