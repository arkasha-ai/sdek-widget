"""ImportanceScorer — RPE-guided learning module.

Each node has its own ImportanceScorer that learns which signals matter
through Reward Prediction Error (RPE), inspired by dopaminergic neurons.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Optional


class ImportanceScorer(nn.Module):
    """Scores the importance of incoming embeddings using RPE-guided learning.
    
    Architecture: Small MLP that predicts importance [0,1] from embedding.
    Learning: Uses Reward Prediction Error — when outcome differs from prediction,
    the model updates to better predict importance.
    """

    def __init__(self, embedding_dim: int = 384, hidden_dim: int = 64, lr: float = 1e-3, device: str = "cuda"):
        super().__init__()
        self.device = device
        self.embedding_dim = embedding_dim

        # Small 2-layer MLP
        self.net = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),
        ).to(device)

        self.optimizer = torch.optim.Adam(self.parameters(), lr=lr)
        self.rpe_threshold = 0.2
        self._recent_scores = []  # for drift detection
        self._checkpoint_weights: Optional[dict] = None

    def forward(self, embedding: torch.Tensor) -> torch.Tensor:
        """Score an embedding's importance [0,1]."""
        return self.net(embedding)

    def score(self, embedding: np.ndarray) -> float:
        """Score a numpy embedding. Returns float in [0,1]."""
        with torch.no_grad():
            t = torch.tensor(embedding, dtype=torch.float32, device=self.device).unsqueeze(0)
            score = self.forward(t)
            return score.item()

    def update(self, embedding: np.ndarray, actual_outcome: float, predicted_score: float = None):
        """Update scorer based on RPE (Reward Prediction Error).
        
        RPE = actual_outcome - predicted_score
        - RPE > threshold: unexpectedly good → amplify (learn to score higher)
        - RPE < -threshold: unexpectedly bad → suppress (learn to score lower)
        - |RPE| <= threshold: expected → skip update
        """
        t = torch.tensor(embedding, dtype=torch.float32, device=self.device).unsqueeze(0)
        score = self.forward(t)

        if predicted_score is None:
            predicted_score = score.item()

        rpe = actual_outcome - predicted_score

        if rpe > self.rpe_threshold:
            # Unexpectedly good → increase importance score
            loss = -torch.log(score + 1e-8)
        elif rpe < -self.rpe_threshold:
            # Unexpectedly bad → decrease importance score
            loss = -torch.log(1 - score + 1e-8)
        else:
            # Expected → skip
            return 0.0

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self._recent_scores.append(score.item())
        if len(self._recent_scores) > 100:
            self._recent_scores = self._recent_scores[-100:]

        return rpe

    def apply_diversity_penalty(self, rpe: float, embedding: np.ndarray, recent_embeddings: list, n: int = 5) -> float:
        """RPE_effective = RPE × (1 - similarity_to_recent_N)
        
        Encourages diversity — if this embedding is similar to recent ones,
        its RPE effect is dampened.
        """
        if not recent_embeddings or len(recent_embeddings) == 0:
            return rpe

        # Compute max cosine similarity to recent N embeddings
        emb_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
        max_sim = 0.0
        for recent in recent_embeddings[-n:]:
            recent_norm = recent / (np.linalg.norm(recent) + 1e-8)
            sim = float(np.dot(emb_norm, recent_norm))
            max_sim = max(max_sim, sim)

        return rpe * (1 - max_sim)

    def save_checkpoint(self):
        """Save current weights for drift detection."""
        self._checkpoint_weights = {k: v.clone() for k, v in self.state_dict().items()}

    def detect_drift(self, threshold: float = 0.1) -> float:
        """Compare current weights to checkpoint. Returns drift magnitude."""
        if self._checkpoint_weights is None:
            return 0.0

        total_drift = 0.0
        n_params = 0
        for name, param in self.named_parameters():
            if name in self._checkpoint_weights:
                diff = (param.data - self._checkpoint_weights[name].to(param.device)).abs().mean().item()
                total_drift += diff
                n_params += 1

        return total_drift / max(n_params, 1)
