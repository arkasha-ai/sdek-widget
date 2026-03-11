"""L1 FastDetector — Qwen2.5-0.5B for rapid intent detection.

Runs in ~50ms on RTX 4090. Classifies intent and produces embedding
for downstream nodes. Analogous to fast subcortical processing.
"""

import torch
import asyncio
import time
import logging
from typing import Optional, Tuple
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np

from .vector_protocol import VectorProtocol
from .importance_scorer import ImportanceScorer
from .messages import BrainNetMessage, MessageType

logger = logging.getLogger("brainnet.L1")

# Intent categories
INTENTS = [
    "greeting", "question", "command", "opinion", "creative",
    "code", "math", "conversation", "help", "unknown"
]

INTENT_PROMPT = """Classify the user's intent into exactly one category.
Categories: greeting, question, command, opinion, creative, code, math, conversation, help, unknown
User: {text}
Intent:"""


class FastDetector:
    """L1: Quick intent detection and embedding generation using Qwen2.5-0.5B."""

    MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

    def __init__(self, model_path: str = None, device: str = "cuda"):
        self.device = device
        self.model_path = model_path or self.MODEL_NAME
        self.model = None
        self.tokenizer = None
        self.vector_protocol: Optional[VectorProtocol] = None
        self.importance_scorer: Optional[ImportanceScorer] = None
        self._loaded = False

    async def load(self):
        """Load model and tokenizer."""
        if self._loaded:
            return

        logger.info(f"Loading L1 FastDetector: {self.model_path}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)
        self._loaded = True
        logger.info("L1 FastDetector loaded")

    def _load_sync(self):
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            device_map=self.device,
            trust_remote_code=True,
        )
        self.model.eval()

        # Initialize vector protocol with model's hidden dim
        hidden_dim = self.model.config.hidden_size
        self.vector_protocol = VectorProtocol(hidden_dim, vector_dim=48, device=self.device)
        self.importance_scorer = ImportanceScorer(
            embedding_dim=48, hidden_dim=32, device=self.device
        )

    async def detect(self, text: str) -> Tuple[str, np.ndarray, float]:
        """Detect intent and produce embedding.
        
        Returns: (intent, embedding, importance_score)
        """
        if not self._loaded:
            await self.load()

        loop = asyncio.get_event_loop()
        intent, embedding = await loop.run_in_executor(None, self._detect_sync, text)

        importance = self.importance_scorer.score(embedding)

        return intent, embedding, importance

    def _detect_sync(self, text: str) -> Tuple[str, np.ndarray]:
        """Synchronous detection."""
        prompt = INTENT_PROMPT.format(text=text)

        messages = [{"role": "user", "content": prompt}]
        formatted = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.tokenizer(formatted, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs, output_hidden_states=True)
            hidden_states = outputs.hidden_states[-1]  # Last layer

            # Get embedding via projection
            embedding = self.vector_protocol.encode(hidden_states)

            # Generate intent text
            gen_ids = self.model.generate(
                **inputs, max_new_tokens=10, temperature=0.1,
                do_sample=False, pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )
            new_tokens = gen_ids[0][inputs["input_ids"].shape[1]:]
            intent_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip().lower()

        # Map to known intent
        intent = "unknown"
        for known in INTENTS:
            if known in intent_text:
                intent = known
                break

        return intent, embedding

    async def process_message(self, msg: BrainNetMessage) -> BrainNetMessage:
        """Process a BrainNetMessage through L1."""
        start = time.time()

        intent, embedding, importance = await self.detect(msg.raw_text or "")

        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"L1: intent={intent}, importance={importance:.3f}, time={elapsed_ms:.0f}ms")

        return BrainNetMessage(
            task_id=msg.task_id,
            source_node="L1_FastDetector",
            timestamp=time.time(),
            message_type=MessageType.SIGNAL,
            embedding=embedding,
            importance_score=importance,
            raw_text=msg.raw_text,
            metadata={
                "intent": intent,
                "l1_time_ms": elapsed_ms,
                "original_source": msg.source_node,
            },
        )
