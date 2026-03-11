"""Gossip Protocol — Inter-node communication layer.

Nodes share state information, importance scores, and conflict flags
through a gossip-style protocol. Each node maintains a local view
of the network state.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import numpy as np

from .messages import BrainNetMessage, MessageType

logger = logging.getLogger("brainnet.gossip")


@dataclass
class NodeState:
    """State of a single node as seen by gossip protocol."""
    node_name: str
    last_heartbeat: float = 0.0
    importance_avg: float = 0.0
    load: float = 0.0  # 0-1, how busy
    conflict_rate: float = 0.0
    last_embedding: Optional[np.ndarray] = None
    metadata: dict = field(default_factory=dict)


class GossipProtocol:
    """Gossip protocol for sharing state between brain nodes."""

    def __init__(self, node_name: str, gossip_interval: float = 1.0):
        self.node_name = node_name
        self.gossip_interval = gossip_interval
        self._states: Dict[str, NodeState] = {}
        self._listeners: List[Callable] = []
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def get_state(self, node_name: str) -> Optional[NodeState]:
        """Get the known state of a node."""
        return self._states.get(node_name)

    def get_all_states(self) -> Dict[str, NodeState]:
        """Get all known node states."""
        return dict(self._states)

    def update_local_state(self, importance_avg: float = 0.0, load: float = 0.0,
                           conflict_rate: float = 0.0, embedding: np.ndarray = None):
        """Update this node's state."""
        self._states[self.node_name] = NodeState(
            node_name=self.node_name,
            last_heartbeat=time.time(),
            importance_avg=importance_avg,
            load=load,
            conflict_rate=conflict_rate,
            last_embedding=embedding,
        )

    async def broadcast(self, msg: BrainNetMessage):
        """Broadcast a message to all listening nodes."""
        gossip_msg = BrainNetMessage(
            task_id=msg.task_id,
            source_node=self.node_name,
            timestamp=time.time(),
            message_type=MessageType.GOSSIP,
            embedding=msg.embedding,
            importance_score=msg.importance_score,
            metadata={
                "gossip_from": self.node_name,
                "original_source": msg.source_node,
                **msg.metadata,
            },
        )
        await self._message_queue.put(gossip_msg)

    def on_gossip(self, callback: Callable):
        """Register a callback for incoming gossip messages."""
        self._listeners.append(callback)

    async def receive(self, msg: BrainNetMessage):
        """Process incoming gossip message."""
        source = msg.metadata.get("gossip_from", msg.source_node)

        # Update state for the source node
        self._states[source] = NodeState(
            node_name=source,
            last_heartbeat=time.time(),
            importance_avg=msg.importance_score,
            last_embedding=msg.embedding,
            metadata=msg.metadata,
        )

        # Notify listeners
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(msg)
                else:
                    listener(msg)
            except Exception as e:
                logger.error(f"Gossip listener error: {e}")

    async def start(self):
        """Start gossip processing loop."""
        self._running = True
        logger.info(f"Gossip protocol started for {self.node_name}")

        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=self.gossip_interval
                )
                await self.receive(msg)
            except asyncio.TimeoutError:
                # Heartbeat: update our own timestamp
                if self.node_name in self._states:
                    self._states[self.node_name].last_heartbeat = time.time()
            except Exception as e:
                logger.error(f"Gossip error: {e}")

    async def stop(self):
        """Stop gossip processing."""
        self._running = False
        logger.info(f"Gossip protocol stopped for {self.node_name}")

    def get_network_health(self) -> dict:
        """Get overall network health metrics."""
        now = time.time()
        active_nodes = {
            name: state for name, state in self._states.items()
            if now - state.last_heartbeat < 30
        }
        return {
            "active_nodes": len(active_nodes),
            "total_nodes": len(self._states),
            "avg_importance": float(np.mean([s.importance_avg for s in active_nodes.values()])) if active_nodes else 0.0,
            "avg_conflict_rate": float(np.mean([s.conflict_rate for s in active_nodes.values()])) if active_nodes else 0.0,
        }
