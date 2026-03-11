"""Aggregator — Embedding clustering and consensus from L2 collegium.

Takes multiple embeddings from collegium members, clusters them,
and produces a consensus embedding weighted by importance scores.
"""

import numpy as np
from scipy.spatial.distance import cosine
from typing import List, Tuple, Optional
import logging

from .messages import BrainNetMessage, MessageType

logger = logging.getLogger("brainnet.aggregator")


class Aggregator:
    """Aggregates multiple embeddings into consensus."""

    def __init__(self, agreement_threshold: float = 0.6):
        self.agreement_threshold = agreement_threshold

    def compute_consensus(self, messages: List[BrainNetMessage]) -> Tuple[np.ndarray, float, dict]:
        """Compute consensus embedding from collegium outputs.
        
        Returns: (consensus_embedding, agreement_score, metadata)
        """
        if not messages:
            raise ValueError("No messages to aggregate")

        embeddings = [m.embedding for m in messages if m.embedding is not None]
        importances = [m.importance_score for m in messages]

        if not embeddings:
            raise ValueError("No embeddings in messages")

        # Compute pairwise agreement (cosine similarity)
        n = len(embeddings)
        agreement_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    agreement_matrix[i][j] = 1.0
                else:
                    sim = 1.0 - cosine(embeddings[i], embeddings[j])
                    agreement_matrix[i][j] = sim

        # Overall agreement score (mean of upper triangle)
        agreement_score = float(np.mean([
            agreement_matrix[i][j] for i in range(n) for j in range(i + 1, n)
        ])) if n > 1 else 1.0

        # Weighted average embedding
        weights = np.array(importances, dtype=np.float32)
        if weights.sum() < 1e-8:
            weights = np.ones(n, dtype=np.float32)
        weights = weights / weights.sum()

        consensus = np.zeros_like(embeddings[0])
        for emb, w in zip(embeddings, weights):
            consensus += w * emb

        # Normalize
        norm = np.linalg.norm(consensus)
        if norm > 1e-8:
            consensus = consensus / norm

        # Identify outliers (members that disagree significantly)
        outliers = []
        for i in range(n):
            avg_agreement = np.mean([agreement_matrix[i][j] for j in range(n) if j != i]) if n > 1 else 1.0
            if avg_agreement < self.agreement_threshold:
                outliers.append(i)

        metadata = {
            "agreement_score": agreement_score,
            "individual_importances": importances,
            "outlier_members": outliers,
            "n_members": n,
        }

        logger.info(
            f"Aggregator: agreement={agreement_score:.3f}, "
            f"outliers={outliers}, weights={weights.tolist()}"
        )

        return consensus, agreement_score, metadata

    def aggregate_message(self, task_id: str, collegium_messages: List[BrainNetMessage]) -> BrainNetMessage:
        """Create aggregated BrainNetMessage from collegium outputs."""
        consensus, agreement, meta = self.compute_consensus(collegium_messages)

        # Combine text responses (pick the one with highest importance)
        best_msg = max(collegium_messages, key=lambda m: m.importance_score)
        combined_text = best_msg.raw_text

        import time
        return BrainNetMessage(
            task_id=task_id,
            source_node="Aggregator",
            timestamp=time.time(),
            message_type=MessageType.SIGNAL,
            embedding=consensus,
            importance_score=float(np.mean([m.importance_score for m in collegium_messages])),
            raw_text=combined_text,
            metadata={
                "agreement_score": agreement,
                "outliers": meta["outlier_members"],
                "best_member": best_msg.source_node,
                "all_responses": [m.raw_text for m in collegium_messages],
            },
        )
