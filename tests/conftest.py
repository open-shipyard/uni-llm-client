# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Fixtures that run each test for every model in MODELS, sync and async.

Tests only use the public API. Vendor-specific data lives in
``fixtures/<provider>/<scenario>.json``: the responses a vendor returns for a
scenario, served in order. Tests are skipped for vendors without that scenario.
"""

import asyncio
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import httpx
import pytest

from uni_llm_client import AsyncClient, Client
from uni_llm_client._registry import PROVIDERS

MODELS = [
    "anthropic/claude-opus-5",
    "anthropic/claude-haiku-4-5",
    "gemini/gemini-3.8-flash",
    "gemini/gemini-2.5-flash",
    "openai/gpt-5.6-sol",
    "openrouter/anthropic/claude-haiku-4.5",
]

FIXTURES = Path(__file__).parent / "fixtures"
TEST_API_KEYS = {name: "test-key" for name in PROVIDERS}

Ask = Callable[..., str]


class FakeVendor:
    """Serves recorded vendor responses and records the requests it receives."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self._responses: list[dict[str, Any]] = []

    def serve(self, model: str, scenario: str) -> None:
        provider = model.partition("/")[0]
        path = FIXTURES / provider / f"{scenario}.json"
        if not path.exists():
            pytest.skip(f"{provider} has no {scenario!r} scenario")
        self._responses = json.loads(path.read_text())

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        recorded = self._responses.pop(0)
        return httpx.Response(recorded["status"], json=recorded["body"])


@pytest.fixture(params=MODELS)
def model(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.fixture
def vendor() -> FakeVendor:
    return FakeVendor()


@pytest.fixture(params=["sync", "async"])
def ask(request: pytest.FixtureRequest, vendor: FakeVendor) -> Ask:
    """Call `ask` on a `Client` or `AsyncClient` wired to the fake vendor."""
    transport = httpx.MockTransport(vendor.handle)

    def ask_sync(
        model: str,
        question: str,
        api_keys: Mapping[str, str] | None = TEST_API_KEYS,
        **kwargs: Any,
    ) -> str:
        http_client = httpx.Client(transport=transport)
        with Client(api_keys=api_keys, http_client=http_client) as client:
            return client.ask(model, question, **kwargs)

    def ask_async(
        model: str,
        question: str,
        api_keys: Mapping[str, str] | None = TEST_API_KEYS,
        **kwargs: Any,
    ) -> str:
        async def run() -> str:
            http_client = httpx.AsyncClient(transport=transport)
            async with AsyncClient(
                api_keys=api_keys, http_client=http_client
            ) as client:
                return await client.ask(model, question, **kwargs)

        return asyncio.run(run())

    return ask_sync if request.param == "sync" else ask_async
