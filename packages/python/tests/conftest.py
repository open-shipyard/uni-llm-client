# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""The models the live tests ask, one test run per model."""

import pytest

MODELS = [
    "anthropic/claude-opus-5",
    "anthropic/claude-haiku-4-5",
    "openrouter/anthropic/claude-haiku-4.5",
]


@pytest.fixture(params=MODELS)
def model(request: pytest.FixtureRequest) -> str:
    return str(request.param)
