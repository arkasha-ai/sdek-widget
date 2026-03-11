"""Vector Protocol — nodes communicate via embeddings, not text.

ProjectionHead maps model hidden states to compact vectors.
Nodes pass these vectors between each other instead of raw text,
reducing bandwidth and enabling direct semantic comparison.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Optional


class ProjectionHead(nn.Module):
    """Projects model hidden states (768/1536d) to compact vectors (32-64d)."""

    def __init__(self, input_dim: int, output_dim: int = 48, device: str = "cuda"):
        super().__init__()
        self.device = device
        self.output_dim = output_dim

        self.projection = nn.Sequential(
            nn.Linear(input_dim, input_dim // 2),
            nn.GELU(),
            nn.Linear(input_dim // 2, output_dim),
            nn.LayerNorm(output_dim),
        ).to(device)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """Project hidden states to compact vectors.
        
        Args:
            hidden_states: (batch, seq_len, hidden_dim) or (batch, hidden_dim)
        Returns:
            (batch, output_dim) projected vector
        """
        if hidden_states.dim() == 3:
            # Pool over sequence: use mean of last layer
            hidden_states = hidden_states.mean(dim=1)
        return self.projection(hidden_states)

    def project(self, hidden_states: torch.Tensor) -> np.ndarray:
        """Project and return as numpy array."""
        with torch.no_grad():
            vec = self.forward(hidden_states)
            return vec.cpu().numpy().squeeze()


class VectorProtocol:
    """Manages vector projections for inter-node communication."""

    def __init__(self, model_dim: int, vector_dim: int = 48, device: str = "cuda"):
        self.device = device
        self.vector_dim = vector_dim
        self.projection = ProjectionHead(model_dim, vector_dim, device)
        self._codebook = {}  # intent → vector mapping

    def encode(self, hidden_states: torch.Tensor) -> np.ndarray:
        """Encode model hidden states to protocol vector."""
        return self.projection.project(hidden_states)

    def decode_to_input_embeds(self, vector: np.ndarray, target_model_dim: int) -> torch.Tensor:
        """Create a pseudo input_embeds from a vector for feeding into another model.
        
        Uses a learned upscale projection to go from compact vector back to model dim.
        This is an approximation — not a perfect inverse.
        """
        t = torch.tensor(vector, dtype=torch.float32, device=self.device).unsqueeze(0)
        # Simple linear upscale (no learned inverse for now)
        if not hasattr(self, '_upscale') or self._upscale.in_features != self.vector_dim:
            self._upscale = nn.Linear(self.vector_dim, target_model_dim).to(self.device)
        with torch.no_grad():
            upscaled = self._upscale(t)
        return upscaled.unsqueeze(1)  # (1, 1, model_dim) — single token embed

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two protocol vectors."""
        norm_a = np.linalg.norm(vec_a) + 1e-8
        norm_b = np.linalg.norm(vec_b) + 1e-8
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def register_intent(self, intent_name: str, vector: np.ndarray):
        """Register a known intent vector in the codebook."""
        self._codebook[intent_name] = vector / (np.linalg.norm(vector) + 1e-8)

    def classify_intent(self, vector: np.ndarray, threshold: float = 0.5) -> Optional[str]:
        """Find closest intent from codebook."""
        if not self._codebook:
            return None

        vec_norm = vector / (np.linalg.norm(vector) + 1e-8)
        best_intent = None
        best_sim = threshold

        for intent, ref_vec in self._codebook.items():
            sim = float(np.dot(vec_norm, ref_vec))
            if sim > best_sim:
                best_sim = sim
                best_intent = intent

        return best_intent
