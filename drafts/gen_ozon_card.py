#!/usr/bin/env python3
"""Generate OZON product card for musical bunny toy."""

import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- Config ---
SIZE = (1000, 1000)
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
TOY_PATH = "/home/clawdbot/.openclaw/media/inbound/file_527---a3deee1a-e522-4ab9-b8d0-2714a4a6ae0a.jpg"
OUT_PATH = "/home/clawdbot/.openclaw/workspace/drafts/ozon_pro_card.png"

# Colors
COLOR_TOP = (62, 216, 220)      # #3ED8DC
COLOR_BOT = (41, 181, 200)      # #29B5C8
COLOR_BUBBLE = (168, 238, 240, 200)  # #A8EEF0 with alpha
COLOR_YELLOW = (255, 220, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_SHADOW = (0, 100, 120, 160)


def star_points(cx, cy, r_outer, r_inner, n=5):
    points = []
    for i in range(n * 2):
        angle = math.pi / 2 + i * math.pi / n
        r = r_outer if i % 2 == 0 else r_inner
        points.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
    return points


def draw_gradient(img):
    """Draw vertical gradient background."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / h
        r = int(COLOR_TOP[0] + (COLOR_BOT[0] - COLOR_TOP[0]) * t)
        g = int(COLOR_TOP[1] + (COLOR_BOT[1] - COLOR_TOP[1]) * t)
        b = int(COLOR_TOP[2] + (COLOR_BOT[2] - COLOR_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def draw_star(draw, cx, cy, r_outer, r_inner, color):
    pts = star_points(cx, cy, r_outer, r_inner)
    draw.polygon(pts, fill=color)


def draw_bubble(base_img, x, y, w, h, num_text, label_text, font_big, font_small):
    """Draw semi-transparent oval bubble with number + label."""
    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Draw ellipse
    d.ellipse([x, y, x + w, y + h], fill=COLOR_BUBBLE)

    # Number — large bold
    cx = x + w // 2
    cy_num = y + h // 2 - 30

    # Shadow
    bbox = font_big.getbbox(num_text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    d.text((cx - tw // 2 + 2, cy_num - th // 2 + 2), num_text,
            font=font_big, fill=(0, 80, 100, 120))
    d.text((cx - tw // 2, cy_num - th // 2), num_text,
            font=font_big, fill=(20, 80, 100, 255))

    # Label — small
    lines = label_text.split("\n")
    line_h = font_small.getbbox("A")[3] + 4
    total_h = line_h * len(lines)
    cy_label = y + h // 2 + 28
    for i, line in enumerate(lines):
        bb = font_small.getbbox(line)
        lw = bb[2] - bb[0]
        d.text((cx - lw // 2, cy_label + i * line_h), line,
               font=font_small, fill=(20, 80, 100, 230))

    base_img.paste(overlay, mask=overlay)


def main():
    # Create base RGBA image
    img = Image.new("RGBA", SIZE, (0, 0, 0, 255))
    draw_gradient(img)

    draw = ImageDraw.Draw(img)

    # --- Fonts ---
    font_title = ImageFont.truetype(FONT_BOLD, 68)
    font_title_sm = ImageFont.truetype(FONT_BOLD, 60)
    font_num = ImageFont.truetype(FONT_BOLD, 90)
    font_label = ImageFont.truetype(FONT_BOLD, 28)
    font_disclaimer = ImageFont.truetype(FONT_REG, 22)

    # --- Decorative stars (small, around title) ---
    # Left star near title
    draw_star(draw, 120, 105, 38, 16, COLOR_YELLOW)
    # Right star near title
    draw_star(draw, 880, 105, 38, 16, COLOR_YELLOW)
    # Extra small accent stars
    draw_star(draw, 75, 155, 18, 8, COLOR_YELLOW)
    draw_star(draw, 925, 155, 18, 8, COLOR_YELLOW)

    # --- Title ---
    title_lines = ["МУЗЫКАЛЬНАЯ", "ИГРУШКА-ЗАЙЧИК"]
    y_start = 40
    for i, line in enumerate(title_lines):
        bbox = font_title.getbbox(line)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (SIZE[0] - tw) // 2
        y = y_start + i * (th + 10)
        # Shadow
        draw.text((x + 3, y + 3), line, font=font_title, fill=(0, 100, 120, 180))
        # Text
        draw.text((x, y), line, font=font_title, fill=COLOR_WHITE)

    # --- Toy image ---
    toy = Image.open(TOY_PATH).convert("RGBA")
    # Resize to 600px height, preserve aspect
    tw, th = toy.size
    new_h = 600
    new_w = int(tw * new_h / th)
    toy = toy.resize((new_w, new_h), Image.LANCZOS)
    # Center horizontally, vertically around middle-lower area
    toy_x = (SIZE[0] - new_w) // 2 + 20
    toy_y = 300
    img.paste(toy, (toy_x, toy_y), mask=toy)

    # --- Bubbles ---
    # Bubble 1: top-left — "10 сказок"
    draw_bubble(img, 55, 240, 260, 200, "10", "сказок", font_num, font_label)

    # Bubble 2: bottom-left — "26 песенок"
    draw_bubble(img, 40, 500, 260, 200, "26", "песенок", font_num, font_label)

    # Bubble 3: right — "6 мелодий для сна"
    draw_bubble(img, 648, 400, 290, 220, "6", "мелодий\nдля сна", font_num, font_label)

    # --- Big yellow star bottom-left ---
    draw_star(draw, 110, 870, 70, 30, COLOR_YELLOW)

    # --- Disclaimer text ---
    disclaimer = "Игрушка для детей от 6 месяцев. Работает от батареек."
    bb = font_disclaimer.getbbox(disclaimer)
    dw = bb[2] - bb[0]
    draw.text(((SIZE[0] - dw) // 2, 955), disclaimer,
              font=font_disclaimer, fill=(255, 255, 255, 180))

    # --- Save ---
    out = img.convert("RGB")
    out.save(OUT_PATH, "PNG", quality=95)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
