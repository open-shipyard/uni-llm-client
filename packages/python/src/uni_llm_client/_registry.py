# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Resolves ``provider/model`` ids to providers, shared by both clients."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from uni_llm_client._effort import Effort, parse_effort
from uni_llm_client._errors import AuthenticationError
from uni_llm_client._messages import Message, Tool
from uni_llm_client.providers._base import ModelCall, Provider
from uni_llm_client.providers.anthropic import AnthropicProvider
from uni_llm_client.providers.openrouter import OpenRouterProvider

PROVIDERS: dict[str, type[Provider]] = {
    provider.name: provider for provider in (AnthropicProvider, OpenRouterProvider)
}


class ProviderRegistry:
    """Creates each provider once and validates a call before anything is sent."""

    def __init__(self, api_keys: Mapping[str, str] | None) -> None:
        self._api_keys = dict(api_keys or {})
        self._providers: dict[str, Provider] = {}

    def prepare(
        self,
        model_id: str,
        messages: Sequence[Message],
        *,
        system: str | None = None,
        tools: Sequence[Tool] = (),
        web_search: bool = False,
        effort: Effort | str | None = None,
        max_tokens: int | None = None,
    ) -> tuple[Provider, ModelCall]:
        """Validate the arguments and resolve the provider without sending anything."""
        parsed_effort = parse_effort(effort)
        if not messages:
            raise ValueError("Expected at least one message")
        if max_tokens is not None and max_tokens < 1:
            raise ValueError(f"Expected a positive max_tokens, got {max_tokens!r}")
        name, _, model = model_id.partition("/")
        if not model:
            raise ValueError(
                f"Expected a model id like 'anthropic/claude-opus-5', got {model_id!r}"
            )
        provider = self._provider(name)
        call = ModelCall(
            model=model,
            messages=tuple(messages),
            system=system,
            tools=tuple(tools),
            web_search=web_search,
            effort=parsed_effort,
            max_tokens=max_tokens,
        )
        return provider, call

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
