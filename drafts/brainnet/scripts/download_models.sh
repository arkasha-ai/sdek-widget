#!/bin/bash
# Download required models from HuggingFace
set -e

echo "📥 Downloading BrainNet models..."

# L1/L3: Qwen2.5-0.5B-Instruct
echo "Downloading Qwen2.5-0.5B-Instruct (L1/L3)..."
python3 -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
print('Downloading Qwen/Qwen2.5-0.5B-Instruct...')
tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen2.5-0.5B-Instruct', trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-0.5B-Instruct', trust_remote_code=True)
print('✅ Qwen2.5-0.5B-Instruct downloaded')
"

# L2: Qwen2.5-1.5B-Instruct
echo "Downloading Qwen2.5-1.5B-Instruct (L2 Collegium)..."
python3 -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
print('Downloading Qwen/Qwen2.5-1.5B-Instruct...')
tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct', trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct', trust_remote_code=True)
print('✅ Qwen2.5-1.5B-Instruct downloaded')
"

echo ""
echo "🎉 All models downloaded!"
echo "Total VRAM needed: ~4GB (0.5B in fp16 × 2 instances + 1.5B in fp16)"
