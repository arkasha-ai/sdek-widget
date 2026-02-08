#!/usr/bin/env python3
"""
IMAP IDLE Listener - Event-driven email notifications for OpenClaw
Listens to multiple IMAP accounts and triggers webhook on new emails
"""
import imaplib
import json
import os
import sys
import time
import urllib.request
import threading
from email.header import decode_header
from pathlib import Path

# Load credentials
SECRETS_PATH = Path.home() / ".openclaw/secrets.env"
HIMALAYA_CONFIG = Path.home() / ".config/himalaya/config.toml"
WORKSPACE = Path.home() / ".openclaw/workspace"

# OpenClaw webhook config
WEBHOOK_URL = "http://127.0.0.1:18789/hooks/wake"
WEBHOOK_TOKEN = "f016901f219067c9d30dea113c41576057c71e4d068d6363"

# IMAP accounts to monitor (all use same password and server)
ACCOUNTS = {
    "dparmeev": {
        "host": "mail.hosting.reg.ru",
        "port": 993,
        "username": "dparmeev@luminesfox.com",
        "password": None,  # loaded from secrets
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

def decode_email_header(header):
    """Decode email header (handles encoded subjects)"""
    if header is None:
        return ""
    
    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
        else:
            decoded_parts.append(str(part))
    
    return ' '.join(decoded_parts)

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
    """IDLE listener for one account"""
    print(f"Starting listener for {name} ({config['username']})")
    
    reconnect_delay = 5
    max_reconnect_delay = 300  # 5 minutes
    last_processed_id = None  # Track last processed email ID
    
    while True:
        mail = None
        try:
            # Connect
            mail = imaplib.IMAP4_SSL(config['host'], config['port'])
            mail.login(config['username'], config['password'])
            mail.select(config['folder'])
            
            print(f"✅ Connected to {name}")
            reconnect_delay = 5  # Reset delay on successful connection
            
            # Get current latest message ID (to avoid re-processing old messages)
            if last_processed_id is None:
                try:
                    status, messages = mail.search(None, 'ALL')
                    if status == 'OK' and messages[0]:
                        email_ids = messages[0].split()
                        if email_ids:
                            last_processed_id = email_ids[-1].decode() if isinstance(email_ids[-1], bytes) else email_ids[-1]
                            print(f"📫 {name}: Starting from message ID {last_processed_id}")
                except:
                    pass
            
            idle_start = time.time()
            while True:
                try:
                    # Start IDLE
                    tag = mail._new_tag().decode()
                    mail.send(f'{tag} IDLE\r\n'.encode())
                    
                    # Wait for response with timeout (5 minutes)
                    mail.sock.settimeout(300)
                    
                    try:
                        response = mail.readline()
                        has_response = bool(response)
                    except Exception:
                        # Timeout - no new messages
                        has_response = False
                    
                    # Exit IDLE
                    mail.send(b'DONE\r\n')
                    mail.sock.settimeout(30)  # Reset timeout
                    mail.readline()  # Read DONE completion
                    
                    if has_response:
                        # New message detected (any mailbox change)
                        # Fetch ALL messages (sorted by date, get last 5)
                        status, messages = mail.search(None, 'ALL')
                        if status == 'OK' and messages[0]:
                            email_ids = messages[0].split()
                            if email_ids:
                                # Get the latest message (last in the list)
                                latest_id = email_ids[-1].decode() if isinstance(email_ids[-1], bytes) else email_ids[-1]
                                
                                # Only process if this is a new message
                                if latest_id != last_processed_id:
                                    # Fetch headers
                                    status, msg_data = mail.fetch(latest_id, '(BODY[HEADER.FIELDS (FROM SUBJECT)])')
                                    
                                    if status == 'OK':
                                        raw_email = msg_data[0][1].decode('utf-8', errors='ignore')
                                        
                                        from_addr = ""
                                        subject = ""
                                        
                                        for line in raw_email.split('\n'):
                                            if line.lower().startswith('from:'):
                                                from_addr = decode_email_header(line[5:].strip())
                                            elif line.lower().startswith('subject:'):
                                                subject = decode_email_header(line[8:].strip())
                                        
                                        # Trigger webhook (OpenClaw will decide if important)
                                        trigger_webhook(name, from_addr, subject)
                                        
                                        # Update last processed ID
                                        last_processed_id = latest_id
                    
                    # Periodic refresh (every 15 minutes, reconnect)
                    if time.time() - idle_start > 900:
                        print(f"🔄 Refreshing connection for {name}")
                        raise Exception("Periodic refresh")
                    
                    # Send NOOP to keep connection alive
                    mail.noop()
                
                except Exception as idle_err:
                    # IDLE error or refresh - will reconnect
                    print(f"⚠️  IDLE error for {name}: {idle_err}")
                    raise
        
        except Exception as e:
            print(f"❌ {name} error: {e}")
            
            if mail:
                try:
                    mail.logout()
                except:
                    pass
            
            # Exponential backoff
            print(f"Reconnecting {name} in {reconnect_delay}s...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

def main():
    """Start all IMAP IDLE listeners"""
    print("🦞 IMAP IDLE Listener for OpenClaw")
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
