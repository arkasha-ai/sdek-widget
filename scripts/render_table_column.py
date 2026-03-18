#!/usr/bin/env python3
"""
Render telescopic column via FLUX.1-dev on Replicate
"""
import os
import sys
import replicate
import urllib.request

# Load token
secrets_path = os.path.expanduser("~/.openclaw/secrets.env")
with open(secrets_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

PROMPT = """
Photorealistic studio product render of a single telescopic lifting column leg for a standing desk.
Three nested square steel tubes (outer 80x80mm, middle 60x60mm, inner 40x40mm), 
fully extended showing all three sections with chrome-polished metallic surfaces.
Central ballscrew spindle visible in cross-section cutaway view.
PTFE plastic glide pads at tube junctions. Thrust bearing at base. 
BLDC electric motor with planetary gearbox mounted at top.
Industrial steel, brushed aluminum finish, clean welds.
Professional product photography, white studio background, 
soft diffused lighting, sharp details, technical industrial aesthetic,
8k resolution, photorealistic, subsurface scattering on metal
""".strip()

print(f"Sending to FLUX.1-dev on Replicate...")
print(f"Prompt: {PROMPT[:100]}...")

output = replicate.run(
    "black-forest-labs/flux-dev",
    input={
        "prompt": PROMPT,
        "num_outputs": 1,
        "aspect_ratio": "3:4",
        "output_format": "jpg",
        "output_quality": 90,
        "num_inference_steps": 28,
        "guidance": 3.5,
    }
)

# Save output
out_path = os.path.expanduser("~/.openclaw/workspace/drafts/column_render_flux.jpg")
os.makedirs(os.path.dirname(out_path), exist_ok=True)

for item in output:
    url = str(item)
    print(f"Downloading from: {url}")
    urllib.request.urlretrieve(url, out_path)
    print(f"Saved to: {out_path}")
    break

print("Done!")
