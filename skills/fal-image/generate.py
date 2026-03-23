#!/usr/bin/env python3
"""
fal.ai Image Generation Script
Usage: python3 generate.py --model <model> --prompt "..." [--image path] [--mask path] [--output path] [--aspect-ratio 4:5]
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Model endpoint mapping
MODELS = {
    "nano-banana-2":   "fal-ai/nano-banana-2",
    "nano-banana-pro": "fal-ai/nano-banana-pro",
    "flux-kontext":    "fal-ai/flux-pro/kontext",
    "flux-fill":       "fal-ai/flux-pro/v1/fill",
    "flux-schnell":    "fal-ai/flux/schnell",
    "flux-dev":        "fal-ai/flux/dev",
}

def load_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    ext = Path(path).suffix.lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"

def fal_request(endpoint: str, payload: dict, token: str) -> dict:
    url = f"https://fal.run/{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Key {token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())

def fal_queue(endpoint: str, payload: dict, token: str, poll_interval: int = 3, timeout: int = 120) -> dict:
    """Submit to async queue and poll for result"""
    submit_url = f"https://queue.fal.run/{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        submit_url, data=data,
        headers={"Authorization": f"Key {token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        submitted = json.loads(r.read())

    request_id = submitted.get("request_id")
    if not request_id:
        raise RuntimeError(f"No request_id in response: {submitted}")

    print(f"  Queued: {request_id}", file=sys.stderr)

    # Poll for status
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(poll_interval)
        status_url = f"https://queue.fal.run/{endpoint}/requests/{request_id}/status"
        req2 = urllib.request.Request(status_url, headers={"Authorization": f"Key {token}"})
        with urllib.request.urlopen(req2, timeout=15) as r:
            status = json.loads(r.read())

        state = status.get("status", "")
        print(f"  [{int(time.time()-start)}s] {state}", file=sys.stderr)

        if state == "COMPLETED":
            result_url = f"https://queue.fal.run/{endpoint}/requests/{request_id}"
            req3 = urllib.request.Request(result_url, headers={"Authorization": f"Key {token}"})
            with urllib.request.urlopen(req3, timeout=15) as r:
                return json.loads(r.read())
        elif state in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Job {state}: {status}")

    raise TimeoutError(f"Timeout after {timeout}s")

def extract_image_url(result: dict) -> str:
    # Try common response structures
    if "images" in result:
        imgs = result["images"]
        if imgs and isinstance(imgs[0], dict):
            return imgs[0].get("url", "")
        elif imgs and isinstance(imgs[0], str):
            return imgs[0]
    if "image" in result:
        img = result["image"]
        if isinstance(img, dict):
            return img.get("url", "")
        return img
    if "output" in result:
        out = result["output"]
        if isinstance(out, list):
            return out[0]
        return out
    raise ValueError(f"Cannot find image URL in result: {list(result.keys())}")

def download_image(url: str, output_path: str):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(output_path, "wb") as f:
        f.write(data)

def main():
    parser = argparse.ArgumentParser(description="fal.ai image generation")
    parser.add_argument("--model", "-m", default="flux-schnell", help="Model alias or full endpoint")
    parser.add_argument("--prompt", "-p", required=True, help="Generation prompt")
    parser.add_argument("--image", "-i", help="Input image path (for img2img/inpainting)")
    parser.add_argument("--mask", help="Mask image path (for inpainting)")
    parser.add_argument("--output", "-o", default="/tmp/fal_output.jpg", help="Output file path")
    parser.add_argument("--aspect-ratio", "-r", default="1:1", help="Aspect ratio (e.g. 4:5)")
    parser.add_argument("--negative", help="Negative prompt")
    parser.add_argument("--sync", action="store_true", help="Use sync API instead of queue")
    args = parser.parse_args()

    # Load token
    secrets_path = Path.home() / ".openclaw/secrets.env"
    token = None
    if secrets_path.exists():
        for line in secrets_path.read_text().splitlines():
            if line.startswith("FAL_API_KEY="):
                token = line.split("=", 1)[1].strip()
    if not token:
        token = os.environ.get("FAL_API_KEY")
    if not token:
        print("ERROR: FAL_API_KEY not found in secrets.env or environment", file=sys.stderr)
        sys.exit(1)

    # Resolve endpoint
    endpoint = MODELS.get(args.model, args.model)
    print(f"Model: {endpoint}", file=sys.stderr)

    # Build payload
    payload = {
        "prompt": args.prompt,
        "aspect_ratio": args.aspect_ratio,
        "output_format": "jpeg",
        "safety_tolerance": "5",
    }

    if args.image:
        payload["image_url"] = load_image_b64(args.image)

    if args.mask:
        payload["mask_url"] = load_image_b64(args.mask)

    if args.negative:
        payload["negative_prompt"] = args.negative

    # schnell and fast models → sync; others → queue
    fast_models = {"fal-ai/flux/schnell", "fal-ai/flux/dev"}
    use_sync = args.sync or endpoint in fast_models

    # Generate
    print(f"Generating with {endpoint} ({'sync' if use_sync else 'queue'})...", file=sys.stderr)
    try:
        if use_sync:
            result = fal_request(endpoint, payload, token)
        else:
            result = fal_queue(endpoint, payload, token)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)

    # Extract and save
    img_url = extract_image_url(result)
    print(f"Downloading: {img_url[:80]}...", file=sys.stderr)
    download_image(img_url, args.output)
    print(f"Saved: {args.output}", file=sys.stderr)
    print(args.output)  # stdout = output path for piping

if __name__ == "__main__":
    main()
