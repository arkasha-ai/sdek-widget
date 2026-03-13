#!/usr/bin/env python3
"""
Build PULSE fitness app - 4 screens in Penpot.
Dark theme, 390x844px screens at y=1000.
"""
import sys
sys.path.insert(0, "/home/clawdbot/.openclaw/workspace/scripts")
from penpot_base import PenpotSession, ScreenBuilder, uid, fill
import math

# Colors
BG      = "#0D0D0D"
SURFACE = "#1A1A1A"
CARD    = "#242424"
PRIMARY = "#FF4757"
SEC     = "#FF6B81"
ACC     = "#4ECDC4"
T1      = "#FFFFFF"
T2      = "#A0A0A0"
T3      = "#606060"
BRD     = "#2A2A2A"

# Layout: y=1000, x=0,470,940,1410
Y_BASE = 1000
SCREENS = [(0, "Pulse/Dashboard"), (470, "Pulse/Workout"), (940, "Pulse/Progress"), (1410, "Pulse/Profile")]

ps = PenpotSession()

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 1: Dashboard
# ═══════════════════════════════════════════════════════════════════════
print("Building Pulse/Dashboard...")
s = ScreenBuilder(ps, "Pulse/Dashboard", 0, Y_BASE, BG)

# Status bar (white for dark theme)
s.status_bar("9:41", T1)

# Header
s.text("greeting", 24, 60, 200, "Good Morning", fs=14, fw="400", color=T2)
s.text("user_name", 24, 80, 200, "Alex", fs=28, fw="700", color=T1)

# Profile avatar circle
av_fid = s.mkframe("Avatar", 320, 60, 46, 46, bg=PRIMARY, r_=23)
s.text_in_frame("av_t", 320, 60, 46, 46, "A", fs=20, fw="700", color=T1, parent=av_fid)

# ── Stats Ring Card ──
ring_card = s.mkframe("Stats Ring Card", 24, 130, 342, 200, bg=CARD, r_=20,
                       shadow=s.shadow_card())

# Ring (approximated with circle strokes)
# Outer ring bg
s.circle("ring_bg", 24+120, 130+30, 120, BRD, parent=ring_card, stroke=BRD, stroke_w=8)
# Progress ring (primary)
s.circle("ring_progress", 24+120, 130+30, 120, BG, parent=ring_card, opacity=0.0,
         stroke=PRIMARY, stroke_w=8)
# Inner ring
s.circle("ring_inner", 24+135, 130+45, 90, BRD, parent=ring_card, stroke=BRD, stroke_w=6)
s.circle("ring_inner_prog", 24+135, 130+45, 90, BG, parent=ring_card, opacity=0.0,
         stroke=ACC, stroke_w=6)
# Center text
s.text("cal_num", 24+140, 130+68, 80, "847", fs=32, fw="700", color=T1, align="center", parent=ring_card)
s.text("cal_label", 24+140, 130+105, 80, "kcal burned", fs=11, fw="400", color=T2, align="center", parent=ring_card)

# Stats row on the right
stats = [("Steps", "12,450", PRIMARY), ("Active", "45 min", ACC), ("Heart", "72 bpm", SEC)]
for i, (label, val, col) in enumerate(stats):
    sy = 130 + 35 + i * 52
    s.rect(f"stat_dot_{i}", 24+260, sy+4, 8, 8, col, parent=ring_card, r_=4)
    s.text(f"stat_val_{i}", 24+275, sy, 80, val, fs=16, fw="600", color=T1, parent=ring_card)
    s.text(f"stat_lbl_{i}", 24+275, sy+22, 80, label, fs=11, fw="400", color=T2, parent=ring_card)

# ── Today's Workout Card ──
wo_card = s.mkframe("Today Workout", 24, 350, 342, 130, bg=CARD, r_=16, shadow=s.shadow_card())
s.text("wo_label", 24+16, 350+16, 200, "Today's Workout", fs=12, fw="500", color=T2, parent=wo_card)
s.text("wo_name", 24+16, 350+36, 250, "Upper Body Strength", fs=20, fw="700", color=T1, parent=wo_card)
s.text("wo_detail", 24+16, 350+64, 200, "45 min  •  12 exercises", fs=13, fw="400", color=T2, parent=wo_card)

# Start button
btn_fid = s.mkframe("Start Btn", 24+232, 350+80, 94, 36, bg=PRIMARY, r_=18, parent=wo_card)
s.text_centered("start_t", 24+232, 350+80, 94, 36, "Start", fs=14, fw="600", color=T1, parent=btn_fid)

# ── Quick Actions ──
s.text("qa_title", 24, 500, 200, "Quick Actions", fs=16, fw="600", color=T1)

actions = [("Run", "Outdoor", PRIMARY), ("Yoga", "30 min", ACC), ("HIIT", "20 min", SEC)]
for i, (label, sub, col) in enumerate(actions):
    ax = 24 + i * 118
    af = s.mkframe(f"QA/{label}", ax, 530, 106, 100, bg=CARD, r_=16)
    # Icon circle
    s.circle(f"qa_ico_{i}", ax+33, 530+16, 40, col, parent=af, opacity=0.15)
    s.text(f"qa_ico_t_{i}", ax+33, 530+24, 40, label[0], fs=20, fw="700", color=col, align="center", parent=af)
    s.text(f"qa_lbl_{i}", ax, 530+68, 106, label, fs=14, fw="600", color=T1, align="center", parent=af)
    s.text(f"qa_sub_{i}", ax, 530+86, 106, sub, fs=11, fw="400", color=T2, align="center", parent=af)

# ── Recent Activity ──
s.text("recent_title", 24, 650, 200, "Recent Activity", fs=16, fw="600", color=T1)

activities = [("Morning Run", "5.2 km • 28 min", "Today"), ("Chest Day", "45 min • 8 exercises", "Yesterday")]
for i, (name, detail, when) in enumerate(activities):
    ay = 680 + i * 56
    af = s.mkframe(f"Activity/{name}", 24, ay, 342, 50, bg=CARD, r_=12)
    s.circle(f"act_dot_{i}", 24+12, ay+15, 20, PRIMARY if i==0 else ACC, parent=af, opacity=0.2)
    s.text(f"act_name_{i}", 24+42, ay+10, 200, name, fs=14, fw="600", color=T1, parent=af)
    s.text(f"act_det_{i}", 24+42, ay+30, 200, detail, fs=11, fw="400", color=T2, parent=af)
    s.text(f"act_when_{i}", 24+270, ay+18, 60, when, fs=11, fw="400", color=T3, align="right", parent=af)

# Nav Bar
s.nav_bar([("house","Home"),("list","Workout"),("star","Progress"),("settings","Profile")],
          active_idx=0, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)

s.flush()
dashboard_id = s.fid
print(f"  Dashboard ID: {dashboard_id}")

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 2: Workout
# ═══════════════════════════════════════════════════════════════════════
print("Building Pulse/Workout...")
s2 = ScreenBuilder(ps, "Pulse/Workout", 470, Y_BASE, BG)
s2.status_bar("9:41", T1)

# Header
s2.icon("arrow-left", 24, 60, 24, T1)
s2.text("wo_title", 60, 62, 200, "Upper Body Strength", fs=18, fw="700", color=T1)
s2.icon("ellipsis", 350, 64, 20, T2)

# Timer section
timer_fid = s2.mkframe("Timer Section", 24, 100, 342, 140, bg=CARD, r_=20)
s2.text("timer_label", 24+16, 100+16, 100, "Elapsed Time", fs=12, fw="400", color=T2, parent=timer_fid)
s2.text("timer_val", 24+16, 100+40, 310, "12:34", fs=48, fw="700", color=T1, parent=timer_fid)
# Pause/Stop buttons
pause_fid = s2.mkframe("Pause Btn", 24+16, 100+100, 145, 30, bg=PRIMARY, r_=15, parent=timer_fid)
s2.text_centered("pause_t", 24+16, 100+100, 145, 30, "Pause", fs=13, fw="600", color=T1, parent=pause_fid)
stop_fid = s2.mkframe("Stop Btn", 24+181, 100+100, 145, 30, bg=BRD, r_=15, parent=timer_fid)
s2.text_centered("stop_t", 24+181, 100+100, 145, 30, "Stop", fs=13, fw="600", color=T1, parent=stop_fid)

# Exercise list
s2.text("exercises_title", 24, 260, 200, "Exercises", fs=16, fw="600", color=T1)
s2.text("ex_count", 290, 262, 76, "4 of 12", fs=12, fw="400", color=T2, align="right")

exercises = [
    ("Bench Press", "4 sets × 8 reps", True, "60 kg"),
    ("Incline Dumbbell", "3 sets × 10 reps", True, "22 kg"),
    ("Cable Fly", "3 sets × 12 reps", True, "15 kg"),
    ("Overhead Press", "4 sets × 8 reps", False, "40 kg"),
    ("Lateral Raise", "3 sets × 15 reps", False, "10 kg"),
    ("Tricep Pushdown", "3 sets × 12 reps", False, "25 kg"),
]

for i, (name, detail, done, weight) in enumerate(exercises):
    ey = 290 + i * 62
    ef = s2.mkframe(f"Ex/{name}", 24, ey, 342, 56, bg=CARD, r_=12)
    # Check circle
    if done:
        s2.circle(f"ex_check_{i}", 24+12, ey+16, 24, PRIMARY, parent=ef)
        s2.text(f"ex_chk_t_{i}", 24+14, ey+19, 20, "✓", fs=14, fw="700", color=T1, align="center", parent=ef)
    else:
        s2.circle(f"ex_check_{i}", 24+12, ey+16, 24, BRD, parent=ef, opacity=0.0, stroke=BRD, stroke_w=2)
    
    s2.text(f"ex_name_{i}", 24+46, ey+12, 180, name, fs=14, fw="600", 
            color=T1 if not done else T2, parent=ef)
    s2.text(f"ex_det_{i}", 24+46, ey+32, 180, detail, fs=11, fw="400", color=T2, parent=ef)
    s2.text(f"ex_wt_{i}", 24+275, ey+20, 55, weight, fs=13, fw="600", color=ACC, align="right", parent=ef)

# Sets tracker at bottom
sets_fid = s2.mkframe("Sets Tracker", 24, 665, 342, 100, bg=CARD, r_=16)
s2.text("sets_title", 24+16, 665+12, 200, "Current: Overhead Press", fs=13, fw="600", color=T1, parent=sets_fid)
s2.text("sets_sub", 24+16, 665+32, 200, "Set 1 of 4  •  8 reps  •  40 kg", fs=12, fw="400", color=T2, parent=sets_fid)
# Set circles
for i in range(4):
    col = PRIMARY if i == 0 else BRD
    s2.circle(f"set_dot_{i}", 24+16+i*40, 665+60, 30, col, parent=sets_fid)
    s2.text(f"set_num_{i}", 24+16+i*40, 665+67, 30, str(i+1), fs=14, fw="600", 
            color=T1, align="center", parent=sets_fid)

# Done button
done_btn = s2.mkframe("Done Set Btn", 24+200, 665+58, 126, 34, bg=PRIMARY, r_=17, parent=sets_fid)
s2.text_centered("done_t", 24+200, 665+58, 126, 34, "Complete Set", fs=13, fw="600", color=T1, parent=done_btn)

s2.nav_bar([("house","Home"),("list","Workout"),("star","Progress"),("settings","Profile")],
           active_idx=1, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s2.flush()
workout_id = s2.fid
print(f"  Workout ID: {workout_id}")

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 3: Progress
# ═══════════════════════════════════════════════════════════════════════
print("Building Pulse/Progress...")
s3 = ScreenBuilder(ps, "Pulse/Progress", 940, Y_BASE, BG)
s3.status_bar("9:41", T1)

s3.text("prog_title", 24, 60, 200, "Progress", fs=24, fw="700", color=T1)

# Time filter chips
chips = ["Week", "Month", "Year"]
cx = 24
for i, chip_text in enumerate(chips):
    cw = 70
    bg = PRIMARY if i == 0 else CARD
    tc = T1
    s3.chip(f"TimeChip/{chip_text}", cx, 100, cw, 32, chip_text, fs=12, fw="500",
            bg_color=bg, text_color=tc, r_=16)
    cx += cw + 10

# ── Weekly Bar Chart ──
chart_fid = s3.mkframe("Weekly Chart", 24, 150, 342, 200, bg=CARD, r_=16)
s3.text("chart_title", 24+16, 150+12, 200, "Calories Burned", fs=14, fw="600", color=T1, parent=chart_fid)
s3.text("chart_total", 24+220, 150+12, 106, "5,240 kcal", fs=13, fw="500", color=ACC, align="right", parent=chart_fid)

# Y-axis labels
y_labels = ["1000", "750", "500", "250", "0"]
for i, lbl in enumerate(y_labels):
    s3.text(f"y_{lbl}", 24+4, 150+40+i*32, 36, lbl, fs=9, fw="400", color=T3, align="right", parent=chart_fid)

# Bars
days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
values = [680, 820, 540, 920, 780, 450, 850]
bar_area_x = 24 + 48
bar_w = 30
bar_gap = (342 - 48 - 16 - len(days) * bar_w) // (len(days) - 1)
max_h = 130

for i, (day, val) in enumerate(zip(days, values)):
    bx = bar_area_x + i * (bar_w + bar_gap)
    bh = int(val / 1000 * max_h)
    by = 150 + 40 + max_h - bh
    col = PRIMARY if i == 3 else SEC  # highlight best day
    s3.rect(f"bar_{day}", bx, by, bar_w, bh, col, parent=chart_fid, r_=4, opacity=0.8 if i!=3 else 1.0)
    s3.text(f"day_{day}", bx-2, 150+175, bar_w+4, day, fs=10, fw="400", color=T2, align="center", parent=chart_fid)

# ── Streak Section ──
streak_fid = s3.mkframe("Streak", 24, 370, 342, 70, bg=CARD, r_=16)
s3.text("streak_title", 24+16, 370+12, 200, "Current Streak", fs=13, fw="500", color=T2, parent=streak_fid)
s3.text("streak_val", 24+16, 370+32, 80, "14 days", fs=20, fw="700", color=PRIMARY, parent=streak_fid)
# Streak dots
for i in range(7):
    active = i < 5  # last 5 days active
    col = PRIMARY if active else BRD
    s3.circle(f"streak_dot_{i}", 24+200+i*20, 370+36, 14, col, parent=streak_fid)

# ── Personal Records ──
s3.text("pr_title", 24, 460, 200, "Personal Records", fs=16, fw="600", color=T1)

prs = [("Bench Press", "100 kg", "Mar 5"), ("Deadlift", "160 kg", "Feb 28"), 
       ("Squat", "130 kg", "Mar 1"), ("Pull-ups", "15 reps", "Mar 10")]
for i, (name, val, date) in enumerate(prs):
    py = 490 + i * 58
    pf = s3.mkframe(f"PR/{name}", 24, py, 342, 52, bg=CARD, r_=12)
    # Trophy icon area
    s3.circle(f"pr_ico_{i}", 24+10, py+12, 28, PRIMARY, parent=pf, opacity=0.15)
    s3.text(f"pr_ico_t_{i}", 24+10, py+16, 28, "★", fs=14, fw="700", color=PRIMARY, align="center", parent=pf)
    s3.text(f"pr_name_{i}", 24+48, py+10, 150, name, fs=14, fw="600", color=T1, parent=pf)
    s3.text(f"pr_date_{i}", 24+48, py+30, 150, date, fs=11, fw="400", color=T2, parent=pf)
    s3.text(f"pr_val_{i}", 24+250, py+16, 80, val, fs=16, fw="700", color=ACC, align="right", parent=pf)

# ── Workout Summary ──
summary_fid = s3.mkframe("Summary", 24, 724, 342, 50, bg=CARD, r_=12)
summaries = [("28", "Workouts"), ("14.5h", "Total Time"), ("8,420", "Avg Cal")]
sw = 342 // 3
for i, (val, lbl) in enumerate(summaries):
    sx = 24 + i * sw
    s3.text(f"sum_val_{i}", sx, 724+8, sw, val, fs=18, fw="700", color=T1, align="center", parent=summary_fid)
    s3.text(f"sum_lbl_{i}", sx, 724+32, sw, lbl, fs=10, fw="400", color=T2, align="center", parent=summary_fid)

s3.nav_bar([("house","Home"),("list","Workout"),("star","Progress"),("settings","Profile")],
           active_idx=2, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s3.flush()
progress_id = s3.fid
print(f"  Progress ID: {progress_id}")

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 4: Profile
# ═══════════════════════════════════════════════════════════════════════
print("Building Pulse/Profile...")
s4 = ScreenBuilder(ps, "Pulse/Profile", 1410, Y_BASE, BG)
s4.status_bar("9:41", T1)

# Profile header
s4.text("prof_title", 24, 60, 100, "Profile", fs=24, fw="700", color=T1)
s4.icon("settings", 346, 64, 20, T2)

# Avatar
av_fid = s4.mkframe("Profile Avatar", 145, 110, 100, 100, bg=PRIMARY, r_=50)
s4.text_in_frame("av_letter", 145, 110, 100, 100, "A", fs=40, fw="700", color=T1, parent=av_fid)

s4.text("prof_name", 0, 224, 390, "Alex Johnson", fs=22, fw="700", color=T1, align="center")
s4.text("prof_handle", 0, 252, 390, "@alexfit", fs=14, fw="400", color=T2, align="center")

# Stats row
stats_row = s4.mkframe("Stats Row", 24, 290, 342, 80, bg=CARD, r_=16)
stat_items = [("186", "Workouts"), ("45.2h", "Total Time"), ("14", "Streak")]
sw = 342 // 3
for i, (val, lbl) in enumerate(stat_items):
    sx = 24 + i * sw
    s4.text(f"ps_val_{i}", sx, 290+16, sw, val, fs=22, fw="700", color=T1, align="center", parent=stats_row)
    s4.text(f"ps_lbl_{i}", sx, 290+46, sw, lbl, fs=11, fw="400", color=T2, align="center", parent=stats_row)
    if i < 2:
        s4.rect(f"ps_div_{i}", 24+(i+1)*sw, 290+20, 1, 40, BRD, parent=stats_row)

# Settings list
settings = [
    ("Goals & Targets", T1),
    ("Workout Preferences", T1),
    ("Notifications", T1),
    ("Connected Apps", T1),
    ("Units & Measurements", T1),
    ("Privacy", T1),
    ("Help & Support", T2),
    ("Log Out", PRIMARY),
]

for i, (label, col) in enumerate(settings):
    sy = 395 + i * 48
    sf = s4.mkframe(f"Setting/{label}", 24, sy, 342, 44, bg=CARD if i < 6 else BG, r_=12 if i==0 or i==5 or i==6 or i==7 else 0)
    s4.text(f"set_lbl_{i}", 24+16, sy+14, 280, label, fs=15, fw="500", color=col, parent=sf)
    if col == T1:
        s4.text(f"set_arrow_{i}", 24+310, sy+12, 16, ">", fs=16, fw="400", color=T3, parent=sf)
    # Divider between items (except last of each group)
    if i < 5:
        s4.rect(f"set_div_{i}", 24+16, sy+43, 310, 1, BRD, parent=sf, opacity=0.3)

s4.nav_bar([("house","Home"),("list","Workout"),("star","Progress"),("settings","Profile")],
           active_idx=3, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s4.flush()
profile_id = s4.fid
print(f"  Profile ID: {profile_id}")

# Export all screens
print("\n=== Exporting Pulse screens ===")
ids = [("Dashboard", dashboard_id), ("Workout", workout_id), 
       ("Progress", progress_id), ("Profile", profile_id)]
for name, oid in ids:
    path = ps.export_png(oid, f"pulse_{name.lower()}", scale=2)
    if path:
        print(f"  {name}: {path}")

print("\nPulse app complete!")
