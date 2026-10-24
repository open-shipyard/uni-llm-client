# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Checks for a step run against the real vendor.

A real model answers in its own words, so a live reply is checked against the
case's mocked reply for what must hold: the stop reason, the tools called and
their arguments, and the invariants of a stream.
"""

import json
from typing import Any

from conftest import VendorCall


def check_live_step(
    name: str, reply: dict[str, Any], expected: dict[str, Any], calls: list[VendorCall]
) -> None:
    for vendor_call in calls:
        assert vendor_call.status < 400, (
            f"the vendor rejected the request with {vendor_call.status}: "
            f"{vendor_call.error_body}"
        )
    assert "error" not in reply, reply
    if name == "ask":
        assert reply["answer"].strip(), "empty answer"
    elif name == "complete":
        check_response(reply["response"], expected["response"])
    else:
        check_stream(reply["events"])
        check_response(
            reply["events"][-1]["response"], expected["events"][-1]["response"]
        )


def check_response(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    expected_calls = blocks(expected, "tool_use")
    actual_calls = blocks(actual, "tool_use")
    if expected_calls and not actual_calls:
        names = ", ".join(call["name"] for call in expected_calls)
        raise AssertionError(f"the model did not call {names}: {actual['message']}")
    assert actual["stop_reason"] == expected["stop_reason"], actual
    assert [c["name"] for c in actual_calls] == [c["name"] for c in expected_calls]
    for actual_call, expected_call in zip(actual_calls, expected_calls, strict=True):
        check_input(actual_call["input"], expected_call["input"])
    if text_of(expected):
        assert text_of(actual).strip(), "the model wrote no text"
    message = actual["message"]
    assert message["role"] == "assistant"
    assert message["vendor"]["kind"] == expected["message"]["vendor"]["kind"]
    assert actual["usage"]["input_tokens"] > 0, actual["usage"]
    assert actual["usage"]["output_tokens"] > 0, actual["usage"]


def check_input(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Same keys; a text value contains the expected one, as "Lyon, France" does."""
    assert actual.keys() == expected.keys(), actual
    for key, value in expected.items():
        if isinstance(value, str):
            assert value.lower() in str(actual[key]).lower(), actual
        else:
            assert actual[key] == value, actual


def check_stream(events: list[dict[str, Any]]) -> None:
    """STREAM-2 and STREAM-3: the order of the events, and the pieces add up."""
    types = [event["type"] for event in events]
    assert types.count("completed") == 1 and types[-1] == "completed", types
    response = events[-1]["response"]
    assert joined(events, "text_delta") == text_of(response)
    reasoning = "".join(b["text"] for b in blocks(response, "reasoning"))
    assert joined(events, "reasoning_delta") == reasoning
    started: dict[str, list[str]] = {}
    ended = []
    for event in events:
        match event["type"]:
            case "tool_use_start":
                assert event["id"] not in started, event
                started[event["id"]] = []
            case "tool_use_delta":
                started[event["id"]].append(event["partial_json"])
            case "tool_use_end":
                block = event["block"]
                pieces = "".join(started.pop(block["id"]))
                assert json.loads(pieces or "{}") == block["input"], block
                ended.append(block)
    assert not started, f"tool calls without an end: {started}"
    assert ended == blocks(response, "tool_use")


def blocks(response: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [b for b in response["message"]["content"] if b["type"] == kind]


def text_of(response: dict[str, Any]) -> str:
    return "".join(b["text"] for b in blocks(response, "text"))


def joined(events: list[dict[str, Any]], kind: str) -> str:
    return "".join(event["text"] for event in events if event["type"] == kind)
