import json, base64, time, urllib.request, subprocess, sys
import websocket

DRAFTS = "/home/clawdbot/.openclaw/workspace/drafts"

components = [
    ("ProjectCard", "Tell me about the RAG knowledge base project"),
    ("CaseStudy", "Describe a challenging project you solved"),
    ("Timeline", "What is your work history?"),
    ("SkillCloud", "What are your main skills?"),
    ("StackList", "What is your tech stack?"),
    ("TagList", "What keywords describe you?"),
    ("MetricRow", "What are your key achievements in numbers?"),
    ("ComparisonTable", "Compare your AI consulting vs custom dev services"),
    ("PricingCalc", "How much do your services cost?"),
    ("ProcessSteps", "How do you work with clients?"),
    ("ContactForm", "I want to hire you"),
    ("BookingButton", "Can we schedule a call?"),
    ("ResumeDownload", "Can I download your resume?"),
    ("ImageGallery", "Do you have any portfolio screenshots?"),
    ("QuoteBlock", "Share a quote about your work philosophy"),
    ("CodeDemo", "Show me an example of your code"),
]

def flush_redis():
    subprocess.run(["docker", "exec", "test-backend-redis-1", "redis-cli", "FLUSHDB"], capture_output=True)

def recv_safe(ws, timeout=5):
    ws.settimeout(timeout)
    try: return json.loads(ws.recv())
    except: return None

def make_screenshot(question, filename, wait=35):
    flush_redis()
    sys.stdout.write(f"\n>>> {filename}\n"); sys.stdout.flush()
    
    req = urllib.request.Request("http://localhost:9222/json/new", method="PUT")
    resp = json.loads(urllib.request.urlopen(req).read())
    tid = resp["id"]
    ws_url = resp.get("webSocketDebuggerUrl")
    ws = websocket.create_connection(ws_url, timeout=60)
    
    for m in ["Page.enable", "Runtime.enable"]:
        ws.send(json.dumps({"id": 0, "method": m})); ws.recv()
    
    ws.send(json.dumps({"id": 3, "method": "Page.navigate", "params": {"url": "http://localhost:3000/"}}))
    
    ws.settimeout(2)
    start = time.time()
    while time.time() - start < 10:
        try:
            r = json.loads(ws.recv())
            if r.get("method") == "Page.loadEventFired": break
        except: pass
    time.sleep(3)
    
    # Type question
    js_q = json.dumps(question)
    ws.settimeout(5)
    ws.send(json.dumps({"id": 10, "method": "Runtime.evaluate", "params": {
        "expression": f"""
        (function() {{
            const input = document.querySelector('input[placeholder]') || document.querySelector('textarea');
            if (!input) return 'no input';
            input.focus();
            const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            if (nativeSet) nativeSet.call(input, {js_q});
            else input.value = {js_q};
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            return 'ok';
        }})()
        """, "returnByValue": True
    }}))
    for _ in range(10):
        r = recv_safe(ws)
        if r and r.get("id") == 10:
            sys.stdout.write(f"  input: {r['result']['result'].get('value')}\n"); sys.stdout.flush()
            break
    
    time.sleep(0.3)
    
    # Press Enter
    ws.send(json.dumps({"id": 12, "method": "Input.dispatchKeyEvent", "params": {
        "type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13
    }}))
    recv_safe(ws, 2)
    ws.send(json.dumps({"id": 13, "method": "Input.dispatchKeyEvent", "params": {
        "type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13
    }}))
    recv_safe(ws, 2)
    
    sys.stdout.write(f"  waiting {wait}s...\n"); sys.stdout.flush()
    time.sleep(wait)
    
    # Scroll down
    ws.send(json.dumps({"id": 50, "method": "Runtime.evaluate", "params": {
        "expression": "window.scrollTo(0, document.body.scrollHeight); document.body.scrollHeight",
        "returnByValue": True
    }}))
    recv_safe(ws, 3)
    time.sleep(1)
    
    # Screenshot
    ws.send(json.dumps({"id": 99, "method": "Page.captureScreenshot", "params": {"format": "png", "captureBeyondViewport": True}}))
    ws.settimeout(15)
    path = None
    for _ in range(30):
        try:
            r = json.loads(ws.recv())
            if r.get("id") == 99:
                data = base64.b64decode(r["result"]["data"])
                path = f"{DRAFTS}/{filename}"
                with open(path, "wb") as f: f.write(data)
                sys.stdout.write(f"  ✅ {len(data)//1024}KB\n"); sys.stdout.flush()
                break
        except: break
    
    ws.close()
    try: urllib.request.urlopen(f"http://localhost:9222/json/close/{tid}")
    except: pass
    return path

# Clean up old tabs
try:
    tabs = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
    for tab in tabs[1:]:
        try: urllib.request.urlopen(f"http://localhost:9222/json/close/{tab['id']}")
        except: pass
except: pass

results = {}
for name, question in components:
    path = make_screenshot(question, f"comp_{name}.png", wait=35)
    results[name] = path
    time.sleep(2)

print("\n\n=== RESULTS ===")
for name, path in results.items():
    print(f"{'✅' if path else '❌'} {name}: {path}")
