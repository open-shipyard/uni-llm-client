# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Calls the real vendor APIs. Opt in with ``pytest -m live``; costs money."""

import os
from collections.abc import Iterator

import pytest

from uni_llm_client import Client, Effort
from uni_llm_client._registry import PROVIDERS

pytestmark = pytest.mark.live

QUESTION = "What is the capital of France? Answer with one word."


@pytest.fixture
def client(model: str) -> Iterator[Client]:
    api_key_env = PROVIDERS[model.partition("/")[0]].api_key_env
    if not os.environ.get(api_key_env):
        pytest.skip(f"{api_key_env} is not set")
    with Client() as client:
        yield client


@pytest.mark.parametrize("effort", [Effort.LOW, Effort.MEDIUM])
def test_answers(client: Client, model: str, effort: Effort) -> None:
    assert "paris" in client.ask(model, QUESTION, effort=effort).lower()


def test_answers_with_web_search(client: Client, model: str) -> None:
    assert "paris" in client.ask(model, QUESTION, web_search=True).lower()
