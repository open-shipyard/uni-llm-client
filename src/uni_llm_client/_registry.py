# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Resolves ``provider/model`` ids to providers, shared by both clients."""

import os
from collections.abc import Mapping

import httpx

from uni_llm_client._effort import Effort, parse_effort
from uni_llm_client._errors import AuthenticationError
from uni_llm_client.providers._base import Provider
from uni_llm_client.providers.anthropic import AnthropicProvider
from uni_llm_client.providers.openrouter import OpenRouterProvider

PROVIDERS: dict[str, type[Provider]] = {
    provider.name: provider for provider in (AnthropicProvider, OpenRouterProvider)
}


class ProviderRegistry:
    """Creates each provider once and builds the first request for a question."""

    def __init__(self, api_keys: Mapping[str, str] | None) -> None:
        self._api_keys = dict(api_keys or {})
        self._providers: dict[str, Provider] = {}

    def prepare(
        self,
        model_id: str,
        question: str,
        *,
        web_search: bool,
        effort: Effort | str | None,
    ) -> tuple[Provider, httpx.Request]:
        """Validate the arguments and build the first request without sending it."""
        parsed_effort = parse_effort(effort)
        name, _, model = model_id.partition("/")
        if not model:
            raise ValueError(
                f"Expected a model id like 'anthropic/claude-opus-5', got {model_id!r}"
            )
        provider = self._provider(name)
        request = provider.build_request(
            model, question, web_search=web_search, effort=parsed_effort
        )
        return provider, request

    def _provider(self, name: str) -> Provider:
        if name not in self._providers:
            provider_cls = PROVIDERS.get(name)
            if provider_cls is None:
                available = ", ".join(sorted(PROVIDERS))
                raise ValueError(f"Unknown provider {name!r}; available: {available}")
            api_key = self._api_keys.get(name) or os.environ.get(
                provider_cls.api_key_env
            )
            if not api_key:
                raise AuthenticationError(
                    f"No API key for {name!r}: pass api_keys={{{name!r}: ...}} "
                    f"or set {provider_cls.api_key_env}"
                )
            self._providers[name] = provider_cls(api_key)
        return self._providers[name]
