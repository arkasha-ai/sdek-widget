"""ConflictMonitor — ACC-inspired conflict detection.

Two levels:
  Level 1 (ERN, 50-100ms): Fast error flag when L1 and L2 disagree
  Level 2 (PFC, 200ms+): Slow deliberate conflict resolution
"""

import numpy as np
import time
import logging
from typing import Optional, Tuple
from scipy.spatial.distance import cosine

from .messages import BrainNetMessage

logger = logging.getLogger("brainnet.conflict")


class ConflictMonitor:
    """Anterior Cingulate Cortex — detects conflicts between processing levels."""

    def __init__(self, ern_threshold: float = 0.4, pfc_threshold: float = 0.3):
        self.ern_threshold = ern_threshold  # disagreement threshold for ERN
        self.pfc_threshold = pfc_threshold  # threshold for PFC intervention
        self._conflict_history = []

    def ern_check(self, l1_msg: BrainNetMessage, l2_consensus: BrainNetMessage) -> Tuple[bool, float]:
        """Level 1: Error-Related Negativity — fast conflict flag.
        
        Compares L1 embedding with L2 consensus. If they disagree significantly,
        raises a conflict flag.
        
        Returns: (has_conflict, disagreement_score)
        """
        start = time.time()

        if l1_msg.embedding is None or l2_consensus.embedding is None:
            return False, 0.0

        # Cosine distance between L1 and L2
        disagreement = cosine(l1_msg.embedding, l2_consensus.embedding)

        has_conflict = disagreement > self.ern_threshold
        elapsed_ms = (time.time() - start) * 1000

        if has_conflict:
            logger.warning(
                f"ERN CONFLICT: L1 vs L2 disagreement={disagreement:.3f} "
                f"(threshold={self.ern_threshold}), time={elapsed_ms:.0f}ms"
            )
            self._conflict_history.append({
                "type": "ERN",
                "disagreement": disagreement,
                "timestamp": time.time(),
                "l1_intent": l1_msg.metadata.get("intent", "unknown"),
            })

        return has_conflict, disagreement

    def pfc_resolve(self, l1_msg: BrainNetMessage, l2_messages: list,
                    consensus_msg: BrainNetMessage) -> dict:
        """Level 2: Prefrontal Cortex — deliberate conflict resolution.
        
        Analyzes the disagreement pattern and decides what to do:
        - "trust_l2": L2 consensus is strong, override L1
        - "trust_l1": L1 was correct, L2 is confused
        - "escalate": Need more processing (send to L3 with caution)
        - "retry": Ask L2 to retry with different parameters
        
        Returns: resolution dict with action and reasoning
        """
        start = time.time()

        # Check L2 internal agreement
        agreement = consensus_msg.metadata.get("agreement_score", 0.0)
        outliers = consensus_msg.metadata.get("outliers", [])

        # If L2 members strongly agree with each other, trust L2
        if agreement > 0.8 and len(outliers) == 0:
            action = "trust_l2"
            reason = f"L2 consensus strong (agreement={agreement:.3f}), overriding L1"
        # If L2 is internally conflicted too, escalate
        elif agreement < 0.5:
            action = "escalate"
            reason = f"Both L1 and L2 conflicted (L2 agreement={agreement:.3f})"
        # If only one L2 member is an outlier, it might be the devil's advocate
        elif len(outliers) == 1 and outliers[0] == 2:  # Member 2 is always critical
            action = "trust_l2"
            reason = "Outlier is devil's advocate (expected), trusting consensus"
        else:
            action = "trust_l1"
            reason = f"L2 inconsistent (outliers={outliers}), falling back to L1"

        elapsed_ms = (time.time() - start) * 1000

        resolution = {
            "action": action,
            "reason": reason,
            "l2_agreement": agreement,
            "l2_outliers": outliers,
            "pfc_time_ms": elapsed_ms,
        }

        logger.info(f"PFC resolution: {action} — {reason}")

        self._conflict_history.append({
            "type": "PFC",
            "resolution": resolution,
            "timestamp": time.time(),
        })

        return resolution

    def get_conflict_rate(self, window_seconds: float = 300) -> float:
        """Get conflict rate over the last N seconds."""
        now = time.time()
        recent = [c for c in self._conflict_history if now - c["timestamp"] < window_seconds]
        ern_conflicts = [c for c in recent if c["type"] == "ERN"]
        return len(ern_conflicts) / max(len(recent), 1)
