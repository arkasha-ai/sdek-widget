#!/usr/bin/env python3
"""
Fix Nota chips - v3. Uses get-page API to get all objects at once, 
then batch-modifies chip texts.
"""
import requests, json, uuid, sys

BASE = "https://penpot.jakeberrimor.com/api/rpc/command"
H = {"Content-Type": "application/transit+json"}
FILE_ID = "4b85babb-b10c-8109-8007-b44132d2992f"
PAGE_ID = "4b85babb-b10c-8109-8007-b44132d29930"

def uid(): return str(uuid.uuid4())
def find(arr, key):
    if not isinstance(arr, list): return None
    for i,v in enumerate(arr):
        if v==key and i+1<len(arr): return arr[i+1]
    return None

s = requests.Session()
s.post(f"{BASE}/login-with-password", headers=H,
    data='["^ ","~:email","spam@jakeberrimor.com","~:password","q25RiI#L"]')

# Get revn
r = s.post(f"{BASE}/update-file", headers=H,
    data=json.dumps(["^ ","~:id",f"~u{FILE_ID}","~:revn",0,"~:vern",0,
                     "~:session-id",f"~u{uid()}","~:changes",[]]))
revn = find(r.json(),"~:revn") or 0
print(f"revn={revn}")

# Get page data
r = s.post(f"{BASE}/get-file", headers=H,
    data=json.dumps(["^ ","~:id",f"~u{FILE_ID}","~:features",
                     {"~#set":["~:components/v2","~:styles/v2","~:flex/auto-fill"]}]))

page_data = r.json()
# Parse transit response to find objects
raw = r.text

# Instead of parsing the full page, let's use a targeted approach
# Find chip text objects via search, get their parent frame info, then batch fix

import subprocess

# Get chip text objects that need fixing
result = subprocess.run([
    "mcporter", "call", "penpot-mcp.search_object",
    "--args", json.dumps({"file_id": FILE_ID, "query": "(Chip|chip|TagChip|mchip|Cat Chip)"}),
    "--output", "json"
], capture_output=True, text=True, timeout=30)

data = json.loads(result.stdout)
text_ids = [o["id"] for o in data["objects"] if o["object_type"] == "text"]
frame_ids = [o["id"] for o in data["objects"] if o["object_type"] == "frame"]

print(f"Found {len(text_ids)} text objects, {len(frame_ids)} frame objects")

# Now get details for each frame and its children in a batch
# To speed things up, let's get 5 frames at a time
from concurrent.futures import ThreadPoolExecutor
import time

def get_frame_tree(frame_id):
    try:
        result = subprocess.run([
            "mcporter", "call", "penpot-mcp.get_object_tree",
            "--args", json.dumps({
                "file_id": FILE_ID,
                "object_id": frame_id,
                "fields": ["name","type","x","y","width","height","content"],
                "depth": 2
            }),
            "--output", "json"
        ], capture_output=True, text=True, timeout=10)
        return json.loads(result.stdout).get("tree")
    except:
        return None

# Process frames in parallel
print("Getting frame trees...")
trees = {}
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(get_frame_tree, fid): fid for fid in frame_ids}
    for future in futures:
        fid = futures[future]
        try:
            tree = future.result(timeout=15)
            if tree:
                trees[fid] = tree
        except:
            pass

print(f"Got {len(trees)} frame trees")

# Collect all modifications needed
fixes = []
for fid, tree in trees.items():
    frame_y = tree["y"]
    frame_h = tree["height"]
    
    for child in tree.get("children", []):
        if child.get("type") != "text":
            continue
        content = child.get("content", {})
        va = content.get("verticalAlign", "")
        if va != "center":
            continue
        
        child_id = child["id"]
        child_name = child.get("name", "?")
        
        # Get font size
        fs = 14
        try:
            para = content["children"][0]["children"][0]
            tc = para["children"][0]
            fs = int(tc.get("fontSize", "14"))
        except:
            pass
        
        # Old formula
        ty = frame_y + (frame_h - fs * 1.4) / 2
        th = fs * 2
        
        # Build content without va
        transit_content = {"~:type": "root", "~:children": [
            {"~:type": "paragraph-set", "~:children": []}
        ]}
        try:
            for ps_child in content.get("children", []):
                if ps_child.get("type") != "paragraph-set":
                    continue
                for para in ps_child.get("children", []):
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
                            "~:fills": [{"~:fill-color": f.get("fillColor","#000"),
                                         "~:fill-opacity": f.get("fillOpacity",1.0)}
                                        for f in tc.get("fills", [])]
                        }
                        for k, tk in [("fontStyle","~:font-style"),("textTransform","~:text-transform"),
                                      ("textDecoration","~:text-decoration"),("letterSpacing","~:letter-spacing")]:
                            if k in tc: t_child[tk] = tc[k]
                        t_para["~:children"].append(t_child)
                    transit_content["~:children"][0]["~:children"].append(t_para)
        except Exception as e:
            continue
        
        fixes.append({
            "id": child_id,
            "name": child_name,
            "frame": tree.get("name", "?"),
            "ty": ty,
            "th": th,
            "content": transit_content
        })

print(f"\nNeed to fix {len(fixes)} chip texts")

# Apply fixes in batches of 10
batch_size = 10
fixed = 0
for i in range(0, len(fixes), batch_size):
    batch = fixes[i:i+batch_size]
    changes = []
    for fix in batch:
        change = ["^ ", "~:type", "~:mod-obj",
                  "~:id", f"~u{fix['id']}",
                  "~:page-id", f"~u{PAGE_ID}",
                  "~:operations", [
                      ["^ ", "~:type", "~:set", "~:attr", "~:y", "~:val", fix["ty"]],
                      ["^ ", "~:type", "~:set", "~:attr", "~:height", "~:val", fix["th"]],
                      ["^ ", "~:type", "~:set", "~:attr", "~:content", "~:val", fix["content"]],
                  ]]
        changes.append(change)
    
    payload = json.dumps(["^ ",
        "~:id", f"~u{FILE_ID}",
        "~:revn", revn,
        "~:vern", 0,
        "~:session-id", f"~u{uid()}",
        "~:changes", changes
    ])
    
    r = s.post(f"{BASE}/update-file", headers=H, data=payload)
    res = r.json()
    new_revn = find(res, "~:revn")
    err = find(res, "~:explain")
    
    if err:
        print(f"  Batch {i//batch_size}: ERR {str(err)[:200]}")
        # Try one by one
        for fix in batch:
            single_change = ["^ ", "~:type", "~:mod-obj",
                            "~:id", f"~u{fix['id']}",
                            "~:page-id", f"~u{PAGE_ID}",
                            "~:operations", [
                                ["^ ", "~:type", "~:set", "~:attr", "~:y", "~:val", fix["ty"]],
                                ["^ ", "~:type", "~:set", "~:attr", "~:height", "~:val", fix["th"]],
                                ["^ ", "~:type", "~:set", "~:attr", "~:content", "~:val", fix["content"]],
                            ]]
            payload2 = json.dumps(["^ ",
                "~:id", f"~u{FILE_ID}",
                "~:revn", revn,
                "~:vern", 0,
                "~:session-id", f"~u{uid()}",
                "~:changes", [single_change]
            ])
            r2 = s.post(f"{BASE}/update-file", headers=H, data=payload2)
            res2 = r2.json()
            new_revn2 = find(res2, "~:revn")
            err2 = find(res2, "~:explain")
            if new_revn2:
                revn = new_revn2
                fixed += 1
                print(f"    OK: {fix['name']} in {fix['frame']}")
            elif err2:
                print(f"    FAIL: {fix['name']}: {str(err2)[:100]}")
            else:
                revn += 1
                fixed += 1
    elif new_revn:
        revn = new_revn
        fixed += len(batch)
        names = [f['name'] for f in batch]
        print(f"  Batch {i//batch_size}: OK ({', '.join(names[:3])}...)")
    else:
        revn += 1
        fixed += len(batch)

print(f"\nFixed {fixed} of {len(fixes)} chip texts")
print("Done!")
