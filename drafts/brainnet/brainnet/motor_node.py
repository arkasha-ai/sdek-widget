"""MotorNode — Function calling and action codebook.

Translates intent + response into executable actions.
Maintains an action codebook mapping intent patterns to functions.
"""

import asyncio
import time
import logging
from typing import Dict, Callable, Optional, Any
import numpy as np

from .messages import BrainNetMessage, MessageType

logger = logging.getLogger("brainnet.motor")


class ActionCodebook:
    """Maps intents/patterns to callable actions."""

    def __init__(self):
        self._actions: Dict[str, Callable] = {}
        self._intent_map: Dict[str, str] = {
            "greeting": "respond_greeting",
            "help": "respond_help",
            "question": "respond_question",
            "command": "execute_command",
            "code": "respond_code",
            "math": "respond_math",
        }

    def register(self, action_name: str, handler: Callable):
        """Register an action handler."""
        self._actions[action_name] = handler

    def get_action(self, intent: str) -> Optional[str]:
        """Map intent to action name."""
        return self._intent_map.get(intent)

    async def execute(self, action_name: str, **kwargs) -> Any:
        """Execute a registered action."""
        handler = self._actions.get(action_name)
        if handler is None:
            logger.warning(f"No handler for action: {action_name}")
            return None
        if asyncio.iscoroutinefunction(handler):
            return await handler(**kwargs)
        return handler(**kwargs)


class MotorNode:
    """Translates decisions into actions."""

    def __init__(self):
        self.codebook = ActionCodebook()
        self._register_default_actions()

    def _register_default_actions(self):
        """Register built-in action handlers."""
        self.codebook.register("respond_greeting", self._action_greeting)
        self.codebook.register("respond_help", self._action_help)
        self.codebook.register("respond_question", self._action_question)
        self.codebook.register("execute_command", self._action_command)
        self.codebook.register("respond_code", self._action_code)
        self.codebook.register("respond_math", self._action_math)

    def _action_greeting(self, response: str = "", **kwargs) -> dict:
        return {"type": "text_response", "response": response, "action": "greeting"}

    def _action_help(self, response: str = "", **kwargs) -> dict:
        return {"type": "text_response", "response": response, "action": "help"}

    def _action_question(self, response: str = "", **kwargs) -> dict:
        return {"type": "text_response", "response": response, "action": "answer"}

    def _action_command(self, response: str = "", **kwargs) -> dict:
        return {"type": "command", "response": response, "action": "execute"}

    def _action_code(self, response: str = "", **kwargs) -> dict:
        return {"type": "code_response", "response": response, "action": "code"}

    def _action_math(self, response: str = "", **kwargs) -> dict:
        return {"type": "math_response", "response": response, "action": "calculate"}

    async def process_message(self, result_msg: BrainNetMessage) -> dict:
        """Process a result message into an action."""
        start = time.time()

        intent = result_msg.metadata.get("intent", "unknown")
        action_name = self.codebook.get_action(intent)

        if action_name:
            result = await self.codebook.execute(
                action_name,
                response=result_msg.raw_text or "",
                embedding=result_msg.embedding,
                metadata=result_msg.metadata,
            )
        else:
            # Default: just pass through the text response
            result = {
                "type": "text_response",
                "response": result_msg.raw_text or "",
                "action": "default",
            }

        elapsed_ms = (time.time() - start) * 1000

        result["motor_time_ms"] = elapsed_ms
        result["intent"] = intent
        result["task_id"] = result_msg.task_id

        logger.info(f"Motor: action={result['action']}, time={elapsed_ms:.0f}ms")
        return result
