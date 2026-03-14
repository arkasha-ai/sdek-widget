#!/usr/bin/env python3
"""
Pulse/Dashboard PREMIUM v5 — FINAL.
Fix: ring colors match metric cards, HR context, tighter system.
"""
import sys, math, uuid as uuid_mod, json, shutil
sys.path.insert(0, "/home/clawdbot/.openclaw/workspace/scripts")
from penpot_base import PenpotSession, ScreenBuilder, uid, find, BASE, H, FILE_ID, PAGE_ID, EXPORT_URL, TF
from lucide_penpot import LUCIDE_D, penpot_icon

# ─── Icons ───────────────────────────────────────────────────────────────────
def _cd(cx, cy, r):
    return (f"M {cx} {cy-r} A {r} {r} 0 1 0 {cx+r} {cy} A {r} {r} 0 0 0 {cx} {cy-r} Z")

LUCIDE_D["bell"] = [
    "M10.268 21a2 2 0 0 0 3.464 0",
    "M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326",
]
LUCIDE_D["heart"] = [
    "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z",
]
LUCIDE_D["moon"] = ["M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"]
LUCIDE_D["activity"] = [
    "M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2",
]
LUCIDE_D["chart-bar"] = ["M12 20V10", "M18 20V4", "M6 20v-4"]
LUCIDE_D["user"] = ["M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2", _cd(12, 7, 4)]
LUCIDE_D["footprints"] = [
    "M4 16v-2.38C4 11.5 2.97 10.5 3 8c.03-2.72 1.49-6 4.5-6C9.37 2 10 3.8 10 5.5 10 7.89 8 9 8 11v5",
    "M14 23v-3.38c0-2.12-1.03-3.12-1-5.62.03-2.72 1.49-6 4.5-6 1.87 0 2.5 1.8 2.5 3.5 0 2.39-2 3.5-2 5.5v6",
    "M4 16h4", "M14 23h4",
]
LUCIDE_D["map-pin"] = [
    "M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0",
    _cd(12, 10, 3),
]
LUCIDE_D["flame"] = [
    "M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z",
]
LUCIDE_D["bike"] = [
    _cd(18.5, 18, 3.5), _cd(5.5, 18, 3.5),
    "M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm-3 11.5V14l-3-3 4-3 2 3h2",
]
LUCIDE_D["chevron-right"] = ["m9 18 6-6-6-6"]
LUCIDE_D["clock"] = [_cd(12,12,10), "M12 6v6l4 2"]
LUCIDE_D["trending-up"] = ["m22 7-8.5 8.5-5-5L2 17", "M16 7h6v6"]

# ─── Color System — RINGS MATCH CARDS ────────────────────────────────────────
BG = "#0A0A0A"
CARD = "#1A1A1C"
CARD_EL = "#1E1E20"
# The 3 ring colors = 3 metric card colors
C_MOVE = "#FF4757"    # Move/Calories = RED (outer ring + calories card)
C_EXERCISE = "#4ECDC4"  # Exercise/Active = TEAL (mid ring + heart card)  
C_STAND = "#74B9FF"   # Stand/Steps = BLUE (inner ring + steps/sleep card... wait)

# Actually, let's make it a proper system:
# Outer ring = Calories (RED) → Calories card
# Middle ring = Steps (BLUE) → Steps card  
# Inner ring = Active (TEAL) → "Active" minutes
# Then separate: Heart=RED (pulse), Sleep=BLUE

# NEW cleaner approach: 3 rings → 3 matching labels below rings
RING_RED = "#FF4757"    # Calories (outer)
RING_BLUE = "#74B9FF"   # Steps (middle)
RING_TEAL = "#4ECDC4"   # Active (inner)

T1 = "#FFFFFF"
T2 = "#8E8E93"
T3 = "#636366"
T4 = "#48484A"
PAD = 24
PURPLE = "#A78BFA"
ORANGE = "#FBBF24"

def shadow_glow(color, opacity=0.15, blur=20):
    return [{"~:id":f"~u{uid()}","~:style":"~:drop-shadow",
             "~:color":{"~:color":color,"~:opacity":opacity},
             "~:offset-x":0,"~:offset-y":0,"~:blur":blur,"~:spread":0,"~:hidden":False}]

def shadow_elev(blur=16, opacity=0.15):
    return [{"~:id":f"~u{uid()}","~:style":"~:drop-shadow",
             "~:color":{"~:color":"#000000","~:opacity":opacity},
             "~:offset-x":0,"~:offset-y":4,"~:blur":blur,"~:spread":0,"~:hidden":False}]


# ─── Arc helper ──────────────────────────────────────────────────────────────
def draw_arc(sb, name, cx, cy, r, start_deg, end_deg, color, stroke_w=8, parent=None, shadow=None):
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
    oid = str(uuid_mod.uuid4())
    fid_target = parent or sb.fid
    stroke = [{"~:stroke-color":color,"~:stroke-opacity":1.0,
               "~:stroke-width":stroke_w,"~:stroke-style":"~:solid",
               "~:stroke-alignment":"~:center",
               "~:stroke-cap-start":"~:round","~:stroke-cap-end":"~:round"}]
    TF0 = {"~:a":1,"~:b":0,"~:c":0,"~:d":1,"~:e":0,"~:f":0}
    xs=[s["~:params"].get("~:x",0) for s in segs if "~:params" in s]
    ys=[s["~:params"].get("~:y",0) for s in segs if "~:params" in s]
    bx_=min(xs); by_=min(ys); bw_=max(1,max(xs)-bx_); bh_=max(1,max(ys)-by_)
    def sr(x,y,w,h): return {"~:x":x,"~:y":y,"~:width":w,"~:height":h,"~:x1":x,"~:y1":y,"~:x2":x+w,"~:y2":y+h}
    def pts(x,y,w,h): return [{"~:x":x,"~:y":y},{"~:x":x+w,"~:y":y},{"~:x":x+w,"~:y":y+h},{"~:x":x,"~:y":y+h}]
    obj = {"~:id":f"~u{oid}","~:type":"~:path","~:name":name,
           "~:frame-id":f"~u{sb.fid}","~:parent-id":f"~u{fid_target}",
           "~:x":bx_,"~:y":by_,"~:width":bw_,"~:height":bh_,
           "~:fills":[],"~:strokes":stroke,
           "~:selrect":sr(bx_,by_,bw_,bh_),"~:points":pts(bx_,by_,bw_,bh_),
           "~:transform":TF0,"~:transform-inverse":TF0,"~:content":segs}
    if shadow:
        obj["~:shadow"] = shadow
    sb._add_change(obj, sb.fid, fid_target)
    return oid


# ─── Delete existing ─────────────────────────────────────────────────────────
def delete_existing(ps):
    r = ps.s.post(f"{BASE}/get-file", headers=H,
        data=json.dumps(["^ ","~:id",f"~u{FILE_ID}","~:features",
            ["~#set",["~:fdata/pointer-map","~:fdata/objects-map","~:fdata/shape-data-type"]]]))
    data = r.json()
    if isinstance(data, list):
        pages_data = find(data, "~:pages-index")
        if pages_data:
            page = find(pages_data, f"~u{PAGE_ID}")
            if page:
                objects = find(page, "~:objects")
                if objects and isinstance(objects, list):
                    to_del = []
                    i = 0
                    while i < len(objects):
                        if isinstance(objects[i], str) and objects[i].startswith("~u"):
                            oid = objects[i].replace("~u","")
                            if i+1 < len(objects):
                                obj = objects[i+1]
                                if isinstance(obj, list):
                                    name = find(obj, "~:name")
                                    if name and ("Pulse" in str(name) or "Dashboard" in str(name)):
                                        to_del.append(oid)
                            i += 2
                        else:
                            i += 1
                    for oid in to_del:
                        r2 = ps.s.post(f"{BASE}/update-file", headers=H, data=json.dumps(
                            ["^ ","~:id",f"~u{FILE_ID}","~:revn",ps.revn,"~:vern",0,
                             "~:session-id",f"~u{uid()}",
                             "~:changes",[["^ ","~:type","~:del-obj","~:id",f"~u{oid}",
                                 "~:page-id",f"~u{PAGE_ID}"]]]))
                        res = r2.json()
                        ps.revn = find(res,"~:revn") or ps.revn+1


# ─── Build ───────────────────────────────────────────────────────────────────
def build():
    ps = PenpotSession()
    
    print("Deleting existing...")
    delete_existing(ps)
    
    sb = ScreenBuilder(ps, "Pulse/Dashboard", 0, 1000, BG)
    
    # ═══ STATUS BAR (y=0..44) ═══
    sb.text("status_time", 32, 14, 50, "9:41", fs=15, fw="600", color=T2)
    for i in range(4):
        h = 4 + i*2
        sb.rect(f"signal_{i}", 300+i*7, 18-h, 4, h, T2, r_=1)
    sb.rect("bat_outer", 332, 12, 25, 12, BG, r_=3, stroke=T2, stroke_w=1)
    sb.rect("bat_fill", 334, 14, 18, 8, T2, r_=2)
    sb.rect("bat_tip", 358, 16, 2, 5, T2, r_=1)
    
    # ═══ HEADER (y=48..88) ═══
    sb.text("greeting", PAD, 48, 200, "Good morning,", fs=14, fw="400", color=T3)
    sb.text("name", PAD, 68, 200, "Alex", fs=26, fw="700", color=T1)
    sb.icon("bell", 316, 60, 22, T3)
    sb.circle("bell_dot", 333, 58, 8, RING_RED)
    sb.circle("avatar_bg", 350, 56, 36, RING_RED)
    sb.text("avatar_letter", 350, 62, 36, "A", fs=16, fw="700", color=T1, align="center")
    
    # ═══ HERO RING (y=104..316) ═══
    ring_cx = 195
    ring_cy = 208
    
    # Ambient glow
    sb.circle("ring_glow", 195-100, ring_cy-100, 200, RING_RED, opacity=0.03)
    
    # Background tracks
    draw_arc(sb, "track_outer", ring_cx, ring_cy, 90, 0, 360, "#1C1C1E", stroke_w=11)
    draw_arc(sb, "track_mid", ring_cx, ring_cy, 72, 0, 360, "#1C1C1E", stroke_w=11)
    draw_arc(sb, "track_inner", ring_cx, ring_cy, 54, 0, 360, "#1C1C1E", stroke_w=11)
    
    # Progress arcs with glow — RED outer, BLUE mid, TEAL inner
    draw_arc(sb, "arc_move", ring_cx, ring_cy, 90, 0, 270, RING_RED, stroke_w=12,
             shadow=shadow_glow(RING_RED, 0.35, 18))
    draw_arc(sb, "arc_exercise", ring_cx, ring_cy, 72, 0, 216, RING_BLUE, stroke_w=12,
             shadow=shadow_glow(RING_BLUE, 0.3, 14))
    draw_arc(sb, "arc_stand", ring_cx, ring_cy, 54, 0, 306, RING_TEAL, stroke_w=12,
             shadow=shadow_glow(RING_TEAL, 0.3, 14))
    
    # Center: hero number
    sb.text("ring_value", 115, ring_cy-22, 160, "847", fs=48, fw="700", color=T1, align="center")
    sb.text("ring_unit", 115, ring_cy+30, 160, "kcal burned", fs=11, fw="400", color=T4, align="center")
    
    # Ring legend — color-matched labels right below rings, compact
    leg_y = 312
    leg_data = [
        (RING_RED, "Move", "847 cal"),
        (RING_BLUE, "Exercise", "8.4k steps"),
        (RING_TEAL, "Stand", "42 min"),
    ]
    leg_w = 114
    for idx, (col, lbl, val) in enumerate(leg_data):
        lx = PAD + idx * leg_w
        sb.circle(f"leg_dot_{idx}", lx+4, leg_y+4, 6, col)
        sb.text(f"leg_lbl_{idx}", lx+14, leg_y, 48, lbl, fs=11, fw="500", color=T3)
        sb.text(f"leg_val_{idx}", lx+14, leg_y+16, 80, val, fs=11, fw="600", color=T2)
    
    # Insight text (y=352)
    insight_y = 350
    sb.icon("trending-up", PAD+48, insight_y+1, 14, RING_TEAL)
    sb.text("insight", PAD+66, insight_y, 260, "12% more than last week — keep it up!",
            fs=12, fw="500", color=T3)

    # ═══ METRICS ROW (y=380..460) — 3 cards matching ring colors ═══
    metrics_y = 380
    card_w = 108
    card_h = 80
    gap = (342 - 3*card_w) // 2
    
    # Cards: Steps (BLUE=ring mid), Heart (RED=ring outer), Sleep (TEAL=ring inner)
    metric_data = [
        ("footprints", RING_BLUE, "8,420", "steps", "75%"),
        ("heart", RING_RED, "72", "bpm resting", ""),
        ("moon", RING_TEAL, "7h 20m", "sleep", "92%"),
    ]
    for idx, (ico, col, val, lbl, pct) in enumerate(metric_data):
        cx = PAD + idx * (card_w + gap)
        cfid = sb.mkframe(f"card_{idx}", cx, metrics_y, card_w, card_h,
                         bg=CARD, r_=16, shadow=shadow_elev(12, 0.2))
        
        # Colored icon bg
        sb.circle(f"ico_bg_{idx}", cx+10, metrics_y+10, 28, col, parent=cfid, opacity=0.1)
        sb.icon(ico, cx+14, metrics_y+14, 18, col, parent=cfid)
        
        # Percentage badge
        if pct:
            sb.text(f"pct_{idx}", cx+card_w-38, metrics_y+14, 30, pct,
                   fs=10, fw="600", color=col, parent=cfid, align="right")
        
        sb.text(f"val_{idx}", cx+10, metrics_y+46, card_w-20, val,
               fs=20, fw="700", color=T1, parent=cfid)
        sb.text(f"lbl_{idx}", cx+10, metrics_y+66, card_w-20, lbl,
               fs=10, fw="400", color=T4, parent=cfid)
    
    # ═══ WORKOUT CARD (y=484..608) ═══
    wo_y = metrics_y + card_h + 24
    wo_h = 124
    wo_fid = sb.mkframe("workout_card", PAD, wo_y, 342, wo_h,
                        bg=CARD_EL, r_=20,
                        shadow=shadow_elev(24, 0.3))
    
    # Accent line
    sb.rect("wo_accent", PAD+20, wo_y+1, 40, 3, RING_RED, parent=wo_fid, r_=2)
    
    sb.text("wo_today", PAD+20, wo_y+16, 60, "Today", fs=11, fw="500", color=T4, parent=wo_fid)
    sb.text("wo_title", PAD+20, wo_y+34, 180, "Morning Run", fs=20, fw="700", color=T1, parent=wo_fid)
    
    # START button
    btn_w = 88
    btn_h = 40
    btn_x = PAD + 342 - 20 - btn_w
    btn_y = wo_y + 16
    sb.rect("btn_glow", btn_x-3, btn_y-3, btn_w+6, btn_h+6, RING_RED, r_=22, opacity=0.25)
    sb.rect("btn_start_bg", btn_x, btn_y, btn_w, btn_h, RING_RED, parent=wo_fid, r_=20)
    sb.text("btn_start", btn_x, btn_y+10, btn_w, "START", fs=14, fw="700", color=T1, align="center", parent=wo_fid)
    
    # Stats
    stats_y = wo_y + 70
    for idx, (ico, txt) in enumerate([("map-pin", "5.2 km"), ("clock", "28 min"), ("flame", "312 kcal")]):
        sx = PAD + 20 + idx * 102
        sb.icon(ico, sx, stats_y+1, 13, T3, parent=wo_fid)
        sb.text(f"wo_s_{idx}", sx+17, stats_y, 80, txt, fs=13, fw="500", color=T2, parent=wo_fid)
    
    # Progress bar
    bar_y = wo_y + 100
    sb.rect("wo_bar_bg", PAD+20, bar_y, 302, 5, "#2C2C2E", parent=wo_fid, r_=3)
    sb.rect("wo_bar_fill", PAD+20, bar_y, 242, 5, RING_RED, parent=wo_fid, r_=3)
    sb.text("wo_pct", PAD+270, bar_y-8, 52, "80%", fs=10, fw="600", color=T3, parent=wo_fid, align="right")
    
    # ═══ RECENT ACTIVITY (y=632..788) ═══
    ra_y = wo_y + wo_h + 24
    sb.text("ra_title", PAD, ra_y, 200, "Recent Activity", fs=17, fw="600", color=T1)
    sb.text("ra_seeall", 290, ra_y+3, 76, "See all", fs=13, fw="500", color=RING_RED, align="right")
    
    activities = [
        (PURPLE, "activity", "Yoga Session", "Yesterday · 45 min", "186 kcal"),
        (ORANGE, "bike", "Cycling", "2 days ago · 1h 10m", "428 kcal"),
    ]
    for idx, (col, ico, title, sub, cal) in enumerate(activities):
        ry = ra_y + 36 + idx * 72
        
        row_fid = sb.mkframe(f"act_row_{idx}", PAD, ry, 342, 60,
                            bg=CARD, r_=14, shadow=shadow_elev(8, 0.08))
        
        sb.circle(f"act_bg_{idx}", PAD+10, ry+10, 40, col, parent=row_fid, opacity=0.12)
        sb.icon(ico, PAD+19, ry+19, 22, col, parent=row_fid)
        
        sb.text(f"act_t_{idx}", PAD+60, ry+12, 160, title, fs=15, fw="600", color=T1, parent=row_fid)
        sb.text(f"act_s_{idx}", PAD+60, ry+32, 160, sub, fs=11, fw="400", color=T4, parent=row_fid)
        
        sb.text(f"act_c_{idx}", PAD+238, ry+12, 68, cal, fs=13, fw="600", color=col, parent=row_fid, align="right")
        
        # Mini intensity bar
        bar_w = 40
        fill_pct = 0.6 if idx == 0 else 0.85
        sb.rect(f"act_barbg_{idx}", PAD+260, ry+38, bar_w, 3, "#2C2C2E", parent=row_fid, r_=2)
        sb.rect(f"act_bar_{idx}", PAD+260, ry+38, int(bar_w*fill_pct), 3, col, parent=row_fid, r_=2)
        
        sb.icon("chevron-right", PAD+318, ry+20, 16, T4, parent=row_fid)
    
    # ═══ NAV BAR (y=790..844) ═══
    nav_y = 790
    nav_fid = sb.mkframe("nav_bar", 0, nav_y, 390, 54, bg="#101012")
    sb.rect("nav_divider", 0, nav_y, 390, 0.5, "#222224", parent=nav_fid)
    
    for i, (icon_name, label, color, active) in enumerate([
        ("house", "Home", RING_RED, True),
        ("activity", "Activity", T4, False),
        ("chart-bar", "Stats", T4, False),
        ("user", "Profile", T4, False),
    ]):
        sx = i * 97  # 390/4
        icon_x = sx + (97 - 22) // 2
        if active:
            sb.rect(f"nav_pill_{i}", sx + 97//2 - 12, nav_y + 48, 24, 3, RING_RED,
                   parent=nav_fid, r_=2)
        sb.icon(icon_name, icon_x, nav_y + 8, 22, color, parent=nav_fid)
        sb.text(f"nav_{label}", sx, nav_y + 34, 97, label, fs=10, fw="500",
               color=color, align="center", parent=nav_fid)
    
    # Home indicator
    sb.rect("home_indicator", 390//2-67, 836, 134, 5, "#3A3A3C", r_=3)
    
    # ═══ FLUSH & EXPORT ═══
    print(f"Total changes: {len(sb.changes)}")
    sb.flush()
    
    path = ps.export_png(sb.fid, "pulse_v2_dashboard", scale=2)
    if path:
        out = "/home/clawdbot/.openclaw/workspace/drafts/pulse_v2_dashboard.png"
        shutil.copy(path, out)
        print(f"Exported → {out}")
    
    return sb.fid

if __name__ == "__main__":
    fid = build()
    print(f"Done! Artboard ID: {fid}")
