# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Synchronous client."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import replace
from types import TracebackType
from typing import Self

import httpx2

from uni_llm_client._effort import Effort
from uni_llm_client._errors import IncompleteResponseError
from uni_llm_client._events import Completed, StreamEvent
from uni_llm_client._messages import (
    Message,
    ReasoningBlock,
    Response,
    StopReason,
    TextBlock,
    Tool,
)
from uni_llm_client._registry import ProviderRegistry
from uni_llm_client._sse import SSEDecoder
from uni_llm_client.providers._base import MAX_REQUESTS

# Answers can take minutes, especially at high effort.
DEFAULT_TIMEOUT = httpx2.Timeout(600.0, connect=10.0)


class Client:
    """Synchronous client. Create it once and reuse it: it holds a connection pool.

    Args:
        api_keys: API key per provider, e.g. ``{"anthropic": "..."}``. Providers
            without one read their environment variable, e.g. ``ANTHROPIC_API_KEY``.
        http_client: HTTP client used to send requests; closed with this client.
    """

    def __init__(
        self,
        *,
        api_keys: Mapping[str, str] | None = None,
        http_client: httpx2.Client | None = None,
    ) -> None:
        self._registry = ProviderRegistry(api_keys)
        self._http = http_client or httpx2.Client(timeout=DEFAULT_TIMEOUT)

    def ask(
        self,
        model: str,
        question: str,
        *,
        web_search: bool = False,
        effort: Effort | str | None = None,
    ) -> str:
        """Ask `model`, a ``"provider/model"`` id, a question and return the answer."""
        provider, call = self._registry.prepare(
            model, [Message.user(question)], web_search=web_search, effort=effort
        )
        for _ in range(MAX_REQUESTS):
            response = provider.parse_response(
                self._http.send(provider.build_request(call))
            )
            if response.stop_reason is not StopReason.PAUSE_TURN:
                return answer_of(response)
            # A server tool loop hit its iteration limit: re-send the turn so far
            # and the server resumes where it left off.
            call = replace(call, messages=(*call.messages, response.message))
        raise IncompleteResponseError(f"No answer after {MAX_REQUESTS} requests")

    def complete(
        self,
        model: str,
        messages: Sequence[Message],
        *,
        system: str | None = None,
        tools: Sequence[Tool] = (),
        web_search: bool = False,
        effort: Effort | str | None = None,
        max_tokens: int | None = None,
    ) -> Response:
        """Send `messages` to `model` and return its whole response."""
        provider, call = self._registry.prepare(
            model,
            messages,
            system=system,
            tools=tools,
            web_search=web_search,
            effort=effort,
            max_tokens=max_tokens,
        )
        return provider.parse_response(self._http.send(provider.build_request(call)))

    def stream(
        self,
        model: str,
        messages: Sequence[Message],
        *,
        system: str | None = None,
        tools: Sequence[Tool] = (),
        web_search: bool = False,
        effort: Effort | str | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[StreamEvent]:
        """Send `messages` to `model` and yield its response as it arrives.

        The request is sent on the first iteration. Closing the iterator early
        closes the vendor's response.
        """
        provider, call = self._registry.prepare(
            model,
            messages,
            system=system,
            tools=tools,
            web_search=web_search,
            effort=effort,
            max_tokens=max_tokens,
        )
        request = provider.build_request(call, stream=True)
        response = self._http.send(request, stream=True)
        try:
            if response.is_error:
                response.read()
                raise provider.error_of(response)
            parser = provider.stream_parser()
            decoder = SSEDecoder()
            for line in response.iter_lines():
                event = decoder.feed(line)
                if event is not None:
                    yield from parser.feed(event)
            yield Completed(parser.finish())
        finally:
            response.close()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def answer_of(response: Response) -> str:
    """The answer `ask` returns: the text after the last tool block, skipping any
    preamble. Raises instead of returning nothing (EFFORT-6)."""
    if response.stop_reason is StopReason.MAX_TOKENS:
        raise IncompleteResponseError(
            "Reached the output token limit before the answer was complete"
        )
    texts: list[str] = []
    for block in response.message.content:
        if isinstance(block, TextBlock):
            texts.append(block.text)
        elif not isinstance(block, ReasoningBlock):
            texts.clear()
    answer = "".join(texts)
    if not answer:
        raise IncompleteResponseError("The response contained no answer text")
    return answer
