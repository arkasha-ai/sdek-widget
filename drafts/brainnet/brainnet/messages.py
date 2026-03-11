"""BrainNet message types and data structures."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import time
import uuid


class MessageType(Enum):
    SIGNAL = "signal"
    GOSSIP = "gossip"
    RESULT = "result"
    STOP = "stop"
    CONSOLIDATE = "consolidate"


@dataclass
class BrainNetMessage:
    """Core message passed between brain nodes via vector protocol."""
    task_id: str
    source_node: str
    timestamp: float
    message_type: MessageType
    embedding: Optional[np.ndarray] = None  # 10-50d float32
    importance_score: float = 0.0
    raw_text: Optional[str] = None  # only for user input/output
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create_signal(cls, source: str, text: str, embedding: np.ndarray = None) -> "BrainNetMessage":
        return cls(
            task_id=str(uuid.uuid4())[:8],
            source_node=source,
            timestamp=time.time(),
            message_type=MessageType.SIGNAL,
            embedding=embedding,
            raw_text=text,
        )

    @classmethod
    def create_result(cls, task_id: str, source: str, text: str, embedding: np.ndarray = None) -> "BrainNetMessage":
        return cls(
            task_id=task_id,
            source_node=source,
            timestamp=time.time(),
            message_type=MessageType.RESULT,
            embedding=embedding,
            raw_text=text,
        )

    def to_dict(self) -> dict:
        d = {
            "task_id": self.task_id,
            "source_node": self.source_node,
            "timestamp": self.timestamp,
            "message_type": self.message_type.value,
            "importance_score": self.importance_score,
            "raw_text": self.raw_text,
            "metadata": self.metadata,
        }
        if self.embedding is not None:
            d["embedding"] = self.embedding.tolist()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "BrainNetMessage":
        emb = np.array(d["embedding"], dtype=np.float32) if "embedding" in d and d["embedding"] is not None else None
        return cls(
            task_id=d["task_id"],
            source_node=d["source_node"],
            timestamp=d["timestamp"],
            message_type=MessageType(d["message_type"]),
            embedding=emb,
            importance_score=d.get("importance_score", 0.0),
            raw_text=d.get("raw_text"),
            metadata=d.get("metadata", {}),
        )
