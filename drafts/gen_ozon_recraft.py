import requests, time, re, os, io
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def read_token():
    with open(os.path.expanduser("~/.openclaw/secrets.env")) as f:
        for line in f:
            m = re.match(r'(?:export\s+)?REPLICATE_API_TOKEN[=\s]+"?([^"\n]+)"?', line.strip())
            if m:
                return m.group(1).strip()
    raise Exception("REPLICATE_API_TOKEN not found")

def generate_recraft(prompt, token, retries=5):
    print(f"  Generating: {prompt[:60]}...")
    for attempt in range(retries):
        r = requests.post(
            "https://api.replicate.com/v1/models/recraft-ai/recraft-v3/predictions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Prefer": "wait"},
            json={"input": {"prompt": prompt, "width": 1000, "height": 1000, "style": "digital_illustration"}},
            timeout=120
        )
        data = r.json()
        status = data.get("status")
        print(f"  HTTP {r.status_code}, status: {status}, id: {data.get('id')}")
        
        if r.status_code == 429 or status == "429":
            wait = 30 * (attempt + 1)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        
        if status == "succeeded":
            return data["output"]
        
        pred_id = data.get("id")
        if not pred_id:
            print(f"  No id in response: {data}")
            time.sleep(15)
            continue
        
        # polling fallback
        for i in range(30):
            time.sleep(4)
            r2 = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}",
                             headers={"Authorization": f"Bearer {token}"})
            d = r2.json()
            print(f"  Poll {i+1}: {d['status']}")
            if d["status"] == "succeeded":
                return d["output"]
            elif d["status"] == "failed":
                raise Exception(str(d))
        raise Exception("Timeout waiting for prediction")
    raise Exception(f"Failed after {retries} retries (rate limit)")

def remove_white_bg(toy_path):
    img = Image.open(toy_path).convert("RGBA")
    data = np.array(img)
    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
    white_mask = (r > 240) & (g > 240) & (b > 240) & \
                 (r.astype(int) - b.astype(int) < 15) & \
                 (r.astype(int) - g.astype(int) < 15)
    data[:,:,3] = np.where(white_mask, 0, 255)
    return Image.fromarray(data)

def download_image(url):
    r = requests.get(url, timeout=60)
    return Image.open(io.BytesIO(r.content)).convert("RGBA")

def make_card(bg_img, toy_rgba, banner_color, title_text, out_path):
    # Resize bg to 1000x1000
    card = bg_img.resize((1000, 1000), Image.LANCZOS).convert("RGBA")
    
    # Resize toy: height 600px, keep aspect
    tw, th = toy_rgba.size
    new_h = 600
    new_w = int(tw * new_h / th)
    toy_resized = toy_rgba.resize((new_w, new_h), Image.LANCZOS)
    
    # Position: centered horizontally, y=390 (bottom at 990)
    x = (1000 - new_w) // 2
    y = 390
    card.paste(toy_resized, (x, y), toy_resized)
    
    # Top banner 160px
    banner = Image.new("RGBA", (1000, 160), banner_color)
    card.paste(banner, (0, 0), banner)
    
    # Bottom dark rect 100px
    bottom_rect = Image.new("RGBA", (1000, 100), (0, 0, 0, 180))
    card.paste(bottom_rect, (0, 900), bottom_rect)
    
    # Draw text
    draw = ImageDraw.Draw(card)
    
    # Title on banner
    font_bold_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    font_reg_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    
    font_title = ImageFont.truetype(font_bold_path, 64)
    font_sub = ImageFont.truetype(font_reg_path, 26)
    
    # Center title in banner
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    tw_text = bbox[2] - bbox[0]
    th_text = bbox[3] - bbox[1]
    tx = (1000 - tw_text) // 2 - bbox[0]
    ty = (160 - th_text) // 2 - bbox[1]
    draw.text((tx, ty), title_text, font=font_title, fill=(255, 255, 255, 255))
    
    # Bottom subtitle
    sub_text = "10 сказок • 26 песенок • 6 мелодий для сна"
    bbox2 = draw.textbbox((0, 0), sub_text, font=font_sub)
    sw = bbox2[2] - bbox2[0]
    sh = bbox2[3] - bbox2[1]
    sx = (1000 - sw) // 2 - bbox2[0]
    sy = 900 + (100 - sh) // 2 - bbox2[1]
    draw.text((sx, sy), sub_text, font=font_sub, fill=(255, 255, 255, 255))
    
    # Save
    card.convert("RGB").save(out_path, "PNG")
    print(f"  Saved: {out_path}")

def main():
    token = read_token()
    print(f"Token loaded: {token[:8]}...")
    
    toy_path = "/home/clawdbot/.openclaw/workspace/drafts/toy_nobg.jpg"
    toy_rgba = remove_white_bg(toy_path)
    print(f"Toy loaded: {toy_rgba.size}")
    
    prompts = [
        "enchanted fairy tale forest for children, glowing magical book pages, stars and castles in background, soft pastel purple and pink colors, dreamy and magical atmosphere, no text, no people, product card background",
        "colorful cartoon music world for children, floating musical notes and stars, rainbow colors, joyful festive atmosphere, confetti and sparkles, no text, no people, product card background",
        "cozy dreamy night sky for children, crescent moon and twinkling stars, soft clouds, lavender and deep blue gradient, peaceful bedtime atmosphere, no text, no people, product card background",
        "bright sunny meadow with rainbow for children, butterflies and flowers, cheerful summer day, pastel yellow and green, playful cartoon style, no text, no people, product card background",
    ]
    
    banners = [
        (138, 43, 226, 200),   # purple
        (255, 140, 0, 200),    # orange
        (25, 25, 112, 200),    # dark blue
        (34, 139, 34, 200),    # green
    ]
    
    titles = [
        "10 СКАЗОК",
        "26 ПЕСЕНОК",
        "6 МЕЛОДИЙ ДЛЯ СНА",
        "МУЗЫКАЛЬНАЯ ИГРУШКА-ЗАЙЧИК",
    ]
    
    out_dir = "/home/clawdbot/.openclaw/workspace/drafts"
    
    for i, (prompt, banner, title) in enumerate(zip(prompts, banners, titles), 1):
        out_path = f"{out_dir}/ozon_recraft_{i}.png"
        if os.path.exists(out_path):
            print(f"\n=== Card {i}: {title} — SKIP (already exists) ===")
            continue
        print(f"\n=== Card {i}: {title} ===")
        if i > 1:
            print("  Waiting 20s before next request...")
            time.sleep(20)
        try:
            output = generate_recraft(prompt, token)
            bg_url = output if isinstance(output, str) else output[0]
            print(f"  BG URL: {bg_url[:60]}...")
            bg_img = download_image(bg_url)
            make_card(bg_img, toy_rgba, banner, title, out_path)
        except Exception as e:
            print(f"  ERROR card {i}: {e}")
    
    print("\nDone!")

if __name__ == "__main__":
    main()
