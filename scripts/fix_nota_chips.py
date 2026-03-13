#!/usr/bin/env python3
"""
Fix Nota app chips centering issue.
Find all chip text objects with va="center" and revert to OLD FORMULA.
OLD FORMULA: ty = container_y + (container_h - fs * 1.4) / 2, height = fs * 2
"""
import sys, json, uuid
sys.path.insert(0, "/home/clawdbot/.openclaw/workspace/scripts")
from penpot_base import PenpotSession, uid, sr, pts, TF, find

ps = PenpotSession()

FILE_ID = "4b85babb-b10c-8109-8007-b44132d2992f"
PAGE_ID = "4b85babb-b10c-8109-8007-b44132d29930"

# Get the full page to find all chip text objects
# Use search to find chip frames first
import subprocess
result = subprocess.run([
    "mcporter", "call", "penpot-mcp.search_object",
    "--args", json.dumps({"file_id": FILE_ID, "query": "(Chip|chip|pill|Cat Chip)"}),
    "--output", "json"
], capture_output=True, text=True, timeout=30)

data = json.loads(result.stdout)
chip_frames = [o for o in data["objects"] if o["object_type"] == "frame"]
chip_texts = [o for o in data["objects"] if o["object_type"] == "text"]

print(f"Found {len(chip_frames)} chip frames, {len(chip_texts)} chip texts")

# For each chip frame, get its tree to check if text inside has va="center"
fixed_count = 0
checked = 0

for cf in chip_frames:
    cf_id = cf["id"]
    cf_name = cf["name"]
    
    # Get tree
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
    
    # Check children for text objects with va="center"
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
        
        if va == "center":
            # This text has va="center" - need to check if parent is artboard-level
            child_id = child["id"]
            child_name = child.get("name", "?")
            
            # Get font size from content
            fs = 14  # default
            try:
                para = content["children"][0]["children"][0]
                text_child = para["children"][0]
                fs = int(text_child.get("fontSize", "14"))
            except:
                pass
            
            # Calculate old formula position
            # ty = container_y + (container_h - fs * 1.4) / 2
            ty = frame_y + (frame_h - fs * 1.4) / 2
            th = fs * 2
            
            print(f"  FIX: {child_name} in {cf_name} | frame=({frame_x},{frame_y},{frame_w}x{frame_h}) | fs={fs} | old_y={child['y']} -> new_y={ty:.1f}")
            
            # Build the modified content (remove verticalAlign, set to top)
            new_content = dict(content)
            if "verticalAlign" in new_content:
                del new_content["verticalAlign"]
            
            # Convert to transit format for the API
            # We need to use mod-obj to change x, y, width, height and content
            changes = [
                ["^ ", "~:type", "~:mod-obj",
                 "~:id", f"~u{child_id}",
                 "~:page-id", f"~u{PAGE_ID}",
                 "~:operations", [
                     ["^ ", "~:type", "~:set", "~:attr", "~:y", "~:val", ty],
                     ["^ ", "~:type", "~:set", "~:attr", "~:height", "~:val", th],
                     ["^ ", "~:type", "~:set", "~:attr", "~:selrect", "~:val", sr(child["x"], ty, child["width"], th)],
                     ["^ ", "~:type", "~:set", "~:attr", "~:points", "~:val", pts(child["x"], ty, child["width"], th)],
                 ]]
            ]
            
            # Also update content to remove vertical-align
            # Build transit content
            transit_content = {
                "~:type": "root",
                "~:children": [{
                    "~:type": "paragraph-set",
                    "~:children": [{
                        "~:type": "paragraph",
                        "~:text-align": "center",
                        "~:paragraph-spacing": 0,
                        "~:children": []
                    }]
                }]
            }
            
            # Copy text children
            try:
                para = content["children"][0]["children"][0]
                text_align = para.get("textAlign", "center")
                transit_content["~:children"][0]["~:children"][0]["~:text-align"] = text_align
                
                for tc in para.get("children", []):
                    transit_child = {
                        "~:text": tc.get("text", ""),
                        "~:font-size": str(tc.get("fontSize", "14")),
                        "~:font-family": tc.get("fontFamily", "Inter"),
                        "~:font-weight": str(tc.get("fontWeight", "400")),
                        "~:line-height": tc.get("lineHeight", "1.4"),
                        "~:fills": []
                    }
                    # Copy fills
                    for f in tc.get("fills", []):
                        transit_child["~:fills"].append({
                            "~:fill-color": f.get("fillColor", "#000000"),
                            "~:fill-opacity": f.get("fillOpacity", 1.0)
                        })
                    # Copy optional attrs
                    if "fontStyle" in tc:
                        transit_child["~:font-style"] = tc["fontStyle"]
                    if "textTransform" in tc:
                        transit_child["~:text-transform"] = tc["textTransform"]
                    if "textDecoration" in tc:
                        transit_child["~:text-decoration"] = tc["textDecoration"]
                    if "letterSpacing" in tc:
                        transit_child["~:letter-spacing"] = tc["letterSpacing"]
                    
                    transit_content["~:children"][0]["~:children"][0]["~:children"].append(transit_child)
            except Exception as e:
                print(f"    WARN: failed to parse content: {e}")
                continue
            
            # Add content change
            changes[0][-1].append(
                ["^ ", "~:type", "~:set", "~:attr", "~:content", "~:val", transit_content]
            )
            
            # Also remove grow-type if it was set to fixed
            changes[0][-1].append(
                ["^ ", "~:type", "~:set", "~:attr", "~:grow-type", "~:val", None]
            )
            
            # Send the change
            H = {"Content-Type": "application/transit+json"}
            payload = json.dumps(["^ ",
                "~:id", f"~u{FILE_ID}",
                "~:revn", ps.revn,
                "~:vern", 0,
                "~:session-id", f"~u{uid()}",
                "~:changes", changes
            ])
            
            r = ps.s.post(f"https://penpot.jakeberrimor.com/api/rpc/command/update-file",
                         headers=H, data=payload)
            res = r.json()
            new_revn = find(res, "~:revn")
            if new_revn:
                ps.revn = new_revn
                fixed_count += 1
            else:
                err = find(res, "~:explain")
                if err:
                    print(f"    ERR: {str(err)[:150]}")
                else:
                    ps.revn += 1
                    fixed_count += 1

print(f"\nChecked {checked} chip texts, fixed {fixed_count} with va='center'")
print("Done!")
