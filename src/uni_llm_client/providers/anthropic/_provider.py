# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Anthropic Messages API."""

import json
from typing import Any

import httpx

from uni_llm_client._effort import Effort, resolve_effort
from uni_llm_client._errors import IncompleteResponseError, RefusalError
from uni_llm_client.providers._base import Provider, http_error
from uni_llm_client.providers.anthropic._models import (
    DEFAULT_WEB_SEARCH_TOOL,
    lookup_model,
)

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# Output tokens reserved for the answer. Token-budget models add their thinking
# budget on top, since the budget must be lower than max_tokens.
MAX_TOKENS = 16_000

# Thinking budgets for token-budget models; MAX uses the model's full output limit.
BUDGET_TOKENS = {Effort.LOW: 1_024, Effort.MEDIUM: 8_192, Effort.HIGH: 16_384}

_THINKING_BLOCKS = frozenset({"thinking", "redacted_thinking"})


class AnthropicProvider(Provider):
    name = "anthropic"
    api_key_env = "ANTHROPIC_API_KEY"

    def build_request(
        self, model: str, question: str, *, web_search: bool, effort: Effort | None
    ) -> httpx.Request:
        info = lookup_model(model)
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": question}],
        }
        if effort is not None:
            if info is not None:
                effort = resolve_effort(effort, info.efforts)
            if info is not None and info.thinking == "budget":
                budget = BUDGET_TOKENS.get(effort, info.max_output_tokens - MAX_TOKENS)
                body["max_tokens"] = budget + MAX_TOKENS
                body["thinking"] = {"type": "enabled", "budget_tokens": budget}
            else:
                body["thinking"] = {"type": "adaptive"}
                body["output_config"] = {"effort": effort.value}
        if web_search:
            tool = info.web_search_tool if info else DEFAULT_WEB_SEARCH_TOOL
            body["tools"] = [{"type": tool, "name": "web_search"}]
        return self._request(body)

    def parse_response(self, response: httpx.Response) -> str | httpx.Request:
        if response.is_error:
            raise http_error(response.status_code, _error_message(response))
        message = response.json()
        match message["stop_reason"]:
            case "pause_turn":
                # A server tool loop hit its iteration limit: re-send the turn so
                # far and the server resumes where it left off.
                body = json.loads(response.request.content)
                body["messages"].append(
                    {"role": "assistant", "content": message["content"]}
                )
                return self._request(body)
            case "max_tokens":
                raise IncompleteResponseError(
                    "Reached the output token limit before the answer was complete"
                )
            case "refusal":
                details = message.get("stop_details") or {}
                raise RefusalError(
                    details.get("explanation") or "The model declined to answer"
                )
        answer = _final_text(message["content"])
        if not answer:
            raise IncompleteResponseError("The response contained no answer text")
        return answer

    def _request(self, body: dict[str, Any]) -> httpx.Request:
        headers = {"x-api-key": self.api_key, "anthropic-version": API_VERSION}
        return httpx.Request("POST", API_URL, headers=headers, json=body)


def _final_text(content: list[dict[str, Any]]) -> str:
    """Join the text blocks after the last tool block, skipping any preamble."""
    texts: list[str] = []
    for block in content:
        if block["type"] == "text":
            texts.append(block["text"])
        elif block["type"] not in _THINKING_BLOCKS:
            texts.clear()
    return "".join(texts)


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])
    except (ValueError, KeyError, TypeError):
        return response.text or f"HTTP {response.status_code}"
