"""Tests for Gossip Protocol."""

import asyncio
import numpy as np
from brainnet.gossip import GossipProtocol
from brainnet.messages import BrainNetMessage, MessageType


async def test_gossip_state():
    """Test node state updates via gossip."""
    gossip = GossipProtocol("test_node")

    gossip.update_local_state(importance_avg=0.7, load=0.5)
    state = gossip.get_state("test_node")
    assert state is not None
    assert state.importance_avg == 0.7
    assert state.load == 0.5
    print("✅ test_gossip_state passed")


async def test_gossip_broadcast():
    """Test message broadcasting."""
    gossip = GossipProtocol("sender")
    received = []

    gossip.on_gossip(lambda msg: received.append(msg))

    # Start gossip in background
    task = asyncio.create_task(gossip.start())

    msg = BrainNetMessage.create_signal("sender", "test")
    await gossip.broadcast(msg)

    # Give it time to process
    await asyncio.sleep(0.2)
    await gossip.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(received) > 0
    assert received[0].message_type == MessageType.GOSSIP
    print("✅ test_gossip_broadcast passed")


async def test_network_health():
    """Test network health reporting."""
    gossip = GossipProtocol("node1")
    gossip.update_local_state(importance_avg=0.5, conflict_rate=0.1)

    health = gossip.get_network_health()
    assert health["active_nodes"] == 1
    assert health["avg_importance"] == 0.5
    print("✅ test_network_health passed")


if __name__ == "__main__":
    asyncio.run(test_gossip_state())
    asyncio.run(test_gossip_broadcast())
    asyncio.run(test_network_health())
    print("\n🎉 All gossip tests passed!")
