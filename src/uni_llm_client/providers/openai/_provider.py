# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""OpenAI Responses API."""

from typing import Any, NoReturn

import httpx

from uni_llm_client._effort import Effort, resolve_effort
from uni_llm_client._errors import (
    IncompleteResponseError,
    ProviderError,
    RateLimitError,
    RefusalError,
)
from uni_llm_client.providers._base import Provider, http_error
from uni_llm_client.providers.openai._models import lookup_model

API_URL = "https://api.openai.com/v1/responses"

# Error codes for prompts or answers that violate OpenAI's usage policies.
_REFUSAL_CODES = frozenset(
    {"invalid_prompt", "bio_policy", "misalignment_policy_violation"}
)


class OpenAIProvider(Provider):
    name = "openai"
    api_key_env = "OPENAI_API_KEY"

    def build_request(
        self, model: str, question: str, *, web_search: bool, effort: Effort | None
    ) -> httpx.Request:
        body: dict[str, Any] = {"model": model, "input": question}
        if effort is not None:
            efforts = lookup_model(model)
            value = (
                efforts[resolve_effort(effort, efforts)] if efforts else effort.value
            )
            body["reasoning"] = {"effort": value}
        if web_search:
            body["tools"] = [{"type": "web_search"}]
        headers = {"Authorization": f"Bearer {self.api_key}"}
        return httpx.Request("POST", API_URL, headers=headers, json=body)

    def parse_response(self, response: httpx.Response) -> str:
        if response.is_error:
            _raise(_error_body(response), response.status_code)
        body = response.json()
        match body["status"]:
            case "failed":
                _raise(body.get("error") or {}, None)
            case "incomplete":
                reason = (body.get("incomplete_details") or {}).get("reason")
                if reason == "content_filter":
                    raise RefusalError("The model declined to answer")
                if reason == "max_output_tokens":
                    raise IncompleteResponseError(
                        "Reached the output token limit before the answer was complete"
                    )
                raise IncompleteResponseError(f"The response is incomplete: {reason}")
        answer = _final_text(body["output"])
        if not answer:
            raise IncompleteResponseError("The response contained no answer text")
        return answer


def _final_text(output: list[dict[str, Any]]) -> str:
    """Join the message text after the last tool call, skipping any preamble."""
    texts: list[str] = []
    for item in output:
        if item["type"] == "message":
            if item.get("phase") == "commentary":
                continue
            for part in item["content"]:
                if part["type"] == "refusal":
                    raise RefusalError(part["refusal"])
                if part["type"] == "output_text":
                    texts.append(part["text"])
        elif item["type"] != "reasoning":
            texts.clear()
    return "".join(texts)


def _error_body(response: httpx.Response) -> dict[str, Any]:
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        return {"message": response.text or f"HTTP {response.status_code}"}
    return error if isinstance(error, dict) else {"message": str(error)}


def _raise(error: dict[str, Any], status_code: int | None) -> NoReturn:
    message = str(error.get("message") or "Unknown error")
    code = error.get("code")
    if code in _REFUSAL_CODES:
        raise RefusalError(message)
    if status_code is not None:
        raise http_error(status_code, message)
    # Failed responses carry no HTTP error status.
    if code == "rate_limit_exceeded":
        raise RateLimitError(message)
    raise ProviderError(message)
