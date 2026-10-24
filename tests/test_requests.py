# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import MockVendor, VendorCall, ask

HERE = Path(__file__).parent
API_KEYS = {"anthropic": "test-key", "openrouter": "test-key"}
CASES = [
    case
    for path in sorted((HERE / "cases").glob("*.json"))
    for case in json.loads(path.read_text())
]


def sent(call: VendorCall, expected: dict[str, Any] | None) -> dict[str, Any]:
    """The parts of `call` that `expected` describes; only its headers are a subset."""
    keys = expected["headers"] if expected else call.headers
    return {
        "method": call.method,
        "url": call.url,
        "headers": {key: call.headers.get(key) for key in keys},
        "json": call.json,
    }


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_sends_the_expected_vendor_requests(
    implementation: str, vendor: MockVendor, case: dict[str, Any]
) -> None:
    if "responses" in case:
        path = HERE / "vendor_responses" / f"{case['responses']}.json"
        vendor.serve(json.loads(path.read_text()))

    reply = ask(implementation, {"api_keys": API_KEYS, **case["ask"]})

    expected = case["requests"]
    # Extra calls are compared whole; missing ones show as a shorter list.
    padded = expected + [None] * (len(vendor.calls) - len(expected))
    calls = [sent(c, e) for c, e in zip(vendor.calls, padded, strict=False)]
    assert calls == expected
    if "error" in case:
        assert reply.get("error", {}).get("type") == case["error"], reply
    else:
        assert reply == {"answer": case["answer"]}
