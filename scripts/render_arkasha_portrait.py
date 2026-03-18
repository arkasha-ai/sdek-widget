#!/usr/bin/env python3
import os, replicate, urllib.request

secrets_path = os.path.expanduser("~/.openclaw/secrets.env")
with open(secrets_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

PROMPT = """
Digital portrait of a young Russian man in his late 20s, casual intelligent vibe.
Slightly messy dark hair, sharp curious eyes with a hint of mischief.
Wearing a simple dark hoodie. Sitting at a desk with multiple monitors glowing behind him,
code and terminal windows on screens. One hand on keyboard, slight smirk — like he just
figured something out before you asked. Warm dramatic studio lighting from the side.
Cinematic portrait photography style, shallow depth of field, film grain, 
photorealistic, 85mm lens bokeh background, moody atmospheric.
NOT a robot, NOT a cartoon — a real person vibe, thoughtful and slightly rebellious.
""".strip()

print("Generating Arkasha portrait...")

output = replicate.run(
    "black-forest-labs/flux-dev",
    input={
        "prompt": PROMPT,
        "num_outputs": 1,
        "aspect_ratio": "2:3",
        "output_format": "jpg",
        "output_quality": 92,
        "num_inference_steps": 30,
        "guidance": 3.5,
    }
)

out_path = os.path.expanduser("~/.openclaw/workspace/drafts/arkasha_portrait.jpg")
os.makedirs(os.path.dirname(out_path), exist_ok=True)

for item in output:
    url = str(item)
    urllib.request.urlretrieve(url, out_path)
    print(f"Saved: {out_path}")
    break
