"""Wrapper functions around an LLM chain."""

import logging
from abc import abstractmethod
from typing import Any, Generator, Optional, Protocol, runtime_checkable

from llama_index.callbacks.base import CallbackManager
from llama_index.callbacks.schema import CBEventType, EventPayload
from llama_index.llms.base import LLM, LLMMetadata, StreamCompletionResponse
from llama_index.llms.utils import LLMType, resolve_llm
from llama_index.prompts.base import Prompt
from llama_index.utils import count_tokens

logger = logging.getLogger(__name__)


@runtime_checkable
class BaseLLMPredictor(Protocol):
    """Base LLM Predictor."""

    callback_manager: CallbackManager

    @property
    @abstractmethod
    def metadata(self) -> LLMMetadata:
        """Get LLM metadata."""

    @abstractmethod
    def predict(self, prompt: Prompt, **prompt_args: Any) -> str:
        """Predict the answer to a query."""

    @abstractmethod
    def stream(self, prompt: Prompt, **prompt_args: Any) -> StreamCompletionResponse:
        """Stream the answer to a query."""

    @abstractmethod
    async def apredict(self, prompt: Prompt, **prompt_args: Any) -> str:
        """Async predict the answer to a query."""

    @abstractmethod
    async def astream(
        self, prompt: Prompt, **prompt_args: Any
    ) -> StreamCompletionResponse:
        """Async predict the answer to a query."""


class LLMPredictor(BaseLLMPredictor):
    """LLM predictor class.

    A lightweight wrapper on top of LLMs that handles:
    - conversion of prompts to the string input format expected by LLMs
    - logging of prompts and responses to a callback manager

    NOTE: Mostly keeping around for legacy reasons. A potential future path is to
    deprecate this class and move all functionality into the LLM class.
    """

    def __init__(
        self,
        llm: Optional[LLMType] = None,
        callback_manager: Optional[CallbackManager] = None,
    ) -> None:
        """Initialize params."""
        self._llm = resolve_llm(llm)
        self.callback_manager = callback_manager or CallbackManager([])

    @property
    def llm(self) -> LLM:
        """Get LLM."""
        return self._llm

    @property
    def metadata(self) -> LLMMetadata:
        """Get LLM metadata."""
        return self._llm.metadata

    def _log_start(self, prompt: Prompt, prompt_args: dict) -> str:
        """Log start of an LLM event."""
        llm_payload = prompt_args.copy()
        llm_payload[EventPayload.TEMPLATE] = prompt
        event_id = self.callback_manager.on_event_start(
            CBEventType.LLM,
            payload=llm_payload,
        )

        return event_id

    def _log_end(self, event_id: str, output: str, formatted_prompt: str) -> None:
        """Log end of an LLM event."""
        prompt_tokens_count = count_tokens(formatted_prompt)
        prediction_tokens_count = count_tokens(output)
        self.callback_manager.on_event_end(
            CBEventType.LLM,
            payload={
                EventPayload.RESPONSE: output,
                EventPayload.PROMPT: formatted_prompt,
                # deprecated
                "formatted_prompt_tokens_count": prompt_tokens_count,
                "prediction_tokens_count": prediction_tokens_count,
                "total_tokens_used": prompt_tokens_count + prediction_tokens_count,
            },
            event_id=event_id,
        )

    def predict(self, prompt: Prompt, **prompt_args: Any) -> str:
        """Predict."""
        event_id = self._log_start(prompt, prompt_args)

        formatted_prompt = prompt.format(llm=self._llm, **prompt_args)
        output = self._llm.complete(formatted_prompt).text

        logger.debug(output)
        self._log_end(event_id, output, formatted_prompt)

        return output

    def stream(self, prompt: Prompt, **prompt_args: Any) -> Generator:
        """Stream."""
        formatted_prompt = prompt.format(llm=self._llm, **prompt_args)
        stream_response = self._llm.stream_complete(formatted_prompt)
        return stream_response

    async def apredict(self, prompt: Prompt, **prompt_args: Any) -> str:
        """Async predict."""
        event_id = self._log_start(prompt, prompt_args)

        formatted_prompt = prompt.format(llm=self._llm, **prompt_args)
        output = (await self._llm.acomplete(formatted_prompt)).text
        logger.debug(output)

        self._log_end(event_id, output, formatted_prompt)
        return output

    async def astream(self, prompt: Prompt, **prompt_args: Any) -> Generator:
        """Async stream."""
        formatted_prompt = prompt.format(llm=self._llm, **prompt_args)
        stream_response = await self._llm.astream_complete(formatted_prompt)
        return stream_response
