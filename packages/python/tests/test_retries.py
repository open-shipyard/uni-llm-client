# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""How long the clients wait before a retry. The HTTP tests cover which errors
are retried, and the retries themselves."""

from email.utils import formatdate

import httpx2
import pytest

from uni_llm_client import RateLimitError
from uni_llm_client._retry import RetryPolicy, backoff, retry_after

NOW = 1_800_000_000.0  # Fri, 15 Jan 2027 08:00:00 GMT
RATE_LIMITED = RateLimitError("Rate limit exceeded", status_code=429)


def delay(headers: dict[str, str]) -> float | None:
    """The policy's delay before the second retry, after a rate limit whose
    response has `headers`; without jitter, so that a backoff is 1 s."""
    response = httpx2.Response(429, headers=headers)
    return RetryPolicy().delay(RATE_LIMITED, 1, response, now=NOW, jitter=0)


@pytest.mark.parametrize(
    ("retries", "longest"),
    [(0, 0.5), (1, 1.0), (2, 2.0), (3, 4.0), (4, 8.0), (5, 8.0), (10_000, 8.0)],
)
def test_backs_off_exponentially_up_to_8_seconds_with_jitter(
    retries: int, longest: float
) -> None:
    assert backoff(retries, jitter=0) == longest
    for jitter in (0.25, 0.5, 0.999):
        assert 0.75 * longest < backoff(retries, jitter) < longest


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"retry-after": "0"}, 0.0),
        ({"retry-after": "7"}, 7.0),
        ({"retry-after": "1.5"}, 1.5),
        ({"retry-after": "60"}, 60.0),
        ({"Retry-After": "7"}, 7.0),
        ({"retry-after-ms": "250"}, 0.25),
        ({"retry-after-ms": "0"}, 0.0),
        ({"retry-after-ms": "250", "retry-after": "7"}, 0.25),
        ({"retry-after-ms": "soon", "retry-after": "7"}, 7.0),
        ({"retry-after": formatdate(NOW + 30, usegmt=True)}, 30.0),
        ({"retry-after": formatdate(NOW + 60, usegmt=True)}, 60.0),
    ],
)
def test_waits_as_long_as_the_vendor_asks(
    headers: dict[str, str], expected: float
) -> None:
    assert delay(headers) == pytest.approx(expected)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"retry-after": "61"},
        {"retry-after": "3600"},
        {"retry-after-ms": "60001"},
        {"retry-after": "-1"},
        {"retry-after": "nan"},
        {"retry-after": "inf"},
        {"retry-after": "soon"},
        {"retry-after": ""},
        {"retry-after": formatdate(NOW + 61, usegmt=True)},
        {"retry-after": formatdate(NOW - 5, usegmt=True)},
    ],
)
def test_backs_off_when_the_vendor_asks_for_too_long_or_nothing_readable(
    headers: dict[str, str],
) -> None:
    assert delay(headers) == backoff(1, jitter=0)


def test_reads_an_http_date_in_any_zone() -> None:
    in_utc = formatdate(NOW + 30, usegmt=True)  # "... GMT"
    unknown_zone = formatdate(NOW + 30)  # "... -0000", which is UTC
    in_paris = "Fri, 15 Jan 2027 09:00:30 +0100"

    assert retry_after({"retry-after": in_utc}, NOW) == 30
    assert retry_after({"retry-after": unknown_zone}, NOW) == 30
    assert retry_after({"retry-after": in_paris}, NOW) == 30
