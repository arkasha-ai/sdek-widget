"""L2 Collegium — 3× Qwen2.5-1.5B parallel forward passes.

Three instances of the same model process the input independently,
producing diverse embeddings that are aggregated for consensus.
Analogous to cortical columns processing in parallel.
"""

import torch
import asyncio
import time
import logging
from typing import List, Tuple, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np

from .vector_protocol import VectorProtocol
from .importance_scorer import ImportanceScorer
from .messages import BrainNetMessage, MessageType

logger = logging.getLogger("brainnet.L2")

COLLEGIUM_PROMPTS = [
    # M1: Analytical — focus on facts and structure
    "Analyze this carefully. Focus on factual accuracy and logical structure.\nInput: {text}\nAnalysis:",
    # M2: Creative — focus on implications and connections
    "Consider the broader implications and creative angles of this.\nInput: {text}\nInsight:",
    # M3: Critical — devil's advocate
    "Challenge this. What could be wrong, missing, or better?\nInput: {text}\nCritique:",
]


class CollegiumMember:
    """One member of the L2 collegium (single model instance)."""

    def __init__(self, member_id: int, model, tokenizer, vector_protocol: VectorProtocol,
                 importance_scorer: ImportanceScorer, device: str = "cuda"):
        self.member_id = member_id
        self.model = model
        self.tokenizer = tokenizer
        self.vector_protocol = vector_protocol
        self.importance_scorer = importance_scorer
        self.device = device
        self.prompt_template = COLLEGIUM_PROMPTS[member_id]

    def forward(self, text: str) -> Tuple[np.ndarray, str, float]:
        """Run forward pass and return (embedding, generated_text, importance)."""
        prompt = self.prompt_template.format(text=text)
        messages = [{"role": "user", "content": prompt}]
        formatted = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(formatted, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs, output_hidden_states=True)
            hidden_states = outputs.hidden_states[-1]
            embedding = self.vector_protocol.encode(hidden_states)

            gen_ids = self.model.generate(
                **inputs, max_new_tokens=100, temperature=0.7,
                do_sample=True, top_p=0.9,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )
            new_tokens = gen_ids[0][inputs["input_ids"].shape[1]:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        importance = self.importance_scorer.score(embedding)
        return embedding, response, importance


class Collegium:
    """L2: Three parallel model instances for diverse processing."""

    MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
    N_MEMBERS = 3

    def __init__(self, model_path: str = None, device: str = "cuda"):
        self.device = device
        self.model_path = model_path or self.MODEL_NAME
        self.members: List[CollegiumMember] = []
        self._loaded = False

    async def load(self):
        """Load the shared model and create collegium members."""
        if self._loaded:
            return

        logger.info(f"Loading L2 Collegium: {self.model_path}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)
        self._loaded = True
        logger.info(f"L2 Collegium loaded ({self.N_MEMBERS} members)")

    def _load_sync(self):
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, trust_remote_code=True
        )
        # Single model, shared across members (same weights, different prompts)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            device_map=self.device,
            trust_remote_code=True,
        )
        model.eval()

        hidden_dim = model.config.hidden_size
        vector_protocol = VectorProtocol(hidden_dim, vector_dim=48, device=self.device)

        for i in range(self.N_MEMBERS):
            scorer = ImportanceScorer(embedding_dim=48, hidden_dim=32, device=self.device)
            member = CollegiumMember(i, model, tokenizer, vector_protocol, scorer, self.device)
            self.members.append(member)

    async def process(self, text: str, l1_embedding: np.ndarray = None) -> List[Tuple[np.ndarray, str, float]]:
        """Run all collegium members in parallel.
        
        Returns: List of (embedding, response, importance) tuples
        """
        if not self._loaded:
            await self.load()

        start = time.time()
        loop = asyncio.get_event_loop()

        # Run all 3 members concurrently via thread pool
        tasks = [
            loop.run_in_executor(None, member.forward, text)
            for member in self.members
        ]
        results = await asyncio.gather(*tasks)

        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"L2: {len(results)} members done in {elapsed_ms:.0f}ms")

        return results

    async def process_message(self, msg: BrainNetMessage) -> List[BrainNetMessage]:
        """Process a BrainNetMessage through L2 collegium."""
        text = msg.raw_text or ""
        results = await self.process(text, msg.embedding)

        messages = []
        for i, (embedding, response, importance) in enumerate(results):
            m = BrainNetMessage(
                task_id=msg.task_id,
                source_node=f"L2_Member_{i}",
                timestamp=time.time(),
                message_type=MessageType.SIGNAL,
                embedding=embedding,
                importance_score=importance,
                raw_text=response,
                metadata={
                    "member_id": i,
                    "role": ["analytical", "creative", "critical"][i],
                    "l1_intent": msg.metadata.get("intent", "unknown"),
                },
            )
            messages.append(m)

        return messages
