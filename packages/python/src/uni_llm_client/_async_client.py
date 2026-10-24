# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Asynchronous client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import replace
from types import TracebackType
from typing import Self

import httpx2

from uni_llm_client._client import DEFAULT_TIMEOUT, answer_of
from uni_llm_client._effort import Effort
from uni_llm_client._errors import IncompleteResponseError
from uni_llm_client._events import Completed, StreamEvent
from uni_llm_client._messages import Message, Response, StopReason, Tool
from uni_llm_client._registry import ProviderRegistry
from uni_llm_client._sse import SSEDecoder
from uni_llm_client.providers._base import MAX_REQUESTS


class AsyncClient:
    """Asynchronous client with the same API as `Client`.

    Args:
        api_keys: API key per provider, e.g. ``{"anthropic": "..."}``. Providers
            without one read their environment variable, e.g. ``ANTHROPIC_API_KEY``.
        http_client: HTTP client used to send requests; closed with this client.
    """

    def __init__(
        self,
        *,
        api_keys: Mapping[str, str] | None = None,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        self._registry = ProviderRegistry(api_keys)
        self._http = http_client or httpx2.AsyncClient(timeout=DEFAULT_TIMEOUT)

    async def ask(
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
            sent = await self._http.send(provider.build_request(call))
            response = provider.parse_response(sent)
            if response.stop_reason is not StopReason.PAUSE_TURN:
                return answer_of(response)
            # A server tool loop hit its iteration limit: re-send the turn so far
            # and the server resumes where it left off.
            call = replace(call, messages=(*call.messages, response.message))
        raise IncompleteResponseError(f"No answer after {MAX_REQUESTS} requests")

    async def complete(
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
        return provider.parse_response(
            await self._http.send(provider.build_request(call))
        )

    async def stream(
        self,
        model: str,
        messages: Sequence[Message],
        *,
        system: str | None = None,
        tools: Sequence[Tool] = (),
        web_search: bool = False,
        effort: Effort | str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamEvent]:
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
        response = await self._http.send(request, stream=True)
        try:
            if response.is_error:
                await response.aread()
                raise provider.error_of(response)
            parser = provider.stream_parser()
            decoder = SSEDecoder()
            async for line in response.aiter_lines():
                event = decoder.feed(line)
                if event is not None:
                    for item in parser.feed(event):
                        yield item
            yield Completed(parser.finish())
        finally:
            await response.aclose()

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
