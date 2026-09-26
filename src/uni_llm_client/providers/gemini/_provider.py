# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Gemini API ``generateContent`` method."""

from typing import Any

import httpx

from uni_llm_client._effort import BUDGET_TOKENS, Effort
from uni_llm_client._errors import (
    AuthenticationError,
    IncompleteResponseError,
    ProviderError,
    RefusalError,
)
from uni_llm_client.providers._base import Provider, http_error
from uni_llm_client.providers.gemini._models import MAX_THINKING_BUDGETS

API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Gemini 3.x has no thinking level above high.
THINKING_LEVELS = {
    Effort.LOW: "low",
    Effort.MEDIUM: "medium",
    Effort.HIGH: "high",
    Effort.MAX: "high",
}

_REFUSAL_REASONS = frozenset(
    {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}
)


class GeminiProvider(Provider):
    name = "gemini"
    api_key_env = "GEMINI_API_KEY"

    def build_request(
        self, model: str, question: str, *, web_search: bool, effort: Effort | None
    ) -> httpx.Request:
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": question}]}]
        }
        if effort is not None:
            max_budget = MAX_THINKING_BUDGETS.get(model)
            thinking: dict[str, Any]
            if max_budget is None:
                thinking = {"thinkingLevel": THINKING_LEVELS[effort]}
            else:
                thinking = {"thinkingBudget": BUDGET_TOKENS.get(effort, max_budget)}
            body["generationConfig"] = {"thinkingConfig": thinking}
        if web_search:
            body["tools"] = [{"googleSearch": {}}]
        url = f"{API_URL}/{model}:generateContent"
        headers = {"x-goog-api-key": self.api_key}
        return httpx.Request("POST", url, headers=headers, json=body)

    def parse_response(self, response: httpx.Response) -> str:
        if response.is_error:
            raise _http_error(response)
        body = response.json()
        # A blocked prompt gets no candidates.
        block_reason = (body.get("promptFeedback") or {}).get("blockReason")
        if block_reason:
            raise RefusalError(f"The prompt was blocked: {block_reason}")
        candidate = body["candidates"][0]
        match candidate.get("finishReason"):
            case "STOP" | None:
                pass
            case "MAX_TOKENS":
                raise IncompleteResponseError(
                    "Reached the output token limit before the answer was complete"
                )
            case reason if reason in _REFUSAL_REASONS:
                raise RefusalError(
                    candidate.get("finishMessage") or "The model declined to answer"
                )
            case reason:
                raise IncompleteResponseError(f"Generation stopped early: {reason}")
        parts = (candidate.get("content") or {}).get("parts") or []
        answer = "".join(
            part["text"] for part in parts if "text" in part and not part.get("thought")
        )
        if not answer:
            raise IncompleteResponseError("The response contained no answer text")
        return answer


def _http_error(response: httpx.Response) -> ProviderError:
    try:
        error = response.json()["error"]
        message = str(error["message"])
    except (ValueError, KeyError, TypeError):
        message = response.text or f"HTTP {response.status_code}"
        return http_error(response.status_code, message)
    # Invalid API keys get HTTP 400 rather than 401.
    reasons = {detail.get("reason") for detail in error.get("details") or []}
    if "API_KEY_INVALID" in reasons:
        return AuthenticationError(message, status_code=response.status_code)
    return http_error(response.status_code, message)
