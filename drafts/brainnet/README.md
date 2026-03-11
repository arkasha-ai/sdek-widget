# BrainNet v0.1.0

Brain-inspired multi-agent AI system with hierarchical processing levels.

## Architecture

```
User Input → [L0 Cache] → [L1 FastDetector] → [L2 Collegium] → [Aggregator]
                                                                     ↓
User Output ← [MotorNode] ← [L3 FinalNode] ← [CriticalThinking] ← [ConflictMonitor]
```

### Processing Levels

| Level | Component | Model | Purpose |
|-------|-----------|-------|---------|
| L0 | CacheLayer | - | 3-tier cache (exact, semantic, pattern) |
| L1 | FastDetector | Qwen2.5-0.5B | Intent detection (~50ms) |
| L2 | Collegium | 3× Qwen2.5-1.5B | Parallel analysis (analytical, creative, critical) |
| L3 | FinalNode | Qwen2.5-0.5B | Response formulation |

### Brain-inspired Components

- **ImportanceScorer**: RPE-guided learning (dopaminergic neurons)
- **ConflictMonitor**: ACC — ERN fast flags + PFC slow resolution
- **CriticalThinking**: DLPFC consistency + IFC devil's advocate
- **GossipProtocol**: Inter-node state sharing
- **VectorProtocol**: Compact embeddings instead of text

## Requirements

- Python 3.10+
- NVIDIA GPU with 8+ GB VRAM (tested on RTX 4090)
- Redis server
- ~6GB disk for models

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (via Docker)
docker run -d --name brainnet-redis -p 6379:6379 redis:alpine

# Download models
bash scripts/download_models.sh

# Check GPU
python scripts/check_gpu.py

# Run
python main.py
```

## Usage

```bash
python main.py
# > BrainNet запущен
# > You: Привет!
# > [L0 miss] [L1: intent=greeting] [L2: 3 forwards] [L3: response]
# > BrainNet: Привет! Чем могу помочь?
# > You: stats
# > 📊 Pipeline Stats: ...
# > You: quit
```

## Testing

```bash
# Unit tests
python -m tests.test_messages
python -m tests.test_cache
python -m tests.test_gossip

# Integration test (requires GPU + Redis)
python -m tests.test_pipeline
```

## VRAM Usage

| Component | VRAM |
|-----------|------|
| Qwen2.5-0.5B (L1+L3 shared) | ~1 GB |
| Qwen2.5-1.5B (L2) | ~3 GB |
| Projection heads + scorers | ~0.1 GB |
| **Total** | **~4 GB** |
