# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""OpenRouter Chat Completions API, which serves models from many vendors."""

from typing import Any, NoReturn

import httpx

from uni_llm_client._effort import Effort
from uni_llm_client._errors import IncompleteResponseError, ProviderError, RefusalError
from uni_llm_client.providers._base import Provider, http_error

API_URL = "https://openrouter.ai/api/v1/chat/completions"

_REFUSAL_ERROR_TYPES = frozenset({"refusal", "content_policy_violation"})


class OpenRouterProvider(Provider):
    name = "openrouter"
    api_key_env = "OPENROUTER_API_KEY"

    def build_request(
        self, model: str, question: str, *, web_search: bool, effort: Effort | None
    ) -> httpx.Request:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": question}],
        }
        if effort is not None:
            # OpenRouter maps the effort to the nearest level the model supports.
            body["reasoning"] = {"effort": effort.value}
        if web_search:
            body["tools"] = [{"type": "openrouter:web_search"}]
        headers = {"Authorization": f"Bearer {self.api_key}"}
        return httpx.Request("POST", API_URL, headers=headers, json=body)

    def parse_response(self, response: httpx.Response) -> str:
        if response.is_error:
            _raise(_error_body(response), response.status_code)
        body = response.json()
        # Failures after generation starts still return HTTP 200.
        if "error" in body:
            _raise(body["error"], body["error"].get("code"))
        choice = body["choices"][0]
        message = choice["message"]
        match choice["finish_reason"]:
            case "error":
                _raise(choice["error"], choice["error"].get("code"))
            case "length":
                raise IncompleteResponseError(
                    "Reached the output token limit before the answer was complete"
                )
            case "content_filter":
                raise RefusalError(
                    message.get("refusal") or "The model declined to answer"
                )
        if message.get("refusal"):
            raise RefusalError(message["refusal"])
        answer = _text(message.get("content"))
        if not answer:
            raise IncompleteResponseError("The response contained no answer text")
        return answer


def _text(content: str | list[dict[str, Any]] | None) -> str:
    if isinstance(content, list):
        return "".join(part["text"] for part in content if part["type"] == "text")
    return content or ""


def _error_body(response: httpx.Response) -> dict[str, Any]:
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        return {"message": response.text or f"HTTP {response.status_code}"}
    return error if isinstance(error, dict) else {"message": str(error)}


def _raise(error: dict[str, Any], status_code: object) -> NoReturn:
    code = status_code if isinstance(status_code, int) else None
    message = str(error.get("message") or "Unknown error")
    error_type = (error.get("metadata") or {}).get("error_type")
    # OpenRouter uses 403 for guardrail, moderation and model refusals.
    if code == 403 or error_type in _REFUSAL_ERROR_TYPES:
        raise RefusalError(message)
    if code is None:
        raise ProviderError(message)
    raise http_error(code, message)
