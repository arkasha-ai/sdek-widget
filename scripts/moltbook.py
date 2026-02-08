#!/usr/bin/env python3
"""
Moltbook CLI - Interact with Moltbook social network
"""

import json
import sys
import os
import requests
from pathlib import Path
from datetime import datetime

BASE_URL = "https://www.moltbook.com/api/v1"
CREDS_PATH = Path.home() / ".config/moltbook/credentials.json"

def load_credentials():
    """Load API credentials from config file"""
    if not CREDS_PATH.exists():
        print(json.dumps({"error": "Not registered. Run: python3 moltbook.py register"}))
        sys.exit(1)
    
    with open(CREDS_PATH) as f:
        return json.load(f)

def make_request(method, endpoint, data=None, params=None):
    """Make authenticated request to Moltbook API"""
    creds = load_credentials()
    headers = {
        "Authorization": f"Bearer {creds['api_key']}",
        "Content-Type": "application/json"
    }
    
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            resp = requests.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def cmd_register(args):
    """Register a new agent"""
    if len(args) < 2:
        print(json.dumps({"error": "Usage: moltbook.py register <name> <description>"}))
        return
    
    name = args[0]
    description = " ".join(args[1:])
    
    data = {"name": name, "description": description}
    
    try:
        resp = requests.post(f"{BASE_URL}/agents/register", json=data)
        result = resp.json()
        
        if "agent" in result:
            # Save credentials
            CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
            creds = {
                "api_key": result["agent"]["api_key"],
                "agent_name": name,
                "profile_url": f"https://www.moltbook.com/u/{name}",
                "claim_url": result["agent"]["claim_url"],
                "verification_code": result["agent"]["verification_code"],
                "registered_at": datetime.now().isoformat()
            }
            with open(CREDS_PATH, "w") as f:
                json.dump(creds, f, indent=2)
        
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

def cmd_status(args):
    """Check claim status"""
    result = make_request("GET", "/agents/status")
    print(json.dumps(result, indent=2))

def cmd_me(args):
    """Get your profile"""
    result = make_request("GET", "/agents/me")
    print(json.dumps(result, indent=2))

def cmd_feed(args):
    """Get your personalized feed"""
    sort = args[0] if args else "hot"
    limit = int(args[1]) if len(args) > 1 else 25
    
    params = {"sort": sort, "limit": limit}
    result = make_request("GET", "/feed", params=params)
    print(json.dumps(result, indent=2))

def cmd_posts(args):
    """Get posts (optionally from a submolt)"""
    params = {"sort": "hot", "limit": 25}
    
    if "--submolt" in args:
        idx = args.index("--submolt")
        if idx + 1 < len(args):
            params["submolt"] = args[idx + 1]
    
    if "--sort" in args:
        idx = args.index("--sort")
        if idx + 1 < len(args):
            params["sort"] = args[idx + 1]
    
    if "--limit" in args:
        idx = args.index("--limit")
        if idx + 1 < len(args):
            params["limit"] = int(args[idx + 1])
    
    result = make_request("GET", "/posts", params=params)
    print(json.dumps(result, indent=2))

def cmd_post(args):
    """Create a new post"""
    if len(args) < 3:
        print(json.dumps({"error": "Usage: moltbook.py post <submolt> <title> <content>"}))
        return
    
    submolt = args[0]
    title = args[1]
    content = " ".join(args[2:])
    
    data = {
        "submolt": submolt,
        "title": title,
        "content": content
    }
    
    result = make_request("POST", "/posts", data=data)
    print(json.dumps(result, indent=2))

def cmd_comment(args):
    """Add a comment to a post"""
    if len(args) < 2:
        print(json.dumps({"error": "Usage: moltbook.py comment <post_id> <content>"}))
        return
    
    post_id = args[0]
    content = " ".join(args[1:])
    
    data = {"content": content}
    result = make_request("POST", f"/posts/{post_id}/comments", data=data)
    print(json.dumps(result, indent=2))

def cmd_comments(args):
    """Get comments for a post"""
    if not args:
        print(json.dumps({"error": "Usage: moltbook.py comments <post_id> [--limit N]"}))
        return
    
    post_id = args[0]
    params = {"limit": 50}
    
    if "--limit" in args:
        idx = args.index("--limit")
        if idx + 1 < len(args):
            params["limit"] = int(args[idx + 1])
    
    result = make_request("GET", f"/posts/{post_id}/comments", params=params)
    print(json.dumps(result, indent=2))

def cmd_upvote(args):
    """Upvote a post"""
    if not args:
        print(json.dumps({"error": "Usage: moltbook.py upvote <post_id>"}))
        return
    
    post_id = args[0]
    result = make_request("POST", f"/posts/{post_id}/upvote")
    print(json.dumps(result, indent=2))

def cmd_search(args):
    """Semantic search"""
    if not args:
        print(json.dumps({"error": "Usage: moltbook.py search <query> [--type posts|comments|all] [--limit N]"}))
        return
    
    # Parse args
    query_parts = []
    params = {"limit": 20, "type": "all"}
    
    i = 0
    while i < len(args):
        if args[i] == "--type" and i + 1 < len(args):
            params["type"] = args[i + 1]
            i += 2
        elif args[i] == "--limit" and i + 1 < len(args):
            params["limit"] = int(args[i + 1])
            i += 2
        else:
            query_parts.append(args[i])
            i += 1
    
    params["q"] = " ".join(query_parts)
    result = make_request("GET", "/search", params=params)
    print(json.dumps(result, indent=2))

def cmd_submolts(args):
    """List all submolts"""
    result = make_request("GET", "/submolts")
    print(json.dumps(result, indent=2))

def cmd_subscribe(args):
    """Subscribe to a submolt"""
    if not args:
        print(json.dumps({"error": "Usage: moltbook.py subscribe <submolt_name>"}))
        return
    
    submolt = args[0]
    result = make_request("POST", f"/submolts/{submolt}/subscribe")
    print(json.dumps(result, indent=2))

def cmd_profile(args):
    """View another molty's profile"""
    if not args:
        print(json.dumps({"error": "Usage: moltbook.py profile <molty_name>"}))
        return
    
    name = args[0]
    params = {"name": name}
    result = make_request("GET", "/agents/profile", params=params)
    print(json.dumps(result, indent=2))

def cmd_follow(args):
    """Follow another molty"""
    if not args:
        print(json.dumps({"error": "Usage: moltbook.py follow <molty_name>"}))
        return
    
    name = args[0]
    result = make_request("POST", f"/agents/{name}/follow")
    print(json.dumps(result, indent=2))

def cmd_verify(args):
    """Verify a comment or post"""
    if len(args) < 2:
        print(json.dumps({"error": "Usage: moltbook.py verify <verification_code> <answer>"}))
        return
    
    code = args[0]
    answer = args[1]
    
    data = {
        "verification_code": code,
        "answer": answer
    }
    
    result = make_request("POST", "/verify", data=data)
    print(json.dumps(result, indent=2))

def main():
    if len(sys.argv) < 2:
        print("Usage: moltbook.py <command> [args...]")
        print("\nCommands:")
        print("  register <name> <description>  - Register a new agent")
        print("  status                          - Check claim status")
        print("  me                              - Get your profile")
        print("  feed [sort] [limit]             - Get personalized feed")
        print("  posts [--submolt X] [--sort X]  - Get posts")
        print("  post <submolt> <title> <text>   - Create post")
        print("  comment <post_id> <text>        - Add comment")
        print("  comments <post_id> [--limit N]  - Get comments for post")
        print("  upvote <post_id>                - Upvote a post")
        print("  search <query> [--type X]       - Semantic search")
        print("  submolts                        - List all submolts")
        print("  subscribe <submolt>             - Subscribe to submolt")
        print("  profile <molty>                 - View molty profile")
        print("  follow <molty>                  - Follow a molty")
        print("  verify <code> <answer>          - Verify comment/post")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        "register": cmd_register,
        "status": cmd_status,
        "me": cmd_me,
        "feed": cmd_feed,
        "posts": cmd_posts,
        "post": cmd_post,
        "comment": cmd_comment,
        "comments": cmd_comments,
        "upvote": cmd_upvote,
        "search": cmd_search,
        "submolts": cmd_submolts,
        "subscribe": cmd_subscribe,
        "profile": cmd_profile,
        "follow": cmd_follow,
        "verify": cmd_verify,
    }
    
    if command in commands:
        commands[command](args)
    else:
        print(json.dumps({"error": f"Unknown command: {command}"}))

if __name__ == "__main__":
    main()
