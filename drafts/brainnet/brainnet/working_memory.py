"""Redis-backed working memory for BrainNet."""

import json
import time
import asyncio
from typing import Optional, List
import redis.asyncio as aioredis
import numpy as np

from .messages import BrainNetMessage


class WorkingMemory:
    """Short-term memory backed by Redis. Stores recent messages, embeddings, and node states."""

    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "brainnet"):
        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: Optional[aioredis.Redis] = None
        self.ttl = 300  # 5 min default TTL

    async def connect(self):
        self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        await self._redis.ping()

    async def close(self):
        if self._redis:
            await self._redis.aclose()

    def _key(self, *parts) -> str:
        return f"{self.prefix}:" + ":".join(parts)

    async def store_message(self, msg: BrainNetMessage):
        """Store a message in working memory with TTL."""
        key = self._key("msg", msg.task_id, msg.source_node)
        await self._redis.setex(key, self.ttl, json.dumps(msg.to_dict()))

        # Also add to task's message list
        list_key = self._key("task", msg.task_id)
        await self._redis.rpush(list_key, json.dumps(msg.to_dict()))
        await self._redis.expire(list_key, self.ttl)

    async def get_task_messages(self, task_id: str) -> List[BrainNetMessage]:
        """Get all messages for a task."""
        list_key = self._key("task", task_id)
        items = await self._redis.lrange(list_key, 0, -1)
        return [BrainNetMessage.from_dict(json.loads(item)) for item in items]

    async def store_embedding(self, key: str, embedding: np.ndarray):
        """Store an embedding vector."""
        emb_key = self._key("emb", key)
        await self._redis.setex(emb_key, self.ttl, json.dumps(embedding.tolist()))

    async def get_embedding(self, key: str) -> Optional[np.ndarray]:
        """Retrieve an embedding vector."""
        emb_key = self._key("emb", key)
        data = await self._redis.get(emb_key)
        if data:
            return np.array(json.loads(data), dtype=np.float32)
        return None

    async def store_node_state(self, node_name: str, state: dict):
        """Store a node's current state."""
        key = self._key("node", node_name)
        await self._redis.setex(key, self.ttl * 2, json.dumps(state))

    async def get_node_state(self, node_name: str) -> Optional[dict]:
        """Get a node's current state."""
        key = self._key("node", node_name)
        data = await self._redis.get(key)
        return json.loads(data) if data else None

    async def store_cache(self, cache_type: str, cache_key: str, value: str):
        """Store a cache entry (for L0 cache layer)."""
        key = self._key("cache", cache_type, cache_key)
        await self._redis.setex(key, self.ttl * 6, value)  # longer TTL for cache

    async def get_cache(self, cache_type: str, cache_key: str) -> Optional[str]:
        """Get a cache entry."""
        key = self._key("cache", cache_type, cache_key)
        return await self._redis.get(key)

    async def get_recent_embeddings(self, n: int = 10) -> List[np.ndarray]:
        """Get N most recent embeddings for diversity checking."""
        pattern = self._key("emb", "*")
        embeddings = []
        async for key in self._redis.scan_iter(match=pattern, count=100):
            data = await self._redis.get(key)
            if data:
                embeddings.append(np.array(json.loads(data), dtype=np.float32))
            if len(embeddings) >= n:
                break
        return embeddings

    async def flush(self):
        """Clear all BrainNet data from Redis."""
        pattern = self._key("*")
        async for key in self._redis.scan_iter(match=pattern, count=100):
            await self._redis.delete(key)
