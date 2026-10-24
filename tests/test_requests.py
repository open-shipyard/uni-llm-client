# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import MockVendor, VendorCall, call

HERE = Path(__file__).parent
PAYLOADS = HERE / "reusable_payloads"
API_KEYS = {"anthropic": "test-key", "openrouter": "test-key"}
CALLS = ("ask", "complete", "stream")
CASES = [
    case
    for path in sorted((HERE / "cases").glob("*.json"))
    for case in json.loads(path.read_text())
]


def payload(name: str) -> Any:
    return json.loads((PAYLOADS / f"{name}.json").read_text())


def replayed(value: Any, replies: list[dict[str, Any]]) -> Any:
    """`value` with each ``{"$reply_message": N}`` replaced by the message step N
    returned, so that a step sends back what the implementation gave it."""
    if isinstance(value, dict):
        if value.keys() == {"$reply_message"}:
            reply = replies[value["$reply_message"]]
            response = (
                reply["response"]
                if "response" in reply
                else reply["events"][-1]["response"]
            )
            return response["message"]
        return {key: replayed(item, replies) for key, item in value.items()}
    if isinstance(value, list):
        return [replayed(item, replies) for item in value]
    return value


def arguments_parsed(value: Any) -> Any:
    """`value` with the JSON text under ``arguments`` parsed, since ports format
    that text differently."""
    if isinstance(value, dict):
        return {
            key: json.loads(item)
            if key == "arguments" and isinstance(item, str)
            else arguments_parsed(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [arguments_parsed(item) for item in value]
    return value


def sent(vendor_call: VendorCall, expected: dict[str, Any] | None) -> dict[str, Any]:
    """The parts of the call that `expected` describes. Its headers are a subset."""
    keys = expected["headers"] if expected else vendor_call.headers
    return {
        "method": vendor_call.method,
        "url": vendor_call.url,
        "headers": {key: vendor_call.headers.get(key) for key in keys},
        "json": arguments_parsed(vendor_call.json),
    }


def without_error_message(reply: dict[str, Any]) -> dict[str, Any]:
    """Error messages differ between ports; only the type is shared."""
    if isinstance(reply.get("error"), dict):
        return {**reply, "error": {"type": reply["error"].get("type")}}
    return reply


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_sends_the_expected_vendor_requests(
    implementation: str, vendor: MockVendor, case: dict[str, Any]
) -> None:
    replies: list[dict[str, Any]] = []
    for number, step in enumerate(case["steps"]):
        (name,) = [key for key in CALLS if key in step]
        vendor.serve([payload(exchange["response"]) for exchange in step["vendor"]])

        args = replayed(payload(step[name]), replies)
        reply = call(implementation, name, {"api_keys": API_KEYS, **args})
        replies.append(reply)

        expected = [
            arguments_parsed(payload(exchange["request"]))
            for exchange in step["vendor"]
        ]
        # Extra calls are compared whole; missing ones show as a shorter list.
        padded = expected + [None] * (len(vendor.calls) - len(expected))
        calls = [sent(c, e) for c, e in zip(vendor.calls, padded, strict=False)]
        assert calls == expected, f"step {number}: vendor requests"
        expected_reply = payload(step["reply"])
        assert without_error_message(reply) == expected_reply, f"step {number}: reply"
