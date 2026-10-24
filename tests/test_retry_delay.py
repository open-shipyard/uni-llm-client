# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""How long the clients wait before a retry (RETRY-3, RETRY-4).

The clients get waits short enough for a test run. The mock vendor records when
each request arrives, and a wait is the gap between two attempts. A wait never
ends early, so its lower bound is exact; `SLACK` leaves room for the machine.
"""

import email.utils
import itertools
from datetime import UTC
from typing import Any

import pytest

from conftest import API_KEYS, MockVendor, call, payload

SLACK = 0.05
QUESTION = "uni-llm-client/request/opus_5_question"
# A backoff of 0.1875 to 0.25 s, and up to 0.1 s for a vendor to ask: far
# enough apart that a wait never passes for the other.
WAITS = {"initial_retry_delay": 0.25, "max_retry_after": 0.1}
BACKOFF = (0.1875, 0.25)


def rate_limit(headers: dict[str, Any]) -> dict[str, Any]:
    response: dict[str, Any] = payload("anthropic/response/rate_limit")
    response["headers"] = headers
    return response


def ask(
    implementation: str,
    vendor: MockVendor,
    errors: list[dict[str, Any]],
    **options: Any,
) -> list[float]:
    """Ask once, the vendor failing with `errors` before it answers; return the
    waits between the vendor requests."""
    vendor.serve([*errors, payload("anthropic/response/answer")])
    args = {"api_keys": API_KEYS, **payload(QUESTION), **options}
    reply = call(implementation, "ask", {"max_retries": len(errors), **args})
    assert "answer" in reply
    times = [c.at for c in vendor.calls]
    return [later - earlier for earlier, later in itertools.pairwise(times)]


def within(wait: float, low: float, high: float) -> bool:
    return low <= wait <= high + SLACK


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        pytest.param({"retry-after": "0"}, (0, 0), id="zero"),
        pytest.param({"retry-after": "0.05"}, (0.05, 0.05), id="seconds"),
        pytest.param({"retry-after": "0.1"}, (0.1, 0.1), id="at-the-limit"),
        pytest.param({"retry-after-ms": "50"}, (0.05, 0.05), id="ms"),
        pytest.param(
            {"retry-after-ms": "0", "retry-after": "0.1"}, (0, 0), id="ms-first"
        ),
        pytest.param(
            {"retry-after-ms": "soon", "retry-after": "0.05"},
            (0.05, 0.05),
            id="unreadable-ms",
        ),
        pytest.param({"retry-after": "0.15"}, BACKOFF, id="over-the-limit"),
        pytest.param({}, BACKOFF, id="none"),
        pytest.param({"retry-after": "-1"}, BACKOFF, id="negative"),
        pytest.param(
            {"retry-after-ms": "nan", "retry-after": "0.05"}, (0.05, 0.05), id="nan-ms"
        ),
        pytest.param({"retry-after": "soon"}, BACKOFF, id="unreadable"),
        pytest.param(
            {"retry-after": "Wed, 21 Oct 2015 07:28:00 GMT"}, BACKOFF, id="past-date"
        ),
    ],
)
def test_waits_as_long_as_the_vendor_asks_up_to_a_limit(
    implementation: str,
    vendor: MockVendor,
    headers: dict[str, str],
    expected: tuple[float, float],
) -> None:
    (wait,) = ask(implementation, vendor, [rate_limit(headers)], **WAITS)

    assert within(wait, *expected), f"waited {wait:.3f} s"


@pytest.mark.parametrize("zone", ["GMT", "-0000"])
def test_waits_until_the_date_the_vendor_asks_for(
    implementation: str, vendor: MockVendor, zone: str
) -> None:
    # A backoff of 3 s, longer than any date the mock vendor sends.
    error = rate_limit({"retry-after": {"$http_date": zone}})
    ask(implementation, vendor, [error], initial_retry_delay=3, max_retry_after=2)

    first, retry = vendor.calls
    date = email.utils.parsedate_to_datetime(first.response_headers["retry-after"])
    if date.tzinfo is None:  # "-0000" is UTC
        date = date.replace(tzinfo=UTC)
    assert within(retry.at, date.timestamp(), date.timestamp())


def test_backs_off_exponentially_up_to_a_limit(
    implementation: str, vendor: MockVendor
) -> None:
    errors = [rate_limit({})] * 4
    waits = ask(
        implementation, vendor, errors, initial_retry_delay=0.05, max_retry_delay=0.2
    )

    # Each wait is up to a quarter shorter, at random.
    longest = [0.05, 0.1, 0.2, 0.2]
    assert all(
        within(wait, 0.75 * most, most)
        for wait, most in zip(waits, longest, strict=True)
    ), waits
