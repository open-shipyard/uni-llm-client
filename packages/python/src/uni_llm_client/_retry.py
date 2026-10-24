# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""When a failed attempt is sent again, and how long the client waits first.

Decisions only, without I/O or sleeping, so that one policy serves both clients
(``docs/specs/retries.md``).
"""

from __future__ import annotations

import email.utils
import math
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC

import httpx2

from uni_llm_client._errors import ProviderError, TransportError, UniLLMError

DEFAULT_MAX_RETRIES = 2

# RETRY-3 by default: from half a second, doubling, up to 8 seconds.
DEFAULT_INITIAL_RETRY_DELAY = 0.5
DEFAULT_MAX_RETRY_DELAY = 8.0

# RETRY-4 by default: the longest wait a vendor can ask for and get.
DEFAULT_MAX_RETRY_AFTER = 60.0

# RETRY-2, besides every 5xx: a request timeout, a conflict and a rate limit.
RETRYABLE_STATUSES = frozenset({408, 409, 429})


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Whether a client sends a failed request again, and when."""

    max_retries: int = DEFAULT_MAX_RETRIES
    """Retries after the first attempt; 0 disables them (RETRY-1)."""

    initial_retry_delay: float = DEFAULT_INITIAL_RETRY_DELAY
    """Seconds before the first retry, doubled for each one after (RETRY-3)."""

    max_retry_delay: float = DEFAULT_MAX_RETRY_DELAY
    """The longest wait the doubling reaches (RETRY-3)."""

    max_retry_after: float = DEFAULT_MAX_RETRY_AFTER
    """The longest wait a vendor can ask for and get (RETRY-4)."""

    def __post_init__(self) -> None:
        for name in (
            "max_retries",
            "initial_retry_delay",
            "max_retry_delay",
            "max_retry_after",
        ):
            value = getattr(self, name)
            if not 0 <= value < math.inf:
                raise ValueError(
                    f"Expected a finite {name} of 0 or more, got {value!r}"
                )

    def delay(
        self,
        error: UniLLMError,
        retries: int,
        response: httpx2.Response | None,
        *,
        now: float,
        jitter: float,
    ) -> float | None:
        """The seconds to wait before sending the request again, or None when the
        client raises `error` instead (RETRY-6).

        Args:
            error: What the last attempt raised.
            retries: The retries already made.
            response: The last attempt's response, if it received one.
            now: The current time as a POSIX timestamp, for a retry-after date.
            jitter: A random number in [0, 1).
        """
        if retries >= self.max_retries or not is_retryable(error):
            return None
        asked = None if response is None else retry_after(response.headers, now)
        if asked is not None and 0 <= asked <= self.max_retry_after:
            return asked
        return backoff(retries, jitter, self.initial_retry_delay, self.max_retry_delay)


def is_retryable(error: UniLLMError) -> bool:
    """Whether another attempt may pass where one raised `error` (RETRY-2).

    The decision is on the status code the error carries, which is the HTTP
    status or the code of an error in the body of a successful response, as
    OpenRouter sends: both shapes get the same answer.
    """
    if isinstance(error, TransportError):
        return True
    if not isinstance(error, ProviderError) or error.status_code is None:
        return False
    status = error.status_code
    return status in RETRYABLE_STATUSES or 500 <= status <= 599


def backoff(
    retries: int,
    jitter: float,
    initial_retry_delay: float = DEFAULT_INITIAL_RETRY_DELAY,
    max_retry_delay: float = DEFAULT_MAX_RETRY_DELAY,
) -> float:
    """The wait before the next retry when the vendor asks for none:
    `initial_retry_delay` after the first attempt, doubling up to
    `max_retry_delay`, less up to a quarter (RETRY-3)."""
    # A capped exponent keeps a large max_retries from overflowing the float.
    longest = min(initial_retry_delay * 2.0 ** min(retries, 32), max_retry_delay)
    return longest * (1 - jitter / 4)


def retry_after(headers: Mapping[str, str], now: float) -> float | None:
    """The seconds the vendor asks to wait (RETRY-4): ``retry-after-ms``, else
    ``retry-after`` in seconds or as an HTTP date, counted from `now`. None when
    it asks for nothing readable."""
    milliseconds = _number(headers.get("retry-after-ms"))
    if milliseconds is not None:
        return milliseconds / 1000
    value = headers.get("retry-after")
    if value is None:
        return None
    seconds = _number(value)
    if seconds is not None:
        return seconds
    try:
        date = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if date.tzinfo is None:  # "-0000": a UTC time from an unknown zone
        date = date.replace(tzinfo=UTC)
    return date.timestamp() - now


@contextmanager
def wrap_transport_errors() -> Iterator[None]:
    """Raise the HTTP library's connection failures and timeouts as
    `TransportError`, with the original as the cause (RETRY-5)."""
    try:
        yield
    except httpx2.TransportError as error:
        raise TransportError(str(error) or type(error).__name__) from error


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None
