# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import MockVendor, VendorCall, ask

HERE = Path(__file__).parent
PAYLOADS = HERE / "reusable_payloads"
API_KEYS = {"anthropic": "test-key", "openrouter": "test-key"}
CASES = [
    case
    for path in sorted((HERE / "cases").glob("*.json"))
    for case in json.loads(path.read_text())
]


def payload(name: str) -> Any:
    return json.loads((PAYLOADS / f"{name}.json").read_text())


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
    vendor.serve([payload(exchange["response"]) for exchange in case["vendor"]])

    reply = ask(implementation, {"api_keys": API_KEYS, **payload(case["ask"])})

    expected = [payload(exchange["request"]) for exchange in case["vendor"]]
    # Extra calls are compared whole; missing ones show as a shorter list.
    padded = expected + [None] * (len(vendor.calls) - len(expected))
    calls = [sent(c, e) for c, e in zip(vendor.calls, padded, strict=False)]
    assert calls == expected
    expected_reply = payload(case["reply"])
    if "error" in expected_reply:
        # Error messages differ between ports; only the type is shared.
        error_type = reply.get("error", {}).get("type")
        assert error_type == expected_reply["error"]["type"], reply
    else:
        assert reply == expected_reply
