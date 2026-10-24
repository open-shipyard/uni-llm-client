# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""The retry policy's pure functions: which errors are retried, and how long the
clients wait. The HTTP tests cover the retries themselves."""

from email.utils import formatdate

import httpx2
import pytest

from uni_llm_client import (
    AuthenticationError,
    IncompleteResponseError,
    ProviderError,
    RateLimitError,
    RefusalError,
    TransportError,
    UniLLMError,
)
from uni_llm_client._retry import RetryPolicy, backoff, is_retryable, retry_after

NOW = 1_800_000_000.0  # Fri, 15 Jan 2027 08:00:00 GMT
RATE_LIMITED = RateLimitError("Rate limit exceeded", status_code=429)


def delay(headers: dict[str, str]) -> float | None:
    """The policy's delay before the second retry, after a rate limit whose
    response has `headers`; without jitter, so that a backoff is 1 s."""
    response = httpx2.Response(429, headers=headers)
    return RetryPolicy().delay(RATE_LIMITED, 1, response, now=NOW, jitter=0)


@pytest.mark.parametrize(
    ("error", "retryable"),
    [
        pytest.param(RATE_LIMITED, True, id="429"),
        pytest.param(ProviderError("", status_code=408), True, id="408"),
        pytest.param(ProviderError("", status_code=409), True, id="409"),
        pytest.param(ProviderError("", status_code=500), True, id="500"),
        pytest.param(ProviderError("", status_code=502), True, id="502"),
        pytest.param(ProviderError("", status_code=503), True, id="503"),
        pytest.param(ProviderError("", status_code=529), True, id="529"),
        pytest.param(TransportError("Connection refused"), True, id="transport"),
        pytest.param(ProviderError("", status_code=400), False, id="400"),
        pytest.param(ProviderError("", status_code=404), False, id="404"),
        pytest.param(ProviderError("", status_code=413), False, id="413"),
        pytest.param(AuthenticationError("", status_code=401), False, id="401"),
        pytest.param(AuthenticationError("", status_code=403), False, id="403"),
        pytest.param(ProviderError("Unknown stop reason"), False, id="no-status"),
        pytest.param(RefusalError("Declined"), False, id="refusal"),
        pytest.param(IncompleteResponseError("Cut"), False, id="incomplete"),
    ],
)
def test_retries_only_what_may_pass_on_another_attempt(
    error: UniLLMError, retryable: bool
) -> None:
    assert is_retryable(error) is retryable


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
