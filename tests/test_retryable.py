# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Which failed attempts the clients send again (RETRY-2).

Each row is a vendor's first answer. The client gets one retry, and the vendor
answers it, so a retried failure costs two vendor requests and a final one costs
one.
"""

from typing import Any

import pytest

from conftest import MockVendor, call
from test_requests import API_KEYS, payload

QUESTIONS = {
    "anthropic": "uni-llm-client/request/opus_5_question",
    "openrouter": "uni-llm-client/request/openrouter_gpt_oss_20b_question",
}
RETRIED_STATUSES = [408, 409, 429, 500, 502, 503, 529]
FINAL_STATUSES = [400, 401, 403, 404, 413]


def with_status(kind: str, status: int) -> dict[str, Any]:
    """The vendor's error response, with `status` and no wait."""
    response: dict[str, Any] = payload(f"{kind}/response/rate_limit")
    response["status"] = status
    if kind == "openrouter":
        response["body"]["error"]["code"] = status
    return response


def in_the_body(status: int) -> dict[str, Any]:
    """An OpenRouter error in the body of a 200, with `status` as its code."""
    response: dict[str, Any] = payload("openrouter/response/server_error")
    response["body"]["choices"][0]["error"]["code"] = status
    return response


ROWS = [
    *(
        pytest.param(kind, with_status(kind, status), retried, id=f"{kind}-{status}")
        for kind in QUESTIONS
        for statuses, retried in ((RETRIED_STATUSES, True), (FINAL_STATUSES, False))
        for status in statuses
    ),
    *(
        pytest.param("openrouter", in_the_body(status), retried, id=f"body-{status}")
        for status, retried in ((429, True), (502, True), (400, False))
    ),
    pytest.param("anthropic", {"disconnect": True}, True, id="disconnect"),
    *(
        pytest.param(kind, payload(f"{kind}/response/{name}"), False, id=name)
        for kind, name in (
            ("anthropic", "refusal"),
            ("anthropic", "max_tokens"),
            ("anthropic", "unknown_stop_reason"),
            ("openrouter", "truncated"),
        )
    ),
]


@pytest.mark.parametrize(("kind", "first", "retried"), ROWS)
def test_retries_only_what_may_pass_on_another_attempt(
    implementation: str,
    vendor: MockVendor,
    kind: str,
    first: dict[str, Any],
    retried: bool,
) -> None:
    vendor.serve([first, payload(f"{kind}/response/answer")])
    args = {"api_keys": API_KEYS, **payload(QUESTIONS[kind]), "max_retries": 1}

    reply = call(implementation, "ask", args)

    assert len(vendor.calls) == (2 if retried else 1)
    assert ("error" in reply) is not retried
