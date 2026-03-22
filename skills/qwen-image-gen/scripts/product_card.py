#!/usr/bin/env python3
"""
Product Card Generator — одна финальная карточка товара.
Вариант C: AI генерирует красивый шаблон/фон, Pillow вставляет товар + точный текст.

Pipeline:
  1. remove-bg (если есть фото) или flux-dev (генерация из описания)
  2. recraft-v4 генерирует шаблон карточки (градиент, декор, место под товар)
  3. Pillow composite: товар + текст (название, цена, скидка, фичи, бейджи)
  4. Сохранение + отправка

Usage:
  source ~/.openclaw/secrets.env
  python3 product_card.py "Кроссовки Nike Air Max" --price 8990 --old-price 12990 \
    --features "Амортизация Air" "Дышащий верх" "Подошва EVA" \
    --photo https://example.com/shoe.jpg \
    --output /tmp/card.png
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ─── Pillow ───────────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

REPLICATE_API = "https://api.replicate.com/v1"
FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

# Version hashes for models that require them
MODEL_VERSIONS = {
    "recraft-ai/recraft-v4": "a8bc7377c37baeea1e01568f88b6abfb38939135071a38ca4267c8f82c3cbbf0",
    "qwen/qwen-image": "0bba9e70f78437359725e0989ead45ca8b09e6c12a070dfe9a09e6856b43a44d",
    "black-forest-labs/flux-dev": "6e4a938f85952bdabcc15aa329178c4d681c52bf25a0342403287dc26944661d",
    "lucataco/remove-bg": "95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1",
}

# Card size (WB/Ozon standard)
CARD_W = 1200
CARD_H = 1600


def load_token():
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        for path in [
            Path.home() / ".openclaw" / "secrets.env",
            Path(".env"),
        ]:
            if path.exists():
                for line in path.read_text().splitlines():
                    if line.startswith("REPLICATE_API_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"\'')
    if not token:
        print("❌ REPLICATE_API_TOKEN not found", file=sys.stderr)
        sys.exit(1)
    return token


def curl_json(method, path, data=None, token=None):
    url = REPLICATE_API + path
    cmd = ["curl", "-s", "-X", method, url,
           "-H", f"Authorization: Bearer {token}",
           "-H", "Content-Type: application/json"]
    if data:
        cmd += ["-d", json.dumps(data)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout)
    except Exception:
        print(f"❌ curl error: {r.stdout[:200]} {r.stderr[:100]}", file=sys.stderr)
        sys.exit(1)


def curl_download(url, out_path, token):
    subprocess.run(
        ["curl", "-s", "-L", "-o", str(out_path),
         "-H", f"Authorization: Bearer {token}", url],
        check=True, timeout=60
    )


def poll(pred_id, token, label="Генерация", max_wait=120):
    start = time.time()
    i = 0
    while time.time() - start < max_wait:
        d = curl_json("GET", f"/predictions/{pred_id}", token=token)
        status = d.get("status")
        if status == "succeeded":
            elapsed = time.time() - start
            print(f"\r✅ {label} — {elapsed:.1f}s           ", file=sys.stderr)
            out = d.get("output", [])
            return out[0] if isinstance(out, list) and out else out
        if status in ("failed", "canceled"):
            print(f"\n❌ {label} {status}: {d.get('error')}", file=sys.stderr)
            sys.exit(1)
        dots = "." * ((i % 3) + 1)
        print(f"\r⏳ {label}{dots}   ", end="", flush=True, file=sys.stderr)
        i += 1
        time.sleep(1.5)
    print(f"\n❌ Timeout {max_wait}s", file=sys.stderr)
    sys.exit(1)


def replicate_run(model_id, version, inp, token, label):
    # Auto-lookup version if not provided
    if not version:
        version = MODEL_VERSIONS.get(model_id)
    payload = {"input": inp}
    if version:
        payload["version"] = version
    else:
        payload["model"] = model_id
    d = curl_json("POST", "/predictions", data=payload, token=token)
    pred_id = d.get("id")
    if not pred_id:
        print(f"❌ No prediction ID: {json.dumps(d)[:200]}", file=sys.stderr)
        sys.exit(1)
    print(f"   🆔 {pred_id}", file=sys.stderr)
    return poll(pred_id, token, label)


def remove_bg(image_url, token, tmp_dir):
    """Remove background from image URL. Returns path to PNG with alpha."""
    print("🔪 Удаление фона...", file=sys.stderr)
    # Upload local file if needed
    p = Path(image_url)
    if p.exists():
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", f"{REPLICATE_API}/files",
             "-H", f"Authorization: Bearer {token}",
             "-F", f"content=@{p}"],
            capture_output=True, text=True, timeout=60
        )
        d = json.loads(r.stdout)
        image_url = d.get("urls", {}).get("get") or d.get("url", image_url)

    url = replicate_run(
        "lucataco/remove-bg", None,
        {"image": image_url},
        token, "Remove BG"
    )
    out = Path(tmp_dir) / "product_nobg.png"
    curl_download(url, out, token)
    return out


def generate_product_image(name, category, token, tmp_dir):
    """Generate product image with AI when no photo provided."""
    print("🎨 Генерация изображения товара...", file=sys.stderr)
    prompt = (
        f"Professional product photo of {name}, {category} category, "
        f"isolated on pure white background, studio lighting, "
        f"high resolution, sharp focus, commercial photography style"
    )
    url = replicate_run(
        "black-forest-labs/flux-dev", None,
        {
            "prompt": prompt,
            "aspect_ratio": "3:4",
            "num_inference_steps": 28,
            "guidance": 3.5,
            "output_format": "png",
            "output_quality": 95,
        },
        token, "Генерация товара"
    )
    out = Path(tmp_dir) / "product_generated.png"
    curl_download(url, out, token)
    return out


def generate_card_template(name, category, color_scheme, token, tmp_dir):
    """Generate beautiful card background/template with recraft-v4."""
    print("🖼️  Генерация шаблона карточки...", file=sys.stderr)

    color_map = {
        "blue": "deep blue and white",
        "dark": "dark charcoal and gold",
        "warm": "warm beige and terracotta",
        "green": "forest green and cream",
        "purple": "deep purple and silver",
        "red": "bold red and white",
        "minimal": "clean white with light gray accents",
    }
    colors = color_map.get(color_scheme, color_map["minimal"])

    prompt = (
        f"Marketplace product card template background, {colors} color scheme, "
        f"modern e-commerce design, clean layout with large empty center area for product photo, "
        f"subtle geometric decorative elements in corners, "
        f"bottom section with slightly darker band for text, "
        f"top area with brand space, professional retail design, "
        f"3:4 vertical format, no text, no product, template only"
    )
    url = replicate_run(
        "recraft-ai/recraft-v4", None,
        {
            "prompt": prompt,
            "style": "realistic_image",
            "size": "832x1280",  # closest to 3:4 from allowed sizes
        },
        token, "Шаблон карточки"
    )
    out = Path(tmp_dir) / "card_template.png"
    curl_download(url, out, token)
    return out


def composite_card(template_path, product_path, product_data, output_path):
    """Compose final card: template + product + text overlays."""
    if not HAS_PILLOW:
        print("❌ Pillow не установлен. pip3 install Pillow", file=sys.stderr)
        sys.exit(1)

    name = product_data["name"]
    price = product_data.get("price")
    old_price = product_data.get("old_price")
    features = product_data.get("features", [])[:3]
    badge = product_data.get("badge", "")

    # Load images
    template = Image.open(template_path).convert("RGBA").resize((CARD_W, CARD_H))
    product = Image.open(product_path).convert("RGBA")

    # Scale product to fit upper 60% of card, centered
    product_area_h = int(CARD_H * 0.58)
    product_area_w = int(CARD_W * 0.80)
    product.thumbnail((product_area_w, product_area_h), Image.LANCZOS)

    prod_x = (CARD_W - product.width) // 2
    prod_y = int(CARD_H * 0.05)

    # Paste product onto template
    card = template.copy()
    card.paste(product, (prod_x, prod_y), product)

    draw = ImageDraw.Draw(card)

    # ── Fonts ──
    def font(size, bold=True):
        path = FONT_PATH if bold else FONT_REGULAR
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    # ── Discount badge ──
    if old_price and price and old_price > price:
        discount = round((1 - price / old_price) * 100)
        badge_text = f"−{discount}%"
        bw, bh = 160, 160
        bx, by = CARD_W - bw - 30, 30
        # Circle background
        draw.ellipse([bx, by, bx + bw, by + bh], fill="#E8002D")
        bf = font(48)
        bbox = draw.textbbox((0, 0), badge_text, font=bf)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (bx + (bw - tw) // 2, by + (bh - th) // 2),
            badge_text, font=bf, fill="white"
        )

    if badge and not (old_price and price):
        bw, bh = 200, 60
        draw.rounded_rectangle([30, 30, 30 + bw, 30 + bh], radius=10, fill="#E8002D")
        bf = font(32)
        draw.text((50, 40), badge, font=bf, fill="white")

    # ── Bottom text area ──
    text_y = int(CARD_H * 0.65)

    # Subtle overlay for readability
    overlay = Image.new("RGBA", (CARD_W, CARD_H - text_y), (0, 0, 0, 100))
    card.paste(overlay, (0, text_y), overlay)

    # Product name
    name_font = font(52)
    # Wrap name if too long
    words = name.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=name_font)
        if bbox[2] - bbox[0] > CARD_W - 80:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    y = text_y + 25
    for line in lines[:2]:
        draw.text((40, y), line, font=name_font, fill="white",
                  stroke_width=1, stroke_fill=(0, 0, 0, 180))
        y += 65

    y += 10

    # Price
    if price:
        price_str = f"{price:,}₽".replace(",", " ")
        pf = font(72)
        draw.text((40, y), price_str, font=pf, fill="#FFE500",
                  stroke_width=1, stroke_fill=(0, 0, 0, 150))
        y += 85

    # Old price (strikethrough)
    if old_price and old_price > (price or 0):
        old_str = f"{old_price:,}₽".replace(",", " ")
        of = font(44, bold=False)
        bbox = draw.textbbox((40, y), old_str, font=of)
        draw.text((40, y), old_str, font=of, fill="#CCCCCC")
        # Strikethrough line
        mid_y = y + (bbox[3] - bbox[1]) // 2
        draw.line([(40, mid_y), (bbox[2], mid_y)], fill="#CCCCCC", width=3)
        y += 60

    y += 15

    # Features (bullet points)
    ff = font(36, bold=False)
    for feat in features:
        draw.text((40, y), f"✓  {feat}", font=ff, fill="white",
                  stroke_width=1, stroke_fill=(0, 0, 0, 120))
        y += 50

    # Convert to RGB for JPEG output
    final = card.convert("RGB")
    final.save(str(output_path), quality=95)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate single product card (Variant C)")
    parser.add_argument("name", help="Product name")
    parser.add_argument("--price", type=int, help="Current price (₽)")
    parser.add_argument("--old-price", type=int, help="Old/crossed-out price (₽)")
    parser.add_argument("--category", default="Товар", help="Product category")
    parser.add_argument("--features", nargs="+", default=[],
                        help="Key features (up to 3)")
    parser.add_argument("--badge", default="", help="Custom badge text e.g. 'Хит продаж'")
    parser.add_argument("--photo", default=None,
                        help="Product photo URL or local path")
    parser.add_argument("--color", default="minimal",
                        choices=["minimal", "blue", "dark", "warm", "green", "purple", "red"],
                        help="Card color scheme (default: minimal)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output path (default: drafts/card_<name>.jpg)")
    parser.add_argument("--keep-tmp", action="store_true",
                        help="Keep temporary files for debugging")

    args = parser.parse_args()
    token = load_token()

    if not HAS_PILLOW:
        print("❌ Pillow требуется: pip3 install Pillow", file=sys.stderr)
        sys.exit(1)

    # Output path
    if args.output:
        output_path = Path(args.output)
    else:
        drafts = Path.home() / ".openclaw" / "workspace" / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in args.name[:25]).strip()
        output_path = drafts / f"card_{safe}.jpg"

    product_data = {
        "name": args.name,
        "price": args.price,
        "old_price": args.old_price,
        "features": args.features[:3],
        "badge": args.badge,
    }

    print(f"\n🛒 Карточка товара: {args.name}", file=sys.stderr)
    print(f"   💰 Цена: {args.price}₽" + (f" (было {args.old_price}₽)" if args.old_price else ""), file=sys.stderr)
    print(f"   🎨 Стиль: {args.color}\n", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Step 1: Product image (remove-bg or generate)
        if args.photo:
            product_path = remove_bg(args.photo, token, tmp_dir)
        else:
            product_path = generate_product_image(args.name, args.category, token, tmp_dir)

        # Pause to respect Replicate rate limit (6 req/min = 1 per 10s)
        print("⏸️  Пауза (rate limit)...", file=sys.stderr)
        time.sleep(12)

        # Step 2: Card template
        template_path = generate_card_template(args.name, args.category, args.color, token, tmp_dir)

        # Step 3: Composite
        print("🧩 Сборка карточки...", file=sys.stderr)
        composite_card(
            template_path,
            product_path,
            product_data,
            output_path
        )

        if args.keep_tmp:
            import shutil
            debug_dir = output_path.parent / f"debug_{output_path.stem}"
            shutil.copytree(tmp_dir, str(debug_dir), dirs_exist_ok=True)
            print(f"   🔍 Debug files: {debug_dir}", file=sys.stderr)

    print(f"\n✅ Карточка готова: {output_path}", file=sys.stderr)

    # Cost estimate
    cost = 0.04  # recraft template
    cost += 0.002 if args.photo else 0.025  # remove-bg or flux-dev
    print(f"   💵 Стоимость: ~${cost:.3f}", file=sys.stderr)

    print(str(output_path))  # stdout — path for piping


if __name__ == "__main__":
    main()
