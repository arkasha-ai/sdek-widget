#!/usr/bin/env python3
"""
Build CENTS finance app - 4 screens in Penpot.
Light/mint theme, 390x844px screens at y=2000.
"""
import sys
sys.path.insert(0, "/home/clawdbot/.openclaw/workspace/scripts")
from penpot_base import PenpotSession, ScreenBuilder, uid, fill

# Colors
BG      = "#F0FDF8"
SURFACE = "#FFFFFF"
CARD    = "#FFFFFF"
PRIMARY = "#00C48C"
SEC     = "#00E5A6"
ACC     = "#FF6B6B"
T1      = "#1A1A2E"
T2      = "#4A5568"
T3      = "#A0AEC0"
BRD     = "#E2F5EE"

Y_BASE = 2000

ps = PenpotSession()

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 1: Dashboard
# ═══════════════════════════════════════════════════════════════════════
print("Building Cents/Dashboard...")
s = ScreenBuilder(ps, "Cents/Dashboard", 0, Y_BASE, BG)
s.status_bar("9:41", T1)

# Header
s.text("greeting", 24, 60, 250, "Good morning,", fs=14, fw="400", color=T2)
s.text("user_name", 24, 80, 250, "Alex", fs=26, fw="700", color=T1)
# Notification bell
bell_f = s.mkframe("Bell", 340, 65, 32, 32, bg=SURFACE, r_=16, stroke=BRD, stroke_w=1)

# ── Balance Card (gradient feel with colored bg) ──
bal_card = s.mkframe("Balance Card", 24, 120, 342, 160, bg=PRIMARY, r_=20,
                      shadow=s.shadow_card_heavy())
s.text("bal_label", 24+20, 120+20, 200, "Total Balance", fs=13, fw="500", color="#FFFFFF", 
       parent=bal_card, opacity=0.8)
s.text("bal_amount", 24+20, 120+45, 280, "$24,562.80", fs=36, fw="700", color="#FFFFFF", parent=bal_card)

# Income / Expense row
s.rect("inc_exp_bg", 24+16, 120+100, 310, 48, "#FFFFFF", parent=bal_card, r_=12, opacity=0.15)
# Income
s.circle("inc_ico", 24+28, 120+110, 28, "#FFFFFF", parent=bal_card, opacity=0.25)
s.text("inc_arrow", 24+34, 120+114, 16, "↑", fs=14, fw="700", color="#FFFFFF", parent=bal_card)
s.text("inc_lbl", 24+62, 120+108, 80, "Income", fs=11, fw="400", color="#FFFFFF", parent=bal_card, opacity=0.8)
s.text("inc_val", 24+62, 120+124, 80, "$8,450", fs=15, fw="600", color="#FFFFFF", parent=bal_card)
# Expense
s.circle("exp_ico", 24+180, 120+110, 28, "#FFFFFF", parent=bal_card, opacity=0.25)
s.text("exp_arrow", 24+186, 120+114, 16, "↓", fs=14, fw="700", color="#FFFFFF", parent=bal_card)
s.text("exp_lbl", 24+214, 120+108, 80, "Expense", fs=11, fw="400", color="#FFFFFF", parent=bal_card, opacity=0.8)
s.text("exp_val", 24+214, 120+124, 80, "$3,280", fs=15, fw="600", color="#FFFFFF", parent=bal_card)

# ── Spending Ring ──
spend_card = s.mkframe("Spending Card", 24, 300, 342, 160, bg=CARD, r_=16, 
                        shadow=s.shadow_card(), stroke=BRD, stroke_w=1)
s.text("spend_title", 24+16, 300+12, 200, "Monthly Spending", fs=14, fw="600", color=T1, parent=spend_card)

# Ring
s.circle("spend_ring_bg", 24+16, 300+40, 100, BRD, parent=spend_card, stroke=BRD, stroke_w=8)
s.circle("spend_ring_1", 24+16, 300+40, 100, BG, parent=spend_card, opacity=0.0, stroke=PRIMARY, stroke_w=8)
s.circle("spend_ring_2", 24+24, 300+48, 84, BG, parent=spend_card, opacity=0.0, stroke=ACC, stroke_w=6)
s.text("spend_center", 24+30, 300+72, 72, "68%", fs=22, fw="700", color=T1, align="center", parent=spend_card)
s.text("spend_sub", 24+30, 300+98, 72, "of budget", fs=10, fw="400", color=T2, align="center", parent=spend_card)

# Category breakdown on right
cats = [("Food", "$820", PRIMARY, 0.35), ("Transport", "$450", "#4F46E5", 0.20), 
        ("Shopping", "$680", ACC, 0.28), ("Bills", "$420", "#F59E0B", 0.17)]
for i, (cat, amt, col, pct) in enumerate(cats):
    cy = 300 + 42 + i * 28
    s.circle(f"cat_dot_{i}", 24+140, cy+2, 8, col, parent=spend_card)
    s.text(f"cat_name_{i}", 24+155, cy, 100, cat, fs=12, fw="400", color=T2, parent=spend_card)
    s.text(f"cat_amt_{i}", 24+270, cy, 56, amt, fs=12, fw="600", color=T1, align="right", parent=spend_card)

# ── Recent Transactions ──
s.text("txn_title", 24, 480, 200, "Recent Transactions", fs=16, fw="600", color=T1)
s.text("txn_see", 280, 482, 86, "See All", fs=13, fw="500", color=PRIMARY, align="right")

txns = [
    ("Whole Foods", "Groceries", "-$86.40", ACC, "Today"),
    ("Spotify", "Subscription", "-$9.99", "#4F46E5", "Today"),
    ("Uber", "Transport", "-$24.50", "#F59E0B", "Yesterday"),
    ("Salary", "Income", "+$4,225", PRIMARY, "Mar 1"),
]
for i, (name, cat, amt, col, date) in enumerate(txns):
    ty = 510 + i * 62
    tf = s.mkframe(f"Txn/{name}", 24, ty, 342, 56, bg=CARD, r_=12, stroke=BRD, stroke_w=1)
    # Category icon circle
    s.circle(f"txn_ico_{i}", 24+12, ty+14, 28, col, parent=tf, opacity=0.12)
    s.text(f"txn_ico_t_{i}", 24+16, ty+18, 20, name[0], fs=14, fw="700", color=col, align="center", parent=tf)
    s.text(f"txn_name_{i}", 24+50, ty+12, 160, name, fs=14, fw="600", color=T1, parent=tf)
    s.text(f"txn_cat_{i}", 24+50, ty+32, 160, cat, fs=11, fw="400", color=T2, parent=tf)
    amt_col = ACC if amt.startswith("-") else PRIMARY
    s.text(f"txn_amt_{i}", 24+240, ty+12, 90, amt, fs=15, fw="600", color=amt_col, align="right", parent=tf)
    s.text(f"txn_date_{i}", 24+240, ty+32, 90, date, fs=11, fw="400", color=T3, align="right", parent=tf)

# Nav Bar
s.nav_bar([("house","Home"),("list","Txns"),("plus","Add"),("star","Budget")],
          active_idx=0, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s.flush()
dash_id = s.fid

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 2: Transactions
# ═══════════════════════════════════════════════════════════════════════
print("Building Cents/Transactions...")
s2 = ScreenBuilder(ps, "Cents/Transactions", 470, Y_BASE, BG)
s2.status_bar("9:41", T1)

s2.text("txn_title", 24, 60, 200, "Transactions", fs=24, fw="700", color=T1)

# Search bar
search_f = s2.mkframe("Search Bar", 24, 100, 342, 44, bg=SURFACE, r_=12, stroke=BRD, stroke_w=1)
s2.icon("search", 24+12, 100+10, 24, T3, parent=search_f)
s2.text("search_hint", 24+44, 100+14, 200, "Search transactions...", fs=14, fw="400", 
        color=T3, parent=search_f)

# Filter chips
filters = [("All", True), ("Income", False), ("Expense", False), ("Recurring", False)]
fx = 24
for i, (label, active) in enumerate(filters):
    fw_c = max(60, len(label)*9 + 24)
    bg_c = PRIMARY if active else SURFACE
    tc = "#FFFFFF" if active else T2
    s2.chip(f"Filter/{label}", fx, 158, fw_c, 32, label, fs=12, fw="500",
            bg_color=bg_c, text_color=tc, r_=16)
    fx += fw_c + 8

# Date header
s2.text("date_today", 24, 205, 200, "Today", fs=13, fw="600", color=T2)

# Transaction list
txn_list = [
    ("Whole Foods", "Groceries", "-$86.40", ACC, "10:30 AM"),
    ("Spotify", "Subscription", "-$9.99", "#4F46E5", "9:00 AM"),
    ("Coffee Bean", "Food & Drink", "-$5.50", "#F59E0B", "8:15 AM"),
]
for i, (name, cat, amt, col, time_s) in enumerate(txn_list):
    ty = 230 + i * 62
    tf = s2.mkframe(f"Txn/{name}", 24, ty, 342, 56, bg=CARD, r_=12, stroke=BRD, stroke_w=1)
    s2.circle(f"txn_ico_{i}", 24+12, ty+14, 28, col, parent=tf, opacity=0.12)
    s2.text(f"txn_ico_t_{i}", 24+16, ty+18, 20, name[0], fs=14, fw="700", color=col, align="center", parent=tf)
    s2.text(f"txn_name_{i}", 24+50, ty+12, 160, name, fs=14, fw="600", color=T1, parent=tf)
    s2.text(f"txn_cat_{i}", 24+50, ty+32, 160, cat, fs=11, fw="400", color=T2, parent=tf)
    s2.text(f"txn_amt_{i}", 24+240, ty+12, 90, amt, fs=15, fw="600", color=ACC, align="right", parent=tf)
    s2.text(f"txn_time_{i}", 24+240, ty+32, 90, time_s, fs=11, fw="400", color=T3, align="right", parent=tf)

# Yesterday section
s2.text("date_yest", 24, 425, 200, "Yesterday", fs=13, fw="600", color=T2)

txn_list2 = [
    ("Uber", "Transport", "-$24.50", "#F59E0B", "6:30 PM"),
    ("Amazon", "Shopping", "-$156.00", "#EF4444", "2:15 PM"),
    ("Salary", "Income", "+$4,225.00", PRIMARY, "12:00 PM"),
    ("Netflix", "Subscription", "-$15.99", "#7C3AED", "Auto"),
    ("Gas Station", "Transport", "-$45.00", "#F59E0B", "9:00 AM"),
]
for i, (name, cat, amt, col, time_s) in enumerate(txn_list2):
    ty = 450 + i * 62
    tf = s2.mkframe(f"Txn2/{name}", 24, ty, 342, 56, bg=CARD, r_=12, stroke=BRD, stroke_w=1)
    s2.circle(f"txn2_ico_{i}", 24+12, ty+14, 28, col, parent=tf, opacity=0.12)
    s2.text(f"txn2_ico_t_{i}", 24+16, ty+18, 20, name[0], fs=14, fw="700", color=col, align="center", parent=tf)
    s2.text(f"txn2_name_{i}", 24+50, ty+12, 160, name, fs=14, fw="600", color=T1, parent=tf)
    s2.text(f"txn2_cat_{i}", 24+50, ty+32, 160, cat, fs=11, fw="400", color=T2, parent=tf)
    amt_col = PRIMARY if amt.startswith("+") else ACC
    s2.text(f"txn2_amt_{i}", 24+240, ty+12, 90, amt, fs=15, fw="600", color=amt_col, align="right", parent=tf)
    s2.text(f"txn2_time_{i}", 24+240, ty+32, 90, time_s, fs=11, fw="400", color=T3, align="right", parent=tf)

s2.nav_bar([("house","Home"),("list","Txns"),("plus","Add"),("star","Budget")],
           active_idx=1, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s2.flush()
txn_id = s2.fid

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 3: Add Transaction
# ═══════════════════════════════════════════════════════════════════════
print("Building Cents/Add...")
s3 = ScreenBuilder(ps, "Cents/Add", 940, Y_BASE, BG)
s3.status_bar("9:41", T1)

s3.text("add_title", 24, 60, 200, "Add Expense", fs=24, fw="700", color=T1)

# Amount display
amt_card = s3.mkframe("Amount Display", 24, 110, 342, 120, bg=CARD, r_=20, 
                       stroke=BRD, stroke_w=1, shadow=s3.shadow_card())
s3.text("currency", 24+20, 110+30, 30, "$", fs=32, fw="300", color=T3, parent=amt_card)
s3.text("amount_val", 24+50, 110+20, 250, "45.50", fs=48, fw="700", color=T1, parent=amt_card)
s3.rect("amt_cursor", 24+220, 110+25, 2, 40, PRIMARY, parent=amt_card)
s3.text("amt_hint", 24+20, 110+82, 200, "Tap to enter amount", fs=12, fw="400", color=T3, parent=amt_card)

# Category selection
s3.text("cat_title", 24, 248, 200, "Category", fs=14, fw="600", color=T1)

categories = [
    ("Food", PRIMARY), ("Transport", "#F59E0B"), ("Shopping", ACC),
    ("Bills", "#4F46E5"), ("Health", "#10B981"), ("Entertainment", "#7C3AED"),
    ("Education", "#0EA5E9"), ("Other", T3),
]
for i, (cat, col) in enumerate(categories):
    row = i // 4
    col_idx = i % 4
    cx = 24 + col_idx * 85
    cy = 278 + row * 80
    cf = s3.mkframe(f"Cat/{cat}", cx, cy, 78, 72, bg=CARD, r_=12, stroke=BRD, stroke_w=1)
    s3.circle(f"cat_ico_{i}", cx+23, cy+12, 32, col, parent=cf, opacity=0.12)
    s3.text(f"cat_ico_t_{i}", cx+23, cy+19, 32, cat[0], fs=14, fw="700", color=col, align="center", parent=cf)
    s3.text(f"cat_lbl_{i}", cx, cy+52, 78, cat, fs=10, fw="500", color=T2, align="center", parent=cf)

# Note field
s3.text("note_label", 24, 448, 200, "Note", fs=14, fw="600", color=T1)
note_f = s3.mkframe("Note Field", 24, 474, 342, 44, bg=CARD, r_=12, stroke=BRD, stroke_w=1)
s3.text("note_hint", 24+16, 474+14, 300, "Add a note...", fs=14, fw="400", color=T3, parent=note_f)

# Date selector
s3.text("date_label", 24, 534, 200, "Date", fs=14, fw="600", color=T1)
date_f = s3.mkframe("Date Field", 24, 560, 342, 44, bg=CARD, r_=12, stroke=BRD, stroke_w=1)
s3.text("date_val", 24+16, 560+14, 260, "Today, Mar 13", fs=14, fw="500", color=T1, parent=date_f)
s3.icon("calendar", 24+302, 560+10, 24, T2, parent=date_f)

# Numpad
keys = [["1","2","3"],["4","5","6"],["7","8","9"],[".","0","←"]]
for row_i, row in enumerate(keys):
    for col_i, key in enumerate(row):
        kx = 24 + col_i * 118
        ky = 620 + row_i * 46
        kf = s3.mkframe(f"Key/{key}", kx, ky, 110, 42, bg=CARD, r_=12)
        s3.text_centered(f"key_t_{key}", kx, ky, 110, 42, key, fs=22, fw="500", color=T1, parent=kf)

# Add button
add_btn = s3.mkframe("Add Btn", 24, 808, 342, 50, bg=PRIMARY, r_=25)
s3.text_centered("add_btn_t", 24, 808, 342, 50, "Add Expense", fs=16, fw="600", color="#FFFFFF", parent=add_btn)

# No nav bar on add screen (it's a modal-like view)

s3.flush()
add_id = s3.fid

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 4: Budget
# ═══════════════════════════════════════════════════════════════════════
print("Building Cents/Budget...")
s4 = ScreenBuilder(ps, "Cents/Budget", 1410, Y_BASE, BG)
s4.status_bar("9:41", T1)

s4.text("budget_title", 24, 60, 200, "Budget", fs=24, fw="700", color=T1)

# Month selector
month_f = s4.mkframe("Month Selector", 120, 62, 150, 28, bg=SURFACE, r_=14, stroke=BRD, stroke_w=1)
s4.text_centered("month_t", 120, 62, 150, 28, "March 2026", fs=13, fw="500", color=T1, parent=month_f)

# Overview card
ov_card = s4.mkframe("Overview Card", 24, 105, 342, 100, bg=CARD, r_=16, 
                      shadow=s4.shadow_card(), stroke=BRD, stroke_w=1)
s4.text("ov_spent", 24+20, 105+16, 100, "Spent", fs=12, fw="400", color=T2, parent=ov_card)
s4.text("ov_spent_val", 24+20, 105+34, 150, "$2,370", fs=24, fw="700", color=T1, parent=ov_card)
s4.text("ov_budget", 24+200, 105+16, 126, "Budget", fs=12, fw="400", color=T2, align="right", parent=ov_card)
s4.text("ov_budget_val", 24+200, 105+34, 126, "$4,500", fs=24, fw="700", color=PRIMARY, align="right", parent=ov_card)
# Progress bar
s4.rect("ov_bar_bg", 24+20, 105+72, 302, 8, BRD, parent=ov_card, r_=4)
bar_w = int(302 * 2370/4500)
s4.rect("ov_bar_fill", 24+20, 105+72, bar_w, 8, PRIMARY, parent=ov_card, r_=4)
s4.text("ov_pct", 24+20+bar_w+6, 105+66, 40, "53%", fs=11, fw="600", color=PRIMARY, parent=ov_card)

# Budget categories
s4.text("cat_title", 24, 225, 200, "Categories", fs=16, fw="600", color=T1)

budgets = [
    ("Food & Dining", 820, 1000, PRIMARY),
    ("Transport", 450, 500, "#F59E0B"),
    ("Shopping", 680, 800, ACC),
    ("Bills & Utilities", 420, 500, "#4F46E5"),
    ("Health & Fitness", 150, 300, "#10B981"),
    ("Entertainment", 220, 400, "#7C3AED"),
]
for i, (cat, spent, budget, col) in enumerate(budgets):
    by = 255 + i * 76
    bf = s4.mkframe(f"Budget/{cat}", 24, by, 342, 70, bg=CARD, r_=12, stroke=BRD, stroke_w=1)
    s4.text(f"b_name_{i}", 24+16, by+10, 200, cat, fs=14, fw="600", color=T1, parent=bf)
    s4.text(f"b_vals_{i}", 24+200, by+10, 126, f"${spent} / ${budget}", fs=13, fw="500", 
            color=T2, align="right", parent=bf)
    # Progress bar
    pct = spent / budget
    s4.rect(f"b_bar_bg_{i}", 24+16, by+38, 310, 6, BRD, parent=bf, r_=3)
    bw = int(310 * min(pct, 1.0))
    bar_col = col if pct < 0.9 else ACC
    s4.rect(f"b_bar_{i}", 24+16, by+38, bw, 6, bar_col, parent=bf, r_=3)
    # Percentage
    pct_str = f"{int(pct*100)}%"
    s4.text(f"b_pct_{i}", 24+16, by+50, 60, pct_str, fs=11, fw="500", color=col, parent=bf)
    # Status
    remaining = budget - spent
    status = f"${remaining} left" if remaining > 0 else "Over budget!"
    status_col = T2 if remaining > 0 else ACC
    s4.text(f"b_status_{i}", 24+230, by+50, 96, status, fs=11, fw="500", color=status_col, 
            align="right", parent=bf)

# Savings goal
s4.text("savings_title", 24, 720, 200, "Savings Goal", fs=16, fw="600", color=T1)
sav_card = s4.mkframe("Savings Goal", 24, 748, 342, 60, bg=CARD, r_=12, stroke=BRD, stroke_w=1)
s4.text("sav_name", 24+16, 748+10, 200, "Emergency Fund", fs=14, fw="600", color=T1, parent=sav_card)
s4.text("sav_val", 24+200, 748+10, 126, "$8,200 / $10,000", fs=12, fw="500", color=T2, align="right", parent=sav_card)
s4.rect("sav_bar_bg", 24+16, 748+36, 310, 6, BRD, parent=sav_card, r_=3)
s4.rect("sav_bar", 24+16, 748+36, int(310*0.82), 6, PRIMARY, parent=sav_card, r_=3)

s4.nav_bar([("house","Home"),("list","Txns"),("plus","Add"),("star","Budget")],
           active_idx=3, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s4.flush()
budget_id = s4.fid

print("\n=== Exporting Cents screens ===")
# Fix export to use dict-based response parsing
import json
EXPORT_URL = "https://penpot.jakeberrimor.com/api/export"
H = {"Content-Type": "application/transit+json"}

ids = [("dashboard", dash_id), ("transactions", txn_id), ("add", add_id), ("budget", budget_id)]
for name, oid in ids:
    payload = json.dumps(["^ ",
        "~:cmd", "~:export-shapes",
        "~:profile-id", f"~u{ps.profile_id}",
        "~:wait", True,
        "~:exports", [["^ ",
            "~:page-id", f"~u{ps.s.cookies.get('page_id', '4b85babb-b10c-8109-8007-b44132d29930')}",
            "~:file-id", f"~u4b85babb-b10c-8109-8007-b44132d2992f",
            "~:object-id", f"~u{oid}",
            "~:type", "~:png", "~:scale", 2, "~:suffix", "", "~:name", f"cents_{name}"
        ]]
    ])
    r = ps.s.post(EXPORT_URL, headers=H, data=payload, timeout=60)
    res = r.json()
    uri = res.get("~:uri", {}).get("~#uri", "")
    if uri:
        img = ps.s.get(uri)
        path = f"/home/clawdbot/.openclaw/workspace/drafts/cents_{name}.png"
        with open(path, "wb") as f:
            f.write(img.content)
        print(f"  {name}: {len(img.content)//1024}KB -> {path}")
    else:
        print(f"  {name}: FAILED")

print("\nCents app complete!")
