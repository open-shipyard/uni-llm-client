# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Asynchronous client."""

from collections.abc import Mapping
from types import TracebackType
from typing import Self

import httpx

from uni_llm_client._client import DEFAULT_TIMEOUT
from uni_llm_client._effort import Effort
from uni_llm_client._errors import IncompleteResponseError
from uni_llm_client._registry import ProviderRegistry
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
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._registry = ProviderRegistry(api_keys)
        self._http = http_client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)

    async def ask(
        self,
        model: str,
        question: str,
        *,
        web_search: bool = False,
        effort: Effort | str | None = None,
    ) -> str:
        """Ask `model`, a ``"provider/model"`` id, a question and return the answer."""
        provider, request = self._registry.prepare(
            model, question, web_search=web_search, effort=effort
        )
        for _ in range(MAX_REQUESTS):
            result = provider.parse_response(await self._http.send(request))
            if isinstance(result, str):
                return result
            request = result
        raise IncompleteResponseError(f"No answer after {MAX_REQUESTS} requests")

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
