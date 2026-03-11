"""L3 FinalNode — Qwen2.5-0.5B for response formulation.

Takes the aggregated consensus from L2 + L1 intent and formulates
the final user-facing response. Uses the same model as L1 but with
a different prompt focused on response generation.
"""

import torch
import asyncio
import time
import logging
from typing import Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np

from .messages import BrainNetMessage, MessageType
from .vector_protocol import VectorProtocol
from .importance_scorer import ImportanceScorer

logger = logging.getLogger("brainnet.L3")

RESPONSE_PROMPT = """You are a helpful AI assistant. Based on the analysis below, formulate a clear, natural response to the user.

User's message: {user_text}
Intent: {intent}
Analysis: {analysis}

Respond naturally and helpfully:"""


class FinalNode:
    """L3: Response formulation using Qwen2.5-0.5B."""

    MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

    def __init__(self, model_path: str = None, device: str = "cuda", shared_model=None, shared_tokenizer=None):
        self.device = device
        self.model_path = model_path or self.MODEL_NAME
        self.model = shared_model
        self.tokenizer = shared_tokenizer
        self.vector_protocol: Optional[VectorProtocol] = None
        self.importance_scorer: Optional[ImportanceScorer] = None
        self._loaded = shared_model is not None

    async def load(self):
        if self._loaded:
            return
        logger.info(f"Loading L3 FinalNode: {self.model_path}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)
        self._loaded = True
        logger.info("L3 FinalNode loaded")

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
        hidden_dim = self.model.config.hidden_size
        self.vector_protocol = VectorProtocol(hidden_dim, vector_dim=48, device=self.device)
        self.importance_scorer = ImportanceScorer(embedding_dim=48, hidden_dim=32, device=self.device)

    async def generate_response(self, user_text: str, intent: str, analysis: str) -> str:
        """Generate final response text."""
        if not self._loaded:
            await self.load()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_sync, user_text, intent, analysis)

    def _generate_sync(self, user_text: str, intent: str, analysis: str) -> str:
        prompt = RESPONSE_PROMPT.format(user_text=user_text, intent=intent, analysis=analysis)
        messages = [{"role": "user", "content": prompt}]
        formatted = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(formatted, return_tensors="pt").to(self.device)

        with torch.no_grad():
            gen_ids = self.model.generate(
                **inputs, max_new_tokens=200, temperature=0.7,
                do_sample=True, top_p=0.9, repetition_penalty=1.2,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )
            new_tokens = gen_ids[0][inputs["input_ids"].shape[1]:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        return response

    async def process_message(self, original_msg: BrainNetMessage,
                              consensus_msg: BrainNetMessage) -> BrainNetMessage:
        """Process through L3 and produce final response."""
        start = time.time()

        intent = consensus_msg.metadata.get("l1_intent",
                 original_msg.metadata.get("intent", "unknown"))
        analysis = consensus_msg.raw_text or ""

        response = await self.generate_response(
            user_text=original_msg.raw_text or "",
            intent=intent,
            analysis=analysis[:500],  # Truncate analysis
        )

        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"L3: response generated in {elapsed_ms:.0f}ms")

        return BrainNetMessage(
            task_id=original_msg.task_id,
            source_node="L3_FinalNode",
            timestamp=time.time(),
            message_type=MessageType.RESULT,
            embedding=consensus_msg.embedding,
            importance_score=consensus_msg.importance_score,
            raw_text=response,
            metadata={
                "intent": intent,
                "l3_time_ms": elapsed_ms,
                "agreement_score": consensus_msg.metadata.get("agreement_score", 0.0),
            },
        )
