"""Tests for BrainNet message types."""

import numpy as np
import time
from brainnet.messages import BrainNetMessage, MessageType


def test_create_signal():
    msg = BrainNetMessage.create_signal("test_node", "hello world")
    assert msg.source_node == "test_node"
    assert msg.raw_text == "hello world"
    assert msg.message_type == MessageType.SIGNAL
    assert msg.task_id is not None
    assert msg.timestamp > 0
    print("✅ test_create_signal passed")


def test_create_result():
    msg = BrainNetMessage.create_result("task123", "L3", "response text")
    assert msg.task_id == "task123"
    assert msg.message_type == MessageType.RESULT
    print("✅ test_create_result passed")


def test_serialization():
    emb = np.random.randn(48).astype(np.float32)
    msg = BrainNetMessage(
        task_id="t1",
        source_node="test",
        timestamp=time.time(),
        message_type=MessageType.SIGNAL,
        embedding=emb,
        importance_score=0.75,
        raw_text="test message",
        metadata={"key": "value"},
    )

    d = msg.to_dict()
    restored = BrainNetMessage.from_dict(d)

    assert restored.task_id == msg.task_id
    assert restored.source_node == msg.source_node
    assert restored.message_type == msg.message_type
    assert restored.importance_score == msg.importance_score
    assert np.allclose(restored.embedding, msg.embedding, atol=1e-6)
    print("✅ test_serialization passed")


def test_message_types():
    for mt in MessageType:
        assert isinstance(mt.value, str)
    print("✅ test_message_types passed")


if __name__ == "__main__":
    test_create_signal()
    test_create_result()
    test_serialization()
    test_message_types()
    print("\n🎉 All message tests passed!")
