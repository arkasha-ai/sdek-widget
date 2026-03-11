"""Orchestrator — Main processing loop connecting all BrainNet components.

Pipeline: Input → L0 Cache → L1 FastDetector → L2 Collegium → Aggregator
→ ConflictMonitor → CriticalThinking → L3 FinalNode → MotorNode → Output
"""

import asyncio
import time
import logging
from typing import Optional

from .messages import BrainNetMessage, MessageType
from .working_memory import WorkingMemory
from .cache_layer import CacheLayer
from .fast_detector import FastDetector
from .collegium import Collegium
from .aggregator import Aggregator
from .conflict_monitor import ConflictMonitor
from .critical_thinking import CriticalThinkingLayer
from .final_node import FinalNode
from .motor_node import MotorNode
from .gossip import GossipProtocol

logger = logging.getLogger("brainnet")


class BrainNetOrchestrator:
    """Main orchestrator connecting all brain components."""

    def __init__(self, device: str = "cuda", redis_url: str = "redis://localhost:6379",
                 l1_model: str = None, l2_model: str = None):
        self.device = device

        # Core components
        self.memory = WorkingMemory(redis_url=redis_url)
        self.cache = CacheLayer(self.memory)
        self.l1 = FastDetector(model_path=l1_model, device=device)
        self.l2 = Collegium(model_path=l2_model, device=device)
        self.aggregator = Aggregator()
        self.conflict_monitor = ConflictMonitor()
        self.critical_thinking = CriticalThinkingLayer()
        self.l3 = FinalNode(model_path=l1_model, device=device)  # Shares model with L1
        self.motor = MotorNode()

        # Gossip protocols for each major node
        self.gossip_l1 = GossipProtocol("L1_FastDetector")
        self.gossip_l2 = GossipProtocol("L2_Collegium")
        self.gossip_l3 = GossipProtocol("L3_FinalNode")

        self._initialized = False
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "conflicts": 0,
            "avg_time_ms": 0.0,
        }

    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing BrainNet...")

        # Connect to Redis
        await self.memory.connect()
        logger.info("Working memory connected")

        # Load models (L1 first, then L2 — L3 shares with L1)
        await self.l1.load()
        logger.info("L1 FastDetector loaded")

        await self.l2.load()
        logger.info("L2 Collegium loaded")

        # L3 shares model with L1
        self.l3.model = self.l1.model
        self.l3.tokenizer = self.l1.tokenizer
        self.l3.vector_protocol = self.l1.vector_protocol
        self.l3.importance_scorer = self.l1.importance_scorer
        self.l3._loaded = True
        logger.info("L3 FinalNode loaded (shared with L1)")

        # Start gossip protocols
        asyncio.create_task(self.gossip_l1.start())
        asyncio.create_task(self.gossip_l2.start())
        asyncio.create_task(self.gossip_l3.start())

        self._initialized = True
        logger.info("BrainNet initialized successfully!")

    async def process(self, text: str) -> str:
        """Process user input through the full pipeline.
        
        Returns: response text
        """
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        self._stats["total_requests"] += 1

        # Create input message
        input_msg = BrainNetMessage.create_signal("user", text)
        await self.memory.store_message(input_msg)

        # === L0: Cache lookup ===
        cache_hit = await self.cache.lookup(text)
        if cache_hit:
            self._stats["cache_hits"] += 1
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"[L0 hit: {cache_hit.level}] time={elapsed:.0f}ms")
            self._update_avg_time(elapsed)
            return cache_hit.response

        logger.info("[L0 miss]")

        # === L1: Fast Detection ===
        l1_msg = await self.l1.process_message(input_msg)
        await self.memory.store_message(l1_msg)
        await self.gossip_l1.broadcast(l1_msg)

        intent = l1_msg.metadata.get("intent", "unknown")
        logger.info(f"[L1: intent={intent}]")

        # === L2: Collegium (3 parallel forwards) ===
        l2_messages = await self.l2.process_message(l1_msg)
        for msg in l2_messages:
            await self.memory.store_message(msg)
        await self.gossip_l2.broadcast(l2_messages[0] if l2_messages else l1_msg)

        logger.info(f"[L2: {len(l2_messages)} forwards]")

        # === Aggregation ===
        consensus_msg = self.aggregator.aggregate_message(input_msg.task_id, l2_messages)
        consensus_msg.metadata["l1_intent"] = intent
        await self.memory.store_message(consensus_msg)

        # === Conflict Monitor ===
        has_conflict, disagreement = self.conflict_monitor.ern_check(l1_msg, consensus_msg)
        if has_conflict:
            self._stats["conflicts"] += 1
            resolution = self.conflict_monitor.pfc_resolve(l1_msg, l2_messages, consensus_msg)
            logger.info(f"[Conflict: {resolution['action']}]")

            if resolution["action"] == "trust_l1":
                # Override consensus with L1's perspective
                consensus_msg.metadata["conflict_override"] = "l1"
        else:
            logger.info("[No conflict]")

        # === Critical Thinking ===
        ct_result = self.critical_thinking.process(consensus_msg, l2_messages)
        if not ct_result["should_proceed"]:
            logger.warning(f"[Critical thinking flagged issues: {ct_result['dlpfc']['issues']}]")

        # === L3: Final Response ===
        result_msg = await self.l3.process_message(input_msg, consensus_msg)
        await self.memory.store_message(result_msg)
        await self.gossip_l3.broadcast(result_msg)

        response_text = result_msg.raw_text or "I couldn't formulate a response."
        logger.info(f"[L3: response ready]")

        # === Motor Node ===
        motor_result = await self.motor.process_message(result_msg)
        final_response = motor_result.get("response", response_text)

        # === Cache the result ===
        await self.cache.store(text, final_response, l1_msg.embedding)

        # === Update importance scorers (RPE) ===
        # Simple heuristic: response length as outcome proxy
        outcome = min(len(final_response) / 500, 1.0)
        if l1_msg.embedding is not None:
            rpe = self.critical_thinking.apply_diversity_penalty(
                outcome - l1_msg.importance_score,
                l1_msg.embedding
            )
            self.l1.importance_scorer.update(l1_msg.embedding, outcome)

        elapsed = (time.time() - start_time) * 1000
        self._update_avg_time(elapsed)
        logger.info(f"Total pipeline time: {elapsed:.0f}ms")

        return final_response

    def _update_avg_time(self, elapsed_ms: float):
        n = self._stats["total_requests"]
        avg = self._stats["avg_time_ms"]
        self._stats["avg_time_ms"] = avg + (elapsed_ms - avg) / n

    def get_stats(self) -> dict:
        return {
            **self._stats,
            "cache_hit_rate": self._stats["cache_hits"] / max(self._stats["total_requests"], 1),
            "conflict_rate": self._stats["conflicts"] / max(self._stats["total_requests"], 1),
        }

    async def shutdown(self):
        """Gracefully shutdown all components."""
        logger.info("Shutting down BrainNet...")
        await self.gossip_l1.stop()
        await self.gossip_l2.stop()
        await self.gossip_l3.stop()
        await self.memory.close()
        logger.info("BrainNet shutdown complete.")
