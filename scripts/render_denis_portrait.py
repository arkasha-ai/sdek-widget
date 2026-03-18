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
Cinematic portrait of a Russian man in his early 30s, thoughtful and analytical expression.
The kind of person who reads technical documentation for fun and spots the flaw in your architecture
before you finish explaining it. Calm confident eyes, slight stubble, 
wearing a casual comfortable pullover or hoodie.
Sitting at a well-organized desk late in the evening, warm lamp light,
coffee mug nearby, notebook with handwritten diagrams half-visible.
He's not looking at the camera — looking slightly to the side, thinking deeply.
Moody dramatic side lighting, cinematic color grading, slight film grain,
85mm portrait lens shallow DOF, photorealistic, natural and honest.
NOT posed, NOT corporate — this is someone building something real.
""".strip()

print("Generating Denis portrait...")

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

out_path = os.path.expanduser("~/.openclaw/workspace/drafts/denis_portrait.jpg")
os.makedirs(os.path.dirname(out_path), exist_ok=True)

for item in output:
    url = str(item)
    urllib.request.urlretrieve(url, out_path)
    print(f"Saved: {out_path}")
    break
