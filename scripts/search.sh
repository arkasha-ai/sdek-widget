#!/bin/bash
# Быстрый поиск по Qdrant
source ~/.openclaw/litellm.env
source ~/.openclaw/secrets.env
export LITELLM_BASE_URL LITELLM_API_KEY QDRANT_URL QDRANT_API_KEY QDRANT_COLLECTION EMBEDDING_MODEL
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py search "$@"
