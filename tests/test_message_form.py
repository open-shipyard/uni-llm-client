# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Which malformed messages are refused before they reach the vendor (MSG-12).

Each row is the one message of a `complete` call. The client refuses it with
`invalid_argument`.
"""

from typing import Any

import pytest

from conftest import MockVendor, call, payload

TEXT = {"type": "text", "text": "What is the capital of France?"}


def user(*blocks: Any) -> dict[str, Any]:
    return {"role": "user", "content": list(blocks)}


@pytest.mark.parametrize(
    "message",
    [
        pytest.param("What is the capital of France?", id="not-an-object"),
        pytest.param({**user(TEXT), "role": "system"}, id="unknown-role"),
        pytest.param({"content": [TEXT]}, id="no-role"),
        pytest.param({**user(), "content": TEXT["text"]}, id="content-as-text"),
        pytest.param(user(TEXT["text"]), id="block-not-an-object"),
        pytest.param(user({"text": TEXT["text"]}), id="block-without-type"),
        pytest.param(user({**TEXT, "type": "image"}), id="unknown-block-type"),
        pytest.param(user({"type": "text"}), id="block-missing-a-field"),
        pytest.param(user({**TEXT, "cache": True}), id="block-unknown-field"),
        pytest.param(user({**TEXT, "text": 1}), id="field-of-another-type"),
        pytest.param({**user(TEXT), "vendor": {"kind": "anthropic"}}, id="vendor"),
    ],
)
def test_refuses_a_malformed_message(
    implementation: str, vendor: MockVendor, message: Any
) -> None:
    vendor.serve([])
    args = payload("uni-llm-client/request/complete_paris_question")
    args["messages"] = [message]

    reply = call(implementation, "complete", args)

    assert vendor.calls == []
    assert reply["error"]["type"] == "invalid_argument"
