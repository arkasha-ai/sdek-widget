#!/usr/bin/env python3
"""
IMAP IDLE Listener v2 - Using imapclient library
Event-driven email notifications for OpenClaw
"""
import json
import os
import sys
import time
import urllib.request
import threading
from pathlib import Path
from imapclient import IMAPClient

# Load credentials
SECRETS_PATH = Path.home() / ".openclaw/secrets.env"

# OpenClaw webhook config
WEBHOOK_URL = "http://127.0.0.1:18789/hooks/wake"
WEBHOOK_TOKEN = "f016901f219067c9d30dea113c41576057c71e4d068d6363"

# IMAP accounts to monitor (all use same password and server)
ACCOUNTS = {
    "dparmeev": {
        "host": "mail.hosting.reg.ru",
        "port": 993,
        "username": "dparmeev@luminesfox.com",
        "password": None,
        "folder": "INBOX"
    },
    "spam": {
        "host": "mail.hosting.reg.ru",
        "port": 993,
        "username": "spam@jakeberrimor.com",
        "password": None,
        "folder": "INBOX"
    },
    "contact": {
        "host": "mail.hosting.reg.ru",
        "port": 993,
        "username": "contact@jakeberrimor.com",
        "password": None,
        "folder": "INBOX"
    },
    "contact-lumines": {
        "host": "mail.hosting.reg.ru",
        "port": 993,
        "username": "contact@luminesfox.com",
        "password": None,
        "folder": "INBOX"
    }
}

def load_secrets():
    """Load passwords from secrets.env"""
    if not SECRETS_PATH.exists():
        print(f"Error: {SECRETS_PATH} not found")
        sys.exit(1)
    
    secrets = {}
    with open(SECRETS_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                secrets[key] = value.strip().strip('"').strip("'")
    
    # All accounts use same password
    imap_password = secrets.get("IMAP_PASSWORD")
    
    if not imap_password:
        print("Error: IMAP_PASSWORD not found in secrets.env")
        sys.exit(1)
    
    # Set password for all accounts
    for name in ACCOUNTS:
        ACCOUNTS[name]["password"] = imap_password

def trigger_webhook(account, from_addr, subject):
    """Send webhook to OpenClaw"""
    text = f"📧 New email in {account}: {from_addr} - {subject}"
    
    payload = {
        "text": text[:500],  # Limit length
        "mode": "now"
    }
    
    headers = {
        "Authorization": f"Bearer {WEBHOOK_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"✅ Webhook sent for {account}: {subject[:50]}")
            else:
                print(f"⚠️  Webhook failed ({response.status}) for {account}")
    
    except Exception as e:
        print(f"❌ Webhook error for {account}: {e}")

def listen_account(name, config):
    """IDLE listener for one account using imapclient"""
    print(f"Starting listener for {name} ({config['username']})")
    
    reconnect_delay = 5
    max_reconnect_delay = 300
    last_seen_uid = None
    
    while True:
        client = None
        try:
            # Connect with SSL
            client = IMAPClient(config['host'], port=config['port'], ssl=True, timeout=30)
            client.login(config['username'], config['password'])
            client.select_folder(config['folder'])
            
            print(f"✅ Connected to {name}")
            reconnect_delay = 5  # Reset delay
            
            # Get current highest UID to avoid processing old messages
            if last_seen_uid is None:
                messages = client.search(['ALL'])
                if messages:
                    last_seen_uid = max(messages)
                    print(f"📫 {name}: Starting from UID {last_seen_uid}")
            
            # Start IDLE mode
            client.idle()
            print(f"🔄 {name}: IDLE mode active")
            
            # Wait for events (with periodic refresh every 5 minutes)
            idle_start = time.time()
            
            while True:
                # Check for new messages (with 5 minute timeout)
                responses = client.idle_check(timeout=300)
                
                # Refresh IDLE every 15 minutes to keep connection alive
                if time.time() - idle_start > 900:
                    print(f"🔄 {name}: Refreshing IDLE connection")
                    client.idle_done()
                    client.noop()
                    client.idle()
                    idle_start = time.time()
                
                # Process responses
                if responses:
                    # Exit IDLE to process
                    client.idle_done()
                    
                    # Check for new messages
                    messages = client.search(['ALL'])
                    if messages:
                        latest_uid = max(messages)
                        
                        # Only process if this is a NEW message
                        if latest_uid != last_seen_uid:
                            # Fetch headers
                            msg_data = client.fetch([latest_uid], ['BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)]'])
                            
                            if latest_uid in msg_data:
                                raw_headers = msg_data[latest_uid][b'BODY[HEADER.FIELDS (FROM SUBJECT)]'].decode('utf-8', errors='ignore')
                                
                                from_addr = ""
                                subject = ""
                                
                                for line in raw_headers.split('\n'):
                                    if line.lower().startswith('from:'):
                                        from_addr = line[5:].strip()
                                    elif line.lower().startswith('subject:'):
                                        subject = line[8:].strip()
                                
                                # Send webhook
                                trigger_webhook(name, from_addr, subject)
                                
                                # Update last seen UID
                                last_seen_uid = latest_uid
                    
                    # Re-enter IDLE mode
                    client.idle()
        
        except Exception as e:
            print(f"❌ {name} error: {e}")
            
            if client:
                try:
                    client.logout()
                except:
                    pass
            
            # Exponential backoff
            print(f"Reconnecting {name} in {reconnect_delay}s...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

def main():
    """Start all IMAP IDLE listeners"""
    print("🦞 IMAP IDLE Listener v2 (imapclient)")
    print(f"Webhook: {WEBHOOK_URL}")
    
    # Load passwords
    load_secrets()
    
    # Start thread for each account
    threads = []
    for name, config in ACCOUNTS.items():
        if config['password']:
            thread = threading.Thread(
                target=listen_account,
                args=(name, config),
                daemon=True,
                name=f"imap-{name}"
            )
            thread.start()
            threads.append(thread)
            print(f"Started thread for {name}")
        else:
            print(f"Skipping {name} (no password)")
    
    if not threads:
        print("No accounts to monitor!")
        sys.exit(1)
    
    print(f"\n✅ Monitoring {len(threads)} accounts")
    print("Press Ctrl+C to stop\n")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
            # Health check
            alive = sum(1 for t in threads if t.is_alive())
            if alive < len(threads):
                print(f"⚠️  Warning: Only {alive}/{len(threads)} threads alive")
    
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
