#!/usr/bin/env python3
"""Check fal.ai balance by sending a minimal test request.
If balance is exhausted — alert Denis via Telegram.
"""
import os, sys, json, requests
from pathlib import Path

# Load secrets
secrets = {}
secrets_file = Path.home() / ".openclaw/secrets.env"
if secrets_file.exists():
    for line in secrets_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            secrets[k.strip()] = v.strip()

FAL_API_KEY = secrets.get("FAL_API_KEY") or os.environ.get("FAL_API_KEY", "")

if not FAL_API_KEY:
    print("FAL_API_KEY not found")
    sys.exit(0)

# Minimal test request to check if account is locked
try:
    resp = requests.post(
        "https://fal.run/fal-ai/flux-2-flex/edit",
        headers={"Authorization": f"Key {FAL_API_KEY}", "Content-Type": "application/json"},
        json={"prompt": "balance_check", "image_urls": []},
        timeout=10,
    )
    detail = ""
    try:
        detail = resp.json().get("detail", "")
    except Exception:
        pass

    if resp.status_code in (402, 403) and ("locked" in detail.lower() or "exhausted" in detail.lower()):
        print(f"ALERT:FAL_BALANCE_EXHAUSTED")
        sys.exit(1)
    else:
        print(f"OK: fal.ai account active (status={resp.status_code})")
        sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(0)  # Network error — don't alert
