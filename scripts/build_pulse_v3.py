#!/usr/bin/env python3
"""Build Pulse/Dashboard V3 — PREMIUM with gradients, blur, glow shadows."""
import sys, json, math, uuid as uuid_mod
sys.path.insert(0, "/home/clawdbot/.openclaw/workspace/scripts")
from penpot_base import PenpotSession, ScreenBuilder, uid, find, BASE, H, FILE_ID, PAGE_ID, EXPORT_URL

# ── Delete ALL existing Pulse/Dashboard artboards ──
ps = PenpotSession()

import subprocess as _sp, re as _re
_r = _sp.run(["mcporter","call","penpot-mcp.search_object",
    f"file_id={FILE_ID}","query=Pulse/Dashboard"],
    capture_output=True,text=True,timeout=20)
_ids = _re.findall(r'"id":\s*"([a-f0-9-]{36})"', _r.stdout)
print(f"Deleting {len(_ids)} existing Pulse/Dashboard artboards...")
if _ids:
    _changes = [["^ ","~:type","~:del-obj","~:id",f"~u{i}","~:page-id",f"~u{PAGE_ID}"] for i in _ids]
    _res = ps.s.post(f"{BASE}/update-file", headers=H, data=json.dumps(
        ["^ ","~:id",f"~u{FILE_ID}","~:revn",ps.revn,"~:vern",0,
         "~:session-id",f"~u{uid()}","~:changes",_changes])).json()
    ps.revn = find(_res,"~:revn") or ps.revn+1
    print(f"  Deleted. revn={ps.revn}")

# ── Colors ──
BG = "#0A0A0A"
SURFACE = "#141414"
CARD = "#1E1E1E"
BRD = "#282828"
RED = "#FF4757"
RED2 = "#FF6B81"
TEAL = "#4ECDC4"
TEAL2 = "#45B7D1"
BLUE = "#74B9FF"
BLUE2 = "#A29BFE"
T1 = "#FFFFFF"
T2 = "#888888"
T3 = "#333333"

TF0 = {"~:a":1,"~:b":0,"~:c":0,"~:d":1,"~:e":0,"~:f":0}

def sr(x,y,w,h):
    return {"~:x":x,"~:y":y,"~:width":w,"~:height":h,"~:x1":x,"~:y1":y,"~:x2":x+w,"~:y2":y+h}

def pts(x,y,w,h):
    return [{"~:x":x,"~:y":y},{"~:x":x+w,"~:y":y},{"~:x":x+w,"~:y":y+h},{"~:x":x,"~:y":y+h}]

def fill(c, a=1.0):
    return {"~:fill-color":c,"~:fill-opacity":a}

def grad_fill(c1, c2, sx=0, sy=0, ex=1, ey=1, o1=1.0, o2=1.0):
    return {"~:fill-color-gradient":{
        "~:type":"~:linear","~:start-x":sx,"~:start-y":sy,"~:end-x":ex,"~:end-y":ey,"~:width":1.0,
        "~:stops":[{"~:color":c1,"~:opacity":o1,"~:offset":0.0},
                   {"~:color":c2,"~:opacity":o2,"~:offset":1.0}]}}

def shadow_glow(color, blur=12, opacity=0.4):
    return [{"~:id":f"~u{uid()}","~:style":"~:drop-shadow",
             "~:color":{"~:color":color,"~:opacity":opacity},
             "~:offset-x":0,"~:offset-y":0,"~:blur":blur,"~:spread":4,"~:hidden":False},
            {"~:id":f"~u{uid()}","~:style":"~:drop-shadow",
             "~:color":{"~:color":color,"~:opacity":opacity*0.5},
             "~:offset-x":0,"~:offset-y":0,"~:blur":blur*2,"~:spread":0,"~:hidden":False}]

def shadow_elevation():
    return [{"~:id":f"~u{uid()}","~:style":"~:drop-shadow",
             "~:color":{"~:color":"#000000","~:opacity":0.5},
             "~:offset-x":0,"~:offset-y":6,"~:blur":24,"~:spread":2,"~:hidden":False},
            {"~:id":f"~u{uid()}","~:style":"~:drop-shadow",
             "~:color":{"~:color":"#000000","~:opacity":0.2},
             "~:offset-x":0,"~:offset-y":1,"~:blur":4,"~:spread":0,"~:hidden":False}]

# ── Build Screen ──
sb = ScreenBuilder(ps, "Pulse/Dashboard", 0, 1000, BG)

# ── BG Glow circles ──
def add_glow_circle(name, rx, ry, d, color, opacity, blend, blur_val=40):
    ax, ay = sb.x + rx, sb.y + ry
    oid = uid()
    blur_obj = {"~:id": f"~u{uid()}", "~:type": "~:layer-blur", "~:value": blur_val, "~:hidden": False, "~:expand-value": 0}
    obj = {"~:id":f"~u{oid}","~:type":"~:circle","~:name":name,
           "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{sb.fid}",
           "~:x":ax,"~:y":ay,"~:width":d,"~:height":d,
           "~:fills":[fill(color, opacity)],
           "~:blend-mode":f"~:{blend}",
           "~:blur":blur_obj,
           "~:selrect":sr(ax,ay,d,d),"~:points":pts(ax,ay,d,d),
           "~:transform":TF0,"~:transform-inverse":TF0}
    sb._add_change(obj, sb.fid, sb.fid)

# Multiple layered ambient glows for atmosphere
add_glow_circle("glow_red_1", -100, 40, 300, RED, 0.12, "screen", 80)
add_glow_circle("glow_red_2", 50, 100, 200, RED2, 0.06, "screen", 50)
add_glow_circle("glow_teal_1", 200, 380, 280, TEAL, 0.08, "screen", 70)
add_glow_circle("glow_blue_1", 280, 200, 160, BLUE, 0.04, "screen", 40)

# ── STATUS BAR ──
sb.text("status_time", 30, 14, 50, "9:41", fs=15, fw="600", color=T2)
for i in range(4):
    h = 4 + i*2
    sb.rect(f"signal_{i}", 308+i*6, 20-h, 4, h, T2, r_=1)
sb.rect("battery_outer", 340, 14, 25, 11, BG, r_=3, stroke=T2, stroke_w=1)
sb.rect("battery_fill", 342, 16, 18, 7, T2, r_=2)
sb.rect("battery_tip", 366, 18, 2, 5, T2, r_=1)

# ── HEADER ──
sb.text("greeting", 24, 54, 200, "Good morning,", fs=12, fw="400", color=T2)
sb.text("name_alex", 24, 72, 200, "Alex", fs=24, fw="700", color=T1)
# Bell icon
sb.icon("bell", 298, 60, 24, T2)
# Avatar with gradient
ax_av, ay_av = sb.x + 330, sb.y + 57
oid_av = uid()
obj_av = {"~:id":f"~u{oid_av}","~:type":"~:circle","~:name":"avatar_bg",
       "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{sb.fid}",
       "~:x":ax_av,"~:y":ay_av,"~:width":38,"~:height":38,
       "~:fills":[grad_fill(RED, RED2, 0, 0, 1, 1)],
       "~:selrect":sr(ax_av,ay_av,38,38),"~:points":pts(ax_av,ay_av,38,38),
       "~:transform":TF0,"~:transform-inverse":TF0}
sb._add_change(obj_av, sb.fid, sb.fid)
sb.text("avatar_letter", 330, 57, 38, "A", fs=14, fw="600", color=T1, align="center")

# ── HERO RING ──
cx, cy = 195, 242  # center of rings relative to screen

# Background circles
def draw_ring_bg(name, r, stroke_w=14):
    d = r*2
    rx = cx - r
    ry = cy - r
    ax, ay = sb.x + rx, sb.y + ry
    oid = uid()
    obj = {"~:id":f"~u{oid}","~:type":"~:circle","~:name":name,
           "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{sb.fid}",
           "~:x":ax,"~:y":ay,"~:width":d,"~:height":d,
           "~:fills":[],
           "~:strokes":[{"~:stroke-color":"#1E1E1E","~:stroke-opacity":1.0,
                         "~:stroke-width":stroke_w,"~:stroke-style":"~:solid",
                         "~:stroke-alignment":"~:center"}],
           "~:selrect":sr(ax,ay,d,d),"~:points":pts(ax,ay,d,d),
           "~:transform":TF0,"~:transform-inverse":TF0}
    sb._add_change(obj, sb.fid, sb.fid)

draw_ring_bg("ring_bg_outer", 98, 14)
draw_ring_bg("ring_bg_mid", 78, 14)
draw_ring_bg("ring_bg_inner", 58, 14)

# Arc helper
def draw_arc(name, r, start_deg, end_deg, color, stroke_w=14, glow_color=None):
    s_rad = math.radians(start_deg - 90)
    e_rad = math.radians(end_deg - 90)
    dth = e_rad - s_rad
    n = max(1, math.ceil(abs(dth)/(math.pi/2)))
    segs = []
    mx = cx + r * math.cos(s_rad)
    my = cy + r * math.sin(s_rad)
    segs.append({"~:command":"~:move-to","~:params":{"~:x":sb.x+mx,"~:y":sb.y+my}})
    for i in range(n):
        t1 = s_rad + i*dth/n
        t2 = s_rad + (i+1)*dth/n
        dt = t2 - t1
        k = math.tan(dt/4)*4/3
        ex1,ey1 = math.cos(t1),math.sin(t1)
        ex2,ey2 = math.cos(t2),math.sin(t2)
        bx1 = ex1 - k*ey1; by1 = ey1 + k*ex1
        bx2 = ex2 + k*ey2; by2 = ey2 - k*ex2
        p1=(sb.x+cx+r*bx1, sb.y+cy+r*by1)
        p2=(sb.x+cx+r*bx2, sb.y+cy+r*by2)
        p3=(sb.x+cx+r*ex2, sb.y+cy+r*ey2)
        segs.append({"~:command":"~:curve-to","~:params":{
            "~:c1x":p1[0],"~:c1y":p1[1],"~:c2x":p2[0],"~:c2y":p2[1],
            "~:x":p3[0],"~:y":p3[1]}})
    oid = uid()
    stroke = [{"~:stroke-color":color,"~:stroke-opacity":1.0,
               "~:stroke-width":stroke_w,"~:stroke-style":"~:solid",
               "~:stroke-alignment":"~:center",
               "~:stroke-cap-start":"~:round","~:stroke-cap-end":"~:round"}]
    xs=[s["~:params"].get("~:x",0) for s in segs if "~:params" in s]
    ys=[s["~:params"].get("~:y",0) for s in segs if "~:params" in s]
    bx_=min(xs); by_=min(ys); bw_=max(1,max(xs)-bx_); bh_=max(1,max(ys)-by_)
    obj = {"~:id":f"~u{oid}","~:type":"~:path","~:name":name,
           "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{sb.fid}",
           "~:x":bx_,"~:y":by_,"~:width":bw_,"~:height":bh_,
           "~:fills":[],"~:strokes":stroke,
           "~:selrect":sr(bx_,by_,bw_,bh_),"~:points":pts(bx_,by_,bw_,bh_),
           "~:transform":TF0,"~:transform-inverse":TF0,"~:content":segs}
    if glow_color:
        obj["~:shadow"] = shadow_glow(glow_color, 12, 0.4)
    sb._add_change(obj, sb.fid, sb.fid)

draw_arc("arc_cal", 98, 0, 270, RED, 14, RED)
draw_arc("arc_steps", 78, 0, 216, BLUE, 14, BLUE) 
draw_arc("arc_active", 58, 0, 306, TEAL, 14, TEAL)

# Add glow circles behind arcs for more luminous effect
add_glow_circle("arc_glow_red", cx-120, cy-120, 240, RED, 0.07, "screen", 35)
add_glow_circle("arc_glow_blue", cx-90, cy-90, 180, BLUE, 0.05, "screen", 30)
add_glow_circle("arc_glow_teal", cx-70, cy-70, 140, TEAL, 0.05, "screen", 25)

# Center text
sb.text("ring_val", 135, 222, 120, "847", fs=36, fw="700", color=T1, align="center")
sb.text("ring_unit", 135, 262, 120, "kcal", fs=13, fw="400", color=T2, align="center")
sb.text("ring_goal", 135, 280, 120, "12% above goal ↑", fs=11, fw="500", color=RED2, align="center")

# ── RING LEGEND (integrated, subtle) ──
legend_y = 368
dots_x = [66, 152, 244]
labels = ["Calories", "Steps", "Active"]
colors_leg = [RED, BLUE, TEAL]
for i, (lx, lbl, col) in enumerate(zip(dots_x, labels, colors_leg)):
    sb.circle(f"leg_dot_{i}", lx, legend_y+4, 6, col)
    sb.text(f"leg_lbl_{i}", lx+10, legend_y+1, 65, lbl, fs=11, fw="400", color=T2)

# ── METRICS ROW ──
metrics_y = 392
cards_data = [
    (20,  "8,420", "steps", "footprints", BLUE),
    (140, "72",    "bpm",   "heart",      RED),
    (260, "7h 20m","sleep", "moon",       TEAL),
]
for mx, val, lbl, ico, col in cards_data:
    cfid = sb.mkframe(f"Card/{lbl}", mx, metrics_y, 110, 76, bg=CARD, r_=14, 
                      shadow=shadow_elevation(), stroke=BRD, stroke_w=1)
    # Top highlight edge for glass effect
    ax_hl, ay_hl = sb.x + mx, sb.y + metrics_y
    oid_hl = uid()
    obj_hl = {"~:id":f"~u{oid_hl}","~:type":"~:rect","~:name":f"m_highlight_{lbl}",
           "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{cfid}",
           "~:x":ax_hl,"~:y":ay_hl,"~:width":110,"~:height":2,
           "~:fills":[grad_fill(T1, CARD, 0.1, 0, 0.9, 0, 0.06, 0.0)],
           "~:r1":14,"~:r2":14,"~:r3":0,"~:r4":0,
           "~:selrect":sr(ax_hl,ay_hl,110,2),"~:points":pts(ax_hl,ay_hl,110,2),
           "~:transform":TF0,"~:transform-inverse":TF0}
    sb._add_change(obj_hl, sb.fid, cfid)
    # Subtle gradient overlay for depth  
    ax_go, ay_go = sb.x + mx, sb.y + metrics_y
    oid_go = uid()
    obj_go = {"~:id":f"~u{oid_go}","~:type":"~:rect","~:name":f"m_grad_{lbl}",
           "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{cfid}",
           "~:x":ax_go,"~:y":ay_go,"~:width":110,"~:height":76,
           "~:fills":[grad_fill(col, CARD, 0, 0, 0.3, 1, 0.06, 0.0)],
           "~:r1":14,"~:r2":14,"~:r3":14,"~:r4":14,
           "~:selrect":sr(ax_go,ay_go,110,76),"~:points":pts(ax_go,ay_go,110,76),
           "~:transform":TF0,"~:transform-inverse":TF0}
    sb._add_change(obj_go, sb.fid, cfid)
    # Colored left accent strip matching ring color
    sb.rect(f"m_accent_{lbl}", mx, metrics_y+8, 3, 60, col, parent=cfid, r_=2, opacity=0.6)
    sb.text(f"m_val_{lbl}", mx+16, metrics_y+14, 76, val, fs=17, fw="600", color=T1, parent=cfid)
    sb.text(f"m_lbl_{lbl}", mx+16, metrics_y+36, 76, lbl, fs=10, fw="400", color=T2, parent=cfid)
    sb.icon(ico, mx+16, metrics_y+52, 16, col, parent=cfid)

# ── TODAY CARD ──
today_y = 484
today_fid = sb.mkframe("Today Card", 24, today_y, 342, 116, bg=CARD, r_=16, 
                       shadow=shadow_elevation(), clip=True, stroke=BRD, stroke_w=1)
# Gradient strip at top
ax_strip, ay_strip = sb.x + 24, sb.y + today_y
oid_strip = uid()
obj_strip = {"~:id":f"~u{oid_strip}","~:type":"~:rect","~:name":"today_gradient_strip",
       "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{today_fid}",
       "~:x":ax_strip,"~:y":ay_strip,"~:width":342,"~:height":3,
       "~:fills":[grad_fill(RED, RED2, 0, 0, 1, 0, 0.9, 0.2)],
       "~:r1":0,"~:r2":0,"~:r3":0,"~:r4":0,
       "~:selrect":sr(ax_strip,ay_strip,342,3),"~:points":pts(ax_strip,ay_strip,342,3),
       "~:transform":TF0,"~:transform-inverse":TF0}
sb._add_change(obj_strip, sb.fid, today_fid)

sb.text("today_label", 38, today_y+18, 200, "TODAY'S WORKOUT", fs=10, fw="500", color=T2, parent=today_fid)
sb.text("today_title", 38, today_y+36, 200, "Morning Run", fs=20, fw="700", color=T1, parent=today_fid)
# Stats
sb.icon("map-pin", 14, today_y+68, 14, T2, parent=today_fid)
sb.text("today_km", 32, today_y+66, 58, "5.2 km", fs=12, fw="400", color=T2, parent=today_fid)
sb.icon("clock", 94, today_y+68, 14, T2, parent=today_fid)
sb.text("today_time", 112, today_y+66, 58, "28 min", fs=12, fw="400", color=T2, parent=today_fid)
sb.icon("flame", 174, today_y+68, 14, T2, parent=today_fid)
sb.text("today_cal", 192, today_y+66, 58, "312 kcal", fs=12, fw="400", color=T2, parent=today_fid)

# START button with gradient
ax_btn, ay_btn = sb.x + 254, sb.y + today_y + 42
oid_btn = uid()
obj_btn = {"~:id":f"~u{oid_btn}","~:type":"~:rect","~:name":"start_btn",
       "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{today_fid}",
       "~:x":ax_btn,"~:y":ay_btn,"~:width":80,"~:height":32,
       "~:fills":[grad_fill(RED, RED2, 0, 0, 1, 1)],
       "~:r1":16,"~:r2":16,"~:r3":16,"~:r4":16,
       "~:selrect":sr(ax_btn,ay_btn,80,32),"~:points":pts(ax_btn,ay_btn,80,32),
       "~:shadow":shadow_glow(RED, 20, 0.5),
       "~:transform":TF0,"~:transform-inverse":TF0}
sb._add_change(obj_btn, sb.fid, today_fid)
sb.text_centered("start_txt", 254, today_y+42, 80, 32, "START", fs=12, fw="600", color=T1, parent=today_fid)

# ── RECENT ACTIVITY ──
ra_y = 612
sb.text("ra_title", 24, ra_y, 200, "Recent Activity", fs=15, fw="600", color=T1)
sb.text("ra_see_all", 282, ra_y, 84, "See all →", fs=12, fw="500", color=RED, align="right")

# Activity rows in card containers
def activity_row(name, y, c1, c2, letter, title, subtitle, kcal, kcal_color):
    # Card container
    row_fid = sb.mkframe(f"ActRow/{name}", 24, y, 342, 60, bg=CARD, r_=14, 
                         shadow=shadow_elevation(), stroke=BRD, stroke_w=1)
    # Gradient circle
    ax_c, ay_c = sb.x + 30, sb.y + y + 10
    oid_c = uid()
    obj_c = {"~:id":f"~u{oid_c}","~:type":"~:circle","~:name":f"act_circle_{name}",
           "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{row_fid}",
           "~:x":ax_c,"~:y":ay_c,"~:width":40,"~:height":40,
           "~:fills":[grad_fill(c1, c2, 0, 0, 1, 1)],
           "~:selrect":sr(ax_c,ay_c,40,40),"~:points":pts(ax_c,ay_c,40,40),
           "~:transform":TF0,"~:transform-inverse":TF0}
    sb._add_change(obj_c, sb.fid, row_fid)
    # Use icon instead of letter - map name to icon
    ico_map = {"yoga": "star", "cycling": "activity"}
    ico_name = ico_map.get(name, "star")
    sb.icon(ico_name, 44, y+20, 16, T1, parent=row_fid)
    sb.text(f"act_title_{name}", 86, y+14, 160, title, fs=14, fw="600", color=T1, parent=row_fid)
    sb.text(f"act_sub_{name}", 86, y+32, 160, subtitle, fs=12, fw="400", color=T2, parent=row_fid)
    sb.text(f"act_kcal_{name}", 280, y+18, 80, kcal, fs=13, fw="600", color=kcal_color, align="right", parent=row_fid)

activity_row("yoga", ra_y+30, TEAL, TEAL2, "Y", "Yoga", "Yesterday · 45 min", "+186 kcal", TEAL)
activity_row("cycling", ra_y+100, BLUE, BLUE2, "C", "Cycling", "2 days ago · 1h 10m", "+428 kcal", BLUE)

# ── NAV BAR ──
nav_y = 790
nav_fid = sb.mkframe("Nav Bar", 0, nav_y, 390, 54, bg=SURFACE)
sb.rect("nav_top_border", 0, nav_y, 390, 1, BRD, parent=nav_fid)

nav_items = [("house", "Home", True), ("activity", "Activity", False), ("bar-chart-2", "Stats", False), ("user", "Profile", False)]
slot_w = 97
for i, (ico, lbl, active) in enumerate(nav_items):
    sx = 1 + i * slot_w  # +1 to center 4*97=388 in 390px
    col = RED if active else "#48484A"
    sb.icon(ico, sx + (slot_w-24)//2, nav_y+10, 24, col, parent=nav_fid)
    sb.text(f"nav_{lbl}", sx, nav_y+37, slot_w, lbl, fs=10, fw="500", color=col, align="center", parent=nav_fid)
    if active:
        sb.rect("nav_active_dot", sx + (slot_w-24)//2, nav_y+35, 24, 2, RED, parent=nav_fid, r_=1)

# ── Flush ──
sb.flush()
print("Done building Pulse/Dashboard V3!")

# ── Export ──
import shutil
out_path = "/home/clawdbot/.openclaw/workspace/drafts/pulse_v3_dashboard.png"
export_path = ps.export_png(sb.fid, "pulse_v3_dashboard", scale=2)
if export_path:
    shutil.copy(export_path, out_path)
    print(f"Exported to {out_path}")
else:
    print("Export failed!")
