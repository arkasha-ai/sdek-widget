"""L0 Cache Layer — Three-level cache before hitting neural nodes.

L1: Exact match (hash of normalized input)
L2: Semantic match (cosine similarity of embeddings)
L3: Pattern match (intent classification)
"""

import hashlib
import json
import time
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

from .working_memory import WorkingMemory


@dataclass
class CacheHit:
    level: str  # "L1_exact", "L2_semantic", "L3_pattern"
    response: str
    similarity: float
    cached_at: float


class CacheLayer:
    """Three-level response cache to avoid redundant computation."""

    def __init__(self, memory: WorkingMemory, semantic_threshold: float = 0.92, pattern_threshold: float = 0.85):
        self.memory = memory
        self.semantic_threshold = semantic_threshold
        self.pattern_threshold = pattern_threshold
        self._semantic_cache = {}  # embedding_key → (embedding, response, timestamp)

    def _normalize(self, text: str) -> str:
        """Normalize text for exact matching."""
        return text.strip().lower()

    def _hash(self, text: str) -> str:
        """Hash normalized text."""
        return hashlib.sha256(self._normalize(text).encode()).hexdigest()[:16]

    async def lookup(self, text: str, embedding: np.ndarray = None) -> Optional[CacheHit]:
        """Try all three cache levels. Returns CacheHit or None."""

        # L1: Exact match
        text_hash = self._hash(text)
        cached = await self.memory.get_cache("exact", text_hash)
        if cached:
            data = json.loads(cached)
            return CacheHit(
                level="L1_exact",
                response=data["response"],
                similarity=1.0,
                cached_at=data["cached_at"],
            )

        if embedding is not None:
            # L2: Semantic match
            for key, (ref_emb, response, ts) in self._semantic_cache.items():
                sim = self._cosine_sim(embedding, ref_emb)
                if sim >= self.semantic_threshold:
                    return CacheHit(
                        level="L2_semantic",
                        response=response,
                        similarity=sim,
                        cached_at=ts,
                    )

            # L3: Pattern match (lower threshold)
            for key, (ref_emb, response, ts) in self._semantic_cache.items():
                sim = self._cosine_sim(embedding, ref_emb)
                if sim >= self.pattern_threshold:
                    return CacheHit(
                        level="L3_pattern",
                        response=response,
                        similarity=sim,
                        cached_at=ts,
                    )

        return None

    async def store(self, text: str, response: str, embedding: np.ndarray = None):
        """Store a response in cache at all applicable levels."""
        now = time.time()

        # L1: Exact match
        text_hash = self._hash(text)
        await self.memory.store_cache("exact", text_hash, json.dumps({
            "response": response,
            "cached_at": now,
        }))

        # L2/L3: Semantic cache (in-memory for speed)
        if embedding is not None:
            cache_key = f"{text_hash}_{now}"
            self._semantic_cache[cache_key] = (embedding.copy(), response, now)

            # Evict old entries (keep last 100)
            if len(self._semantic_cache) > 100:
                sorted_keys = sorted(self._semantic_cache.keys(), key=lambda k: self._semantic_cache[k][2])
                for k in sorted_keys[:len(self._semantic_cache) - 100]:
                    del self._semantic_cache[k]

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a) + 1e-8
        norm_b = np.linalg.norm(b) + 1e-8
        return float(np.dot(a, b) / (norm_a * norm_b))
