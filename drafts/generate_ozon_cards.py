#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# Paths
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
TOY_IMG = "/home/clawdbot/.openclaw/media/inbound/file_527---a3deee1a-e522-4ab9-b8d0-2714a4a6ae0a.jpg"
OUT_DIR = "/home/clawdbot/.openclaw/workspace/drafts"

SIZE = (1000, 1000)

def font(path, size):
    return ImageFont.truetype(path, size)

def draw_rounded_rect(draw, xy, radius, fill, outline=None, outline_width=2):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=outline_width)

def gradient_bg(size, color1, color2, vertical=True):
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    w, h = size
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    steps = h if vertical else w
    for i in range(steps):
        t = i / steps
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        if vertical:
            draw.line([(0, i), (w, i)], fill=(r, g, b))
        else:
            draw.line([(i, 0), (i, h)], fill=(r, g, b))
    return img

def load_toy(target_height=500):
    img = Image.open(TOY_IMG).convert("RGBA")
    w, h = img.size
    ratio = target_height / h
    new_w = int(w * ratio)
    return img.resize((new_w, target_height), Image.LANCZOS)

def centered_text(draw, text, y, font_obj, fill, width=1000):
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    draw.text((x, y), text, font=font_obj, fill=fill)

def text_height(draw, text, font_obj):
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    return bbox[3] - bbox[1]

# ─────────────────────────────────────────────
# CARD 1 — HERO
# ─────────────────────────────────────────────
def card1():
    img = gradient_bg(SIZE, (255, 249, 230), (255, 224, 102))
    draw = ImageDraw.Draw(img)

    # Title
    f_title = font(FONT_BOLD, 72)
    f_sub = font(FONT_BOLD, 38)

    # Shadow effect for title
    title = "Музыкальная игрушка"
    # Draw shadow
    centered_text(draw, title, 58, f_title, (200, 160, 0, 80), 1000)
    centered_text(draw, title, 55, f_title, (80, 60, 0))

    # Toy image
    toy = load_toy(520)
    tx = (1000 - toy.width) // 2
    ty = 155
    img.paste(toy, (tx, ty), toy)

    # Pills at bottom
    pills = ["10 сказок", "26 песенок", "6 мелодий для сна"]
    pill_colors = [(255, 200, 0), (255, 170, 30), (255, 140, 60)]
    pill_text_colors = [(80, 50, 0), (80, 50, 0), (80, 50, 0)]
    f_pill = font(FONT_BOLD, 32)

    # Calculate total width
    pill_widths = []
    for p in pills:
        bb = draw.textbbox((0,0), p, font=f_pill)
        pill_widths.append(bb[2] - bb[0] + 48)

    total_w = sum(pill_widths) + 20 * (len(pills)-1)
    start_x = (1000 - total_w) // 2
    pill_y = 870
    pill_h = 54

    for i, (pill, pw, pc, ptc) in enumerate(zip(pills, pill_widths, pill_colors, pill_text_colors)):
        px = start_x + sum(pill_widths[:i]) + 20 * i
        draw_rounded_rect(draw, (px, pill_y, px + pw, pill_y + pill_h), 27, pc)
        bb = draw.textbbox((0,0), pill, font=f_pill)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        tx2 = px + (pw - tw) // 2
        ty2 = pill_y + (pill_h - th) // 2 - bb[1]
        draw.text((tx2, ty2), pill, font=f_pill, fill=ptc)

    # Decorative dots
    for x, y, r, c in [(50, 50, 15, (255,200,50,120)), (950, 80, 10, (255,180,0,100)),
                        (30, 900, 8, (255,220,80,100)), (970, 950, 12, (255,200,30,100))]:
        draw.ellipse((x-r, y-r, x+r, y+r), fill=c)

    img = img.convert("RGB")
    path = os.path.join(OUT_DIR, "ozon_card_1_hero.png")
    img.save(path, "PNG")
    print(f"Saved: {path}")

# ─────────────────────────────────────────────
# CARD 2 — FEATURES
# ─────────────────────────────────────────────
def card2():
    img = Image.new("RGB", SIZE, (240, 248, 255))
    draw = ImageDraw.Draw(img)

    f_title = font(FONT_BOLD, 66)
    f_block_title = font(FONT_BOLD, 44)
    f_block_sub = font(FONT_REG, 30)
    f_bottom = font(FONT_BOLD, 36)

    # Decorative top arc
    draw.ellipse((-200, -300, 1200, 200), fill=(210, 235, 255))

    # Title
    centered_text(draw, "Что умеет Зайчик?", 60, f_title, (30, 80, 150))

    # 3 blocks
    blocks = [
        ("10 сказок", "Русские народные сказки", (255, 230, 100), (80, 60, 0), (120, 90, 0)),
        ("26 детских песенок", "Любимые с детства", (180, 230, 255), (0, 60, 120), (0, 80, 160)),
        ("6 мелодий для сна", "Нежные колыбельные", (200, 240, 200), (0, 80, 40), (0, 100, 50)),
    ]

    block_w = 860
    block_h = 170
    block_x = 70
    start_y = 185

    for i, (title, sub, bg, tc, sc) in enumerate(blocks):
        by = start_y + i * (block_h + 25)
        # Shadow
        draw_rounded_rect(draw, (block_x+4, by+4, block_x+block_w+4, by+block_h+4), 24, (200, 210, 220))
        # Block
        draw_rounded_rect(draw, (block_x, by, block_x+block_w, by+block_h), 24, bg)

        # Icon circle
        ic_x = block_x + 35
        ic_y = by + block_h // 2
        ic_r = 40
        draw.ellipse((ic_x - ic_r, ic_y - ic_r, ic_x + ic_r, ic_y + ic_r), fill=(255,255,255,180))

        # Number
        num = title.split()[0]
        f_num = font(FONT_BOLD, 36)
        nb = draw.textbbox((0,0), num, font=f_num)
        nw = nb[2] - nb[0]
        nh = nb[3] - nb[1]
        draw.text((ic_x - nw//2, ic_y - nh//2 - nb[1]), num, font=f_num, fill=tc)

        # Text
        txt_x = block_x + 105
        f_bt = font(FONT_BOLD, 40)
        f_bs = font(FONT_REG, 28)
        draw.text((txt_x, by + 35), title, font=f_bt, fill=tc)
        draw.text((txt_x, by + 90), sub, font=f_bs, fill=sc)

    # Bottom label
    label = "Для детей от 0+"
    bb = draw.textbbox((0,0), label, font=f_bottom)
    lw = bb[2] - bb[0]
    lh = bb[3] - bb[1]
    lx = (1000 - lw - 60) // 2
    ly = 890
    draw_rounded_rect(draw, (lx, ly, lx + lw + 60, ly + lh + 24), 30, (100, 160, 220))
    draw.text((lx + 30, ly + 12 - bb[1]), label, font=f_bottom, fill=(255,255,255))

    path = os.path.join(OUT_DIR, "ozon_card_2_features.png")
    img.save(path, "PNG")
    print(f"Saved: {path}")

# ─────────────────────────────────────────────
# CARD 3 — BENEFITS
# ─────────────────────────────────────────────
def card3():
    img = Image.new("RGB", SIZE, (255, 240, 245))
    draw = ImageDraw.Draw(img)

    # Top decoration
    draw.ellipse((-100, -200, 1100, 300), fill=(255, 220, 235))

    f_title = font(FONT_BOLD, 64)
    f_item = font(FONT_BOLD, 40)
    f_check = font(FONT_BOLD, 52)

    centered_text(draw, "Почему выбирают нас?", 55, f_title, (160, 40, 80))

    items = [
        "Безопасный пластик (BPA free)",
        "Удобно держать маленьким ручкам",
        "Яркие цвета развивают зрение",
        "Тихая кнопка включения",
    ]

    item_bg = [(255, 245, 250), (255, 240, 248), (255, 248, 252), (255, 244, 250)]
    start_y = 200
    row_h = 140
    row_w = 860
    row_x = 70

    for i, (item, ibg) in enumerate(zip(items, item_bg)):
        ry = start_y + i * (row_h + 18)
        # Shadow
        draw_rounded_rect(draw, (row_x+3, ry+3, row_x+row_w+3, ry+row_h+3), 20, (230, 210, 220))
        # Row bg
        draw_rounded_rect(draw, (row_x, ry, row_x+row_w, ry+row_h), 20, ibg,
                          outline=(255, 180, 200), outline_width=2)

        # Green checkmark circle
        cx = row_x + 65
        cy = ry + row_h // 2
        draw.ellipse((cx-35, cy-35, cx+35, cy+35), fill=(80, 200, 100))
        # Checkmark
        draw.text((cx - 18, cy - 28), "✓", font=font(FONT_BOLD, 46), fill=(255,255,255))

        # Item text
        bb = draw.textbbox((0,0), item, font=f_item)
        th = bb[3] - bb[1]
        draw.text((row_x + 120, ry + row_h//2 - th//2 - bb[1]//2), item, font=f_item, fill=(100, 30, 60))

    # Bottom accent
    acc_text = "Одобрено педиатрами"
    f_acc = font(FONT_BOLD, 32)
    bb = draw.textbbox((0,0), acc_text, font=f_acc)
    aw = bb[2] - bb[0]
    ax = (1000 - aw - 60) // 2
    ay = 920
    draw_rounded_rect(draw, (ax, ay, ax + aw + 60, ay + 50), 25, (255, 120, 160))
    draw.text((ax + 30, ay + 9 - bb[1]), acc_text, font=f_acc, fill=(255, 255, 255))

    path = os.path.join(OUT_DIR, "ozon_card_3_benefits.png")
    img.save(path, "PNG")
    print(f"Saved: {path}")

# ─────────────────────────────────────────────
# CARD 4 — EMOTIONAL
# ─────────────────────────────────────────────
def card4():
    img = Image.new("RGB", SIZE, (255, 245, 238))
    draw = ImageDraw.Draw(img)

    # Soft circle decoration
    draw.ellipse((600, -100, 1200, 500), fill=(255, 230, 210))
    draw.ellipse((-100, 500, 400, 1100), fill=(255, 235, 215))

    f_big = font(FONT_BOLD, 70)
    f_sub = font(FONT_REG, 36)
    f_stars = font(FONT_BOLD, 50)
    f_rating = font(FONT_BOLD, 34)

    # Main headline (two lines)
    line1 = "Сладкие сны"
    line2 = "каждую ночь"
    centered_text(draw, line1, 55, f_big, (180, 80, 30))
    centered_text(draw, line2, 135, f_big, (180, 80, 30))

    # Sub
    sub = "Споёт колыбельную и расскажет сказку"
    centered_text(draw, sub, 235, f_sub, (150, 90, 60))

    # Toy image
    toy = load_toy(460)
    tx = (1000 - toy.width) // 2
    ty = 300
    img.paste(toy, (tx, ty), toy)

    # Stars rating box
    stars = "★★★★★"
    rating_text = "4.9  ·  Более 500 отзывов"

    sb = draw.textbbox((0,0), stars, font=f_stars)
    sw = sb[2] - sb[0]
    rb = draw.textbbox((0,0), rating_text, font=f_rating)
    rw = rb[2] - rb[0]

    box_w = max(sw, rw) + 80
    box_x = (1000 - box_w) // 2
    box_y = 840

    draw_rounded_rect(draw, (box_x, box_y, box_x + box_w, box_y + 130), 30,
                      (255, 200, 150), outline=(255, 160, 80), outline_width=3)

    # Stars
    centered_text(draw, stars, box_y + 12, f_stars, (255, 160, 0))
    # Rating
    centered_text(draw, rating_text, box_y + 76, f_rating, (120, 60, 20))

    path = os.path.join(OUT_DIR, "ozon_card_4_emotional.png")
    img.save(path, "PNG")
    print(f"Saved: {path}")

# Run all
os.makedirs(OUT_DIR, exist_ok=True)
card1()
card2()
card3()
card4()
print("All done!")
