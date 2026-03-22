#!/usr/bin/env python3
"""
Multi-model image generator via Replicate API.
Uses curl subprocess to avoid Python SSL/proxy issues on this host.

Commands:
  generate "prompt" [options]  — generate an image
  list [--category CAT]       — list available models
  search "query"              — search models by description
  info "model-id"             — detailed model info
  recommend "task"            — recommend best model for task
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MODELS_FILE = SCRIPT_DIR.parent / "models.json"
REPLICATE_API = "https://api.replicate.com/v1"
DEFAULT_OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "drafts"


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
        log("❌ REPLICATE_API_TOKEN not found in env or ~/.openclaw/secrets.env")
        sys.exit(1)
    return token


def load_models():
    if not MODELS_FILE.exists():
        log(f"❌ Models file not found: {MODELS_FILE}")
        sys.exit(1)
    return json.loads(MODELS_FILE.read_text())


def curl_json(method, url, data=None, token=None, timeout=30):
    """Run curl and return parsed JSON."""
    cmd = ["curl", "-s", "-X", method, url,
           "-H", f"Authorization: Bearer {token}",
           "-H", "Content-Type: application/json"]
    if data:
        cmd += ["-d", json.dumps(data)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        log(f"❌ curl error: {result.stderr}")
        sys.exit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        log(f"❌ Invalid JSON: {result.stdout[:300]}")
        sys.exit(1)


def curl_download(url, out_path, token=None, timeout=60):
    """Download file via curl."""
    cmd = ["curl", "-s", "-L", "-o", str(out_path), url]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        log(f"❌ Download failed: {result.stderr.decode()}")
        sys.exit(1)


def upload_image(path_or_url, token):
    """If local path, upload to Replicate Files API. Return URL."""
    p = Path(path_or_url)
    if p.exists():
        log(f"📤 Uploading: {p.name}...")
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"{REPLICATE_API}/files",
             "-H", f"Authorization: Bearer {token}",
             "-F", f"content=@{p}"],
            capture_output=True, text=True, timeout=60
        )
        d = json.loads(result.stdout)
        url = d.get("urls", {}).get("get") or d.get("url")
        if not url:
            log(f"❌ Upload failed: {result.stdout[:200]}")
            sys.exit(1)
        log(f"✅ Uploaded: {url}")
        return url
    return path_or_url


def poll_prediction(pred_id, token, max_wait=120):
    """Poll until prediction completes."""
    start = time.time()
    dots = 0
    while time.time() - start < max_wait:
        d = curl_json("GET", f"{REPLICATE_API}/predictions/{pred_id}", token=token)
        status = d.get("status")
        if status == "succeeded":
            elapsed = time.time() - start
            log(f"\r✅ Done in {elapsed:.1f}s          ")
            return d.get("output")
        elif status in ("failed", "canceled"):
            log(f"\n❌ Prediction {status}: {d.get('error')}")
            sys.exit(1)
        dots = (dots + 1) % 4
        log_line = f"\r⏳ Generating{'.' * (dots + 1)}{'  ' * (3 - dots)}"
        print(log_line, end="", flush=True, file=sys.stderr)
        time.sleep(1.5)
    log(f"\n❌ Timed out after {max_wait}s")
    sys.exit(1)


def auto_select_model(prompt, db):
    """Pick the best model based on prompt keywords."""
    prompt_lower = prompt.lower()
    for rule in db.get("auto_select_rules", []):
        for kw in rule["keywords"]:
            if kw in prompt_lower:
                model_key = rule["model"]
                if model_key in db["models"]:
                    return model_key
    return db.get("default_model", "flux-schnell")


def build_input(model_cfg, args):
    """Build the API input payload from model config and CLI args."""
    mapping = model_cfg.get("param_mapping", {})
    defaults = dict(model_cfg.get("default_params", {}))
    inp = dict(defaults)

    # Prompt (always required)
    prompt_key = mapping.get("prompt", "prompt")
    inp[prompt_key] = args.prompt

    # Negative prompt
    if args.negative and mapping.get("negative"):
        inp[mapping["negative"]] = args.negative

    # Aspect ratio — handle dimension-based models
    if args.aspect_ratio:
        if model_cfg.get("uses_dimensions"):
            dims_map = model_cfg.get("aspect_ratio_to_dims", {})
            if args.aspect_ratio in dims_map:
                w, h = dims_map[args.aspect_ratio]
                inp["width"] = w
                inp["height"] = h
            else:
                log(f"⚠️  Aspect ratio {args.aspect_ratio} not supported, using default dimensions")
        elif mapping.get("aspect_ratio"):
            inp[mapping["aspect_ratio"]] = args.aspect_ratio

    # Steps
    if args.steps is not None and mapping.get("steps"):
        inp[mapping["steps"]] = args.steps

    # Guidance
    if args.guidance is not None and mapping.get("guidance"):
        inp[mapping["guidance"]] = args.guidance

    # Seed
    if args.seed is not None and mapping.get("seed"):
        inp[mapping["seed"]] = args.seed

    # Output format
    if args.format and mapping.get("format"):
        inp[mapping["format"]] = args.format

    # Output quality
    if args.quality is not None and mapping.get("quality"):
        inp[mapping["quality"]] = args.quality

    # Safety
    if args.no_safety and mapping.get("safety"):
        safety_key = mapping["safety"]
        if safety_key is not None:
            safety_vals = model_cfg.get("safety_values")
            if safety_vals:
                inp[safety_key] = safety_vals["off"]
            elif isinstance(inp.get(safety_key), bool) or safety_key == "disable_safety_checker":
                inp[safety_key] = True

    # Image input (img2img)
    if args.image and mapping.get("image"):
        image_key = mapping["image"]
        # nano-banana-pro expects array
        if image_key == "image_input":
            inp[image_key] = [args.image]
        else:
            inp[image_key] = args.image

        if args.strength is not None and mapping.get("strength"):
            inp[mapping["strength"]] = args.strength

    return inp


def resolve_output_format(args, model_cfg):
    """Determine actual output format considering model limitations."""
    fmt = args.format or "webp"
    # Some models don't support webp (e.g., nano-banana-pro)
    notes = model_cfg.get("notes", "")
    if "no webp" in notes.lower() and fmt == "webp":
        fmt = "jpg"
        log(f"⚠️  Model doesn't support webp, using {fmt}")
    return fmt


def cmd_generate(args):
    """Generate an image."""
    token = load_token()
    db = load_models()

    # Resolve model
    model_key = args.model
    if model_key == "auto":
        model_key = auto_select_model(args.prompt, db)
        log(f"🤖 Auto-selected model: {model_key}")

    if model_key not in db["models"]:
        log(f"❌ Unknown model: {model_key}")
        log(f"   Available: {', '.join(sorted(db['models'].keys()))}")
        sys.exit(1)

    model_cfg = db["models"][model_key]

    # Check img2img support
    if args.image and not model_cfg.get("supports_img2img"):
        log(f"⚠️  Model {model_key} doesn't support img2img, ignoring --image")
        args.image = None

    # Upload local image if needed
    if args.image:
        args.image = upload_image(args.image, token)

    # Resolve output format
    actual_format = resolve_output_format(args, model_cfg)
    args.format = actual_format

    # Build input
    inp = build_input(model_cfg, args)

    # Build output path
    if args.output:
        out_path = Path(args.output)
    else:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in args.prompt[:30]).strip()
        out_path = DEFAULT_OUTPUT_DIR / f"{model_key}_{ts}_{safe}.{actual_format}"

    # Create prediction
    model_id = model_cfg["id"]
    version = model_cfg.get("version")

    log(f"🎨 Model: {model_cfg['name']} ({model_id})")
    log(f"📝 Prompt: {args.prompt[:80]}{'...' if len(args.prompt) > 80 else ''}")
    log(f"💰 Est. cost: ${model_cfg['cost_usd']}")

    if version:
        payload = {"version": version, "input": inp}
    else:
        payload = {"model": model_id, "input": inp}

    d = curl_json("POST", f"{REPLICATE_API}/predictions", data=payload, token=token)

    pred_id = d.get("id")
    if not pred_id:
        error = d.get("detail") or d.get("error") or json.dumps(d)[:300]
        log(f"❌ Failed to create prediction: {error}")
        sys.exit(1)

    log(f"🆔 Prediction: {pred_id}")

    # Poll
    output = poll_prediction(pred_id, token, max_wait=args.wait)

    if not output:
        log("❌ No output returned")
        sys.exit(1)

    # Extract image URL — output can be string, list of strings, or other
    if isinstance(output, list):
        image_url = output[0] if output else None
    elif isinstance(output, str):
        image_url = output
    else:
        log(f"❌ Unexpected output format: {type(output)}")
        sys.exit(1)

    if not image_url:
        log("❌ No image URL in output")
        sys.exit(1)

    # Download
    log(f"💾 Downloading to: {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    curl_download(image_url, out_path, token=token)

    # Stdout = file path (for piping)
    print(str(out_path))
    log(f"✅ Saved: {out_path}")
    log(f"🔗 URL: {image_url}")


def cmd_list(args):
    """List available models."""
    db = load_models()
    models = db["models"]

    if args.category:
        cat = args.category.lower()
        models = {k: v for k, v in models.items() if cat in [c.lower() for c in v.get("categories", [])]}

    if not models:
        log(f"No models found for category: {args.category}")
        sys.exit(0)

    # Table header
    print(f"{'ID':<22} {'Name':<28} {'Cost':>6} {'Speed':>6} {'Categories':<25} {'img2img'}")
    print("-" * 100)

    for key, m in sorted(models.items(), key=lambda x: x[1]["cost_usd"]):
        cats = ", ".join(m.get("categories", []))
        img2img = "✓" if m.get("supports_img2img") else ""
        print(f"{key:<22} {m['name']:<28} ${m['cost_usd']:<5.3f} {m['speed_s']:>4}s  {cats:<25} {img2img}")


def cmd_search(args):
    """Search models by query matching name, description, pros."""
    db = load_models()
    query = args.query.lower()
    results = []

    for key, m in db["models"].items():
        searchable = " ".join([
            m.get("name", ""), m.get("description", ""),
            " ".join(m.get("pros", [])), " ".join(m.get("categories", []))
        ]).lower()
        if query in searchable:
            results.append((key, m))

    if not results:
        print(f"No models found matching: {args.query}")
        return

    print(f"Found {len(results)} model(s) matching '{args.query}':\n")
    for key, m in results:
        print(f"  {key:<22} {m['name']:<28} ${m['cost_usd']:.3f}  {m.get('description', '')}")


def cmd_info(args):
    """Show detailed info about a model."""
    db = load_models()
    key = args.model_id

    if key not in db["models"]:
        print(f"Unknown model: {key}")
        print(f"Available: {', '.join(sorted(db['models'].keys()))}")
        sys.exit(1)

    m = db["models"][key]
    print(f"Model: {m['name']}")
    print(f"ID: {m['id']}")
    print(f"Cost: ${m['cost_usd']:.3f} per image")
    print(f"Speed: ~{m['speed_s']}s")
    print(f"Categories: {', '.join(m.get('categories', []))}")
    print(f"img2img: {'Yes' if m.get('supports_img2img') else 'No'}")
    print(f"LoRA: {'Yes' if m.get('supports_lora') else 'No'}")
    print()
    print("Pros:")
    for p in m.get("pros", []):
        print(f"  + {p}")
    print("Cons:")
    for c in m.get("cons", []):
        print(f"  - {c}")
    if m.get("aspect_ratios"):
        print(f"\nAspect ratios: {', '.join(m['aspect_ratios'])}")
    if m.get("notes"):
        print(f"\nNotes: {m['notes']}")
    if m.get("description"):
        print(f"\n{m['description']}")


def cmd_recommend(args):
    """Recommend a model for a task."""
    db = load_models()
    task = args.task.lower()

    # Use auto_select_rules first
    model_key = auto_select_model(task, db)
    m = db["models"][model_key]

    print(f"🎯 Recommended: {model_key}")
    print(f"   {m['name']} — ${m['cost_usd']:.3f}, ~{m['speed_s']}s")
    print(f"   {m.get('description', '')}")
    print()

    # Also suggest alternatives
    # Find all matching rules
    matched = set()
    for rule in db.get("auto_select_rules", []):
        for kw in rule["keywords"]:
            if kw in task:
                matched.add(rule["model"])

    # Add models from same categories
    primary_cats = set(m.get("categories", []))
    for k, other in db["models"].items():
        if k != model_key:
            other_cats = set(other.get("categories", []))
            if primary_cats & other_cats:
                matched.add(k)

    matched.discard(model_key)
    if matched:
        print("Alternatives:")
        for alt_key in sorted(matched):
            if alt_key in db["models"]:
                alt = db["models"][alt_key]
                print(f"  • {alt_key:<22} {alt['name']:<28} ${alt['cost_usd']:.3f}  ~{alt['speed_s']}s")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-model image generator via Replicate API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  generate "prompt"     Generate an image
  list                  List available models
  search "query"        Search models
  info "model-id"       Model details
  recommend "task"      Get model recommendation
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # generate
    gen_p = subparsers.add_parser("generate", help="Generate an image")
    gen_p.add_argument("prompt", help="Image generation prompt")
    gen_p.add_argument("--model", "-m", default="auto", help="Model ID from database or 'auto' (default: auto)")
    gen_p.add_argument("--negative", default=None, help="Negative prompt")
    gen_p.add_argument("--aspect-ratio", "-r", default="1:1", help="Aspect ratio (default: 1:1)")
    gen_p.add_argument("--steps", "-s", type=int, default=None, help="Inference steps")
    gen_p.add_argument("--guidance", "-g", type=float, default=None, help="Guidance scale")
    gen_p.add_argument("--output", "-o", default=None, help="Output file path")
    gen_p.add_argument("--format", default=None, help="Output format: webp/png/jpg")
    gen_p.add_argument("--quality", type=int, default=None, help="Output quality 0-100")
    gen_p.add_argument("--image", default=None, help="Input image for img2img (URL or local path)")
    gen_p.add_argument("--strength", type=float, default=None, help="img2img strength 0-1")
    gen_p.add_argument("--seed", type=int, default=None, help="Fixed seed for reproducibility")
    gen_p.add_argument("--no-safety", action="store_true", help="Disable safety checker")
    gen_p.add_argument("--wait", type=int, default=180, help="Max wait seconds (default: 180)")

    # list
    list_p = subparsers.add_parser("list", help="List available models")
    list_p.add_argument("--category", "-c", default=None,
                        help="Filter by category: fast, photo, anime, text, edit, universal")

    # search
    search_p = subparsers.add_parser("search", help="Search models")
    search_p.add_argument("query", help="Search query")

    # info
    info_p = subparsers.add_parser("info", help="Model details")
    info_p.add_argument("model_id", help="Model ID from database")

    # recommend
    rec_p = subparsers.add_parser("recommend", help="Recommend model for task")
    rec_p.add_argument("task", help="Task description")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "recommend":
        cmd_recommend(args)


if __name__ == "__main__":
    main()
