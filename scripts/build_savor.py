#!/usr/bin/env python3
"""
Build SAVOR recipe app - 4 screens in Penpot.
Warm theme, 390x844px screens at y=3000.
"""
import sys, json
sys.path.insert(0, "/home/clawdbot/.openclaw/workspace/scripts")
from penpot_base import PenpotSession, ScreenBuilder, uid, fill

# Colors
BG      = "#FFFBF5"
SURFACE = "#FFFFFF"
CARD    = "#FFFFFF"
PRIMARY = "#FF6B35"
SEC     = "#FF8C5A"
ACC     = "#2ECC71"
T1      = "#2D2D2D"
T2      = "#6B6B6B"
T3      = "#A8A8A8"
BRD     = "#F0E6DC"

Y_BASE = 3000
EXPORT_URL = "https://penpot.jakeberrimor.com/api/export"
H = {"Content-Type": "application/transit+json"}

ps = PenpotSession()

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 1: Discovery
# ═══════════════════════════════════════════════════════════════════════
print("Building Savor/Discovery...")
s = ScreenBuilder(ps, "Savor/Discovery", 0, Y_BASE, BG)
s.status_bar("9:41", T1)

# Header
s.text("app_title", 24, 58, 200, "Savor", fs=28, fw="700", color=PRIMARY)
s.text("subtitle", 24, 90, 250, "What are you cooking today?", fs=14, fw="400", color=T2)

# Search bar
sf = s.mkframe("Search Bar", 24, 120, 342, 44, bg=SURFACE, r_=22, stroke=BRD, stroke_w=1)
s.icon("search", 24+14, 120+10, 24, T3, parent=sf)
s.text("search_hint", 24+46, 120+14, 260, "Search recipes, ingredients...", fs=14, fw="400", color=T3, parent=sf)

# ── Featured Recipe Card ──
feat_card = s.mkframe("Featured Card", 24, 180, 342, 180, bg=PRIMARY, r_=20,
                       shadow=s.shadow_card_heavy())
# Gradient overlay feel
s.rect("feat_overlay", 24, 180+90, 342, 90, "#000000", parent=feat_card, r_=0, opacity=0.3)
s.text("feat_badge", 24+16, 180+16, 80, "Featured", fs=11, fw="600", color="#FFFFFF", parent=feat_card)
s.text("feat_title", 24+16, 180+120, 250, "Thai Green Curry", fs=22, fw="700", color="#FFFFFF", parent=feat_card)
s.text("feat_detail", 24+16, 180+148, 250, "30 min  •  Easy  •  4 servings", fs=12, fw="400", 
       color="#FFFFFF", parent=feat_card, opacity=0.8)
# Rating
s.text("feat_rating", 24+280, 180+16, 46, "4.8 ★", fs=12, fw="600", color="#FFFFFF", 
       align="right", parent=feat_card)

# ── Cuisine Chips ──
s.text("cuisine_title", 24, 378, 200, "Cuisines", fs=16, fw="600", color=T1)

cuisines = [("All", True), ("Italian", False), ("Asian", False), ("Mexican", False), ("Indian", False)]
cx = 24
for i, (name, active) in enumerate(cuisines):
    cw = max(60, len(name)*9 + 24)
    bg_c = PRIMARY if active else SURFACE
    tc = "#FFFFFF" if active else T2
    s.chip(f"Cuisine/{name}", cx, 406, cw, 32, name, fs=12, fw="500",
           bg_color=bg_c, text_color=tc, r_=16)
    cx += cw + 8

# ── Recipe Grid (2 columns) ──
recipes = [
    ("Pasta Carbonara", "20 min", "4.5"),
    ("Chicken Tikka", "35 min", "4.7"),
    ("Caesar Salad", "15 min", "4.2"),
    ("Beef Tacos", "25 min", "4.6"),
]

for i, (name, time_s, rating) in enumerate(recipes):
    col = i % 2
    row = i // 2
    rx = 24 + col * 174
    ry = 454 + row * 170
    
    rf = s.mkframe(f"Recipe/{name}", rx, ry, 164, 160, bg=CARD, r_=16, 
                    stroke=BRD, stroke_w=1, shadow=s.shadow_card())
    
    # Image placeholder
    img_colors = [PRIMARY, "#4F46E5", ACC, SEC]
    s.rect(f"r_img_{i}", rx, ry, 164, 90, img_colors[i], parent=rf, r_=0, opacity=0.2)
    s.text(f"r_img_t_{i}", rx, ry+30, 164, "📷", fs=28, fw="400", color=img_colors[i], 
           align="center", parent=rf, opacity=0.4)
    
    # Recipe info
    s.text(f"r_name_{i}", rx+12, ry+98, 140, name, fs=14, fw="600", color=T1, parent=rf)
    s.text(f"r_time_{i}", rx+12, ry+118, 80, time_s, fs=11, fw="400", color=T2, parent=rf)
    s.text(f"r_rating_{i}", rx+110, ry+118, 42, f"★ {rating}", fs=11, fw="600", color=PRIMARY, 
           align="right", parent=rf)
    
    # Bookmark icon area
    s.circle(f"r_bm_{i}", rx+126, ry+136, 24, BRD, parent=rf, opacity=0.5)

s.nav_bar([("house","Home"),("search","Search"),("bookmark","Saved"),("settings","Profile")],
          active_idx=0, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s.flush()
disc_id = s.fid

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 2: Recipe Detail
# ═══════════════════════════════════════════════════════════════════════
print("Building Savor/Recipe Detail...")
s2 = ScreenBuilder(ps, "Savor/Recipe Detail", 470, Y_BASE, BG)
s2.status_bar("9:41", T1)

# Back button
s2.icon("arrow-left", 24, 60, 24, T1)
s2.icon("bookmark", 346, 60, 24, T2)

# Hero image placeholder
s2.rect("hero_img", 0, 40, 390, 200, PRIMARY, opacity=0.15)
s2.text("hero_placeholder", 0, 110, 390, "Recipe Photo", fs=24, fw="600", color=PRIMARY, 
        align="center", opacity=0.3)

# Recipe info overlay
info_card = s2.mkframe("Recipe Info", 24, 220, 342, 120, bg=CARD, r_=20, 
                         shadow=s2.shadow_card_heavy())
s2.text("recipe_name", 24+16, 220+16, 280, "Thai Green Curry", fs=22, fw="700", color=T1, parent=info_card)
s2.text("recipe_desc", 24+16, 220+44, 310, "A fragrant and creamy curry with fresh vegetables", 
        fs=13, fw="400", color=T2, parent=info_card)

# Stats row
stats = [("30 min", "Time"), ("Easy", "Level"), ("4", "Servings"), ("320", "Calories")]
sw = 310 // 4
for i, (val, lbl) in enumerate(stats):
    sx = 24+16 + i * sw
    s2.text(f"stat_val_{i}", sx, 220+78, sw, val, fs=15, fw="700", color=PRIMARY, align="center", parent=info_card)
    s2.text(f"stat_lbl_{i}", sx, 220+96, sw, lbl, fs=10, fw="400", color=T2, align="center", parent=info_card)

# ── Ingredients ──
s2.text("ing_title", 24, 358, 200, "Ingredients", fs=18, fw="700", color=T1)
s2.text("ing_count", 290, 360, 76, "8 items", fs=12, fw="400", color=T2, align="right")

ingredients = [
    "400ml Coconut Milk",
    "2 tbsp Green Curry Paste",
    "300g Chicken Breast",
    "1 Red Bell Pepper",
    "150g Baby Corn",
    "2 tbsp Fish Sauce",
    "1 tbsp Palm Sugar",
    "Fresh Thai Basil",
]
for i, ing in enumerate(ingredients):
    iy = 388 + i * 34
    s2.circle(f"ing_dot_{i}", 24, iy+8, 8, PRIMARY if i<3 else BRD)
    s2.text(f"ing_{i}", 40, iy+4, 300, ing, fs=14, fw="400", color=T1)

# ── Steps ──
s2.text("steps_title", 24, 668, 200, "Instructions", fs=18, fw="700", color=T1)

steps = [
    "Heat oil in a large pan over medium heat",
    "Add curry paste and cook for 2 minutes",
    "Pour in coconut milk and bring to simmer",
]
for i, step in enumerate(steps):
    sy = 698 + i * 42
    # Step number
    sn_fid = s2.mkframe(f"Step/{i+1}", 24, sy, 28, 28, bg=PRIMARY, r_=14)
    s2.text_centered(f"step_num_{i}", 24, sy, 28, 28, str(i+1), fs=13, fw="700", color="#FFFFFF", parent=sn_fid)
    s2.text(f"step_text_{i}", 60, sy+4, 296, step, fs=13, fw="400", color=T1)

# Cook button
cook_btn = s2.mkframe("Cook Btn", 24, 808, 342, 50, bg=PRIMARY, r_=25)
s2.text_centered("cook_t", 24, 808, 342, 50, "Start Cooking", fs=16, fw="600", color="#FFFFFF", parent=cook_btn)

s2.flush()
detail_id = s2.fid

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 3: Search
# ═══════════════════════════════════════════════════════════════════════
print("Building Savor/Search...")
s3 = ScreenBuilder(ps, "Savor/Search", 940, Y_BASE, BG)
s3.status_bar("9:41", T1)

s3.text("search_title", 24, 60, 200, "Search", fs=24, fw="700", color=T1)

# Search bar (active state)
sf = s3.mkframe("Search Bar", 24, 100, 342, 44, bg=SURFACE, r_=22, stroke=PRIMARY, stroke_w=2)
s3.icon("search", 24+14, 100+10, 24, PRIMARY, parent=sf)
s3.text("search_val", 24+46, 100+14, 230, "chicken", fs=14, fw="500", color=T1, parent=sf)
s3.text("clear_btn", 24+310, 100+12, 20, "✕", fs=16, fw="400", color=T3, parent=sf)

# Filter chips
filters = [("All", True), ("Under 30m", False), ("Vegetarian", False), ("Easy", False)]
fx = 24
for i, (label, active) in enumerate(filters):
    fw_c = max(60, len(label)*8 + 28)
    bg_c = PRIMARY if active else SURFACE
    tc = "#FFFFFF" if active else T2
    s3.chip(f"Filter/{label}", fx, 158, fw_c, 32, label, fs=12, fw="500",
            bg_color=bg_c, text_color=tc, r_=16)
    fx += fw_c + 8

# Results count
s3.text("results_count", 24, 206, 200, "12 results found", fs=13, fw="400", color=T2)

# Results list
results = [
    ("Chicken Tikka Masala", "Indian • 35 min • Medium", "4.7"),
    ("Lemon Herb Chicken", "Mediterranean • 25 min • Easy", "4.5"),
    ("Chicken Stir Fry", "Asian • 20 min • Easy", "4.3"),
    ("Chicken Parmesan", "Italian • 40 min • Medium", "4.6"),
    ("Chicken Caesar Wrap", "American • 15 min • Easy", "4.1"),
    ("Teriyaki Chicken Bowl", "Japanese • 30 min • Easy", "4.8"),
]

for i, (name, detail, rating) in enumerate(results):
    ry = 232 + i * 80
    rf = s3.mkframe(f"Result/{name}", 24, ry, 342, 74, bg=CARD, r_=12, 
                     stroke=BRD, stroke_w=1)
    # Image placeholder
    img_cols = [PRIMARY, SEC, ACC, "#4F46E5", "#F59E0B", "#7C3AED"]
    s3.rect(f"res_img_{i}", 24+10, ry+10, 54, 54, img_cols[i%len(img_cols)], 
            parent=rf, r_=8, opacity=0.2)
    s3.text(f"res_img_t_{i}", 24+10, ry+22, 54, "🍗", fs=22, fw="400", 
            color=img_cols[i%len(img_cols)], align="center", parent=rf, opacity=0.5)
    
    s3.text(f"res_name_{i}", 24+74, ry+14, 200, name, fs=14, fw="600", color=T1, parent=rf)
    s3.text(f"res_det_{i}", 24+74, ry+36, 200, detail, fs=11, fw="400", color=T2, parent=rf)
    s3.text(f"res_rat_{i}", 24+74, ry+54, 60, f"★ {rating}", fs=11, fw="600", color=PRIMARY, parent=rf)
    # Bookmark
    s3.icon("bookmark", 24+308, ry+26, 20, T3, parent=rf)

s3.nav_bar([("house","Home"),("search","Search"),("bookmark","Saved"),("settings","Profile")],
           active_idx=1, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s3.flush()
search_id = s3.fid

# ═══════════════════════════════════════════════════════════════════════
# SCREEN 4: My Cookbook
# ═══════════════════════════════════════════════════════════════════════
print("Building Savor/My Cookbook...")
s4 = ScreenBuilder(ps, "Savor/My Cookbook", 1410, Y_BASE, BG)
s4.status_bar("9:41", T1)

s4.text("cook_title", 24, 60, 200, "My Cookbook", fs=24, fw="700", color=T1)
s4.text("cook_count", 24, 90, 200, "18 saved recipes", fs=14, fw="400", color=T2)

# Collection chips
collections = [("All", True), ("Favorites", False), ("Quick Meals", False), ("Desserts", False)]
cx = 24
for i, (name, active) in enumerate(collections):
    cw = max(60, len(name)*8 + 28)
    bg_c = PRIMARY if active else SURFACE
    tc = "#FFFFFF" if active else T2
    s4.chip(f"Col/{name}", cx, 120, cw, 32, name, fs=12, fw="500",
            bg_color=bg_c, text_color=tc, r_=16)
    cx += cw + 8

# Saved recipes grid (2 columns)
saved = [
    ("Thai Green Curry", "30 min", "4.8", PRIMARY),
    ("Pasta Carbonara", "20 min", "4.5", SEC),
    ("Chicken Tikka", "35 min", "4.7", ACC),
    ("Caesar Salad", "15 min", "4.2", "#4F46E5"),
    ("Beef Tacos", "25 min", "4.6", "#F59E0B"),
    ("Mushroom Risotto", "40 min", "4.4", "#7C3AED"),
    ("Lemon Chicken", "25 min", "4.5", "#0EA5E9"),
    ("Berry Smoothie", "5 min", "4.3", ACC),
]

for i, (name, time_s, rating, col) in enumerate(saved):
    c = i % 2
    r = i // 2
    rx = 24 + c * 174
    ry = 168 + r * 160
    
    rf = s4.mkframe(f"Saved/{name}", rx, ry, 164, 150, bg=CARD, r_=16, 
                     stroke=BRD, stroke_w=1, shadow=s4.shadow_card())
    
    # Image placeholder
    s4.rect(f"s_img_{i}", rx, ry, 164, 82, col, parent=rf, r_=0, opacity=0.15)
    s4.text(f"s_img_t_{i}", rx, ry+24, 164, "🍽", fs=28, fw="400", color=col, 
            align="center", parent=rf, opacity=0.4)
    
    # Bookmark filled
    s4.circle(f"s_bm_{i}", rx+128, ry+8, 28, SURFACE, parent=rf, opacity=0.8)
    s4.text(f"s_bm_t_{i}", rx+128, ry+12, 28, "♥", fs=14, fw="700", color=PRIMARY, align="center", parent=rf)
    
    s4.text(f"s_name_{i}", rx+10, ry+88, 144, name, fs=13, fw="600", color=T1, parent=rf)
    s4.text(f"s_time_{i}", rx+10, ry+108, 80, time_s, fs=11, fw="400", color=T2, parent=rf)
    s4.text(f"s_rat_{i}", rx+108, ry+108, 46, f"★ {rating}", fs=11, fw="600", color=PRIMARY, 
            align="right", parent=rf)

s4.nav_bar([("house","Home"),("search","Search"),("bookmark","Saved"),("settings","Profile")],
           active_idx=2, bg_color=SURFACE, active_color=PRIMARY, inactive_color=T3)
s4.flush()
cookbook_id = s4.fid

# Export all screens
print("\n=== Exporting Savor screens ===")
ids = [("discovery", disc_id), ("detail", detail_id), ("search", search_id), ("cookbook", cookbook_id)]
for name, oid in ids:
    payload = json.dumps(["^ ",
        "~:cmd", "~:export-shapes",
        "~:profile-id", f"~u{ps.profile_id}",
        "~:wait", True,
        "~:exports", [["^ ",
            "~:page-id", "~u4b85babb-b10c-8109-8007-b44132d29930",
            "~:file-id", "~u4b85babb-b10c-8109-8007-b44132d2992f",
            "~:object-id", f"~u{oid}",
            "~:type", "~:png", "~:scale", 2, "~:suffix", "", "~:name", f"savor_{name}"
        ]]
    ])
    r = ps.s.post(EXPORT_URL, headers=H, data=payload, timeout=60)
    res = r.json()
    uri = res.get("~:uri", {}).get("~#uri", "")
    if uri:
        img = ps.s.get(uri)
        path = f"/home/clawdbot/.openclaw/workspace/drafts/savor_{name}.png"
        with open(path, "wb") as f:
            f.write(img.content)
        print(f"  {name}: {len(img.content)//1024}KB -> {path}")
    else:
        print(f"  {name}: FAILED")

print("\nSavor app complete!")
