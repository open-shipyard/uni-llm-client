# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""The interface every vendor implements."""

from abc import ABC, abstractmethod
from typing import ClassVar

import httpx

from uni_llm_client._effort import Effort
from uni_llm_client._errors import AuthenticationError, ProviderError, RateLimitError

# Upper bound on requests per question, including follow-ups for paused turns.
MAX_REQUESTS = 6


class Provider(ABC):
    """Translates the generic API into one vendor's HTTP API.

    Implementations do no I/O: `Client` and `AsyncClient` send the requests
    they build, so a single implementation serves both.
    """

    name: ClassVar[str]
    """Model id prefix, e.g. ``"anthropic"`` in ``"anthropic/claude-opus-5"``."""

    api_key_env: ClassVar[str]
    """Environment variable read when no API key is passed to the client."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @abstractmethod
    def build_request(
        self, model: str, question: str, *, web_search: bool, effort: Effort | None
    ) -> httpx.Request:
        """Build the request that asks `model` the `question`."""

    @abstractmethod
    def parse_response(self, response: httpx.Response) -> str | httpx.Request:
        """Return the answer, or a follow-up request if the vendor paused the turn."""


def http_error(status_code: int, message: str) -> ProviderError:
    """Map an HTTP error status to the matching library error."""
    if status_code in (401, 403):
        return AuthenticationError(message, status_code=status_code)
    if status_code == 429:
        return RateLimitError(message, status_code=status_code)
    return ProviderError(message, status_code=status_code)
