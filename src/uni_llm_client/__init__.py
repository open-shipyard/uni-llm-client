# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Abstract LLM APIs behind a common signature."""

from importlib.metadata import version

from uni_llm_client._async_client import AsyncClient
from uni_llm_client._client import Client
from uni_llm_client._effort import Effort
from uni_llm_client._errors import (
    AuthenticationError,
    IncompleteResponseError,
    ProviderError,
    RateLimitError,
    RefusalError,
    UniLLMError,
)

__version__ = version("uni-llm-client")

__all__ = [
    "AsyncClient",
    "AuthenticationError",
    "Client",
    "Effort",
    "IncompleteResponseError",
    "ProviderError",
    "RateLimitError",
    "RefusalError",
    "UniLLMError",
    "__version__",
]
