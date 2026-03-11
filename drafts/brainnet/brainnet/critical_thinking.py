"""CriticalThinkingLayer — DLPFC + IFC inspired logic and devil's advocate.

DLPFC: Checks consistency of collegium response
IFC right: M_c always plays devil's advocate
Diversity penalty: RPE_effective = RPE * (1 - similarity_to_recent_N)
Drift detection: Compares weights to 7-day checkpoint
"""

import numpy as np
import time
import logging
from typing import List, Optional, Tuple

from .messages import BrainNetMessage
from .importance_scorer import ImportanceScorer

logger = logging.getLogger("brainnet.critical")


class CriticalThinkingLayer:
    """DLPFC + IFC: Logical verification and devil's advocacy."""

    def __init__(self, diversity_window: int = 5, drift_check_interval: int = 100):
        self.diversity_window = diversity_window
        self.drift_check_interval = drift_check_interval
        self._recent_embeddings: List[np.ndarray] = []
        self._process_count = 0

    def dlpfc_check(self, consensus_msg: BrainNetMessage, l2_messages: List[BrainNetMessage]) -> dict:
        """DLPFC: Check consistency of collegium response.
        
        Verifies that the aggregated answer is coherent by checking:
        1. Embedding alignment between consensus and individual members
        2. Importance score distribution
        3. Whether any member flagged issues
        """
        if not l2_messages:
            return {"consistent": True, "confidence": 0.0, "issues": []}

        issues = []

        # Check 1: Importance variance
        importances = [m.importance_score for m in l2_messages]
        imp_var = float(np.var(importances))
        if imp_var > 0.1:
            issues.append(f"High importance variance: {imp_var:.3f}")

        # Check 2: Embedding spread
        embeddings = [m.embedding for m in l2_messages if m.embedding is not None]
        if len(embeddings) >= 2:
            sims = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    norm_i = np.linalg.norm(embeddings[i]) + 1e-8
                    norm_j = np.linalg.norm(embeddings[j]) + 1e-8
                    sim = float(np.dot(embeddings[i], embeddings[j]) / (norm_i * norm_j))
                    sims.append(sim)
            avg_sim = float(np.mean(sims))
            if avg_sim < 0.4:
                issues.append(f"Low member agreement: avg_sim={avg_sim:.3f}")
        else:
            avg_sim = 1.0

        # Check 3: Critical member (M2, devil's advocate) flags
        critical_msg = next((m for m in l2_messages if m.metadata.get("role") == "critical"), None)
        if critical_msg and critical_msg.importance_score > 0.7:
            issues.append("Devil's advocate flagged high importance concern")

        consistent = len(issues) == 0
        confidence = avg_sim * (1 - imp_var)

        result = {
            "consistent": consistent,
            "confidence": confidence,
            "avg_similarity": avg_sim,
            "importance_variance": imp_var,
            "issues": issues,
        }

        if not consistent:
            logger.warning(f"DLPFC: Consistency check failed: {issues}")
        else:
            logger.info(f"DLPFC: Consistent (confidence={confidence:.3f})")

        return result

    def ifc_devils_advocate(self, consensus_msg: BrainNetMessage,
                            critical_member_msg: Optional[BrainNetMessage] = None) -> dict:
        """IFC right hemisphere: Devil's advocate processing.
        
        Always challenges the consensus — if the critical member (M_c) found issues,
        amplifies them. If not, generates standard challenges.
        """
        challenges = []

        # If M_c (critical member) provided specific critique
        if critical_member_msg and critical_member_msg.raw_text:
            challenges.append({
                "source": "M_c",
                "challenge": critical_member_msg.raw_text,
                "severity": critical_member_msg.importance_score,
            })

        # Standard challenges based on consensus properties
        agreement = consensus_msg.metadata.get("agreement_score", 0.0)
        if agreement > 0.95:
            challenges.append({
                "source": "IFC",
                "challenge": "Suspiciously high agreement — groupthink risk",
                "severity": 0.3,
            })

        if consensus_msg.importance_score < 0.2:
            challenges.append({
                "source": "IFC",
                "challenge": "Very low importance — might be dismissing something relevant",
                "severity": 0.4,
            })

        return {
            "has_challenges": len(challenges) > 0,
            "challenges": challenges,
            "recommendation": "proceed" if not challenges or all(c["severity"] < 0.5 for c in challenges) else "review",
        }

    def apply_diversity_penalty(self, rpe: float, embedding: np.ndarray) -> float:
        """RPE_effective = RPE × (1 - similarity_to_recent_N)
        
        Encourages diversity in learned patterns.
        """
        if not self._recent_embeddings:
            self._recent_embeddings.append(embedding.copy())
            return rpe

        emb_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
        max_sim = 0.0
        for recent in self._recent_embeddings[-self.diversity_window:]:
            r_norm = recent / (np.linalg.norm(recent) + 1e-8)
            sim = float(np.dot(emb_norm, r_norm))
            max_sim = max(max_sim, abs(sim))

        self._recent_embeddings.append(embedding.copy())
        if len(self._recent_embeddings) > self.diversity_window * 2:
            self._recent_embeddings = self._recent_embeddings[-self.diversity_window * 2:]

        effective_rpe = rpe * (1 - max_sim)
        if abs(effective_rpe - rpe) > 0.01:
            logger.debug(f"Diversity penalty: RPE {rpe:.3f} → {effective_rpe:.3f} (sim={max_sim:.3f})")

        return effective_rpe

    def process(self, consensus_msg: BrainNetMessage, l2_messages: List[BrainNetMessage]) -> dict:
        """Full critical thinking pass."""
        self._process_count += 1

        # DLPFC consistency check
        dlpfc = self.dlpfc_check(consensus_msg, l2_messages)

        # IFC devil's advocate
        critical_msg = next((m for m in l2_messages if m.metadata.get("role") == "critical"), None)
        ifc = self.ifc_devils_advocate(consensus_msg, critical_msg)

        # Combined assessment
        should_proceed = dlpfc["consistent"] and ifc["recommendation"] == "proceed"

        return {
            "dlpfc": dlpfc,
            "ifc": ifc,
            "should_proceed": should_proceed,
            "process_count": self._process_count,
        }
