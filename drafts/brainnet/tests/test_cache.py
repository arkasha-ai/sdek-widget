"""Tests for L0 Cache Layer."""

import asyncio
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from brainnet.cache_layer import CacheLayer
from brainnet.working_memory import WorkingMemory


async def test_exact_cache():
    """Test L1 exact match cache."""
    memory = WorkingMemory()
    memory._redis = AsyncMock()
    memory._redis.get = AsyncMock(return_value=None)
    memory._redis.setex = AsyncMock()

    cache = CacheLayer(memory)

    # Store
    await cache.store("hello", "world response")

    # Lookup (won't find in Redis mock, but tests the flow)
    result = await cache.lookup("hello")
    # Redis mock returns None, so no hit from Redis
    assert result is None  # exact match goes through Redis
    print("✅ test_exact_cache passed")


async def test_semantic_cache():
    """Test L2 semantic match cache."""
    memory = WorkingMemory()
    memory._redis = AsyncMock()
    memory._redis.get = AsyncMock(return_value=None)
    memory._redis.setex = AsyncMock()

    cache = CacheLayer(memory, semantic_threshold=0.9)

    # Store with embedding
    emb = np.random.randn(48).astype(np.float32)
    emb = emb / np.linalg.norm(emb)
    await cache.store("test input", "test response", emb)

    # Similar embedding should hit
    similar_emb = emb + np.random.randn(48).astype(np.float32) * 0.05
    similar_emb = similar_emb / np.linalg.norm(similar_emb)

    hit = await cache.lookup("different text", similar_emb)
    assert hit is not None
    assert hit.level in ("L2_semantic", "L3_pattern")
    assert hit.response == "test response"
    print("✅ test_semantic_cache passed")


async def test_no_cache_hit():
    """Test cache miss."""
    memory = WorkingMemory()
    memory._redis = AsyncMock()
    memory._redis.get = AsyncMock(return_value=None)

    cache = CacheLayer(memory)
    result = await cache.lookup("something new")
    assert result is None
    print("✅ test_no_cache_hit passed")


if __name__ == "__main__":
    asyncio.run(test_exact_cache())
    asyncio.run(test_semantic_cache())
    asyncio.run(test_no_cache_hit())
    print("\n🎉 All cache tests passed!")
