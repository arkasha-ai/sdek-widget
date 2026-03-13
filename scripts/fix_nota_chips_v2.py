#!/usr/bin/env python3
"""
Fix Nota app chips centering - v2
Uses correct mod-obj operations format.
"""
import sys, json, uuid, subprocess
sys.path.insert(0, "/home/clawdbot/.openclaw/workspace/scripts")
from penpot_base import sr, pts, TF

BASE = "https://penpot.jakeberrimor.com/api/rpc/command"
EXPORT_URL = "https://penpot.jakeberrimor.com/api/export"
H = {"Content-Type": "application/transit+json"}
FILE_ID = "4b85babb-b10c-8109-8007-b44132d2992f"
PAGE_ID = "4b85babb-b10c-8109-8007-b44132d29930"

import requests
s = requests.Session()
s.post(f"{BASE}/login-with-password", headers=H,
    data='["^ ","~:email","spam@jakeberrimor.com","~:password","q25RiI#L"]')

def uid(): return str(uuid.uuid4())

def find(arr, key):
    if not isinstance(arr, list): return None
    for i,v in enumerate(arr):
        if v==key and i+1<len(arr): return arr[i+1]
    return None

# Get current revn
r = s.post(f"{BASE}/update-file", headers=H,
    data=json.dumps(["^ ","~:id",f"~u{FILE_ID}","~:revn",0,"~:vern",0,
                     "~:session-id",f"~u{uid()}","~:changes",[]]))
revn = find(r.json(),"~:revn") or 0
print(f"revn={revn}")

# Find all chip frames
result = subprocess.run([
    "mcporter", "call", "penpot-mcp.search_object",
    "--args", json.dumps({"file_id": FILE_ID, "query": "(Chip|chip|pill|Cat Chip|TagChip|mchip)"}),
    "--output", "json"
], capture_output=True, text=True, timeout=30)

data = json.loads(result.stdout)
chip_frames = [o for o in data["objects"] if o["object_type"] == "frame"]
print(f"Found {len(chip_frames)} chip frames")

fixed_count = 0
checked = 0
errors = 0

for cf in chip_frames:
    cf_id = cf["id"]
    cf_name = cf["name"]
    
    result2 = subprocess.run([
        "mcporter", "call", "penpot-mcp.get_object_tree",
        "--args", json.dumps({
            "file_id": FILE_ID,
            "object_id": cf_id,
            "fields": ["name", "type", "x", "y", "width", "height", "content", "parent-id", "frame-id"],
            "depth": 2
        }),
        "--output", "json"
    ], capture_output=True, text=True, timeout=15)
    
    try:
        tree = json.loads(result2.stdout)["tree"]
    except:
        continue
    
    if "children" not in tree:
        continue
    
    frame_x = tree["x"]
    frame_y = tree["y"]
    frame_w = tree["width"]
    frame_h = tree["height"]
    
    for child in tree.get("children", []):
        if child.get("type") != "text":
            continue
        
        content = child.get("content", {})
        va = content.get("verticalAlign", "")
        
        checked += 1
        
        if va != "center":
            continue
        
        child_id = child["id"]
        child_name = child.get("name", "?")
        
        # Get font size
        fs = 14
        try:
            para = content["children"][0]["children"][0]
            text_child = para["children"][0]
            fs = int(text_child.get("fontSize", "14"))
        except:
            pass
        
        # OLD FORMULA
        ty = frame_y + (frame_h - fs * 1.4) / 2
        th = fs * 2
        
        # Build transit content WITHOUT verticalAlign
        transit_content = {"~:type": "root", "~:children": [
            {"~:type": "paragraph-set", "~:children": []}
        ]}
        
        try:
            for ps_child in content["children"]:
                if ps_child.get("type") != "paragraph-set":
                    continue
                for para in ps_child.get("children", []):
                    if para.get("type") != "paragraph":
                        continue
                    t_para = {
                        "~:type": "paragraph",
                        "~:text-align": para.get("textAlign", "center"),
                        "~:paragraph-spacing": para.get("paragraphSpacing", 0),
                        "~:children": []
                    }
                    for tc in para.get("children", []):
                        t_child = {
                            "~:text": tc.get("text", ""),
                            "~:font-size": str(tc.get("fontSize", "14")),
                            "~:font-family": tc.get("fontFamily", "Inter"),
                            "~:font-weight": str(tc.get("fontWeight", "400")),
                            "~:line-height": str(tc.get("lineHeight", "1.4")),
                            "~:fills": []
                        }
                        for f in tc.get("fills", []):
                            t_child["~:fills"].append({
                                "~:fill-color": f.get("fillColor", "#000000"),
                                "~:fill-opacity": f.get("fillOpacity", 1.0)
                            })
                        for k in ["fontStyle", "textTransform", "textDecoration", "letterSpacing"]:
                            if k in tc:
                                transit_key = "~:" + "".join(
                                    ["-"+c.lower() if c.isupper() else c for c in k]
                                ).lstrip("-")
                                t_child[transit_key] = tc[k]
                        t_para["~:children"].append(t_child)
                    transit_content["~:children"][0]["~:children"].append(t_para)
        except Exception as e:
            print(f"    WARN parse: {e}")
            continue
        
        # Build mod-obj change - use individual set operations
        operations = []
        # Set y
        operations.append(["^ ", "~:type", "~:set", "~:attr", "~:y", "~:val", ty])
        # Set height
        operations.append(["^ ", "~:type", "~:set", "~:attr", "~:height", "~:val", th])
        # Set content (without va center)
        operations.append(["^ ", "~:type", "~:set", "~:attr", "~:content", "~:val", transit_content])
        
        change = ["^ ", "~:type", "~:mod-obj",
                  "~:id", f"~u{child_id}",
                  "~:page-id", f"~u{PAGE_ID}",
                  "~:operations", operations]
        
        payload = json.dumps(["^ ",
            "~:id", f"~u{FILE_ID}",
            "~:revn", revn,
            "~:vern", 0,
            "~:session-id", f"~u{uid()}",
            "~:changes", [change]
        ])
        
        r = s.post(f"{BASE}/update-file", headers=H, data=payload)
        res = r.json()
        new_revn = find(res, "~:revn")
        err = find(res, "~:explain")
        
        if err:
            errors += 1
            if errors <= 3:
                print(f"  ERR {child_name}: {str(err)[:120]}")
        elif new_revn:
            revn = new_revn
            fixed_count += 1
            print(f"  OK: {child_name} in {cf_name}")
        else:
            revn += 1
            fixed_count += 1
            print(f"  OK: {child_name} in {cf_name} (revn assumed)")

print(f"\nChecked {checked} chip texts, fixed {fixed_count}, errors {errors}")
