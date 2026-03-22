#!/usr/bin/env python3
"""
Product Card Pipeline — генерация комплекта карточек товара для WB/Ozon.

Расширение скилла qwen-image-gen. Использует существующий generate.py
как базу + добавляет remove-bg, text overlay, параллельную генерацию.

Usage:
  python3 product_card_pipeline.py \
    --name "Кроссовки Nike Air Max" \
    --price 8990 --old-price 12990 \
    --category "Обувь" \
    --features "Амортизация Air,Дышащий верх,Подошва EVA" \
    --photo https://example.com/shoe.jpg

  # Без фото (AI генерация):
  python3 product_card_pipeline.py \
    --name "Беспроводные наушники" --price 3490 \
    --category "Электроника"

  # JSON input:
  python3 product_card_pipeline.py \
    --json '{"name":"Рюкзак","price":4590,"features":["30л","Водостойкий"]}'

Requirements:
  - REPLICATE_API_TOKEN in env or ~/.openclaw/secrets.env
  - curl (subprocess)
  - Pillow (pip3 install Pillow) — for text overlays; degrades gracefully without it
  - Python 3.8+
"""

import argparse
import json
import os
import subprocess
import sys
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

REPLICATE_API = "https://api.replicate.com/v1"
CARD_WIDTH = 1440
CARD_HEIGHT = 1920
OUTPUT_FORMAT = "png"
MAX_POLL_WAIT = 180

# Model choices per step
MODELS = {
    "remove_bg": "lucataco/remove-bg",
    "generate_product": {
        "model": "black-forest-labs/flux-dev",
        "cost": 0.025,
        "params": {
            "num_inference_steps": 28,
            "guidance": 3.5,
            "aspect_ratio": "3:4",
            "output_format": "png",
            "output_quality": 95,
        },
    },
    "info_card": {
        "model": "recraft-ai/recraft-v4",
        "cost": 0.040,
        "params": {"aspect_ratio": "3:4"},
    },
    "lifestyle": {
        "model": "black-forest-labs/flux-kontext-pro",
        "cost": 0.040,
        "params": {
            "aspect_ratio": "3:4",
            "output_format": "png",
            "output_quality": 95,
            "safety_tolerance": 5,
        },
    },
    "specs_card": {
        "model": "recraft-ai/recraft-v4",
        "cost": 0.040,
        "params": {"aspect_ratio": "3:4"},
    },
    "promo_card": {
        "model": "recraft-ai/recraft-v4",
        "cost": 0.040,
        "params": {"aspect_ratio": "3:4"},
    },
}

# Lifestyle scene templates per category
LIFESTYLE_SCENES = {
    "Обувь": "person walking in a modern city street, natural daylight, lifestyle photography",
    "Электроника": "modern minimalist desk setup, warm lighting, lifestyle tech photography",
    "Одежда": "fashion model in urban setting, natural lighting, lifestyle photography",
    "Сумки": "traveler at airport or cafe, natural daylight, lifestyle photography",
    "Дом": "cozy modern living room interior, natural lighting, lifestyle photography",
    "Спорт": "gym or outdoor workout area, energetic lighting, lifestyle fitness photography",
    "Красота": "bathroom vanity with mirror, soft lighting, beauty lifestyle photography",
    "default": "clean modern interior, natural soft lighting, lifestyle product photography",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    print(msg, file=sys.stderr, flush=True)


def load_token():
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        secrets = Path.home() / ".openclaw" / "secrets.env"
        if secrets.exists():
            for line in secrets.read_text().splitlines():
                line = line.strip()
                if line.startswith("REPLICATE_API_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token:
        log("❌ REPLICATE_API_TOKEN not found")
        sys.exit(1)
    return token


def curl_json(method, url, data=None, token=None, timeout=30):
    cmd = [
        "curl", "-s", "-X", method, url,
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
    ]
    if data:
        cmd += ["-d", json.dumps(data)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"curl error: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON: {result.stdout[:300]}")


def curl_download(url, out_path, timeout=60):
    cmd = ["curl", "-s", "-L", "-o", str(out_path), url]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"Download failed: {result.stderr.decode()}")


def upload_to_replicate(local_path, token):
    """Upload a local file to Replicate Files API, return URL."""
    p = Path(local_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {local_path}")
    log(f"📤 Uploading {p.name}...")
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            f"{REPLICATE_API}/files",
            "-H", f"Authorization: Bearer {token}",
            "-F", f"content=@{p}",
        ],
        capture_output=True, text=True, timeout=60,
    )
    d = json.loads(result.stdout)
    url = d.get("urls", {}).get("get") or d.get("url")
    if not url:
        raise RuntimeError(f"Upload failed: {result.stdout[:200]}")
    log(f"✅ Uploaded → {url[:80]}...")
    return url


def poll_prediction(pred_id, token, max_wait=MAX_POLL_WAIT):
    start = time.time()
    while time.time() - start < max_wait:
        d = curl_json("GET", f"{REPLICATE_API}/predictions/{pred_id}", token=token)
        status = d.get("status")
        if status == "succeeded":
            elapsed = time.time() - start
            log(f"  ✅ Prediction {pred_id[:8]} done in {elapsed:.1f}s")
            return d.get("output")
        elif status in ("failed", "canceled"):
            raise RuntimeError(f"Prediction {status}: {d.get('error')}")
        time.sleep(1.5)
    raise TimeoutError(f"Prediction timed out after {max_wait}s")


def run_model(model_id, inp, token, version=None):
    """Create prediction, poll, return output URL(s)."""
    if version:
        payload = {"version": version, "input": inp}
    else:
        payload = {"model": model_id, "input": inp}

    d = curl_json("POST", f"{REPLICATE_API}/predictions", data=payload, token=token)
    pred_id = d.get("id")
    if not pred_id:
        error = d.get("detail") or d.get("error") or json.dumps(d)[:300]
        raise RuntimeError(f"Failed to create prediction: {error}")

    log(f"  🆔 {model_id} → {pred_id[:8]}")
    output = poll_prediction(pred_id, token)

    # Normalize output to URL string
    if isinstance(output, list):
        return output[0] if output else None
    return output


def download_to(url, out_dir, name, ext="png"):
    """Download URL to out_dir/name.ext, return path."""
    out_path = Path(out_dir) / f"{name}.{ext}"
    curl_download(url, out_path)
    return str(out_path)


# ─── Pipeline Steps ──────────────────────────────────────────────────────────

def step_remove_bg(image_url, token):
    """Remove background from product photo."""
    log("🔲 Step: Remove background")
    output_url = run_model(
        MODELS["remove_bg"],
        {"image": image_url},
        token,
    )
    if not output_url:
        raise RuntimeError("remove-bg returned no output")
    return output_url


def step_generate_product(product_name, category, token):
    """Generate product image from text (when no photo provided)."""
    log("🎨 Step: Generate product image from description")
    cfg = MODELS["generate_product"]
    prompt = (
        f"Professional product photography of {product_name}, "
        f"category: {category}, isolated on pure white background, "
        f"studio lighting, high detail, commercial product photo, centered"
    )
    inp = {**cfg["params"], "prompt": prompt}
    output_url = run_model(cfg["model"], inp, token)
    if not output_url:
        raise RuntimeError("Product generation returned no output")
    return output_url


def step_main_photo(product_png_url, out_dir, token):
    """Create main photo: product on clean white background, centered."""
    log("📸 Step: Main photo (white background)")
    # Download the clean product image
    tmp_path = download_to(product_png_url, out_dir, "product_clean")

    try:
        from PIL import Image

        img = Image.open(tmp_path).convert("RGBA")
        # Create white background
        bg = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (255, 255, 255, 255))
        # Scale product to fit with padding (80% of width, 70% of height)
        max_w = int(CARD_WIDTH * 0.80)
        max_h = int(CARD_HEIGHT * 0.70)
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        # Center
        x = (CARD_WIDTH - img.width) // 2
        y = (CARD_HEIGHT - img.height) // 2
        bg.paste(img, (x, y), img)
        out_path = Path(out_dir) / "slide_1_main.png"
        bg.convert("RGB").save(str(out_path), "PNG", quality=95)
        log(f"  ✅ Main photo → {out_path}")
        return str(out_path)
    except ImportError:
        log("  ⚠️ Pillow not available, using raw product image as main photo")
        out_path = Path(out_dir) / "slide_1_main.png"
        Path(tmp_path).rename(out_path)
        return str(out_path)


def step_info_card(product_name, features, product_img_url, out_dir, token):
    """Generate info card with key features (Slide 2)."""
    log("📋 Step: Info card with features")
    cfg = MODELS["info_card"]
    features_text = ", ".join(features[:4]) if features else "premium quality"
    prompt = (
        f"Professional product infographic card for '{product_name}'. "
        f"Clean white background, product image in center. "
        f"Key features listed with icons: {features_text}. "
        f"Modern minimalist design, vertical 3:4 layout, "
        f"professional typography, no cluttered text"
    )
    inp = {**cfg["params"], "prompt": prompt}
    output_url = run_model(cfg["model"], inp, token)
    if output_url:
        return download_to(output_url, out_dir, "slide_2_info")
    return None


def step_lifestyle(product_name, category, product_img_url, out_dir, token):
    """Generate lifestyle photo (Slide 3) — product in context."""
    log("🏠 Step: Lifestyle photo")
    cfg = MODELS["lifestyle"]
    scene = LIFESTYLE_SCENES.get(category, LIFESTYLE_SCENES["default"])
    prompt = (
        f"Place this {product_name} product naturally into a scene: {scene}. "
        f"Product should be the hero element, realistic integration, "
        f"professional commercial photography style"
    )
    inp = {**cfg["params"], "prompt": prompt}
    # flux-kontext-pro needs input_image for editing
    if product_img_url:
        inp["input_image"] = product_img_url
    output_url = run_model(cfg["model"], inp, token)
    if output_url:
        return download_to(output_url, out_dir, "slide_3_lifestyle")
    return None


def step_specs_card(product_name, features, dimensions, out_dir, token):
    """Generate specifications/dimensions card (Slide 4)."""
    log("📐 Step: Specs card")
    cfg = MODELS["specs_card"]
    specs_text = ""
    if dimensions:
        specs_text += f"Dimensions: {dimensions}. "
    if features:
        specs_text += "Features: " + ", ".join(features)
    prompt = (
        f"Product specification infographic for '{product_name}'. "
        f"{specs_text}. "
        f"Clean technical drawing style, measurement lines and arrows, "
        f"vertical 3:4 card, professional blueprint aesthetic, "
        f"white background, clear readable text"
    )
    inp = {**cfg["params"], "prompt": prompt}
    output_url = run_model(cfg["model"], inp, token)
    if output_url:
        return download_to(output_url, out_dir, "slide_4_specs")
    return None


def step_promo_card(product_name, price, old_price, out_dir, token):
    """Generate promo/discount card (Slide 5) — optional."""
    if not old_price or old_price <= price:
        return None
    log("🏷️ Step: Promo card")
    cfg = MODELS["promo_card"]
    discount_pct = int((1 - price / old_price) * 100)
    prompt = (
        f"Sale promotional card for '{product_name}'. "
        f"Big bold '-{discount_pct}%' discount badge, "
        f"price {price} RUB crossed out old price {old_price} RUB, "
        f"'SALE' text, red and white color scheme, "
        f"vertical 3:4 card, eye-catching commercial design, "
        f"clean modern typography, urgency feel"
    )
    inp = {**cfg["params"], "prompt": prompt}
    output_url = run_model(cfg["model"], inp, token)
    if output_url:
        return download_to(output_url, out_dir, "slide_5_promo")
    return None


def step_add_price_overlay(image_path, price, old_price=None, badge=None):
    """Add price/discount overlay to an image using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Try to load a decent font, fall back to default
        font_size = 48
        small_font_size = 32
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", small_font_size)
        except (IOError, OSError):
            font = ImageFont.load_default()
            small_font = font

        w, h = img.size

        # Price badge at bottom
        price_text = f"{price:,}₽".replace(",", " ")
        if old_price and old_price > price:
            old_text = f"{old_price:,}₽".replace(",", " ")
            discount_pct = int((1 - price / old_price) * 100)

            # Background rect
            rect_h = 120
            draw.rectangle([(0, h - rect_h), (w, h)], fill=(0, 0, 0, 200))

            # Old price with strikethrough
            draw.text((40, h - rect_h + 15), old_text, fill=(180, 180, 180), font=small_font)
            # Line through old price
            bbox = draw.textbbox((40, h - rect_h + 15), old_text, font=small_font)
            mid_y = (bbox[1] + bbox[3]) // 2
            draw.line([(bbox[0], mid_y), (bbox[2], mid_y)], fill=(255, 80, 80), width=3)

            # New price
            draw.text((40, h - rect_h + 55), price_text, fill=(255, 255, 255), font=font)

            # Discount badge
            badge_text = f"-{discount_pct}%"
            draw.rectangle([(w - 200, h - rect_h + 10), (w - 20, h - rect_h + 70)], fill=(255, 50, 50))
            draw.text((w - 190, h - rect_h + 18), badge_text, fill=(255, 255, 255), font=font)
        else:
            rect_h = 80
            draw.rectangle([(0, h - rect_h), (w, h)], fill=(0, 0, 0, 200))
            draw.text((40, h - rect_h + 15), price_text, fill=(255, 255, 255), font=font)

        # Top badge
        if badge:
            draw.rectangle([(20, 20), (250, 70)], fill=(255, 50, 50))
            draw.text((30, 25), badge, fill=(255, 255, 255), font=small_font)

        img.save(image_path, "PNG", quality=95)
        log(f"  ✅ Overlay added to {Path(image_path).name}")
        return True
    except ImportError:
        log("  ⚠️ Pillow not installed, skipping overlay")
        return False


# ─── Main Pipeline ────────────────────────────────────────────────────────────

def product_card_pipeline(product_data, photo_url=None, out_dir=None, slides="standard"):
    """
    Main pipeline: generates a full set of product card images.

    Args:
        product_data: dict with keys:
            - name (str, required): product name
            - price (int/float, required): price in RUB
            - old_price (int/float, optional): original price for discount calc
            - category (str, optional): product category
            - features (list[str], optional): key features
            - description (str, optional): product description
            - dimensions (str, optional): e.g. "30x20x10 cm"
            - brand (str, optional): brand name
            - badge (str, optional): e.g. "ХИТ", "NEW", "TOP"
        photo_url: URL of product photo (or None to generate)
        out_dir: output directory (default: ~/drafts/cards/<timestamp>/)
        slides: "min" (3-4), "standard" (5-6), "max" (7-8)

    Returns:
        dict with:
            - slides: list of file paths
            - cost: total cost in USD
            - time_s: total time in seconds
            - errors: list of any non-fatal errors
    """
    start_time = time.time()
    token = load_token()

    # Parse product data
    name = product_data["name"]
    price = product_data.get("price", 0)
    old_price = product_data.get("old_price")
    category = product_data.get("category", "Товары")
    features = product_data.get("features", [])
    dimensions = product_data.get("dimensions", "")
    badge = product_data.get("badge")

    # Setup output dir
    if not out_dir:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name[:30]).strip()
        out_dir = Path.home() / ".openclaw" / "workspace" / "drafts" / "cards" / f"{ts}_{safe_name}"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {"slides": [], "cost": 0.0, "time_s": 0, "errors": []}

    log(f"{'='*60}")
    log(f"🏪 Product Card Pipeline")
    log(f"📦 {name} | 💰 {price}₽ | 📂 {category}")
    log(f"📁 Output: {out_dir}")
    log(f"{'='*60}")

    # ── Step 1: Get clean product image ───────────────────────────────────
    product_img_url = None
    if photo_url:
        # Has photo → remove background
        log("\n── Phase 1: Background Removal ──")
        try:
            product_img_url = step_remove_bg(photo_url, token)
            result["cost"] += 0.002
        except Exception as e:
            log(f"  ❌ remove-bg failed: {e}")
            result["errors"].append(f"remove-bg: {e}")
            # Fallback: use original photo
            product_img_url = photo_url
    else:
        # No photo → generate
        log("\n── Phase 1: Product Generation ──")
        try:
            product_img_url = step_generate_product(name, category, token)
            result["cost"] += 0.025
        except Exception as e:
            log(f"  ❌ Generation failed: {e}")
            result["errors"].append(f"generate: {e}")
            return result

    # ── Step 2: Main photo (local, fast) ──────────────────────────────────
    log("\n── Phase 2: Main Photo ──")
    try:
        main_path = step_main_photo(product_img_url, out_dir, token)
        if main_path:
            result["slides"].append(main_path)
    except Exception as e:
        log(f"  ❌ Main photo failed: {e}")
        result["errors"].append(f"main_photo: {e}")

    # ── Step 3: Parallel slide generation ─────────────────────────────────
    log("\n── Phase 3: Parallel Slide Generation ──")

    # Determine which slides to generate
    slide_tasks = []

    # Always: info card + lifestyle
    slide_tasks.append(("info_card", step_info_card, [name, features, product_img_url, out_dir, token]))
    slide_tasks.append(("lifestyle", step_lifestyle, [name, category, product_img_url, out_dir, token]))

    if slides in ("standard", "max"):
        slide_tasks.append(("specs", step_specs_card, [name, features, dimensions, out_dir, token]))

    if slides == "max" and old_price and old_price > price:
        slide_tasks.append(("promo", step_promo_card, [name, price, old_price, out_dir, token]))

    # Run in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for task_name, func, args in slide_tasks:
            future = executor.submit(func, *args)
            futures[future] = task_name

        for future in as_completed(futures):
            task_name = futures[future]
            try:
                path = future.result()
                if path:
                    result["slides"].append(path)
                    # Add cost based on which model was used
                    if task_name in ("info_card", "specs", "promo"):
                        result["cost"] += 0.040  # recraft-v4
                    elif task_name == "lifestyle":
                        result["cost"] += 0.040  # flux-kontext-pro
            except Exception as e:
                log(f"  ❌ {task_name} failed: {e}")
                result["errors"].append(f"{task_name}: {e}")

    # ── Step 4: Price/discount overlays ───────────────────────────────────
    log("\n── Phase 4: Overlays ──")
    # Add price overlay to main photo
    if result["slides"]:
        step_add_price_overlay(result["slides"][0], price, old_price, badge)

    # ── Done ──────────────────────────────────────────────────────────────
    result["time_s"] = round(time.time() - start_time, 1)

    # Sort slides by name for consistent order
    result["slides"].sort()

    log(f"\n{'='*60}")
    log(f"✅ Pipeline complete!")
    log(f"📊 Slides: {len(result['slides'])}")
    log(f"💰 Total cost: ${result['cost']:.3f}")
    log(f"⏱️ Total time: {result['time_s']}s")
    if result["errors"]:
        log(f"⚠️ Errors: {len(result['errors'])}")
    log(f"📁 Output: {out_dir}")
    log(f"{'='*60}")

    # Save manifest
    manifest = {
        "product": product_data,
        "photo_url": photo_url,
        "slides": result["slides"],
        "cost_usd": result["cost"],
        "time_s": result["time_s"],
        "errors": result["errors"],
        "generated_at": datetime.now().isoformat(),
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    log(f"📋 Manifest: {manifest_path}")

    # Print JSON result to stdout (for piping)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    return result


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate marketplace product card image set",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # With existing photo
  %(prog)s --name "Nike Air Max" --price 8990 --photo https://example.com/shoe.jpg

  # AI-generated (no photo)
  %(prog)s --name "Wireless Earbuds" --price 3490 --category "Electronics"

  # Full options
  %(prog)s --name "Рюкзак" --price 4590 --old-price 6990 \\
    --category "Сумки" --features "30л,Водостойкий,Ноутбук" \\
    --badge "ХИТ" --slides max

  # JSON input
  %(prog)s --json '{"name":"Кроссовки","price":8990,"features":["Air","Mesh"]}'
        """,
    )
    parser.add_argument("--name", help="Product name")
    parser.add_argument("--price", type=int, help="Price in RUB")
    parser.add_argument("--old-price", type=int, help="Old price (for discount)")
    parser.add_argument("--category", default="Товары", help="Product category")
    parser.add_argument("--features", help="Comma-separated features")
    parser.add_argument("--dimensions", help="Dimensions string, e.g. '30x20x10 cm'")
    parser.add_argument("--brand", help="Brand name")
    parser.add_argument("--badge", help="Badge text: ХИТ, NEW, TOP")
    parser.add_argument("--photo", help="Product photo URL (omit for AI generation)")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument(
        "--slides",
        choices=["min", "standard", "max"],
        default="standard",
        help="Slide count: min(3-4), standard(5-6), max(7-8)",
    )
    parser.add_argument("--json", dest="json_input", help="Full product data as JSON string")

    args = parser.parse_args()

    # Build product_data from args
    if args.json_input:
        product_data = json.loads(args.json_input)
    elif args.name:
        product_data = {
            "name": args.name,
            "price": args.price or 0,
            "old_price": args.old_price,
            "category": args.category,
            "features": args.features.split(",") if args.features else [],
            "dimensions": args.dimensions or "",
            "brand": args.brand or "",
            "badge": args.badge,
        }
    else:
        parser.print_help()
        sys.exit(1)

    # Ensure features is a list
    if isinstance(product_data.get("features"), str):
        product_data["features"] = [f.strip() for f in product_data["features"].split(",")]

    product_card_pipeline(
        product_data=product_data,
        photo_url=args.photo,
        out_dir=args.output_dir,
        slides=args.slides,
    )


if __name__ == "__main__":
    main()
